from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from bson import ObjectId
import json
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from functools import wraps
from core.mongodb import db

SECRET_KEY = os.getenv("HASH_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60   

@method_decorator(csrf_exempt, name="dispatch")
class MongoClassView(View):
    def post(self, request, *args, **kwargs):
        try:
            # Example mapped data
            mapped_data = {"name": "John"}

            # Insert into MongoDB
            db["patients"].insert_one(mapped_data)

            return JsonResponse({"message": "Data inserted successfully"}, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def create_user_view(request):
    """Register a new user in MongoDB."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            users_collection = db["Users"]
            result = users_collection.insert_one(data)
            return JsonResponse(
                {"message": "User created", "id": str(result.inserted_id)},
                status=201,
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
        
def get_users_view(request):
    """Retrieve all users from MongoDB."""
    if request.method == "GET":
        try:
            # Access the "Users" collection
            users_collection = db["Users"]

            # Retrieve all users from the collection
            users = list(users_collection.find({}))

            # Convert ObjectId to string for JSON serialization
            for user in users:
                user["_id"] = str(user["_id"])

            # Return the list of users as a JSON response
            return JsonResponse({"users": users}, status=200, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)

def get_user_by_id_view(request, user_id):
    """Retrieve a user by their ID from MongoDB."""
    if request.method == "GET":
        try:
            # Access the "Users" collection
            users_collection = db["Users"]

            # Convert the user_id string to ObjectId
            user_id = ObjectId(user_id)

            # Find the user by their _id
            user = users_collection.find_one({"_id": user_id})

            # If the user is not found, return a 404 error
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Convert ObjectId to string for JSON serialization
            user["_id"] = str(user["_id"])

            # Return the user as a JSON response
            return JsonResponse({"user": user}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
def jwt_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)

        if "error" in payload:
            return JsonResponse({"error": payload["error"]}, status=401)

        request.user_id = payload["sub"]
        return view_func(request, *args, **kwargs)
    return wrapper


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}

# Register a new user
@jwt_required
@csrf_exempt
def register_user(request):
    if request.method == "POST":
        try:
            # Parse the request body
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")
            role = data.get("role")
            personal_details = data.get("personal_details")
            contact = data.get("contact")

            # Validate required fields
            if not all([username, password, role, personal_details, contact]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            # Check if the username already exists
            users_collection = db["Users"]
            if users_collection.find_one({"username": username}):
                return JsonResponse({"error": "Username already exists"}, status=400)

            # Hash the password
            hashed_password = hash_password(password)

            # Create the user document
            user = {
                "username": username,
                "password": hashed_password,
                "role": role,
                "personal_details": personal_details,
                "contact": contact,
            }

            # Insert the user into the database
            result = users_collection.insert_one(user)

            return JsonResponse({
                "message": "User registered successfully",
                "user_id": str(result.inserted_id)
            }, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)

# Authenticate a user and generate JWT
@csrf_exempt
def authenticate_user(request):
    if request.method == "POST":
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        users_collection = db["Users"]

        # Find the user by username
        user = users_collection.find_one({"username": username})
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        # Verify the password
        if not verify_password(password, user["password"]):
            return JsonResponse({"error": "Incorrect password"}, status=401)

        # Generate the access token
        access_token = create_access_token({"sub": str(user["_id"])})

        # Prepare the user details to return
        user_details = {
            "user_id": str(user["_id"]),
            "username": user["username"],
            "personal_details": user.get("personal_details", {}),
            "contact": user.get("contact", {}),
            "role": user.get("role", ""),
            # Add other fields as needed
        }

        # Return the access token and user details
        return JsonResponse({
            "access_token": access_token,
            "user": user_details
        }, status=200)


# Protected route
@jwt_required
def protected_view(request):
    users_collection = db["Users"]
    user_id = request.user_id
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    return JsonResponse({"message": f"Hello, {user['username']}!"})

@jwt_required
@csrf_exempt
def post_medical_record(request):
    medical_records_collection = db["MedicalRecords"]
    users_collection = db["Users"]
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
