# Face Recognition Attendance System

A smart, cloud-integrated attendance monitoring system using **Face Recognition** and **Flask**.

Web App preview - [Attendance System](https://attendance-system-012.up.railway.app) 

## 🚀 Features

-   **Real-time Recognition**: Instantly identifies registered users via webcam.
-   **Unified Dashboard**: Single web interface for both **User Registration** and **Live Attendance**.
-   **Cloud Integration**:
    -   User photos are stored safely in **Cloudinary** (`attendance/` folder).
    -   Daily attendance CSV logs are auto-synced to Cloudinary (`attendance_records/`).
-   **Dual Registration**: Add users by uploading a file or capturing a photo directly from the browser.
-   **Daily Logging**: Automatically generates unique CSV files for each day (e.g., `Attendance_2024-03-15.csv`).
-   **Reports & Export**: View synthesized daily reports and download CSVs via a dedicated dashboard page.
-   **Email Alerts**: Sends an automated email notification the first time a user checks in each day.

## 🛠️ Tech Stack

-   **Backend**: Python, Flask
-   **AI/CV**: OpenCV, face_recognition
-   **Cloud**: Cloudinary API
-   **Frontend**: HTML5, CSS3 (Glassmorphism), JavaScript

## 📋 Prerequisites

-   Python 3.8+
-   A free [Cloudinary](https://cloudinary.com/) account.
-   **C++ Build Tools** (Required for `dlib` on Windows):
    -   Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with "Desktop development with C++" workload.

## ⚙️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/Face-Recognition-Based-Attendance-Monitoring-System.git
    cd Face-Recognition-Based-Attendance-Monitoring-System
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**:
    Create a file named `.env` in the root directory and add your Cloudinary credentials:
    ```env
    CLOUDINARY_CLOUD_NAME=your_cloud_name
    CLOUDINARY_API_KEY=your_api_key
    CLOUDINARY_API_SECRET=your_api_secret
    ```

## 🖥️ Usage

1.  **Start the Application**:
    ```bash
    python app.py
    ```

2.  **Open Dashboard**:
    Go to `http://127.0.0.1:5000` in your browser.

3.  **Register Users (Left Panel)**:
    -   **Upload**: Drag & drop a photo and enter a name.
    -   **Camera**: Use the "Use Camera" tab to snap a photo instantly.
    -   *Images are auto-uploaded to Cloudinary.*

4.  **Take Attendance (Right Panel)**:
    -   Click **"Start Attendance"** to enable the webcam.
    -   The system will scan for faces and log them in `Attendance_{Date}.csv`.
    -   Every new entry triggers an automatic **background sync** to Cloudinary.
    -   Click **"Stop Attendance"** when done.

## 📂 Project Structure

```
├── app.py              # Main Flask application & Business Logic
├── templates/
│   └── index.html      # Unified Dashboard UI
├── requirements.txt    # Python dependencies
├── .env                # API Keys (Excluded from Git)
├── .gitignore          # Git ignore rules
└── Attendance_*.csv    # Daily generated attendance logs
```

## 🔒 Security Note

-   Ensure `.env` is added to your `.gitignore` file (already configured) to prevent leaking API keys.

---
*Built for the Advanced Agentic Coding Project.*
