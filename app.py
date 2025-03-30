from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_marshmallow import Marshmallow
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from models import db, Container, Announcement, Arrival, Admin
from datetime import datetime, timedelta
import pandas as pd
from difflib import SequenceMatcher

app = Flask(__name__)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '2166df75b79a7249e7323f2a1ffa7ae8')

# Get database URL with proper formatting for PostgreSQL
database_url = os.environ.get('DATABASE_URL', 'postgresql://comoros_tracking_user:hcYsAODyEDQX6WqxnZVNaZAGWL3OR5To@dpg-cvjpmrhr0fns738iltvg-a.oregon-postgres.render.com/comoros_tracking')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session lasts 7 days

# Initialize extensions
db.init_app(app)
ma = Marshmallow(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# Container Schema
class ContainerSchema(ma.Schema):
    class Meta:
        fields = ('id', 'container_number', 'location', 'status', 'destination', 
                 'eta', 'vessel_name', 'last_updated')

container_schema = ContainerSchema()
containers_schema = ContainerSchema(many=True)

# Add custom Jinja2 test
@app.template_test('day_is')
def day_is(value, other):
    if value is None:
        return False
    return value.date() == other.date()

# Routes
@app.route('/')
def home():
    from datetime import datetime, timedelta
    # Get announcements
    announcements = Announcement.query.filter_by(
        is_active=True
    ).order_by(Announcement.created_at.desc()).all()  # Changed this line to get all active announcements
    
    # Get upcoming arrivals for next 7 days
    today = datetime.utcnow()
    next_week = today + timedelta(days=7)
    
    mutsamudu_arrivals = Arrival.query.filter(
        Arrival.destination_port == 'Mutsamudu',
        Arrival.eta >= today,
        Arrival.eta <= next_week
    ).order_by(Arrival.eta).all()
    
    moroni_arrivals = Arrival.query.filter(
        Arrival.destination_port == 'Moroni',
        Arrival.eta >= today,
        Arrival.eta <= next_week
    ).order_by(Arrival.eta).all()

    return render_template('index.html',
                         announcements=announcements,  # Changed this line
                         mutsamudu_arrivals=mutsamudu_arrivals,
                         moroni_arrivals=moroni_arrivals)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/rates')
def rates():
    return render_template('rates.html')

@app.route('/container', methods=['POST'])
def create_container():  # Changed from add_container to create_container
    container_number = request.json['container_number']
    location = request.json['location']
    status = request.json['status']

    new_container = Container(container_number=container_number, location=location, status=status)
    db.session.add(new_container)
    db.session.commit()
    
    return container_schema.jsonify(new_container)

def get_string_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def has_single_digit_difference(str1, str2):
    if len(str1) != len(str2):
        return False
    differences = sum(1 for a, b in zip(str1, str2) if a != b)
    return differences == 1

@app.route('/container/<container_number>', methods=['GET'])
def track_container(container_number):
    # First try exact match
    container = Container.query.filter_by(container_number=container_number).first()
    
    if not container:
        # If no exact match, look for containers with similar numbers
        all_containers = Container.query.all()
        similar_containers = [c for c in all_containers if has_single_digit_difference(c.container_number, container_number)]
        
        if len(similar_containers) == 1:
            # Found one container with single digit difference
            container = similar_containers[0]
            message = f"Exact container not found. Showing results for similar container: {container.container_number}"
        else:
            return jsonify({"message": "Container not found"}), 404
    else:
        message = None
    
    if container:
        eta = None
        if container.vessel and container.vessel.eta:
            eta = container.vessel.eta.strftime('%Y-%m-%d %H:%M')
            
        response_data = {
            'container_number': container.container_number,
            'current_location': container.vessel.current_port if container.vessel else 'Not Assigned',
            'final_destination': container.final_destination,
            'status': container.status,
            'vessel_name': container.vessel.vessel_name if container.vessel else 'Not Assigned',
            'eta': eta,
            'last_updated': container.last_updated,
            'suggested': message  # Add suggestion message if it exists
        }
        return jsonify(response_data)

@app.route('/containers', methods=['GET'])
def get_all_containers():
    containers = Container.query.all()
    return containers_schema.jsonify(containers)

@app.route('/schedule/<port>', methods=['GET'])
def get_schedule(port):
    # Add logic to fetch schedule for specific port
    pass

@app.route('/admin/schedule')
@login_required
def admin_schedule():
    from datetime import datetime
    today = datetime.utcnow()  # Remove .date() since we'll compare in the template
    arrivals = Arrival.query.all()
    return render_template('admin/schedule.html', arrivals=arrivals, today=today)

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Admin.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        return render_template('admin/login.html', error='Invalid credentials')
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    from datetime import datetime
    
    # Get counts
    containers_count = Container.query.count()
    announcements_count = Announcement.query.count()
    active_announcements = Announcement.query.filter_by(is_active=True).count()
    arrivals_count = Arrival.query.count()
    
    # Calculate next arrival hours
    next_arrival = Arrival.query.filter(Arrival.eta > datetime.utcnow()).order_by(Arrival.eta).first()
    next_arrival_hours = '0'
    if next_arrival:
        time_diff = next_arrival.eta - datetime.utcnow()
        next_arrival_hours = str(round(time_diff.total_seconds() / 3600))

    # Mock recent activities (you can replace this with real data)
    recent_activities = [
        {
            'type': 'container',
            'icon': 'fas fa-box',
            'description': 'New container MSCU1234567 added',
            'timestamp': '2 hours ago'
        },
        {
            'type': 'announcement',
            'icon': 'fas fa-bullhorn',
            'description': 'Port maintenance announcement published',
            'timestamp': '4 hours ago'
        },
        {
            'type': 'arrival',
            'icon': 'fas fa-ship',
            'description': 'Vessel "Maersk Line" arrival updated',
            'timestamp': '6 hours ago'
        }
    ]

    return render_template('admin/dashboard.html',
                         current_date=datetime.now(),
                         containers_count=containers_count,
                         announcements_count=announcements_count,
                         active_announcements=active_announcements,
                         arrivals_count=arrivals_count,
                         next_arrival_hours=next_arrival_hours,
                         recent_activities=recent_activities)

@app.route('/admin/announcements')
@login_required
def admin_announcements():
    announcements = Announcement.query.all()
    return render_template('admin/announcements.html', announcements=announcements)

@app.route('/admin/containers')
@login_required
def admin_containers():
    # Use SQLAlchemy join to ensure vessel data is loaded
    containers = Container.query.outerjoin(Arrival, Container.vessel_id == Arrival.id).all()
    vessels = Arrival.query.all()  # Get all vessels for the dropdown
    return render_template('admin/containers.html', containers=containers, vessels=vessels)

# Remove or comment out this duplicate route
# @app.route('/admin/schedule')
# @login_required
# def admin_schedule():
#     from datetime import datetime
#     arrivals = Arrival.query.all()
#     today = datetime.utcnow()
#     return render_template('admin/schedule.html', arrivals=arrivals, today=today)

@app.route('/admin')
def admin_redirect():
    return redirect(url_for('admin_login'))

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

# Add container CRUD operations
@app.route('/admin/containers/add', methods=['POST'])
@login_required
def add_container():
    try:
        data = request.json
        new_container = Container(
            container_number=data['container_number'],
            final_destination=data['final_destination'],
            vessel_id=data.get('vessel_id')
        )
        db.session.add(new_container)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Container added successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/containers/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def update_delete_container(id):
    container = Container.query.get_or_404(id)
    
    if request.method == 'DELETE':
        db.session.delete(container)
        db.session.commit()
        return jsonify({'message': 'Container deleted successfully'})
    
    # Handle PUT request
    data = request.get_json()
    
    # Update container fields
    container.container_number = data['container_number']
    container.final_destination = data['final_destination']
    container.vessel_id = data['vessel_id'] or None  # Handle empty vessel_id
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Container updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/containers/<int:id>', methods=['GET'])
@login_required
def get_container_by_id(id):  # Renamed from get_container to get_container_by_id
    container = Container.query.get_or_404(id)
    return jsonify({
        'container_number': container.container_number,
        'final_destination': container.final_destination,
        'vessel_id': container.vessel_id
    })

# Add announcement CRUD operations
@app.route('/admin/announcements/add', methods=['POST'])
@login_required
def add_announcement():
    data = request.json
    new_announcement = Announcement(
        title=data['title'],
        content=data['content'],
        category=data['category'],
        is_active=data['is_active']
    )
    try:
        db.session.add(new_announcement)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Announcement added successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error adding announcement'}), 500

@app.route('/admin/announcements/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    
    if request.method == 'GET':
        return jsonify({
            'title': announcement.title,
            'category': announcement.category,
            'content': announcement.content,
            'is_active': announcement.is_active
        })
    elif request.method == 'PUT':
        data = request.get_json()
        announcement.title = data.get('title')
        announcement.category = data.get('category')
        announcement.content = data.get('content')
        announcement.is_active = data.get('is_active')
        
        db.session.commit()
        return jsonify({'success': True})
    else:  # DELETE
        db.session.delete(announcement)
        db.session.commit()
        return jsonify({'success': True})

@app.route('/admin/schedule/add', methods=['POST'])
@login_required
def add_arrival():
    from datetime import datetime
    try:
        data = request.json
        new_arrival = Arrival(
            vessel_name=data['vessel_name'],
            voyage_number=data['voyage_number'],
            origin_port=data['origin_port'],
            current_port=data['current_port'],  # Added field
            destination_port=data['destination_port'],
            eta=datetime.strptime(data['eta'], '%Y-%m-%dT%H:%M'),
            status=data['status'],
            berth=data['berth']
        )
        db.session.add(new_arrival)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Arrival added successfully'})
    except Exception as e:
        print('Error:', str(e))  # For debugging
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Add update location endpoint
@app.route('/admin/schedule/<int:id>/location', methods=['PUT'])
@login_required
def update_vessel_location(id):
    try:
        arrival = Arrival.query.get_or_404(id)
        data = request.json
        arrival.current_port = data['current_port']
        arrival.status = data.get('status', arrival.status)  # Optionally update status
        db.session.commit()
        return jsonify({'success': True, 'message': 'Location updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/schedule/<int:id>', methods=['DELETE'])
@login_required
def delete_arrival(id):
    try:
        arrival = Arrival.query.get_or_404(id)
        db.session.delete(arrival)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Vessel deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/schedule/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_arrival(id):
    arrival = Arrival.query.get_or_404(id)
    
    if request.method == 'GET':
        return jsonify({
            'vessel_name': arrival.vessel_name,
            'voyage_number': arrival.voyage_number,
            'origin_port': arrival.origin_port,
            'destination_port': arrival.destination_port,
            'current_port': arrival.current_port,
            'eta': arrival.eta.strftime('%Y-%m-%dT%H:%M'),
            'status': arrival.status,
            'berth': arrival.berth
        })
    elif request.method == 'PUT':
        data = request.get_json()
        arrival.vessel_name = data.get('vessel_name')
        arrival.voyage_number = data.get('voyage_number')
        arrival.origin_port = data.get('origin_port')
        arrival.destination_port = data.get('destination_port')
        arrival.current_port = data.get('current_port')
        arrival.eta = datetime.strptime(data.get('eta'), '%Y-%m-%dT%H:%M')
        arrival.status = data.get('status')
        arrival.berth = data.get('berth')
        
        db.session.commit()
        return jsonify({'success': True})
    else:  # DELETE
        db.session.delete(arrival)
        db.session.commit()
        return jsonify({'success': True})

@app.route('/admin/containers/upload', methods=['POST'])
@login_required
def upload_containers():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'success': False, 'message': 'Invalid file format'}), 400

    try:
        # Read Excel file
        df = pd.read_excel(file)
        required_columns = ['Container Number', 'Assign to Vessel', 'Final Destination']
        
        # Verify required columns
        if not all(col in df.columns for col in required_columns):
            return jsonify({
                'success': False,
                'message': f'Missing required columns. Required: {", ".join(required_columns)}'
            }), 400

        containers_added = 0
        errors = []

        # Process each row
        for _, row in df.iterrows():
            try:
                # Look up vessel by name/voyage number
                vessel_info = row['Assign to Vessel'].split(' (')
                vessel_name = vessel_info[0]
                voyage_number = vessel_info[1].split(')')[0] if len(vessel_info) > 1 else None
                
                vessel = Arrival.query.filter_by(
                    vessel_name=vessel_name,
                    voyage_number=voyage_number
                ).first() if voyage_number else None

                # Create new container
                new_container = Container(
                    container_number=row['Container Number'],
                    final_destination=row['Final Destination'],
                    vessel_id=vessel.id if vessel else None
                )
                db.session.add(new_container)
                containers_added += 1
                
            except Exception as e:
                errors.append(f"Error in row {containers_added + 1}: {str(e)}")
                continue

        db.session.commit()
        
        return jsonify({
            'success': True,
            'added': containers_added,
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error processing file: {str(e)}'
        }), 500

@app.before_request
def before_request():
    if current_user.is_authenticated:
        session.permanent = True  # Make session permanent

# Initialize admin user
def init_admin():
    with app.app_context():
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            admin = Admin(username='admin')
            admin.set_password('admin123')  # Change this to a secure password
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Initialize admin user
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            admin = Admin(username='admin')
            admin.set_password('admin123')  # Change this password in production
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully")
            
    app.run(debug=True)
