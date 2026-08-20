import asyncio
from unittest.mock import patch

import pytest

from utils.background_jobs import run_tracked_job


async def _successful_job() -> None:
    return None


async def _failing_job() -> None:
    raise RuntimeError("boom")


def test_run_tracked_job_transitions_to_queued() -> None:
    with patch("service.background_job_service.update_job_status") as mock_update:
        asyncio.run(run_tracked_job("job-123", _successful_job))

    mock_update.assert_called_once_with("job-123", "queued")


def test_run_tracked_job_marks_failed_on_exception() -> None:
    with (
        patch("service.background_job_service.update_job_status") as mock_update,
        pytest.raises(RuntimeError),
    ):
        asyncio.run(run_tracked_job("job-123", _failing_job))

    mock_update.assert_called_once_with("job-123", "failed")
