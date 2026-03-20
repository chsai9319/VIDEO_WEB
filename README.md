# 🎬 MyVault — Personal Video Studio

A self-hosted personal video platform built with **Flask** + **Python**.  
Upload, organize, stream, and download your videos from any browser.

---

## 📁 Project Structure

```
myvault/
├── app.py               # Flask backend (REST API + video streaming)
├── templates/
│   └── index.html       # Frontend UI
├── static/              # (optional) CSS/JS assets
├── uploads/             # Video storage (auto-created, gitignored)
├── requirements.txt     # Python dependencies
├── Dockerfile           # Multi-stage Docker image
├── docker-compose.yml   # One-command orchestration
└── .dockerignore
```

---

## 🚀 Quick Start

### Option A — Docker Compose (Recommended)

```bash
# Build and start
docker compose up --build

# Run in background
docker compose up -d --build

# Stop
docker compose down

# View logs
docker compose logs -f
```

Visit **http://localhost:5000**

---

### Option B — Run Locally (Python)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start development server
python app.py
```

Visit **http://localhost:5000**

---

### Option C — Docker (manual)

```bash
# Build image
docker build -t myvault .

# Run container
docker run -d \
  --name myvault \
  -p 5000:5000 \
  -v myvault_uploads:/app/uploads \
  -e MAX_CONTENT_MB=2048 \
  myvault
```

---

## ⚙️ Environment Variables

| Variable         | Default         | Description                              |
|------------------|-----------------|------------------------------------------|
| `PORT`           | `5000`          | Port the server listens on               |
| `UPLOAD_FOLDER`  | `uploads`       | Directory where videos are stored        |
| `MAX_CONTENT_MB` | `2048`          | Max upload file size in MB (2 GB)        |
| `FLASK_DEBUG`    | `false`         | Enable Flask debug mode                  |
| `WORKERS`        | `2`             | Gunicorn worker processes                |

---

## 📡 REST API Reference

| Method   | Endpoint                          | Description                        |
|----------|-----------------------------------|------------------------------------|
| `GET`    | `/`                               | Serve the web UI                   |
| `POST`   | `/api/upload`                     | Upload a video file (multipart)    |
| `GET`    | `/api/videos`                     | List all videos (supports `?q=&sort=`) |
| `GET`    | `/api/videos/<id>`                | Get single video metadata          |
| `PATCH`  | `/api/videos/<id>`                | Update name / duration             |
| `DELETE` | `/api/videos/<id>`                | Delete video                       |
| `GET`    | `/api/videos/<id>/stream`         | Stream video (HTTP Range support)  |
| `GET`    | `/api/videos/<id>/download`       | Download video as attachment       |
| `GET`    | `/api/stats`                      | Aggregate stats                    |
| `GET`    | `/health`                         | Health check                       |

### Query Parameters for `GET /api/videos`
- `?q=keyword` — search by video name
- `?sort=date|size|name|views` — sort order

---

## 🎥 Supported Formats

`MP4` · `MOV` · `AVI` · `MKV` · `WEBM` · `WMV` · `MPEG` · `OGV` · `3GP` · `FLV` · `M4V`

---

## 🔒 Security Notes

- Runs as a **non-root user** inside Docker
- Uses `werkzeug.utils.secure_filename` to sanitize filenames
- File type validation on both extension and MIME type
- Configurable max upload size to prevent abuse

---

## 📦 Tech Stack

- **Backend**: Python 3.12, Flask 3.1, Gunicorn
- **Frontend**: Vanilla HTML/CSS/JS (no framework dependency)
- **Storage**: Local filesystem + JSON metadata
- **Container**: Docker multi-stage build (slim image)
