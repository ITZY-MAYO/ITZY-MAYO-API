from firebase_admin import firestore
from google.cloud.firestore_v1 import GeoPoint, FieldFilter
from typing import List, Optional
from datetime import datetime # Ensure datetime is imported

from src.models.schedule import Schedule # Only Schedule is needed for read operations

SCHEDULES_COLLECTION = "schedule"

async def get_schedule(
    db: firestore.AsyncClient, schedule_id: str
) -> Optional[Schedule]:
    doc_ref = db.collection(SCHEDULES_COLLECTION).document(schedule_id)
    doc_snapshot = await doc_ref.get()

    if not doc_snapshot.exists:
        return None

    schedule_db_data = doc_snapshot.to_dict()
    if not schedule_db_data: return None

    schedule_db_data["id"] = doc_snapshot.id

    retrieved_geopoint = schedule_db_data.pop("geoPoint", None)
    if isinstance(retrieved_geopoint, GeoPoint):
        schedule_db_data["latitude"] = retrieved_geopoint.latitude
        schedule_db_data["longitude"] = retrieved_geopoint.longitude
    else:
        schedule_db_data["latitude"] = None
        schedule_db_data["longitude"] = None
    
    return Schedule(**schedule_db_data)

async def get_schedules_by_user(
    db: firestore.AsyncClient, firebase_userid: str
) -> List[Schedule]:
    schedules_list = []
    query = db.collection(SCHEDULES_COLLECTION).where(
        filter=FieldFilter("userId", "==", firebase_userid)
    )
    docs_stream = query.stream()

    async for doc_snapshot in docs_stream:
        if doc_snapshot.exists:
            schedule_db_data = doc_snapshot.to_dict()
            if not schedule_db_data: continue

            schedule_db_data["id"] = doc_snapshot.id
            retrieved_geopoint = schedule_db_data.pop("geoPoint", None)
            if isinstance(retrieved_geopoint, GeoPoint):
                schedule_db_data["latitude"] = retrieved_geopoint.latitude
                schedule_db_data["longitude"] = retrieved_geopoint.longitude
            else:
                schedule_db_data["latitude"] = None
                schedule_db_data["longitude"] = None

            schedules_list.append(Schedule(**schedule_db_data))
    return schedules_list
