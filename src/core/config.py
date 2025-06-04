# Future application settings can be placed here.

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os


class Settings(BaseSettings):
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(
        ..., description="Path to the Firebase service account key JSON file"
    )

    # Configure Pydantic Settings to load from a .env file
    # The .env file should be in the same directory as where the application is run from,
    # or you can specify a path. For project root, an empty string or "." usually works if
    # the app is run from the root.
    # We will assume the .env file is in the project root.
    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            ".env",
        ),
        extra="ignore",
    )


# Instantiate the settings
settings = Settings()
