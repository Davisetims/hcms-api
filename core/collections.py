from core.mongodb import db

users_collection = db["Users"]
medical_history_collection = db["MedicalHistory"]
prescriptions_collection = db["Prescriptions"]
appointments_collection = db["Appointments"]
medical_records_collection = db["MedicalRecords"]
billing_collection = db["Billing"]
test_results_collection = db["TestResults"]
messages_collection = db["Messages"]
consultations_collection = db ["Consultations"]