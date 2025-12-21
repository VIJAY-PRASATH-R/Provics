# Flask imports
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from models import db, User, IndustrialVisit, Application, MoU, Notification, Review
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
from fpdf import FPDF
from dotenv import load_dotenv
from whitenoise import WhiteNoise

# Load environment variables
# Load environment variables (Force Override)
from dotenv import load_dotenv, find_dotenv
env_file = find_dotenv(raise_error_if_not_found=True)
load_dotenv(env_file, override=True)

from flask_mail import Mail, Message

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_dev_secret_key')

# --- MAIL CONFIGURATION (Real SMTP) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com' # Default to Gmail
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
# Explicitly set sender, fallback to username if not set
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')

mail = Mail(app)

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
upload_folder = os.path.join(basedir, 'static', 'uploads')

# Use DATABASE_URL if present
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
   database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///' + os.path.join(basedir, 'iv_planner.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = upload_folder

# Production Static Files
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/')

# Ensure upload directory exists
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

db.init_app(app)

# Helper: Send Email (Real)
def send_email(to_email, subject, body):
    try:
        sender = app.config['MAIL_USERNAME']
        msg = Message(subject=subject, recipients=[to_email], body=body, sender=sender)
        mail.send(msg)
        print(f"[SUCCESS] Email sent to {to_email}")
        return True, None
    except Exception as e:
        print(f"[FAILED] Email sending failed: {str(e)}")
        return False, str(e)

# Helper: Create Notification & Email
def notify_user(user_id, message, email_subject=None):
    # 1. In-App Notification
    notif = Notification(user_id=user_id, message=message)
    db.session.add(notif)
    db.session.commit()
    
    # 2. Email Notification
    user = User.query.get(user_id)
    if user:
        subject = email_subject or "New Notification from Provics"
        send_email(user.email, subject, message)

# Context Processor for Notifications in Header
@app.context_processor
def inject_notifications():
    if 'user_id' in session:
        unread_count = Notification.query.filter_by(user_id=session['user_id'], is_read=False).count()
        recent_notifs = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.created_at.desc()).limit(5).all()
        return dict(unread_count=unread_count, notifications=recent_notifs)
    return dict(unread_count=0, notifications=[])


# Create Database tables (run once)
with app.app_context():
    db.create_all()
    # No default users created. Real registration required.

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['name'] = user.name
            
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'college':
                return redirect(url_for('college_dashboard'))
            elif user.role == 'provider':
                return redirect(url_for('provider_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid email or password', 'error')
            
    return render_template('login.html')

import re

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        # Basic validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email address format.', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
        else:
            hashed_pw = generate_password_hash(password)
            new_user = User(email=email, password_hash=hashed_pw, name=name, role=role)
            db.session.add(new_user)
            db.session.commit()
            
            # Send Welcome Email
            send_email(email, "Welcome to Provics!", f"Hi {name},\n\nThank you for joining Provics. We are excited to have you on board as a {role}.\n\nBest Regards,\nThe Provics Team")
            
            flash('Registration successful! Welcome email sent. Please login.', 'success')
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- DASHBOARDS ---

from ai_utils import get_recommendations

def check_expired_mous():
    with app.app_context(): # Ensure existing context usage if called outside
        pass # Not needed if inside route
    today = datetime.now().date()
    # Need to import/ensure models are available, they are top level
    expired_mous = MoU.query.filter(MoU.status == 'active', MoU.end_date < today).all()
    for mou in expired_mous:
        mou.status = 'expired'
        # notify_user handles db session for notif, but here we modify Mou, so we need commit
        notify_user(mou.college_id, f"Your MoU has expired.", "MoU Expired")
        notify_user(mou.provider_id, f"MoU has expired.", "MoU Expired")
    if expired_mous:
        db.session.commit()

@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    search_query = request.args.get('search')
    type_filter = request.args.get('type')
    
    # Base query
    query = IndustrialVisit.query.filter_by(status='approved')
    
    # Filters
    if search_query:
        query = query.filter(IndustrialVisit.title.contains(search_query) | IndustrialVisit.description.contains(search_query))
    if type_filter:
        query = query.filter_by(visit_type=type_filter)
        
    available_visits = query.limit(50).all()
    
    my_applications = Application.query.filter_by(student_id=session['user_id']).all()
    user_details = User.query.get(session['user_id'])
    
    # AI Recommendations
    # We pass ALL approved visits to the AI engine to rank them for the user
    all_approved = IndustrialVisit.query.filter_by(status='approved').all()
    recommendations = get_recommendations(user_details, all_approved)
    
    # Filter recommendations to only show top 3 that are NOT applied to and have score > 0
    applied_ids = [app.visit_id for app in my_applications]
    top_picks = [r for r in recommendations if r['visit'].id not in applied_ids and r['score'] > 0][:3]
    
    return render_template('dashboard_student.html', 
                           user=user_details, 
                           visits=available_visits, 
                           applications=my_applications,
                           recommendations=top_picks)

@app.route('/student/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
        
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        user.bio = request.form['bio']
        user.skills = request.form['skills']
        
        # Resume Link (or upgrade to file upload later)
        user.resume_link = request.form['resume_link']
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student_dashboard'))
        
    return render_template('edit_profile.html', user=user)

@app.route('/notifications/mark_read')
def mark_notifications_read():
    if 'user_id' in session:
        Notification.query.filter_by(user_id=session['user_id'], is_read=False).update({'is_read': True})
        db.session.commit()
    return redirect(request.referrer)


@app.route('/college/dashboard')
def college_dashboard():
    if 'user_id' not in session or session['role'] != 'college':
        return redirect(url_for('login'))
        
    check_expired_mous()
    
    pending_visits = IndustrialVisit.query.filter_by(status='pending').all()
    approved_visits_count = IndustrialVisit.query.filter_by(status='approved').count()
    rejected_visits_count = IndustrialVisit.query.filter_by(status='rejected').count()
    
    # MoU Data
    my_mous = MoU.query.filter_by(college_id=session['user_id']).all()
    active_mou_count = MoU.query.filter_by(college_id=session['user_id'], status='active').count()
    pending_mou_count = MoU.query.filter_by(college_id=session['user_id'], status='pending').count()
    
    stats = {
        'approved_visits': approved_visits_count,
        'rejected_visits': rejected_visits_count,
        'active_mous': active_mou_count,
        'pending_mous': pending_mou_count
    }
    
    return render_template('dashboard_college.html', 
                           user=session, 
                           pending_visits=pending_visits, 
                           mous=my_mous,
                           stats=stats)

@app.route('/provider/dashboard')
def provider_dashboard():
    if 'user_id' not in session or session['role'] != 'provider':
        return redirect(url_for('login'))
    
    check_expired_mous()
    
    my_visits = IndustrialVisit.query.filter_by(provider_id=session['user_id']).all()
    
    # Stats Calculation
    total_visits = len(my_visits)
    total_applications = 0
    for v in my_visits:
        total_applications += len(v.applications)
        
    avg_rating = 0
    total_reviews = 0
    for v in my_visits:
        for r in v.reviews:
            avg_rating += r.rating
            total_reviews += 1
    if total_reviews > 0:
        avg_rating = round(avg_rating / total_reviews, 1)
    
    # MoU Data
    mou_requests = MoU.query.filter_by(provider_id=session['user_id'], status='pending').all()
    active_mous = MoU.query.filter_by(provider_id=session['user_id'], status='active').all()
    
    stats = {
        'total_visits': total_visits,
        'total_applications': total_applications,
        'active_mous': len(active_mous),
        'avg_rating': avg_rating,
        'review_count': total_reviews
    }
    
    return render_template('dashboard_provider.html', 
                           user=session, 
                           visits=my_visits,
                           mou_requests=mou_requests,
                           active_mous=active_mous,
                           stats=stats)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
        
    # Stats
    total_users = User.query.count()
    total_visits = IndustrialVisit.query.count()
    total_applications = Application.query.count()
    
    users = User.query.all()
    
    return render_template('dashboard_admin.html', user=session, users=users, stats={
        'users': total_users,
        'visits': total_visits,
        'applications': total_applications
    })

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.email != 'admin@test.com': # Prevent deleting main admin
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'User {user_to_delete.name} deleted.', 'success')
    else:
        flash('Cannot delete the main admin account.', 'error')
        
    return redirect(url_for('admin_dashboard'))

# --- FEATURE ROUTES ---

@app.route('/visit/create', methods=['GET', 'POST'])
def create_visit():
    if 'user_id' not in session or session['role'] != 'provider':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        date_str = request.form['date']
        location = request.form['location']
        visit_type = request.form.get('visit_type', 'Industrial Visit')
        
        try:
            visit_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            new_visit = IndustrialVisit(
                title=title,
                company_name=session['name'],
                description=description,
                date=visit_date,
                location=location,
                visit_type=visit_type,
                provider_id=session['user_id']
            )
            db.session.add(new_visit)
            db.session.commit()
            flash('Opportunity created successfully! Waiting for approval.', 'success')
            return redirect(url_for('provider_dashboard'))
        except Exception as e:
            flash(f'Error creating opportunity: {str(e)}', 'error')
            
    return render_template('create_visit.html')

@app.route('/visit/approve/<int:visit_id>')
def approve_visit(visit_id):
    if 'user_id' not in session or session['role'] != 'college':
        return redirect(url_for('login'))
        
    visit = IndustrialVisit.query.get_or_404(visit_id)
    visit.status = 'approved'
    db.session.commit()
    
    notify_user(visit.provider_id, f'Your "{visit.title}" has been approved by {session["name"]}.')
    
    flash(f'Visit "{visit.title}" has been approved.', 'success')
    return redirect(url_for('college_dashboard'))

@app.route('/visit/reject/<int:visit_id>')
def reject_visit(visit_id):
    if 'user_id' not in session or session['role'] != 'college':
        return redirect(url_for('login'))
        
    visit = IndustrialVisit.query.get_or_404(visit_id)
    visit.status = 'rejected'
    db.session.commit()
    
    notify_user(visit.provider_id, f'Your "{visit.title}" was rejected by {session["name"]}.')
    
    flash(f'Visit "{visit.title}" has been rejected.', 'success')
    return redirect(url_for('college_dashboard'))

@app.route('/visit/apply/<int:visit_id>')
def apply_visit(visit_id):
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
        
    # Check if already applied
    existing_app = Application.query.filter_by(student_id=session['user_id'], visit_id=visit_id).first()
    if existing_app:
        flash('You have already applied for this visit.', 'info')
    else:
        new_app = Application(student_id=session['user_id'], visit_id=visit_id)
        db.session.add(new_app)
        db.session.commit()
        
        visit = IndustrialVisit.query.get(visit_id)
        notify_user(visit.provider_id, f'New application for "{visit.title}" by {session["name"]}.', "New Student Application")
        
        # Notify Student as well
        send_email(User.query.get(session['user_id']).email, "Application Submitted", f"You have successfully applied for: {visit.title}")
        
        flash('Application submitted successfully!', 'success')
        
    return redirect(url_for('student_dashboard'))

# --- MOU ROUTES ---

@app.route('/mou/request', methods=['GET', 'POST'])
def request_mou():
    if 'user_id' not in session or session['role'] != 'college':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        provider_email = request.form['provider_email']
        terms = request.form['terms']
        
        provider = User.query.filter_by(email=provider_email, role='provider').first()
        if not provider:
            flash('Provider not found with that email.', 'error')
        else:
            existing = MoU.query.filter_by(college_id=session['user_id'], provider_id=provider.id, status='pending').first()
            if existing:
                flash('Pending MoU request already exists.', 'info')
            else:
                new_mou = MoU(college_id=session['user_id'], provider_id=provider.id, terms=terms)
                db.session.add(new_mou)
                db.session.commit()
                notify_user(provider.id, f'New MoU request from {session["name"]}.')
                flash('MoU Request sent to provider.', 'success')
                return redirect(url_for('college_dashboard'))

    return render_template('request_mou.html')

@app.route('/mou/approve/<int:mou_id>', methods=['POST'])
def approve_mou(mou_id):
    if 'user_id' not in session or session['role'] != 'provider':
        return redirect(url_for('login'))
        
    mou = MoU.query.get_or_404(mou_id)
    if mou.provider_id != session['user_id']:
        return redirect(url_for('provider_dashboard'))
        
    start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
    
    mou.start_date = start_date
    mou.end_date = end_date
    mou.status = 'active'
    db.session.commit()
    
    notify_user(mou.college_id, f'MoU accepted by {session["name"]}. You can now download the agreement.')
    flash('MoU Accepted and Activated.', 'success')
    return redirect(url_for('provider_dashboard'))

@app.route('/mou/reject/<int:mou_id>')
def reject_mou(mou_id):
    if 'user_id' not in session or session['role'] != 'provider':
        return redirect(url_for('login'))
        
    mou = MoU.query.get_or_404(mou_id)
    
    mou.status = 'rejected'
    db.session.commit()
    notify_user(mou.college_id, f'MoU rejected by {session["name"]}.')
    flash('MoU Rejected.', 'info')
    return redirect(url_for('provider_dashboard'))

@app.route('/mou/download/<int:mou_id>')
def download_mou(mou_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    mou = MoU.query.get_or_404(mou_id)
    # Check access
    if session['user_id'] not in [mou.college_id, mou.provider_id]:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('index'))
        
    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Memorandum of Understanding", ln=1, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"This agreement is made between:", ln=1)
    pdf.cell(200, 10, txt=f"College: {mou.college.name}", ln=1)
    pdf.cell(200, 10, txt=f"Provider: {mou.provider.name}", ln=1)
    pdf.ln(5)
    
    pdf.cell(200, 10, txt=f"Valid From: {mou.start_date} To: {mou.end_date}", ln=1)
    pdf.ln(5)
    
    pdf.multi_cell(0, 10, txt=f"Terms of Agreement:\n{mou.terms}")
    pdf.ln(20)
    
    pdf.cell(200, 10, txt="Signed Digitally via Provics Platform", ln=1, align='C')
    
    # Save to buffer
    pdf_buffer = BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    pdf_buffer.write(pdf_output)
    pdf_buffer.seek(0)
    
    return send_file(pdf_buffer, as_attachment=True, download_name=f'MoU_{mou.id}.pdf', mimetype='application/pdf')

# --- REVIEWS ---

@app.route('/visit/review/<int:visit_id>', methods=['POST'])
def post_review(visit_id):
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
        
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    
    # Check if attended (for now, we just check if approved application exists, 
    # ideally check if visit date passed)
    
    new_review = Review(visit_id=visit_id, student_id=session['user_id'], rating=rating, comment=comment)
    db.session.add(new_review)
    db.session.commit()
    
    flash('Thank you for your feedback!', 'success')
    return redirect(url_for('student_dashboard'))

# --- AUTH EXTRAS ---

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate OTP
            reset_otp = str(random.randint(100000, 999999))
            
            # Save to session
            session['reset_email'] = email
            session['reset_otp'] = reset_otp
            
            # Send Email
            success, error = send_email(email, "Password Reset OTP", f"Your Password Reset OTP is: {reset_otp}")
            
            if success:
                flash(f'OTP sent to {email}.', 'success')
                return redirect(url_for('verify_reset_otp'))
            else:
                flash(f'Failed to send email: {error}', 'error')
        else:
            flash('Email not found.', 'error')
    return render_template('forgot_password.html')

@app.route('/reset_password/verify', methods=['GET', 'POST'])
def verify_reset_otp():
    if 'reset_email' not in session or 'reset_otp' not in session:
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        otp_input = request.form['otp']
        if otp_input == session['reset_otp']:
            session['reset_verified'] = True
            return redirect(url_for('reset_new_password'))
        else:
            flash('Invalid OTP', 'error')
            
    return render_template('verify_reset_otp.html')

@app.route('/reset_password/new', methods=['GET', 'POST'])
def reset_new_password():
    if 'reset_verified' not in session:
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
        else:
            email = session['reset_email']
            user = User.query.filter_by(email=email).first()
            if user:
                user.password_hash = generate_password_hash(password)
                db.session.commit()
                
                # Cleanup
                session.pop('reset_email', None)
                session.pop('reset_otp', None)
                session.pop('reset_verified', None)
                
                flash('Password reset successful! Please login.', 'success')
                return redirect(url_for('login'))
                
    return render_template('reset_new_password.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

import random

# --- ACCOUNT DELETION & OTP ---

@app.route('/account/delete', methods=['GET', 'POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = User.query.get(session['user_id'])
    
    if not user:
        session.clear()
        flash('Account not found or already deleted.', 'info')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Generate OTP
        otp = str(random.randint(100000, 999999))
        session['delete_otp'] = otp
        session['delete_otp_email'] = user.email
        
        # Send OTP Email
        success, error = send_email(user.email, "Account Deletion OTP", f"Your OTP to DELETE your Provics account is: {otp}\n\nWarning: This action is irreversible.")
        
        if success:
            flash('OTP sent to your email. Please verify to confirm deletion.', 'info')
            return redirect(url_for('verify_delete_account'))
        else:
            flash(f'Failed to send OTP email: {error}', 'error')
            return redirect(url_for('delete_account'))
        
    return render_template('delete_account.html', user=user)

@app.route('/account/delete/verify', methods=['GET', 'POST'])
def verify_delete_account():
    if 'user_id' not in session or 'delete_otp' not in session:
        return redirect(url_for('delete_account'))
        
    if request.method == 'POST':
        otp_input = request.form['otp']
        
        if otp_input == session['delete_otp']:
            # Perform Deletion
            user = User.query.get(session['user_id'])
            
            if user:
                user_email = user.email
                db.session.delete(user)
                db.session.commit()
            else:
                # User might already be gone, fallback to session email if available
                user_email = session.get('delete_otp_email')
            
            # 2. Cleanup session
            session.clear()
            
            # 3. Send final goodbye email
            send_email(user_email, "Account Deleted", "Your Provics account has been permanently deleted. We are sorry to see you go!")
            
            flash('Your account has been deleted permanently.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
            
    return render_template('verify_delete.html')

if __name__ == '__main__':
    # Use port from environment variable for deployment (default 5000)
    port = int(os.environ.get('PORT', 5000))
    # ENABLE DEBUG FOR FIXING 500 ERROR
    app.run(debug=True, host='0.0.0.0', port=port)
