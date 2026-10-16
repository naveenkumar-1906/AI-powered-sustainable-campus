
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"


# --------------------------------------------------
# ROUTER IMPORTS
# --------------------------------------------------

from routes.issues import router as issues_router
from routes.camera import router as camera_router

try:
    from routes.analytics import router as analytics_router
except ImportError:
    analytics_router = None

try:
    from routes.live import router as live_router
except ImportError:
    live_router = None


# --------------------------------------------------
# DATABASE STARTUP
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from database.db import init_db
        init_db()
        print("CleanO Campus database initialized.")
    except ImportError:
        print("No database init_db() function found.")
    except Exception as exc:
        print(f"Database initialization failed: {exc}")
        raise

    print("Issues endpoint: /api/issues")
    print("Alerts endpoint: GET /api/alerts")
    print("CCTV endpoint: POST /api/camera/analyze-video")
    print("CleanO Campus API is ready.")

    yield

    print("CleanO Campus API stopped.")


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="CleanO Campus API",
    description="DSU campus sustainability and CCTV analysis",
    version="1.4.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# FRONTEND STATIC FILES
# --------------------------------------------------

for folder in ("css", "js", "assets"):
    (FRONTEND_DIR / folder).mkdir(parents=True, exist_ok=True)

app.mount(
    "/css",
    StaticFiles(directory=str(FRONTEND_DIR / "css")),
    name="css",
)

app.mount(
    "/js",
    StaticFiles(directory=str(FRONTEND_DIR / "js")),
    name="js",
)

app.mount(
    "/assets",
    StaticFiles(directory=str(FRONTEND_DIR / "assets")),
    name="assets",
)


# --------------------------------------------------
# API ROUTERS
# --------------------------------------------------

# Keep the existing issue API routes.
app.include_router(issues_router)

# camera.py already declares the /api/camera prefix.
# Do not add another /api prefix.
app.include_router(camera_router)

# Optional analytics routes.
if analytics_router is not None:
    app.include_router(analytics_router, prefix="/api")

# Optional WebSocket/live routes.
if live_router is not None:
    app.include_router(live_router)


# --------------------------------------------------
# ALERTS COMPATIBILITY ENDPOINT
# --------------------------------------------------

@app.get("/api/alerts", tags=["Alerts"])
def get_alerts():
    """
    Compatibility endpoint for the frontend.

    This returns an empty list until the actual alert database
    or alert service is connected. It does not create fake alerts.
    """
    return {
        "alerts": [],
        "count": 0,
        "message": "No alerts available."
    }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "healthy",
        "app": "CleanO Campus",
    }


# --------------------------------------------------
# FRONTEND HOME PAGE
# --------------------------------------------------

@app.get("/", include_in_schema=False)
def serve_frontend():
    index_file = FRONTEND_DIR / "index.html"

    if not index_file.is_file():
        return JSONResponse(
            status_code=500,
            content={
                "error": "frontend/index.html was not found",
                "expected_path": str(index_file),
            },
        )

    return FileResponse(index_file)


# --------------------------------------------------
# OPTIONAL BLOCK PAGE
# --------------------------------------------------

@app.get("/block", include_in_schema=False)
def serve_block_page():
    block_file = FRONTEND_DIR / "pages" / "block.html"

    if not block_file.is_file():
        return JSONResponse(
            status_code=404,
            content={"error": "Block page not found"},
        )

    return FileResponse(block_file)
