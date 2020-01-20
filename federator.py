# Description:
#   ------>>>>>> THIS SCRIPT WILL OVERWRITE THE LOCAL CONFIG FILE <<<<<<------
#   Dynamically creates credentials to AWS for 1 hour.  Credentials can then be
#   consumed by any language AWS CLI supports (AWS CLI, Python, Powershell, go,
#   etc...) by specifying the api command and the profile.
#   Example:  aws ec2 describe-instances --profile itec-sandbox-01
#
#   Access is limited to the access you are assigned via LDAP groups and company
#   Federated Identity Management (FIM).
#
#   Required Modules:
#   - boto3
#   - getpass
#   - requests
#   - os
#
#   * Currently works on Linux based OS's but will soon contain functionality
#   for Windows OS's

import boto3
from getpass import getpass
import requests
import os

# CONST
LOGON_PAGE = "url"
FIM_PAGE = "url"
ROLE_TO_ASSUME = 'role'

# Remove the accounts you do not have access to:
profile_list = [
    "1234",  # acct-dev-01
    "4567",  # acct-prod-01
    "6789"   # acct-qa-01
]


def main():
    username = input('Enter username: ')
    password = getpass('Enter password: ')

    form = {
        'auth_mode': 'BASIC',
        'orig_url': '',
        'app_name': '',
        'override_uri_retention': 'false',
        'user': username,
        'password': password
    }

    # Log into FIM pages & get saml response
    session = requests.Session()
    session.post(LOGON_PAGE, data=form)
    response = requests.get(FIM_PAGE, cookies=session.cookies)
    saml = str(response.text).split('name="SAMLResponse" value="')
    saml = saml[1]
    saml = str(saml).split('">')
    saml_assertion = saml[0]

    # Ensure config file exists and remove contents
    if not os.path.isdir('/Users/' + username + '/.aws/'):
        os.mkdir('/Users/' + username + '/.aws/')
    if os.path.isfile('/Users/' + username + '/.aws/credentials'):
        # Remove contents
        open('/Users/' + username + '/.aws/credentials', 'w').close()
    # Create config and add [default]
    if not os.path.isfile('/Users/' + username + '/.aws/config'):
        content = open('/Users/' + username + '/.aws/config', 'a')
        content.write('[default]\n')
        content.write('region = us-east-1\n')
        content.write('\n')

    # Setup Connection
    session = boto3.Session()
    sts_client = session.client('sts')

    for item in profile_list:
        try:
            role_arn = 'arn:aws:iam::' + item + ':role/' + ROLE_TO_ASSUME
            principal_arn = "arn:aws:iam::" + item + ":saml-provider/saml-provider"
            response = sts_client.assume_role_with_saml(
                RoleArn=role_arn,
                PrincipalArn=principal_arn,
                SAMLAssertion=saml_assertion,
                DurationSeconds=3600
            )
            access_key_id = response['Credentials']['AccessKeyId']
            secret_access_key = response['Credentials']['SecretAccessKey']
            session_token = response['Credentials']['SessionToken']

        except Exception as e:
            print(f'Failed to create a profile for {item}.  '
                  f'Verify you have access to this account or correct role_arn.')
            access_key_id = ''
            secret_access_key = ''
            session_token = ''

        # Assume into account
        iam_client = session.client(
            'iam',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
        )
        response = iam_client.list_account_aliases()
        account_alias = response['AccountAliases']
        account_alias = str(account_alias).split("'")[1]
        print(f'Creating profile for {account_alias}')

        # Create profiles
        try:
            if os.path.isdir('c:\\users\\' + username):
                # Create for Windows
                create_profile_windows(
                    access_key_id,
                    secret_access_key,
                    session_token,
                    username,
                    account_alias,
                    region='us-east-1'
                )
            elif os.path.isdir('/Users/' + username):
                # Create for Linux kernel
                create_profile_linux(
                    access_key_id,
                    secret_access_key,
                    session_token,
                    username,
                    account_alias,
                    region='us-east-1'
                )

        except Exception as e:
            print('')


def create_profile_windows(
        access_key_id,
        secret_access_key,
        session_token,
        username,
        account_alias,
        region
):
    if os.path.isdir('c:\\users\\' + username + '\\.aws'):
        print('Windows stuff')


def create_profile_linux(
        access_key_id,
        secret_access_key,
        session_token,
        username,
        account_alias,
        region
):
    print()

    # Write contents
    content = open('/Users/' + username + '/.aws/credentials', 'a')
    content.write('[' + account_alias + ']\n')
    content.write('aws_access_key_id=' + access_key_id + '\n')
    content.write('aws_secret_access_key=' + secret_access_key + '\n')
    content.write('aws_session_token=' + session_token + '\n')
    content.write('region= ' + region + '\n')
    content.write('\n')


# Run main() function
main()
