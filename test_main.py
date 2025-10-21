import unittest
from unittest import mock
import json
import datetime
from io import StringIO
import sys

import run


class TestMainBlock(unittest.TestCase):
    @mock.patch.dict(
        'os.environ',
        {
            'ACCESS_TOKEN': 'mock_token',
            'SLACK_WEBHOOK': 'https://mock-slack.com/webhook',
            'SEARCH_URL': 'https://mock-search.com/search?data=',
            'SLACK_TOKEN': 'mock_slack_token',
            'NOTION_TOKEN': 'mock_notion_token',
            'NOTION_PAGE_ID': 'mock-page-id',
        },
    )
    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('requests.get')
    @mock.patch('requests.post')
    @mock.patch('requests.patch')
    def test_successful_invitation_acceptance(
        self, mock_patch, mock_post, mock_get, mock_stdout
    ):
        """Test successful processing of a valid repository invitation."""
        # Mock GitHub invitations request
        mock_get.side_effect = [
            # GitHub invitations response
            mock.Mock(
                json=lambda: [
                    {
                        'id': 12345,
                        'expired': False,
                        'created_at': '2023-07-15T12:00:00Z',
                        'url': 'https://api.github.com/invitations/12345',
                        'repository': {
                            'full_name': 'org/John_Doe_Backend_Technical_Assessment',
                            'html_url': 'https://github.com/org/John_Doe_Backend_Technical_Assessment',
                        },
                    }
                ]
            ),
            # Notion database children response
            mock.Mock(
                json=lambda: {
                    'results': [
                        {
                            'id': 'mock-database-id',
                            'child_database': {'title': 'Backend Engineer'},
                        }
                    ]
                }
            ),
            # Notion database query response
            mock.Mock(
                json=lambda: {
                    'results': [
                        {
                            'properties': {
                                'Take-home Assignment': {
                                    'people': [
                                        {'person': {'email': 'reviewer@example.com'}}
                                    ]
                                }
                            }
                        }
                    ]
                }
            ),
            # Slack user lookup response
            mock.Mock(json=lambda: {'user': {'id': 'U12345'}}),
        ]

        # Mock response status codes
        mock_post.return_value = mock.Mock(status_code=200)
        mock_patch.return_value = mock.Mock(status_code=204)

        # Run the main function
        run.main()

        # Assert that the invitation was processed correctly
        output = mock_stdout.getvalue()
        self.assertIn('Accepting invitation ID 12345', output)
        self.assertIn('Responses: Slack - 200, GitHub - 204', output)

        # Verify the correct API calls were made
        self.assertEqual(mock_get.call_count, 4)
        self.assertEqual(mock_post.call_count, 1)  # Slack webhook
        self.assertEqual(mock_patch.call_count, 1)  # GitHub accept invitation

        # Verify GitHub invitation API was called
        self.assertTrue(
            any(
                call[0][0] == 'https://api.github.com/user/repository_invitations'
                for call in mock_get.call_args_list
            )
        )

        # Verify Slack webhook was called with the correct message
        slack_payload = json.loads(mock_post.call_args[1]['data'])
        self.assertIn(':adore-x5:', slack_payload['text'])
        self.assertIn('U12345', slack_payload['text'])

    @mock.patch.dict(
        'os.environ',
        {
            'ACCESS_TOKEN': 'mock_token',
            'SLACK_WEBHOOK': 'https://mock-slack.com/webhook',
            'SEARCH_URL': 'https://mock-search.com/search?data=',
            'SLACK_TOKEN': 'mock_slack_token',
            'NOTION_TOKEN': 'mock_notion_token',
            'NOTION_PAGE_ID': 'mock-page-id',
        },
    )
    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('requests.get')
    @mock.patch('requests.post')
    @mock.patch('requests.patch')
    def test_no_matching_notion_database(
        self, mock_patch, mock_post, mock_get, mock_stdout
    ):
        """Test invitation processing when no matching Notion database is found."""
        # Mock GitHub invitations request
        mock_get.side_effect = [
            # GitHub invitations response
            mock.Mock(
                json=lambda: [
                    {
                        'id': 12345,
                        'expired': False,
                        'created_at': '2023-07-15T12:00:00Z',
                        'url': 'https://api.github.com/invitations/12345',
                        'repository': {
                            'full_name': 'org/John_Doe_Unknown_Role_Technical_Assessment',
                            'html_url': 'https://github.com/org/John_Doe_Unknown_Role_Technical_Assessment',
                        },
                    }
                ]
            ),
            # Notion database children response (no match)
            mock.Mock(
                json=lambda: {
                    'results': [
                        {
                            'id': 'frontend-database-id',
                            'child_database': {'title': 'Frontend Engineer'},
                        }
                    ]
                }
            ),
        ]

        # Mock response status codes
        mock_post.return_value = mock.Mock(status_code=200)
        mock_patch.return_value = mock.Mock(status_code=204)

        # Run the main function
        run.main()

        # Assert that the invitation was processed with a warning
        output = mock_stdout.getvalue()
        self.assertIn('No matching notion database found', output)
        self.assertIn('Accepting invitation ID 12345', output)

        # Verify the Slack message includes the 404 engineers message
        slack_payload = json.loads(mock_post.call_args[1]['data'])
        self.assertIn('`Engineers 404 NOT FOUND`', slack_payload['text'])

    @mock.patch.dict(
        'os.environ',
        {
            'ACCESS_TOKEN': 'mock_token',
            'SLACK_WEBHOOK': 'https://mock-slack.com/webhook',
            'SEARCH_URL': 'https://mock-search.com/search?data=',
            'SLACK_TOKEN': 'mock_slack_token',
            'NOTION_TOKEN': 'mock_notion_token',
            'NOTION_PAGE_ID': 'mock-page-id',
        },
    )
    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('requests.get')
    def test_expired_invitation(self, mock_get, mock_stdout):
        """Test handling of expired invitations."""
        # Mock GitHub API response with an expired invitation
        mock_get.return_value = mock.Mock(
            json=lambda: [
                {
                    'id': 12345,
                    'expired': True,
                    'url': 'https://api.github.com/invitations/12345',
                    'repository': {
                        'full_name': 'org/John_Doe_Backend_Technical_Assessment',
                    },
                }
            ]
        )

        # Run the main function
        run.main()

        # Assert that expired invitation was skipped
        output = mock_stdout.getvalue()
        self.assertIn('Skipped handling invitation 12345', output)
        self.assertIn('because the invitation has expired', output)

    @mock.patch.dict(
        'os.environ',
        {
            'ACCESS_TOKEN': 'mock_token',
            'SLACK_WEBHOOK': 'https://mock-slack.com/webhook',
            'SEARCH_URL': 'https://mock-search.com/search?data=',
            'SLACK_TOKEN': 'mock_slack_token',
            'NOTION_TOKEN': 'mock_notion_token',
            'NOTION_PAGE_ID': 'mock-page-id',
        },
    )
    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('requests.get')
    def test_exception_handling(self, mock_get, mock_stdout):
        """Test exception handling during invitation processing."""
        # Mock GitHub API response
        mock_get.side_effect = [
            # GitHub invitations response
            mock.Mock(
                json=lambda: [
                    {
                        'id': 12345,
                        'expired': False,
                        'created_at': '2023-07-15T12:00:00Z',
                        'url': 'https://api.github.com/invitations/12345',
                        'repository': {
                            'full_name': 'org/John_Doe_Backend_Technical_Assessment',
                            'html_url': 'https://github.com/org/John_Doe_Backend_Technical_Assessment',
                        },
                    }
                ]
            ),
            # Make Notion API call raise an exception
            Exception("Test error"),
        ]

        # Run the main function
        run.main()

        # Assert that exception was caught and logged
        output = mock_stdout.getvalue()
        self.assertIn(
            'Error occurred when accepting invitation for invitation 12345', output
        )

    @mock.patch.dict(
        'os.environ',
        {
            'ACCESS_TOKEN': 'mock_token',
            'SLACK_WEBHOOK': 'https://mock-slack.com/webhook',
            'SEARCH_URL': 'https://mock-search.com/search?data=',
            'SLACK_TOKEN': 'mock_slack_token',
            'NOTION_TOKEN': 'mock_notion_token',
            'NOTION_PAGE_ID': 'mock-page-id',
        },
    )
    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('requests.get')
    def test_no_invitations(self, mock_get, mock_stdout):
        """Test behavior when there are no repository invitations."""
        # Mock GitHub API response with empty list
        mock_get.return_value = mock.Mock(json=lambda: [])

        # Run the main function
        run.main()

        # Assert that nothing was processed (no output)
        output = mock_stdout.getvalue()
        self.assertEqual('', output)

    @mock.patch.dict(
        'os.environ',
        {
            'ACCESS_TOKEN': 'mock_token',
            'SLACK_WEBHOOK': 'https://mock-slack.com/webhook',
            'SEARCH_URL': 'https://mock-search.com/search?data=',
            'SLACK_TOKEN': 'mock_slack_token',
            'NOTION_TOKEN': 'mock_notion_token',
            'NOTION_PAGE_ID': 'mock-page-id',
        },
    )
    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('requests.get')
    @mock.patch('requests.post')
    @mock.patch('requests.patch')
    def test_multiple_invitations(self, mock_patch, mock_post, mock_get, mock_stdout):
        """Test processing multiple invitations with different roles."""
        # Mock GitHub API response with multiple invitations
        mock_get.side_effect = [
            # GitHub invitations response with multiple invites
            mock.Mock(
                json=lambda: [
                    {
                        'id': 12345,
                        'expired': False,
                        'created_at': '2023-07-15T12:00:00Z',
                        'url': 'https://api.github.com/invitations/12345',
                        'repository': {
                            'full_name': 'org/John_Doe_Backend_Technical_Assessment',
                            'html_url': 'https://github.com/org/John_Doe_Backend_Technical_Assessment',
                        },
                    },
                    {
                        'id': 12346,
                        'expired': False,
                        'created_at': '2023-07-15T13:00:00Z',
                        'url': 'https://api.github.com/invitations/12346',
                        'repository': {
                            'full_name': 'org/Jane_Smith_Frontend_Technical_Assessment',
                            'html_url': 'https://github.com/org/Jane_Smith_Frontend_Technical_Assessment',
                        },
                    },
                    {
                        'id': 12347,
                        'expired': True,
                        'url': 'https://api.github.com/invitations/12347',
                        'repository': {
                            'full_name': 'org/Bob_Brown_Data_Technical_Assessment',
                        },
                    },
                ]
            ),
            # Notion database response for Backend
            mock.Mock(
                json=lambda: {
                    'results': [
                        {
                            'id': 'backend-database-id',
                            'child_database': {'title': 'Backend Engineer'},
                        }
                    ]
                }
            ),
            # Notion database query response for Backend
            mock.Mock(
                json=lambda: {
                    'results': [
                        {
                            'properties': {
                                'Take-home Assignment': {
                                    'people': [
                                        {
                                            'person': {
                                                'email': 'backend-reviewer@example.com'
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                }
            ),
            # Slack user lookup response for Backend
            mock.Mock(json=lambda: {'user': {'id': 'U12345'}}),
            # Notion database response for Frontend
            mock.Mock(
                json=lambda: {
                    'results': [
                        {
                            'id': 'frontend-database-id',
                            'child_database': {'title': 'Frontend Engineer'},
                        }
                    ]
                }
            ),
            # Notion database query response for Frontend
            mock.Mock(
                json=lambda: {
                    'results': [
                        {
                            'properties': {
                                'Take-home Assignment': {
                                    'people': [
                                        {
                                            'person': {
                                                'email': 'frontend-reviewer@example.com'
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                }
            ),
            # Slack user lookup response for Frontend
            mock.Mock(json=lambda: {'user': {'id': 'U12346'}}),
        ]

        # Mock responses
        mock_post.return_value = mock.Mock(status_code=200)
        mock_patch.return_value = mock.Mock(status_code=204)

        # Run the main function
        run.main()

        # Assert all invitations were processed appropriately
        output = mock_stdout.getvalue()
        self.assertIn('Accepting invitation ID 12345', output)
        self.assertIn('Accepting invitation ID 12346', output)
        self.assertIn('Skipped handling invitation 12347', output)

        # Verify the correct number of API calls were made
        self.assertEqual(mock_patch.call_count, 2)
        self.assertEqual(mock_post.call_count, 2)

    @mock.patch.dict(
        'os.environ',
        {
            'ACCESS_TOKEN': 'mock_token',
            'SLACK_WEBHOOK': 'https://mock-slack.com/webhook',
            'SEARCH_URL': 'https://mock-search.com/search?data=',
            'SLACK_TOKEN': 'mock_slack_token',
            'NOTION_TOKEN': 'mock_notion_token',
            'NOTION_PAGE_ID': 'mock-page-id',
        },
    )
    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('requests.get')
    @mock.patch('requests.post')
    @mock.patch('requests.patch')
    def test_invalid_repo_name_format(
        self, mock_patch, mock_post, mock_get, mock_stdout
    ):
        """Test handling of a repository with invalid name format."""
        # Mock GitHub API response with invalid repo name format
        mock_get.side_effect = [
            # GitHub invitations response
            mock.Mock(
                json=lambda: [
                    {
                        'id': 12345,
                        'expired': False,
                        'created_at': '2023-07-15T12:00:00Z',
                        'url': 'https://api.github.com/invitations/12345',
                        'repository': {
                            'full_name': 'org/InvalidRepoName',
                            'html_url': 'https://github.com/org/InvalidRepoName',
                        },
                    }
                ]
            ),
            # Notion database children response (no match because of invalid repo name)
            mock.Mock(
                json=lambda: {
                    'results': [
                        {
                            'id': 'frontend-database-id',
                            'child_database': {'title': 'Frontend Engineer'},
                        }
                    ]
                }
            ),
        ]

        # Mock responses
        mock_post.return_value = mock.Mock(status_code=200)
        mock_patch.return_value = mock.Mock(status_code=204)

        # Run the main function
        run.main()

        # Assert the invitation was processed with default values
        output = mock_stdout.getvalue()
        self.assertIn('Accepting invitation ID 12345', output)
        self.assertIn('No matching notion database found', output)

        # Verify the Slack message contains placeholder text
        slack_payload = json.loads(mock_post.call_args[1]['data'])
        self.assertIn('`Engineers 404 NOT FOUND`', slack_payload['text'])


if __name__ == '__main__':
    unittest.main()
