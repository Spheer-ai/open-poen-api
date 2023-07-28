# open-poen-api
The API of Open Poen - an open spending platform where we make publicly available how money from the community is spent.

### commands

```
poetry run uvicorn open_poen_api.app:app --reload
```

Start DB.
```
docker compose up
```

Stop and wipe DB.
```
docker compose down -v
```

Login and save bearer token as a variable (Fish).
```
set token (http --form POST ":8000/auth/jwt/login" username=mark@gmail.com password=test | jq -r '.access_token')
```

Initiate Gocardless.
```
http GET ":8000/users/1/gocardless-initiate?institution_id=ING_INGBNL2A" "Authorization: Bearer $token"
```

