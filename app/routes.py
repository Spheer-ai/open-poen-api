from fastapi import FastAPI

app = FastAPI()


# ACTIVITY
@app.post("/initiative/{initiative_id}/activity")
async def root(initiative_id: int):
    return {"name": "Eerste Activiteit"}


@app.put("/initiative/{initiative_id}/activity/{activity_id}")
async def root(initiative_id: int, activity_id: int):
    return {"name": "Eerste Activiteit"}


@app.delete("/initiative/{initiative_id}/activity/{activity_id}")
async def root(initiative_id: int, activity_id: int):
    return {"name": "Eerste Activiteit"}


@app.get("/initiative/{initiative_id}/activity/{activity_id}/users")
async def root(initiative_id: int, activity_id: int):
    return [
        {"first_name": "Mark", "last_name": "de Wijk"},
        {"first_name": "Jamal", "last_name": "Vleij"},
    ]


# ACTIVITY - PAYMENT
@app.post("/initiative/{initiative_id}/activity/{activity_id}/payment")
async def root(initiative_id: int, activity_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@app.put("/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}")
async def root(initiative_id: int, activity_id: int, payment_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@app.delete("/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}")
async def root(initiative_id: int, activity_id: int, payment_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@app.get("/initiative/{initiative_id}/activity/{activity_id}/payments")
async def root(initiative_id: int, activity_id: int):
    return {"status_code": 200, "content": "to implement"}


# INITIATIVE
@app.post("/initiative")
async def root():
    return {"name": "Buurtproject", "created_at": "2022-6-6"}


@app.put("/initiative/{initiative_id}")
async def root(initiative_id: int):
    return {"name": "Buurtproject", "created_at": "2022-6-6"}


@app.delete("/initiative/{initiative_id}")
async def root(initiative_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@app.get("/initiatives")
async def root():
    return [
        {"name": "Buurtproject", "created_at": "2022-6-6"},
        {"name": "Smoelenboek", "created_at": "2022-2-22"},
    ]


@app.get("/initiatives/aggregate-numbers")
async def root():
    # TODO: Merge into /initiatives?
    # NOTE: Can't merge, because /initiatives will be paginated.
    return {"total_spent": 100, "total_earned": 100, "initiative_count": 22}


@app.get("/initiative/{initiative_id}/users")
async def root(initiative_id: int):
    return [
        {"first_name": "Mark", "last_name": "de Wijk"},
        {"first_name": "Jamal", "last_name": "Vleij"},
    ]


@app.get("/initiative/{initiative_id}/activities")
async def root(initiative_id: int):
    return [
        {"name": "Eerste Activiteit"},
        {"name": "Tweede Activiteit"},
    ]


# INITIATIVE - PAYMENT
@app.post("/initiative/{initiative_id}/payment")
async def root(initiative_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@app.put("/initiative/{initiative_id}/payment/{payment_id}")
async def root(initiative_id: int, payment_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@app.delete("/initiative/{initiative_id}/payment/{payment_id}")
async def root(initiative_id: int, payment_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@app.get("/initiative/{initiative_id}/payments")
async def root(initiative_id: int):
    return [
        {"amount": 10.01, "debitor": "Mark de Wijk"},
        {"amount": 9.01, "debitor": "Jamal Vleij"},
    ]


# INITIATIVE - DEBIT CARD
@app.post("/initiative/{initiative_id}/debit-card")
async def root(initiative_id: int):
    return {"card_number": 12345678, "created_at": "2011-8-1"}


@app.put("/initiative/{initiative_id}/debit-card/{debit_card_id}")
async def root(initiative_id: int, debit_card_id: int):
    # Use this to (de)couple a debit card from/to an initiative.
    return {"card_number": 12345678, "created_at": "2011-8-1"}


@app.get("/initiative/{initiative_id}/debit-cards")
async def root(initiative_id: int):
    return [
        {"card_number": 12345678, "created_at": "2011-8-1"},
        {"card_number": 12345679, "created_at": "2011-8-1"},
    ]


@app.get("/initiative/{initiative_id}/debit-cards/aggregate-numbers")
async def root(initiative_id: int):
    return [
        {"card_number": 12345678, "received": 2000, "spent": 199},
        {"card_number": 12345679, "received": 0, "spent": 0},
    ]


# USER
@app.post("/user")
async def root():
    return {"first_name": "Mark", "last_name": "de Wijk"}


@app.put("/user/{user_id}")
async def root(user_id: int):
    # Use this to link a user to an initiative.
    return {"first_name": "Mark", "last_name": "de Wijk"}


@app.delete("/user/{user_id}")
async def root(user_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@app.get("/users")
async def root():
    return [
        {"first_name": "Mark", "last_name": "de Wijk"},
        {"first_name": "Jamal", "last_name": "Vleij"},
    ]


# FUNDER
@app.post("/funder")
async def root():
    # If we continue linking to initiatives, we need to add such a query param.
    return {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"}


@app.put("/funder/{funder_id}")
async def root(funder_id: int):
    return {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"}


@app.delete("/funder/{funder_id}")
async def root(funder_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@app.get("/funders")
async def root():
    # If we continue linking to initiatives, we need to add such a query param.
    return [
        {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"},
        {"name": "Stichting Leergeld", "created_at": "2022-1-1"},
    ]


# BNG
@app.post("/bng-connection")
async def root():
    # Should accept IBAN and only available to admins.
    return {"IBAN": "NL32INGB00039845938"}


@app.delete("/bng-connection")
async def root():
    return {"status_code": 204, "content": "Succesfully deleted."}


@app.get("/bng-connection")
async def root():
    # Only available to admins.
    return {"IBAN": "NL32INGB00039845938"}


@app.get("/bng-connection/status")
async def root():
    return {
        "present": True,
        "online": True,
        "days_left": 33,
        "last_sync": "2022-12-1, 17:53",
    }
