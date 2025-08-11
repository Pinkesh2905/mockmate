import csv
from django.core.management.base import BaseCommand
from core.models import PracticeProblem
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Import practice problems from CSV file'

    def handle(self, *args, **kwargs):
        with open('practice_problems.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                title = row['title']
                slug = row['slug']
                topic = row['topic']
                statement = row['description']  # CSV has 'description', your model uses 'statement'
                difficulty = row['difficulty']

                PracticeProblem.objects.get_or_create(
                    title=title,
                    slug=slug,
                    defaults={
                        'topic': topic,
                        'statement': statement,
                        'difficulty': difficulty,
                    }
                )

        self.stdout.write(self.style.SUCCESS('✅ Practice problems imported successfully!'))
