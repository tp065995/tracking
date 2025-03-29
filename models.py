from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # 'priority', 'maintenance', 'notice'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Arrival(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vessel_name = db.Column(db.String(100), nullable=False)
    voyage_number = db.Column(db.String(50))
    origin_port = db.Column(db.String(100))
    current_port = db.Column(db.String(100))  # Added current port
    destination_port = db.Column(db.String(100))
    eta = db.Column(db.DateTime)
    status = db.Column(db.String(50))
    berth = db.Column(db.String(50))
    containers = db.relationship('Container', backref='vessel', lazy=True)  # Add relationship
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Container(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    container_number = db.Column(db.String(20), unique=True, nullable=False)
    final_destination = db.Column(db.String(100))  # Changed from location to final_destination
    current_location = db.Column(db.String(100))   # Added current_location
    vessel_id = db.Column(db.Integer, db.ForeignKey('arrival.id'))  # Add foreign key
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def status(self):
        if not self.vessel:
            return "Not Assigned"
        
        if self.vessel.current_port == self.final_destination:
            return "Arrived"
        elif self.vessel.current_port:
            return f"In Transit via {self.vessel.current_port}"
        else:
            return "En Route"

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
