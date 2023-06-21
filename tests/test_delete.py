from open_poen_api.schemas_and_models.models import entities as e


def test_delete_non_existing_user(client, session_2, admin_authorization_header):
    authorization_header, email = admin_authorization_header
    response = client.delete("/user/42", headers=authorization_header)
    assert response.status_code == 404
    assert session_2.get(e.User, 42) is None


def test_delete_non_existing_initiative(client, session_2, admin_authorization_header):
    authorization_header, email = admin_authorization_header
    response = client.delete("/initiative/42", headers=authorization_header)
    assert response.status_code == 404
    assert session_2.get(e.Initiative, 42) is None
