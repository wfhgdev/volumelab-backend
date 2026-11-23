Feature: Gestión CRUD de usuarios
  Como administrador
  Quiero gestionar cuentas de app_user
  Para mantener los datos y permisos de los usuarios

  Scenario: Crear un usuario válido
    Given no existe un usuario con el email "ana@example.com"
    When creo el usuario "Ana" con el email "ana@example.com"
    Then el usuario se crea correctamente
    And el estado HTTP es 201

  Scenario: Rechazar un email duplicado sin distinguir mayúsculas
    Given ya existe un usuario con el email "ana@example.com"
    When creo el usuario "Ana" con el email "ANA@example.com"
    Then la operación falla por conflicto
    And el estado HTTP es 409

  Scenario: Rechazar datos inválidos al crear un usuario
    Given no existe un usuario con el email "email-invalido"
    When creo el usuario "Ana" con el email "email-invalido"
    Then la operación falla por validación
    And el estado HTTP es 422

  Scenario: Listar usuarios existentes
    Given ya existe un usuario con el email "ana@example.com"
    When listo los usuarios
    Then la lista contiene el usuario con ese email
    And el estado HTTP es 200

  Scenario: Consultar un usuario existente
    Given ya existe un usuario con el email "ana@example.com"
    When consulto ese usuario existente
    Then obtengo los datos del usuario "ana@example.com"
    And el estado HTTP es 200

  Scenario: Consultar un usuario inexistente
    Given no existe el usuario con identificador 999
    When consulto el usuario con identificador 999
    Then la operación indica que no fue encontrado
    And el estado HTTP es 404

  Scenario: Actualizar un usuario existente
    Given ya existe un usuario con el email "ana@example.com"
    When actualizo el nombre del usuario existente a "Lucia" y su estado a "BLOQUEADO"
    Then el usuario queda actualizado con nombre "Lucia" y estado "BLOQUEADO"
    And el estado HTTP es 200

  Scenario: Eliminar un usuario existente
    Given ya existe un usuario con el email "ana@example.com"
    When elimino ese usuario existente
    Then el estado HTTP es 204

  Scenario: Eliminar un usuario inexistente
    Given no existe el usuario con identificador 999
    When elimino el usuario con identificador 999
    Then la operación indica que no fue encontrado
    And el estado HTTP es 404
