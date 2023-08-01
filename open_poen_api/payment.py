from . import models as ent
from . import schemas as s
from typing import Any
from fastapi import HTTPException
from sqlmodel import Session


def check_for_forbidden_fields(payment: ent.Payment, fields: dict[str, Any]):
    if payment.type != ent.PaymentType.MANUAL:
        forbidden_fields = [
            f for f in s.FORBIDDEN_NON_MANUAL_PAYMENT_FIELDS if f in fields.keys()
        ]
        if len(forbidden_fields) > 0:
            raise HTTPException(
                status_code=403,
                detail=f"Payment type {payment.type.name} disallows changing fields {forbidden_fields}",
            )
