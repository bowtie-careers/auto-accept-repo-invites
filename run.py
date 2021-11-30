import json
import os

import requests
from requests.auth import HTTPBasicAuth

ACCESS_TOKEN = os.environ['ACCESS_TOKEN']
SLACK_WEBHOOK = os.environ['SLACK_WEBHOOK']

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
                created_at = invitation['created_at']
                repo = invitation['repository']['full_name']
                url = invitation['url']

                print(
                    f'Accepting invitation ID {invitation_id} via {url}, '
                    f'invited at {created_at}...',
                )

                # Send alert to Slack
                slack_response = requests.post(
                    SLACK_WEBHOOK,
                    data=json.dumps({
                        'text': '\n'.join([
                            'New assessment from candidate has been submitted at ',
                            f'`{created_at}` :tada:',
                            invitation['repository']['html_url'],
                        ]),
                    }),
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
                    'Error occured when accepting invitation for invitation '
                    f'{invitation_id} - {exc.__class__.__name__}',
                )

        else:
            print(
                f'Skipped handling invitation {invitation_id} '
                'because the invitation has expired',
            )
