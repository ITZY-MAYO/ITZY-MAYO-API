from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.api.v1.endpoints import locations

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Add shutdown code here if needed in the future

app = FastAPI(
    title="Itzy Mayo API",
    description="API for Itzy Mayo services, starting with location tracking.",
    version="0.1.0",
    lifespan=lifespan
)

# Include the API routers
app.include_router(locations.router, prefix="/api/v1", tags=["locations"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to Itzy Mayo API"}

# To run this application (from the project root directory):
# Ensure your virtual environment is activated: source .venv/bin/activate
# Then run: uvicorn src.main:app --reload 