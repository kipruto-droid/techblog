from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from . import db


# ---------------------------
# USER MODEL
# ---------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    is_admin = db.Column(db.Boolean, default=False)

    # Relationships
    posts = db.relationship("Post", backref="author", lazy=True)
    likes = db.relationship("Like", backref="user", lazy=True)
    profile = db.relationship("Profile", uselist=False, backref="user")

    # password methods
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ---------------------------
# BLOG POSTS
# ---------------------------
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=False)   # short description
    content = db.Column(db.Text, nullable=True)    # full blog/article text
    category = db.Column(db.String(100), nullable=False, default="General")

    # media (optional uploads or links)
    image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))

    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="published")

    # Foreign key → User
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Relationships
    likes = db.relationship("Like", backref="post", lazy="dynamic", cascade="all, delete-orphan")


# ---------------------------
# TRENDING STORIES (AI fetched)
# ---------------------------
class TrendingStory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    source_url = db.Column(db.String(500))
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------
# PROFILE (extra info for each user)
# ---------------------------
class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)

    avatar_filename = db.Column(db.String(255))      # uploaded avatar filename
    bio = db.Column(db.Text)
    tech_department = db.Column(db.String(120))      # e.g. "AI/ML", "Game Dev", "Cybersec"
    skills = db.Column(db.String(255))               # comma-separated tags
    website = db.Column(db.String(255))
    twitter = db.Column(db.String(255))
    github = db.Column(db.String(255))
    linkedin = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------
# LIKES (User ↔ Post many-to-many)
# ---------------------------
class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # prevent duplicate likes
    __table_args__ = (db.UniqueConstraint("user_id", "post_id", name="uq_user_post_like"),)
