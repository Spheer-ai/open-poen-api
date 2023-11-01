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

##### Docker
The development for this API is done within a Docker container. I use "Dev Containers", a VSCode extension, to open the Docker container with the API in the Docker Compose file in VSCode. Debugging happens there as well, so no debugger is explicitly attached.

###### Step by step:

1. Open the folder in VSCode and open it inside Dev Containers. Config files are included in this repo. Tweak if needed.

2. Once inside, you can run the API from the shell with:
```
poetry run uvicorn open_poen_api:app --host 0.0.0.0 --port 8000
```

3. If you want to run the API in debug mode, I suggest you create an entry script in Python where you import the app and run it.

###### Misc

If you want to wipe all data (volumes) in the db for example, you can do:
```
docker compose down -v
```

If you need to attach to the API's container from your native shell:
```
docker exec -it open-poen-api-app-1 /bin/bash
```

##### Debugging GoCardless

Part of the API is the use of an external service, GoCardless, to import payments from user bank accounts thanks to PSD2. To debug this functionality, you can use the sandbox account that they provide, which is an optional institution_id for the relevant route.

The flow is as follows:
1. The user requests Open Poen to connect.
2. Open Poen forwards to GoCardless.
3. GoCardless forwards to the user's bank.
4. The bank redirects back to Gocardless.
5. GoCardless redirects back to Open Poen.

To make sure GoCardless can redirect the user back to your locally running API when you are debugging, you can use a service like "ngrok":
```
ngrok http 8000
```

Ngrok will then give you an URL. Set the domain name of the URL to the domain name of the API. Ngrok will then make sure the user is redirected to your locally running API:

![alt text](./images/ngrok.png)

So in this case we would set:
```
DOMAIN_NAME=9f2a-2a00-1370-819c-4201-bf7b-fc7-6d47-8401.ngrok-free.app
```

### Gotcha's
* .env files have to end with an empty line. The script that parses these for Terraform otherwise skips the last key value pair.

##### Using Docker on MacOS's M1 chip set
Docker will by default look for binaries for the M1 chip set when you install dependencies for the Docker image. There are not always available and therefore you'll probably run into problems. Solve this by:

Building the docker image explicitly for amd64/linux (Make sure that, when you update or switch your version, you rebuild manually by running this command.):
```
docker image build . -f Dockerfile.dev --platform linux/amd64 -t open-poen-api-m1
```

Ensuring the `docker compose up` command uses this image by modiyfing docker-compose.yml:
```
version: '3.3'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - 8000:8000
      - 5678:5678

etc...
```

Becomes:
```
version: '3.3'

services:
  app:
    image: open-poen-api-m1
    ports:
      - 8000:8000
      - 5678:5678

etc...
```

### CLI commands
Add a superuser:
```
poetry run open-poen add-user mark@groningen.nl --superuser --role user --password "test"
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