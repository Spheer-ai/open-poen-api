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

Add a super_user:
```
poetry run open-poen add-user mark@groningen.nl --superuser --role user --password "test"
```

Login and save bearer token as a variable (Fish).
```
set token (http --form POST ":8000/auth/jwt/login" username=mark@groningen.nl password=test | jq -r '.access_token')
```

Initiate Gocardless.
```
http GET ":8000/users/1/gocardless-initiate?institution_id=ING_INGBNL2A" "Authorization: Bearer $token"
```

Create a new user (Loeki) with role 'administrator":
```
http POST ":8000/user" \
"Authorization: Bearer $token" \
email="loeki@amsterdam.nl" \
first_name="Loeki" \
last_name="Den Uyl" \
biography="Medewerker bij Gemeente Amsterdam" \
role="administrator" \
```

```
http POST ":8000/auth/forgot-password" \
email="loeki@amsterdam.nl"
```

Retrieve the token from the WebUI of Mailhog and change the password to "test":
```
set loeki_token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwicGFzc3dvcmRfZmdwdCI6IiQyYiQxMiRVZFY0bS5ZR3VhLlhUNC9kRDUuMlllRDZJeUtBMUM5anozWHRBeEZlN1pUaEh5ci9lcUFpaSIsImF1ZCI6ImZhc3RhcGktdXNlcnM6cmVzZXQiLCJleHAiOjE2OTA4ODE4MjZ9.DQKMpdbsSXud0KWWRtEK7hSGIc3TqtOAjIQMCrwGbvY
http POST ":8000/auth/reset-password" \
token=$loeki_token \
password="test"
```

Logged out list view:
```
http GET ":8000/users"
```

Logged in as superuser list view:
```
http GET ":8000/users" "Authorization: Bearer $token"
```

Change Loeki's role as anonymous:
```
http PATCH ":8000/user/2" \
role="financial"
```

Change Loeki's role as Loeki herself as administrator:
```
http PATCH ":8000/user/2" \
"Authorization: Bearer $loeki_token" \
role="financial"
```

Change Loeki's role as super_user.
```
http PATCH ":8000/user/2" \
"Authorization: Bearer $token" \
role="financial"
```

Change Loeki's role to a non existing role as super_user.
```
http PATCH ":8000/user/2" \
"Authorization: Bearer $token" \
role="non_existing_role"
```