from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from apscheduler.schedulers.background import BackgroundScheduler
from flask_login import LoginManager
import secrets
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
scheduler = BackgroundScheduler()


def create_app():
    app = Flask(__name__)

    # Configure database
    app.config['SECRET_KEY'] = secrets.token_hex(16)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///techblog.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    #uploads
    app.config["MAX_CONTENT_LENGTH"] =32 * 1024 * 1024
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    app.config["AVATAR_FOLDER"] = os.path.join(app.config["UPLOAD_FOLDER"], "avatars")
    app.config["POSTS_FOLDER"] = os.path.join(app.config["UPLOAD_FOLDER"], "posts")

    # Ensure folders exist
    os.makedirs(app.config["AVATAR_FOLDER"], exist_ok=True)
    os.makedirs(app.config["POSTS_FOLDER"], exist_ok=True)


    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = 'info'

    # Import and register blueprints
    from .routes import main
    from .auth import auth
    from .admin import admin

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(admin)

    # Schedule AI agent job here AFTER app is fully set up
    from .ai_agent import update_trending_stories
    # Import inside the function to avoid circular imports

    with app.app_context():
        update_trending_stories()

    scheduler.add_job(func=lambda:update_trending_stories(),
                      trigger="interval", minutes=30)
    scheduler.start()

    return app
