from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
import json
from datetime import datetime
from core.collections import users_collection ,billing_collection
from core.users import jwt_required

@jwt_required
@csrf_exempt
def manage_billing(request):
    if request.method == "POST":
        try:
            # Get the logged-in user's ID from the request
            user_id = request.user_id
            user = users_collection.find_one({"_id": ObjectId(user_id)})

            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            user_role = user.get("role")

            # Parse request data
            data = json.loads(request.body)
            patient_id = data.get("patient_id")
            total_amount = data.get("total_amount")
            services = data.get("services")
            payment_method = data.get("payment_method")
            billing_id = data.get("billing_id")

            if user_role in ["receptionist", "admin"]:
                # Receptionist/Admin can create a billing record
                if not all([patient_id, total_amount, services]):
                    return JsonResponse({"error": "Missing required fields for billing"}, status=400)

                billing = {
                    "patient_id": ObjectId(patient_id),
                    "total_amount": total_amount,
                    "payment_status": "Unpaid",
                    "services": services,
                    "created_at": datetime.utcnow()
                }
                result = billing_collection.insert_one(billing)
                return JsonResponse({"message": "Billing added successfully", "billing_id": str(result.inserted_id)}, status=201)

            elif user_role == "patient":
                # Patient can only update payment status
                if not all([billing_id, payment_method]):
                    return JsonResponse({"error": "Billing ID and Payment method are required"}, status=400)

                billing = billing_collection.find_one({"_id": ObjectId(billing_id), "patient_id": ObjectId(user_id)})
                if not billing:
                    return JsonResponse({"error": "Billing record not found"}, status=404)

                billing_collection.update_one(
                    {"_id": ObjectId(billing_id)},
                    {"$set": {"payment_status": "Paid", "payment_method": payment_method, "paid_at": datetime.utcnow()}}
                )
                return JsonResponse({"message": "Payment successful"}, status=200)

            else:
                return JsonResponse({"error": "Unauthorized action"}, status=403)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@jwt_required
@csrf_exempt

def get_user_bills(request):
    if request.method == "GET":
        try:
            # Get logged-in user's ID and role
            user_id = request.user_id
            user = users_collection.find_one({"_id": ObjectId(user_id)})

            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            user_role = user.get("role")
            query = {}

            # Define the query based on user role
            if user_role == "receptionist":
                query["receptionist_id"] = ObjectId(user_id)  # Receptionist sees bills they created
            elif user_role == "patient":
                query["patient_id"] = ObjectId(user_id)  # Patient sees only their own bills
            elif user_role == "admin":
                query = {}  # Admin sees all bills
            else:
                return JsonResponse({"error": "Unauthorized access"}, status=403)

            # Fetch bills from the database
            bills = list(billing_collection.find(query))

            # Format response
            formatted_bills = []
            for bill in bills:
                # Fetch patient details
                patient = users_collection.find_one({"_id": bill["patient_id"]})
                receptionist = users_collection.find_one({"_id": bill.get("receptionist_id")})

                bill_data = {
                    "_id": str(bill["_id"]),
                    "total_amount": bill["total_amount"],
                    "payment_status": bill["payment_status"],
                    "services": bill["services"],
                    "created_at": bill["created_at"].isoformat(),
                }

                if user_role == "patient" and receptionist:
                    # Patient sees who billed them
                    bill_data["billed_by"] = {
                        "first_name": receptionist["personal_details"]["first_name"],
                        "last_name": receptionist["personal_details"]["last_name"],
                        "email": receptionist["contact"]["email"],
                        "phone": receptionist["contact"]["phone"]
                    }
                elif user_role == "receptionist" and patient:
                    # Receptionist sees patient details
                    bill_data["billed_for"] = f"{patient['personal_details']['first_name']} {patient['personal_details']['last_name']}"

                formatted_bills.append(bill_data)

            return JsonResponse({"bills": formatted_bills}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)
