# main.py
import sys
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ---------------- Path Setup ----------------
# Add src to sys.path so Python can find your modules
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Import routers
from draft_routes import router as draft_router      # draft generate
from send_routes import router as act_router         # draft update/send & calendar event

# ---------------- App Init ----------------
app = FastAPI(
    title="Draft Email API",
    description="API for generating, updating and sending email drafts",
    version="1.0.0"
)

# ---------------- Logging ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ⚠️ In production, restrict this to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Static Files + Frontend ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")

if os.path.exists(INDEX_FILE):
    # Serve all root files (index.html, JS, CSS, etc.) via /static
    app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

    @app.get("/")
    async def serve_index():
        """Serve the main frontend index.html at root /"""
        return FileResponse(INDEX_FILE)
else:
    logging.warning("⚠️ index.html not found at project root!")

# ---------------- Routers ----------------
app.include_router(draft_router, prefix="/api")  # /api/generate-draft
app.include_router(act_router, prefix="/api")    # /api/act

# ---------------- Run ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
