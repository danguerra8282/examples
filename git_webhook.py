# Lambda that gets Git information from dynamo table and pulls/zips/deploys new
# code whenever the git repo commitId changes.  The new commitId is then stored
# in the dynamo table.  This is used for the self updating codepipelines and is
# triggered every minute on the minute.

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
# from git import Repo
# import lambda2
# import pyhttpd
# import matplotlib.pyplot as plt

# Logging
logger = logging.getLogger()
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)
logging.getLogger("botocore").setLevel(logging.ERROR)


def lambda_handler(event, context):
    logger.debug(f'event: {event}')
    logger.debug(f'context: {context}')

    # Variables
    git_dynamo_table = 'git_repos'

    # Setup Connections
    session = boto3.Session()
    dynamo_client = session.client('dynamodb')
    ssm_client = session.client('ssm')
    codepipeline_client = session.client('codepipeline')
    s3_client = session.client('s3')

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

    # Check git repos for CommitId changes
    try:
        # git_username = ssm_client.get_parameter(
        #     Name='x_git_webhook_username',
        #     WithDecryption=True
        # )
        # git_password = ssm_client.get_parameter(
        #     Name='x_git_webhook_password',
        #     WithDecryption=True
        # )
        # git_username = git_username['Parameter']['Value']
        # git_password = git_password['Parameter']['Value']

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

            # if 'Personal_Repo' in repo_name:
            if 'x_Team_Repo' not in repo_name:
                # Clone repo locally
                try:
                    response = git.exec_command(
                        'clone', 'https://' + developer_token + ':x-oauth-basic@' + str(git_url) + '.git'
                    )
                    logger.debug(f'response: {response}')
                    directory_contents = os.listdir('/tmp')
                    logger.debug(f'/tmp directory_contents: {directory_contents}')
                    directory_contents = os.listdir('/tmp/' + repo_name)
                    logger.debug(f'/tmp/{repo_name} directory_contents: {directory_contents}')

                    # Get git log latest commit_id
                    latest_commit_id = git.exec_command('log', cwd='/tmp/' + repo_name) #### WORKS ####
                    logger.debug(f'latest_commit_id git log: {latest_commit_id}')
                    latest_commit_id = str(latest_commit_id)
                    latest_commit_id = latest_commit_id.split('commit ')
                    latest_commit_id = latest_commit_id[1].split('Author')[0]
                    latest_commit_id = latest_commit_id[:-2]
                    logger.info(f'latest_commit_id: {latest_commit_id}')

                    # Compare latest_commit_id against stored_commit_id
                    logger.debug(f'latest_commit_id: {latest_commit_id}')
                    logger.debug(f'stored_commit_id: {stored_commit_id}')
                    if latest_commit_id != stored_commit_id:
                        # zip up the cloned repo and copy it out into the codepipelines s3 bucket
                        print('do stuff')
                        # zipfile.ZipFile('hello.zip', mode='w').write("hello.csv")

                        # Get s3 source bucket from repo's codepipeline.json
                        try:
                            print()
                            with open('/tmp/' + repo_name + '/iac/CodePipeline.json') as f:
                                codepipeline_json = json.load(f)
                            logger.debug(f'codepipeline_json: {codepipeline_json}')
                            pipeline_name = codepipeline_json['Parameters']['pProductName']
                            logger.debug(f'pipeline_name: {pipeline_name}')
                            bucket_name = pipeline_name + '-source-bucket'

                        except Exception as e:
                            logger.error(f'Failed getting s3 source bucket from CodePipeline.json')
                            logger.error(f'e: {e}')

                        # Zip up files
                        try:
                            shutil.copytree('/tmp/' + repo_name + '/iac', '/tmp/iac')
                            zip_ref = zipfile.ZipFile('/tmp/deploy.zip', 'w')
                            # for dirname, subdirs, files in os.walk('/tmp/' + repo_name + '/iac'):
                            for dirname, subdirs, files in os.walk('/tmp/iac'):
                                zip_ref.write(dirname)
                                for filename in files:
                                    zip_ref.write(os.path.join(dirname, filename))
                            zip_ref.close()
                            directory_contents = os.listdir('/tmp/')
                            logger.debug(f'directory_contents after zip: {directory_contents}')
                        except Exception as e:
                            logger.error(f'Failed zipping files')
                            logger.error(f'e: {e}')

                        # Copy deploy.zip to pipeline's s3 bucket
                        try:
                            print()
                            copy_to_s3_bucket(
                                s3_client,
                                bucket_name,
                                '/tmp/deploy.zip'
                            )
                        except Exception as e:
                            logger.error(f'Failed copying deploy.zip to {bucket_name}')
                            logger.error(f'e: {e}')

                        # Update git_repos dynamoTable with the new commit_id
                        try:
                            logger.info(f'Update {git_dynamo_table} with latest_commit_id: {latest_commit_id} on '
                                        f'repo_name: {repo_name}')
                            dynamo_add_item(
                                dynamo_client,
                                git_dynamo_table,
                                repo_name,
                                developer_token,
                                'https://' + git_url,
                                latest_commit_id
                            )
                        except Exception as e:
                            logger.error(f'Failed updating dynamo table {git_dynamo_table} - with latest_commit_id: '
                                         f'{latest_commit_id} on repo_name: {repo_name}')
                            logger.error(f'e: {e}')
                except Exception as e:
                    logger.error(f'Failed while cloning repo {git_url}.  Verify developer token still exists.')
                    logger.error(f'e: {e}')

                # Remove /tmp contents after each execution
                try:
                    logger.debug(f'Removing /tmp/{repo_name}')
                    shutil.rmtree('/tmp/' + repo_name)
                    logger.debug(f'Removing /tmp/deploy.zip')
                    os.remove('/tmp/deploy.zip')
                    logger.debug(f'Removing /tmp/iac')
                    shutil.rmtree('/tmp/iac')
                    directory_contents = os.listdir('/tmp')
                    logger.debug(f'/tmp directory_contents: {directory_contents}')
                except Exception as e:
                    logger.info(f'Unable to remove previously logged object because it does not exist.  Continuing...')
                    logger.error(f'e: {e}')

            # Log moving to the next repo in list
            print('next...')

        # Add any repos that have changed to an array
    except Exception as e:
        print('something happened during git work')
        print(e)
        # directory_contents = os.listdir('/tmp')
        # logger.debug(f'/tmp directory_contents: {directory_contents}')
        # directory_contents = os.listdir('/tmp/Personal_Repo')
        # logger.debug(f'/tmp/Personal_Repo directory_contents: {directory_contents}')

    # Loop through the array, download the repo locally, zip up the contents, and
    # put into s3 bucket so that the pipelines will auto trigger
    try:
        print()
    except Exception as e:
        print()


def get_values_from_dynamo_column(
                                dynamo_client,
                                table_name,
                                column_name
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


def copy_to_s3_bucket(
        s3_client,
        bucket_name,
        file
):
    # Verify bucket exists
    buckets = s3_client.list_buckets()
    logger.info(f'buckets: {buckets}')
    logger.info(f'Copying {file} to {bucket_name}')
    s3_client.upload_file(file, bucket_name, 'deploy.zip')


def dynamo_add_item(
        dynamo_client,
        table_name,
        repo_name,
        developer_token,
        git_url,
        commit_id
):
    dynamo_client.put_item(
        TableName=table_name,
        Item={
            'repo_name': {
                'S': repo_name
            },
            'developer_token': {
                'S': developer_token
            },
            'git_url': {
                'S': git_url
            },
            'commit_id': {
                'S': commit_id
            }
        }
    )
