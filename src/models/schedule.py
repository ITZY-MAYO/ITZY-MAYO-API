from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime # Import datetime

# For GeoPoint, we'll handle it in the CRUD layer.
# API models will use latitude and longitude.
# The CRUD layer will handle conversion from/to Firestore's geoPoint.


class ScheduleBase(BaseModel):
    # Pydantic field name: API exposure | Firestore field name (via alias)
    name: str = Field(..., alias="title", description="Name of the schedule")
    latitude: float = Field(..., description="Latitude of the schedule location")
    longitude: float = Field(..., description="Longitude of the schedule location")
    firebase_userid: str = Field(
        ..., alias="userId", description="Firebase User ID of the schedule owner"
    )
    description: Optional[str] = Field(
        None, alias="content", description="Optional description for the schedule"
    )
    # Add the datetime field, assuming it comes as a Firestore Timestamp 
    # and Pydantic can handle its conversion to Python datetime.
    # If it needs special handling (e.g., from string), a validator might be needed.
    schedule_datetime: datetime = Field(..., alias="datetime", description="Date and time of the schedule")

    class Config:
        populate_by_name = True # Allows using aliases for both serialization and validation
        # formerly known as allow_population_by_field_name


class ScheduleCreate(ScheduleBase):
    # For creation, the client will send data according to Pydantic field names (name, firebase_userid, etc.)
    # Pydantic will then use aliases if you were to create a dict from this model to send to Firestore directly using these aliases.
    # However, our CRUD layer will handle the mapping explicitly for GeoPoint.
    pass


class ScheduleUpdate(BaseModel):
    # When updating, client sends Pydantic field names.
    # Aliases help if we dump this model to a dict for Firestore update using aliases.
    name: Optional[str] = Field(None, alias="title", description="Name of the schedule")
    latitude: Optional[float] = Field(
        None, description="Latitude of the schedule location"
    )
    longitude: Optional[float] = Field(
        None, description="Longitude of the schedule location"
    )
    description: Optional[str] = Field(
        None, alias="content", description="Optional description for the schedule"
    )
    schedule_datetime: Optional[datetime] = Field(None, alias="datetime", description="Date and time of the schedule")

    class Config:
        populate_by_name = True


class ScheduleInDBBase(ScheduleBase):
    id: str = Field(..., description="Firestore document ID of the schedule")

    class Config:
        from_attributes = True  # For compatibility if creating from ORM-like objects


# This is the main model that will be returned by API endpoints reading schedule data
class Schedule(ScheduleInDBBase):
    pass
