from app import app, db
from models import Admin

def init_db():
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        
        # Simple credentials for testing
        DEFAULT_USERNAME = 'admin'
        DEFAULT_PASSWORD = 'admin123'
        
        try:
            print("\nSetting up admin account...")
            
            # Remove any existing admin accounts
            print("Removing existing admin accounts...")
            Admin.query.delete()
            db.session.commit()
            
            # Create fresh admin account
            print(f"Creating new admin account with username: {DEFAULT_USERNAME}")
            admin = Admin(username=DEFAULT_USERNAME)
            admin.set_password(DEFAULT_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            
            # Verify the account
            print("\nVerifying admin account...")
            admin = Admin.query.filter_by(username=DEFAULT_USERNAME).first()
            if admin and admin.check_password(DEFAULT_PASSWORD):
                print("✓ Admin account verified successfully!")
                print("\nYou can now login with:")
                print(f"Username: {DEFAULT_USERNAME}")
                print(f"Password: {DEFAULT_PASSWORD}")
            else:
                print("❌ ERROR: Admin account verification failed!")
            
            # Double check password hash
            if admin:
                print(f"\nDebug Info:")
                print(f"Admin ID: {admin.id}")
                print(f"Password Hash: {admin.password_hash[:20]}...")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            db.session.rollback()
            raise e

if __name__ == '__main__':
    print("Starting database initialization...")
    init_db()
    print("\nDatabase initialization complete!")
