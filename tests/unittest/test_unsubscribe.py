def test_unsubscribe_page_is_rendered(client):
    response = client.get("/unsubscribe/")

    assert response.status_code == 200  # noqa: PLR2004
    assert response.headers["content-type"].startswith("text/html")
    assert "Unsubscribe from Mailing List" in response.text
