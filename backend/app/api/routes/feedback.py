"""Feedback API — submit and list user feedback."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.feedback import Feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class FeedbackOut(BaseModel):
    id: int
    text: str
    submitted_at: str  # ISO datetime string


@router.post("", response_model=FeedbackOut, status_code=201)
def submit_feedback(body: FeedbackIn, request: Request, db: Session = Depends(get_db)) -> FeedbackOut:
    ua = request.headers.get("user-agent", "")[:500]
    item = Feedback(text=body.text, user_agent=ua)
    db.add(item)
    db.commit()
    db.refresh(item)
    return FeedbackOut(id=item.id, text=item.text, submitted_at=item.submitted_at.isoformat())


@router.get("", response_model=list[FeedbackOut])
def list_feedback(db: Session = Depends(get_db)) -> list[FeedbackOut]:
    items = db.query(Feedback).order_by(Feedback.submitted_at.desc()).limit(100).all()
    return [FeedbackOut(id=i.id, text=i.text, submitted_at=i.submitted_at.isoformat()) for i in items]
