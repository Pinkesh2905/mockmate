import requests
import json
import time
import csv
import io
import logging
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from typing import List, Dict, Any
from .models import (
    TestCase, PracticeProblem, UserProblemStats, UserStats, 
    Badge, UserBadge, PracticeSubmission
)

logger = logging.getLogger(__name__)

# JDoodle API Configuration
JDOODLE_CLIENT_ID = getattr(settings, 'JDOODLE_CLIENT_ID', '')
JDOODLE_CLIENT_SECRET = getattr(settings, 'JDOODLE_CLIENT_SECRET', '')
JDOODLE_API_URL = "https://api.jdoodle.com/v1/execute"

# Language mapping for JDoodle
LANGUAGE_MAPPING = {
    'python3': {'language': 'python3', 'version': '0'},
    'cpp17': {'language': 'cpp17', 'version': '0'},
    'java': {'language': 'java', 'version': '3'},
    'javascript': {'language': 'nodejs', 'version': '3'},
    'csharp': {'language': 'csharp', 'version': '3'},
    'go': {'language': 'go', 'version': '3'},
    'rust': {'language': 'rust', 'version': '3'},
    'php': {'language': 'php', 'version': '3'},
    'ruby': {'language': 'ruby', 'version': '3'},
    'kotlin': {'language': 'kotlin', 'version': '2'},
    'swift': {'language': 'swift', 'version': '3'},
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
            'versionIndex': lang_info['versionIndex']
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
    
    # --- NEW: Core logic for evaluating a submission against all test cases ---
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
                "status": "RUNTIME_ERROR",
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
                    "input": test_case.input_data,
                    "error_message": execution_result.get('output') # JDoodle puts compile errors in output
                })
                break # Stop evaluation on compilation error
            
            # Handle runtime errors during execution
            if execution_result['error']:
                overall_status = "RUNTIME_ERROR"
                individual_results.append({
                    "case_number": i + 1,
                    "status": "Runtime Error",
                    "input": test_case.input_data,
                    "error_message": execution_result['error']
                })
                break # Stop evaluation on first runtime error

            # Compare outputs
            actual_output = execution_result['output']
            expected_output = test_case.expected_output.strip()

            case_result = {
                "case_number": i + 1,
                "is_sample": test_case.is_sample,
                "input": test_case.input_data,
                "expected_output": expected_output,
                "actual_output": actual_output,
            }

            if actual_output == expected_output:
                passed_count += 1
                case_result["status"] = "PASSED"
            else:
                overall_status = "WRONG_ANSWER"
                case_result["status"] = "FAILED"
            
            individual_results.append(case_result)
        
            # If a case fails, we can stop, but for providing full feedback, we continue.
            # If you want to stop on the first failure, uncomment the following lines:
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
    """Service for handling test case operations"""
    
    @staticmethod
    def import_test_cases_from_csv(problem: PracticeProblem, csv_file) -> int:
        """Import test cases from CSV file"""
        try:
            csv_file.seek(0)
            content = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            
            imported_count = 0
            with transaction.atomic():
                # Clear existing test cases if any
                problem.test_cases.all().delete()
                
                for i, row in enumerate(reader):
                    # Required fields
                    input_data = row.get('input_data', '').strip()
                    expected_output = row.get('expected_output', '').strip()
                    
                    if not input_data or not expected_output:
                        continue
                    
                    # Optional fields with defaults
                    is_sample = str(row.get('is_sample', 'False')).lower() in ['true', '1', 'yes']
                    is_hidden = str(row.get('is_hidden', 'True')).lower() in ['true', '1', 'yes']
                    description = row.get('description', f'Test Case {i+1}')
                    difficulty_weight = int(row.get('difficulty_weight', 1))
                    order = int(row.get('order', i))
                    
                    TestCase.objects.create(
                        problem=problem,
                        input_data=input_data,
                        expected_output=expected_output,
                        is_sample=is_sample,
                        is_hidden=is_hidden,
                        description=description,
                        difficulty_weight=max(1, min(10, difficulty_weight)),
                        order=order
                    )
                    imported_count += 1
                
            return imported_count
            
        except Exception as e:
            logger.error(f"Error importing test cases from CSV: {str(e)}")
            raise
    
    @staticmethod
    def import_problems_from_csv(csv_file, created_by_user) -> int:
        """Import problems from CSV file"""
        try:
            csv_file.seek(0)
            content = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            
            imported_count = 0
            with transaction.atomic():
                for row in reader:
                    title = row.get('title', '').strip()
                    if not title:
                        continue
                    
                    problem = PracticeProblem.objects.create(
                        title=title,
                        difficulty=row.get('difficulty', 'EASY').upper(),
                        statement=row.get('statement', ''),
                        constraints=row.get('constraints', ''),
                        companies=row.get('companies', ''),
                        time_complexity=row.get('time_complexity', ''),
                        space_complexity=row.get('space_complexity', ''),
                        time_limit=int(row.get('time_limit', 5)),
                        memory_limit=int(row.get('memory_limit', 256)),
                        created_by=created_by_user,
                        status='PENDING_APPROVAL'
                    )
                    imported_count += 1
                
            return imported_count
            
        except Exception as e:
            logger.error(f"Error importing problems from CSV: {str(e)}")
            raise
    
    @staticmethod
    def update_user_problem_stats(user, problem, submission, status):
        """Update user problem statistics after submission"""
        try:
            user_problem_stats, created = UserProblemStats.objects.get_or_create(
                user=user,
                problem=problem
            )
            
            user_problem_stats.is_attempted = True
            user_problem_stats.total_attempts += 1
            
            if status == 'ACCEPTED' and not user_problem_stats.is_solved:
                user_problem_stats.is_solved = True
                user_problem_stats.first_solved_at = timezone.now()
                
                # Update problem statistics
                problem.accepted_submissions = problem.submissions.filter(status='ACCEPTED').count()
                
                # Update user overall stats
                user_stats, created = UserStats.objects.get_or_create(user=user)
                user_stats.problems_solved += 1
                user_stats.accepted_submissions += 1
                
                # Update difficulty-specific stats
                if problem.difficulty == 'EASY':
                    user_stats.easy_solved += 1
                elif problem.difficulty == 'MEDIUM':
                    user_stats.medium_solved += 1
                elif problem.difficulty == 'HARD':
                    user_stats.hard_solved += 1
                
                # Update streak
                user_stats.update_streak()
                user_stats.save()
            
            # Update best submission if applicable
            if not user_problem_stats.best_submission or submission.score > user_problem_stats.best_submission.score:
                user_problem_stats.best_submission = submission
                user_problem_stats.best_runtime = submission.total_runtime or 0
                user_problem_stats.best_memory = submission.peak_memory or 0
                user_problem_stats.best_score = submission.score
            
            user_problem_stats.save()
            
            # Update problem statistics
            problem.total_submissions = problem.submissions.count()
            problem.save()
            
        except Exception as e:
            logger.error(f"Error updating user problem stats: {str(e)}")

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
            recent_activity = submissions.order_by('-submission_time')[:10]
            
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