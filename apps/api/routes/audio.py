from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

AUDIO_ROOT = Path("data/cache/tts_real").resolve()
AUDIO_MEDIA_TYPES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
}
ALLOWED_SUFFIXES = set(AUDIO_MEDIA_TYPES)

@router.get("/audio/{filename}")
def get_audio(filename: str):
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid audio filename.")

    audio_path = (AUDIO_ROOT / filename).resolve()

    if not str(audio_path).startswith(str(AUDIO_ROOT)):
        raise HTTPException(status_code=400, detail="Invalid audio path.")

    if audio_path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported audio file type.")

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")

    return FileResponse(
        str(audio_path),
        media_type=AUDIO_MEDIA_TYPES.get(audio_path.suffix.lower(), "application/octet-stream"),
        filename=audio_path.name,
    )
