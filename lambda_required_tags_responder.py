# Shuts down an EC2 instance if required tags are missing
# REQUIRED_TAGS are defined in the validate_tags function

# Import Modules
import boto3
import logging
import datetime
from datetime import datetime

# Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)
logging.getLogger("botocore").setLevel(logging.ERROR)


# MAIN
def lambda_handler(_event, _context):
    logger.info(f'Starting Required Tags Responder')
    logger.debug(f'_event: {_event}')

    # Get Cloudwatch event source_type
    event_source_type = _event['source']
    logger.debug(f'event_source_type: {event_source_type}')

    # Get datetime
    try:
        utc_date_time = datetime.utcnow()
        logger.info(f'utc_date_time: {utc_date_time}')
    except Exception as e:
        logger.error(f'Failed retrieving datetime')
        raise e

    # Setup Connections
    session = boto3.Session()
    ec2_client = session.client('ec2')

    try:
        instance_ids = _event['resources']
        logger.debug(f'instance_ids: {instance_ids}')

        for instance_id in instance_ids:
            instance_id = instance_id.split('/')[1]
            logger.debug(f'instance_id: {instance_id}')
            response = get_ec2_tags(ec2_client,
                                    instance_id,
                                    )
            response = validate_tags(response)
            logger.info(f'response: {response} tags are missing on {instance_id}')
            if response:
                response = shutdown_and_tag_ec2_instance(ec2_client,
                                                         instance_id,
                                                         response
                                                         )

    except Exception as e:
        logger.error(f'Failed action during Required Tags Responder')
        raise e


def get_ec2_tags(ec2_client,
                 instance_id):
    """
    Gets and returns the tags on an EC2 instance
    :param instance_id: string
    :param ec2_client: boto3.client
    return: dict
    """
    try:
        logger.debug(f'instance_id: {instance_id}')
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        logger.debug(f'response: {response}')
        for res in response['Reservations']:
            for instance in res['Instances']:
                tags = instance['Tags']
                logger.debug(f'tags: {tags}')
        return tags
    except Exception as e:
        logger.error(f'Failed to get tags from instance')
        raise e


def validate_tags(object_tags):
    """
    Gets and returns the tags on an EC2 instance
    :param required_tags: array
    :param object_tags: array
    return: array
    """

    # CONSTANTS
    REQUIRED_TAGS = ['Name',
                     'Team',
                     'BusinessUnit']

    try:
        present_tags_array = []
        required_tags_missing = REQUIRED_TAGS
        logger.debug(f'In function required_tags: {REQUIRED_TAGS}')
        logger.debug(f'In function object_tags: {object_tags}')
        for required_tag in REQUIRED_TAGS:
            required_tag_present = False
            logger.info(f'Checking for required_tag: {required_tag}')
            for tag in object_tags:
                logger.debug(f'tag: {tag}')
                if required_tag in tag['Key']:
                    if tag['Value']:
                        required_tag_present = True
                        present_tags_array.append(required_tag)
        logger.debug(f'present_tags_array: {present_tags_array}')
        for item in present_tags_array:
            if item in REQUIRED_TAGS:
                required_tags_missing.remove(item)
        return required_tags_missing
    except Exception as e:
        logger.error(f'Failed validating tags')
        raise e


def shutdown_and_tag_ec2_instance(ec2_client,
                                  instance_id,
                                  tag):
    """
    Shuts down and tag an EC2 instance
    :param ec2_client: boto3 client
    :param instance_id: string
    :param tag: array
    return: string
    """
    logger.info(f'Shutting down EC2 instance {instance_id}')
    ec2_client.stop_instances(InstanceIds=[instance_id])
    logger.info(f'Tagging EC2 instance {instance_id} with shutdown reason')
    ec2_client.create_tags(Resources=[instance_id],
                           Tags=[{
                               'Key': 'LastAutomatedShutdownReason',
                               'Value': (str(datetime.utcnow()) + ' - Missing tags: ' + str(tag))
                                }]
                           )
    return True
