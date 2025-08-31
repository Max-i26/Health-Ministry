from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import secrets
import string
import json
from flask_moment import Moment
from sqlalchemy import func,text




# Import models
from models import db, Ministry, Hospital, HospitalAdmin, Doctor, Patient, PatientIdentifier, MedicalEncounter, QRToken, AuditLog, PatientHospital

app = Flask(__name__)
moment = Moment(app)
app.secret_key = 'suhgisuhfjkabfkm,nfzznfl'

# Database Configuration
app.config["SECRET_KEY"] = "ut6r6jhpu7jiythuurooik"
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+pymysql://root@localhost:3308/carecode?charset=utf8mb4")

# Initialize database
db.init_app(app)

def generate_random_password(length=8):
    """Generate a random password for hospital admins"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_hospital_code(hospital_name):
    """Generate a unique hospital code"""
    # Take first 3 letters of hospital name and add random numbers
    prefix = ''.join(hospital_name.split()[:2])[:6].upper().replace(' ', '')
    suffix = ''.join(secrets.choice(string.digits) for _ in range(4))
    return f"{prefix}{suffix}"

def log_audit_action(action, acting_user_type, acting_user_id, details=None, patient_id=None, hospital_id=None):
    """Log audit actions"""
    try:
        audit_log = AuditLog(
            acting_user_type=acting_user_type,
            acting_user_id=acting_user_id,
            patient_id=patient_id,
            hospital_id=hospital_id,
            action=action,
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")

# =============================================================================
# MINISTRY ROUTES
# =============================================================================

@app.route('/')
def index():
    return redirect(url_for('ministry_login'))

@app.route('/ministry/login', methods=['GET', 'POST'])
def ministry_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        ministry = Ministry.query.filter_by(admin_username=username, is_active=True).first()
        
        if ministry and check_password_hash(ministry.password_hash, password):
            session['user_type'] = 'ministry'
            session['ministry_id'] = ministry.id
            session['ministry_name'] = ministry.name
            
            # Log login action
            log_audit_action('ministry_login', 'ministry', ministry.id)
            
            return redirect(url_for('ministry_dashboard'))
        else:
            flash('Invalid credentials or account is inactive')
    
    return render_template('ministry/login.html')

@app.route('/ministry/dashboard')
def ministry_dashboard():
    if 'user_type' not in session or session['user_type'] != 'ministry':
        return redirect(url_for('ministry_login'))
    
    ministry_id = session['ministry_id']
    
    # Get statistics
    total_hospitals = Hospital.query.filter_by(ministry_id=ministry_id, is_active=True).count()
    total_doctors = db.session.query(Doctor).join(Hospital).filter(
        Hospital.ministry_id == ministry_id,
        Hospital.is_active == True,
        Doctor.is_active == True
    ).count()
    total_patients = db.session.query(Patient).join(Hospital, Patient.created_by_hospital == Hospital.id).filter(
        Hospital.ministry_id == ministry_id,
        Hospital.is_active == True,
        Patient.is_active == True
    ).count()
    total_encounters = db.session.query(MedicalEncounter).join(Hospital).filter(
        Hospital.ministry_id == ministry_id,
        Hospital.is_active == True
    ).count()
    
    # Get recent hospitals
    recent_hospitals = Hospital.query.filter_by(ministry_id=ministry_id, is_active=True).order_by(Hospital.created_at.desc()).limit(5).all()
    
    # Get recent activities from audit logs
    recent_activities = AuditLog.query.join(Hospital, AuditLog.hospital_id == Hospital.id, isouter=True).filter(
        db.or_(
            Hospital.ministry_id == ministry_id,
            AuditLog.acting_user_type == 'ministry'
        )
    ).order_by(AuditLog.created_at.desc()).limit(10).all()
    
    return render_template('ministry/dashboard.html', 
                         total_hospitals=total_hospitals,
                         total_doctors=total_doctors,
                         total_patients=total_patients,
                         total_encounters=total_encounters,
                         recent_hospitals=recent_hospitals,
                         recent_activities=recent_activities)

@app.route('/ministry/add_hospital', methods=['GET', 'POST'])
def add_hospital():
    if 'user_type' not in session or session['user_type'] != 'ministry':
        return redirect(url_for('ministry_login'))
    
    if request.method == 'POST':
        try:
            ministry_id = session['ministry_id']
            
            # Hospital information
            hospital_name = request.form['hospital_name']
            address_line1 = request.form['address_line1']
            city = request.form['city']
            province = request.form['province']
            postal_code = request.form.get('postal_code', '')
            phone_primary = request.form['phone_primary']
            email = request.form['email']
            
            # Admin information
            admin_full_name = request.form['admin_full_name']
            admin_email = request.form['admin_email']
            admin_phone = request.form['admin_phone']
            
            # Generate credentials
            admin_username = hospital_name.lower().replace(' ', '_').replace('-', '_') + '_admin'
            admin_password = generate_random_password(10)
            hospital_code = generate_hospital_code(hospital_name)
            
            # Create hospital
            hospital = Hospital(
                ministry_id=ministry_id,
                name=hospital_name,
                code=hospital_code,
                address={
                    'address_line1': address_line1,
                    'city': city,
                    'province': province,
                    'postal_code': postal_code
                },
                contact_info={
                    'phone_primary': phone_primary,
                    'email': email
                }
            )
            db.session.add(hospital)
            db.session.flush()  # Get hospital ID
            
            # Create hospital admin
            hospital_admin = HospitalAdmin(
                hospital_id=hospital.id,
                username=admin_username,
                password_hash=generate_password_hash(admin_password),
                full_name=admin_full_name,
                email=admin_email,
                contact_info={
                    'phone_primary': admin_phone
                }
            )
            db.session.add(hospital_admin)
            db.session.commit()
            
            # Log action
            log_audit_action('hospital_created', 'ministry', session['ministry_id'], 
                           {'hospital_name': hospital_name, 'hospital_code': hospital_code}, 
                           hospital_id=hospital.id)
            
            flash(f'Hospital added successfully!<br>Hospital Code: <strong>{hospital_code}</strong><br>Admin Username: <strong>{admin_username}</strong><br>Admin Password: <strong>{admin_password}</strong><br><small>Please share these credentials with the hospital.</small>')
            return redirect(url_for('view_hospitals'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding hospital: {str(e)}')
    
    return render_template('ministry/add_hospital.html')

@app.route('/ministry/hospitals')
def view_hospitals():
    if 'user_type' not in session or session['user_type'] != 'ministry':
        return redirect(url_for('ministry_login'))
    
    ministry_id = session['ministry_id']
    
    # Get hospitals with statistics
    hospitals = db.session.query(Hospital).filter_by(ministry_id=ministry_id, is_active=True).all()
    
    # Add statistics to each hospital
    for hospital in hospitals:
        hospital.doctor_count = Doctor.query.filter_by(hospital_id=hospital.id, is_active=True).count()
        hospital.patient_count = Patient.query.filter_by(created_by_hospital=hospital.id, is_active=True).count()
        hospital.encounter_count = MedicalEncounter.query.filter_by(hospital_id=hospital.id).count()
        hospital.admin = HospitalAdmin.query.filter_by(hospital_id=hospital.id, is_active=True).first()
    
    return render_template('ministry/view_hospitals.html', hospitals=hospitals)


@app.route('/ministry/hospital/<hospital_id>')
def view_hospital_details(hospital_id):
    if 'user_type' not in session or session['user_type'] != 'ministry':
        return redirect(url_for('ministry_login'))

    ministry_id = session['ministry_id']

    # Get hospital (ensure it belongs to this ministry)
    hospital = Hospital.query.filter_by(id=hospital_id, ministry_id=ministry_id, is_active=True).first()
    if not hospital:
        flash('Hospital not found or access denied')
        return redirect(url_for('view_hospitals'))

    # Get hospital admin
    hospital_admin = HospitalAdmin.query.filter_by(hospital_id=hospital_id, is_active=True).first()

    # Get doctors and patients
    doctors = Doctor.query.filter_by(hospital_id=hospital_id, is_active=True).all()
    patients = Patient.query.filter_by(created_by_hospital=hospital_id, is_active=True).all()

    # Calculate age for each patient
    for patient in patients:
        if patient.date_of_birth:
            today = date.today()
            age = today.year - patient.date_of_birth.year
            if (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day):
                age -= 1
            patient.age = age  # add a new attribute for the template
        else:
            patient.age = None

    # Get recent encounters count
    recent_encounters_count = MedicalEncounter.query.filter_by(hospital_id=hospital_id).filter(
        MedicalEncounter.treatment_date >= datetime.now().date().replace(day=1)
    ).count()

    # Get audit logs
    audit_logs = AuditLog.query.filter_by(hospital_id=hospital_id).order_by(AuditLog.created_at.desc()).limit(10).all()

    return render_template(
        'ministry/hospital_details.html',
        hospital=hospital,
        hospital_admin=hospital_admin,
        doctors=doctors,
        patients=patients,
        recent_encounters_count=recent_encounters_count,
        audit_logs=audit_logs
    )

@app.route('/ministry/hospitals/<hospital_id>/toggle_status', methods=['POST'])
def toggle_hospital_status(hospital_id):
    if 'user_type' not in session or session['user_type'] != 'ministry':
        return redirect(url_for('ministry_login'))
    
    ministry_id = session['ministry_id']
    
    hospital = Hospital.query.filter_by(id=hospital_id, ministry_id=ministry_id).first()
    if hospital:
        hospital.is_active = not hospital.is_active
        hospital.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log action
        action = 'hospital_activated' if hospital.is_active else 'hospital_deactivated'
        log_audit_action(action, 'ministry', ministry_id, 
                       {'hospital_name': hospital.name}, 
                       hospital_id=hospital.id)
        
        status = 'activated' if hospital.is_active else 'deactivated'
        flash(f'Hospital {hospital.name} has been {status}')
    else:
        flash('Hospital not found')
    
    return redirect(url_for('view_hospitals'))

@app.route('/ministry/patients')
def view_all_patients():
    if 'user_type' not in session or session['user_type'] != 'ministry':
        return redirect(url_for('ministry_login'))
    
    ministry_id = session['ministry_id']
    
    # Get all patients from hospitals under this ministry
    patients = db.session.query(Patient, Hospital).join(Hospital, Patient.created_by_hospital == Hospital.id).filter(
        Hospital.ministry_id == ministry_id,
        Hospital.is_active == True,
        Patient.is_active == True
    ).all()
    
    return render_template('ministry/view_patients.html', patients=patients)

@app.route('/ministry/doctors')
def view_all_doctors():
    if 'user_type' not in session or session['user_type'] != 'ministry':
        return redirect(url_for('ministry_login'))
    
    ministry_id = session['ministry_id']
    
    # Get all doctors from hospitals under this ministry
    doctors = db.session.query(Doctor, Hospital).join(Hospital).filter(
        Hospital.ministry_id == ministry_id,
        Hospital.is_active == True,
        Doctor.is_active == True
    ).all()
    
    return render_template('ministry/view_doctors.html', doctors=doctors)

@app.route('/ministry/analytics')
def analytics():
    # 1. Auth check
    if session.get('user_type') != 'ministry':
        return redirect(url_for('ministry_login'))
    ministry_id = session['ministry_id']

    # 2. Monthly encounters over last 12 months
    monthly_encounters = (
        db.session
        .query(
            func.date_format(MedicalEncounter.treatment_date, '%Y-%m')
                .label('month'),
            func.count(MedicalEncounter.id).label('count')
        )
        .select_from(MedicalEncounter)
        .join(
            Hospital,
            MedicalEncounter.hospital_id == Hospital.id
        )
        .filter(
            Hospital.ministry_id == ministry_id,
            MedicalEncounter.treatment_date >= func.date_sub(
                func.curdate(),
                text('INTERVAL 12 MONTH')
            )
        )
        .group_by('month')
        .order_by('month')
        .all()
    )

    # 3. Hospital performance stats
    hospital_stats = (
        db.session
        .query(
            Hospital.name,
            func.count(MedicalEncounter.id).label('encounter_count'),
            func.count(func.distinct(Patient.id)).label('patient_count'),
            func.count(func.distinct(Doctor.id)).label('doctor_count')
        )
        .select_from(Hospital)
        .outerjoin(
            MedicalEncounter,
            MedicalEncounter.hospital_id == Hospital.id
        )
        .outerjoin(
            Patient,
            Patient.created_by_hospital == Hospital.id
        )
        .outerjoin(
            Doctor,
            MedicalEncounter.doctor_id == Doctor.id
        )
        .filter(
            Hospital.ministry_id == ministry_id,
            Hospital.is_active == True
        )
        .group_by(Hospital.id, Hospital.name)
        .all()
    )

    # 4. Render with both variables defined
    return render_template(
        'ministry/analytics.html',
        monthly_encounters=monthly_encounters,
        hospital_stats=hospital_stats
    )
@app.route('/ministry/audit_logs')
def view_audit_logs():
    if 'user_type' not in session or session['user_type'] != 'ministry':
        return redirect(url_for('ministry_login'))
    
    ministry_id = session['ministry_id']
    page = request.args.get('page', 1, type=int)
    
    # Get audit logs for hospitals under this ministry
    audit_logs = AuditLog.query.join(Hospital, AuditLog.hospital_id == Hospital.id, isouter=True).filter(
        db.or_(
            Hospital.ministry_id == ministry_id,
            AuditLog.acting_user_type == 'ministry'
        )
    ).order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('ministry/audit_logs.html', audit_logs=audit_logs)

@app.route('/logout')
def logout():
    if 'user_type' in session and session['user_type'] == 'ministry':
        log_audit_action('ministry_logout', 'ministry', session.get('ministry_id'))
    
    session.clear()
    return redirect(url_for('index'))

# Initialize database tables
with app.app_context():
    db.create_all()
    
    # Create default ministry if doesn't exist
    if not Ministry.query.first():
        default_ministry = Ministry(
            name='National Health Ministry',
            admin_username='ministry_admin',
            password_hash=generate_password_hash('admin123'),
            contact_info={
                'phone': '+94-11-1234567',
                'email': 'admin@health.gov.lk',
                'address': 'Colombo, Sri Lanka'
            }
        )
        db.session.add(default_ministry)
        db.session.commit()
        print("Default ministry created with username: ministry_admin, password: admin123")

if __name__ == '__main__':
    app.run(debug=True)