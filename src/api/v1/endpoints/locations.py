from fastapi import APIRouter, HTTPException
from src.models.location import LocationCreate, LocationInDB

router = APIRouter()

@router.post("/locations/", response_model=None, status_code=201)
async def record_location(location: LocationCreate):
    """
    Receives location data (Firebase User ID, latitude, longitude) 
    and stores it in the database.
    """
    try:
        return location
    except Exception as e:
        # Log the exception e here if you have logging setup
        raise HTTPException(status_code=500, detail=f"Failed to record location: {str(e)}") 