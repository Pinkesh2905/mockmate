import csv
import os
from django.core.management.base import BaseCommand
from core.models import Contest
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Import contests from contests.csv file.'

    def handle(self, *args, **kwargs):
        csv_path = os.path.join('core', 'data', 'contests.csv')

        with open(csv_path, encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                Contest.objects.update_or_create(
                    slug=row['slug'],
                    defaults={
                        'title': row['title'],
                        'description': row['description'],
                        'start_time': parse_datetime(row['start_time']),
                        'end_time': parse_datetime(row['end_time']),
                        'registration_url': row['registration_url']
                    }
                )

        self.stdout.write(self.style.SUCCESS('✅ Contests imported successfully.'))
