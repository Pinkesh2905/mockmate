import csv
import json
import os
import uuid
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.text import slugify
from django.db import transaction
from practice.models import PracticeProblem, Category, Tag, TestCase

class Command(BaseCommand):
    help = 'Import problems from CSV files with safe UUID handling'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before importing',
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            with transaction.atomic():
                TestCase.objects.all().delete()
                PracticeProblem.objects.all().delete()
                Tag.objects.all().delete() 
                Category.objects.all().delete()
            self.stdout.write('Existing data cleared.')
        
        fixtures_dir = os.path.join(
            settings.BASE_DIR, 
            'practice',
            'fixtures'
        )
        
        self.stdout.write('Starting import...')
        
        # Import in correct order with transactions
        with transaction.atomic():
            self.import_categories(os.path.join(fixtures_dir, 'categories.csv'))
            self.import_tags(os.path.join(fixtures_dir, 'tags.csv'))
            self.import_problems(os.path.join(fixtures_dir, 'coding_problems.csv'))
            self.import_test_cases(os.path.join(fixtures_dir, 'test_cases.csv'))
        
        self.stdout.write(
            self.style.SUCCESS('Successfully imported all data!')
        )
    
    def import_categories(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Always create new - avoid get_or_create to prevent UUID lookups
                    if not Category.objects.filter(name=row['name']).exists():
                        category = Category.objects.create(
                            name=row['name'],
                            description=row.get('description', ''),
                            color_code=row.get('color_code', '#3B82F6')
                        )
                        self.stdout.write(f'Created category: {category.name}')
                    else:
                        self.stdout.write(f'Category already exists: {row["name"]}')
            self.stdout.write('Categories imported.')
        except FileNotFoundError:
            self.stdout.write('Categories CSV not found, skipping...')
        except Exception as e:
            self.stdout.write(f'Error importing categories: {str(e)}')
    
    def import_tags(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Always create new - avoid get_or_create to prevent UUID lookups
                    if not Tag.objects.filter(name=row['name']).exists():
                        tag = Tag.objects.create(name=row['name'])
                        self.stdout.write(f'Created tag: {tag.name}')
                    else:
                        self.stdout.write(f'Tag already exists: {row["name"]}')
            self.stdout.write('Tags imported.')
        except FileNotFoundError:
            self.stdout.write('Tags CSV not found, skipping...')
        except Exception as e:
            self.stdout.write(f'Error importing tags: {str(e)}')
    
    def import_problems(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        # Skip if problem already exists (by title)
                        if PracticeProblem.objects.filter(title=row['title']).exists():
                            self.stdout.write(f'Problem already exists: {row["title"]}')
                            continue
                        
                        # Process hints
                        hints = []
                        if row.get('hints'):
                            try:
                                hints = json.loads(row['hints'])
                            except:
                                hints = [row['hints']]
                        
                        # Get category by name (avoid UUID lookups)
                        category = None
                        if row.get('category_name'):
                            try:
                                category = Category.objects.get(name=row['category_name'])
                            except Category.DoesNotExist:
                                category = Category.objects.create(name=row['category_name'])
                        
                        # Generate unique slug
                        slug = row.get('slug', slugify(row['title']))
                        original_slug = slug
                        counter = 1
                        while PracticeProblem.objects.filter(slug=slug).exists():
                            slug = f"{original_slug}-{counter}"
                            counter += 1
                        
                        # Create problem (let Django generate UUID automatically)
                        problem = PracticeProblem.objects.create(
                            title=row['title'],
                            slug=slug,
                            difficulty=row.get('difficulty', 'EASY'),
                            category=category,
                            companies=row.get('companies', ''),
                            statement=row.get('statement', ''),
                            constraints=row.get('constraints', ''),
                            hints=hints,
                            approach=row.get('approach', ''),
                            time_complexity=row.get('time_complexity', ''),
                            space_complexity=row.get('space_complexity', ''),
                            leetcode_url=row.get('leetcode_url', ''),
                            hackerrank_url=row.get('hackerrank_url', ''),
                            external_url=row.get('external_url', ''),
                            time_limit=int(row['time_limit']) if row.get('time_limit') else 5,
                            memory_limit=int(row['memory_limit']) if row.get('memory_limit') else 256,
                            is_premium=row.get('is_premium', '').upper() == 'TRUE',
                            is_private=row.get('is_private', '').upper() == 'TRUE',
                            status=row.get('status', 'PUBLISHED'),
                        )
                        
                        # Add tags
                        if row.get('tags'):
                            tag_names = [name.strip() for name in row['tags'].split(',')]
                            for tag_name in tag_names:
                                if tag_name:  # Skip empty tag names
                                    try:
                                        tag = Tag.objects.get(name=tag_name)
                                    except Tag.DoesNotExist:
                                        tag = Tag.objects.create(name=tag_name)
                                    problem.tags.add(tag)
                        
                        self.stdout.write(f'Created: {problem.title} (UUID: {problem.id})')
                    
                    except Exception as e:
                        self.stdout.write(f'Error creating problem "{row.get("title", "Unknown")}": {str(e)}')
                        
        except FileNotFoundError:
            self.stdout.write('Problems CSV not found!')
        except Exception as e:
            self.stdout.write(f'Error importing problems: {str(e)}')
    
    def import_test_cases(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        # Find problem by title (avoid UUID lookups)
                        problem = PracticeProblem.objects.get(title=row['problem_title'])
                        
                        # Always create new test case (avoid get_or_create)
                        test_case = TestCase.objects.create(
                            problem=problem,
                            input_data=row['input_data'],
                            expected_output=row['expected_output'],
                            is_sample=row.get('is_sample', '').upper() == 'TRUE',
                            is_hidden=row.get('is_hidden', 'TRUE').upper() == 'TRUE',
                            description=row.get('description', ''),
                            explanation=row.get('explanation', ''),
                            difficulty_weight=int(row.get('difficulty_weight', 1)),
                            order=int(row.get('order', 0))
                        )
                        self.stdout.write(f'Created test case for: {problem.title}')
                    except PracticeProblem.DoesNotExist:
                        self.stdout.write(f'Problem not found: {row.get("problem_title", "Unknown")}')
                    except Exception as e:
                        self.stdout.write(f'Error creating test case: {str(e)}')
            self.stdout.write('Test cases imported.')
        except FileNotFoundError:
            self.stdout.write('Test cases CSV not found, skipping...')
        except Exception as e:
            self.stdout.write(f'Error importing test cases: {str(e)}')