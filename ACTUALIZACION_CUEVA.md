# Actualización basada en flujo.docx

## Fuente y decisiones

- Documento: `C:\Users\marce\Desktop\construc software\flujo.docx`.
- Base local: `342cc50` (primera implementación 2D).
- Rama local: `feature/cave-cinematic-combat`.
- Decisiones del usuario: combate en **tiempo real**; arma recogida con E y equipada desde el **inventario**.
- No se creó ningún commit ni se publicó la actualización.

## Implementado

1. Introducción sobre fondo negro con tres textos blancos y fundidos:
   - «Ellos te lo arrebataron…»
   - «Encuéntralos y destrúyelos…»
   - «Venga a tu familia…»
   - Enter omite la secuencia; Esc pausa; cargar una partida no la repite.
2. Restos de Guerrero o hechicero en la primera sala. Entregan espada o bastón de fuego, una única vez, sin equipar automáticamente.
3. Espada: alcance de 144 píxeles lógicos (dos alturas normales del héroe), sin consumo de maná.
4. Mago: 100 de maná inicial; cada fuego consume 15 al lanzarse. Proyectiles con trayectoria y colisión contra enemigos/rocas. Un fallo también consume maná. No hay recuperación pasiva.
5. Al matar al primer Goblin se restaura el maná a 100 y aparece la armadura en la posición del cadáver. No se puede volver a otorgar el botín al cargar o atacar al enemigo muerto. En este prototipo, el guardián también recarga el maná al morir.
6. Enemigos que persiguen, rodean rocas y atacan cerca del héroe con intervalos; sin contraataque automático gráfico.
7. Cueva de roca con iluminación cálida animada de antorchas y luz de los proyectiles.
8. Guardado v2: maná, arma, botín, posición enemiga e intervalos. Migración v1 sin alterar el archivo al cargar.

### Parámetros de combate

| Parámetro | Valor |
|---|---|
| Velocidad del jugador | 220 px/s |
| Velocidad enemiga | 105 px/s |
| Intervalo de espada | 0,55 s |
| Intervalo de fuego | 0,75 s |
| Alcance/velocidad de fuego | 420 px / 420 px/s |
| Distancia de golpe enemigo | 48 px |
| Intervalo de golpe enemigo | 1,15 s |

Las coordenadas son de la escena lógica, independientes del tamaño de ventana. Las pruebas verifican contacto a 30, 60 y 120 FPS. Pausa, inventario y personalización detienen la simulación.

## Ejecutar

Abrir en VS Code la carpeta:

```text
C:\Users\marce\Desktop\redes\Grupo-1-PixelQuest
```

```powershell
.\.venv\Scripts\python.exe -B -m src.main
```

También funciona `JUGAR.bat`. Elegir **Nueva aventura** para observar la historia y los restos desde el inicio.

## Evidencia automatizada

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

```text
Ran 91 tests
OK
```

Incluye partidas gráficas hasta victoria con ambas clases, derrota sin ataque del jugador, cinematográfica natural/omitida, pausa de proyectiles/persecución, costo e insuficiencia de maná, botín único, navegación, alcance, colisión del fuego y migración v1. La consola también completa una partida como Mago con bastón y maná.

Se verificó el arranque con el controlador real de ventanas de Windows. Se revisaron capturas de introducción, restos y fuego con 85 de maná. Una medición de 120 renderizados en SDL dummy dio 5,37 ms promedio por render; no representa una medición de FPS de juego en todos los equipos.

## Pruebas humanas pendientes

- [ ] Ver los tres textos con sus fundidos y comprobar la transición al juego.
- [ ] Omitir la introducción con Enter y pausarla con Esc.
- [ ] Crear ambas clases y recoger sus armas de los restos; equiparlas con I.
- [ ] Comprobar alcance de espada y desplazamiento mientras se ataca.
- [ ] Lanzar fuego y verificar 100 → 85; comprobar el bloqueo con menos de 15.
- [ ] Observar la persecución alrededor de rocas y esquivar ataques.
- [ ] Matar al Goblin y comprobar recarga a 100 y aparición de armadura.
- [ ] Recoger/equipar armadura y completar el combate final.
- [ ] Guardar/cargar con maná gastado, enemigo desplazado y botín recogido.
- [ ] Revisar iluminación, legibilidad y fluidez en la ventana de VS Code.

## Comportamiento y pendientes conocidos

- Guardar, cargar, avanzar o salir al menú requiere que no haya fuego en vuelo. Si está pausado, hay que reanudar para que el proyectil termine.
- Si se agota el maná sin matar, se puede cargar un guardado anterior o comenzar una nueva aventura; no hay pociones ni regeneración por tiempo.
- La consola mantiene combate por turnos y no simula persecución ni la secuencia gráfica. Guardar desde CLI conserva maná/botín pero restablece posiciones visuales al volver al modo 2D.
- Los textos se conservaron como aparecen en el documento, normalizando los puntos suspensivos.
- La validación humana y la revisión por responsables de cada capa siguen pendientes.

## Prompts y aclaraciones del usuario

```text
vamos a implementar una actualización pero sin subirla al githup

para esto te guíaras con el documento llamado flujo para implementar nuevas cosas en el juego C:\Users\marce\Desktop\construc software
```

Respuestas a las decisiones de diseño:

```text
Tiempo real (Recomendado)
Equipar desde inventario
```

Autorización:

```text
implementa
```
