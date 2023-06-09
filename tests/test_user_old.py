# @pytest.mark.parametrize(
#     "auth, status_code, email_in_db",
#     [
#         ("user_admin_2", 200, True),
#         ("user_financial_2", 403, False),
#         ("user_user_2", 403, False),
#         ("user_guest_2", 401, False),
#     ],
# )
# def test_post_user(client, session_2, auth, status_code, email_in_db, request):
#     authorization_header, _ = request.getfixturevalue(auth)
#     user_data = {
#         "email": "janedoe@gmail.com",
#         "role": "financial",
#     }
#     response = client.post("/user", json=user_data, headers=authorization_header)
#     assert response.status_code == status_code
#     email_exists = "janedoe@gmail.com" in [
#         i.email for i in session_2.exec(select(ent.User)).all()
#     ]
#     assert email_exists == email_in_db


# def test_duplicate_email(client, user_admin_2):
#     user_data = {
#         "email": "user1@example.com",
#     }
#     authorization_header, _ = user_admin_2
#     response = client.post("/user", json=user_data, headers=authorization_header)
#     assert response.status_code == 400
#     assert response.json()["detail"] == "Email address already registered"


# def test_update_email_to_none(client, user_admin_2):
#     new_user_data = {"email": None, "first_name": "mark"}
#     header, _ = user_admin_2
#     response = client.patch(
#         f"/user/1",
#         json=new_user_data,
#         headers=header,
#     )
#     assert response.status_code == 422


# @pytest.mark.parametrize(
#     "auth, user_data, expected_status_code",
#     [
#         (
#             "user_admin_2",
#             {
#                 "first_name": "New First Name",
#                 "last_name": "New Last Name",
#                 "email": "different@address.com",
#             },
#             200,
#         ),
#         ("user_admin_2", {"hidden": True}, 200),
#         (
#             "user_financial_2",
#             {
#                 "first_name": "New First Name",
#                 "last_name": "New Last Name",
#                 "email": "different@address.com",
#             },
#             403,
#         ),
#         ("user_financial_2", {"hidden": True}, 403),
#         (
#             "user_user_2",
#             {
#                 "first_name": "New First Name",
#                 "last_name": "New Last Name",
#                 "email": "different@address.com",
#             },
#             403,
#         ),
#         ("user_user_2", {"hidden": True}, 403),
#         (
#             "user_user_owner_2",
#             {
#                 "first_name": "New First Name",
#                 "last_name": "New Last Name",
#                 "email": "different@address.com",
#             },
#             200,
#         ),
#         ("user_user_owner_2", {"hidden": True}, 403),
#         (
#             "user_guest_2",
#             {
#                 "first_name": "New First Name",
#                 "last_name": "New Last Name",
#                 "email": "different@address.com",
#             },
#             401,
#         ),
#         ("user_guest_2", {"hidden": True}, 401),
#     ],
# )
# def test_patch_user(client, session_2, auth, user_data, expected_status_code, request):
#     authorization_header, user_id = request.getfixturevalue(auth)
#     existing_user = session_2.get(ent.User, user_id)

#     for field, new_value in user_data.items():
#         assert getattr(existing_user, field) != new_value

#     response = client.patch(
#         f"/user/{existing_user.id}",
#         json=user_data,
#         headers=authorization_header,
#     )

#     assert response.status_code == expected_status_code

#     if expected_status_code == 200:
#         session_2.refresh(existing_user)
#         for field, new_value in user_data.items():
#             assert getattr(existing_user, field) == new_value


# @pytest.mark.parametrize(
#     "auth, status_code, should_see_email",
#     [
#         ("user_admin_2", 200, True),
#         ("user_financial_2", 200, False),
#         ("user_user_2", 200, False),
#         ("user_guest_2", 401, False),
#     ],
# )
# def test_get_users(client, auth, status_code, should_see_email, request):
#     authorization_header, _ = request.getfixturevalue(auth)
#     response = client.get(
#         "/users",
#         headers=authorization_header,
#     )
#     assert response.status_code == status_code
#     if status_code == 200:
#         response_json = response.json()
#         assert "users" in response_json
#         users = response_json["users"]
#         assert isinstance(users, list)
#         for user in users:
#             if should_see_email:
#                 assert "email" in user
#             else:
#                 assert "email" not in user


# def test_retrieve_token(client, session_2):
#     data = {"username": "user1@example.com", "password": "DEBUG_PASSWORD"}
#     headers = {"Content-Type": "application/x-www-form-urlencoded"}

#     response = client.post("/token", headers=headers, data=data)
#     assert response.status_code == 200
#     assert (
#         "access_token" in response.json() and response.json()["token_type"] == "bearer"
#     )


# def test_add_non_existing_initiative(client, session_2, user_admin_2):
#     user_data = {
#         "email": "johndoe@gmail.com",
#         "role": "admin",
#         "initiative_ids": [42],
#     }
#     authorization_header, _ = user_admin_2
#     response = client.post("/user", json=user_data, headers=authorization_header)
#     assert response.status_code == 404
#     assert (
#         response.json()["detail"]
#         == "One or more instances of Initiative to link do not exist"
#     )


# def test_add_existing_initiative(client, session_2, user_admin_2):
#     user_data = {
#         "email": "johndoe@gmail.com",
#         "role": "admin",
#         "initiative_ids": [1],
#     }
#     authorization_header, _ = user_admin_2
#     response = client.post("/user", json=user_data, headers=authorization_header)
#     assert response.status_code == 200
#     assert response.json()["initiatives"][0]["id"] == 1


# def test_add_duplicate_initiatives(client, session_2, user_admin_2):
#     user_data = {
#         "email": "johndoe@gmail.com",
#         "role": "admin",
#         "initiative_ids": [1, 1],
#     }
#     authorization_header, _ = user_admin_2
#     response = client.post("/user", json=user_data, headers=authorization_header)
#     assert response.status_code == 404


# def test_add_two_initiatives(client, session_2, user_admin_2):
#     user_data = {
#         "email": "johndoe@gmail.com",
#         "role": "admin",
#         "initiative_ids": [1, 2],
#     }
#     authorization_header, _ = user_admin_2
#     response = client.post("/user", json=user_data, headers=authorization_header)
#     assert response.status_code == 200
#     assert response.json()["initiatives"][0]["id"] in (1, 2)
#     assert response.json()["initiatives"][1]["id"] in (1, 2)
#     assert len(response.json()["initiatives"]) == 2
