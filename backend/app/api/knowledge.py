from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.upload_safety import save_upload, resolve_upload_path, UploadTooLargeError

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])
UPLOAD_DIR = Path("uploads")
SUPPORTED_EXTENSIONS = {".pdf", ".pptx", ".mp4"}


@router.post("/upload")
def upload_course_file(file: UploadFile = File(...)):
    """Validate before loading providers; blocking ingestion runs in a worker thread."""
    try:
        destination = resolve_upload_path(UPLOAD_DIR, file.filename)
        if destination.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Supported formats: PDF, PPTX, MP4.")
        destination = save_upload(file.file, UPLOAD_DIR, file.filename)
        from app.knowledge.knowledge_base_builder import build_knowledge_base
        result = build_knowledge_base(str(destination))
        result["content_units"] = [unit.model_dump(exclude={"embedding"}) for unit in result["content_units"]]
        if not result["content_units"]:
            raise HTTPException(status_code=422, detail="No content could be extracted.")
        return {"status": "processed", **result}
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Knowledge processing failed.") from exc
