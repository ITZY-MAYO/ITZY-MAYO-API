from src.models.location import LocationCreate, LocationInDB
from src.db.database import get_db_connection


async def create_location(location: LocationCreate) -> LocationInDB:
    connection = await get_db_connection()
    async with connection as db:
        cursor = await db.execute(
            "INSERT INTO locations (firebase_userid, latitude, longitude) VALUES (?, ?, ?)",
            (location.firebase_userid, location.latitude, location.longitude),
        )
        await db.commit()
        location_id = cursor.lastrowid
        await cursor.close()

        # Fetch the created record to include autogenerated fields like id and timestamp
        async with db.execute(
            "SELECT id, firebase_userid, latitude, longitude, timestamp FROM locations WHERE id = ?",
            (location_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return LocationInDB(
                    id=row[0],
                    firebase_userid=row[1],
                    latitude=row[2],
                    longitude=row[3],
                    timestamp=str(row[4]),
                )
            else:
                # This case should ideally not happen if insert was successful
                raise Exception("Failed to retrieve created location")
