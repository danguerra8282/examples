# Enables KMS Key Rotation if not already set on any modified KMS Key

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


# MAIN #
def lambda_handler(_event, _context):
    logger.info(f'Starting KMS Key Rotation')
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
    kms_client = session.client('kms')

    # Get keyId from _event
    try:
        if 'CreateKey' in _event['detail']['eventName']:
            key_id = _event['detail']['responseElements']['keyMetadata']['keyId']

        # Enable Key Rotation
        try:
            if key_id:
                response = kms_client.enable_key_rotation(KeyId=key_id)
                logger.debug(f'response" {response}')
                logger.info(f'Key Rotation Enabled on key_id: {key_id}')
        except Exception as e:
            logger.error(f'Failed setting KMS Key rotation on key_id: \
                {key_id}')
    except Exception as e:
        logger.info('No key_id found in the _event')
