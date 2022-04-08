# Description:
#    Clones a github repo

# Import Modules
import boto3
import logging
import json
import datetime
from datetime import datetime
import sys
import os
import requests
import git
import zipfile
import shutil


# CONST
# DEVELOPER_TOKEN = 'asdf1234asdf1234'
DEVELOPER_TOKEN_SECRET_ID = sys.argv[1]
# REPO_NAME = '_repo_name_'
REPO_NAME = sys.argv[2]
GIT_URL = 'github.domain.com/ORG/' + REPO_NAME


def main():
    # Setup Connections
    session = boto3.Session()
    secretsmanager_client = session.client('secretsmanager')

    # Get Developer Token from Secrets Manager
    try:
        print(f'Attempting to get Developer Token from Secrets Manager')
        secret_value = secretsmanager_client.get_secret_value(
            SecretId=DEVELOPER_TOKEN_SECRET_ID
        )
        secret_value = json.loads(secret_value['SecretString'])
        secret_value = secret_value['developer_token']
        # print(f'secret_value: {secret_value}')

    except Exception as e:
        print(f'Failed to get Developer Token from Secrets Manager')
        raise e

    try:
        print(f'Attempting to clone repo locally...')
        response = clone_repo(
            # DEVELOPER_TOKEN,
            secret_value,
            GIT_URL,
            REPO_NAME
        )
        if response:
            print(f'Repo cloned successfully...')
    except Exception as e:
        print(f'Failed cloning repo locally')
        raise e


def clone_repo(
        developer_token,
        git_url,
        repo_name
):
    response = git.exec_command(
        'clone', 'https://' + developer_token + ':x-oauth-basic@' + git_url + '.git'
    )
    print(f'response: {response}')
    directory_contents = os.listdir('/tmp')
    print(f'/tmp directory_contents: {directory_contents}')
    directory_contents = os.listdir('/tmp/' + repo_name)
    print(f'/tmp/{repo_name} directory_contents: {directory_contents}')

    if response:
        return True
    else:
        return False


main()
