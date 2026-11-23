Feature: Muscle group catalog management
  As a catalog administrator
  I want to manage muscle groups
  So that exercises can keep consistent muscle associations

  Scenario: Create a muscle group with an administrator creator
    Given an administrator exists
    When I create a muscle group named "Chest"
    Then the response status is 201
    And the muscle group name is "Chest"

  Scenario: Reject a client as the creator
    Given a client exists
    When I create a muscle group named "Chest"
    Then the response status is 403

  Scenario: Reject an unknown creator
    Given the creator does not exist
    When I create a muscle group named "Chest"
    Then the response status is 404

  Scenario: Reject a blank name
    Given an administrator exists
    When I create a muscle group named " "
    Then the response status is 422

  Scenario: Reject a duplicate name
    Given an administrator exists
    And a muscle group named "Chest" exists
    When I create a muscle group named "Chest"
    Then the response status is 409

  Scenario: List an empty catalog
    Given an administrator exists
    When I list muscle groups
    Then the response status is 200
    And the list contains 0 muscle groups

  Scenario: List an existing muscle group
    Given an administrator exists
    And a muscle group named "Chest" exists
    When I list muscle groups
    Then the response status is 200
    And the list contains 1 muscle group

  Scenario: Retrieve an existing muscle group
    Given an administrator exists
    And a muscle group named "Chest" exists
    When I retrieve the muscle group
    Then the response status is 200
    And the muscle group name is "Chest"

  Scenario: Retrieve an unknown muscle group
    Given an administrator exists
    When I retrieve an unknown muscle group
    Then the response status is 404

  Scenario: Update a description without replacing other fields
    Given an administrator exists
    And a muscle group named "Chest" exists
    When I update its description to "Pectoral muscles"
    Then the response status is 200
    And the muscle group name is "Chest"
    And the description is "Pectoral muscles"

  Scenario: Reject a client as the replacement creator
    Given an administrator exists
    And a muscle group named "Chest" exists
    When I assign a client as its creator
    Then the response status is 403

  Scenario: Delete an unassociated muscle group
    Given an administrator exists
    And a muscle group named "Chest" exists
    When I delete the muscle group
    Then the response status is 204
    And the muscle group no longer exists

  Scenario: Preserve a muscle group associated with exercises
    Given an administrator exists
    And a muscle group named "Chest" exists
    And the muscle group is associated with an exercise
    When I delete the muscle group
    Then the response status is 409
    And the muscle group and its association remain stored

  Scenario: Retrieve an anonymized muscle group
    Given an administrator exists
    And a muscle group named "Chest" exists
    And the muscle group has an anonymized creator
    When I retrieve the muscle group
    Then the response status is 200
    And its creator is null
