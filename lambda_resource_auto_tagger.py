# Tags a resource with information from the user that executed the creation

# Import Modules
import boto3
import logging
import datetime
from datetime import datetime

# Logging
logger = logging.getLogger()
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)
logging.getLogger("botocore").setLevel(logging.ERROR)

####### MAIN #######
def lambda_handler(_event, _context):
    logger.info(f'Starting Resource Auto Tagger')
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
    sts_client = session.client('sts')
    iam_client = session.client('iam')


    # Tagging for EC2
    try:
        if "aws.ec2" in event_source_type:
            logger.debug(f'--- Execute EC2 Tagging ---')
            response = ec2_tagging(_event, 
                                   ec2_client, 
                                   sts_client,
                                   iam_client)
            logger.debug(f'response: {response}')
    except Exception as e:
        logger.error(f'Failed action during Tagging for EC2')
        raise e


def ec2_tagging(_event, 
                ec2_client, 
                sts_client,
                iam_client):
    """
    Executes tagging requirements for EC2 instances
    :param _event: dict
    :ec2_client: boto3.client
    :sts_client: boto3.client
    :iam_client: boto3.client
    :return: string
    """

    # Get instanceIds from _event
    try:
        instance_ids = _event['detail']['requestParameters']['instancesSet']['items']
        if instance_ids:
            logger.debug(f'instance_ids array: {instance_ids}')
            instance_id_array = []
            for instance_id in instance_ids:
                instance_id = instance_id['instanceId']
                logger.debug(f'instance_id: {instance_id}')
                instance_id_array.append(instance_id)
                logger.info(f'instance_id_array: {instance_id_array}')

            # Check and assign tags for EC2
            for instance_id in instance_id_array:
                try:
                    response = ec2_client.describe_instances(InstanceIds=[instance_id])
                    logger.debug(f'response: {response}')
                    for res in response['Reservations']:
                        for instance in res['Instances']:
                            # Assign Local Variables
                            assign_owner_tag = True
                            assign_environment_tag = True
                            assign_account_id_tag = True

                            tags = instance['Tags']
                            logger.debug(f'tags: {tags}')
                            for tag in tags:
                                tag = str(tag).lower()
                                if 'owner' in tag:
                                    assign_owner_tag = False
                                    logger.info(f'Owner tag already populated')
                                if 'environment' in tag:
                                    assign_environment_tag = False
                                    logger.info(f'Environment tag already populated')
                                if 'accountid' in tag:
                                    assign_account_id_tag = False
                                    logger.info(f'AccountId tag already populated')
                                    
                            # Assign Owner tag if necessary
                            if assign_owner_tag:
                                response, user_identity = assign_owner(_event, 
                                                                       instance_id, 
                                                                       ec2_client)
                                if response:
                                    logger.info(f'Assigned Owner: {user_identity} to {instance_id}')
                                else:
                                    logger.error(f'Failed assigning owner to: {instance_id}')

                            # Assign Environment tag if necessary
                            if assign_environment_tag:
                                response, environment_name = assign_environment(iam_client, 
                                                                                ec2_client, 
                                                                                instance_id)
                                if response:
                                    logger.info(f'Assigned Environment: {environment_name} to {instance_id}')
                                else:
                                    logger.error(f'Failed assigning environment to {instance_id}')

                            # Assign AccountId tag if necessary
                            if assign_account_id_tag:
                                response, account_id = assign_account_id(sts_client, 
                                                                         ec2_client, 
                                                                         instance_id)
                                if response:
                                    logger.info(f'Assigned AccountId: {account_id} to {instance_id}')
                                else:
                                    logger.error(f'Failed assigning AccountId to {instance_id}')

                except Exception as e:
                    logger.error(f'Failed while trying to tag EC2 instance: {instance_id}')
        
        else:
            logger.debug(f'No instance_id found')

    except Exception as e:
        instance_ids = None
        logger.debug(f'No instance_id found')

    return None # Added Last, changed from return user_identity


def assign_owner(_event, 
                 instance_id, 
                 connection_client):
    """
    Executes tagging for Owner on instances
    :param _event: dict
    :param instance_id: string
    :param connection_client: boto3.client for AWS specific resource
    :return: boolean
    """

    try:
        user_identity = _event['detail']['userIdentity']['principalId']
        if user_identity:
            user_identity = user_identity.split(':', 1)[1]
            logger.debug(f'user_identity: {user_identity}')
            connection_client.create_tags(Resources=[instance_id],
                            Tags=[{'Key':'Owner', 
                                    'Value':user_identity
                                }]
                            )
            return True, user_identity
    except Exception as e:
        user_identity = None
        logger.debug(f'No user_identity found')
        return False

def assign_environment(iam_client, 
                       connection_client, 
                       instance_id):
    """
    Executes tagging for Environment on instances
    :param iam_client: boto3.client(IAM)
    :param connection_client: boto3.client for AWS specific resource
    :param instance_id: string
    :return: boolean
    """

    try:
        environment_name = iam_client.list_account_aliases()['AccountAliases'][0]
        logger.debug(f'environment_name: {environment_name}')
        connection_client.create_tags(Resources=[instance_id],
                                Tags=[{'Key':'Environment', 
                                        'Value':environment_name
                                    }]
                                )
        return True, environment_name
    except Exception as e:
        logger.debug(f'No environment found')
        return False

def assign_account_id(sts_client, 
                      connection_client, 
                      instance_id):
    """
    Executes tagging for AccountId on instances
    :param sts_client: boto3.client(STS)
    :param connection_client: boto3.client for AWS specific resource
    :param instance_id: string
    :return: boolean
    """

    try:
        account_id = sts_client.get_caller_identity()["Account"]
        logger.debug(f'account_id: {account_id}')
        connection_client.create_tags(Resources=[instance_id],
                                Tags=[{'Key':'AccountId', 
                                        'Value':account_id
                                    }]
                                )
        return True, account_id
    except Exception as e:
        logger.debug(f'No account_id found')
        return False
