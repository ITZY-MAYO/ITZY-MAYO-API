from pydantic import BaseModel, Field
from datetime import datetime

class NotificationHistoryBase(BaseModel):
    user_id: str = Field(..., description="Firebase User ID")
    schedule_id: str = Field(..., description="ID of the schedule for which notification was sent")
    last_sent_at: datetime = Field(..., description="Timestamp of the last notification sent")

class NotificationHistoryCreate(NotificationHistoryBase):
    pass

class NotificationHistoryInDB(NotificationHistoryBase):
    # In Firestore, the document ID might be a composite key like user_id + "_" + schedule_id
    # Or, user_id and schedule_id can be fields if you prefer auto-generated document IDs.
    # For this model, we assume user_id and schedule_id are fields, and Firestore might have its own doc ID.
    # If using composite ID, this model might not need a separate 'id' field unless it represents that composite key.
    pass

# Simpler model if document ID is composite and fields are just last_sent_at
class LastSentTimestamp(BaseModel):
    last_sent_at: datetime 