from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()

class User(db.Model):
   id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128)) # Changed from password to password_hash
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False) # student, college, provider, admin
    
    # Profile Fields
    bio = db.Column(db.Text, nullable=True)
    skills = db.Column(db.String(500), nullable=True)
    resume_link = db.Column(db.String(500), nullable=True) # External link or file path

    # Relationships
    visits_created = db.relationship('IndustrialVisit', backref='provider', lazy=True, cascade="all, delete-orphan")
    applications = db.relationship('Application', backref='student', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan")
    
    # MoU Relationships
    mous_as_college = db.relationship('MoU', foreign_keys='MoU.college_id', backref='college', lazy=True, cascade="all, delete-orphan")
    mous_as_provider = db.relationship('MoU', foreign_keys='MoU.provider_id', backref='provider', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('industrial_visit.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1-5
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MoU(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, active, rejected, expired
    start_date = db.Column(db.Date, nullable=True) # Set when approved
    end_date = db.Column(db.Date, nullable=True)   # Set when approved
    terms = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class IndustrialVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    visit_type = db.Column(db.String(50), default='Industrial Visit') # IV, Internship, Mentorship
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected, completed
    
    applications = db.relationship('Application', backref='visit', lazy=True)
    reviews = db.relationship('Review', backref='visit', lazy=True)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    visit_id = db.Column(db.Integer, db.ForeignKey('industrial_visit.id'), nullable=False)
    status = db.Column(db.String(20), default='applied') # applied, accepted, rejected
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)
