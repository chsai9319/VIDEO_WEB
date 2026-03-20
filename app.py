import os
import uuid
import json
import mimetypes
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, request, jsonify, send_from_directory,
    render_template, Response, abort
)
from werkzeug.utils import secure_filename

# ─── CONFIG ───────────────────────────────────────────────────────────────────

UPLOAD_FOLDER = Path(os.environ.get("UPLOAD_FOLDER", "uploads"))
METADATA_FILE = UPLOAD_FOLDER / "metadata.json"
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_MB", 2048)) * 1024 * 1024  # default 2 GB

ALLOWED_EXTENSIONS = {
    "mp4", "mov", "avi", "mkv", "webm", "wmv",
    "mpeg", "mpg", "ogv", "3gp", "flv", "m4v"
}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


# ─── METADATA HELPERS ─────────────────────────────────────────────────────────

def load_metadata() -> dict:
    if METADATA_FILE.exists():
        try:
            return json.loads(METADATA_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_metadata(data: dict):
    METADATA_FILE.write_text(json.dumps(data, indent=2))


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Upload ─────────────────────────────────────────────────────────────────────
@app.route("/api/upload", methods=["POST"])
def upload_video():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"}), 400

    original_name = secure_filename(file.filename)
    ext = original_name.rsplit(".", 1)[1].lower()
    video_id = str(uuid.uuid4())
    stored_filename = f"{video_id}.{ext}"
    save_path = UPLOAD_FOLDER / stored_filename

    file.save(str(save_path))
    size = save_path.stat().st_size

    metadata = load_metadata()
    metadata[video_id] = {
        "id": video_id,
        "name": original_name.rsplit(".", 1)[0],
        "original_filename": original_name,
        "stored_filename": stored_filename,
        "ext": ext,
        "size": size,
        "date": datetime.utcnow().isoformat() + "Z",
        "duration": None,      # updated by frontend via PATCH
        "views": 0,
    }
    save_metadata(metadata)

    return jsonify(metadata[video_id]), 201


# ── List videos ───────────────────────────────────────────────────────────────
@app.route("/api/videos", methods=["GET"])
def list_videos():
    metadata = load_metadata()
    videos = list(metadata.values())

    # Optional query filters
    q = request.args.get("q", "").lower()
    sort = request.args.get("sort", "date")   # date | size | name | views

    if q:
        videos = [v for v in videos if q in v["name"].lower()]

    sort_key = {
        "date":  lambda v: v.get("date", ""),
        "size":  lambda v: v.get("size", 0),
        "name":  lambda v: v.get("name", "").lower(),
        "views": lambda v: v.get("views", 0),
    }.get(sort, lambda v: v.get("date", ""))

    videos.sort(key=sort_key, reverse=(sort != "name"))
    return jsonify(videos)


# ── Get single video metadata ─────────────────────────────────────────────────
@app.route("/api/videos/<video_id>", methods=["GET"])
def get_video(video_id):
    metadata = load_metadata()
    if video_id not in metadata:
        return jsonify({"error": "Video not found"}), 404
    return jsonify(metadata[video_id])


# ── Update metadata (name, duration) ─────────────────────────────────────────
@app.route("/api/videos/<video_id>", methods=["PATCH"])
def update_video(video_id):
    metadata = load_metadata()
    if video_id not in metadata:
        return jsonify({"error": "Video not found"}), 404

    data = request.get_json(silent=True) or {}
    allowed_fields = {"name", "duration"}
    for field in allowed_fields:
        if field in data:
            metadata[video_id][field] = data[field]

    save_metadata(metadata)
    return jsonify(metadata[video_id])


# ── Delete video ──────────────────────────────────────────────────────────────
@app.route("/api/videos/<video_id>", methods=["DELETE"])
def delete_video(video_id):
    metadata = load_metadata()
    if video_id not in metadata:
        return jsonify({"error": "Video not found"}), 404

    stored_filename = metadata[video_id]["stored_filename"]
    file_path = UPLOAD_FOLDER / stored_filename
    if file_path.exists():
        file_path.unlink()

    del metadata[video_id]
    save_metadata(metadata)
    return jsonify({"message": "Video deleted", "id": video_id})


# ── Stream / serve video with HTTP range support ──────────────────────────────
@app.route("/api/videos/<video_id>/stream")
def stream_video(video_id):
    metadata = load_metadata()
    if video_id not in metadata:
        abort(404)

    # Increment view count
    metadata[video_id]["views"] = metadata[video_id].get("views", 0) + 1
    save_metadata(metadata)

    stored_filename = metadata[video_id]["stored_filename"]
    file_path = UPLOAD_FOLDER / stored_filename

    if not file_path.exists():
        abort(404)

    file_size = file_path.stat().st_size
    mime_type = mimetypes.guess_type(stored_filename)[0] or "video/mp4"
    range_header = request.headers.get("Range")

    if range_header:
        # Parse byte range
        byte_range = range_header.strip().replace("bytes=", "")
        start_str, end_str = byte_range.split("-")
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
        chunk_size = end - start + 1

        def generate():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(65536, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    yield data
                    remaining -= len(data)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": chunk_size,
            "Content-Type": mime_type,
        }
        return Response(generate(), status=206, headers=headers)

    # Full file response
    return send_from_directory(
        str(UPLOAD_FOLDER), stored_filename,
        mimetype=mime_type,
        as_attachment=False
    )


# ── Download video ────────────────────────────────────────────────────────────
@app.route("/api/videos/<video_id>/download")
def download_video(video_id):
    metadata = load_metadata()
    if video_id not in metadata:
        abort(404)

    stored_filename = metadata[video_id]["stored_filename"]
    original_filename = metadata[video_id]["original_filename"]

    return send_from_directory(
        str(UPLOAD_FOLDER),
        stored_filename,
        as_attachment=True,
        download_name=original_filename
    )


# ── Stats ─────────────────────────────────────────────────────────────────────
@app.route("/api/stats")
def stats():
    metadata = load_metadata()
    videos = list(metadata.values())
    total_size = sum(v.get("size", 0) for v in videos)
    total_duration = sum(v.get("duration") or 0 for v in videos)
    total_views = sum(v.get("views", 0) for v in videos)

    return jsonify({
        "count": len(videos),
        "total_size": total_size,
        "total_duration": total_duration,
        "total_views": total_views,
    })


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "MyVault"})


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)
