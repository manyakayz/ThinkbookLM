from __future__ import annotations
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user, verify_csrf
from app.models.document import Document, DocumentUploadResult
from app.models.user import User
from app.repositories import documents as documents_repo
from app.repositories import notebooks as notebooks_repo
from app.services import db, storage, vector_store
from app.services.ingestion import pipeline

router = APIRouter(tags=["documents"])


@router.post(
    "/notebooks/{notebook_id}/documents",
    response_model=DocumentUploadResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def upload_document(
    notebook_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    pool = db.get_pool()
    with pool.connection() as conn:
        if not notebooks_repo.exists(conn, notebook_id, user_id=current_user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")

    content = await file.read()
    file_size = len(content)

    try:
        extension = storage.validate_upload(file.filename, file_size)
    except storage.UnsupportedFileType as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except storage.FileTooLarge as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e))
    except storage.EmptyFile as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

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
                user_id=current_user.id,
            )
            conn.commit()
    except Exception:
        storage.delete(stored_filename)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create document record.")

    # Process synchronously for this milestone
    updated_doc, chunk_count = pipeline.process_document(document.id)

    return DocumentUploadResult(document=updated_doc, chunk_count=chunk_count)


@router.get("/notebooks/{notebook_id}/documents", response_model=list[Document])
def list_documents(notebook_id: int, current_user: User = Depends(get_current_user)):
    pool = db.get_pool()
    with pool.connection() as conn:
        if not notebooks_repo.exists(conn, notebook_id, user_id=current_user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
        return documents_repo.list_for_notebook(conn, notebook_id, user_id=current_user.id)


@router.get("/documents/{document_id}", response_model=Document)
def get_document(document_id: int, current_user: User = Depends(get_current_user)):
    pool = db.get_pool()
    with pool.connection() as conn:
        document = documents_repo.get_by_id(conn, document_id, user_id=current_user.id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return document


@router.delete("/documents/{document_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_csrf)])
def delete_document(document_id: int, current_user: User = Depends(get_current_user)):
    """Delete a document, its database records, stored file, and ChromaDB vectors."""
    pool = db.get_pool()
    with pool.connection() as conn:
        document = documents_repo.get_by_id(conn, document_id, user_id=current_user.id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        stored_filename = documents_repo.get_stored_filename(conn, document_id, user_id=current_user.id)

        # 1. Delete from PostgreSQL (cascades to chunks)
        documents_repo.delete(conn, document_id, user_id=current_user.id)
        conn.commit()

    # 2. Delete vectors from ChromaDB
    try:
        vector_store.delete_document(document_id)
    except Exception:
        pass

    # 3. Delete physical file from disk
    if stored_filename:
        storage.delete(stored_filename)

    return {"deleted": True, "document_id": document_id}
