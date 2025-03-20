import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI')

DATABASE_NAME = "test"

# Initialize MongoDB Connection
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]  # Only specify the database, collections will be handled in views
