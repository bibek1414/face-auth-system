// webcam.js - Handles webcam access and face capture for authentication
let videoElement = null;
let canvas = null;
let stream = null;
let captureButton = null;
let retakeButton = null;
let faceDataInput = null;
let previewImage = null;
let videoContainer = null;
let captureContainer = null;
let faceFeedback = null;

// Initialize the webcam capture UI
function initWebcam(containerId, inputId, previewId, captureId, retakeId, feedbackId = null) {
    videoContainer = document.getElementById(containerId);
    faceDataInput = document.getElementById(inputId);
    previewImage = document.getElementById(previewId);
    captureButton = document.getElementById(captureId);
    retakeButton = document.getElementById(retakeId);
    
    if (feedbackId) {
        faceFeedback = document.getElementById(feedbackId);
    }

    if (!videoContainer || !faceDataInput || !previewImage || !captureButton || !retakeButton) {
        console.error('Missing required elements for webcam functionality');
        return;
    }

    // Create video element
    videoElement = document.createElement('video');
    videoElement.setAttribute('playsinline', '');
    videoElement.setAttribute('autoplay', '');
    videoElement.className = 'webcam-video';
    videoContainer.appendChild(videoElement);

    // Create canvas element (for capturing images)
    canvas = document.createElement('canvas');
    canvas.style.display = 'none';
    document.body.appendChild(canvas);

    // Show video container, hide capture container
    videoContainer.style.display = 'block';
    previewImage.parentElement.style.display = 'none';

    // Set up event listeners
    captureButton.addEventListener('click', captureFace);
    retakeButton.addEventListener('click', restartCamera);

    // Start camera
    startCamera();
}

// Start the webcam
function startCamera() {
    // Request permission to use camera
    navigator.mediaDevices.getUserMedia({ 
        video: { 
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: 'user'
        }, 
        audio: false 
    })
    .then(function(mediaStream) {
        stream = mediaStream;
        videoElement.srcObject = mediaStream;
        videoElement.play();
    })
    .catch(function(err) {
        console.error('Error accessing webcam:', err);
        if (faceFeedback) {
            faceFeedback.innerHTML = 'Error accessing webcam. Please ensure camera permissions are enabled.';
            faceFeedback.style.display = 'block';
            faceFeedback.className = 'alert alert-danger';
        }
    });
}

// Stop the webcam stream
function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
}

// Capture face from webcam
function captureFace() {
    if (!videoElement || !canvas) return;

    // Set canvas dimensions to match video
    canvas.width = videoElement.videoWidth;
    canvas.height = videoElement.videoHeight;
    
    // Draw the current video frame to canvas
    const context = canvas.getContext('2d');
    context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
    
    // Convert canvas to base64 data URL
    const imageData = canvas.toDataURL('image/jpeg');
    
    // Stop the camera
    stopCamera();
    
    // Hide video, show preview
    videoContainer.style.display = 'none';
    previewImage.src = imageData;
    previewImage.parentElement.style.display = 'block';
    
    // Store the image data in the hidden input
    if (faceDataInput) {
        faceDataInput.value = imageData;
    }
}

// Restart the camera to retake photo
function restartCamera() {
    // Clear the preview and form data
    previewImage.src = '';
    faceDataInput.value = '';
    
    // Hide preview, show video
    previewImage.parentElement.style.display = 'none';
    videoContainer.style.display = 'block';
    
    // Start the camera again
    startCamera();
}

// Verify face without submitting the form (AJAX)
function verifyFace(username) {
    if (!faceDataInput || !faceDataInput.value) {
        if (faceFeedback) {
            faceFeedback.innerHTML = 'Please capture your face first.';
            faceFeedback.style.display = 'block';
            faceFeedback.className = 'alert alert-warning';
        }
        return;
    }

    if (faceFeedback) {
        faceFeedback.innerHTML = 'Verifying...';
        faceFeedback.style.display = 'block';
        faceFeedback.className = 'alert alert-info';
    }

    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Send request to verify face
    fetch('/auth/verify-face/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            username: username,
            face_data: faceDataInput.value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (faceFeedback) {
                faceFeedback.innerHTML = `Face verified successfully! Confidence: ${data.score}%`;
                faceFeedback.className = 'alert alert-success';
            }
            return true;
        } else {
            if (faceFeedback) {
                faceFeedback.innerHTML = `Verification failed: ${data.error || 'Face not recognized'} ${data.score ? `(Score: ${data.score}%)` : ''}`;
                faceFeedback.className = 'alert alert-danger';
            }
            return false;
        }
    })
    .catch(error => {
        console.error('Error verifying face:', error);
        if (faceFeedback) {
            faceFeedback.innerHTML = 'Error communicating with server. Please try again.';
            faceFeedback.className = 'alert alert-danger';
        }
        return false;
    });
}

// Clean up when page is unloaded
window.addEventListener('beforeunload', function() {
    stopCamera();
});