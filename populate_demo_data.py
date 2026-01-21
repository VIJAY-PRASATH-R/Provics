from app import app, db, User, IndustrialVisit, Application, MoU, Review, Notification
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def populate():
    with app.app_context():
        print("Populating database with demo data...")
        
        # --- 1. Create Users ---
        users_data = [
            # Colleges
            {"name": "Anna University", "email": "anna@test.com", "role": "college", "bio": "Leading State University."},
            {"name": "IIT Madras", "email": "iitm@test.com", "role": "college", "bio": "Institute of excellence."},
            
            # Providers
            {"name": "Tesla India", "email": "tesla@test.com", "role": "provider", "bio": "Automotive and Energy."},
            {"name": "Zoho Corp", "email": "zoho@test.com", "role": "provider", "bio": "Software Development SaaS."},
            {"name": "L&T Construction", "email": "lnt@test.com", "role": "provider", "bio": "Construction heavyweights."},
            
            # Students
            {"name": "Rahul Kumar", "email": "rahul@test.com", "role": "student", "skills": "Python, Flask, AI", "bio": "Aspiring Developer"},
            {"name": "Priya Sharma", "email": "priya@test.com", "role": "student", "skills": "Civil Engineering, AutoCAD", "bio": "Structure enthusiast"},
            {"name": "Amit Patel", "email": "amit@test.com", "role": "student", "skills": "MBA, Marketing", "bio": "Business analyst"}
        ]
        
        users = {}
        for u in users_data:
            user = User.query.filter_by(email=u['email']).first()
            if not user:
                user = User(
                    name=u['name'], 
                    email=u['email'], 
                    password_hash=generate_password_hash('pass123'), 
                    role=u['role'],
                    bio=u.get('bio', ''),
                    skills=u.get('skills', '')
                )
                db.session.add(user)
                db.session.commit() # Commit to get ID
                print(f"Created {u['role']}: {u['name']}")
            users[u['email']] = user

        # --- 2. Create Visits ---
        visits_data = [
            {
                "provider": "tesla@test.com", 
                "title": "EV Manufacturing Insight", 
                "description": "A comprehensive tour of our electric vehicle assembly line.",
                "location": "Bengaluru",
                "date": datetime.now() + timedelta(days=10),
                "type": "Industrial Visit",
                "status": "approved"
            },
            {
                "provider": "zoho@test.com", 
                "title": "SaaS Product Development Internship", 
                "description": "2-month internship for backend developers.",
                "location": "Chennai",
                "date": datetime.now() + timedelta(days=5),
                "type": "Internship",
                "status": "approved"
            },
            {
                "provider": "lnt@test.com", 
                "title": "Site Visit: Metro Project", 
                "description": "On-site visit to the new metro line construction.",
                "location": "Mumbai",
                "date": datetime.now() + timedelta(days=20),
                "type": "Industrial Visit",
                "status": "pending"
            }
        ]
        
        db_visits = []
        for v in visits_data:
            provider = users.get(v['provider'])
            if provider:
                visit = IndustrialVisit.query.filter_by(title=v['title']).first()
                if not visit:
                    visit = IndustrialVisit(
                        title=v['title'],
                        company_name=provider.name,
                        description=v['description'],
                        location=v['location'],
                        date=v['date'],
                        visit_type=v['type'],
                        provider_id=provider.id,
                        status=v['status']
                    )
                    db.session.add(visit)
                    db.session.commit()
                    print(f"Created Visit: {v['title']}")
                db_visits.append(visit)

        # --- 3. Create Applications ---
        # Rahul applies to Zoho
        rahul = users.get('rahul@test.com')
        zoho_visit = IndustrialVisit.query.filter_by(title="SaaS Product Development Internship").first()
        
        if rahul and zoho_visit:
            if not Application.query.filter_by(student_id=rahul.id, visit_id=zoho_visit.id).first():
                new_app_record = Application(student_id=rahul.id, visit_id=zoho_visit.id, status='accepted')
                db.session.add(new_app_record)
                print(f"Application: Rahul -> Zoho")

        # --- 4. Create MoUs ---
        # Anna Univ <-> Tesla (Active)
        anna = users.get('anna@test.com')
        tesla = users.get('tesla@test.com')
        
        if anna and tesla:
            if not MoU.query.filter_by(college_id=anna.id, provider_id=tesla.id).first():
                mou = MoU(
                    college_id=anna.id, 
                    provider_id=tesla.id, 
                    status='active', 
                    start_date=datetime.now() - timedelta(days=30),
                    end_date=datetime.now() + timedelta(days=335),
                    terms="Standard IV agreement for 50 students."
                )
                db.session.add(mou)
                print("MoU: Anna Univ <-> Tesla")

        # --- 5. Notifications ---
        if rahul:
            n = Notification(user_id=rahul.id, message="Your application for Zoho Internship was accepted!", is_read=False)
            db.session.add(n)

        db.session.commit()
        print("Demo data populated successfully!")

if __name__ == '__main__':
    populate()
