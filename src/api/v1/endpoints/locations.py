from fastapi import APIRouter, status
from src.models.location import LocationCreate
import logging
import asyncio
from datetime import datetime, timedelta, timezone # Import datetime utilities

# Firebase Admin SDK
import firebase_admin
from firebase_admin import (
    firestore,
    # messaging, # Removed as it's now in notification_service
)
from firebase_admin.exceptions import FirebaseError
from google.cloud.firestore_v1 import FieldFilter

# Geopy for distance calculation
from geopy.distance import geodesic

# Import from the new notification service
from src.services.notification_service import send_fcm_proximity_notification

from src.crud import crud_schedule # Import the crud_schedule module
from src.crud import crud_fcm_token # Import the new FCM token CRUD module
from src.crud import crud_notification_history # Import notification history CRUD

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/locations/", response_model=dict, status_code=status.HTTP_200_OK)
async def handle_location_update_and_proximity_check(location_data: LocationCreate):
    """
    Receives location data (Firebase User ID, latitude, longitude),
    checks if the user is near any of their scheduled locations,
    and sends an FCM notification if true.
    Returns whether the notification was sent.
    Optionally, location data can also be stored here.
    """
    if not firebase_admin._apps:
        logger.warning(
            "Firebase Admin SDK not initialized. Cannot proceed with Firebase operations."
        )
        # Potentially raise HTTPException(status_code=503, detail="Firebase service unavailable")
        return {
            "notification_sent": False,
            "detail": "Firebase service not initialized.",
        }

    # Use Async Firestore client
    db = firestore.AsyncClient()
    found_proximate_schedule = False
    notification_sent_status = False
    proximate_schedule_item = None # Store the found schedule item
    details = "No proximate schedule found or user has no token."

    # Placeholder for original functionality: Store the location_data if needed
    logger.info(f"Received location for user {location_data.firebase_userid}: lat={location_data.latitude}, lon={location_data.longitude}")
    # e.g., await crud.store_location(db, location_data)

    try:
        # Fetch schedules using the CRUD function
        user_schedules = await crud_schedule.get_schedules_by_user(
            db=db, firebase_userid=location_data.firebase_userid
        )

        current_device_location = (location_data.latitude, location_data.longitude)

        for schedule_item_loop in user_schedules: # Iterate over Schedule model instances
            # schedule_item_loop is now a Schedule Pydantic model instance
            # which has latitude and longitude attributes directly
            
            # Ensure schedule_item_loop has latitude and longitude
            if schedule_item_loop.latitude is not None and schedule_item_loop.longitude is not None:
                schedule_location = (
                    schedule_item_loop.latitude,
                    schedule_item_loop.longitude,
                )
                distance_meters = geodesic(
                    current_device_location, schedule_location
                ).meters
                logger.info(f"Comparing with schedule '{schedule_item_loop.name}' (ID: {schedule_item_loop.id}). Distance: {distance_meters:.2f}m")

                if distance_meters <= 100: # Using 100 meters as proximity threshold
                    found_proximate_schedule = True
                    proximate_schedule_item = schedule_item_loop # Save the matched schedule
                    logger.info(
                        f"User {location_data.firebase_userid} is within 100m of schedule '{proximate_schedule_item.name}' (ID: {proximate_schedule_item.id})."
                    )
                    break  # Found one, no need to check further
            else:
                logger.warning(
                    f"Schedule {schedule_item_loop.id} for user {location_data.firebase_userid} has missing latitude or longitude."
                )

        if found_proximate_schedule and proximate_schedule_item:
            current_time = datetime.now(timezone.utc)
            can_send_notification = True

            # Check notification history for cooldown
            history = await crud_notification_history.get_notification_history(
                db, location_data.firebase_userid, proximate_schedule_item.id
            )

            if history and history.last_sent_at:
                # Ensure last_sent_at is offset-aware for comparison with current_time
                last_sent_at_aware = history.last_sent_at
                if last_sent_at_aware.tzinfo is None:
                    last_sent_at_aware = last_sent_at_aware.replace(tzinfo=timezone.utc)
                
                time_since_last_sent = current_time - last_sent_at_aware
                if time_since_last_sent < timedelta(minutes=10):
                    can_send_notification = False
                    cooldown_remaining = timedelta(minutes=10) - time_since_last_sent
                    details = f"Notification for schedule '{proximate_schedule_item.name}' recently sent. Cooldown active for {cooldown_remaining.total_seconds() // 60:.0f} more minutes."
                    logger.info(details)
                else:
                    logger.info(f"Cooldown period for schedule '{proximate_schedule_item.name}' has passed. Last sent: {history.last_sent_at}")
            else:
                logger.info(f"No previous notification history found for schedule '{proximate_schedule_item.name}'.")

            if can_send_notification:
                # Fetch FCM token using the CRUD function
                fcm_token_obj = await crud_fcm_token.get_fcm_token_by_user_id(
                    db=db, firebase_userid=location_data.firebase_userid
                )

                if fcm_token_obj and fcm_token_obj.token:
                    user_fcm_token = fcm_token_obj.token
                    logger.info(
                        f"Attempting to send FCM to user {location_data.firebase_userid} for schedule '{proximate_schedule_item.name}'."
                    )
                    if await send_fcm_proximity_notification(
                        user_fcm_token, location_data.firebase_userid
                    ):
                        notification_sent_status = True
                        details = f"Notification sent successfully for schedule '{proximate_schedule_item.name}'."
                        logger.info(details)
                        # Update notification history
                        await crud_notification_history.update_notification_history(
                            db, location_data.firebase_userid, proximate_schedule_item.id, current_time
                        )
                    else:
                        details = f"FCM token found, but failed to send notification for schedule '{proximate_schedule_item.name}'."
                        logger.error(details) # Log as error if sending failed
                elif fcm_token_obj:
                    details = f"FCM token document found, but token string is missing for user {location_data.firebase_userid}. Cannot send notification for '{proximate_schedule_item.name}'."
                    logger.warning(details)
                else:
                    details = f"No FCM token document found for user {location_data.firebase_userid}. Cannot send notification for '{proximate_schedule_item.name}'."
                    logger.warning(details)
        else:
            details = "No proximate schedule found for the user."
            logger.info(
                f"No proximate schedules found for user {location_data.firebase_userid}."
            )

    except FirebaseError as e:
        logger.error(
            f"Firebase error during proximity check for {location_data.firebase_userid}: {e}",
            exc_info=True,
        )
        details = f"A Firebase error occurred: {str(e)}"
    except Exception as e:
        logger.error(
            f"Unexpected error during proximity check for {location_data.firebase_userid}: {e}",
            exc_info=True,
        )
        details = f"An unexpected error occurred: {str(e)}"

    return {"notification_sent": notification_sent_status, "detail": details}


# --- Helper function to send FCM notification ---  <- This entire function will be removed
# async def send_fcm_proximity_notification(token: str, user_id: str) -> bool:
#     message = messaging.Message(
#         notification=messaging.Notification(
#             title="일정 알림",  # "Schedule Notification"
#             body="주변에 설정된 일정이 있습니다!",  # "There is a schedule nearby!"
#         ),
#         token=token,
#         # You can also send data payload if needed
#         # data={
#         #     "userId": user_id,
#         #     "type": "proximity_alert"
#         # }
#     )
#     try:
#         response = await asyncio.to_thread(messaging.send, message)
#         logger.info(f"Successfully sent FCM message to {user_id}: {response}")
#         return True
#     except FirebaseError as e:
#         logger.error(f"Error sending FCM message to {user_id}: {e}", exc_info=True)
#         # More specific error handling can be done here based on e.g. e.code
#         # messaging.UnregisteredError, messaging.ThirdPartyAuthError etc.
#     except Exception as e:
#         logger.error(
#             f"Unexpected error sending FCM message to {user_id}: {e}", exc_info=True
#         )
#     return False
