from fastapi import FastAPI

from app.database import initialize_database

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    """Initialize the database on startup."""
    try:
        await initialize_database()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        raise e


@app.get("/")
async def root():
    return {"message": "Hello World"}
