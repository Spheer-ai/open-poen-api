from fastapi import APIRouter

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


# ACTIVITY
@router.post("/initiative/{initiative_id}/activity")
async def root(initiative_id: int):
    return {"name": "Eerste Activiteit"}


@router.put("/initiative/{initiative_id}/activity/{activity_id}")
async def root(initiative_id: int, activity_id: int):
    return {"name": "Eerste Activiteit"}


@router.delete("/initiative/{initiative_id}/activity/{activity_id}")
async def root(initiative_id: int, activity_id: int):
    return {"name": "Eerste Activiteit"}


@router.get("/initiative/{initiative_id}/activity/{activity_id}/users")
async def root(initiative_id: int, activity_id: int):
    return [
        {"first_name": "Mark", "last_name": "de Wijk"},
        {"first_name": "Jamal", "last_name": "Vleij"},
    ]


# ACTIVITY - PAYMENT
@router.post("/initiative/{initiative_id}/activity/{activity_id}/payment")
async def root(initiative_id: int, activity_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@router.put("/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}")
async def root(initiative_id: int, activity_id: int, payment_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@router.delete(
    "/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}"
)
async def root(initiative_id: int, activity_id: int, payment_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@router.get("/initiative/{initiative_id}/activity/{activity_id}/payments")
async def root(initiative_id: int, activity_id: int):
    return {"status_code": 200, "content": "to implement"}


# INITIATIVE
@router.post("/initiative")
async def root():
    return {"name": "Buurtproject", "created_at": "2022-6-6"}


@router.put("/initiative/{initiative_id}")
async def root(initiative_id: int):
    return {"name": "Buurtproject", "created_at": "2022-6-6"}


@router.delete("/initiative/{initiative_id}")
async def root(initiative_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@router.get("/initiatives")
async def root():
    return [
        {"name": "Buurtproject", "created_at": "2022-6-6"},
        {"name": "Smoelenboek", "created_at": "2022-2-22"},
    ]


@router.get("/initiatives/aggregate-numbers")
async def root():
    # TODO: Merge into /initiatives?
    # NOTE: Can't merge, because /initiatives will be paginated.
    return {"total_spent": 100, "total_earned": 100, "initiative_count": 22}


@router.get("/initiative/{initiative_id}/users")
async def root(initiative_id: int):
    return [
        {"first_name": "Mark", "last_name": "de Wijk"},
        {"first_name": "Jamal", "last_name": "Vleij"},
    ]


@router.get("/initiative/{initiative_id}/activities")
async def root(initiative_id: int):
    return [
        {"name": "Eerste Activiteit"},
        {"name": "Tweede Activiteit"},
    ]


# INITIATIVE - PAYMENT
@router.post("/initiative/{initiative_id}/payment")
async def root(initiative_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@router.put("/initiative/{initiative_id}/payment/{payment_id}")
async def root(initiative_id: int, payment_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@router.delete("/initiative/{initiative_id}/payment/{payment_id}")
async def root(initiative_id: int, payment_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@router.get("/initiative/{initiative_id}/payments")
async def root(initiative_id: int):
    return [
        {"amount": 10.01, "debitor": "Mark de Wijk"},
        {"amount": 9.01, "debitor": "Jamal Vleij"},
    ]


# INITIATIVE - DEBIT CARD
@router.post("/initiative/{initiative_id}/debit-card")
async def root(initiative_id: int):
    return {"card_number": 12345678, "created_at": "2011-8-1"}


@router.put("/initiative/{initiative_id}/debit-card/{debit_card_id}")
async def root(initiative_id: int, debit_card_id: int):
    # Use this to (de)couple a debit card from/to an initiative.
    return {"card_number": 12345678, "created_at": "2011-8-1"}


@router.get("/initiative/{initiative_id}/debit-cards")
async def root(initiative_id: int):
    return [
        {"card_number": 12345678, "created_at": "2011-8-1"},
        {"card_number": 12345679, "created_at": "2011-8-1"},
    ]


@router.get("/initiative/{initiative_id}/debit-cards/aggregate-numbers")
async def root(initiative_id: int):
    return [
        {"card_number": 12345678, "received": 2000, "spent": 199},
        {"card_number": 12345679, "received": 0, "spent": 0},
    ]


# USER
@router.post("/user")
async def root():
    return {"first_name": "Mark", "last_name": "de Wijk"}


@router.put("/user/{user_id}")
async def root(user_id: int):
    # Use this to link a user to an initiative.
    return {"first_name": "Mark", "last_name": "de Wijk"}


@router.delete("/user/{user_id}")
async def root(user_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@router.get("/users")
async def root():
    return [
        {"first_name": "Mark", "last_name": "de Wijk"},
        {"first_name": "Jamal", "last_name": "Vleij"},
    ]


# FUNDER
@router.post("/funder")
async def root():
    # If we continue linking to initiatives, we need to add such a query param.
    return {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"}


@router.put("/funder/{funder_id}")
async def root(funder_id: int):
    return {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"}


@router.delete("/funder/{funder_id}")
async def root(funder_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@router.get("/funders")
async def root():
    # If we continue linking to initiatives, we need to add such a query param.
    return [
        {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"},
        {"name": "Stichting Leergeld", "created_at": "2022-1-1"},
    ]


# BNG
@router.post("/bng-connection")
async def root():
    # Should accept IBAN and only available to admins.
    return {"IBAN": "NL32INGB00039845938"}


@router.delete("/bng-connection")
async def root():
    return {"status_code": 204, "content": "Succesfully deleted."}


@router.get("/bng-connection")
async def root():
    # Only available to admins.
    return {"IBAN": "NL32INGB00039845938"}


@router.get("/bng-connection/status")
async def root():
    return {
        "present": True,
        "online": True,
        "days_left": 33,
        "last_sync": "2022-12-1, 17:53",
    }
