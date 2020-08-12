# Custom Resource Example; will returned a specific Security Group's arn based on the Security Group name passed to it

# Import Modules
import boto3
import logging
import json
import datetime
from datetime import datetime
import cfnresponse  # <--- Required for custom_resource
import time


def lambda_handler(event, context):
    # Logging
    logger = logging.getLogger()
    # logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    session = boto3.Session()
    ec2_client = session.client('ec2')

    logger.debug(f'event: {event}')  # <--- Input from CloudFormation
    security_group = event['ResourceProperties']['SecurityGroup']
    logger.debug(f'context: {context}')
    security_group_found = 'none'
    response_data = ''

    if 'Create' in event['RequestType']:
        try:
            logger.info(f'Searching for Security Group: {security_group}')
            security_groups = ec2_client.describe_security_groups(
                Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': ['vpc-123xyz']
                    },
                ],
            )

            for sg in security_groups['SecurityGroups']:
                if security_group in sg['GroupName']:
                    security_group_found = sg['GroupId']
                    logger.info(f"SecurityGroupId found: {security_group_found}")

            # logger.info(f'Security Group ARN: {response}')

        except Exception as e:
            logger.error(f'Failure while searching for Security Group {security_group}')
            logger.error(f'e: {e}')
            cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
            raise e
    else:
        security_group_found = 'none'

    # Send Signal   <--- Send Signal back to CloudFormation saying the custom_resource is complete.
    # REQUIRED or the cloudformation will never complete
    response_data = dict()
    response_data['security_group_found'] = security_group_found
    logger.debug(f'response_data: {response_data}')

    cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, "CustomResourcePhysicalID")
