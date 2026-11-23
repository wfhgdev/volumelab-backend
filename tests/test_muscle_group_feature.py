import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import text

from app.models.app_user_model import AppUserModel
from app.models.muscle_group_model import MuscleGroupModel
from tests.catalog_support import associate_group


scenarios("../features/muscle_group.feature")


@pytest.fixture
def group_context(muscle_group_api):
    client, db, admin = muscle_group_api
    return {"client": client, "db": db, "creator": admin.id, "group_id": None, "response": None}


@given("an administrator exists")
def administrator_exists(group_context):
    assert group_context["creator"] > 0


@given("a client exists")
def client_exists(group_context):
    user = group_context["db"].get(AppUserModel, group_context["creator"])
    user.role = "CLIENTE"
    group_context["db"].commit()


@given("the creator does not exist")
def missing_creator(group_context):
    group_context["creator"] = 999


@given(parsers.parse('a muscle group named "{name}" exists'))
def existing_group(group_context, name):
    record = MuscleGroupModel(name=name, created_by=group_context["creator"])
    group_context["db"].add(record)
    group_context["db"].commit()
    group_context["group_id"] = record.id


@given("the muscle group is associated with an exercise")
def associated_group(group_context):
    associate_group(group_context["db"], group_context["group_id"], group_context["creator"])


@given("the muscle group has an anonymized creator")
def anonymized_group(group_context):
    record = group_context["db"].get(MuscleGroupModel, group_context["group_id"])
    record.created_by = None
    group_context["db"].commit()


@when(parsers.parse('I create a muscle group named "{name}"'))
def create_group(group_context, name):
    group_context["response"] = group_context["client"].post("/muscle-groups/", json={
        "name": name, "created_by": group_context["creator"],
    })


@when("I list muscle groups")
def list_groups(group_context):
    group_context["response"] = group_context["client"].get("/muscle-groups/")


@when("I retrieve the muscle group")
def retrieve_group(group_context):
    group_context["response"] = group_context["client"].get(f"/muscle-groups/{group_context['group_id']}")


@when("I retrieve an unknown muscle group")
def retrieve_unknown_group(group_context):
    group_context["response"] = group_context["client"].get("/muscle-groups/999")


@when(parsers.parse('I update its description to "{description}"'))
def update_description(group_context, description):
    group_context["response"] = group_context["client"].put(
        f"/muscle-groups/{group_context['group_id']}", json={"description": description},
    )


@when("I assign a client as its creator")
def assign_client_creator(group_context):
    db = group_context["db"]
    user = AppUserModel(name="Client", email="client@example.com", password_hash="test", role="CLIENTE", status="ACTIVO")
    db.add(user)
    db.commit()
    group_context["response"] = group_context["client"].put(
        f"/muscle-groups/{group_context['group_id']}", json={"created_by": user.id},
    )


@when("I delete the muscle group")
def delete_group(group_context):
    group_context["response"] = group_context["client"].delete(f"/muscle-groups/{group_context['group_id']}")


@then(parsers.parse("the response status is {status_code:d}"))
def response_status(group_context, status_code):
    assert group_context["response"].status_code == status_code


@then(parsers.parse('the muscle group name is "{name}"'))
def group_name(group_context, name):
    assert group_context["response"].json()["name"] == name


@then(parsers.parse('the description is "{description}"'))
def group_description(group_context, description):
    assert group_context["response"].json()["description"] == description


@then(parsers.re(r"the list contains (?P<count>\d+) muscle groups?"))
def group_count(group_context, count):
    assert len(group_context["response"].json()) == int(count)


@then("the muscle group no longer exists")
def deleted_group(group_context):
    assert group_context["client"].get(f"/muscle-groups/{group_context['group_id']}").status_code == 404


@then("the muscle group and its association remain stored")
def preserved_group(group_context):
    assert group_context["client"].get(f"/muscle-groups/{group_context['group_id']}").status_code == 200
    assert group_context["db"].execute(text("SELECT COUNT(*) FROM muscle_workout")).scalar_one() == 1


@then("its creator is null")
def creator_is_null(group_context):
    assert group_context["response"].json()["created_by"] is None
