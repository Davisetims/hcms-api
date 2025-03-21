from django.urls import path
from .views import create_user_view, get_users_view, get_user_by_id_view,\
 register_user, authenticate_user, protected_view,post_medical_record, \
 post_medical_history

urlpatterns = [
    path("users/", create_user_view, name="create-user"),  # Register user (POST)
    path("all/users/", get_users_view, name="get-user"),  
    path('users/<str:user_id>/', get_user_by_id_view, name='get-user-by-id'),# Get user by ID (GET)
    path('register/', register_user, name='register'),
    path('login/', authenticate_user, name='login'),
    path('protected/', protected_view, name='protected'),
    path('medical-records/', post_medical_record, name='post-medical-record'),
    path('medical-history/', post_medical_history, name='post-medical-history'),
]

