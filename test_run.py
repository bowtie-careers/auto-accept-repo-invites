import unittest

from run import extract_candidate_info_from_repo


class TestRun(unittest.TestCase):
    def test_extract_candidate_info_from_repo(self):
        test_cases = [
            (
                "Victor_Boy_Data_Something_Technical_Assessment",
                ("Victor Boy", "Data Engineer/Manager"),
            ),
            (
                "Victor_Boy_Asura_Senior_Data_Manager_Technical_Assessment",
                ("Victor Boy", "Data Engineer/Manager"),
            ),
            (
                "Alice_Smith_Frontend_Engineer_Technical_Assessment",
                ("Alice Smith", "Frontend Engineer"),
            ),
            (
                "John_Doe_Backend_Engineer_Technical_Assessment",
                ("John Doe", "Backend Engineer"),
            ),
            (
                "Jane_Doe_DevOps_Engineer_Technical_Assessment",
                ("Jane Doe", "DevOps Engineer"),
            ),
            (
                "Bob_Jones_Data_Engineer_Technical_Assessment",
                ("Bob Jones", "Data Engineer/Manager"),
            ),
            (
                "Charlie_Brown_Software_Engineer",
                ("CANDIDATE_NAME_NOT_FOUND", "POSITION_NOT_FOUND"),
            ),
        ]

        for repo_name, expected in test_cases:
            with self.subTest(repo_name=repo_name):
                result = extract_candidate_info_from_repo(repo_name)
                self.assertEqual(result, expected)
