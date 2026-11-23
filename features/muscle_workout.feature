Feature: Weighted muscle associations
  As a catalog user
  I want to associate exercises with muscle groups
  So that muscle contributions remain consistent

  Scenario Outline: Derive weighing from the muscle role
    Given an exercise and a muscle group exist
    When I associate the group as "<role>"
    Then the response status is 201
    And the weighing is <weighing>

    Examples:
      | role       | weighing |
      | PRIMARIO   | 100      |
      | SECUNDARIO | 50       |
      | TERCIARIO  | 10       |

  Scenario: Accept an explicitly matching weighing
    Given an exercise and a muscle group exist
    When I associate the group as "SECUNDARIO" with weighing 50
    Then the response status is 201
    And the weighing is 50

  Scenario: Reject a weighing inconsistent with its role
    Given an exercise and a muscle group exist
    When I associate the group as "SECUNDARIO" with weighing 100
    Then the response status is 422

  Scenario: Reject a duplicate association
    Given an exercise and a muscle group exist
    And a primary association exists
    When I associate the group as "PRIMARIO"
    Then the response status is 409

  Scenario: Reject an unknown exercise
    Given an exercise and a muscle group exist
    And the requested exercise does not exist
    When I associate the group as "PRIMARIO"
    Then the response status is 404

  Scenario: Reject an unknown muscle group
    Given an exercise and a muscle group exist
    And the requested muscle group does not exist
    When I associate the group as "PRIMARIO"
    Then the response status is 404

  Scenario: List an empty association catalog
    Given an exercise and a muscle group exist
    When I list associations
    Then the response status is 200
    And the list contains 0 associations

  Scenario: Retrieve an association by its composite key
    Given an exercise and a muscle group exist
    And a primary association exists
    When I retrieve the association
    Then the response status is 200
    And the weighing is 100

  Scenario: Update role and weighing together
    Given an exercise and a muscle group exist
    And a primary association exists
    When I change the muscle role to secondary
    Then the response status is 200
    And the weighing is 50

  Scenario: Remove only the association
    Given an exercise and a muscle group exist
    And a primary association exists
    When I remove the association
    Then the response status is 204
    And the association no longer exists
    And both parent records remain stored

  Scenario: Reject a new association after recording sets
    Given an exercise and a muscle group exist
    And the exercise has a recorded set
    When I associate the group as "PRIMARIO"
    Then the response status is 409
    And the association no longer exists

  Scenario: Preserve the muscle role after recording sets
    Given an exercise and a muscle group exist
    And a primary association exists
    And the exercise has a recorded set
    When I change the muscle role to secondary
    Then the response status is 409
    And the primary association remains unchanged

  Scenario: Preserve the association after recording sets
    Given an exercise and a muscle group exist
    And a primary association exists
    And the exercise has a recorded set
    When I remove the association
    Then the response status is 409
    And the primary association remains unchanged

  Scenario: Filter associations by muscle group
    Given an exercise and a muscle group exist
    And a primary association exists
    When I filter associations by the muscle group
    Then the response status is 200
    And the list contains 1 association
