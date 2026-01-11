from flask import Flask, render_template, request, redirect, url_for, flash, Response
import os
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
import cv2
import numpy as np
import face_recognition
import requests
import io
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# Configure Cloudinary
cloudinary.config( 
  cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'), 
  api_key = os.getenv('CLOUDINARY_API_KEY'), 
  api_secret = os.getenv('CLOUDINARY_API_SECRET') 
)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ATTENDANCE_FILE = 'attendance.csv'

# Global variables for face recognition
known_face_encodings = []
known_face_names = []

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_known_faces():
    """Load images from Cloudinary and encode faces."""
    global known_face_encodings, known_face_names
    known_face_encodings = []
    known_face_names = []
    
    print("Connecting to Cloudinary...")
    try:
        response = cloudinary.api.resources(type="upload", prefix="attendance/", max_results=500)
        resources = response.get('resources', [])
        
        if not resources:
            print("No images found in Cloudinary 'attendance' folder.")
            return

        print(f"Found {len(resources)} images in 'attendance' folder. Processing...")
        
        for res in resources:
            if res['format'] in ['jpg', 'png', 'jpeg']:
                try:
                    image_url = res['secure_url']
                    full_public_id = res['public_id']
                    name = os.path.basename(full_public_id)
                    
                    response = requests.get(image_url)
                    image_bytes = response.content
                    image_file = io.BytesIO(image_bytes)
                    image = face_recognition.load_image_file(image_file)
                    
                    encodings = face_recognition.face_encodings(image)
                    if encodings:
                        known_face_encodings.append(encodings[0])
                        known_face_names.append(name)
                        print(f"Loaded: {name}")
                except Exception as e:
                    print(f"Error processing {name}: {e}")
                    
    except Exception as e:
        print(f"Failed to connect to Cloudinary: {e}")

def mark_attendance(name):
    """Mark attendance in CSV file."""
    if not os.path.isfile(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, 'w') as f:
            f.writelines('Name,Date,Time')

    with open(ATTENDANCE_FILE, 'r+') as f:
        myDataList = f.readlines()
        nameList = []
        for line in myDataList:
            entry = line.split(',')
            nameList.append(entry[0])
            
        if name not in nameList:
            now = datetime.now()
            dtString = now.strftime('%Y-%m-%d,%H:%M:%S')
            f.writelines(f'\n{name},{dtString}')
            print(f"Attendance marked for {name}")

def gen_frames():
    """Generate frames for video streaming with face recognition."""
    cap = cv2.VideoCapture(0)
    try:
        while True:
            success, img = cap.read()
            if not success:
                break
            else:
                imgS = cv2.resize(img, (0, 0), fx=0.25, fy=0.25)
                imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

                facesCurFrame = face_recognition.face_locations(imgS)
                encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

                for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
                    matches = face_recognition.compare_faces(known_face_encodings, encodeFace)
                    faceDis = face_recognition.face_distance(known_face_encodings, encodeFace)
                    
                    matchIndex = np.argmin(faceDis)
                    
                    if matches[matchIndex]:
                        name = known_face_names[matchIndex].upper()
                        
                        y1, x2, y2, x1 = faceLoc
                        y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                        cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                        
                        mark_attendance(name)

                ret, buffer = cv2.imencode('.jpg', img)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        cap.release()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    name = request.form.get('name')

    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))
    
    if not name:
        flash('Please enter a name', 'error')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        try:
            # Upload to Cloudinary with a folder prefix
            upload_result = cloudinary.uploader.upload(file, public_id=f"attendance/{name}")
            
            # Reload faces to include the new user immediately
            # Optimization: could just append to global list, but this is safer
            load_known_faces()
            
            flash(f'Successfully registered {name}! (Saved to Cloudinary)', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'error')
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a PNG or JPG.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Load faces before starting server
    load_known_faces()
    app.run(debug=True, port=5000)
