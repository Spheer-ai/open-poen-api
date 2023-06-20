import open_poen_api.models as m


def test_delete_non_existing_user(client, session_2, admin_authorization_header):
    authorization_header, email = admin_authorization_header
    response = client.delete("/user/42", headers=authorization_header)
    assert response.status_code == 404
    assert session_2.get(m.User, 42) is None


def test_delete_non_existing_initiative(client, session_2, admin_authorization_header):
    authorization_header, email = admin_authorization_header
    response = client.delete("/initiative/42", headers=authorization_header)
    assert response.status_code == 404
    assert session_2.get(m.Initiative, 42) is None
