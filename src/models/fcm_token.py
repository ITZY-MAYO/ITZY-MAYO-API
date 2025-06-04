from pydantic import BaseModel

class FCMToken(BaseModel):
    # The document ID in Firestore is the firebase_userid.
    # This model represents the fields within that document.
    token: str

class FCMTokenInDB(FCMToken):
    # If you want to include the user_id (document_id) in the model explicitly after fetching
    user_id: str # Represents the document ID from Firestore
    pass 