from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from main import _drop_query_string
from models import User
from service.open_telemetry_service import (
    ACTIVITIES_FLOW,
    AUTH_FLOW_KEY,
    AUTH_STEP_KEY,
    FLOW_KEY,
    MIGRATIONS_FLOW,
    NHS_LOGIN_FLOW,
    STEP_ACTIVITY_PUBLISH,
    STEP_JWT_VALIDATION,
    STEP_KEY,
    STEP_MIGRATION_PUBLISH,
    STEP_TOKEN_EXCHANGE,
    _strip_query,
    auth_step_span,
    message_trace_attributes,
    step_span,
    tracer,
)

_exporter = InMemorySpanExporter()
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(_exporter))


@pytest.fixture(autouse=True)
def span_exporter():
    _exporter.clear()
    yield _exporter


def test_auth_step_span_attributes(span_exporter) -> None:
    with auth_step_span(STEP_TOKEN_EXCHANGE) as span:
        assert span.is_recording()

    finished = span_exporter.get_finished_spans()[-1]
    assert finished.name == STEP_TOKEN_EXCHANGE
    assert finished.attributes[AUTH_STEP_KEY] == STEP_TOKEN_EXCHANGE
    assert finished.attributes[AUTH_FLOW_KEY] == NHS_LOGIN_FLOW


def test_auth_step_span_error_status(span_exporter) -> None:
    with pytest.raises(ValueError), auth_step_span(STEP_TOKEN_EXCHANGE):
        raise ValueError("foo")

    span = span_exporter.get_finished_spans()[-1]
    assert span.status.status_code == StatusCode.ERROR
    assert span.status.description == "ValueError"
    # only the exception type should end up on the span, not the message
    assert not span.events
    assert "foo" not in str(span.attributes)


def test_step_span_attributes(span_exporter) -> None:
    with step_span(STEP_MIGRATION_PUBLISH, MIGRATIONS_FLOW) as span:
        assert span.is_recording()

    finished = span_exporter.get_finished_spans()[-1]
    assert finished.name == STEP_MIGRATION_PUBLISH
    assert finished.attributes[STEP_KEY] == STEP_MIGRATION_PUBLISH
    assert finished.attributes[FLOW_KEY] == MIGRATIONS_FLOW


def test_step_span_error_status(span_exporter) -> None:
    with pytest.raises(ValueError), step_span(STEP_ACTIVITY_PUBLISH, ACTIVITIES_FLOW):
        raise ValueError("boom")

    span = span_exporter.get_finished_spans()[-1]
    assert span.status.status_code == StatusCode.ERROR
    assert span.status.description == "ValueError"
    # only the exception type should end up on the span, not the message
    assert not span.events
    assert "boom" not in str(span.attributes)


def test_query_string_redaction(span_exporter) -> None:
    scope = {"path": "/nhs_login/callback"}
    with tracer.start_as_current_span("server-span") as span:
        _drop_query_string(span, scope)

    recorded = span_exporter.get_finished_spans()[-1]
    assert recorded.attributes["http.target"] == "/nhs_login/callback"
    assert recorded.attributes["http.url"] == "/nhs_login/callback"
    assert recorded.attributes["url.full"] == "/nhs_login/callback"
    assert recorded.attributes["url.query"] == "REDACTED"

    # no-op when the instrumentation passes no span
    _drop_query_string(None, scope)


def test_outbound_url_redaction(span_exporter) -> None:
    class FakeRequest:
        url = "https://auth.example.nhs.uk/token?code=abc123&state=xyz"

    with tracer.start_as_current_span("client-span") as span:
        _strip_query(span, FakeRequest())

    recorded = span_exporter.get_finished_spans()[-1]
    assert recorded.attributes["http.url"] == "https://auth.example.nhs.uk/token"
    assert recorded.attributes["url.full"] == "https://auth.example.nhs.uk/token"


def test_message_trace_attributes(span_exporter) -> None:
    with tracer.start_as_current_span("message-producer"):
        attributes = message_trace_attributes()

    assert len(attributes) == 1
    attribute = next(iter(attributes.values()))
    assert attribute["DataType"] == "String"
    assert "Root=" in attribute["StringValue"]


def test_jwt_validation_span(client: TestClient, authenticated_user: User, span_exporter) -> None:
    resp = client.get(
        "/v1/users/", headers={"Authorization": f"Bearer {authenticated_user.token.token}"}
    )
    assert resp.status_code == HTTPStatus.OK

    spans = [s for s in span_exporter.get_finished_spans() if s.name == STEP_JWT_VALIDATION]
    assert spans
    span = spans[-1]
    assert span.attributes[AUTH_STEP_KEY] == STEP_JWT_VALIDATION
    assert span.attributes[AUTH_FLOW_KEY] == NHS_LOGIN_FLOW
    assert "auth.cache_hit" in span.attributes


def test_callback_code_not_in_spans(client: TestClient, span_exporter) -> None:
    resp = client.get(
        "/nhs_login/callback?code=abc123def456&state=active10_12345",
        follow_redirects=False,
    )
    assert resp.status_code == HTTPStatus.TEMPORARY_REDIRECT

    spans = span_exporter.get_finished_spans()
    assert spans
    for span in spans:
        for value in span.attributes.values():
            assert "abc123def456" not in str(value)
