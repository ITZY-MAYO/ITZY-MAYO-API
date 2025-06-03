from pydantic import BaseModel

class LocationCreate(BaseModel):
    firebase_userid: str
    latitude: float
    longitude: float

class LocationInDB(LocationCreate):
    id: int
    timestamp: str # Assuming timestamp is stored as TEXT in ISO format

    class Config:
        from_attributes = True # For compatibility with ORM models if used later, good practice 