from django.core.management.base import BaseCommand
from core.models import Course
import csv

class Command(BaseCommand):
    help = "Import course data from CSV"

    def handle(self, *args, **kwargs):
        with open('courses.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                title = row['title']
                slug = row['slug']
                description = row['description']
                Course.objects.get_or_create(title=title, slug=slug, defaults={'description': description})

        self.stdout.write(self.style.SUCCESS("✅ Courses imported successfully"))
