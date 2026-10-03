# Arquitectura de Pixel Quest

Pixel Quest utiliza arquitectura en capas. Las dependencias apuntan hacia el dominio; ninguna clase del dominio conoce la consola, los archivos JSON o los servicios.

## Capas

```mermaid
flowchart LR
    MAIN["src/main.py"] --> UI["Interfaz · MenuCLI"]
    MAIN --> APP["Aplicación · GameService"]
    MAIN --> DATA["Persistencia · DataManager"]
    UI --> APP
    APP --> DOMAIN["Dominio · Modelos y reglas"]
    APP --> DATA
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
        -inventory: list
        -weapon: Item
        -armor: Item
        +add_item(item)
        +equip_item(index)
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
        +start_new_game(name, hero_class)
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

La lista debe contener un único jefe final vivo mientras la partida esté en curso. El jefe debe estar en la última habitación. Una victoria requiere al héroe vivo, ubicado en esa habitación, con el jefe derrotado.

`DataManager` valida el contenedor JSON. `GameService` valida el significado del estado y reconstruye los modelos.
