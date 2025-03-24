from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
import json
from datetime import datetime
from core.collections import users_collection ,db, medical_history_collection, \
medical_records_collection
from core.users import jwt_required

@csrf_exempt
@jwt_required
def post_medical_record(request):
    medical_records_collection = db["MedicalRecords"]
    if request.method == "POST":
        try:
            # Get the logged-in user's ID from the request
            user_id = request.user_id

            # Fetch the user from the database
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Check if the user is a doctor
            if user.get("role") != "doctor":
                return JsonResponse({"error": "Only doctors can post medical records"}, status=403)

            # Parse the request body
            data = json.loads(request.body)
            patient_id = data.get("patient_id")
            record_type = data.get("record_type")
            description = data.get("description")
            file_url = data.get("file_url")

            # Validate required fields
            if not all([patient_id, record_type, description, file_url]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            # Create the medical record
            medical_record = {
                "patient_id": ObjectId(patient_id),
                "doctor_id": ObjectId(user_id),  # The logged-in doctor's ID
                "record_type": record_type,
                "description": description,
                "file_url": file_url,
                "uploaded_at": datetime.utcnow()
            }

            # Insert the record into the MedicalRecords collection
            result = medical_records_collection.insert_one(medical_record)

            return JsonResponse({
                "message": "Medical record created successfully",
                "record_id": str(result.inserted_id)
            }, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


# Function to post medical history (only for doctors)
@jwt_required
@csrf_exempt
def post_medical_history(request):
    if request.method == "POST":
        try:
        
            # Get the logged-in user's ID from the request
            user_id = request.user_id

            # Fetch the user from the database
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Check if the user is a doctor
            if user.get("role") != "doctor":
                return JsonResponse({"error": "Only doctors can post medical history"}, status=403)

            # Parse the request body
            data = json.loads(request.body)
            patient_id = data.get("patient_id")
            conditions = data.get("conditions")
            documents = data.get("documents")

            # Validate required fields
            if not all([patient_id, conditions, documents]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            # Create the medical history document
            medical_history = {
                "patient_id": ObjectId(patient_id),
                "diagnosed_by": ObjectId(user_id),  # The logged-in doctor's ID
                "conditions": conditions,
                "documents": documents,
                "registered_at": datetime.utcnow()
            }

            # Insert the medical history into the collection
            result = medical_history_collection.insert_one(medical_history)

            return JsonResponse({
                "message": "Medical history created successfully",
                "medical_history_id": str(result.inserted_id)
            }, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


@jwt_required
def get_medical_records(request):
    if request.method == "GET":
        try:
            # Get the logged-in user's ID from the request
            user_id = request.user_id

            # Fetch the user from the database
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Determine the user's role
            role = user.get("role")

            # Build the query based on the user's role
            if role == "doctor":
                query = {"doctor_id": ObjectId(user_id)}
            elif role == "patient":
                query = {"patient_id": ObjectId(user_id)}
            else:
                return JsonResponse({"error": "Unauthorized access"}, status=403)

            # Retrieve medical records based on the query
            medical_records = list(medical_records_collection.find(query))

            # Fetch personal details for each medical record
            for record in medical_records:
                # Fetch patient details
                patient = users_collection.find_one({"_id": record["patient_id"]})
                if patient:
                    record["patient_details"] = {
                        "first_name": patient["personal_details"]["first_name"],
                        "last_name": patient["personal_details"]["last_name"],
                        "age": patient["personal_details"]["age"],
                        "gender": patient["personal_details"]["gender"]
                    }

                # Fetch doctor details (if the logged-in user is a patient)
                if role == "patient":
                    doctor = users_collection.find_one({"_id": record["doctor_id"]})
                    if doctor:
                        record["doctor_details"] = {
                            "first_name": doctor["personal_details"]["first_name"],
                            "last_name": doctor["personal_details"]["last_name"],
                            "specialization": doctor.get("specialization", "")
                        }

                # Convert ObjectId to string for JSON serialization
                record["_id"] = str(record["_id"])
                record["patient_id"] = str(record["patient_id"])
                record["doctor_id"] = str(record["doctor_id"])

            # Return the list of medical records with personal details
            return JsonResponse({"medical_records": medical_records}, status=200, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
    