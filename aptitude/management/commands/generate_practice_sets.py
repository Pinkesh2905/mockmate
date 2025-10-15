from django.core.management.base import BaseCommand
from django.db import transaction
from aptitude.models import AptitudeCategory, AptitudeTopic, AptitudeProblem, PracticeSet
import random

class Command(BaseCommand):
    help = 'Generate practice sets automatically from existing problems'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of practice sets to generate'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options['count']
        
        categories = AptitudeCategory.objects.all()
        if not categories.exists():
            self.stdout.write(self.style.ERROR('No categories found. Import categories first.'))
            return
        
        practice_sets_created = 0
        
        for category in categories:
            problems = AptitudeProblem.objects.filter(topic__category=category)
            
            if problems.count() < 5:
                continue
                
            # Create category-wise practice sets
            for difficulty in ['Easy', 'Medium', 'Hard']:
                difficulty_problems = problems.filter(difficulty=difficulty)
                if difficulty_problems.count() >= 5:
                    practice_set = PracticeSet.objects.create(
                        title=f"{category.name} - {difficulty} Level",
                        description=f"Practice set for {category.name} with {difficulty.lower()} difficulty problems"
                    )
                    
                    # Add random problems
                    selected_problems = random.sample(list(difficulty_problems), min(10, difficulty_problems.count()))
                    practice_set.problems.set(selected_problems)
                    practice_sets_created += 1
            
            # Create mixed difficulty practice set
            if problems.count() >= 10:
                practice_set = PracticeSet.objects.create(
                    title=f"{category.name} - Mixed Practice",
                    description=f"Mixed difficulty practice set for {category.name}"
                )
                
                selected_problems = random.sample(list(problems), min(15, problems.count()))
                practice_set.problems.set(selected_problems)
                practice_sets_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Generated {practice_sets_created} practice sets')
        )