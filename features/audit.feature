Feature: Gestión CRUD de registros de auditoría (audit)
  Como administrador de VolumeLab
  Quiero gestionar los registros de auditoría de operaciones críticas
  Para garantizar la trazabilidad y cumplimiento RGPD del sistema

  Scenario: Crear un registro de auditoría válido para un usuario existente
    Given existe un usuario registrado para auditoría
    When creo un registro de auditoría de acción "INSERT" sobre la entidad "workout_session" con record_id "42" y endpoint "/workout-sessions/42"
    Then el registro de auditoría se crea correctamente con acción "INSERT" y entidad "workout_session"
    And el estado HTTP es 201

  Scenario: Crear un registro de auditoría sin usuario asociado (user_id nulo)
    When creo un registro de auditoría anónimo de acción "EXPORT" sobre la entidad "workout_session" con record_id "batch-1"
    Then el registro de auditoría se crea correctamente sin usuario asociado
    And el estado HTTP es 201

  Scenario: Rechazar la creación de un registro de auditoría para un usuario inexistente
    When intento crear un registro de auditoría para el usuario inexistente 999
    Then la operación indica que no fue encontrado
    And el estado HTTP es 404

  Scenario: Rechazar una acción de auditoría no permitida
    When intento crear un registro de auditoría con acción inválida "SELECT"
    Then la operación falla por validación
    And el estado HTTP es 422

  Scenario: Listar registros de auditoría filtrados por acción
    Given existe un usuario registrado para auditoría
    And ya existe un registro de auditoría de acción "INSERT" para la entidad "workout_session"
    And ya existe un registro de auditoría de acción "EXPORT" para la entidad "workout_set"
    When listo los registros de auditoría filtrando por acción "EXPORT"
    Then obtengo una lista con 1 registro de auditoría de acción "EXPORT"
    And el estado HTTP es 200

  Scenario: Rechazar un listado con rango de fechas invertido
    When listo los registros de auditoría con fecha inicial posterior a la fecha final
    Then la operación falla por rango de fechas inválido
    And el estado HTTP es 400

  Scenario: Consultar un registro de auditoría existente por ID
    Given existe un usuario registrado para auditoría
    And ya existe un registro de auditoría de acción "INSERT" para la entidad "workout_session"
    When consulto ese registro de auditoría existente
    Then obtengo el registro de auditoría consultado
    And el estado HTTP es 200

  Scenario: Consultar un registro de auditoría inexistente
    When consulto el registro de auditoría con identificador 999
    Then la operación indica que no fue encontrado
    And el estado HTTP es 404

  Scenario: Actualizar la acción y el endpoint de un registro de auditoría existente
    Given existe un usuario registrado para auditoría
    And ya existe un registro de auditoría de acción "INSERT" para la entidad "workout_session"
    When actualizo la acción del registro existente a "UPDATE" y el endpoint a "/workout-sessions/42/close"
    Then el registro queda actualizado con acción "UPDATE" y endpoint "/workout-sessions/42/close"
    And el estado HTTP es 200

  Scenario: Eliminar un registro de auditoría existente
    Given existe un usuario registrado para auditoría
    And ya existe un registro de auditoría de acción "DELETE" para la entidad "workout"
    When elimino ese registro de auditoría existente
    Then el estado HTTP es 204
    And al consultar ese registro de auditoría obtengo un estado HTTP 404

  Scenario: Eliminar un registro de auditoría inexistente
    When elimino el registro de auditoría con identificador 999
    Then la operación indica que no fue encontrado
    And el estado HTTP es 404
