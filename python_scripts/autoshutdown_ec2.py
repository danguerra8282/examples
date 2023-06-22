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
        ec2_client = session.client('ec2')
    except Exception as e:
        logger.error(f'Failed creating session')
        logger.error(f'e: {e}')
        raise e

    # Shutdown EC2 Instances
    try:
        instances = ec2_client.describe_instances()
        for res in instances['Reservations']:
            for instance in res['Instances']:
                instance_id = instance['InstanceId']
                instance_tags = instance['Tags']
                try:
                    response = shut_down_instance(
                        ec2_client,
                        instance_id,
                        instance_tags
                    )
                    if response:
                        logger.info(f'Enforcing Stopped State {instance_id}...')
                        tag_ec2(
                            ec2_client,
                            instance_id,
                            "LastAutomatedShutDownReason",
                            "AutoShutDown - " + str(datetime.now()) + ' UTC'
                        )
                except Exception as e:
                    logger.info(f'{instance_id} is already in a Stopped or Stopping state')
                    logger.error(f'e: {e}')
    except Exception as e:
        logger.error(f'Failed describing instances')
        logger.error(f'e: {e}')
        raise e


def shut_down_instance(
        ec2_client,
        instance_id,
        tags
):
    """
    Execute API Stop command to any EC2 Instance with AutoShutDown:True in Tags
    :param ec2_client: boto3.client
    :param instance_id: (String) the instance to check for AutoShutDown tag value
    :param tags: (String) the instance's tags to parse through
    :return: bool
    """
    for tag in tags:
        if "AutoShutDown" in tag['Key']:
            if tag['Value'].lower() == "true":
                ec2_client.stop_instances(
                    InstanceIds=[
                        instance_id
                    ]
                )
                return True


def tag_ec2(
        ec2_client,
        instance_id,
        tag_name,
        tag_value
):
    """
    Added a specified tag to an EC2 instance
    :param ec2_client: boto3.client
    :param instance_id: (String) the EC2 instance to tag
    :param tag_name: (String) the Name for the tag being added
    :param tag_value: (String) the Value for the tag being added
    :return: None
    """
    ec2_client.create_tags(
        Resources=[
            instance_id,
        ],
        Tags=[
            {
                'Key': tag_name,
                'Value': tag_value
            },
        ]
    )
