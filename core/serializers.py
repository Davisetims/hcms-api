from rest_framework import serializers
from .models import User, PersonalDetails, Contact

class PersonalDetailsSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField(min_value=0)
    gender = serializers.ChoiceField(choices=["Male", "Female", "Other"])

class ContactSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone = serializers.ListField(child=serializers.CharField())

class UserSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)  # MongoDB uses `_id` which is a string
    role = serializers.ChoiceField(choices=["doctor", "patient", "admin", "nurse", "receptionist"])
    personal_details = PersonalDetailsSerializer()
    contact = ContactSerializer()
    username = serializers.CharField(max_length=30)
    password = serializers.CharField(write_only=True, min_length=8)

    def create(self, validated_data):
        """Handle creation of User instance with embedded documents."""
        personal_details_data = validated_data.pop("personal_details")
        contact_data = validated_data.pop("contact")

        personal_details = PersonalDetails(**personal_details_data)
        contact = Contact(**contact_data)

        user = User(**validated_data, personal_details=personal_details, contact=contact)
        user.save()
        return user

    def update(self, instance, validated_data):
        """Handle updates for User instance."""
        instance.role = validated_data.get("role", instance.role)
        instance.username = validated_data.get("username", instance.username)
        if "password" in validated_data:
            instance.password = validated_data["password"]

        if "personal_details" in validated_data:
            for attr, value in validated_data["personal_details"].items():
                setattr(instance.personal_details, attr, value)

        if "contact" in validated_data:
            for attr, value in validated_data["contact"].items():
                setattr(instance.contact, attr, value)

        instance.save()
        return instance
