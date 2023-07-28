from fastapi import Query, HTTPException
from pydantic import BaseModel
from ..gocardless import INSTITUTION_ID_TO_TRANSACTION_TOTAL_DAYS


def validate_institution_id(institution_id: str = Query(...)):
    if institution_id not in INSTITUTION_ID_TO_TRANSACTION_TOTAL_DAYS:
        raise HTTPException(status_code=400, detail="institution_id is not selectable")
    return institution_id


class GocardlessInitiate(BaseModel):
    url: str
