import mongoengine as me

class PersonalDetails(me.EmbeddedDocument):
    first_name = me.StringField(required=True, max_length=100)
    last_name = me.StringField(required=True, max_length=100)
    age = me.IntField(required=True, min_value=0)
    gender = me.StringField(required=True, choices=["Male", "Female", "Other"])

class Contact(me.EmbeddedDocument):
    email = me.EmailField(required=True, unique=True)
    phone = me.ListField(me.StringField())  # Allows multiple phone numbers

class User(me.Document):
    role = me.StringField(required=True, choices=["doctor", "patient", 'admin', 'nurse', 'receptionist'])
    personal_details = me.EmbeddedDocumentField(PersonalDetails, required=True)
    contact = me.EmbeddedDocumentField(Contact, required=True)
    password = me.StringField(required=True, min_length= 8, max_length=1000)
    username = me.StringField(required=True, max_length=30)

    def __str__(self):
        return f"{self.personal_details.first_name} {self.personal_details.last_name} ({self.role})"
