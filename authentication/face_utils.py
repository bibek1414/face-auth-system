import face_recognition
import numpy as np
import pickle
import os
import cv2
from django.conf import settings
from io import BytesIO
from PIL import Image

def process_face_image(image_file):
    """Process uploaded image file and extract face encoding"""
    try:
        # Read the image file
        image = face_recognition.load_image_file(image_file)
        
        # Find faces in the image
        face_locations = face_recognition.face_locations(image)
        
        if not face_locations:
            return None, "No face detected in the image. Please try again."
            
        if len(face_locations) > 1:
            return None, "Multiple faces detected. Please upload an image with only your face."
        
        # Get the encoding of the first face
        face_encoding = face_recognition.face_encodings(image, face_locations)[0]
        
        # Convert numpy array to bytes for storage
        encoding_bytes = pickle.dumps(face_encoding)
        
        return encoding_bytes, None
    except Exception as e:
        return None, f"Error processing face image: {str(e)}"

def compare_faces(known_encoding_bytes, image_file, tolerance=None):
    """Compare face in uploaded image with stored encoding"""
    if tolerance is None:
        tolerance = getattr(settings, 'FACE_RECOGNITION_TOLERANCE', 0.6)
        
    try:
        # Load the known face encoding
        known_face_encoding = pickle.loads(known_encoding_bytes)
        
        # Load the image to check
        image = face_recognition.load_image_file(image_file)
        
        # Find faces in the image
        face_locations = face_recognition.face_locations(image)
        
        if not face_locations:
            return False, 0.0, "No face detected in the provided image."
            
        # Get the encoding of the face
        face_encoding = face_recognition.face_encodings(image, face_locations)[0]
        
        # Compare the faces
        face_distances = face_recognition.face_distance([known_face_encoding], face_encoding)
        match_score = 1 - float(face_distances[0])
        match = face_distances[0] <= tolerance
        
        if match:
            return True, match_score, None
        else:
            return False, match_score, "Face does not match the registered user."
            
    except Exception as e:
        return False, 0.0, f"Error comparing faces: {str(e)}"

def save_face_encoding(user_profile, encoding_bytes):
    """Save face encoding to file"""
    filepath = user_profile.get_face_encoding_path()
    
    if not filepath:
        return False
    
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(encoding_bytes)
        return True
    except Exception:
        return False

def load_face_encoding(user_profile):
    """Load face encoding from file"""
    filepath = user_profile.get_face_encoding_path()
    
    if not filepath or not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'rb') as f:
            encoding_bytes = f.read()
        return encoding_bytes
    except Exception:
        return None