from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify, send_file
import os
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
from dotenv import load_dotenv
import cv2
import numpy as np
import face_recognition
import requests
import io
from datetime import datetime
import threading

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

# Global variables
known_face_encodings = []
known_face_names = []
todays_attendance = [] # List of {'name': 'Name', 'time': 'HH:MM:SS'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_to_cloud(content, public_id):
    """Uploads content (string/bytes) to Cloudinary in a separate thread."""
    try:
        # resource_type='raw' is used for non-image files like CSV
        # convert string to bytes if needed
        if isinstance(content, str):
            content = content.encode('utf-8')
            
        cloudinary.uploader.upload(content, resource_type="raw", public_id=public_id, overwrite=True, invalidate=True)
        print(f"Synced to Cloudinary: {public_id}")
    except Exception as e:
        print(f"Cloud upload failed: {e}")

def load_todays_data():
    """Fetch today's attendance CSV from Cloudinary to populate memory."""
    global todays_attendance
    todays_attendance = []
    
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    public_id = f"attendance_records/Attendance_{date_str}.csv"
    
    print("Checking for existing daily records in cloud...")
    try:
        # Generate the URL for the raw file
        url, options = cloudinary.utils.cloudinary_url(public_id, resource_type="raw")
        
        # Try to fetch it
        response = requests.get(url)
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            # Skip header
            for line in lines[1:]:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    todays_attendance.append({'name': parts[0], 'time': parts[1]})
            print(f"Loaded {len(todays_attendance)} records from cloud for today.")
        else:
            print("No existing records for today found (New Day).")
            
    except Exception as e:
        print(f"Error loading today's data: {e}")

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

import smtplib
from email.message import EmailMessage

# ... (rest of imports)

def send_email(name, time_str):
    """Sends an email notification on first daily check-in."""
    sender_email = os.getenv('MAIL_USERNAME')
    sender_password = os.getenv('MAIL_PASSWORD')
    recipient_email = os.getenv('MAIL_RECIPIENT')

    if not sender_email or not sender_password or not recipient_email:
        print("Email credentials missing in .env. Skipping notification.")
        return

    msg = EmailMessage()
    msg['Subject'] = f"Attendance Alert: {name} Checked In"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    content = f"""
    Hello,
    
    This is an automatic notification from the Attendance System to notify you that {name} has checked in..
    
    User: {name}
    Time: {time_str}
    Date: {datetime.now().strftime('%Y-%m-%d')}
    
    Status: PRESENT
    """
    msg.set_content(content)

    try:
        # Connect to Gmail SMTP (SSL)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
            print(f"Email notification sent for {name}.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def mark_attendance(name):
    """Mark attendance in memory and sync to cloud."""
    global todays_attendance
    
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S')
    
    # Check if user already exists
    found = False
    
    for entry in todays_attendance:
        if entry['name'] == name:
            entry['time'] = time_str # Update time
            found = True
            print(f"Updated memory for {name} at {time_str}")
            break
            
    if not found:
        todays_attendance.append({'name': name, 'time': time_str})
        print(f"Added to memory: {name} at {time_str}")
        
        # Trigger Email Notification (Threaded to not block UI)
        threading.Thread(target=send_email, args=(name, time_str)).start()

    # Generate CSV Content
    csv_lines = ['Name,Time']
    for entry in todays_attendance:
        csv_lines.append(f"{entry['name']},{entry['time']}")
    
    csv_content = '\n'.join(csv_lines)
    
    # Sync to Cloudinary
    public_id = f"attendance_records/Attendance_{date_str}.csv"
    threading.Thread(target=upload_to_cloud, args=(csv_content, public_id)).start()

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

@app.route('/reports')
def reports():
    return render_template('reports.html')

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
            load_known_faces()
            
            flash(f'Successfully registered {name}! (Saved to Cloudinary)', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'error')
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a PNG or JPG.', 'error')
        return redirect(url_for('index'))

@app.route('/get_attendance', methods=['POST'])
def get_attendance():
    date_str = request.form.get('date')
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    if not date_str:
        return jsonify({'error': 'Date is required'}), 400
    
    # If today, return memory data
    if date_str == today_str:
        return jsonify({'count': len(todays_attendance), 'data': todays_attendance})
    
    # If past date, fetch from Cloudinary
    public_id = f"attendance_records/Attendance_{date_str}.csv"
    try:
        url, options = cloudinary.utils.cloudinary_url(public_id, resource_type="raw")
        response = requests.get(url)
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            data = []
            for line in lines[1:]:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    data.append({'name': parts[0], 'time': parts[1]})
            return jsonify({'count': len(data), 'data': data})
        else:
            return jsonify({'count': 0, 'data': []})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_attendance/<date_str>')
def download_attendance(date_str):
    # For download, we can just redirect to the Cloudinary URL
    # This is efficient and handles file generation for us
    public_id = f"attendance_records/Attendance_{date_str}.csv"
    url, options = cloudinary.utils.cloudinary_url(public_id, resource_type="raw")
    return redirect(url)

if __name__ == '__main__':
    # Load data on startup
    load_todays_data()
    load_known_faces()
    app.run(debug=True, port=5000)
