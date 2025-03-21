from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
import json
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from functools import wraps
from core.collections import users_collection



SECRET_KEY = os.getenv("HASH_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60   


@csrf_exempt
def create_user_view(request):
    """Register a new user in MongoDB."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            result = users_collection.insert_one(data)
            return JsonResponse(
                {"message": "User created", "id": str(result.inserted_id)},
                status=201,
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
        
def get_users_view(request):
    """Retrieve users from MongoDB, optionally filtered by role, and exclude the password field."""
    if request.method == "GET":
        try:
    
            # Get the role query parameter (if provided)
            role = request.GET.get("role")

            # Build the query
            query = {}
            if role:
                query["role"] = role

            # Retrieve users based on the query, excluding the password field
            users = list(users_collection.find(query, {"password": 0}))

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

            # Check if the username already exist
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

