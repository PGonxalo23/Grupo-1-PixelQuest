"""Adaptador de presentación que agrega la posición al guardado del servicio."""

from copy import deepcopy


class VisualDataManager:
    """Implementa el mismo contrato de persistencia utilizado por GameService.

    El dominio conserva su JSON v1. Los clientes de consola pueden ignorar `view`.
    La vista se restaura únicamente después de que el servicio acepte la partida.
    """

    def __init__(self, data_manager, world):
        self._data_manager = data_manager
        self._world = world
        self._loaded_view = None

    def exists(self):
        return self._data_manager.exists()

    def save(self, state):
        data = deepcopy(state)
        data["view"] = self._world.to_dict()
        self._data_manager.save(data)

    def load(self):
        data = self._data_manager.load()
        self._loaded_view = deepcopy(data.get("view"))
        return data

    def restore_view(self, snapshot):
        enemy = snapshot["room"].get("enemy")
        return self._world.restore(self._loaded_view, snapshot["current_room_index"],
                                   bool(enemy and enemy["health"] > 0))
