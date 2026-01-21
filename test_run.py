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
                ("Charlie Brown", "POSITION_NOT_FOUND"),
            ),
            (
                "Charlie_Brown_Software_Engineer_Intern_Technical_Assessment",
                ("Charlie Brown", "Software Engineer Intern"),
            ),
            # Test case with hyphenated first name
            (
                "Nice-Avery_Bar_Software_Engineer_Intern_Technical_Assessment",
                ("Nice-Avery Bar", "Software Engineer Intern"),
            ),
            # Test case with hyphenated last name
            (
                "John_Smith-Jones_Backend_Technical_Assessment",
                ("John Smith-Jones", "Backend Engineer"),
            ),
            # Test case with completely invalid format
            (
                "InvalidRepoName",
                ("InvalidRepoName", "POSITION_NOT_FOUND"),
            ),
            # Test cases for fallback matching logic
            # Case: Name without Technical_Assessment suffix
            (
                "John_Doe_Backend",
                ("John Doe", "Backend Engineer"),
            ),
            # Case: Name with extra parts, fallback should limit to first 2 words
            (
                "Alice_Smith_Jane_More_Words",
                ("Alice Smith", "POSITION_NOT_FOUND"),
            ),
            # Case: Hyphenated name with fallback
            (
                "Mary-Jane_Watson",
                ("Mary-Jane Watson", "POSITION_NOT_FOUND"),
            ),
            # Case: Single word name
            (
                "SingleName",
                ("SingleName", "POSITION_NOT_FOUND"),
            ),
            # Case: Name with role keyword but wrong format
            (
                "Bob_Jones_Frontend",
                ("Bob Jones", "Frontend Engineer"),
            ),
            # Case: Three-part name, should take first 2
            (
                "First_Middle_Last_Something",
                ("First Middle", "POSITION_NOT_FOUND"),
            ),
            # Case: With hyphens and underscores
            (
                "Jean-Paul_Sartre-Smith",
                ("Jean-Paul Sartre-Smith", "POSITION_NOT_FOUND"),
            ),
        ]

        for repo_name, expected in test_cases:
            with self.subTest(repo_name=repo_name):
                result = extract_candidate_info_from_repo(repo_name)
                self.assertEqual(result, expected)
