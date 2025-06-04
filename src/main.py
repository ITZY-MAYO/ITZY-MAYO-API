from fastapi import FastAPI
from contextlib import asynccontextmanager
import firebase_admin
from firebase_admin import credentials
import logging  # Add logging import
import os  # Import os module

from src.api.v1.endpoints import locations
from src.api.v1.endpoints import schedules  # Import the new schedules router
from src.core.config import settings  # Import the settings instance

# Configure basic logging
# In a more complex app, you might move this to a dedicated logging_config.py
# and use different handlers/formatters.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)  # Create a logger for this module


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Firebase Admin SDK using Pydantic Settings
    cred_path = settings.GOOGLE_APPLICATION_CREDENTIALS
    if not cred_path:
        logger.error(
            "GOOGLE_APPLICATION_CREDENTIALS not found in settings or .env file."
        )
    else:
        try:
            # Explicitly set the environment variable for other Google Cloud libraries
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
            logger.info(
                f"Set GOOGLE_APPLICATION_CREDENTIALS environment variable to: {cred_path}"
            )

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info(
                "Firebase Admin SDK initialized successfully using credentials from settings."
            )
        except FileNotFoundError:
            logger.error(
                f"Firebase credentials file not found at path: {cred_path}. Check your .env file and path."
            )
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)

    yield
    # Add shutdown code here if needed in the future
    # For Firebase, cleanup is usually handled automatically, but you could add firebase_admin.delete_app(firebase_admin.get_app()) if needed.


app = FastAPI(
    title="Itzy Mayo API",
    description="API for Itzy Mayo services, starting with location tracking.",
    version="0.1.0",
    lifespan=lifespan,
)

# Include the API routers
app.include_router(locations.router, prefix="/api/v1/locations", tags=["locations"])
app.include_router(
    schedules.router, prefix="/api/v1/schedules", tags=["schedules"]
)  # Add the schedules router


@app.get("/")
async def read_root():
    return {"message": "Welcome to Itzy Mayo API"}


# To run this application (from the project root directory):
# Ensure your virtual environment is activated: source .venv/bin/activate
# Then run: uvicorn src.main:app --reload
