"""Pillar II — Ask the Market. Natural-language questions over the contract warehouse."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.llm.text_to_sql import SqlGuardError, answer_question
from app.schemas.ask import AskRequest, AskResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    if len(question) > 500:
        raise HTTPException(status_code=400, detail="Question is too long (max 500 chars).")

    try:
        result = answer_question(question)
    except SqlGuardError as exc:
        raise HTTPException(status_code=422, detail=f"Could not build a safe query: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — surface a clean message, log the detail
        logger.exception("ask failed")
        raise HTTPException(status_code=500, detail="The query could not be answered.") from exc

    return AskResponse(
        question=result.question, answer=result.answer, sql=result.sql,
        sources=result.sources, row_count=result.row_count,
        columns=result.columns, rows=result.rows,
    )
