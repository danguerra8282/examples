# Lambda that clones a git repo, pulls an accounts cost metrics, and then pushes the updated
# metrics back to the git repo.

# Import Modules
import boto3
import logging
import json
import datetime
# from datetime import datetime
import sys
import os
import requests
import git


# Logging
logger = logging.getLogger()
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)
logging.getLogger("botocore").setLevel(logging.ERROR)

# CONST
ROLE_TO_ASSUME = 'mult-account-role-name'


def lambda_handler(event, context):
    logger.debug(f'event: {event}')
    logger.debug(f'context: {context}')

    # Variables
    git_dynamo_table = 'git_repo_table_name'

    # Setup Connections
    session = boto3.Session()
    iam_client = session.client('iam')
    dynamo_client = session.client('dynamodb')
    ce_client = session.client('ce')
    sts_client = session.client('sts')

    # Verify DynamoTable Exists
    try:
        logger.debug(f'Verifying DynamoTable {git_dynamo_table} exists')
        response = dynamo_client.describe_table(TableName=git_dynamo_table)
        if response:
            logger.debug(f'DynamoTable {git_dynamo_table} found')
        else:
            logger.error(f'DynamoTable {git_dynamo_table} not found.  Verify it exists.')
            exit(1)
    except Exception as e:
        logger.error(f'Unable to find DynamoTable {git_dynamo_table}')
        logger.error(e)
        raise e

    # Pull Contents of DynamoTable
    # Git Repos
    try:
        response = get_values_from_dynamo_column(
            dynamo_client,
            git_dynamo_table,
            'git_url'
        )
        logger.debug(f'response: {response}')
    except Exception as e:
        logger.error(f'Failed getting information from DynamoTable')
        logger.error(e)
        raise e
    # Account IDs
    try:
        account_ids = get_values_from_dynamo_column(
            dynamo_client,
            "Environments",
            "AccountId"
        )
        logger.info(f'AccountIds found in Environments dynamo: {account_ids}')
        accounts_list = []
        for account_id in account_ids:
            accounts_list.append(account_id['AccountId']['S'])
        logger.info(f'accounts_list: {accounts_list}')

    except Exception as e:
        logger.error(f'Failed while getting information from dynamo table')
        logger.debug(e)
        raise e

    # Check git repos for CommitId changes
    try:
        changed_repos = []
        for resp in response:
            logger.debug(f'resp: {resp}')
            git_url = resp['git_url']['S']
            git_url = git_url.split("https://")[1]
            logger.debug(f'git_url: {git_url}')
            developer_token = resp['developer_token']['S']
            logger.debug(f'developer_token: {developer_token}')
            repo_name = resp['repo_name']['S']
            logger.debug(f'repo_name: {repo_name}')
            stored_commit_id = resp['commit_id']['S']
            logger.debug(f'stored_commit_id: {stored_commit_id}')

            # Clone repo locally
            if 'xxx_Repo_Name' in repo_name:
                response = git.exec_command(
                    'clone', 'https://' + developer_token + ':x-oauth-basic@' + str(git_url) + '.git'
                )
                logger.debug(f'response: {response}')
                directory_contents = os.listdir('/tmp')
                logger.debug(f'/tmp directory_contents: {directory_contents}')
                directory_contents = os.listdir('/tmp/' + repo_name)
                logger.debug(f'directory_contents: {directory_contents}')

                # # Pull Metrics for Account
                # response = get_account_metrics(
                #     iam_client,
                #     ce_client,
                #     start_range='2020-02-01',
                #     end_range='2020-05-01',
                #     granularity='MONTHLY',
                #     metric='UnblendedCost'
                # )
                # logger.debug(f'response: {response}')

                # Get Date Ranges for Metrics
                current_date = datetime.datetime.now()
                # Year
                current_year = '%04d' % current_date.year
                previous_year = int(current_year) - 1
                logger.debug(f'previous_year: {previous_year}')

                # Month
                current_month = '%02d' % current_date.month
                previous_month = int(current_month) - 1
                if previous_month < 10:
                    previous_month = '0' + str(previous_month)
                logger.debug(f'previous_month: {previous_month}')

                # Day
                current_day = '%02d' % current_date.day

                start_range = str(previous_year) + '-' + current_month + '-01'
                daily_start_range = current_year + '-' + str(previous_month) + '-' + current_day
                monthly_start_range = str(previous_year) + '-' + current_month + '-01'
                end_range = current_year + '-' + current_month + '-' + current_day
                logger.debug(f'start_range: {start_range}')
                logger.debug(f'end_range: {end_range}')
                logger.debug(f'daily_start_range: {daily_start_range}')
                logger.debug(f'monthly_start_range: {monthly_start_range}')

                # Pull Metrics for Accounts
                base_table = '{"graphs": [ '
                for account in accounts_list:
                    logger.info(f'Starting actions in {account}')
                    # Get credentials for account_id (Turn into a function?)
                    try:
                        assumed_credentials = sts_client.assume_role(
                            RoleArn=('arn:aws:iam::' + account + ':role/' + ROLE_TO_ASSUME),
                            RoleSessionName='AssumedRole'
                        )
                        logger.debug(f'assumed_credentials: {assumed_credentials}')
                    except Exception as e:
                        logger.error(f'Failed getting credentials for {account}')
                        logger.error(e)
                        raise e

                    # Setup connection in specified account
                    try:
                        iam_client = session.client('iam',
                            aws_access_key_id=assumed_credentials["Credentials"]['AccessKeyId'],
                            aws_secret_access_key=assumed_credentials["Credentials"]['SecretAccessKey'],
                            aws_session_token=assumed_credentials["Credentials"]['SessionToken'], )
                        logger.debug(f'iam_client: {iam_client}')

                        ce_client = session.client('ce',
                            aws_access_key_id=assumed_credentials["Credentials"]['AccessKeyId'],
                            aws_secret_access_key=assumed_credentials["Credentials"]['SecretAccessKey'],
                            aws_session_token=assumed_credentials["Credentials"]['SessionToken'], )
                        logger.debug(f'ce_client: {ce_client}')
                    except Exception as e:
                        logger.error(f'Failed creating session connection')
                        logger.error(e)
                        raise e

                    # Total Charge for Account
                    response = get_account_monthly_cost_metrics(
                        iam_client,
                        ce_client,
                        start_range=monthly_start_range,
                        end_range=end_range,
                        granularity='MONTHLY',
                        metric='UnblendedCost'
                    )
                    logger.debug(f'response: {response}')
                    base_table += response

                    # Daily Billing for by Team Tag
                    response = get_account_team_cost_metrics(
                        iam_client,
                        ce_client,
                        start_range=daily_start_range,
                        end_range=end_range,
                        granularity='DAILY',
                        metric='UnblendedCost'
                    )
                    logger.debug(f'response: {response}')
                    base_table += response

                base_table = base_table[:-1]
                base_table += ']}'

                # Write response to file
                fp = open('/tmp/' + repo_name + '/data/test.json', "w")
                # fp.write(str(response))
                fp.write(str(base_table))
                fp.close()
                fp = open('/tmp/' + repo_name + '/data/test.json', "r")
                metrics_contents = fp.read()
                fp.close()
                logger.debug(f'metrics_contents: {metrics_contents}')

                # Add file to git folder
                logger.debug(f'Adding files to git repo')
                response = git.exec_command(
                    'add', '.', cwd='/tmp/' + repo_name
                )
                logger.debug(f'response: {response}')
                directory_contents = os.listdir('/tmp/' + repo_name)
                logger.debug(f'/tmp/{repo_name} directory_contents: {directory_contents}')

                # Commit files to git repo
                logger.debug(f'Committing files to git repo')
                commit_env = os.environ
                commit_env['GIT_AUTHOR_NAME'] = 'info'
                commit_env['GIT_AUTHOR_EMAIL'] = 'info@place.com'
                commit_env['GIT_COMMITTER_NAME'] = 'info_AWS_Lambda'
                commit_env['GIT_COMMITTER_EMAIL'] = 'info@place.com'
                logger.debug(f'Pushing files to git repo')
                response = git.exec_command(
                    'commit', '-am "Updated Metrics"', cwd='/tmp/' + repo_name, env=commit_env
                )
                logger.debug(f'response: {response}')

                # Push files to git repo
                response = git.exec_command(
                    'push', cwd='/tmp/' + repo_name
                )
                logger.debug(f'response: {response}')

    except Exception as e:
        print('something happened during git work')
        print(e)


def get_account_team_cost_metrics(
        iam_client,
        ce_client,
        start_range,
        end_range,
        granularity,
        metric
):
    account_alias = iam_client.list_account_aliases()
    account_alias = account_alias['AccountAliases'][0]
    logger.debug(f'account_alias: {account_alias}')
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_range,
            'End': end_range
        },
        Granularity=granularity,
        Metrics=[
            metric
        ],
        GroupBy=[
            {
                'Type': 'TAG',
                'Key': 'Team'
            }
        ],
    )
    logger.debug(f'team_tag_response: {response}')
    # Define Table
    table = ['Date']
    table_string = '["Date'
    for day in response['ResultsByTime']:
        date = day['TimePeriod']['Start']
        logger.debug(f'day: {day}')

        for group in day['Groups']:
            # Add to table
            team = group['Keys'][0]
            if team not in table:
                table.append(team)
                table_string += '","' + team
    table_string += '"],'
    print(f"table: {table}")
    print(f'table_string: {table_string}')

    # Add Daily Charges by team
    # charges_table = []
    charges_table = ''
    for day in response['ResultsByTime']:
        date = day['TimePeriod']['Start']
        # charges_table.append(date)
        charges_table += '["' + date + '"'
        # print(day['Groups'][1])
        for table_group in table:
            # logger.debug(f'table_group: {table_group}')
            if 'Date' not in table_group:
                is_present = False
                for key in day['Groups']:
                    # logger.debug(f"key: {key['Keys'][0]}")
                    if table_group == key['Keys'][0]:
                        # print(key)
                        charge = key['Metrics']['UnblendedCost']['Amount']
                        # print(f'charge: {charge}')
                        trimmed_charge = charge.split('.')
                        # print(f'trimmed_charge: {len(trimmed_charge)}')
                        if len(trimmed_charge) > 1:
                            charge = trimmed_charge[0] + '.' + (trimmed_charge[1])[:2]
                            # print(f'updated charge: {charge}')
                        charge = float(charge)
                        # charges_table.append(charge)
                        charges_table += ', ' + str(charge)
                        is_present = True
                if not is_present:
                    charge = 0
                    # charges_table.append(charge)
                    charges_table += ', ' + str(0)
        charges_table += '],'
    charges_table = charges_table[:-1]
    print(f"charges_table: {charges_table}")

    # Put Data in Table Format
    return_table = '{"graph": {"data": [' + table_string + \
                   charges_table + '],' \
                   '"options" : {' \
                   '"title": "' + account_alias + \
                   ' Daily Team Charge - All Services", ' \
                   '"legend": { "position": "top" },' \
                   '"hAxis": {' \
                   '"title": "Date"' \
                   '},' \
                   '"vAxis": {' \
                   '"title": "Cost (in Dollars $)"' \
                   '}}}},'

    return return_table


def get_account_monthly_cost_metrics(
        iam_client,
        ce_client,
        start_range,
        end_range,
        granularity,
        metric
):
    account_alias = iam_client.list_account_aliases()
    account_alias = account_alias['AccountAliases'][0]
    logger.debug(f'account_alias: {account_alias}')
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_range,
            'End': end_range
        },
        Granularity=granularity,
        Metrics=[
            metric
        ],
    )
    # Pull Data in Table Format
    table = '{"graph": {"data": [["Date", "Monthly Cost"]'
    data = ''
    for resp in response['ResultsByTime']:
        daily_cost = resp['Total']['UnblendedCost']['Amount']
        print(f"['{resp['TimePeriod']['Start']}', {daily_cost}],")
        data += ',["' + resp['TimePeriod']['Start'] + '", ' + daily_cost + ']'
    table += data + '],' \
                    '"options" : {' \
                    '"title": "' + account_alias + ' Monthly Account Charge - All Services", ' \
                    '"legend": { "position": "top" },' \
                    '"hAxis": {' \
                    '"title": "Date"' \
                    '},' \
                    '"vAxis": {' \
                    '"title": "Cost (in Dollars $)"' \
                    '}}}},'

    return table


def get_account_metrics(
        iam_client,
        ce_client,
        start_range,
        end_range,
        granularity,
        metric
):
    account_alias = iam_client.list_account_aliases()
    account_alias = account_alias['AccountAliases'][0]
    logger.debug(f'account_alias: {account_alias}')
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_range,
            'End': end_range
        },
        Granularity=granularity,
        Metrics=[
            metric
        ],
    )
    # Pull Data in Table Format
    table = '{ "graphs" : [ {"graph": {"data": [["Date", "Monthly Cost"]'
    data = ''
    for resp in response['ResultsByTime']:
        daily_cost = resp['Total']['UnblendedCost']['Amount']
        print(f"['{resp['TimePeriod']['Start']}', {daily_cost}],")
        data += ',["' + resp['TimePeriod']['Start'] + '", ' + daily_cost + ']'
    table += data + '],' \
                    '"options" : {' \
                    '"title": "' + account_alias + ' Monthly Account Charge - All Services", ' \
                    '"legend": { "position": "top" },' \
                    '"hAxis": {' \
                    '"title": "Date"' \
                    '},' \
                    '"vAxis": {' \
                    '"title": "Cost (in Dollars $)"' \
                    '}}}}]}'

    return table


def get_values_from_dynamo_column(
                                dynamo_client,
                                table_name,
                                column_name,
                                filter=None,
                                filter_type=None,
                                exact_match=None
):
    """
    Searches and returns anything with the filter from dynamo
    :param dynamo_client: boto3.client
    :param table_name: (string) dynamo table to search
    :param column_name: (string) dynamo column to return data from
    :param filter: (string) optional filter string
    :param filter_type: (String) required type data type of optional filter
    :param exact_match: (String) optional for filter to be exact & not fuzzy
    :return files: array of strings
    """
    try:
        response = dynamo_client.scan(TableName=table_name)
        logger.debug(f'response: {response}')
    except Exception as e:
        logger.error(f'Failed to retrieve data from table')
        raise e

    array = []
    for resp in response['Items']:
        try:
            if column_name in resp:
                for value in resp[column_name]:
                    # array.append(resp[column_name][value])
                    array.append(resp)
        except Exception as e:
            logger.error(f'column_name: {column_name} not found in \
                        {table_name} dynamo table')
            logger.error(e)
            raise e
    logger.debug(f'array: {array}')
    return array
