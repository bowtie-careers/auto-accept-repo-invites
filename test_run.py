import unittest

from run import extract_candidate_info_from_repo


class TestRun(unittest.TestCase):
    def test_extract_candidate_info_from_repo(self):
        test_cases = [
            (
                "Victor_Boy_Data_Something_Technical_Assessment",
                ("Victor Boy", "data"),
            ),
            (
                "Alice_Smith_Frontend_Engineer_Technical_Assessment",
                ("Alice Smith", "frontend"),
            ),
            (
                "John_Doe_Backend_Engineer_Technical_Assessment",
                ("John Doe", "backend"),
            ),
            (
                "Jane_Doe_DevOps_Engineer_Technical_Assessment",
                ("Jane Doe", "devops"),
            ),
            (
                "Bob_Jones_Data_Engineer_Technical_Assessment",
                ("Bob Jones", "data"),
            ),
            (
                "Charlie_Brown_Software_Engineer",
                ("CANDIDATE_NAME_NOT_FOUND", "POSITION_NOT_FOUND"),
            ),
        ]

        for repo_name, expected in test_cases:
            result = extract_candidate_info_from_repo(repo_name)
            self.assertEqual(result, expected)
