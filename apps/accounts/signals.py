from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Superusers automatically get the admin role
        role = 'admin' if instance.is_superuser else 'user'
        UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
