# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from core.models import PracticeSubmission, UserTopicProgress

# @receiver(post_save, sender=PracticeSubmission)
# def update_user_problem_stats(sender, instance, created, **kwargs):
#     if created:
#         topic = instance.problem.topic
#         progress, _ = UserTopicProgress.objects.get_or_create(user=instance.user, topic=topic)
#         if instance.problem.difficulty == 'Easy':
#             progress.easy_solved += 1
#         elif instance.problem.difficulty == 'Medium':
#             progress.medium_solved += 1
#         elif instance.problem.difficulty == 'Hard':
#             progress.hard_solved += 1
#         progress.save()