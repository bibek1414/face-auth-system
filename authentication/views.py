from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from datetime import timedelta
import json
import base64
import logging

from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm
from .models import UserProfile, LoginLog, DigitalSignature
from .face_utils import process_face_image, compare_faces
from .crypto_utils import create_login_challenge, sign_login_challenge, verify_login_signature , generate_key_pair
logger = logging.getLogger(__name__)
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            # Generate key pair for the new user
            try:
                public_key, private_key = generate_key_pair()
                
                # Get or create profile
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.public_key = public_key
                profile.private_key = private_key
                profile.save()
            except Exception as e:
                logger.error(f"Key generation failed during registration: {str(e)}")
                messages.warning(request, "Account created but security features could not be initialized.")
            
            # Process face image if provided
            if 'face_data' in request.POST and request.POST['face_data']:
                try:
                    # Process base64 data from webcam
                    face_data = request.POST['face_data']
                    format, imgstr = face_data.split(';base64,')
                    face_image = base64.b64decode(imgstr)
                    
                    # Create a BytesIO object
                    from io import BytesIO
                    import tempfile
                    from PIL import Image
                    
                    img = Image.open(BytesIO(face_image))
                    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                    img.save(temp_file.name)
                    
                    # Process the face image
                    encoding_bytes, error = process_face_image(temp_file.name)
                    
                    if error:
                        messages.error(request, error)
                    else:
                        # Save the face encoding
                        user_profile = user.profile
                        user_profile.face_encoding = encoding_bytes
                        user_profile.save()
                        messages.success(request, "Face registered successfully!")
                    
                    # Clean up the temp file
                    import os
                    os.unlink(temp_file.name)
                    
                except Exception as e:
                    messages.error(request, f"Error processing face image: {str(e)}")
            
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('authentication:dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'authentication/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('authentication:dashboard')
        
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        
        username = request.POST.get('username')
        password = request.POST.get('password')
        face_data = request.POST.get('face_data')
        
        # Basic validation
        if not username or not password:
            messages.error(request, "Please provide username and password.")
            return render(request, 'authentication/login.html', {'form': form})
        
        # Get user
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "Invalid username or password.")
            return render(request, 'authentication/login.html', {'form': form})
        
        # Check if profile exists and create if it doesn't
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)
            messages.info(request, "User profile was created.")
        
        # Check if account is locked
        if profile.is_locked:
            lockout_time = settings.LOCKOUT_TIME_MINUTES
            if profile.last_failed_login and timezone.now() < profile.last_failed_login + timedelta(minutes=lockout_time):
                remaining_time = (profile.last_failed_login + timedelta(minutes=lockout_time) - timezone.now())
                minutes = int(remaining_time.total_seconds() // 60)
                messages.error(request, f"Account is locked due to multiple failed attempts. Try again in {minutes} minutes.")
                return render(request, 'authentication/login.html', {'form': form})
            else:
                # Reset lockout
                profile.is_locked = False
                profile.login_attempts = 0
                profile.save()
        
        # Check password
        user = authenticate(username=username, password=password)
        if not user:
            # Record failed login
            profile.login_attempts += 1
            profile.last_failed_login = timezone.now()
            
            if profile.login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                profile.is_locked = True
                messages.error(request, "Account locked due to multiple failed login attempts.")
            else:
                messages.error(request, "Invalid username or password.")
                
            profile.save()
            
            LoginLog.objects.create(
                user_id=User.objects.get(username=username).id,
                successful=False,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return render(request, 'authentication/login.html', {'form': form})
        
        # Face recognition if required
        score = None
        if profile.face_encoding:
            if not face_data:
                messages.error(request, "Face verification required. Please allow camera access.")
                return render(request, 'authentication/login.html', {'form': form})
            
            try:
                # Process the face data
                format, imgstr = face_data.split(';base64,')
                face_image = base64.b64decode(imgstr)
                
                from io import BytesIO
                import tempfile
                from PIL import Image
                
                img = Image.open(BytesIO(face_image))
                temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                img.save(temp_file.name)
                
                # Compare faces
                match, score, error = compare_faces(profile.face_encoding, temp_file.name)
                
                import os
                os.unlink(temp_file.name)
                
                if error:
                    messages.error(request, error)
                    return render(request, 'authentication/login.html', {'form': form})
                
                if not match:
                    profile.login_attempts += 1
                    profile.last_failed_login = timezone.now()
                    
                    if profile.login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                        profile.is_locked = True
                        messages.error(request, "Account locked due to multiple failed login attempts.")
                    else:
                        messages.error(request, "Face verification failed. Please try again.")
                        
                    profile.save()
                    
                    LoginLog.objects.create(
                        user=user,
                        successful=False,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        face_match_score=score
                    )
                    
                    return render(request, 'authentication/login.html', {'form': form})
            
            except Exception as e:
                logger.error(f"Face verification error: {str(e)}")
                messages.error(request, f"Error during face verification: {str(e)}")
                return render(request, 'authentication/login.html', {'form': form})
        
        # Check if the user has keys, generate if not
        if not profile.public_key or not profile.private_key:
            try:
                # Generate new key pair
                public_key, private_key = generate_key_pair()
                
                # Save keys to profile
                profile.public_key = public_key
                profile.private_key = private_key
                profile.save()
                
                logger.info(f"Generated new key pair for user {user.username}")
            except Exception as e:
                logger.error(f"Key generation failed: {str(e)}")
                messages.error(request, "Error setting up security credentials. Please contact support.")
                return render(request, 'authentication/login.html', {'form': form})
        
        # Digital signature creation with error handling
        try:
            token, expires_at = create_login_challenge(user)
            signature = sign_login_challenge(profile, token)
            
            if not signature:
                raise ValueError("Failed to generate digital signature")
            
            DigitalSignature.objects.create(
                user=user,
                token=token,
                signature=signature,  # Corrected parameter name
                expires_at=expires_at
            )
        except Exception as e:
            logger.error(f"Digital signature creation failed: {str(e)}")
            messages.error(request, "Error during login process. Please try again.")
            return render(request, 'authentication/login.html', {'form': form})
        
        # Reset login attempts on successful login
        profile.login_attempts = 0
        profile.is_locked = False
        profile.save()
        
        # Log the successful login
        LoginLog.objects.create(
            user=user,
            successful=True,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            face_match_score=score if score is not None else None,
            signature_verified=True
        )
        
        login(request, user)
        messages.success(request, "Login successful!")
        return redirect('authentication:dashboard')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'authentication/login.html', {'form': form})
@login_required
def dashboard_view(request):
    # Ensure user has a profile
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    # Get recent login history
    login_logs = LoginLog.objects.filter(user=request.user).order_by('-timestamp')[:5]
    
    context = {
        'user': request.user,
        'login_logs': login_logs,
        'has_face_data': bool(profile.face_encoding)
    }
    
    return render(request, 'authentication/dashboard.html', context)

@login_required
def profile_view(request):
    # Ensure user has a profile
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        
        if 'face_data' in request.POST and request.POST['face_data']:
            try:
                # Process base64 data from webcam
                face_data = request.POST['face_data']
                format, imgstr = face_data.split(';base64,')
                face_image = base64.b64decode(imgstr)
                
                # Create a BytesIO object
                from io import BytesIO
                import tempfile
                from PIL import Image
                img = Image.open(BytesIO(face_image))
                temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                img.save(temp_file.name)
                
                # Process the face image
                encoding_bytes, error = process_face_image(temp_file.name)
                
                if error:
                    messages.error(request, error)
                else:
                    # Save the face encoding
                    profile.face_encoding = encoding_bytes
                    profile.save()
                    messages.success(request, "Face updated successfully!")
                
                # Clean up the temp file
                import os
                os.unlink(temp_file.name)
                
            except Exception as e:
                messages.error(request, f"Error processing face image: {str(e)}")
        
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('authentication:profile')
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'form': form,
        'has_face_data': bool(profile.face_encoding)
    }
    return render(request, 'authentication/profile.html', context)

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('authentication:login')

@require_POST
def verify_face_view(request):
    """AJAX endpoint to verify face without completing login"""
    
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        face_data = data.get('face_data')
        
        if not username or not face_data:
            return JsonResponse({'success': False, 'error': 'Missing required data'})
        
        # Get user
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
            
        # Get or create profile
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)
        
        if not profile.face_encoding:
            return JsonResponse({'success': False, 'error': 'No face data registered for this user'})
        
        # Process the face data
        format, imgstr = face_data.split(';base64,')
        face_image = base64.b64decode(imgstr)
        
        # Create a temp file
        from io import BytesIO
        import tempfile
        from PIL import Image
        
        img = Image.open(BytesIO(face_image))
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        img.save(temp_file.name)
        
        # Compare faces
        match, score, error = compare_faces(profile.face_encoding, temp_file.name)
        
        # Clean up the temp file
        import os
        os.unlink(temp_file.name)
        
        if error:
            return JsonResponse({'success': False, 'error': error})
        
        if match:
            return JsonResponse({'success': True, 'score': round(score * 100, 2)})
        else:
            return JsonResponse({'success': False, 'error': 'Face verification failed', 'score': round(score * 100, 2)})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Error: {str(e)}"})

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip