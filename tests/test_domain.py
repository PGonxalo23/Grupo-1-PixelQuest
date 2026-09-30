import unittest
from src.domain.exceptions import (
    DomainError,
    ValidationError,
    InvalidNameError,
    InvalidStatError,
    InvalidItemError,
)
from src.domain.validators import (
    validate_name,
    validate_positive_int,
    validate_non_negative_int,
    validate_item_type,
)

class TestDomainValidations(unittest.TestCase):

    def test_validate_name_valid(self):
        self.assertEqual(validate_name("  Guerrero  "), "Guerrero")

    def test_validate_name_invalid(self):
        with self.assertRaises(InvalidNameError):
            validate_name("")
        with self.assertRaises(InvalidNameError):
            validate_name("   ")
        with self.assertRaises(InvalidNameError):
            validate_name(None)

    def test_validate_positive_int_valid(self):
        self.assertEqual(validate_positive_int(10, "attack"), 10)

    def test_validate_positive_int_invalid(self):
        with self.assertRaises(InvalidStatError):
            validate_positive_int(0, "attack")
        with self.assertRaises(InvalidStatError):
            validate_positive_int(-5, "attack")
        with self.assertRaises(InvalidStatError):
            validate_positive_int(True, "attack")

    def test_validate_non_negative_int_valid(self):
        self.assertEqual(validate_non_negative_int(0, "bonus"), 0)
        self.assertEqual(validate_non_negative_int(5, "bonus"), 5)

    def test_validate_non_negative_int_invalid(self):
        with self.assertRaises(InvalidStatError):
            validate_non_negative_int(-1, "bonus")
        with self.assertRaises(InvalidStatError):
            validate_non_negative_int(False, "bonus")

    def test_validate_item_type_valid(self):
        self.assertEqual(validate_item_type(" Weapon "), "weapon")
        self.assertEqual(validate_item_type("ARMOR"), "armor")

    def test_validate_item_type_invalid(self):
        with self.assertRaises(InvalidItemError):
            validate_item_type("potion")

    def test_hierarchy(self):
        err = InvalidNameError("Error")
        self.assertIsInstance(err, ValidationError)
        self.assertIsInstance(err, DomainError)

if __name__ == "__main__":
    unittest.main() 