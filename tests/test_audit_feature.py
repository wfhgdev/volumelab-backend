import pytest
from pytest_bdd import given, parsers, scenarios, then, when


scenarios("../features/audit.feature")


@pytest.fixture
def audit_context(client):
    return {"client": client}


@given("an authenticated client account")
def authenticated_client(user_client, audit_context):
    audit_context["client"] = user_client


@given("an authenticated administrator account")
def authenticated_administrator(admin_client, audit_context):
    audit_context["client"] = admin_client


@when("I list audit events without authentication")
@when("I list audit events")
def list_audit_events(audit_context):
    audit_context["response"] = audit_context["client"].get("/audits/")


@when(parsers.parse('I list audit events with action "{action}"'))
def filter_audit_events(audit_context, action):
    audit_context["response"] = audit_context["client"].get("/audits/", params={"action": action})


@when("I list audit events with an inverted date range")
def list_audit_events_with_invalid_dates(audit_context):
    audit_context["response"] = audit_context["client"].get("/audits/", params={
        "date_from": "2026-11-25T00:00:00", "date_to": "2026-11-20T00:00:00",
    })


@when(parsers.parse("I retrieve audit event {audit_id:d}"))
def retrieve_audit_event(audit_context, audit_id):
    audit_context["response"] = audit_context["client"].get(f"/audits/{audit_id}")


@when("I create an audit event directly")
def create_audit_event(audit_context):
    audit_context["response"] = audit_context["client"].post("/audits/", json={})


@when("I update an audit event directly")
def update_audit_event(audit_context):
    audit_context["response"] = audit_context["client"].put("/audits/1", json={})


@when("I delete an audit event directly")
def delete_audit_event(audit_context):
    audit_context["response"] = audit_context["client"].delete("/audits/1")


@then(parsers.parse("the audit response status is {status_code:d}"))
def check_audit_response_status(audit_context, status_code):
    assert audit_context["response"].status_code == status_code
