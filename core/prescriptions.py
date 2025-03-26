from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
import json
from datetime import datetime
from core.collections import users_collection ,prescriptions_collection
from core.users import jwt_required





# Function for doctors to post prescriptions
@jwt_required
@csrf_exempt
def post_prescription(request):
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
                return JsonResponse({"error": "Only doctors can post prescriptions"}, status=403)

            # Parse the request body
            data = json.loads(request.body)
            patient_id = data.get("patient_id")
            medications = data.get("medications")

            # Validate required fields
            if not all([patient_id, medications]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            # Create the prescription document
            prescription = {
                "patient_id": ObjectId(patient_id),
                "doctor_id": ObjectId(user_id),  # The logged-in doctor's ID
                "prescribed_date": datetime.utcnow(),
                "medications": medications
            }

            # Insert the prescription into the collection
            result = prescriptions_collection.insert_one(prescription)

            return JsonResponse({
                "message": "Prescription created successfully",
                "prescription_id": str(result.inserted_id)
            }, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
    

# Function for patients to view their prescriptions
@jwt_required
@csrf_exempt

def get_patient_prescriptions(request):
    if request.method == "GET":
        try:
            # Get the logged-in user's ID from the request
            user_id = request.user_id

            # Fetch the user from the database
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Check if the user is a patient
            if user.get("role") != "patient":
                return JsonResponse({"error": "Only patients can view their prescriptions"}, status=403)

            # Retrieve prescriptions for the logged-in patient
            prescriptions = list(prescriptions_collection.find({"patient_id": ObjectId(user_id)}))

            # Convert ObjectId to string for JSON serialization and fetch doctor's name
            for prescription in prescriptions:
                prescription["_id"] = str(prescription["_id"])

                # Fetch the doctor's details
                doctor = users_collection.find_one({"_id": ObjectId(prescription["doctor_id"])})
                if doctor:
                    prescription["doctor_first_name"] = doctor["personal_details"]["first_name"]
                    prescription["doctor_last_name"] = doctor["personal_details"]["last_name"]
                
                # Remove patient_id and doctor_id from response
                prescription.pop("patient_id", None)
                prescription.pop("doctor_id", None)

            # Return the list of prescriptions as a JSON response
            return JsonResponse({"prescriptions": prescriptions}, status=200, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)