from firebase_admin import firestore
from google.cloud.firestore_v1 import GeoPoint, FieldFilter  # For creating GeoPoint instances and FieldFilter
from typing import (
    List,
    Optional,
)  # For older Python, use List & Optional. For 3.9+, use list & | None
from datetime import datetime # Ensure datetime is imported

from src.models.schedule import Schedule, ScheduleCreate, ScheduleUpdate
import logging

logger = logging.getLogger(__name__)

# Firestore collection name
SCHEDULES_COLLECTION = "schedule"


async def create_schedule(
    db: firestore.AsyncClient, schedule_data: ScheduleCreate
) -> Schedule:
    """
    Creates a new schedule document in Firestore.
    Converts latitude/longitude to GeoPoint for storage.
    """
    doc_ref = db.collection(SCHEDULES_COLLECTION).document()  # Auto-generate ID

    # Manually construct the dictionary for Firestore using Pydantic model attribute names
    # Pydantic's aliases are for how data is *loaded* into the model or *dumped with by_alias=True*.
    # Here, we are constructing the Firestore document from the Pydantic model attributes.
    firestore_data = {
        "title": schedule_data.name, # Pydantic's .name maps to Firestore's "title"
        "userId": schedule_data.firebase_userid, # Pydantic's .firebase_userid maps to "userId"
        "content": schedule_data.description, # Pydantic's .description maps to "content"
        "geoPoint": GeoPoint(schedule_data.latitude, schedule_data.longitude), # Store as geoPoint
        "datetime": schedule_data.schedule_datetime # Pydantic's .schedule_datetime to "datetime"
    }
    # Note: The model_dump(by_alias=True) approach could also work if structured carefully.
    # e.g., temp_dict = schedule_data.model_dump(by_alias=True)
    # temp_dict["geoPoint"] = GeoPoint(schedule_data.latitude, schedule_data.longitude)
    # del temp_dict["latitude"]
    # del temp_dict["longitude"]
    # await doc_ref.set(temp_dict)

    await doc_ref.set(firestore_data)

    # Construct the response model. Since Schedule model has populate_by_name=True and aliases,
    # we can pass the original Pydantic model attributes along with the new ID.
    # Or, pass the firestore_data and ID, and Pydantic will map using aliases.
    response_data_dict = firestore_data.copy() # Start with what was saved
    response_data_dict["id"] = doc_ref.id
    # Add latitude and longitude back for the response model as it expects them directly
    response_data_dict["latitude"] = schedule_data.latitude
    response_data_dict["longitude"] = schedule_data.longitude
    # Pydantic will use aliases: title -> name, userId -> firebase_userid, content -> description, datetime -> schedule_datetime
    return Schedule(**response_data_dict)


async def get_schedule(
    db: firestore.AsyncClient, schedule_id: str
) -> Optional[Schedule]:
    """
    Retrieves a single schedule document by its ID.
    Converts GeoPoint back to latitude/longitude for the response model.
    """
    doc_ref = db.collection(SCHEDULES_COLLECTION).document(schedule_id)
    doc_snapshot = await doc_ref.get()

    if not doc_snapshot.exists:
        return None

    schedule_db_data = doc_snapshot.to_dict()
    if not schedule_db_data:
        return None  # Should not happen if exists is true, but good practice

    # Add id to the dictionary for Pydantic model creation
    schedule_db_data["id"] = doc_snapshot.id

    # Extract GeoPoint and convert to latitude/longitude for the Pydantic model
    # The Pydantic model expects latitude and longitude, not the geoPoint object directly.
    retrieved_geopoint = schedule_db_data.pop("geoPoint", None) # Use Firestore key "geoPoint"
    if isinstance(retrieved_geopoint, GeoPoint):
        schedule_db_data["latitude"] = retrieved_geopoint.latitude
        schedule_db_data["longitude"] = retrieved_geopoint.longitude
    else:
        # Handle missing or malformed geopoint, perhaps set lat/lon to None or raise error
        schedule_db_data["latitude"] = None
        schedule_db_data["longitude"] = None
    
    # Pydantic will use aliases: title -> name, userId -> firebase_userid, content -> description, datetime -> schedule_datetime
    return Schedule(**schedule_db_data)


async def get_schedules_by_user(
    db: firestore.AsyncClient, firebase_userid: str
) -> List[Schedule]:
    """
    Retrieves all schedules for a given firebase_userid.
    Converts GeoPoint back to latitude/longitude for each schedule.
    """
    schedules_list = []
    # Query Firestore using the Firestore field name "userId"
    query = db.collection(SCHEDULES_COLLECTION).where(
        filter=FieldFilter("userId", "==", firebase_userid) # Use Firestore key "userId"
    )
    docs_stream = query.stream()

    async for doc_snapshot in docs_stream:
        if doc_snapshot.exists:
            schedule_db_data = doc_snapshot.to_dict()
            if not schedule_db_data:
                continue

            schedule_db_data["id"] = doc_snapshot.id
            retrieved_geopoint = schedule_db_data.pop("geoPoint", None) # Firestore key
            if isinstance(retrieved_geopoint, GeoPoint):
                schedule_db_data["latitude"] = retrieved_geopoint.latitude
                schedule_db_data["longitude"] = retrieved_geopoint.longitude
            else:
                schedule_db_data["latitude"] = None
                schedule_db_data["longitude"] = None

            schedules_list.append(Schedule(**schedule_db_data))
    return schedules_list


async def update_schedule(
    db: firestore.AsyncClient, schedule_id: str, schedule_data: ScheduleUpdate
) -> Optional[Schedule]:
    """
    Updates an existing schedule document.
    Handles partial updates and converts lat/lon to GeoPoint if they are part of the update.
    """
    doc_ref = db.collection(SCHEDULES_COLLECTION).document(schedule_id)

    # Check if document exists before attempting update
    doc_snapshot = await doc_ref.get()
    if not doc_snapshot.exists:
        return None

    # Use model_dump with by_alias=True to get Firestore field names, exclude unset fields
    update_data = schedule_data.model_dump(by_alias=True, exclude_unset=True)

    # If latitude or longitude is being updated, handle the geoPoint field.
    # The Pydantic model gives lat/lon, Firestore wants geoPoint.
    if "latitude" in update_data or "longitude" in update_data:
        # Get existing geoPoint to merge if only one coordinate is provided
        existing_firestore_data = doc_snapshot.to_dict() or {}
        current_geopoint_obj = existing_firestore_data.get("geoPoint")

        new_latitude = update_data.pop("latitude", None) # Remove from update_data
        new_longitude = update_data.pop("longitude", None) # Remove from update_data

        final_latitude = new_latitude if new_latitude is not None else (current_geopoint_obj.latitude if isinstance(current_geopoint_obj, GeoPoint) else None)
        final_longitude = new_longitude if new_longitude is not None else (current_geopoint_obj.longitude if isinstance(current_geopoint_obj, GeoPoint) else None)

        if final_latitude is not None and final_longitude is not None:
            update_data["geoPoint"] = GeoPoint(final_latitude, final_longitude)
        elif new_latitude is not None or new_longitude is not None:
            # One coord provided but not the other, and no existing to merge from: Error or specific logic needed.
            # For now, if we can't form a full GeoPoint, we don't update it.
            pass 

    if not update_data:  # No actual data to update
        return await get_schedule(db, schedule_id)  # Return current state

    await doc_ref.update(update_data)
    return await get_schedule(db, schedule_id)  # Return the updated document


async def delete_schedule(db: firestore.AsyncClient, schedule_id: str) -> bool:
    """
    Deletes a schedule document by its ID.
    """
    doc_ref = db.collection(SCHEDULES_COLLECTION).document(schedule_id)
    doc_snapshot = (
        await doc_ref.get()
    )  # Check existence for a more robust delete indication
    if not doc_snapshot.exists:
        return False  # Or raise NotFound

    await doc_ref.delete()
    return True
