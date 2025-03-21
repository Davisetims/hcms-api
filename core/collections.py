from core.mongodb import db

users_collection = db["Users"]
medical_history_collection = db["MedicalHistory"]
prescriptions_collection = db["Prescriptions"]
appointments_collection = db["Appointments"]
