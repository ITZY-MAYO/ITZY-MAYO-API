from fastapi import APIRouter, status
from src.models.location import LocationCreate
import logging
import asyncio

# Firebase Admin SDK
import firebase_admin
from firebase_admin import (
    firestore,
    # messaging, # Removed as it's now in notification_service
)
from firebase_admin.exceptions import FirebaseError

# Geopy for distance calculation
from geopy.distance import geodesic

# Import from the new notification service
from src.services.notification_service import send_fcm_proximity_notification

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
    details = "No proximate schedule found or user has no token."

    # Placeholder for original functionality: Store the location_data if needed
    logger.info(f"Received location for user {location_data.firebase_userid}: lat={location_data.latitude}, lon={location_data.longitude}")
    # e.g., await crud.store_location(db, location_data)

    try:
        schedules_ref = db.collection("schedule")
        # Use await for stream() and iterate with async for
        user_schedules_stream = schedules_ref.where(
            "firebase_userid", "==", location_data.firebase_userid
        ).stream()  # .stream() itself returns an async iterator

        current_device_location = (location_data.latitude, location_data.longitude)

        async for schedule_doc in user_schedules_stream:  # Iterate with async for
            schedule_data = schedule_doc.to_dict()
            if not schedule_data:
                continue
            logger.info(f"Schedule data: {schedule_data}")
            location_geopoint = schedule_data.get("geoPoint")
            logger.info(f"Location geopoint: {location_geopoint}")
            if isinstance(location_geopoint, firestore.GeoPoint):
                schedule_location = (
                    location_geopoint.latitude,
                    location_geopoint.longitude,
                )
                distance_meters = geodesic(
                    current_device_location, schedule_location
                ).meters
                logger.info(f"Distance meters: {distance_meters}")
                if distance_meters <= 100:
                    found_proximate_schedule = True
                    logger.info(
                        f"User {location_data.firebase_userid} is within 100m of schedule {schedule_doc.id} (distance: {distance_meters:.2f}m)"
                    )
                    break  # Found one, no need to check further
            else:
                logger.warning(
                    f"Schedule {schedule_doc.id} for user {location_data.firebase_userid} has missing or invalid location_geopoint."
                )

        if found_proximate_schedule:
            fcm_token_doc_ref = db.collection("fcm_tokens").document(
                location_data.firebase_userid
            )
            fcm_token_doc = await fcm_token_doc_ref.get()  # Add await here

            if fcm_token_doc.exists:
                fcm_token_data = fcm_token_doc.to_dict()
                user_fcm_token = fcm_token_data.get("token") if fcm_token_data else None

                if user_fcm_token:
                    logger.info(
                        f"Found FCM token for user {location_data.firebase_userid}."
                    )
                    if await send_fcm_proximity_notification(
                        user_fcm_token, location_data.firebase_userid
                    ):
                        notification_sent_status = True
                        details = "Notification sent successfully."
                    else:
                        details = "Proximate schedule found, FCM token found, but failed to send notification."
                else:
                    details = "Proximate schedule found, but user's FCM token is missing in the document."
                    logger.warning(
                        f"FCM token missing in document for user {location_data.firebase_userid}."
                    )
            else:
                details = "Proximate schedule found, but no FCM token document found for user."
                logger.warning(
                    f"No FCM token document found for user {location_data.firebase_userid}."
                )
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
