from unittest.mock import patch

import pytest

MONTH = 1714637586


def activity(**scores) -> dict:
    return {
        "date": MONTH,
        "user_postcode": "HD81",
        "user_age_range": "23-39",
        "activity": {"brisk_minutes": 20, "walking_minutes": 30, "steps": 0, **scores},
    }


@pytest.mark.parametrize(
    ("scores", "published"),
    [
        ({"effort": 7, "feeling": 2}, (7, 2)),
        ({}, (None, None)),
        ({"feeling": 2}, (None, None)),
    ],
    ids=["wheeling", "walking", "feeling-without-effort"],
)
def test_create_activity_publishes_effort_and_feeling(
    client, authenticated_user, scores, published
):
    with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        response = client.post(
            "/v2/activities",
            json=activity(**scores),
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 201  # noqa: PLR2004
    args, _kwargs = mock_add_task.call_args
    assert (args[1].activity.effort, args[1].activity.feeling) == published


def test_bulk_activities_publish_effort_and_feeling(client, authenticated_user):
    payload = {"month": MONTH, "activities": [activity(effort=10, feeling=1), activity(feeling=2)]}

    with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        response = client.post(
            "/v2/migrations/activities",
            json=payload,
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 201  # noqa: PLR2004
    args, _kwargs = mock_add_task.call_args
    published = [(a.activity.effort, a.activity.feeling) for a in args[1].activities]
    assert published == [(10, 1), (None, None)]


@pytest.mark.parametrize("url", ["/v2/activities", "/v2/migrations/activities"])
@pytest.mark.parametrize("scores", [{"effort": 0}, {"effort": 11}, {"effort": 5, "feeling": 3}])
def test_out_of_range_effort_or_feeling(client, authenticated_user, url, scores):
    body = activity(**scores)
    if "migrations" in url:
        body = {"month": MONTH, "activities": [body]}

    response = client.post(
        url, json=body, headers={"Authorization": f"Bearer {authenticated_user.token.token}"}
    )

    assert response.status_code == 422  # noqa: PLR2004
