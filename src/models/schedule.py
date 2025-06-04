from pydantic import BaseModel, Field
from typing import Optional  # For older Python, use Optional. For 3.10+, use str | None

# For GeoPoint, we'll handle it in the CRUD layer.
# API models will use latitude and longitude.


class ScheduleBase(BaseModel):
    name: str = Field(..., description="Name of the schedule")
    latitude: float = Field(..., description="Latitude of the schedule location")
    longitude: float = Field(..., description="Longitude of the schedule location")
    firebase_userid: str = Field(
        ..., description="Firebase User ID of the schedule owner"
    )
    description: Optional[str] = Field(
        None, description="Optional description for the schedule"
    )


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Name of the schedule")
    latitude: Optional[float] = Field(
        None, description="Latitude of the schedule location"
    )
    longitude: Optional[float] = Field(
        None, description="Longitude of the schedule location"
    )
    description: Optional[str] = Field(
        None, description="Optional description for the schedule"
    )
    # firebase_userid is typically not updatable directly this way for an existing schedule,
    # as it defines ownership. If a schedule needs to change owner, it's often a delete & recreate,
    # or a special admin operation.


class ScheduleInDBBase(ScheduleBase):
    id: str = Field(..., description="Firestore document ID of the schedule")

    class Config:
        from_attributes = True  # For compatibility if creating from ORM-like objects


# This is the main model that will be returned by API endpoints reading schedule data
class Schedule(ScheduleInDBBase):
    pass
