from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    face_image = forms.ImageField(required=False, help_text="Upload your face image for registration")
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class CustomAuthenticationForm(AuthenticationForm):
    face_image = forms.ImageField(required=False, help_text="Capture your face for authentication")
    
    class Meta:
        model = User
        fields = ("username", "password")

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['face_image']
        widgets = {
            'face_image': forms.ClearableFileInput(attrs={'class': 'hidden'})
        }