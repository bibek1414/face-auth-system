from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import base64
import uuid
import datetime
from django.utils import timezone

def generate_key_pair():
    """Generate RSA key pair and return as PEM strings"""
    key = RSA.generate(2048)
    private_key = key.export_key().decode('utf-8')
    public_key = key.publickey().export_key().decode('utf-8')
    return public_key, private_key

def sign_data(private_key_pem, data):
    """Sign data using private key"""
    try:
        # Import the private key
        key = RSA.import_key(private_key_pem)
        
        # Create hash of the data
        h = SHA256.new(data.encode('utf-8'))
        
        # Sign the hash
        signature = pkcs1_15.new(key).sign(h)
        
        # Return base64 encoded signature
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        print(f"Error signing data: {str(e)}")
        return None

def verify_signature(public_key_pem, data, signature):
    """Verify signature using public key"""
    try:
        # Decode the signature from base64
        signature_bytes = base64.b64decode(signature)
        
        # Import the public key
        key = RSA.import_key(public_key_pem)
        
        # Create hash of the data
        h = SHA256.new(data.encode('utf-8'))
        
        # Verify the signature
        pkcs1_15.new(key).verify(h, signature_bytes)
        return True
    except Exception as e:
        print(f"Signature verification failed: {str(e)}")
        return False

def generate_login_token(user):
    """Generate a unique token for login"""
    return str(uuid.uuid4())

def create_login_challenge(user):
    """Create a login challenge with expiration time"""
    token = generate_login_token(user)
    expires_at = timezone.now() + datetime.timedelta(minutes=5)
    return token, expires_at

def sign_login_challenge(user_profile, token):
    """Sign the login challenge with user's private key"""
    if not user_profile.private_key:
        return None
    
    signature = sign_data(user_profile.private_key, token)
    return signature

def verify_login_signature(user_profile, token, signature):
    """Verify the login signature with user's public key"""
    if not user_profile.public_key or not signature:
        return False
    
    return verify_signature(user_profile.public_key, token, signature)