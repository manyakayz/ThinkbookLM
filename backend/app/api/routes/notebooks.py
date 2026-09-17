from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.models.notebook import Notebook, NotebookCreate
from app.repositories import notebooks as notebooks_repo
from app.services import db

router = APIRouter(prefix="/notebooks", tags=["notebooks"])

@router.post("", response_model=Notebook)
def create_notebook(data: NotebookCreate):
    pool = db.get_pool()
    with pool.connection() as conn:
        notebook = notebooks_repo.create(conn, name=data.name)
        conn.commit()
    return notebook

@router.get("", response_model=list[Notebook])
def list_notebooks():
    pool = db.get_pool()
    with pool.connection() as conn:
        return notebooks_repo.list_all(conn)

@router.get("/{notebook_id}", response_model=Notebook)
def get_notebook(notebook_id: int):
    pool = db.get_pool()
    with pool.connection() as conn:
        notebook = notebooks_repo.get_by_id(conn, notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        return notebook

