Feature: Gestión del ciclo de vida de Mesociclos (CRUD)
  Como usuario de VolumeLab
  Quiero gestionar mis bloques de mesociclos de entrenamiento
  Para planificar y estructurar mi progresión física

  Scenario: Crear un mesociclo exitosamente
    Given un usuario existente con rol CLIENTE
    When envío una solicitud para crear un mesociclo con nombre "Mesociclo Fuerza", fecha inicio "2026-03-01", fecha fin "2026-03-31" y estado "PLANIFICADO"
    Then la respuesta debe tener el código de estado 201
    And el mesociclo creado debe contener el nombre "Mesociclo Fuerza" y estado "PLANIFICADO"

  Scenario: Fallar al crear un mesociclo con fecha de fin anterior a la de inicio
    Given un usuario existente con rol CLIENTE
    When envío una solicitud para crear un mesociclo con nombre "Mesociclo Invalido", fecha inicio "2026-04-30", fecha fin "2026-04-01" y estado "PLANIFICADO"
    Then la respuesta debe tener un código de error de validación 422 o 400

  Scenario: Fallar al crear un mesociclo para un usuario que no existe
    When envío una solicitud para crear un mesociclo para el usuario inexistente 999999
    Then la respuesta debe tener el código de estado 404

  Scenario: Consultar un mesociclo existente por su identificador
    Given un mesociclo previamente creado con nombre "Mesociclo Hipertrofia"
    When consulto el mesociclo por su identificador
    Then la respuesta debe tener el código de estado 200
    And los datos deben coincidir con el mesociclo creado

  Scenario: Fallar al consultar un mesociclo inexistente
    When consulto un mesociclo con el identificador inexistente 999999
    Then la respuesta debe tener el código de estado 404

  Scenario: Actualizar un mesociclo existente
    Given un mesociclo previamente creado con nombre "Mesociclo Resistencia"
    When actualizo el nombre a "Mesociclo Resistencia Avanzada" y el estado a "ACTIVO"
    Then la respuesta debe tener el código de estado 200
    And el mesociclo actualizado debe tener el nombre "Mesociclo Resistencia Avanzada" y estado "ACTIVO"

  Scenario: Eliminar un mesociclo existente
    Given un mesociclo previamente creado con nombre "Mesociclo a Borrar"
    When elimino el mesociclo por su identificador
    Then la respuesta debe tener el código de estado 204
    And si intento consultar nuevamente dicho mesociclo obtengo un código 404
