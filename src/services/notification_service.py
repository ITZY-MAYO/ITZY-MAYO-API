import asyncio
import logging

from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)


async def send_fcm_proximity_notification(token: str, user_id: str) -> bool:
    message = messaging.Message(
        notification=messaging.Notification(
            title="일정 알림",  # "Schedule Notification"
            body="주변에 설정된 일정이 있습니다!",  # "There is a schedule nearby!"
        ),
        token=token,
        # You can also send data payload if needed
        # data={
        #     "userId": user_id,
        #     "type": "proximity_alert"
        # }
    )
    try:
        # messaging.send is a blocking call, so run it in a separate thread
        response = await asyncio.to_thread(messaging.send, message)
        logger.info(f"Successfully sent FCM message to {user_id}: {response}")
        return True
    except FirebaseError as e:
        logger.error(f"Error sending FCM message to {user_id}: {e}", exc_info=True)
        # More specific error handling can be done here based on e.g. e.code
        # messaging.UnregisteredError, messaging.ThirdPartyAuthError etc.
    except Exception as e:
        logger.error(
            f"Unexpected error sending FCM message to {user_id}: {e}", exc_info=True
        )
    return False
