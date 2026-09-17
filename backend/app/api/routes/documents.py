from __future__ import annotations
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from app.models.document import Document, DocumentUploadResult
from app.repositories import documents as documents_repo
from app.repositories import notebooks as notebooks_repo
from app.services import db, storage
from app.services.ingestion import pipeline

router = APIRouter(tags=["documents"])

@router.post("/notebooks/{notebook_id}/documents", response_model=DocumentUploadResult)
async def upload_document(notebook_id: int, file: UploadFile = File(...)):
    pool = db.get_pool()
    with pool.connection() as conn:
        if not notebooks_repo.exists(conn, notebook_id):
            raise HTTPException(status_code=404, detail="Notebook not found")

    content = await file.read()
    file_size = len(content)
    
    try:
        extension = storage.validate_upload(file.filename, file_size)
    except storage.UnsupportedFileType as e:
        raise HTTPException(status_code=400, detail=str(e))
    except storage.FileTooLarge as e:
        raise HTTPException(status_code=413, detail=str(e))
    except storage.EmptyFile as e:
        raise HTTPException(status_code=400, detail=str(e))

    stored_filename = storage.generate_stored_filename(extension)
    storage.save(stored_filename, content)

    try:
        with pool.connection() as conn:
            document = documents_repo.create(
                conn,
                notebook_id=notebook_id,
                original_filename=file.filename,
                stored_filename=stored_filename,
                file_type=extension,
                file_size=file_size,
            )
            conn.commit()
    except Exception as e:
        storage.delete(stored_filename)
        raise HTTPException(status_code=500, detail="Failed to create document record.")

    # Process synchronously for this milestone
    updated_doc, chunk_count = pipeline.process_document(document.id)

    return DocumentUploadResult(document=updated_doc, chunk_count=chunk_count)

@router.get("/notebooks/{notebook_id}/documents", response_model=list[Document])
def list_documents(notebook_id: int):
    pool = db.get_pool()
    with pool.connection() as conn:
        if not notebooks_repo.exists(conn, notebook_id):
            raise HTTPException(status_code=404, detail="Notebook not found")
        return documents_repo.list_for_notebook(conn, notebook_id)

@router.get("/documents/{document_id}", response_model=Document)
def get_document(document_id: int):
    pool = db.get_pool()
    with pool.connection() as conn:
        document = documents_repo.get_by_id(conn, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document

