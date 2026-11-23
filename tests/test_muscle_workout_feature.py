import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import text


scenarios("../features/muscle_workout.feature")


@pytest.fixture
def association_context(association_api):
    client, db, workout, group = association_api
    return {
        "client": client, "db": db, "workout_id": workout.id,
        "muscle_group_id": group.id, "response": None,
    }


def resource(context):
    return f"/muscle-workouts/{context['workout_id']}/{context['muscle_group_id']}"


def create_association(context, role, **extra):
    return context["client"].post("/muscle-workouts/", json={
        "workout_id": context["workout_id"], "muscle_group_id": context["muscle_group_id"],
        "muscle_role": role,
    } | extra)


@given("an exercise and a muscle group exist")
def parent_records(association_context):
    assert association_context["workout_id"] > 0
    assert association_context["muscle_group_id"] > 0


@given("a primary association exists")
def existing_association(association_context):
    assert create_association(association_context, "PRIMARIO").status_code == 201


@given("the requested exercise does not exist")
def missing_workout(association_context):
    association_context["workout_id"] = 999


@given("the requested muscle group does not exist")
def missing_group(association_context):
    association_context["muscle_group_id"] = 999


@given("the exercise has a recorded set")
def recorded_set(association_context):
    association_context["db"].execute(text(
        "INSERT INTO workout_set (exercise_id) VALUES (:id)"
    ), {"id": association_context["workout_id"]})
    association_context["db"].commit()


@when(parsers.parse('I associate the group as "{role}"'))
def associate_group(association_context, role):
    association_context["response"] = create_association(association_context, role)


@when(parsers.parse('I associate the group as "{role}" with weighing {weighing:d}'))
def associate_with_weighing(association_context, role, weighing):
    association_context["response"] = create_association(association_context, role, weighing=weighing)


@when("I list associations")
def list_associations(association_context):
    association_context["response"] = association_context["client"].get("/muscle-workouts/")


@when("I filter associations by the muscle group")
def filter_associations(association_context):
    association_context["response"] = association_context["client"].get(
        f"/muscle-workouts/?muscle_group_id={association_context['muscle_group_id']}",
    )


@when("I retrieve the association")
def retrieve_association(association_context):
    association_context["response"] = association_context["client"].get(resource(association_context))


@when("I change the muscle role to secondary")
def update_role(association_context):
    association_context["response"] = association_context["client"].put(
        resource(association_context), json={"muscle_role": "SECUNDARIO"},
    )


@when("I remove the association")
def remove_association(association_context):
    association_context["response"] = association_context["client"].delete(resource(association_context))


@then(parsers.parse("the response status is {status_code:d}"))
def response_status(association_context, status_code):
    assert association_context["response"].status_code == status_code


@then(parsers.parse("the weighing is {weighing:d}"))
def weighing_value(association_context, weighing):
    assert association_context["response"].json()["weighing"] == weighing


@then(parsers.re(r"the list contains (?P<count>\d+) associations?"))
def association_count(association_context, count):
    assert len(association_context["response"].json()) == int(count)


@then("the association no longer exists")
def missing_association(association_context):
    assert association_context["client"].get(resource(association_context)).status_code == 404


@then("both parent records remain stored")
def preserved_parents(association_context):
    client = association_context["client"]
    assert client.get(f"/workouts/{association_context['workout_id']}").status_code == 200
    assert client.get(f"/muscle-groups/{association_context['muscle_group_id']}").status_code == 200


@then("the primary association remains unchanged")
def preserved_association(association_context):
    response = association_context["client"].get(resource(association_context))
    assert response.status_code == 200
    assert response.json()["muscle_role"] == "PRIMARIO"
    assert response.json()["weighing"] == 100
