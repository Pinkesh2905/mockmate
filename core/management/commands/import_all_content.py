
import sys
import csv

# Fix large field error for huge HTML chunks
csv.field_size_limit(sys.maxsize)
from bs4 import BeautifulSoup

import os
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from core.models import (
    Topic, Lesson, Quiz, Question, Option,
    CodeExample, Article, Course, PracticeProblem
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '../../../core/data')


class Command(BaseCommand):
    help = '📦 Import all core learning content (topics, lessons, quizzes, articles, etc) from CSV files.'

    def handle(self, *args, **kwargs):
        print("🚀 Starting import...")
        self.import_topics()
        self.import_lessons()
        self.import_questions()
        self.import_code_examples()
        self.import_articles()
        self.import_courses()
        self.import_practice_problems()
        self.stdout.write(self.style.SUCCESS('✅ All content imported successfully.\n'))

    def import_topics(self):
        print("📘 Importing topics...")
        with open(os.path.join(DATA_DIR, 'topics.csv'), encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                Topic.objects.get_or_create(
                    slug=row['topic_slug'],
                    defaults={
                        'name': row['topic_name'],
                        'description': row['topic_description']
                    }
                )

    def import_lessons(self):
        print("📗 Importing lessons...")
        with open(os.path.join(DATA_DIR, 'lessons.csv'), encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    topic = Topic.objects.get(slug=row['topic_slug'])
                    Lesson.objects.get_or_create(
                        topic=topic,
                        title=row['lesson_title'],
                        defaults={
                            'content': row['lesson_content'],
                            'order': int(row.get('lesson_order', 0))
                        }
                    )
                except Topic.DoesNotExist:
                    print(f"❌ Topic not found for lesson: {row['topic_slug']}")

    def import_questions(self):
        print("❓ Importing quiz questions...")
        with open(os.path.join(DATA_DIR, 'questions.csv'), encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    topic = Topic.objects.get(slug=row['topic_slug'])
                    quiz, _ = Quiz.objects.get_or_create(topic=topic, defaults={'title': f"{topic.name} Quiz"})

                    question, created = Question.objects.get_or_create(
                        quiz=quiz,
                        question_text=row['question_text'],
                        defaults={'explanation': row['explanation']}
                    )

                    if created:
                        Option.objects.create(question=question, text=row['option_1'], is_correct=(int(row['correct_option']) == 1))
                        Option.objects.create(question=question, text=row['option_2'], is_correct=(int(row['correct_option']) == 2))
                        Option.objects.create(question=question, text=row['option_3'], is_correct=(int(row['correct_option']) == 3))
                        Option.objects.create(question=question, text=row['option_4'], is_correct=(int(row['correct_option']) == 4))
                except Topic.DoesNotExist:
                    print(f"❌ Topic not found for question: {row['topic_slug']}")

    def import_code_examples(self):
        print("💻 Importing code examples...")
        with open(os.path.join(DATA_DIR, 'code_examples.csv'), encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    topic = Topic.objects.get(slug=row['topic_slug'])
                    CodeExample.objects.get_or_create(
                        topic=topic,
                        language=row['language'],
                        defaults={'code': row['code']}
                    )
                except Topic.DoesNotExist:
                    print(f"❌ Topic not found for code example: {row['topic_slug']}")

    def import_articles(self):
        print("📰 Importing articles from articles.csv...")
        articles_file = os.path.join(DATA_DIR, 'articles.csv')
        seen_slugs = set()

        with open(articles_file, encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            count = 0
            skipped = 0

            for row in reader:
                title = (row['title'] or '').strip()
                link = (row['link'] or '').strip()

                if not title or not link or not link.startswith('http'):
                    skipped += 1
                    continue

                slug = slugify(title)
                if not slug:
                    skipped += 1
                    continue

                if slug in seen_slugs:
                    slug = f"{slug}-{count}"

                seen_slugs.add(slug)

                Article.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'title': title,
                        'link': link,
                        'category': row.get('category', 'general').strip(),
                        'author_id': row.get('author_id', '').strip(),
                        'tags': '',
                    }
                )
                count += 1

        print(f"✅ Imported {count} articles, skipped {skipped} bad rows.")

        print("📰 Importing articles from articles2.csv...")
        articles2_file = os.path.join(DATA_DIR, 'articles2.csv')
        with open(articles2_file, encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            count = 0
            skipped = 0

            for row in reader:
                title = (row['title'] or '').strip()
                link = (row['link'] or '').strip()

                if not title or not link or not link.startswith('http'):
                    skipped += 1
                    continue

                slug = slugify(title)
                if not slug:
                    skipped += 1
                    continue

                if slug in seen_slugs:
                    slug = f"{slug}-{count}"

                seen_slugs.add(slug)

                Article.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'title': title,
                        'link': link,
                        'category': 'general',
                        'author_id': '',
                        'tags': row.get('tags', '').strip(),
                    }
                )
                count += 1

        print(f"✅ Imported {count} articles from articles2.csv, skipped {skipped} bad rows.")


    def import_courses(self):
        print("🎥 Importing courses from gfg_final.csv...")
        csv_file = os.path.join(DATA_DIR, 'gfg_final.csv')
        seen_slugs = set()
        count = 0
        skipped = 0

        with open(csv_file, encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                title = (row.get('title') or '').strip()
                video_link = (row.get('video_link') or '').strip()
                thumbnail = (row.get('thumbnail_link') or '').strip()

                # Must have title + valid video link
                if not title or not video_link.startswith('http'):
                    skipped += 1
                    continue

                if 'localhost' in video_link or '127.0.0.1' in video_link:
                    skipped += 1
                    continue

                # Normalize YouTube links to embed
                if 'watch?v=' in video_link:
                    video_link = video_link.replace('watch?v=', 'embed/')
                elif 'youtu.be/' in video_link:
                    video_id = video_link.split('youtu.be/')[-1]
                    video_link = f"https://www.youtube.com/embed/{video_id}"

                slug = slugify(title)
                if not slug:
                    skipped += 1
                    continue

                if slug in seen_slugs:
                    slug = f"{slug}-{count}"

                seen_slugs.add(slug)

                # Fallback to default thumb if missing
                final_thumbnail = thumbnail if thumbnail else 'default'

                Course.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'title': title,
                        'video_link': video_link,
                        'thumbnail': final_thumbnail,
                        'duration': row.get('duration', '').strip(),
                        'views': row.get('views', '').strip(),
                        'likes': row.get('likes', '').strip(),
                        'comments': row.get('comments', '').strip(),
                        'date': row.get('date', '').strip(),
                        'description': row.get('description', '').strip(),
                        # Hardcoded safe fallback fields:
                        'category': 'General',
                        'instructor': 'Our Expert',
                        'level': 'Beginner',
                        'total_lessons': 1,
                        'rating': 4.5,
                        'students': 1,
                        'price': 'Free',
                    }
                )

                count += 1

        print(f"✅ Imported {count} courses, skipped {skipped} bad rows.")


    def import_practice_problems(self):
        print("💡 Importing practice problems from gfg_questions_full.csv...")
        problems_file = os.path.join(DATA_DIR, 'gfg_questions_full.csv')
        seen_slugs = set()
        with open(problems_file, encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            count = 0
            skipped = 0

            for row in reader:
                title = (row.get('title') or '').strip()
                url = (row.get('url') or '').strip()
                raw_description = (row.get('description') or '').strip()

                if not url or not url.startswith('http'):
                    skipped += 1
                    continue

                # Clean the description using BeautifulSoup
                soup = BeautifulSoup(raw_description, 'html.parser')
                keep_tags = []
                for tag in soup.find_all(['p', 'pre', 'ul', 'ol', 'li', 'code', 'strong', 'em']):
                    keep_tags.append(str(tag))
                clean_description = "\n".join(keep_tags)

                if not title:
                    fallback = url.split('/')[-1]
                    slug = slugify(fallback)
                    title = fallback.replace('-', ' ').title()
                else:
                    slug = slugify(title)

                if not slug:
                    skipped += 1
                    continue

                if slug in seen_slugs:
                    slug = f"{slug}-{count}"

                seen_slugs.add(slug)

                PracticeProblem.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'title': title,
                        'difficulty': row.get('difficulty', 'Unknown').strip(),
                        'companies': row.get('companies', '').strip(),
                        'url': url,
                        'statement': clean_description,
                    }
                )
                count += 1

        print(f"✅ Imported {count} practice problems, skipped {skipped} bad rows.")
