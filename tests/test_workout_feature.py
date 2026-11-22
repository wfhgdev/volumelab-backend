import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import text

from app.models.workout_model import WorkoutModel


scenarios("../features/workout.feature")


@pytest.fixture
def workout_context(workout_api):
    client, db, user = workout_api
    return {"client": client, "db": db, "user": user, "workout_id": None, "response": None}


@given("a client exists")
def client_exists(workout_context):
    assert workout_context["user"].id > 0


@given("an administrator exists")
def administrator_exists(workout_context):
    workout_context["user"].role = "ADMIN"
    workout_context["db"].commit()


@given(parsers.parse('a workout named "{name}" exists'))
def existing_workout(workout_context, name):
    workout = WorkoutModel(name=name, type="DINAMICO", created_by=workout_context["user"].id)
    workout_context["db"].add(workout)
    workout_context["db"].commit()
    workout_context["workout_id"] = workout.id


@given(parsers.parse("the client owns {count:d} public workouts"))
def existing_public_workouts(workout_context, count):
    db = workout_context["db"]
    db.add_all([WorkoutModel(name=f"Public exercise {index}", type="DINAMICO", created_by=workout_context["user"].id, public=True) for index in range(count)])
    db.commit()


@given("the workout has a recorded set")
def recorded_set(workout_context):
    workout_context["db"].execute(text("INSERT INTO workout_set (exercise_id) VALUES (:id)"), {"id": workout_context["workout_id"]})
    workout_context["db"].commit()


@given("the workout is inactive")
def inactive_workout(workout_context):
    workout = workout_context["db"].get(WorkoutModel, workout_context["workout_id"])
    workout.state = False
    workout_context["db"].commit()


@when(parsers.parse('I create a {visibility} workout named "{name}"'))
def create_workout(workout_context, visibility, name):
    workout_context["response"] = workout_context["client"].post("/workouts/", json={
        "name": name, "type": "DINAMICO", "created_by": workout_context["user"].id, "public": visibility == "public",
    })


@when("I create an assisted workout without bodyweight")
def create_invalid_workout(workout_context):
    workout_context["response"] = workout_context["client"].post("/workouts/", json={
        "name": "Assisted pull-up", "type": "DINAMICO", "created_by": workout_context["user"].id, "allow_negative_ballast": True,
    })


@when("I list workouts")
def list_workouts(workout_context):
    workout_context["response"] = workout_context["client"].get("/workouts/")


@when("I retrieve the existing workout")
def retrieve_workout(workout_context):
    workout_context["response"] = workout_context["client"].get(f"/workouts/{workout_context['workout_id']}")


@when("I retrieve an unknown workout")
def retrieve_unknown_workout(workout_context):
    workout_context["response"] = workout_context["client"].get("/workouts/999")


@when(parsers.parse('I update its description to "{description}"'))
def update_description(workout_context, description):
    update_workout(workout_context, {"description": description})


def update_workout(context, payload):
    context["response"] = context["client"].put(f"/workouts/{context['workout_id']}", json=payload)


@when("I change its type to isometric")
def change_type(workout_context):
    update_workout(workout_context, {"type": "ISOMETRICO"})


@when("I publish the existing workout")
def publish_workout(workout_context):
    update_workout(workout_context, {"public": True})


@when("I reactivate the workout")
def reactivate_workout(workout_context):
    update_workout(workout_context, {"state": True})


@when("I deactivate the workout")
def deactivate_workout(workout_context):
    workout_context["response"] = workout_context["client"].delete(f"/workouts/{workout_context['workout_id']}")


@then(parsers.parse("the response status is {status_code:d}"))
def response_status(workout_context, status_code):
    assert workout_context["response"].status_code == status_code


@then(parsers.parse('the workout name is "{name}"'))
def workout_name(workout_context, name):
    assert workout_context["response"].json()["name"] == name


@then(parsers.parse('the description is "{description}"'))
def workout_description(workout_context, description):
    assert workout_context["response"].json()["description"] == description


@then(parsers.parse("the workout list contains {count:d} items"))
def workout_count(workout_context, count):
    assert len(workout_context["response"].json()) == count


@then("the workout remains stored and inactive")
def preserved_workout(workout_context):
    db = workout_context["db"]
    db.expire_all()
    workout = db.get(WorkoutModel, workout_context["workout_id"])
    assert workout is not None
    assert workout.state is False


@then("its recorded set remains stored")
def preserved_set(workout_context):
    assert workout_context["db"].execute(text("SELECT COUNT(*) FROM workout_set WHERE exercise_id = :id"), {"id": workout_context["workout_id"]}).scalar_one() == 1


@then("the workout is active")
def workout_is_active(workout_context):
    assert workout_context["response"].json()["state"] is True
