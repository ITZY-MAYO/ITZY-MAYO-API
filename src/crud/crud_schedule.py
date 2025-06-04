from firebase_admin import firestore
from google.cloud.firestore_v1.types import GeoPoint  # For creating GeoPoint instances
from typing import (
    List,
    Optional,
)  # For older Python, use List & Optional. For 3.9+, use list & | None

from src.models.schedule import Schedule, ScheduleCreate, ScheduleUpdate

# Firestore collection name
SCHEDULES_COLLECTION = "schedules"


async def create_schedule(
    db: firestore.AsyncClient, schedule_data: ScheduleCreate
) -> Schedule:
    """
    Creates a new schedule document in Firestore.
    Converts latitude/longitude to GeoPoint for storage.
    """
    doc_ref = db.collection(SCHEDULES_COLLECTION).document()  # Auto-generate ID

    schedule_dict = schedule_data.model_dump()
    # Convert lat/lon to GeoPoint before saving
    schedule_dict["location_geopoint"] = GeoPoint(
        schedule_data.latitude, schedule_data.longitude
    )
    # Remove individual latitude and longitude as they are now in location_geopoint
    del schedule_dict["latitude"]
    del schedule_dict["longitude"]

    await doc_ref.set(schedule_dict)

    # For the response model, we still want to return lat/lon
    # The Schedule model expects latitude and longitude, not location_geopoint
    # So, we reconstruct the response data with the original lat/lon and new ID
    return Schedule(id=doc_ref.id, **schedule_data.model_dump())


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

    # Convert GeoPoint back to latitude and longitude for the Schedule model
    latitude = schedule_db_data.get("location_geopoint", {}).get("latitude")
    longitude = schedule_db_data.get("location_geopoint", {}).get("longitude")
    if latitude is None or longitude is None:
        # Handle cases where GeoPoint might be missing or malformed if necessary
        # For now, we assume it's present if the document is valid
        pass

    return Schedule(
        id=doc_snapshot.id,
        name=schedule_db_data.get("name"),
        latitude=latitude,
        longitude=longitude,
        firebase_userid=schedule_db_data.get("firebase_userid"),
        description=schedule_db_data.get("description"),
    )


async def get_schedules_by_user(
    db: firestore.AsyncClient, firebase_userid: str
) -> List[Schedule]:
    """
    Retrieves all schedules for a given firebase_userid.
    Converts GeoPoint back to latitude/longitude for each schedule.
    """
    schedules_list = []
    query = db.collection(SCHEDULES_COLLECTION).where(
        "firebase_userid", "==", firebase_userid
    )
    docs_stream = query.stream()

    async for doc_snapshot in docs_stream:
        if doc_snapshot.exists:
            schedule_db_data = doc_snapshot.to_dict()
            if not schedule_db_data:
                continue

            latitude = schedule_db_data.get("location_geopoint", {}).get("latitude")
            longitude = schedule_db_data.get("location_geopoint", {}).get("longitude")

            schedules_list.append(
                Schedule(
                    id=doc_snapshot.id,
                    name=schedule_db_data.get("name"),
                    latitude=latitude,
                    longitude=longitude,
                    firebase_userid=schedule_db_data.get("firebase_userid"),
                    description=schedule_db_data.get("description"),
                )
            )
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

    update_data = schedule_data.model_dump(
        exclude_unset=True
    )  # Only include fields that were set

    # If latitude or longitude is being updated, update/create the GeoPoint
    if "latitude" in update_data or "longitude" in update_data:
        # Need existing lat/lon if only one is provided, or use new ones if both provided
        existing_data = doc_snapshot.to_dict() or {}
        current_geopoint = existing_data.get("location_geopoint")

        new_latitude = update_data.get(
            "latitude", current_geopoint.latitude if current_geopoint else None
        )
        new_longitude = update_data.get(
            "longitude", current_geopoint.longitude if current_geopoint else None
        )

        if new_latitude is not None and new_longitude is not None:
            update_data["location_geopoint"] = GeoPoint(new_latitude, new_longitude)

        # Remove individual latitude and longitude from update_data if they were used to make GeoPoint
        if "latitude" in update_data:
            del update_data["latitude"]
        if "longitude" in update_data:
            del update_data["longitude"]

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
