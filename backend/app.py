from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid, os, shutil
from dotenv import load_dotenv
load_dotenv()
from analysis import analyze_video

app = FastAPI(title="Rudi AI Starter API")

# CORS from .env (comma-separated)
_ORIGINS = os.getenv("CORS_ORIGINS", "http://127.0.0.1:3000")
_ORIGINS = [o.strip() for o in _ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class AnalyzeResponse(BaseModel):
    per_hit: list
    summary: dict

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...)):
    # save temp file
    ext = os.path.splitext(file.filename)[1]
    vid_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    with open(vid_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        result = analyze_video(vid_path)
        return result
    finally:
        # clean up uploaded file to keep disk small
        try:
            os.remove(vid_path)
        except Exception:
            pass
@app.get("/health")
def health():
    return {"status": "ok"}
from dotenv import load_dotenv
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()
_MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
_MAX_BYTES = _MAX_MB * 1024 * 1024

@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    # Only guard the analyze endpoint
    if request.url.path == "/analyze":
        cl = request.headers.get("content-length")
        try:
            if cl and int(cl) > _MAX_BYTES:
                return JSONResponse({"detail": f"File too large. Limit is {_MAX_MB} MB."}, status_code=413)
        except Exception:
            pass
    return await call_next(request)


