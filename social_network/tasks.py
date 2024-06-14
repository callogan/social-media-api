from datetime import datetime

from django.db.models import Q

from social_network.models import Post

from celery import shared_task


@shared_task
def count_posts() -> int:
    return Post.objects.count()


@shared_task
def publish_posts() -> None:
    posts = Post.objects.filter(
        Q(publish_time__lte=datetime.now()) & Q(published=False)
    )
    for post in posts:
        post.published = True
        post.save()
