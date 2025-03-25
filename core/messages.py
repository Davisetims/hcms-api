from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
import json
from datetime import datetime
from core.collections import users_collection, messages_collection
from core.users import jwt_required

@jwt_required
@csrf_exempt
def send_message(request):
    if request.method == "POST":
        try:
            # Get the logged-in user's ID
            sender_id = request.user_id
            sender = users_collection.find_one({"_id": ObjectId(sender_id)})

            if not sender:
                return JsonResponse({"error": "Sender not found"}, status=404)

            sender_role = sender.get("role")

            # Parse request data
            data = json.loads(request.body)
            receiver_id = data.get("receiver_id")
            message_content = data.get("message")

            if not receiver_id or not message_content:
                return JsonResponse({"error": "Receiver ID and message are required"}, status=400)

            # Check if the receiver exists
            receiver = users_collection.find_one({"_id": ObjectId(receiver_id)})

            if not receiver:
                return JsonResponse({"error": "Receiver not found"}, status=404)

            receiver_role = receiver.get("role")

            # Define allowed messaging rules
            allowed_messaging = {
                "patient": ["doctor"],
                "doctor": ["patient", "admin", "receptionist"],
                "admin": ["doctor", "receptionist"],
                "receptionist": ["admin", "doctor"]
            }

            if receiver_role not in allowed_messaging.get(sender_role, []):
                return JsonResponse({"error": "You are not allowed to message this user"}, status=403)

            # Create the message document
            message = {
                "sender_id": ObjectId(sender_id),
                "receiver_id": ObjectId(receiver_id),
                "message": message_content,
                "sent_at": datetime.utcnow(),
                "status": "unread"
            }

            # Insert message into Messages collection
            result = messages_collection.insert_one(message)

            return JsonResponse({
                "message": "Message sent successfully",
                "message_id": str(result.inserted_id)
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@jwt_required
@csrf_exempt
def get_messages(request):
    try:
        # Get the logged-in user's ID
        user_id = request.user_id  # Assuming user_id is available in the request
        user = users_collection.find_one({"_id": ObjectId(user_id)})

        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        # Fetch messages where the logged-in user is the receiver
        messages = messages_collection.find({"receiver_id": ObjectId(user_id)}).sort("created_at", -1)

        # Format messages with sender details
        message_list = []
        for msg in messages:
            sender = users_collection.find_one(
                {"_id": ObjectId(msg["sender_id"])}, 
                {"personal_details.first_name": 1, "personal_details.last_name": 1, "role": 1}
            )

            message_list.append({
                "message_id": str(msg["_id"]),
                "sender": {
                    "first_name": sender.get("personal_details", {}).get("first_name", "Unknown"),
                    "last_name": sender.get("personal_details", {}).get("last_name", "Unknown"),
                    "role": sender.get("role", "Unknown")
                },
                "message": msg["message"],
                "timestamp": msg.get("sent_at", "Unknown")  # Fix: Provide default if missing
            })

        return JsonResponse({"messages": message_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)