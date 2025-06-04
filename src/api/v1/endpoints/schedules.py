from fastapi import APIRouter, HTTPException, status
from typing import List  # For older Python, use List. For 3.9+, use list

from firebase_admin import firestore  # For firestore.AsyncClient()
from src.models.schedule import Schedule, ScheduleCreate, ScheduleUpdate
from src.crud import crud_schedule  # Import the CRUD module
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# It's good practice to initialize the client once per module if possible,
# or pass it around, or use a dependency injection system.
# For simplicity here, we'll create it as needed or once at module level.
# However, since db client should be managed by lifespan ideally,
# for now, we re-create it per call or use a simple global for this router.
# For a robust app, use FastAPI dependencies for DB session management.


# Helper to get DB client - in a real app, use FastAPI's Depends system
# This is a simplified approach for now.
def get_db_client():
    # Note: Firebase Admin SDK must be initialized (e.g., in main.py lifespan)
    # for firestore.AsyncClient() to work correctly with ADC or provided credentials.
    return firestore.AsyncClient()


@router.post("/", response_model=Schedule, status_code=status.HTTP_201_CREATED)
async def create_new_schedule(schedule: ScheduleCreate):
    db = get_db_client()
    try:
        created_schedule = await crud_schedule.create_schedule(
            db=db, schedule_data=schedule
        )
        return created_schedule
    except Exception as e:
        logger.error(
            f"Error creating schedule for user {schedule.firebase_userid}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create schedule",
        )


@router.get("/user/{firebase_userid}", response_model=List[Schedule])
async def read_schedules_by_user(firebase_userid: str):
    db = get_db_client()
    schedules = await crud_schedule.get_schedules_by_user(
        db=db, firebase_userid=firebase_userid
    )
    return schedules


@router.get("/{schedule_id}", response_model=Schedule)
async def read_schedule_by_id(schedule_id: str):
    db = get_db_client()
    schedule = await crud_schedule.get_schedule(db=db, schedule_id=schedule_id)
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found"
        )
    return schedule


@router.put("/{schedule_id}", response_model=Schedule)
async def update_existing_schedule(schedule_id: str, schedule_update: ScheduleUpdate):
    db = get_db_client()
    updated_schedule = await crud_schedule.update_schedule(
        db=db, schedule_id=schedule_id, schedule_data=schedule_update
    )
    if updated_schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found or no update performed",
        )
    return updated_schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_schedule(schedule_id: str):
    db = get_db_client()
    deleted_successfully = await crud_schedule.delete_schedule(
        db=db, schedule_id=schedule_id
    )
    if not deleted_successfully:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found or could not be deleted",
        )
    return  # Returns 204 No Content on success
