
from django.contrib import admin
from .models import UserProfile, LoginLog, DigitalSignature

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'has_face_data', 'has_keys', 'login_attempts', 'is_locked')
    search_fields = ('user__username', 'user__email')
    list_filter = ('is_locked',)
    
    def has_face_data(self, obj):
        return bool(obj.face_encoding)
    has_face_data.boolean = True
    
    def has_keys(self, obj):
        return bool(obj.public_key and obj.private_key)
    has_keys.boolean = True

@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'timestamp', 'successful', 'ip_address', 'face_match_score')
    list_filter = ('successful', 'timestamp')
    search_fields = ('user__username', 'ip_address')
    date_hierarchy = 'timestamp'

@admin.register(DigitalSignature)
class DigitalSignatureAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'expires_at', 'used')
    list_filter = ('used', 'created_at')
    search_fields = ('user__username',)
    readonly_fields = ('token', 'created_at')