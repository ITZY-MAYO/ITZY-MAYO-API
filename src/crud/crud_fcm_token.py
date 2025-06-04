from firebase_admin import firestore
from typing import Optional

from src.models.fcm_token import FCMTokenInDB, FCMToken # Import both

FCM_TOKENS_COLLECTION = "fcm_token"  # As used in existing locations.py

async def get_fcm_token_by_user_id(
    db: firestore.AsyncClient, firebase_userid: str
) -> Optional[FCMTokenInDB]:
    """
    Retrieves an FCM token for a given firebase_userid.
    The firebase_userid is the document ID in the fcm_tokens collection.
    """
    doc_ref = db.collection(FCM_TOKENS_COLLECTION).document(firebase_userid)
    doc_snapshot = await doc_ref.get()

    if not doc_snapshot.exists:
        return None

    token_data = doc_snapshot.to_dict()
    if not token_data or "token" not in token_data:
        # Log or handle missing token field if necessary
        return None
    
    # The document ID is the firebase_userid
    return FCMTokenInDB(user_id=doc_snapshot.id, token=token_data["token"]) 