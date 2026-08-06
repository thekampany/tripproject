from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile
from django.db.models.signals import post_delete
from .models import DayProgram

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()


@receiver(post_delete, sender=DayProgram)
def delete_map_image_file(sender, instance, **kwargs):
    if instance.map_image:
        instance.map_image.delete(save=False)