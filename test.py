import unittest
import json
import aba


class TestABA(unittest.TestCase):
    def setUp(self):
        # Charge le json d'exemple
        with open('exemple.json', 'r') as f:
            json_data = json.load(f)

        # Création et initialisation d'un objet ABA
        self.aba = aba.ABA()
        self.aba.parse_from_json(json_data)
        self.aba.validate()

    def test_argument_generation(self):
        args = self.aba.derive_arguments()

        # Vérifie présence argument spécifique p supporté par a
        expected_arg = {
            "conclusion": "p",
            "assumptions": frozenset({"a"})
        }
        self.assertTrue(any(arg["conclusion"] == expected_arg["conclusion"] and arg["assumptions"] == expected_arg["assumptions"] for arg in args))

        # Vérifie un fait q sans hypothèse
        expected_fact = {
            "conclusion": "q",
            "assumptions": frozenset()
        }
        self.assertTrue(any(arg["conclusion"] == expected_fact["conclusion"] and arg["assumptions"] == expected_fact["assumptions"] for arg in args))

        # Vérifie argument r supporté par b,c
        another_expected_arg = {
            "conclusion": "r",
            "assumptions": frozenset({"b", "c"})
        }
        self.assertTrue(any(arg["conclusion"] == another_expected_arg["conclusion"] and arg["assumptions"] == another_expected_arg["assumptions"] for arg in args))


class TestPreferenceAttack(unittest.TestCase):
    def setUp(self):
        self.aba = aba.ABA()
        self.aba.literals = {'a', 'b'}
        self.aba.assumptions = {'a', 'b'}
        self.aba.contraries = {'a': 'b', 'b': 'a'}
        self.aba.preferences = {'a': 2, 'b': 1}  # a préféré à b

    def test_preference_allows_attack(self):
        self.assertTrue(self.aba.check_preference_allows_attack('a', 'b'))
        self.assertFalse(self.aba.check_preference_allows_attack('b', 'a'))

        self.aba.preferences = {'a': 1, 'b': 1}
        self.assertTrue(self.aba.check_preference_allows_attack('a', 'b'))
        self.assertTrue(self.aba.check_preference_allows_attack('b', 'a'))

    def test_derive_attacks_with_preference(self):
        arguments = [
            {'conclusion': 'a', 'assumptions': {'a'}},
            {'conclusion': 'b', 'assumptions': {'b'}}
        ]
        attacks = self.aba.derive_attacks(arguments)
        self.assertIn((arguments[0], arguments[1]), attacks)
        self.assertNotIn((arguments[1], arguments[0]), attacks)


if __name__ == '__main__':
    unittest.main()
