import base64
import datetime
import hashlib
import json
import os
import re
from typing import List

import requests
from requests.auth import HTTPBasicAuth

ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK')
SEARCH_URL = os.environ.get('SEARCH_URL')
SLACK_TOKEN = os.environ.get('SLACK_TOKEN')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}
NOTION_PAGE_ID = os.environ.get('NOTION_PAGE_ID')


def get_notion_database_id(position_query):
    url = f'https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children'
    response = requests.get(url, headers=NOTION_HEADERS).json()
    matching_ids = [
        result['id']
        for result in response['results']
        if result.get('child_database', {}).get('title', '').startswith(position_query)
    ]
    return matching_ids[0].replace('-', '') if len(matching_ids) == 1 else ''


def retrieve_all_take_home_reviewers(database_id: str) -> List[str]:
    endpoint = f'https://api.notion.com/v1/databases/{database_id}/query'
    response = requests.post(endpoint, headers=NOTION_HEADERS, timeout=30).json()
    results = response.get('results', [])
    emails = []
    for result in results:
        properties = result.get('properties', {})
        columns = properties.get(
            'Take-home Assignment', properties.get('Reviewer & Interviewer', {})
        )
        if not columns:
            continue

        peoples = columns.get('people', [])
        for people in peoples:
            _email = people.get('person', {}).get('email', None)
            if _email:
                emails.append(_email)

    return sorted(list(set(emails)))


def get_next_name(invitation_id: int, names: List[str]) -> str:
    """
    Retrieve distinct names for every new invitation ID
    """
    hash_object = hashlib.md5(str(invitation_id).encode())
    hash_hex = hash_object.hexdigest()

    # Convert the first 8 characters of the hash to an integer
    hash_int = int(hash_hex[:8], 16)
    index = hash_int % len(names)

    return names[index]


def get_notion_user_emails(database_id, created_at):
    url = f'https://api.notion.com/v1/databases/{database_id}/query'
    body = {
        'filter': {
            'or': [
                {
                    'and': [
                        {
                            'property': 'Start Date',
                            'date': {'on_or_before': created_at},
                        },
                        {'property': 'End Date', 'date': {'on_or_after': created_at}},
                    ]
                },
                {
                    'and': [
                        {'property': 'Start Date', 'date': {'on_or_before': today}},
                        {'property': 'End Date', 'date': {'on_or_after': today}},
                    ]
                },
            ]
        }
    }
    response = requests.post(url, headers=NOTION_HEADERS, data=json.dumps(body)).json()
    results = response.get('results', [])
    properties = results[0].get('properties', {}) if results else {}
    record = properties.get(
        'Take-home Assessment',
        properties.get(
            'Take-home Assignment', properties.get('Reviewer & Interviewer', {})
        ),
    )
    return [user['person']['email'] for user in record['people']]


def get_slack_user_id(user_email):
    url = f'https://slack.com/api/users.lookupByEmail?email={user_email}'
    headers = {
        'Authorization': f'Bearer {SLACK_TOKEN}',
        'Content-Type': 'application/json',
    }
    response = requests.get(url, headers=headers).json()
    return response.get('user').get('id')


def extract_candidate_info_from_repo(repo_name: str):
    '''
    Extract candidate name and position from the repo name using regex.

    return a tuple of (candidate_name, position)
    '''
    regex = r'^(?P<candidate_name>.+?)_(?P<position>[A-Za-z]+)_+[A-Za-z]+?_Technical_Assessment$'
    match = re.match(regex, repo_name)
    if not match:
        return 'CANDIDATE_NAME_NOT_FOUND', 'POSITION_NOT_FOUND'

    candidate_info = match.groupdict()
    return (
        candidate_info['candidate_name'].replace('_', ' '),
        # position is only the first word in the position string
        # eg:
        # 'Frontend Engineer' -> 'frontend'
        # 'Data Manager' -> 'data'
        # 'DevOps Engineer' -> 'devops'
        candidate_info['position'].replace('_', ' ').lower(),
    )


if __name__ == '__main__':
    auth = HTTPBasicAuth('bowtie-careers', ACCESS_TOKEN)

    invitations = requests.get(
        'https://api.github.com/user/repository_invitations',
        auth=auth,
    ).json()

    for invitation in invitations:
        invitation_id = invitation['id']

        if not invitation['expired']:
            try:
                today = str(datetime.datetime.now())
                created_at = invitation['created_at']
                # repo format is `{candidate_name}_{role}_Technical_Assessment`
                repo_name = invitation['repository']['full_name'].split('/')[1]
                url = invitation['url']
                repo_url = invitation['repository']['html_url']
                candidate_name, position = extract_candidate_info_from_repo(repo_name)

                # to find the candidate's profile on TeamTailor
                team_tailor_name_query = f'{{"query":"{candidate_name}","root":[]}}'
                name_base64 = base64.b64encode(team_tailor_name_query.encode()).decode(
                    'utf-8'
                )
                profile_url = f'{SEARCH_URL}{name_base64}'

                # to find the position in Notion
                position_query = next(
                    (
                        query
                        for keyword, query in [
                            ('frontend', 'Frontend Engineer - Interview'),
                            ('backend', 'Backend Engineer - Interview'),
                            ('data', 'Data Engineer/Manager'),
                            ('ai', 'AI Engineer'),
                            ('devops', 'DevOps Engineer - Interview'),
                            ('devsecops', 'DevOps Engineer - Interview'),
                            ('intern', 'Software Engineer Intern - Interview'),
                        ]
                        if keyword in position
                    ),
                    '',
                )
                notion_database_id = (
                    get_notion_database_id(position_query)
                    if position_query != ''
                    else ''
                )
                if notion_database_id != '':
                    notion_user_emails = retrieve_all_take_home_reviewers(
                        notion_database_id
                    )
                    email = get_next_name(invitation_id, notion_user_emails)
                    slack_user_id = get_slack_user_id(email)
                    mentions = f'<@{slack_user_id}> :adore-x5: '
                else:
                    mentions = '`Engineers 404 NOT FOUND` :shock:'
                    print('No matching notion database found')

                print(
                    f'Accepting invitation ID {invitation_id} via {url}, '
                    f'invited at {created_at}...',
                )

                # Send alert to Slack
                slack_response = requests.post(
                    SLACK_WEBHOOK,
                    data=json.dumps(
                        {
                            'text': '\n'.join(
                                [
                                    'New assessment from candidate has been submitted at ',
                                    f'`{created_at}` :tada:',
                                    repo_url,
                                    profile_url,
                                    mentions,
                                ]
                            ),
                        }
                    ),
                    headers={'Content-Type': 'application/json'},
                )

                # Accept the invitation
                accept_invitation_response = requests.patch(url, auth=auth)

                print(
                    f'Responses: Slack - {slack_response.status_code}, '
                    f'GitHub - {accept_invitation_response.status_code}',
                )

            except Exception as exc:
                print(
                    'Error occurred when accepting invitation for invitation '
                    f'{invitation_id} - {exc.__class__.__name__}',
                )

        else:
            print(
                f'Skipped handling invitation {invitation_id} '
                'because the invitation has expired',
            )
