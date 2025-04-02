from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
from .crypto_utils import generate_key_pair

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Generate RSA key pair for the new user
        public_key, private_key = generate_key_pair()
        
        # Create user profile with keys
        UserProfile.objects.create(
            user=instance,
            public_key=public_key,
            private_key=private_key
        )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()