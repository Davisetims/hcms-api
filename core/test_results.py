from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
import json
from datetime import datetime
from core.collections import users_collection ,test_results_collection
from core.users import jwt_required

@csrf_exempt
@jwt_required
def post_test_result(request):
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
                return JsonResponse({"error": "Only doctors can post test results"}, status=403)

            # Parse the request body
            data = json.loads(request.body)

            medical_record_id = data.get("medical_record_id")
            patient_id = data.get("patient_id")
            test_name = data.get("test_name")
            test_date = data.get("test_date")  # Expected in ISO format
            results = data.get("results")
            remarks = data.get("remarks", "")

            # Validate required fields
            if not all([medical_record_id, patient_id, test_name, test_date, results]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            # Convert test_date to datetime object
            try:
                test_date = datetime.fromisoformat(test_date)
            except ValueError:
                return JsonResponse({"error": "Invalid date format"}, status=400)

            # Create the test result document
            test_result = {
                "medical_record_id": ObjectId(medical_record_id),
                "patient_id": ObjectId(patient_id),
                "doctor_id": ObjectId(user_id),
                "test_name": test_name,
                "test_date": test_date,
                "results": results,
                "status": "Completed",
                "remarks": remarks,
                "uploaded_by": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            }

            # Insert into the test results collection
            result = test_results_collection.insert_one(test_result)

            return JsonResponse({
                "message": "Test result posted successfully",
                "test_result_id": str(result.inserted_id)
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
@jwt_required
@csrf_exempt
def get_test_results(request):
    try:
        # Get the logged-in user's ID and role
        user_id = request.user_id
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        user_role = user.get("role")

        # Define query filter based on role
        query = {}
        if user_role == "doctor":
            query["doctor_id"] = ObjectId(user_id)  # Doctor sees only the tests they uploaded
        elif user_role == "patient":
            query["patient_id"] = ObjectId(user_id)  # Patient sees only their own results
        else:
            return JsonResponse({"error": "Unauthorized access"}, status=403)

        # Fetch test results
        test_results = list(test_results_collection.find(query))

        results_list = []
        for result in test_results:
            result_data = {
                "_id": str(result["_id"]),
                "medical_record_id": str(result["medical_record_id"]),
                "test_name": result["test_name"],
                "test_date": result["test_date"].isoformat() if "test_date" in result else None,
                "results": result["results"],
                "status": result["status"],
                "remarks": result["remarks"]
            }

            # Fetch patient details if doctor is logged in
            if user_role == "doctor":
                patient = users_collection.find_one({"_id": result["patient_id"]})
                if patient:
                    result_data["patient_details"] = {
                        "first_name": patient["personal_details"]["first_name"],
                        "last_name": patient["personal_details"]["last_name"],
                        "age": patient["personal_details"]["age"],
                        "gender": patient["personal_details"]["gender"]
                    }

            # Fetch doctor details if patient is logged in
            if user_role == "patient":
                doctor = users_collection.find_one({"_id": result["doctor_id"]})
                if doctor:
                    result_data["uploaded_by"] = f"Dr.{doctor['personal_details']['first_name']} {doctor['personal_details']['last_name']}"

            results_list.append(result_data)

        return JsonResponse({"test_results": results_list}, status=200)
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
