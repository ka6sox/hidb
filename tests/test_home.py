def test_index_guest(client):
    response = client.get("/")
    assert b"Log In" in response.data
    assert b"Register" in response.data


def test_index_logged_in(client, auth):
    auth.login()
    response = client.get("/")
    assert b"Log Out" in response.data
    assert b"Items" in response.data or b"item" in response.data
