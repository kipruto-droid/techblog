# reset_db.py
from app import create_app, db

def reset_database():
    app = create_app()
    with app.app_context():
        print("⚠️ Dropping all tables...")
        db.drop_all()
        print("✅ Tables dropped.")

        print("📦 Creating all tables...")
        db.create_all()
        print("✅ Tables created.")

if __name__ == "__main__":
    reset_database()
