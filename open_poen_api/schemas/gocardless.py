from fastapi import Query, HTTPException
from pydantic import BaseModel
from ..gocardless import INSTITUTIONS


def validate_institution_id(institution_id: str):
    if institution_id not in INSTITUTIONS["x"].institution_ids:
        raise HTTPException(status_code=400, detail="institution_id is not selectable")
    return institution_id


def validate_n_days_access(n_days_access: int):
    if n_days_access > 90:
        raise HTTPException(
            status_code=400,
            detail=f"n_days_access is {n_days_access}, but the maximum for this bank is 90 days.",
        )
    if n_days_access < 1:
        raise HTTPException(
            status_code=400,
            detail=f"n_days_access is {n_days_access}, but it can't be less than one.",
        )
    return n_days_access


def validate_n_days_history(institution_id: str, n_days_history: int):
    max_n_days = INSTITUTIONS["x"].get_transaction_total_days(institution_id)
    if n_days_history > max_n_days:
        raise HTTPException(
            status_code=400,
            detail=f"n_days_history is {n_days_history}, but the maximum for this bank is {max_n_days}.",
        )
    if n_days_history < 1:
        raise HTTPException(
            status_code=400,
            detail=f"n_days_history is {n_days_history}, but it can't be less than one.",
        )
    return n_days_history


class GocardlessInitiate(BaseModel):
    url: str
