
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database.db import init_db
from routes.issues import router as issues_router
from routes.analytics import router as analytics_router
from routes.live import router as live_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database when the server starts.
    init_db()
    yield


app = FastAPI(
    title="CleanO Campus API",
    description="Campus sustainability and issue management backend",
    version="1.0.0",
    lifespan=lifespan,
)


# Register all API routers.
app.include_router(issues_router)
app.include_router(analytics_router)
app.include_router(live_router)


@app.get("/")
def home():
    return {
        "message": "CleanO Campus API is running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
