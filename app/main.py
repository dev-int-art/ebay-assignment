from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.listings import router as listings_router
from app.database import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on startup."""
    await initialize_database()
    yield


app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(listings_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
