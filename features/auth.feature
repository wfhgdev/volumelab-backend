Feature: Account registration and authentication
  Users register as active clients and access their profile with a valid bearer token.

  Background:
    Given the authentication API is available

  Scenario: Register an active client without exposing credentials
    When I register a new account
    Then the response status is 201
    And the response contains an active client without credentials
    And the stored password is hashed
    And registration creates one audit event for the new account

  Scenario Outline: Reject privileged registration fields
    When I register with the forbidden field "<field>" set to "<value>"
    Then the response status is 422
    And no account or audit event is created

    Examples:
      | field         | value       |
      | role          | ADMIN       |
      | status        | BLOQUEADO   |
      | password_hash | stored-hash |

  Scenario: Reject a duplicate email regardless of letter case
    Given an account with role "CLIENTE" and status "ACTIVO"
    When I register with the existing email in uppercase
    Then the response status is 409
    And the existing account is preserved without an audit event

  Scenario Outline: Sign in and retrieve the authenticated profile
    Given an account with role "<role>" and status "ACTIVO"
    When I sign in with the account credentials
    Then the response status is 200
    And the response contains a bearer token with the configured lifetime
    And I can retrieve my profile using the issued token

    Examples:
      | role    |
      | ADMIN   |
      | CLIENTE |

  Scenario: Reject an incorrect password
    Given an account with role "CLIENTE" and status "ACTIVO"
    When I sign in with an incorrect password
    Then the response status is 401
    And the response requests bearer authentication
    And the response does not contain a token

  Scenario: Reject an unknown email
    When I sign in with an unknown email
    Then the response status is 401
    And the response requests bearer authentication
    And the response does not contain a token

  Scenario: Reject a blocked account at sign in
    Given an account with role "CLIENTE" and status "BLOQUEADO"
    When I sign in with the account credentials
    Then the response status is 403
    And the response does not contain a token

  Scenario: Reject an unauthenticated profile request
    When I request my profile without a token
    Then the response status is 401
    And the response requests bearer authentication

  Scenario Outline: Reject an invalid profile token
    Given an account with role "CLIENTE" and status "ACTIVO"
    When I request my profile with a "<kind>" token
    Then the response status is 401
    And the response requests bearer authentication

    Examples:
      | kind                |
      | expired             |
      | malformed           |
      | wrong_signature     |
      | non_numeric_subject |

  Scenario: Reject a previously issued token after the account is blocked
    Given an account with role "CLIENTE" and status "ACTIVO"
    When the account is blocked before its token is used
    Then the response status is 401
    And the response requests bearer authentication
