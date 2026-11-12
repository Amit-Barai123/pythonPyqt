import unittest

from sample_data import get_sample_rows
from services.validator import calculate_totals, validate_input_rows


class ValidatorTests(unittest.TestCase):
    def test_sample_data_is_valid(self):
        self.assertEqual(validate_input_rows(get_sample_rows()), [])

    def test_empty_rows_are_rejected(self):
        self.assertTrue(validate_input_rows([]))

    def test_invalid_date_and_amounts_are_reported(self):
        row = ["not-a-date", "Client", "Design", "Task", "zero", "-2"]
        problems = validate_input_rows([row])
        self.assertTrue(any("valid date" in problem for problem in problems))
        self.assertTrue(any("hours must be a number" in problem for problem in problems))
        self.assertTrue(any("rate cannot be negative" in problem for problem in problems))

    def test_totals_are_grouped_by_client(self):
        hours, amount, by_client = calculate_totals(get_sample_rows())
        self.assertEqual(hours, 35)
        self.assertEqual(amount, 3240)
        self.assertEqual(by_client["Max Studio"], 1740)
        self.assertEqual(by_client["blueBerry"], 1500)


if __name__ == "__main__":
    unittest.main()
