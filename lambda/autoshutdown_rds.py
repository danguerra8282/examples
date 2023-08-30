import boto3
import logging
from datetime import datetime


def lambda_handler(event, context):
    # Logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # logger.setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    logger.debug(f'event: {event}')
    logger.debug(f'context: {context}')

    # Setup Connection
    try:
        session = boto3.Session()
        rds_client = session.client('rds')
    except Exception as e:
        logger.error(f'Failed creating session')
        logger.error(f'e: {e}')
        raise e

    # Get RDS Instances
    try:
        rds_instances = rds_client.describe_db_instances()
        for rds_instance in rds_instances['DBInstances']:
            instance_identifier = rds_instance['DBInstanceIdentifier']
            instance_arn = rds_instance['DBInstanceArn']
            power_state = rds_instance['DBInstanceStatus']
            tag_list = rds_instance['TagList']
            logger.debug(f'instance_identifier: {instance_identifier}')
            logger.debug(f'instance_arn: {instance_arn}')
            logger.debug(f'power_state: {power_state}')
            logger.debug(f'tag_list: {tag_list}')
            logger.info(f'Instance: {instance_identifier} is currently {power_state}')

            # Process AutoShutDown
            try:
                if power_state == 'available':
                    response = shut_down_rds(
                        rds_client,
                        instance_identifier,
                        tag_list
                    )
                else:
                    response = False
            except Exception as e:
                logger.error(f'Failed Processing AutoShutDown')
                logger.error(f'e: {e}')
                raise e

            # Tag Instance
            try:
                if response:
                    tag_instance(
                        rds_client,
                        instance_arn,
                        "LastAutomatedShutDownReason",
                        "AutoShutDown - " + str(datetime.now()) + ' UTC'
                    )
            except Exception as e:
                logger.error(f'Failed Tagging Instance')
                logger.error(f'e: {e}')
                raise e

    except Exception as e:
        logger.error(f'Failed Getting RDS Instances')
        logger.error(f'e: {e}')
        raise e


def tag_instance(
        rds_client,
        instance_arn,
        tag_name,
        tag_value
):
    """
    Added a specified tag to a RDS instance
    :param rds_client: boto3.client
    :param instance_arn: (String) the RDS instance arn to tag
    :param tag_name: (String) the Name for the tag being added
    :param tag_value: (String) the Value for the tag being added
    :return: None
    """
    rds_client.add_tags_to_resource(
        ResourceName=instance_arn,
        Tags=[
            {
                'Key': tag_name,
                'Value': tag_value
            },
        ]
    )


def shut_down_rds(
        rds_client,
        instance_identifier,
        tag_list
):
    """
    Executes API stop command against a RDS instance with AutoShutDown:True in Tags
    :param rds_client: boto3.client
    :param instance_identifier: (String) RDS Instance Identifier
    :param tag_list: (Array) RDS Instance Tags
    :return: bool
    """
    # Parse Tags
    for tag in tag_list:
        if tag['Key'] == "AutoShutDown":
            if tag['Value'].lower() == 'true':
                logging.info(f'Enforcing Stopped State on {instance_identifier}')

                # Shutdown instance
                response = rds_client.stop_db_instance(
                    DBInstanceIdentifier=instance_identifier
                )
                logging.info(f"{instance_identifier} is now in the following state: "
                             f"{response['DBInstance']['DBInstanceStatus']}")
                return True
    logging.info(f'Instance: {instance_identifier} is not set for AutoShutDown')
    return False
