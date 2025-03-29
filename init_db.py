from app import app, db
from models import Admin

def init_db():
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        
        DEFAULT_USERNAME = 'admin@comoros.com'
        DEFAULT_PASSWORD = 'CoMoRoS@2024'
        
        try:
            print("Checking for existing admin...")
            # Delete existing admin if it exists
            Admin.query.delete()
            db.session.commit()
            
            print("Creating new admin user...")
            admin = Admin(username=DEFAULT_USERNAME)
            admin.set_password(DEFAULT_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            
            # Verify the admin was created
            created_admin = Admin.query.filter_by(username=DEFAULT_USERNAME).first()
            if created_admin and created_admin.check_password(DEFAULT_PASSWORD):
                print("\nAdmin user created successfully!")
                print("You can now login with:")
                print(f"Username: {DEFAULT_USERNAME}")
                print(f"Password: {DEFAULT_PASSWORD}")
            else:
                print("\nERROR: Failed to verify admin credentials!")
                
        except Exception as e:
            print(f"Error: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    print("Starting database initialization...")
    init_db()
    print("Database initialization complete!")
