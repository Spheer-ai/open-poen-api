# open-poen-api
The API of Open Poen - an open spending platform where we make publicly available how money from the community is spent.

### Setup
##### Configure git-crypt
The policy file with all permission related configuration is encrypted for security. Make sure you create a GPG key and supply it to @marcus302.

##### Get certificates for BNG
Place your debugging and/or production certificates in /auth. Debugging certificates you can get [here](https://api.xs2a-sandbox.bngbank.nl/developer-portal/guides/sandbox-certificates).

##### Set environment variabels
Use the .env.example files to configure your environment variables. Afterwards remove the .example suffix.

##### Use Poetry
Poetry is used for tracking dependencies and managing the virtual environment. Make sure you use Python **3.11** or higher for running this API.



Start the API.
```
poetry run uvicorn open_poen_api.app:app --reload
```

Start the DB and some development tools.
```
docker compose up
```

Stop DB and development tools. Add -v to wipe the DB.
```
docker compose down -v
```

Attach to the app container.
```
docker exec -it open-poen-api-app-1 /bin/bash
```

### CLI commands
Add a super_user:
```
docker exec -it open-poen-api-app-1 open-poen add-user mark@groningen.nl --superuser --role user --password "test"
```

### Interacting with the API
Login and save bearer token as a variable (Fish shell).
```
set token (http --form POST ":8000/auth/jwt/login" username=mark@groningen.nl password=test | jq -r '.access_token')
```

Initiate Gocardless.
```
http GET ":8000/users/1/gocardless-initiate?institution_id=ING_INGBNL2A&n_days_access=7&n_days_history=14" "Authorization: Bearer $token"
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

Ask for a new password.
```
http POST ":8000/auth/forgot-password" \
email="loeki@amsterdam.nl"
```

Retrieve the token from the WebUI of Mailhog and change the password to "test" The bearer token is saved in a variable for later. (Fish shell):
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

### API Docs
You can look at the automatically generated OpenAPI documentation by navigating to /docs.