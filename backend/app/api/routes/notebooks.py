from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, verify_csrf
from app.models.notebook import Notebook, NotebookCreate
from app.models.user import User
from app.repositories import notebooks as notebooks_repo
from app.services import db

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


@router.post("", response_model=Notebook, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
def create_notebook(data: NotebookCreate, current_user: User = Depends(get_current_user)):
    pool = db.get_pool()
    with pool.connection() as conn:
        notebook = notebooks_repo.create(conn, name=data.name, user_id=current_user.id)
        conn.commit()
    return notebook


@router.get("", response_model=list[Notebook])
def list_notebooks(current_user: User = Depends(get_current_user)):
    pool = db.get_pool()
    with pool.connection() as conn:
        return notebooks_repo.list_all(conn, user_id=current_user.id)


@router.get("/{notebook_id}", response_model=Notebook)
def get_notebook(notebook_id: int, current_user: User = Depends(get_current_user)):
    pool = db.get_pool()
    with pool.connection() as conn:
        notebook = notebooks_repo.get_by_id(conn, notebook_id, user_id=current_user.id)
        if not notebook:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
        return notebook
