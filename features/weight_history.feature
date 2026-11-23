Feature: Gestión CRUD del histórico de peso corporal
  Como usuario o administrador
  Quiero gestionar registros de weight_history
  Para mantener la evolución histórica del peso corporal

  Scenario: Crear un registro de peso válido
    Given existe el usuario con identificador 1
    When registro un peso de 75.50 kg para el usuario 1
    Then el registro de peso se crea correctamente con 75.50 kg para el usuario 1
    And el estado HTTP es 201

  Scenario: Rechazar la creación de un registro para un usuario inexistente
    Given no existe el usuario con identificador 999
    When registro un peso de 75.50 kg para el usuario 999
    Then la operación indica que no fue encontrado
    And el estado HTTP es 404

  Scenario: Rechazar un peso inválido al crear un registro
    Given existe el usuario con identificador 1
    When registro un peso de 0 kg para el usuario 1
    Then la operación falla por validación
    And el estado HTTP es 422

  Scenario: Listar registros de peso existentes
    Given existe el usuario con identificador 1
    And ya existe un registro de peso de 78.25 kg para el usuario 1
    When listo los registros de peso
    Then obtengo una lista con 1 registro de peso para el usuario 1
    And el estado HTTP es 200

  Scenario: Listar registros de peso filtrados por usuario
    Given existe el usuario con identificador 1
    And existe el usuario con identificador 2
    And ya existe un registro de peso de 78.25 kg para el usuario 1
    And ya existe un registro de peso de 64.00 kg para el usuario 2
    When listo los registros de peso del usuario 1
    Then obtengo una lista con 1 registro de peso para el usuario 1
    And el estado HTTP es 200

  Scenario: Consultar un registro de peso existente
    Given existe el usuario con identificador 1
    And ya existe un registro de peso de 80.10 kg para el usuario 1
    When consulto ese registro de peso existente
    Then obtengo el registro de peso con 80.10 kg para el usuario 1
    And el estado HTTP es 200

  Scenario: Consultar un registro de peso inexistente
    Given no existe el registro de peso con identificador 999
    When consulto el registro de peso con identificador 999
    Then la operación indica que no fue encontrado
    And el estado HTTP es 404

  Scenario: Actualizar un registro de peso existente
    Given existe el usuario con identificador 1
    And ya existe un registro de peso de 80.10 kg para el usuario 1
    When actualizo el peso del registro existente a 79.40 kg
    Then el registro queda actualizado con peso 79.40 kg
    And el estado HTTP es 200

  Scenario: Eliminar un registro de peso existente
    Given existe el usuario con identificador 1
    And ya existe un registro de peso de 80.10 kg para el usuario 1
    When elimino ese registro de peso existente
    Then el estado HTTP es 204

  Scenario: Eliminar un registro de peso inexistente
    Given no existe el registro de peso con identificador 999
    When elimino el registro de peso con identificador 999
    Then la operación indica que no fue encontrado
    And el estado HTTP es 404
