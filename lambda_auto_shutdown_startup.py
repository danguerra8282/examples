# Shutsdown or PowersOn an EC2 instance

# Import Modules
import boto3
import logging
import json
import datetime
from datetime import datetime

# Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)
logging.getLogger("botocore").setLevel(logging.ERROR)


# MAIN #
def lambda_handler(_event, _context):
    logger.info(f'Starting auto_shutdown_startup actions')
    logger.debug(f'_event: {_event}')

    # Get Cloudwatch event source_type
    try:
        event_source_type = _event['source']
        logger.debug(f'event_source_type: {event_source_type}')
    except Exception as e:
        logger.debug(f'No source found in the _event')

    # Get datetime
    try:
        utc_date_time = datetime.utcnow()
        logger.info(f'utc_date_time: {utc_date_time}')
        current_hour = utc_date_time.hour
        current_hour = current_hour - 4
        logger.debug(f'current_hour: {current_hour}')
    except Exception as e:
        logger.error(f'Failed retrieving datetime')
        raise e

    # Setup Connections
    session = boto3.Session()
    ec2_client = session.client('ec2')
    dynamo_client = session.client('dynamodb')

    # Get information from dynamo table
    try:
        account_ids = get_values_from_dynamo_column(dynamo_client,
                                                    "Environments",
                                                    "AccountId",
                                                    None,
                                                    'S')
        logger.info(f'AccountIds found in Environments dynamo: {account_ids}')
    except Exception as e:
        logger.error(f'Failed while getting information from dynamo table')
        raise e

    # Loop through each account and take action
    for account in account_ids:
        try:
            logger.info(f'Starting actions in {account}')
            instances = ec2_client.describe_instances()
            logger.debug(f'instances: {instances}')
            # for instance in instances['Reservations'][0]['Instances']:
            for res in instances['Reservations']:
                for instance in res['Instances']:
                    logger.debug(f'***** instance: {instance}')
                    try:
                        logger.info(f"Checking instance: {instance['InstanceId']}")

                        # Shutdown Action
                        try:
                            if ('pending' in instance['State']['Name'] or
                                    'running' in instance['State']['Name']):
                                shutdown_process(
                                    ec2_client,
                                    instance,
                                    current_hour)
                        except Exception as e:
                            logger.error(f'Failed shutdown_process on {instance}')
                            raise e

                        # Startup Action
                        try:
                            if 'stopped' in instance['State']['Name']:
                                startup_process(
                                    ec2_client,
                                    instance,
                                    current_hour
                                )
                        except Exception as e:
                            logger.error(f'Failed startup_process on {instance}')
                            raise e
                    except Exception as e:
                        logger.error(f'Failed action on {instance}')
                        raise e

        except Exception as e:
            logger.error(f'Failed action in account: {account}')
            raise e


def shutdown_process(ec2_client,
                     instance,
                     current_hour):
    """
    Checks EC2 instance for AutoShutDown tag and powers off instance
    :param ec2_client: boto3.client
    :param instance: (dict) instance object
    :param current_hour: (int) current datetime hour
    """
    for tag in instance['Tags']:
        tag_lowered = str(tag['Key']).lower()
        if 'autoshutdown' in tag_lowered:
            auto_shutdown_time = tag.get('Value')
            logger.debug(f'auto_shutdown_time: {auto_shutdown_time}')
            logger.debug(f'current_hour: {current_hour}')
            if auto_shutdown_time == str(current_hour):
                logger.info(f"Shutting down: {instance['InstanceId']}")
                response = ec2_client.stop_instances(
                    InstanceIds=[instance['InstanceId']]
                    )
                logger.debug(f'response: {response}')
                ec2_client.create_tags(
                    Resources=[instance['InstanceId']],
                    Tags=[{
                        'Key': 'LastAutomatedShutdownReason',
                        'Value': (str(datetime.utcnow()) +
                                  ' - AutoShutdown requested')
                        }]
                    )


def startup_process(ec2_client,
                    instance,
                    current_hour):
    """
    Checks EC2 instance for AutoStartup tag and powers on instance
    :param ec2_client: boto3.client
    :param instance: (dict) instance object
    :param current_hour: (int) current datetime hour
    """
    for tag in instance['Tags']:
        tag_lowered = str(tag['Key']).lower()
        if 'autostartup' in tag_lowered:
            auto_startup_time = tag.get('Value')
            logger.debug(f'auto_startup_time: {auto_startup_time}')
            logger.debug(f'current_hour: {current_hour}')
            if auto_startup_time == str(current_hour):
                logger.info(f"Powering on: {instance['InstanceId']}")
                response = ec2_client.start_instances(
                    InstanceIds=[instance['InstanceId']]
                    )
                logger.debug(f'response: {response}')
                ec2_client.create_tags(
                    Resources=[instance['InstanceId']],
                    Tags=[{
                        'Key': 'LastAutomatedStartup',
                        'Value': (str(datetime.utcnow()))
                        }]
                    )


def get_values_from_dynamo_column(dynamo_client,
                                  table_name,
                                  column_name,
                                  filter=None,
                                  filter_type=None):
    """
    Searches and returns anything with the filter from dynamo
    :param dynamo_client: boto3.client
    :param table_name: (string) table to search
    :param column_name: (string) column to search
    :param filter: (string) optional value to filter on
    :param filter_type: (string) required if filter!=None;
        object type for the filter string
    :return array: array of strings
    """
    try:
        response = dynamo_client.scan(TableName=table_name)
        logger.debug(f'response: {response}')
    except Exception as e:
        logger.error(f'Failed to retreive data from table')
        raise e

    if filter:
        filtered_array = []
        for resp in response['Items']:
            try:
                if filter in resp['AccountName'][filter_type]:
                    for value in resp[column_name]:
                        filtered_array.append(resp[column_name][value])
            except Exception as e:
                logger.error(f'filtering failed: column_name: {column_name} \
                    not found in {table_name} dynamo table')
                raise e
        logger.debug(f'filtered_array: {filtered_array}')
        return filtered_array
    else:
        array = []
        for resp in response['Items']:
            try:
                if column_name in resp:
                    for value in resp[column_name]:
                        array.append(resp[column_name][value])
            except Exception as e:
                logger.error(f'column_name: {column_name} not found in \
                            {table_name} dynamo table')
                raise e
        logger.debug(f'array: {array}')
        return array
