Feature: Audit log access
  Administrators can inspect audit events while the API prevents direct changes.

  Scenario: Reject an unauthenticated audit request
    When I list audit events without authentication
    Then the audit response status is 401

  Scenario: Reject audit access for clients
    Given an authenticated client account
    When I list audit events
    Then the audit response status is 403

  Scenario: Allow administrators to list audit events
    Given an authenticated administrator account
    When I list audit events
    Then the audit response status is 200

  Scenario: Filter audit events by action
    Given an authenticated administrator account
    When I list audit events with action "INSERT"
    Then the audit response status is 200

  Scenario: Reject an inverted audit date range
    Given an authenticated administrator account
    When I list audit events with an inverted date range
    Then the audit response status is 400

  Scenario: Reject a missing audit event
    Given an authenticated administrator account
    When I retrieve audit event 999999
    Then the audit response status is 404

  Scenario: Reject direct changes to audit events
    Given an authenticated administrator account
    When I create an audit event directly
    Then the audit response status is 405
    When I update an audit event directly
    Then the audit response status is 405
    When I delete an audit event directly
    Then the audit response status is 405
