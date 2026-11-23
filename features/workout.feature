Feature: Workout catalog management
  As a catalog user
  I want to manage exercises
  So that I can maintain a consistent training catalog

  Scenario: Create a dynamic workout
    Given a client exists
    When I create a private workout named "Squat"
    Then the response status is 201
    And the workout name is "Squat"

  Scenario: Reject a duplicate workout name
    Given a client exists
    And a workout named "Squat" exists
    When I create a private workout named "Squat"
    Then the response status is 409

  Scenario: Reject negative ballast without bodyweight
    Given a client exists
    When I create an assisted workout without bodyweight
    Then the response status is 422

  Scenario: List an empty catalog
    Given a client exists
    When I list workouts
    Then the response status is 200
    And the workout list contains 0 items

  Scenario: Retrieve an existing workout
    Given a client exists
    And a workout named "Squat" exists
    When I retrieve the existing workout
    Then the response status is 200
    And the workout name is "Squat"

  Scenario: Retrieve an unknown workout
    Given a client exists
    When I retrieve an unknown workout
    Then the response status is 404

  Scenario: Update a workout description
    Given a client exists
    And a workout named "Squat" exists
    When I update its description to "Controlled movement"
    Then the response status is 200
    And the description is "Controlled movement"

  Scenario: Deactivate a workout while preserving its recorded sets
    Given a client exists
    And a workout named "Squat" exists
    And the workout has a recorded set
    When I deactivate the workout
    Then the response status is 204
    And the workout remains stored and inactive
    And its recorded set remains stored

  Scenario: Prevent a type change for a workout with recorded sets
    Given a client exists
    And a workout named "Squat" exists
    And the workout has a recorded set
    When I change its type to isometric
    Then the response status is 409

  Scenario: Reject the twenty-first public workout for a client
    Given a client exists
    And the client owns 20 public workouts
    When I create a public workout named "Extra exercise"
    Then the response status is 409

  Scenario: Allow private workouts after reaching the public limit
    Given a client exists
    And the client owns 20 public workouts
    When I create a private workout named "Private exercise"
    Then the response status is 201

  Scenario: Allow administrators to exceed the public limit
    Given an administrator exists
    And the client owns 20 public workouts
    When I create a public workout named "Extra exercise"
    Then the response status is 201

  Scenario: Reject publishing a private workout after reaching the limit
    Given a client exists
    And the client owns 20 public workouts
    And a workout named "Private exercise" exists
    When I publish the existing workout
    Then the response status is 409

  Scenario: Reactivate a deactivated workout
    Given a client exists
    And a workout named "Squat" exists
    And the workout is inactive
    When I reactivate the workout
    Then the response status is 200
    And the workout is active
