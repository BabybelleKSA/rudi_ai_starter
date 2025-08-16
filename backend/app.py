from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid, os, shutil
from analysis import analyze_video

app = FastAPI(title="Rudi AI Starter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
