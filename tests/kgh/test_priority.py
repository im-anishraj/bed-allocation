import unittest
from hospital.people import Patient
from hospital.priority import calculate_patient_priority


class TestPatientPriority(unittest.TestCase):

    def test_high_priority_patient(self):
        # Critical patient: high acuity (40) + known covid (35) + age 85 (20) = 95 -> HIGH PRIORITY
        patient = Patient(
            name="Critical Patient",
            sex="female",
            department="medicine",
            is_high_acuity=True,
            is_known_covid=True,
            age=85,
        )
        res = calculate_patient_priority(patient)
        self.assertGreaterEqual(res["score"], 70)
        self.assertEqual(res["target_ward"], "Critical")
        self.assertEqual(res["priority_tier"], "HIGH PRIORITY")
        self.assertEqual(res["priority_level"], "HIGH PRIORITY (Immediate Bed Required)")
        self.assertEqual(res["color"], "red")
        self.assertIn("High Clinical Acuity (+40)", res["factors"])
        self.assertIn("Confirmed COVID-19 Isolation (+35)", res["factors"])

    def test_medium_priority_patient(self):
        # Moderate patient: immunosuppressed (30) + age 68 (15) = 45 -> MEDIUM PRIORITY / Monitor
        patient = Patient(
            name="Vulnerable Patient",
            sex="male",
            department="surgery",
            is_immunosupressed=True,
            age=68,
        )
        res = calculate_patient_priority(patient)
        self.assertGreaterEqual(res["score"], 40)
        self.assertLess(res["score"], 70)
        self.assertEqual(res["target_ward"], "Monitor")
        self.assertEqual(res["priority_tier"], "MEDIUM PRIORITY")
        self.assertEqual(res["priority_level"], "MEDIUM PRIORITY (Urgent Admission)")
        self.assertEqual(res["color"], "orange")

    def test_standard_priority_patient(self):
        # Routine patient: age 35, no acute or safety flags -> score 0 -> General
        patient = Patient(
            name="Routine Patient",
            sex="male",
            department="medicine",
            age=35,
        )
        res = calculate_patient_priority(patient)
        self.assertEqual(res["score"], 0)
        self.assertEqual(res["target_ward"], "General")
        self.assertEqual(res["priority_tier"], "STANDARD PRIORITY")
        self.assertEqual(res["priority_level"], "STANDARD PRIORITY (Routine Admission)")
        self.assertEqual(res["color"], "green")
        self.assertEqual(len(res["factors"]), 0)

    def test_safety_risks_ladder(self):
        # Falls risk (15) + middle age 50 (5) = 20 pts -> General
        patient = Patient(
            name="Safety Patient",
            sex="female",
            department="medicine",
            age=50,
            is_falls_risk=True,
        )
        res = calculate_patient_priority(patient)
        self.assertEqual(res["score"], 20)
        self.assertEqual(res["target_ward"], "General")
        self.assertTrue(any("Falls Risk" in f for f in res["factors"]))

    def test_dict_input(self):
        # Verify function accepts dictionary as well as Patient instance
        patient_dict = {
            "Name": "Dict Patient",
            "Age": 82,
            "High Acuity": "Yes",
            "COVID-19 status": "Red",
        }
        res = calculate_patient_priority(patient_dict)
        self.assertGreaterEqual(res["score"], 70)
        self.assertEqual(res["priority_tier"], "HIGH PRIORITY")


if __name__ == "__main__":
    unittest.main()
