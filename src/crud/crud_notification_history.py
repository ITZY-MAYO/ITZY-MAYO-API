from firebase_admin import firestore
from typing import Optional
from datetime import datetime

from src.models.notification_history import LastSentTimestamp

NOTIFICATION_HISTORY_COLLECTION = "notification_history"

async def get_notification_history(
    db: firestore.AsyncClient, user_id: str, schedule_id: str
) -> Optional[LastSentTimestamp]:
    """
    Retrieves the last sent timestamp for a user-schedule pair.
    Document ID is expected to be f'{user_id}_{schedule_id}'.
    """
    doc_id = f"{user_id}_{schedule_id}"
    doc_ref = db.collection(NOTIFICATION_HISTORY_COLLECTION).document(doc_id)
    doc_snapshot = await doc_ref.get()

    if not doc_snapshot.exists:
        return None

    data = doc_snapshot.to_dict()
    if not data or "last_sent_at" not in data:
        return None 
        
    # Firestore timestamps are automatically converted to datetime objects by the client library
    return LastSentTimestamp(last_sent_at=data["last_sent_at"])

async def update_notification_history(
    db: firestore.AsyncClient, user_id: str, schedule_id: str, timestamp: datetime
) -> None:
    """
    Updates or creates the last sent timestamp for a user-schedule pair.
    Document ID is f'{user_id}_{schedule_id}'.
    """
    doc_id = f"{user_id}_{schedule_id}"
    doc_ref = db.collection(NOTIFICATION_HISTORY_COLLECTION).document(doc_id)
    # Using set with merge=True would also work if there were other fields,
    # but for just one field, set is fine and will create/overwrite.
    await doc_ref.set({"last_sent_at": timestamp}) 