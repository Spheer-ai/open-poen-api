from open_poen_api.schemas_and_models.models import entities as e


def test_delete_non_existing_user(client, session_2, admin_auth_2):
    authorization_header, _, _, _ = admin_auth_2
    response = client.delete("/user/42", headers=authorization_header)
    assert response.status_code == 404
    assert session_2.get(e.User, 42) is None


def test_delete_non_existing_initiative(client, session_2, admin_auth_2):
    authorization_header, _, _, _ = admin_auth_2
    response = client.delete("/initiative/42", headers=authorization_header)
    assert response.status_code == 404
    assert session_2.get(e.Initiative, 42) is None


def test_delete_non_existing_activity(client, session_2, admin_auth_2):
    authorization_header, _, _, _ = admin_auth_2
    response = client.delete("/initiative/1/activity/42", headers=authorization_header)
    assert response.status_code == 404
    assert session_2.get(e.Activity, 42) is None


def test_forbidden_delete(client, session_2, user_auth_2):
    authorization_header, _, _, _ = user_auth_2
    response = client.delete("/user/1", headers=authorization_header)
    assert response.status_code == 403
    assert session_2.get(e.User, 1) is not None
