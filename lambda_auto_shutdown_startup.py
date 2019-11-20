# Shuts down or PowersOn EC2 & RDS instances

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

# CONSTANTS
ROLE_TO_ASSUME = 'CloudLambda'

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
        current_hour = current_hour - 5
        if current_hour < 0:
            current_hour = 24 + current_hour    # + because its a double negative...
        logger.debug(f'current_hour: {current_hour}')
    except Exception as e:
        logger.error(f'Failed retrieving datetime')
        raise e

    # Setup Connections
    session = boto3.Session()
    sts_client = session.client('sts')
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
    for account_id in account_ids:
        # Get credentials for account_id (Turn into a function?)
        try:
            assumed_credentials = sts_client.assume_role(
                RoleArn=('arn:aws:iam::' + account_id + ':role/' + ROLE_TO_ASSUME),
                RoleSessionName='AssumedRole'
            )
            logger.debug(f'assumed_credentials: {assumed_credentials}')
        except Exception as e:
            logger.error(f'Failed getting credentials for {account_id}')
            if job_id:
                response = codepipeline_client.put_job_failure_result(
                    jobId=job_id,
                    failureDetails={
                        'type': 'JobFailed',
                        'message': 'Failed assuming credentials'
                    }
                )
            raise e

        # Setup connection in specified account
        try:
            ec2_client = session.client('ec2',
                aws_access_key_id=assumed_credentials["Credentials"]['AccessKeyId'],
                aws_secret_access_key=assumed_credentials["Credentials"]['SecretAccessKey'],
                aws_session_token=assumed_credentials["Credentials"]['SessionToken'],)
            logger.debug(f'ec2_client: {ec2_client}')
            rds_client = session.client('rds',
                aws_access_key_id=assumed_credentials["Credentials"]['AccessKeyId'],
                aws_secret_access_key=assumed_credentials["Credentials"]['SecretAccessKey'],
                aws_session_token=assumed_credentials["Credentials"]['SessionToken'],)
            logger.debug(f'rds_client: {rds_client}')
        except Exception as e:
            logger.error(f'Failed creating session connection')
            if job_id:
                response = codepipeline_client.put_job_failure_result(
                    jobId=job_id,
                    failureDetails={
                        'type': 'JobFailed',
                        'message': 'Failed creating session connections'
                    }
                )
            raise e

        # EC2 Actions
        try:
            logger.info(f'Starting EC2 actions in {account_id}')
            instances = ec2_client.describe_instances()
            logger.debug(f'instances: {instances}')
            for res in instances['Reservations']:
                for instance in res['Instances']:
                    logger.debug(f'***** instance: {instance}')
                    try:
                        logger.info(f"Checking instance: {instance['InstanceId']}")

                        # Shutdown Action
                        try:
                            if ('pending' in instance['State']['Name'] or
                                    'running' in instance['State']['Name']):
                                shutdown_process_ec2(
                                    ec2_client,
                                    instance,
                                    current_hour)
                        except Exception as e:
                            logger.error(f'Failed shutdown_process_ec2 on {instance}')
                            raise e

                        # Startup Action
                        try:
                            if 'stopped' in instance['State']['Name']:
                                startup_process_ec2(
                                    ec2_client,
                                    instance,
                                    current_hour
                                )
                        except Exception as e:
                            logger.error(f'Failed startup_process_ec2 on {instance}')
                            raise e
                    except Exception as e:
                        logger.error(f'Failed action on {instance}')
                        raise e
        except Exception as e:
            logger.error(f'Failed action in account_id: {account_id}')
            raise e

        # RDS Actions
        try:
            logger.info(f'Starting RDS actions in {account_id}')
            rds_instances = rds_client.describe_db_instances()
            logger.debug(f'rds_instances: {rds_instances}')
            for db_instance in rds_instances['DBInstances']:
                logger.debug(f'db_instance: {db_instance}')

                # Shutdown RDS
                try:
                    shutdown_process_rds(
                        rds_client,
                        db_instance,
                        current_hour
                    )
                except Exception as e:
                    logger.error(f'Failed shutdown_process_rds on: {db_instance["DBInstanceArn"]}')
                    raise e

                # Startup RDS
                try:
                    startup_process_rds(
                        rds_client,
                        db_instance,
                        current_hour
                    )
                except Exception as e:
                    logger.error(f'Failed startup_process_rds on: {db_instance["DBInstanceArn"]}')
                    raise e

        except Exception as e:
            logger.error(f'Failed action in account_id: {account_id}')
            raise e


def shutdown_process_ec2(ec2_client,
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
            logger.info(f'auto_shutdown_time: {auto_shutdown_time}')
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


def shutdown_process_rds(rds_client,
                         db_instance,
                         current_hour):
    """
    Gets the tags for the db_instance and stops it if autoshutdown time equals
    the current time.  This doesn't work on Aurora MySQL and Aurora PostgreSQL.
    :param ec2_client: boto3.client
    :param instance: (dict) instance object
    :param current_hour: (int) current datetime hour
    :return:
    """
    # Get Tags
    rds_tags = rds_client.list_tags_for_resource(
        ResourceName=db_instance['DBInstanceArn']
    )
    logger.debug(f'{db_instance["DBInstanceArn"]} tags: {rds_tags}')

    for tag in rds_tags['TagList']:
        tag_lowered = str(tag['Key']).lower()
        if 'autoshutdown' in tag_lowered:
            auto_shutdown_time = tag.get('Value')
            logger.debug(f'auto_shutdown_time: {auto_shutdown_time}')
            logger.debug(f'current_hour: {current_hour}')
            if auto_shutdown_time == str(current_hour):
                logger.info(f'Shutting down: {db_instance["DBInstanceArn"]}')
                try:
                    response = rds_client.stop_db_instance(
                        DBInstanceIdentifier=db_instance["DBInstanceIdentifier"]
                    )
                    logger.debug(f'response: {response}')
                    response = rds_client.add_tags_to_resource(
                        ResourceName=db_instance['DBInstanceArn'],
                        Tags=[
                            {
                                'Key': 'LastAutomatedShutdownReason',
                                'Value': (str(datetime.utcnow()) + ' - AutoShutdown requested')
                            },
                        ]
                    )
                except Exception as e:
                    logger.info(f'{db_instance["DBInstanceArn"]} already shutdown')


def startup_process_ec2(ec2_client,
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
            logger.info(f'auto_startup_time: {auto_startup_time}')
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


def startup_process_rds(rds_client,
                        db_instance,
                        current_hour):
    """
    Gets the tags for the db_instance and starts it if autostartup time equals
    the current time.  This doesn't work on Aurora MySQL and Aurora PostgreSQL.
    :param rds_client: boto3.client
    :param db_instance: (dict) instance object
    :param current_hour: (int) current datetime hour
    :return:
    """
    # Get Tags
    rds_tags = rds_client.list_tags_for_resource(
        ResourceName=db_instance['DBInstanceArn']
    )
    logger.debug(f'{db_instance["DBInstanceArn"]} tags: {rds_tags}')

    for tag in rds_tags['TagList']:
        tag_lowered = str(tag['Key']).lower()
        if 'autostartup' in tag_lowered:
            auto_startup_time = tag.get('Value')
            logger.debug(f'auto_startup_time: {auto_startup_time}')
            logger.debug(f'current_hour: {current_hour}')
            if auto_startup_time == str(current_hour):
                logger.info(f'Starting: {db_instance["DBInstanceArn"]}')
                try:
                    response = rds_client.start_db_instance(
                        DBInstanceIdentifier=db_instance["DBInstanceIdentifier"]
                    )
                    logger.debug(f'response: {response}')
                    response = rds_client.add_tags_to_resource(
                        ResourceName=db_instance['DBInstanceArn'],
                        Tags=[
                            {
                                'Key': 'LastAutomatedStartup',
                                'Value': (str(datetime.utcnow()))
                            },
                        ]
                    )
                except Exception as e:
                    logger.info(f'{db_instance["DBInstanceArn"]} already started')


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
