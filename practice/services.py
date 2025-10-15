import requests
import json
import time
import csv
import io
import logging
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction
from django.core.exceptions import ValidationError
from typing import List, Dict, Any
from .models import (
    TestCase, PracticeProblem, UserProblemStats, UserStats, 
    Badge, UserBadge, PracticeSubmission, Category, Tag
)

logger = logging.getLogger(__name__)

# JDoodle API Configuration
JDOODLE_CLIENT_ID = getattr(settings, 'JDOODLE_CLIENT_ID', '')
JDOODLE_CLIENT_SECRET = getattr(settings, 'JDOODLE_CLIENT_SECRET', '')
JDOODLE_API_URL = "https://api.jdoodle.com/v1/execute"

# Language mapping for JDoodle - FIXED: Changed 'version' key
LANGUAGE_MAPPING = {
    'python3': {'language': 'python3', 'versionIndex': '0'},
    'cpp17': {'language': 'cpp17', 'versionIndex': '0'},
    'java': {'language': 'java', 'versionIndex': '3'},
    'javascript': {'language': 'nodejs', 'versionIndex': '3'},
    'csharp': {'language': 'csharp', 'versionIndex': '3'},
    'go': {'language': 'go', 'versionIndex': '3'},
    'rust': {'language': 'rust', 'versionIndex': '3'},
    'php': {'language': 'php', 'versionIndex': '3'},
    'ruby': {'language': 'ruby', 'versionIndex': '3'},
    'kotlin': {'language': 'kotlin', 'versionIndex': '2'},
    'swift': {'language': 'swift', 'versionIndex': '3'},
}

class CodeExecutionService:
    """Service to handle code execution via JDoodle API"""

    @staticmethod
    def run_code(language: str, code: str, std_input: str) -> Dict[str, Any]:
        """Runs a single piece of code with given input."""
        if language not in LANGUAGE_MAPPING:
            return {'error': 'Unsupported language', 'output': ''}

        lang_info = LANGUAGE_MAPPING[language]

        payload = {
            'clientId': JDOODLE_CLIENT_ID,
            'clientSecret': JDOODLE_CLIENT_SECRET,
            'script': code,
            'stdin': std_input,
            'language': lang_info['language'],
            'versionIndex': lang_info['versionIndex']  # FIXED: Now matches the dict key
        }

        try:
            response = requests.post(JDOODLE_API_URL, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            # Check for errors from the API itself (e.g., compilation)
            if 'error' in result and result['error']:
                return {
                    'output': result.get('output', ''),
                    'memory': result.get('memory'),
                    'cpuTime': result.get('cpuTime'),
                    'error': result.get('error'),
                    'is_compilation_error': True,
                }

            return {
                'output': result.get('output', '').strip(),
                'memory': result.get('memory'),
                'cpuTime': result.get('cpuTime'),
                'error': None,
                'is_compilation_error': False,
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"JDoodle API request failed: {e}")
            return {'error': 'Failed to connect to execution service.', 'output': ''}
        except Exception as e:
            logger.error(f"An unexpected error occurred during code execution: {e}")
            return {'error': str(e), 'output': ''}
    
    @staticmethod
    def run_against_test_cases(code: str, language: str, test_cases, time_limit: int = 5) -> List[Dict]:
        """Run code against multiple test cases (for sample test runs)"""
        results = []
        
        for test_case in test_cases:
            execution_result = CodeExecutionService.run_code(
                language, 
                code, 
                test_case.input_data
            )
            
            # Handle compilation errors
            if execution_result.get('is_compilation_error'):
                results.append({
                    "test_case_id": str(test_case.id),
                    "description": test_case.description or "Test Case",
                    "passed": False,
                    "error": "Compilation Error",
                    "error_message": execution_result.get('output', 'Compilation failed'),
                    "input": test_case.input_data if test_case.is_sample else "[Hidden]",
                    "expected_output": test_case.expected_output if test_case.is_sample else "[Hidden]",
                    "actual_output": "",
                    "execution_time": 0
                })
                break  # Stop on compilation error
            
            # Handle runtime errors
            if execution_result.get('error'):
                results.append({
                    "test_case_id": str(test_case.id),
                    "description": test_case.description or "Test Case",
                    "passed": False,
                    "error": "Runtime Error",
                    "error_message": execution_result['error'],
                    "input": test_case.input_data if test_case.is_sample else "[Hidden]",
                    "expected_output": test_case.expected_output if test_case.is_sample else "[Hidden]",
                    "actual_output": execution_result.get('output', ''),
                    "execution_time": execution_result.get('cpuTime', 0)
                })
                continue
            
            # Compare outputs
            actual_output = execution_result['output'].strip()
            expected_output = test_case.expected_output.strip()
            passed = actual_output == expected_output
            
            results.append({
                "test_case_id": str(test_case.id),
                "description": test_case.description or f"Test Case {test_case.order + 1}",
                "passed": passed,
                "input": test_case.input_data if test_case.is_sample else "[Hidden]",
                "expected_output": expected_output if test_case.is_sample else "[Hidden]",
                "actual_output": actual_output if test_case.is_sample else ("[Hidden]" if not passed else "[Correct]"),
                "execution_time": execution_result.get('cpuTime', 0),
                "memory": execution_result.get('memory', 0)
            })
        
        return results
    
    @staticmethod
    def evaluate_submission(submission: PracticeSubmission) -> Dict[str, Any]:
        """
        Evaluates a submission against all test cases for the associated problem.
        This is the heart of the LeetCode-style evaluation.
        """
        problem = submission.problem
        test_cases = TestCase.objects.filter(problem=problem).order_by('order')
        
        if not test_cases.exists():
            return {
                "status": "INTERNAL_ERROR",
                "message": "No test cases found for this problem.",
                "passed_cases": 0,
                "total_cases": 0,
                "results": [],
                "execution_time": 0,
                "memory_used": 0,
            }

        passed_count = 0
        total_count = len(test_cases)
        overall_status = "ACCEPTED"
        individual_results = []
        
        max_cpu_time = 0.0
        max_memory = 0

        for i, test_case in enumerate(test_cases):
            execution_result = CodeExecutionService.run_code(
                submission.language,
                submission.code,
                test_case.input_data
            )

            # Update max resource usage
            if execution_result.get('cpuTime'):
                max_cpu_time = max(max_cpu_time, float(execution_result['cpuTime']))
            if execution_result.get('memory'):
                max_memory = max(max_memory, int(execution_result['memory']))

            # Handle compilation or fatal API errors
            if execution_result.get('is_compilation_error'):
                overall_status = "COMPILATION_ERROR"
                individual_results.append({
                    "case_number": i + 1,
                    "status": "Compilation Error",
                    "input": test_case.input_data if test_case.is_sample else "[Hidden]",
                    "error_message": execution_result.get('output', 'Compilation failed')
                })
                break  # Stop evaluation on compilation error
            
            # Handle runtime errors during execution
            if execution_result['error']:
                overall_status = "RUNTIME_ERROR"
                individual_results.append({
                    "case_number": i + 1,
                    "status": "Runtime Error",
                    "input": test_case.input_data if test_case.is_sample else "[Hidden]",
                    "error_message": execution_result['error']
                })
                break  # Stop evaluation on first runtime error

            # Compare outputs
            actual_output = execution_result['output']
            expected_output = test_case.expected_output.strip()

            case_result = {
                "case_number": i + 1,
                "is_sample": test_case.is_sample,
                "input": test_case.input_data if test_case.is_sample else "[Hidden]",
                "expected_output": expected_output if test_case.is_sample else "[Hidden]",
                "actual_output": actual_output if test_case.is_sample else "[Hidden]",
            }

            if actual_output == expected_output:
                passed_count += 1
                case_result["status"] = "PASSED"
            else:
                overall_status = "WRONG_ANSWER"
                case_result["status"] = "FAILED"
            
            individual_results.append(case_result)
            
            # Optional: Stop on first failure for faster feedback
            # if overall_status == "WRONG_ANSWER":
            #     break

        final_result = {
            "status": overall_status,
            "passed_cases": passed_count,
            "total_cases": total_count,
            "results": individual_results,
            "execution_time": max_cpu_time,
            "memory_used": max_memory,
        }
        return final_result


class TestCaseService:
    
    @staticmethod
    def import_test_cases_from_csv(problem, csv_file):
        """
        Import test cases from CSV file for a specific problem.
        Expected CSV columns: input_data, expected_output, is_sample, is_hidden, 
                             description, explanation, difficulty_weight, order
        """
        try:
            csv_file.seek(0)
            content = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            
            created_count = 0
            for row in reader:
                TestCase.objects.create(
                    problem=problem,
                    input_data=row.get('input_data', '').strip(),
                    expected_output=row.get('expected_output', '').strip(),
                    is_sample=row.get('is_sample', 'FALSE').upper() == 'TRUE',
                    is_hidden=row.get('is_hidden', 'TRUE').upper() == 'TRUE',
                    description=row.get('description', ''),
                    explanation=row.get('explanation', ''),
                    difficulty_weight=int(row.get('difficulty_weight', 1)),
                    order=int(row.get('order', 0))
                )
                created_count += 1
            
            return created_count
            
        except Exception as e:
            raise ValidationError(f"Error importing test cases: {str(e)}")
    
    @staticmethod
    def import_problems_from_csv(csv_file, created_by):
        """
        Import problems from CSV (problems only, without test cases).
        For bulk problem upload without test cases.
        """
        try:
            csv_file.seek(0)
            content = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            
            imported_count = 0
            
            for row in reader:
                # Check if problem already exists
                slug = row.get('slug') or slugify(row.get('title', ''))
                if PracticeProblem.objects.filter(slug=slug).exists():
                    logger.warning(f"Problem with slug '{slug}' already exists, skipping...")
                    continue
                
                # Parse tags and companies
                tags_list = [tag.strip() for tag in row.get('tags', '').split(',') if tag.strip()]
                companies = row.get('companies', '').strip()
                
                # Parse hints from JSON string or comma-separated
                hints = row.get('hints', '')
                try:
                    hints_list = json.loads(hints) if hints else []
                except:
                    hints_list = [h.strip() for h in hints.split(',') if h.strip()]
                
                # Get or create category
                category = None
                category_name = row.get('category_name', '').strip()
                if category_name:
                    category, _ = Category.objects.get_or_create(
                        name=category_name,
                        defaults={'description': f'{category_name} problems'}
                    )
                
                # Create problem
                problem = PracticeProblem.objects.create(
                    title=row.get('title'),
                    slug=slug,
                    difficulty=row.get('difficulty', 'EASY').upper(),
                    category=category,
                    companies=companies,
                    statement=row.get('statement', ''),
                    constraints=row.get('constraints', ''),
                    hints=hints_list,
                    approach=row.get('approach', ''),
                    time_complexity=row.get('time_complexity', ''),
                    space_complexity=row.get('space_complexity', ''),
                    leetcode_url=row.get('leetcode_url', ''),
                    hackerrank_url=row.get('hackerrank_url', ''),
                    external_url=row.get('external_url', ''),
                    time_limit=int(row.get('time_limit', 5)),
                    memory_limit=int(row.get('memory_limit', 256)),
                    is_premium=row.get('is_premium', 'FALSE').upper() == 'TRUE',
                    is_private=row.get('is_private', 'FALSE').upper() == 'TRUE',
                    status=row.get('status', 'DRAFT'),  # Start as DRAFT for review
                    created_by=created_by
                )
                
                # Add tags
                for tag_name in tags_list:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    problem.tags.add(tag)
                
                imported_count += 1
                logger.info(f"Imported problem: {problem.title}")
            
            return imported_count
            
        except Exception as e:
            raise ValidationError(f"Error importing problems: {str(e)}")
    
    @staticmethod
    def update_user_problem_stats(user, problem, submission, status):
        """Update user statistics after submission"""
        user_problem_stats, created = UserProblemStats.objects.get_or_create(
            user=user,
            problem=problem
        )
        
        user_problem_stats.is_attempted = True
        user_problem_stats.total_attempts += 1
        
        if status == 'ACCEPTED':
            if not user_problem_stats.is_solved:
                user_problem_stats.is_solved = True
                user_problem_stats.first_solved_at = timezone.now()
                
                # Update user overall stats
                user_stats, _ = UserStats.objects.get_or_create(user=user)
                user_stats.problems_solved += 1
                user_stats.accepted_submissions += 1
                user_stats.total_submissions += 1
                
                # Update difficulty-specific counts
                if problem.difficulty == 'EASY':
                    user_stats.easy_solved += 1
                elif problem.difficulty == 'MEDIUM':
                    user_stats.medium_solved += 1
                elif problem.difficulty == 'HARD':
                    user_stats.hard_solved += 1
                
                user_stats.update_streak()
                user_stats.save()
                
                # Award badges
                BadgeService.check_and_award_badges(user)
            else:
                # Still count the submission even if already solved
                user_stats, _ = UserStats.objects.get_or_create(user=user)
                user_stats.total_submissions += 1
                user_stats.save()
            
            # Update best submission
            if submission.execution_time:
                if not user_problem_stats.best_runtime or submission.execution_time < user_problem_stats.best_runtime:
                    user_problem_stats.best_runtime = submission.execution_time
                    user_problem_stats.best_submission = submission
            
            if submission.memory_used:
                if not user_problem_stats.best_memory or submission.memory_used < user_problem_stats.best_memory:
                    user_problem_stats.best_memory = submission.memory_used
        else:
            # Failed submission - still count it
            user_stats, _ = UserStats.objects.get_or_create(user=user)
            user_stats.total_submissions += 1
            user_stats.save()
        
        user_problem_stats.save()
        
        # Update problem statistics
        problem.total_submissions += 1
        if status == 'ACCEPTED':
            problem.accepted_submissions += 1
        problem.save()


class BadgeService:
    """Service for handling badge awards"""
    
    @staticmethod
    def check_and_award_badges(user):
        """Check and award badges based on user achievements"""
        try:
            user_stats = UserStats.objects.get(user=user)
            
            # First submission badge
            if user_stats.total_submissions == 1:
                BadgeService.award_badge(user, "First Submission")
            
            # First accepted solution
            if user_stats.accepted_submissions == 1:
                BadgeService.award_badge(user, "First Accepted Solution")
            
            # Problem milestone badges
            if user_stats.problems_solved == 10:
                BadgeService.award_badge(user, "Problem Solver")
            elif user_stats.problems_solved == 50:
                BadgeService.award_badge(user, "Coding Enthusiast")
            elif user_stats.problems_solved == 100:
                BadgeService.award_badge(user, "Coding Master")
            
            # Streak badges
            if user_stats.current_streak == 7:
                BadgeService.award_badge(user, "Week Warrior")
            elif user_stats.current_streak == 30:
                BadgeService.award_badge(user, "Monthly Master")
            
            # Difficulty badges
            if user_stats.easy_solved >= 25:
                BadgeService.award_badge(user, "Easy Mode Champion")
            if user_stats.medium_solved >= 25:
                BadgeService.award_badge(user, "Medium Mode Master")
            if user_stats.hard_solved >= 10:
                BadgeService.award_badge(user, "Hard Mode Hero")
                
        except Exception as e:
            logger.error(f"Error checking badges: {str(e)}")
    
    @staticmethod
    def award_badge(user, badge_name: str) -> bool:
        """Award a badge to a user if they don't have it"""
        try:
            badge = Badge.objects.get(name=badge_name)
            user_badge, created = UserBadge.objects.get_or_create(user=user, badge=badge)
            
            if created:
                # Award points
                user_stats = UserStats.objects.get(user=user)
                user_stats.total_points += 10  # Base points for badge
                user_stats.save()
                logger.info(f"Awarded badge '{badge_name}' to user {user.username}")
                return True
            return False
            
        except Badge.DoesNotExist:
            logger.warning(f"Badge '{badge_name}' does not exist")
            return False
        except Exception as e:
            logger.error(f"Error awarding badge: {str(e)}")
            return False


class AnalyticsService:
    """Service for analytics and insights"""
    
    @staticmethod
    def get_user_insights(user):
        """Get detailed insights for a user"""
        try:
            user_stats = UserStats.objects.get(user=user)
            user_problem_stats = UserProblemStats.objects.filter(user=user)
            
            # Calculate additional metrics
            total_problems = PracticeProblem.objects.filter(status='PUBLISHED').count()
            completion_rate = (user_stats.problems_solved / total_problems) * 100 if total_problems > 0 else 0
            
            # Language distribution
            submissions = PracticeSubmission.objects.filter(user=user)
            language_stats = {}
            for submission in submissions:
                lang = submission.get_language_display()
                language_stats[lang] = language_stats.get(lang, 0) + 1
            
            # Recent activity
            recent_activity = submissions.order_by('-submitted_at')[:10]
            
            return {
                'completion_rate': completion_rate,
                'language_stats': language_stats,
                'recent_activity': recent_activity,
                'total_problems_available': total_problems
            }
            
        except Exception as e:
            logger.error(f"Error getting user insights: {str(e)}")
            return {}
    
    @staticmethod
    def get_platform_metrics():
        """Get platform-wide metrics"""
        try:
            from django.db.models import Count, Avg
            
            total_users = UserStats.objects.count()
            total_problems = PracticeProblem.objects.filter(status='PUBLISHED').count()
            total_submissions = PracticeSubmission.objects.count()
            
            # Average acceptance rate
            avg_acceptance = PracticeProblem.objects.filter(
                status='PUBLISHED'
            ).aggregate(Avg('acceptance_rate'))['acceptance_rate__avg'] or 0
            
            # Most popular problems
            popular_problems = PracticeProblem.objects.filter(
                status='PUBLISHED'
            ).annotate(
                submission_count=Count('submissions')
            ).order_by('-submission_count')[:10]
            
            return {
                'total_users': total_users,
                'total_problems': total_problems,
                'total_submissions': total_submissions,
                'average_acceptance_rate': avg_acceptance,
                'popular_problems': popular_problems
            }
            
        except Exception as e:
            logger.error(f"Error getting platform metrics: {str(e)}")
            return {}