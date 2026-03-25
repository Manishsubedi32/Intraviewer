# 🧠 Intraviewer Backend - AI Mock Interview API

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Model](https://img.shields.io/badge/LLM-Phi--3%20Mini-blue?style=flat)](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct)
[![Speech](https://img.shields.io/badge/ASR-Faster--Whisper-orange?style=flat)](https://github.com/SYSTRAN/faster-whisper)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The backend service for **Intraviewer**, an intelligent mock interview platform. This API handles real-time audio/video processing, emotion recognition, speech-to-text transcription, and AI-driven question generation using local LLMs.

---

## 🌟 Key Features

- **🔥 Fast API:** High-performance async endpoints built with FastAPI.
- **🎙️ Real-Time Transcription:** Integrated `faster-whisper` for low-latency speech-to-text.
- **🎭 Emotion Analysis:** Real-time facial expression recognition using RAF-DB trained CNN models.
- **🧠 AI Question Generation:** Generates contextual interview questions based on CV and Job Description using **Phi-3 Mini** (run locally via `llama-cpp`).
- **⚡ WebSocket Streaming:** Bi-directional streaming for live audio/video processing.
- **💡 Interview Tips:** Extracts and serves random interview hacks from PDF resources.
- **🔐 Secure Auth:** JWT-based authentication and secure session management.
- **📦 Database:** PostgreSQL with SQLAlchemy ORM for robust data persistence.

---

## 📸 Prototype

<p align="center">
  <img src="images/Screenshot%202026-02-26%20at%2012.06.53%20AM.png" alt="Dashboard" width="45%">
  <img src="images/Screenshot%202026-02-26%20at%2012.07.13%20AM.png" alt="Interview" width="45%">
</p>
<p align="center">
  <img src="images/Screenshot%202026-02-26%20at%2012.09.59%20AM.png" alt="Feedback" width="45%">
  <img src="images/Screenshot%202026-03-25%20at%203.57.03%E2%80%AFPM.png" alt="Analysis" width="45%">
</p>

---

## 🛠️ Tech Stack

- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL, SQLAlchemy
- **ML/AI:**
  - **LLM:** Phi-3 Mini (GGUF format via `llama-cpp-python`)
  - **ASR:** Faster-Whisper
  - **Vision:** TensorFlow/Keras (CNN) & OpenCV
- **Utilities:** PyPDF, NumPy, Pandas

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** installed.
- **PostgreSQL** installed and running.
- **FFmpeg** installed (required for audio processing).
  - _Mac:_ `brew install ffmpeg`
  - _Linux:_ `sudo apt install ffmpeg`
  - _Windows:_ [Download & Add to Path](https://ffmpeg.org/download.html)

### 1. Clone the Repository

```bash
git clone https://github.com/Manishsubedi32/intraviewer-backend.git
cd intraviewer-backend
```

### 2. Create a Virtual Environment

It's recommended to use a virtual environment to manage dependencies.

```bash
# Mac/Linux
python3 -m venv env
source env/bin/activate

# Windows
python -m venv env
.\env\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configuration

Create a `.env` file in the root directory:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/intraviewer_db
DB_USERNAME=user
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=intraviewer_db

# JWT Secret
SECRET_KEY=your_super_secret_key_here
ALGORITHM=HS256

# Optional: Model Paths (if custom)
WHISPER_MODEL_SIZE=base
```

### 5. Download Models

Ensure the necessary model files are present in the `backend/` root or specified paths:

- `best_model.h5` (For emotion recognition)
- `100_hacks.pdf` (For interview tips)
- LLM models will be downloaded automatically by `llama-cpp` on first run/install.

### 6. Run the Server

```bash
# Development mode with auto-reload
uvicorn src.main:app --reload
```

The API will be available at: **http://127.0.0.1:8000**

---

## 📚 API Documentation

Once the server is running, you can access the interactive API docs:

- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📂 Project Structure

```
backend/
├── src/
│   ├── core/           # Config and Security (Auth)
│   ├── db/             # Database connection and session
│   ├── models/         # SQLAlchemy Database Models
│   ├── routers/        # API Endpoints (Auth, Users, Questions, etc.)
│   ├── schemas/        # Pydantic Schemas for Request/Response
│   ├── services/       # Business Logic (AI, Auth, Sessions)
│   ├── utils/          # Helper functions
│   └── main.py         # App Entry Point
├── best_model.h5       # Emotion Recognition Model
├── 100_hacks.pdf       # Source for interview tips
├── requirements.txt
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository and create a pull request.

## 📄 License

This project is licensed under the MIT License.
