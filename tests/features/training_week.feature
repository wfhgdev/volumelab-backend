Feature: Gestión del ciclo de vida de Semanas de Entrenamiento (training_week)
  Como usuario de VolumeLab
  Quiero estructurar las semanas de entrenamiento dentro de mis mesociclos
  Para organizar y comparar mi progresión temporalmente

  Scenario: Crear una semana de entrenamiento exitosamente
    Given un mesociclo base existente
    When envío una solicitud para crear una semana con orden 1, fecha inicio "2026-01-01" y fecha fin "2026-01-07"
    Then la respuesta debe tener el código de estado 201
    And la semana creada debe pertenecer al mesociclo y tener orden 1

  Scenario: Fallar al crear una semana de entrenamiento con fecha de fin anterior a la de inicio
    Given un mesociclo base existente
    When envío una solicitud para crear una semana con orden 2, fecha inicio "2026-01-15" y fecha fin "2026-01-01"
    Then la respuesta de semana debe tener un código de error de validación 422 o 400

  Scenario: Fallar al crear una semana de entrenamiento con número de orden duplicado en el mismo mesociclo
    Given una semana de entrenamiento previamente creada con orden 1
    When envío una solicitud para crear otra semana con el mismo orden 1 en el mismo mesociclo
    Then la respuesta debe tener el código de estado 409

  Scenario: Fallar al crear una semana de entrenamiento para un mesociclo inexistente
    When envío una solicitud para crear una semana para el mesociclo inexistente 999999
    Then la respuesta debe tener el código de estado 404

  Scenario: Consultar una semana de entrenamiento existente por ID
    Given una semana de entrenamiento previamente creada con orden 1
    When consulto la semana de entrenamiento por su identificador
    Then la respuesta debe tener el código de estado 200
    And los datos deben coincidir con la semana creada

  Scenario: Fallar al consultar una semana de entrenamiento inexistente
    When consulto una semana de entrenamiento con el identificador inexistente 999999
    Then la respuesta debe tener el código de estado 404

  Scenario: Actualizar las fechas de una semana de entrenamiento existente
    Given una semana de entrenamiento previamente creada con orden 1
    When actualizo la fecha de fin de la semana a "2026-01-08"
    Then la respuesta debe tener el código de estado 200
    And la semana actualizada debe tener fecha fin "2026-01-08"

  Scenario: Eliminar una semana de entrenamiento existente
    Given una semana de entrenamiento previamente creada con orden 1
    When elimino la semana de entrenamiento por su identificador
    Then la respuesta debe tener el código de estado 204
    And si intento consultar nuevamente dicha semana obtengo un código 404
