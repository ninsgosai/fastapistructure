from fastapi import FastAPI
from views import router as user_router
from db import init_db
import uvicorn

app = FastAPI()

@app.on_event("startup")
def startup_event():
    """Initialize the database on startup."""
    init_db()  # Create tables if they don't exist

app.include_router(user_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
