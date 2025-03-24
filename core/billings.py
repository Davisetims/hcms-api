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

            # Parse request data
            data = json.loads(request.body)
            patient_id = data.get("patient_id")
            total_amount = data.get("total_amount")
            services = data.get("services")
            payment_method = data.get("payment_method")

            # Validate required fields
            if not patient_id:
                return JsonResponse({"error": "Patient ID is required"}, status=400)

            if user.get("role") == "admin":
                # Admin can create a new billing record with 'Unpaid' status
                if not all([total_amount, services]):
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
            
            elif user.get("role") == "patient":
                # Patient can only update payment status
                if not payment_method:
                    return JsonResponse({"error": "Payment method is required"}, status=400)
                
                billing_id = data.get("billing_id")
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
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
