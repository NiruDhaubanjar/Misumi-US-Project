from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from tasks import process_folder_task

app = FastAPI(title="HTML to Excel Processor")

class FolderRequest(BaseModel):
    folder_name: str 

INPUT_FOLDER = os.getenv("INPUT_FOLDER", "./data/Input Files")
OUTPUT_FOLDER = os.getenv("OUTPUT_FOLDER", "./data/Output Files")

# --- For selected folders ---
class FolderList(BaseModel):
    folders: list[str]

@app.post("/process_selected_folders/")
def process_selected_folders(data: FolderList):
    tasks = []
    for folder_name in data.folders:
        folder_path = os.path.join(INPUT_FOLDER, folder_name)
        if os.path.exists(folder_path):
            try:
                task = process_folder_task.delay(folder_path, INPUT_FOLDER, OUTPUT_FOLDER)
                tasks.append(task.id)
            except:
                print(f"⚠️ Failed to dispatch task for {folder_path}: {e}")
    response = {
        "total_folders": len(tasks),
        "dispatched_tasks": tasks,
        "message": f"{len(tasks)} folders dispatched successfully."
    }
    return response


@app.post("/process_all_folders/")
def process_all_folders():
    html_folders = [
        root for root, _, files in os.walk(INPUT_FOLDER)
        if any(f.lower().endswith(".html") for f in files)
        and os.path.basename(root) != "Product_Specification"
    ]
    if not html_folders:
        return {"message": " No folders with HTML files found."}

    tasks = []
    for folder in html_folders:
        task = process_folder_task.delay(folder, INPUT_FOLDER, OUTPUT_FOLDER)
        tasks.append(task.id)

    response = {
        "total_folders": len(tasks),
        "dispatched_tasks": tasks,
        "message": f"{len(tasks)} folders dispatched successfully."
    }
    return response

@app.get("/task-status/{task_id}")
async def task_status(task_id: str):
    from celery.result import AsyncResult
    result = AsyncResult(task_id)
    return {"task_id": task_id, "status": result.status, "result": result.result}
