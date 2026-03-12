"""Роуты звонков."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_session_manager
from app.models.call_session import SessionManager

router = APIRouter(prefix="/api", tags=["calls"])


@router.get("/calls")
async def get_calls(sm: SessionManager = Depends(get_session_manager)):
    """Список активных и завершённых звонков."""
    return {
        "active": [s.to_dict() for s in sm.active_calls],
        "archived": [s.to_dict() for s in sm.archived_calls],
    }


@router.get("/calls/{call_id}")
async def get_call(call_id: str, sm: SessionManager = Depends(get_session_manager)):
    """Детали одного звонка."""
    session = sm.get_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Звонок не найден")
    return session.to_dict()
