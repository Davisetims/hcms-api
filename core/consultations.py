from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
import json
from datetime import datetime
from core.collections import users_collection , consultations_collection
from core.users import jwt_required

@jwt_required
@csrf_exempt
def post_meeting_link(request):
    if request.method == "POST":
        try:
            # Get the logged-in user's ID from the request
            user_id = request.user_id

            # Fetch the user from the MongoDB database
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Check if the user is a doctor
            if user.get("role") != "doctor":
                return JsonResponse({"error": "Only doctors can upload meeting links"}, status=403)

            # Parse the request body
            data = json.loads(request.body)

            patient_id = data.get("patient_id")
            meeting_link = data.get("meeting_link")
            consultation_date = data.get("consultation_date")  # Expected in ISO format

            # Validate required fields
            if not all([patient_id, meeting_link, consultation_date]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            # Convert consultation_date to datetime object
            try:
                consultation_date = datetime.fromisoformat(consultation_date)
            except ValueError:
                return JsonResponse({"error": "Invalid date format"}, status=400)

            # Create the consultation document
            consultation = {
                "doctor_id": ObjectId(user_id),
                "patient_id": ObjectId(patient_id),
                "meeting_link": meeting_link,
                "consultation_date": consultation_date,
                "status": "Scheduled",
                "uploaded_by": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                "created_at": datetime.utcnow()
            }

            # Insert into the consultations collection
            result = consultations_collection.insert_one(consultation)

            return JsonResponse({
                "message": "Meeting link uploaded successfully",
                "consultation_id": str(result.inserted_id)
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
@jwt_required
@csrf_exempt
def get_meeting_details(request, consultation_id):
    try:
        # Get the logged-in user's ID
        user_id = request.user_id  
        if not user_id:
            return JsonResponse({"error": "User not authenticated"}, status=401)
        
        # Validate consultation_id format
        if not ObjectId.is_valid(consultation_id):
            return JsonResponse({"error": "Invalid consultation ID format"}, status=400)

        # Fetch user details
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        user_role = user.get("role")
        if user_role not in ["doctor", "patient"]:
            return JsonResponse({"error": "Unauthorized role"}, status=403)

        # Fetch the consultation from MongoDB
        consultation = consultations_collection.find_one({"_id": ObjectId(consultation_id)})
        if not consultation:
            return JsonResponse({"error": "Consultation not found"}, status=404)

        # Check if user is part of this consultation
        doctor_id = consultation.get("doctor_id")
        patient_id = consultation.get("patient_id")
        
        if not (ObjectId(user_id) == doctor_id or ObjectId(user_id) == patient_id):
            return JsonResponse({"error": "Unauthorized access to this consultation"}, status=403)

        # Prepare base meeting details
        meeting_data = {
            "_id": str(consultation["_id"]),
            "meeting_link": consultation.get("meeting_link"),
            "consultation_date": consultation.get("consultation_date", consultation.get("created_at")),
            "status": consultation.get("status"),
            "notes": consultation.get("notes"),
        }

        # Format date if it exists
        if meeting_data["consultation_date"] and isinstance(meeting_data["consultation_date"], datetime):
            meeting_data["consultation_date"] = meeting_data["consultation_date"].isoformat()

        # Add participant details based on role
        if user_role == "doctor":
            patient = users_collection.find_one({"_id": patient_id})
            if patient:
                meeting_data["patient_details"] = {
                    "first_name": patient.get("personal_details", {}).get("first_name"),
                    "last_name": patient.get("personal_details", {}).get("last_name"),
                    "age": patient.get("personal_details", {}).get("age"),
                    "gender": patient.get("personal_details", {}).get("gender"),
                    "email": patient.get("personal_details", {}).get("email"),
                    "phone": patient.get("personal_details", {}).get("phone")
                }
        else:  # user is patient
            doctor = users_collection.find_one({"_id": doctor_id})
            if doctor:
                meeting_data["doctor_details"] = {
                    "first_name": doctor.get("personal_details", {}).get("first_name"),
                    "last_name": doctor.get("personal_details", {}).get("last_name"),
                    "specialization": doctor.get("specialization"),
                    "email": doctor.get("personal_details", {}).get("email"),
                    "phone": doctor.get("personal_details", {}).get("phone"),
                    "license_number": doctor.get("license_number")
                }

        return JsonResponse(meeting_data, status=200)

    except Exception as e:
        return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)
    
@jwt_required
@csrf_exempt
def get_user_consultations(request):
    try:
        # 1. Get and validate user ID
        user_id = request.user_id  
        if not user_id:
            return JsonResponse({"error": "Authentication required"}, status=401)

        if not ObjectId.is_valid(user_id):
            return JsonResponse({"error": "Invalid user ID format"}, status=400)

        # 2. Get user document and role
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        user_role = user.get("role")
        if user_role not in ["doctor", "patient"]:
            return JsonResponse({"error": "Unauthorized role"}, status=403)

        # 3. Build query based on user role
        query = {"doctor_id": ObjectId(user_id)} if user_role == "doctor" else {"patient_id": ObjectId(user_id)}

        # 4. Get all consultations
        consultations = list(consultations_collection.find(query).sort("consultation_date", -1))

        # 5. Process and format the results
        formatted_consultations = []
        for consultation in consultations:
            # Get the other participant's details
            other_participant_id = consultation["patient_id"] if user_role == "doctor" else consultation["doctor_id"]
            other_user = users_collection.find_one({"_id": other_participant_id})

            formatted_consultations.append({
                "id": str(consultation["_id"]),
                "date": consultation.get("consultation_date", consultation.get("created_at")).isoformat(),
                "status": consultation.get("status", "scheduled"),
                "meeting_link": consultation.get("meeting_link", ""),
                "participant": {
                    "name": f"{other_user['personal_details']['first_name']} {other_user['personal_details']['last_name']}" if other_user else "Unknown",
                    "role": "patient" if user_role == "doctor" else "doctor",
                    "specialization": other_user.get("specialization", "") if user_role == "patient" and other_user else ""
                },
                "notes": consultation.get("notes", "")[:100]  # Truncate long notes
            })

        # 6. Return all consultations
        return JsonResponse({"consultations": formatted_consultations}, status=200)

    except Exception as e:
        return JsonResponse({"error": "Internal server error"}, status=500)