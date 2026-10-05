# Arquitectura de Pixel Quest

Pixel Quest utiliza arquitectura en capas. Las dependencias apuntan hacia el dominio; ninguna clase del dominio conoce la consola, los archivos JSON o los servicios.

## Capas

```mermaid
flowchart LR
    MAIN["src/main.py"] --> UI["Interfaz · GraphicalGame / MenuCLI"]
    MAIN --> APP["Aplicación · GameService"]
    MAIN --> DATA["Persistencia · DataManager"]
    UI --> APP
    APP --> DOMAIN["Dominio · Modelos y reglas"]
    APP --> DATA
    MAIN --> VIEWDATA["VisualDataManager"]
    APP --> VIEWDATA
    VIEWDATA --> DATA
    VIEWDATA --> WORLD["ExplorationWorld"]
    UI --> WORLD
    UI --> ART["pixel_art · Pygame"]
    DATA --> JSON[("data/savegame.json")]

    classDef entry fill:#17365d,color:#fff,stroke:#17365d
    classDef layer fill:#eaf2f8,color:#17365d,stroke:#245b8a
    classDef storage fill:#eaf6ef,color:#1e5138,stroke:#26734d
    class MAIN entry
    class UI,APP,DOMAIN layer
    class DATA,JSON storage
```

Reglas de dependencia:

- `src/domain` no importa servicios, UI, JSON, `input` ni `print`.
- `GameService` utiliza modelos y recibe persistencia por inyección.
- `MenuCLI` utiliza la API pública de `GameService` y captura excepciones controladas; no accede a modelos ni a `DataManager`.
- `GraphicalGame` usa esa misma API para combatir, recoger, equipar y personalizar. Maneja las animaciones y eventos sin calcular daño ni alterar directamente al héroe.
- `ExplorationWorld` controla coordenadas, alcance visual y colisiones. No conoce los modelos de combate ni necesita Pygame.
- `VisualDataManager` implementa el contrato de persistencia e incorpora `view` al JSON; el estado visual se aplica solo después de una restauración válida del dominio.
- `pixel_art.py` dibuja recursos originales con Pygame. Dominio y Servicios no dependen de ese paquete.
- `main.py` ensambla las capas sin contener reglas del juego.

## Diagrama de clases

```mermaid
classDiagram
    class Item {
        -name: str
        -item_type: str
        -attack_bonus: int
        -defense_bonus: int
        +to_dict() dict
        +from_dict(data) Item
    }

    class Character {
        -name: str
        -max_health: int
        -health: int
        -base_attack: int
        -base_defense: int
        +receive_damage(raw_attack) int
        +is_alive bool
    }

    class Hero {
        -hero_class: str
        -color: str
        -inventory: list
        -weapon: Item
        -armor: Item
        +add_item(item)
        +equip_item(index)
        +change_color(color)
        +to_dict() dict
        +from_dict(data) Hero
    }

    class Enemy {
        -is_boss: bool
        +to_dict() dict
        +from_dict(data) Enemy
    }

    class Room {
        -number: int
        -description: str
        +enemy: Enemy
        +item: Item
        -is_final: bool
        +to_dict() dict
        +from_dict(data) Room
    }

    class GameService {
        -status: str
        -current_room_index: int
        +start_new_game(name, hero_class, color)
        +change_hero_color(color)
        +get_hero_classes() dict
        +get_snapshot() dict
        +collect_item()
        +equip_item(index)
        +attack()
        +advance()
        +save_game()
        +load_game()
    }

    class DataManager {
        -path: Path
        +exists() bool
        +save(state)
        +load() dict
    }

    class MenuCLI {
        +run()
    }

    class GraphicalGame {
        +run()
        +process_event(event)
        +update(dt)
        +render()
    }

    class ExplorationWorld {
        -position: tuple
        -facing: str
        +move(dx, dy, dt)
        +can_attack(snapshot) bool
        +to_dict() dict
        +restore(data, room_index) bool
    }

    class VisualDataManager {
        +save(state)
        +load() dict
        +exists() bool
        +restore_view(snapshot) bool
    }

    Character <|-- Hero
    Character <|-- Enemy
    Hero "1" o-- "*" Item : inventario
    Hero "1" --> "0..1" Item : arma
    Hero "1" --> "0..1" Item : armadura
    Room "1" --> "0..1" Enemy
    Room "1" --> "0..1" Item
    GameService "1" --> "1" Hero
    GameService "1" --> "*" Room
    GameService --> DataManager
    MenuCLI --> GameService
    GraphicalGame --> GameService
    GraphicalGame --> ExplorationWorld
    GraphicalGame --> VisualDataManager
    GameService --> VisualDataManager : contrato inyectado
    VisualDataManager --> DataManager
    VisualDataManager --> ExplorationWorld
```

## Secuencia de una partida

```mermaid
sequenceDiagram
    actor J as Jugador
    participant UI as MenuCLI
    participant S as GameService
    participant D as Dominio
    participant DM as DataManager

    J->>UI: Nueva partida
    UI->>S: start_new_game(nombre, clase)
    S->>D: Crear Hero, Item, Enemy y Room
    D-->>S: Modelos válidos
    S-->>UI: Mensajes iniciales

    loop Mientras status == playing
        J->>UI: Elegir acción
        alt Guardar partida
            UI->>S: save_game()
            S->>DM: save(export_state())
            DM-->>S: Guardado completado
        else Acción de juego
            UI->>S: collect/equip/attack/advance
            S->>D: Aplicar reglas
            D-->>S: Estado actualizado
        end
        S-->>UI: Mensajes
    end
```

## Contrato de persistencia

| Campo | Tipo | Regla |
|---|---|---|
| `version` | entero | Debe ser exactamente `1`. |
| `status` | texto | `playing`, `victory` o `defeat`. |
| `current_room` | entero | Índice existente dentro de `rooms`. |
| `hero` | objeto | Incluye nombre, clase, vida, estadísticas, inventario y equipo. |
| `rooms` | lista no vacía | Cada habitación incluye número, descripción, enemigo, objeto y `is_final`. |
| `hero.color` | texto opcional | RGB hexadecimal `#RRGGBB`; si falta, usa el color de la clase. |
| `view` | objeto opcional | Versión visual, índice de sala, posición y orientación. |

La lista debe contener un único jefe final vivo mientras la partida esté en curso. El jefe debe estar en la última habitación. Una victoria requiere al héroe vivo, ubicado en esa habitación, con el jefe derrotado.

`DataManager` valida el contenedor JSON. `GameService` valida el significado del estado y reconstruye los modelos.

La ampliación conserva `version: 1`: color y vista son adiciones compatibles. `VisualDataManager` agrega `view` en una copia del estado sin mutar el original. Una posición fuera de la sala, dentro de una columna o enemigo, no finita o perteneciente a otra habitación se descarta y el héroe vuelve a la entrada. Un color inválido sí invalida el dominio guardado y conserva intacta la partida actual.

## Flujo gráfico de un turno

```mermaid
sequenceDiagram
    actor J as Jugador
    participant G as GraphicalGame
    participant W as ExplorationWorld
    participant S as GameService
    J->>G: WASD / flechas
    G->>W: move(dirección, dt)
    W-->>G: Posición limitada por paredes y columnas
    J->>G: Espacio
    G->>W: can_attack(snapshot)
    W-->>G: Enemigo cercano
    G->>S: attack()
    S-->>G: Ataque, contraataque y estado del encuentro
    G->>G: Animar turno; bloquear ataques repetidos
    G-->>J: Vida, daño flotante y victoria/derrota
```

## Aislamiento por célula

- **Dominio:** `Hero.color`, `change_color()` y `validate_color()`.
- **Servicios:** catálogo de clases para la vista y caso de uso `change_hero_color()`.
- **Interfaz/Integración:** renderizado, exploración, persistencia visual y arranque.
- **Integrador:** dependencias, documentación y pruebas cruzadas.

La configuración local `.vscode/` y el entorno `.venv/` están excluidos de Git. Los cambios se encuentran en una rama local de funcionalidad; los prompts y evidencias se preparan para la revisión del equipo.
