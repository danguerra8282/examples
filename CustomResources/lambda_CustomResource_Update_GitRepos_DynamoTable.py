# Custom Resource; will populate a new record in git_repos dynamoTable

# Import Modules
import boto3
import logging
import json
import datetime
from datetime import datetime
import cfnresponse
import time
import os


def lambda_handler(event, context):
    # Logging
    logger = logging.getLogger()
    # logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    session = boto3.Session()
    dynamo_client = session.client('dynamodb')

    # Variables
    git_dynamo_table = 'git_repos'

    logger.debug(f'event: {event}')
    logger.debug(f'context: {context}')
    git_url = event['ResourceProperties']['GitHubRepoUrl']
    # git_url = git_url.split("https://")[1]
    logger.debug(f'git_url: {git_url}')
    developer_token = event['ResourceProperties']['GitHubDeveloperToken']
    logger.debug(f'developer_token: {developer_token}')
    repo_name = git_url.split('/')[-1]
    logger.debug(f'repo_name: {repo_name}')

    if 'Create' in event['RequestType']:
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

        # Add new record to table
        try:
            logger.info(f'Adding {repo_name} to {git_dynamo_table} DynamoTable')
            dynamo_add_item(
                dynamo_client,
                git_dynamo_table,
                repo_name,
                developer_token,
                git_url
            )
        except Exception as e:
            logger.error(f'Failed adding {repo_name} to {git_dynamo_table}')
            logger.error(f'e: {e}')

    # Send Signal
    response_data = dict()
    response_data['SUCCESS'] = "SUCCESS - This worked"
    logger.debug(f'response_data: {response_data}')

    cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, "CustomResourcePhysicalID")


def dynamo_add_item(
        dynamo_client,
        table_name,
        repo_name,
        developer_token,
        git_url
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
                'S': '0'
            }
        }
    )
