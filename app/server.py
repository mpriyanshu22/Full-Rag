
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, HTTPException, Path, UploadFile
from pydantic import BaseModel, Field

from app.utils import save_to_disk
from .db.collections.files import FileSchema, files_collection
from .graph.workflow import resume_analysis_graph
from .queue.q import q
from .queue.workers import process_file

app = FastAPI()


class JobAnalysisRequest(BaseModel):
    file_id: str = Field(..., description="ID of the resume file stored in MongoDB")
    job_description: str = Field(..., description="Raw text of the Job Description")


@app.get("/")
def hello():
    return {"message": "Healthy!"}


@app.post("/upload")
async def upload_file(file: UploadFile):
    schema_data = FileSchema(name=file.filename, status="saving")
    
    # Motor expects a dictionary, not a Pydantic model instance
    db_file = await files_collection.insert_one(
        document=schema_data
    )
    
    file_id_str = str(db_file.inserted_id)
    file_path = f"/mnt/uploads/{file_id_str}/{file.filename}"
    
    await save_to_disk(file=await file.read(), path=file_path)
    
    # Push to task queue
    q.enqueue(process_file, file_id_str, file_path)
    
    # Update status to queued
    await files_collection.update_one(
        {"_id": db_file.inserted_id},
        {"$set": {"status": "queued"}}
    )
    
    return {"file_id": file_id_str}


@app.post("/analyze")
async def analyze_resume_for_job(request: JobAnalysisRequest):
    initial_state = {
        "file_id": request.file_id,
        "job_description": request.job_description,
        "resume_text": None,
        "rewritten_jd": None,
        "report": None,
        "error": None,
    }

    final_state = await resume_analysis_graph.ainvoke(initial_state)

    if final_state.get("error"):
        raise HTTPException(status_code=400, detail=final_state["error"])

    return {
        "success": True,
        "rewritten_jd": final_state.get("rewritten_jd"),
        "report": final_state.get("report"),
    }


# Placed after static routes and guarded against invalid IDs / missing records
@app.get("/files/{id}")
async def get_file_by_id(id: str = Path(..., description="ID of the file")):
    try:
        obj_id = ObjectId(id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    db_file = await files_collection.find_one({"_id": obj_id})
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "id": str(db_file["_id"]),
        "name": db_file.get("name"),
        "status": db_file.get("status"),
        "result": db_file.get("pages"),
    }