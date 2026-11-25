Feature: Gestión y consulta de registros de auditoría (audit)
  Como administrador de VolumeLab
  Quiero consultar los registros de auditoría de operaciones críticas
  Para garantizar la trazabilidad y cumplimiento RGPD del sistema

  Scenario: Un usuario no autenticado no puede consultar auditoría
    When intento listar los registros de auditoría sin autenticación
    Then el estado HTTP de auditoría es 401

  Scenario: Un usuario cliente no puede consultar auditoría
    Given existe un usuario cliente autenticado
    When intento listar los registros de auditoría como cliente
    Then el estado HTTP de auditoría es 403

  Scenario: Un administrador puede consultar el listado de auditoría
    Given existe un usuario administrador autenticado
    When listo los registros de auditoría como administrador
    Then el estado HTTP de auditoría es 200

  Scenario: Un administrador puede filtrar auditorías por acción
    Given existe un usuario administrador autenticado
    When listo los registros de auditoría filtrando por acción "INSERT"
    Then el estado HTTP de auditoría es 200

  Scenario: Rechazar un listado con rango de fechas invertido
    Given existe un usuario administrador autenticado
    When listo los registros de auditoría con fecha inicial posterior a la fecha final
    Then el estado HTTP de auditoría es 400

  Scenario: Consultar un registro de auditoría inexistente
    Given existe un usuario administrador autenticado
    When consulto el registro de auditoría con identificador 999999
    Then el estado HTTP de auditoría es 404

  Scenario: Los endpoints POST, PUT y DELETE no están permitidos en auditoría
    Given existe un usuario administrador autenticado
    When intento crear un registro de auditoría por POST
    Then el estado HTTP de auditoría es 405
    When intento modificar un registro de auditoría por PUT
    Then el estado HTTP de auditoría es 405
    When intento eliminar un registro de auditoría por DELETE
    Then el estado HTTP de auditoría es 405
