
"""
-- Create database
CREATE DATABASE IF NOT EXISTS healthcare_management;
USE healthcare_management;

-- Hospitals table
CREATE TABLE hospitals (
    hospital_id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Doctors table
CREATE TABLE doctors (
    doctor_id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_id INT,
    doctor_name VARCHAR(255) NOT NULL,
    specialization VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE CASCADE
);

-- Patients table
CREATE TABLE patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_id INT,
    patient_name VARCHAR(255) NOT NULL,
    age INT,
    gender ENUM('Male', 'Female', 'Other'),
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE CASCADE
);

-- Medical records table (hospitals can manage, ministry cannot see)
CREATE TABLE medical_records (
    record_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT,
    doctor_id INT,
    diagnosis TEXT,
    prescription TEXT,
    notes TEXT,
    visit_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE CASCADE
);

-- Insert default ministry user (optional)
-- INSERT INTO ministry_users (username, password_hash) VALUES ('ministry', 'hashed_password');
"""

print("Healthcare Management System files created successfully!")
print("\nNext steps:")
print("1. Install dependencies: pip install -r requirements.txt")
print("2. Set up MySQL database using the schema.sql file")
print("3. Update database credentials in app.py")
print("4. Run the application: python app.py")
print("5. Access Ministry portal at: http://localhost:5000/ministry/login")
print("6. Ministry default credentials: username: ministry, password: admin123")