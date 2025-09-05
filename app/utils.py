import os, uuid
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_IMAGES = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_VIDEOS = {"mp4", "webm", "mov", "avi", "mkv"}

def _ext_ok(filename, allowed):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in allowed

def save_upload(file_storage, subfolder="posts", kind="image"):
    """
    kind: "image" or "video"
    subfolder: "posts" or "avatars"
    Returns relative path from /static (e.g. "uploads/posts/uuid-name.png")
    """
    if not file_storage or file_storage.filename == "":
        return None

    allowed = ALLOWED_IMAGES if kind == "image" else ALLOWED_VIDEOS
    if not _ext_ok(file_storage.filename, allowed):
        return None

    base = current_app.config["UPLOAD_FOLDER"]
    if subfolder == "avatars":
        base = current_app.config["AVATAR_FOLDER"]
    elif subfolder == "posts":
        base = current_app.config["POSTS_FOLDER"]

    filename = secure_filename(file_storage.filename)
    unique = f"{uuid.uuid4().hex}-{filename}"
    path = os.path.join(base, unique)
    file_storage.save(path)

    # Return path relative to static
    return f"uploads/{subfolder}/{unique}"
