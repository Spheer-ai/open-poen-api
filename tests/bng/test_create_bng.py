from datetime import datetime, timedelta


async def test_create_bng(async_client, async_session, user_created_by_admin):
    params = {
        "iban": "NL34BNGT5532530633",
        "expires_on": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
    }
    user_id = 1
    response = await async_client.get(f"/users/{user_id}/bng-initiate", params=params)
    print("stop")
