from app import app, db
from models import Admin

def init_db():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Set default admin credentials
        DEFAULT_USERNAME = 'admin'
        DEFAULT_PASSWORD = 'admin123'
        
        # Check if admin exists
        admin = Admin.query.filter_by(username=DEFAULT_USERNAME).first()
        if not admin:
            # Create admin user with default credentials
            admin = Admin(username=DEFAULT_USERNAME)
            admin.set_password(DEFAULT_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created successfully")
            print(f"Username: {DEFAULT_USERNAME}")
            print(f"Password: {DEFAULT_PASSWORD}")
        else:
            print("Admin user already exists")

if __name__ == '__main__':
    init_db()
