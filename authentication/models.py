from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    face_encoding = models.BinaryField(null=True, blank=True)
    face_image = models.ImageField(upload_to='face_data/', null=True, blank=True)
    public_key = models.TextField(null=True, blank=True)
    private_key = models.TextField(null=True, blank=True)  # In production, consider a more secure storage method
    login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_face_encoding_path(self):
        if not self.face_encoding:
            return None
        
        # Create a unique filename based on user ID but keep it consistent for the same user
        filename = f"user_{self.user.id}_face_encoding.pkl"
        filepath = os.path.join(settings.FACE_DATA_DIR, filename)
        return filepath

class LoginLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    face_match_score = models.FloatField(null=True, blank=True)
    signature_verified = models.BooleanField(null=True, blank=True)
    
    def __str__(self):
        status = "Success" if self.successful else "Failed"
        return f"{status} login for {self.user.username} at {self.timestamp}"

class DigitalSignature(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='signatures')
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    signature = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Signature for {self.user.username} ({self.token})"
    
    class Meta:
        ordering = ['-created_at']