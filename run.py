import base64
import datetime
import json
import os

import requests
from requests.auth import HTTPBasicAuth

ACCESS_TOKEN = os.environ['ACCESS_TOKEN']
SLACK_WEBHOOK = os.environ['SLACK_WEBHOOK']
SEARCH_URL = os.environ['SEARCH_URL']
SLACK_TOKEN = os.environ['SLACK_TOKEN']
NOTION_TOKEN = os.environ['NOTION_TOKEN']
NOTION_HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}
NOTION_PAGE_ID = os.environ['NOTION_PAGE_ID']


def get_notion_database_id(position_query):
    url = f'https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children'
    response = requests.get(url, headers=NOTION_HEADERS).json()
    matching_ids = [
        result['id']
        for result in response['results']
        if result.get('child_database', {}).get('title', '').startswith(position_query)
    ]
    return matching_ids[0].replace('-', '') if len(matching_ids) == 1 else ''


def get_notion_user_emails(database_id, created_at):
    url = f'https://api.notion.com/v1/databases/{database_id}/query'
    body = {
        'filter': {
            'or': [
                {
                    'and': [
                        {'property': 'Start Date', 'date': {'on_or_before': created_at}},
                        {'property': 'End Date', 'date': {'on_or_after': created_at}},
                    ]
                },
                {
                    'and': [
                        {'property': 'Start Date', 'date': {'on_or_before': today}},
                        {'property': 'End Date', 'date': {'on_or_after': today}},
                    ]
                }
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
                repo = invitation['repository']['full_name'].split('/')[1]
                url = invitation['url']
                repo_url = invitation['repository']['html_url']
                name, position = (
                    ' '.join(repo.split('_')[0:2]),
                    ' '.join(repo.split('_')[2:-2]).lower(),
                )
                name_query = f'{{"query":"{name}","root":[]}}'
                name_base64 = base64.b64encode(name_query.encode()).decode('utf-8')
                profile_url = f'{SEARCH_URL}{name_base64}'
                position_query = next(
                    (
                        query
                        for keyword, query in [
                            ('frontend', 'Frontend Engineer - Interview'),
                            ('backend', 'Backend Engineer - Interview'),
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
                    notion_user_emails = get_notion_user_emails(
                        notion_database_id, created_at
                    )
                    slack_user_ids = [
                        get_slack_user_id(email) for email in notion_user_emails
                    ]
                    mentions = ' '.join(
                        [f'<@{user_id}>' for user_id in slack_user_ids]
                    ) + ' :adore:' * len(slack_user_ids)
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
