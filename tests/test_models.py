import unittest
from src.domain.models import Hero, Item, Enemy, Room, InventoryError, InvalidNameError

class TestModels(unittest.TestCase):

    def test_hero_creation_warrior(self):
        hero = Hero("Conan", "warrior")
        self.assertEqual(hero.name, "Conan")
        self.assertEqual(hero.health, 30)
        self.assertEqual(hero.attack, 7)
        self.assertEqual(hero.defense, 4)

    def test_hero_creation_mage(self):
        hero = Hero("Gandalf", "mage")
        self.assertEqual(hero.health, 22)
        self.assertEqual(hero.attack, 10)
        self.assertEqual(hero.defense, 2)

    def test_replacing_weapon_does_not_stack_bonuses(self):
        hero = Hero("Ada", "warrior")
        sword1 = Item("Espada", "weapon", attack_bonus=3)
        sword2 = Item("Hacha", "weapon", attack_bonus=5)
        hero.add_item(sword1)
        hero.add_item(sword2)
        hero.equip_item(0) # Ataque total: 7 + 3 = 10
        hero.equip_item(1) # Ataque total: 7 + 5 = 12 (sin acumular el 3 de la Espada)
        self.assertEqual(hero.attack, 12)

    def test_damage_calculation_minimum_one(self):
        hero = Hero("Defensor", "warrior") # Defensa = 4
        # Ataque enemigo (2) < Defensa (4) -> Debe recibir 1 de daño mínimo
        damage = hero.receive_damage(raw_attack=2)
        self.assertEqual(damage, 1)
        self.assertEqual(hero.health, 29)

    def test_health_never_below_zero(self):
        hero = Hero("Frágil", "mage") # Vida 22
        hero.receive_damage(raw_attack=100)
        self.assertEqual(hero.health, 0)
        self.assertFalse(hero.is_alive)

    def test_duplicate_item_raises_inventory_error(self):
        hero = Hero("Heroe", "warrior")
        item1 = Item("Pimienta", "weapon", attack_bonus=1)
        item2 = Item("Pimienta", "weapon", attack_bonus=1)
        hero.add_item(item1)
        with self.assertRaises(InventoryError):
            hero.add_item(item2)

    def test_invalid_inventory_index_raises_error(self):
        hero = Hero("Heroe", "warrior")
        with self.assertRaises(InventoryError):
            hero.equip_item(99)

    def test_round_trip_serialization(self):
        hero = Hero("Aragorn", "warrior")
        sword = Item("Andúril", "weapon", attack_bonus=5)
        hero.add_item(sword)
        hero.equip_item(0)
        
        data = hero.to_dict()
        reconstructed = Hero.from_dict(data)

        self.assertEqual(reconstructed.name, hero.name)
        self.assertEqual(reconstructed.health, hero.health)
        self.assertEqual(reconstructed.attack, hero.attack)
        self.assertEqual(len(reconstructed.inventory), 1)
        self.assertEqual(reconstructed.weapon.name, "Andúril")

if __name__ == "__main__":
    unittest.main()