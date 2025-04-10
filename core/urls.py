from django.urls import path
from core.users import create_user_view,get_users_view, get_user_by_id_view,\
register_user, authenticate_user
from core.medical_records import  post_medical_record,post_medical_history , get_medical_records
from core.prescriptions import post_prescription, get_patient_prescriptions
from core.appointments import book_appointment, get_appointments ,update_appointment,\
cancel_appointment
from core.billings import manage_billing, get_user_bills
from core.test_results import post_test_result, get_test_results
from core.messages import send_message, get_messages
from core.consultations import post_meeting_link, get_meeting_details, get_user_consultations
 

urlpatterns = [
    path("users/", create_user_view, name="create-user"),  # Register user (POST)
    path("all/users/", get_users_view, name="get-user"),  
    path('users/<str:user_id>/', get_user_by_id_view, name='get-user-by-id'),# Get user by ID (GET)
    path('register/user/', register_user, name='register'),
    path('login/', authenticate_user, name='login'),
    path('post/medical-records/', post_medical_record, name='post-medical-record'),
    path('get/user/medical-records/', get_medical_records, name='get-medical-record'),
    path('medical-history/', post_medical_history, name='post-medical-history'),
    path('post/prescriptions/', post_prescription, name='post-prescription'),
    path('get/patient/prescriptions/', get_patient_prescriptions, name='get-patient-prescriptions'),
    path('book/appointments/', book_appointment, name='book-appointment'),
    path('get/user/appointments/', get_appointments, name='get-appointments'),
    path('update/user/appointments/', update_appointment, name='update-appointments'),
    path('cancel/appointments/<str:appointment_id>/', cancel_appointment, name='cancel-appointment'),
    path('post/bill/', manage_billing, name='invoicing'),
    path('get/user/bills/', get_user_bills, name='get-invoices'),
    path('post/test/results/', post_test_result, name='test-results'),
    path('get/user/test/results/', get_test_results, name='get-test-results'),
    path('send/message/', send_message, name='send-message'),
    path('get/message/', get_messages, name='get-message'),
    path('post/meeting/link/', post_meeting_link, name='meeting'),
    path('get/meeting/link/<consultation_id>/', get_meeting_details, name='get-meeting'),
    path('get/meeting/link/', get_user_consultations, name='get-meeting'),



]

