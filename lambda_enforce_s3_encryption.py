# Deploys enforce_s3_encryption
# Triggers off of CloudWatch event
# This requires a Lambda role that has the following permissions:
#   - S3
#   - KMS

# Import Modules
import boto3
import logging
import datetime
from datetime import datetime
import json

# Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)
logging.getLogger("botocore").setLevel(logging.ERROR)


# MAIN #
def lambda_handler(_event, _context):
    logger.info(f'Starting Enforce_S3_Encryption')
    logger.debug(f'_event: {_event}')
    bucket_name = _event['detail']['requestParameters']['bucketName']
    logger.info(f'Checking bucket_name: {bucket_name}')

    # Setup Connections
    session = boto3.Session()
    s3_client = session.client('s3')
    kms_client = session.client('kms')

    # Check Bucket Encryption
    try:
        response = s3_client.get_bucket_encryption(Bucket=bucket_name)
        logger.debug(f'response: {response}')
        logger.info(f'Encryption already set on {bucket_name}')
    except Exception as e:
        logger.info(f'Encryption not set on {bucket_name}')
        response = False

    if not response:
        # Get aws/s3 key for the account
        logger.info(f'Getting default encryption KMS key...')
        try:
            kms_list = kms_client.list_aliases()
            for key in kms_list['Aliases']:
                if 'alias/aws/s3' in key['AliasName']:
                    s3_key = key['TargetKeyId']
                    logger.debug(f's3_key: {s3_key}')
        except Exception as e:
            logger.error(f'Failed to find aws/s3 key for this account')

        # Set default encryption
        try:
            logger.info(f'Setting default encryption...')
            response = s3_client.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'aws:kms',
                                'KMSMasterKeyID': s3_key
                            }
                        },
                    ]
                }
            )
            logger.info(f'Default encryption has been set on {bucket_name}')
        except Exception as e:
            logger.error(f'Failed setting default encryption on {bucket_name}')
