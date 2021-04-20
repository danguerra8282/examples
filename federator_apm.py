# Description:
#   ------>>>>>> THIS SCRIPT WILL OVERWRITE THE LOCAL CONFIG FILE <<<<<<------
#   Dynamically creates credentials to AWS for 1 hour.  Credentials can then be
#   consumed by any language AWS CLI supports (AWS CLI, Python, Powershell, go,
#   etc...) by specifying the api command and the profile.
#   Example:  aws ec2 describe-instances --profile profile_name
#
#   Access is limited to the access you are assigned via LDAP groups and 
#   SSO Provider (F5 APM).
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
import base64
import xml.etree.ElementTree as ET

# CONST
F5_APM_PAGE = "https://site.domain.com"
F5_APM_POLICY_PAGE = F5_APM_PAGE + "/my.policy"
F5_APM_PAGE_RES_PAGE = F5_APM_PAGE + "/saml/idp/res?id=/Common/AWS.res"


def main():
    username = input('Enter username: ')
    password = getpass('Enter password: ')

    form = {
        'auth_mode': 'BASIC',
        'orig_url': '',
        'app_name': '',
        'override_uri_retention': 'false',
        'fieldId': '',
        'username': username,
        'password': password
    }

    session = requests.Session()
    session.post(F5_APM_PAGE)
    # print(f'{session.cookies}')

    s = session.post(F5_APM_POLICY_PAGE, cookies=session.cookies, data=form)
    # print(f'{s.text}')
    t = session.post(F5_APM_PAGE_RES_PAGE, cookies=session.cookies, data=form)
    # print(f'{t.text}')
    saml_assertion = str(t.text).split('<input type="hidden" name="SAMLResponse"')
    saml_assertion = saml_assertion[1].split('="')
    saml_assertion = saml_assertion[1].split('"/>')
    saml_assertion = saml_assertion[0]
    # print(f'saml_assertion: {saml_assertion}')

    if saml_assertion[-1] == '=':
        print('saml_assertion missing padding; fixing...')
        saml_assertion = saml_assertion + '='

    data = base64.b64decode(saml_assertion)
    # print(f'data: {data}')
    data = data.decode()
    # print(f'data: {data}')

    ns = {
        'saml2p': '{urn:oasis:names:tc:SAML:2.0:protocol}',
        'saml2': '{urn:oasis:names:tc:SAML:2.0:assertion}'
    }
    xp_subject_role_entitlement = \
        "{saml2}Assertion/{saml2}AttributeStatement/{saml2}Attribute[@Name=" \
        "'https://aws.amazon.com/SAML/Attributes/Role']/{saml2}AttributeValue".format(**ns)
    root = ET.fromstring(data)
    roles = root.findall(xp_subject_role_entitlement)
    roles_text = list(map(lambda m: m.text, roles))
    # print(root)
    # print(roles)
    # print(roles_text)

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

    session = boto3.Session()
    sts_client = session.client('sts')

    for role in roles_text:
        role = role.split(',')
        role_arn = role[1].strip()
        print(role_arn)

        try:
            principal_arn = (role_arn.split(':role')[0]) + ':saml-provider/SAML_PROVIDER_NAME'
            response = sts_client.assume_role_with_saml(
                RoleArn=role_arn,
                PrincipalArn=principal_arn,
                SAMLAssertion=saml_assertion,
                DurationSeconds=3600
            )
            access_key_id = response['Credentials']['AccessKeyId']
            secret_access_key = response['Credentials']['SecretAccessKey']
            session_token = response['Credentials']['SessionToken']
            print(f'access_key_id: {access_key_id}')
            print(f'secret_access_key: {secret_access_key}')
            print(f'session_token: {session_token}')
            print()
            # print(f'response: {response}')
        except Exception as e:
            print(f'e: {e}')
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
        # print(f'access_key_id: {access_key_id}')
        # print(f'secret_access_key: {secret_access_key}')
        # print(f'session_token: {session_token}')

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
                    # role[1].strip(),
                    role_arn.split('/')[1],
                    region='us-east-1'
                )

        except Exception as e:
            print(f'e: {e}')


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
        role,
        region
):
    print()

    # Write contents
    content = open('/Users/' + username + '/.aws/credentials', 'a')
    content.write('[' + account_alias + '/' + role + ']\n')
    content.write('aws_access_key_id=' + access_key_id + '\n')
    content.write('aws_secret_access_key=' + secret_access_key + '\n')
    content.write('aws_session_token=' + session_token + '\n')
    content.write('region= ' + region + '\n')
    content.write('\n')


# Run main() function
main()
