from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
import json
from datetime import datetime
from core.collections import users_collection , appointments_collection
from core.users import jwt_required


# Function for patients to book appointments
@jwt_required
@csrf_exempt
def book_appointment(request):
    if request.method == "POST":
        try:
            # Get the logged-in user's ID from the request
            user_id = request.user_id

            # Fetch the user from the database
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Check if the user is a patient
            if user.get("role") != "patient":
                return JsonResponse({"error": "Only patients can book appointments"}, status=403)

            # Parse the request body
            data = json.loads(request.body)
            doctor_id = data.get("doctor_id")
            appointment_date = data.get("appointment_date")
            notes = data.get("notes")

            # Validate required fields
            if not all([doctor_id, appointment_date]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            # Convert appointment_date to a datetime object
            try:
                appointment_date = datetime.fromisoformat(appointment_date)
            except ValueError:
                return JsonResponse({"error": "Invalid appointment_date format. Use ISO format (e.g., 2024-02-20T10:00:00Z)"}, status=400)

            # Create the appointment document
            appointment = {
                "patient_id": ObjectId(user_id),  # The logged-in patient's ID
                "doctor_id": ObjectId(doctor_id),
                "appointment_date": appointment_date,
                "status": "Scheduled",  # Default status
                "notes": notes if notes else ""  # Optional field
            }

            # Insert the appointment into the collection
            result = appointments_collection.insert_one(appointment)

            return JsonResponse({
                "message": "Appointment booked successfully",
                "appointment_id": str(result.inserted_id)
            }, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
@jwt_required
@csrf_exempt
def get_appointments(request):
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

            # Retrieve appointments based on the query
            appointments = list(appointments_collection.find(query))

            # Fetch personal details for each appointment
            for appointment in appointments:
                # Fetch patient details
                patient = users_collection.find_one({"_id": appointment["patient_id"]})
                if patient:
                    appointment["patient_details"] = {
                        "first_name": patient["personal_details"]["first_name"],
                        "last_name": patient["personal_details"]["last_name"],
                        "age": patient["personal_details"]["age"],
                        "gender": patient["personal_details"]["gender"]
                    }

                # Fetch doctor details (if the logged-in user is a patient)
                if role == "patient":
                    doctor = users_collection.find_one({"_id": appointment["doctor_id"]})
                    if doctor:
                        appointment["doctor_details"] = {
                            "first_name": doctor["personal_details"]["first_name"],
                            "last_name": doctor["personal_details"]["last_name"],
                            "specialization": doctor.get("specialization", "")
                        }

                # Remove IDs from the response
                appointment.pop("_id", None)
                appointment.pop("patient_id", None)
                appointment.pop("doctor_id", None)

            # Return the list of appointments with personal details
            return JsonResponse({"appointments": appointments}, status=200, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)