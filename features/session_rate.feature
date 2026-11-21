Feature: Gestión CRUD de valoraciones de sesiones de entrenamiento (session_rate)
  Como usuario autenticado
  Quiero valorar sesiones de entrenamiento públicas
  Para compartir mi opinión y consultar la puntuación comunitaria de las sesiones

  Scenario: Crear una valoración válida para una sesión pública
    Given existe una sesión pública con id 100
    And no existe una valoración del usuario 1 para la sesión 100
    When creo la valoración con puntuación 5 para la sesión 100 y usuario 1
    Then la valoración se crea correctamente con puntuación 5
    And el estado HTTP es 201

  Scenario: Rechazar una valoración para una sesión privada
    Given existe una sesión privada con id 101
    When intento valorar la sesión 101 con puntuación 4 para el usuario 1
    Then la operación falla porque la sesión no es pública
    And el estado HTTP es 400

  Scenario: Rechazar una valoración duplicada del mismo usuario sobre la misma sesión
    Given ya existe una valoración del usuario 1 para la sesión 100
    When creo la valoración con puntuación 4 para la sesión 100 y usuario 1
    Then la operación falla por conflicto de voto duplicado
    And el estado HTTP es 409

  Scenario: Rechazar una puntuación fuera del rango permitido
    Given existe una sesión pública con id 100
    When creo la valoración con puntuación 6 para la sesión 100 y usuario 1
    Then la operación falla por validación de datos
    And el estado HTTP es 422

  Scenario: Listar valoraciones existentes
    Given ya existe una valoración del usuario 1 para la sesión 100
    When listo las valoraciones de sesiones
    Then obtengo una lista con al menos 1 valoración
    And el estado HTTP es 200

  Scenario: Consultar una valoración por ID existente
    Given existe una valoración registrada con id 10
    When consulto la valoración con id 10
    Then obtengo los datos de la valoración con id 10
    And el estado HTTP es 200

  Scenario: Consultar una valoración por ID inexistente
    Given no existe ninguna valoración con id 999
    When consulto la valoración con id 999
    Then la operación indica que la valoración no fue encontrada
    And el estado HTTP es 404

  Scenario: Consultar la puntuación media de una sesión
    Given existe una sesión pública con id 100
    And la sesión 100 tiene valoraciones registradas
    When consulto la puntuación acumulada de la sesión 100
    Then obtengo la nota media y el total de valoraciones
    And el estado HTTP es 200

  Scenario: Actualizar una valoración existente
    Given existe una valoración registrada con id 10
    When actualizo la puntuación de la valoración 10 a 4
    Then la valoración 10 queda actualizada con puntuación 4
    And el estado HTTP es 200

  Scenario: Crear o actualizar valoración mediante upsert
    Given existe una sesión pública con id 100
    When realizo un upsert con puntuación 3 para la sesión 100 y usuario 1
    Then la valoración queda registrada o actualizada con puntuación 3
    And el estado HTTP es 200

  Scenario: Eliminar una valoración existente
    Given existe una valoración registrada con id 10
    When elimino la valoración con id 10
    Then el estado HTTP es 204

  Scenario: Eliminar una valoración inexistente
    Given no existe ninguna valoración con id 999
    When elimino la valoración con id 999
    Then la operación indica que la valoración no fue encontrada
    And el estado HTTP es 404
