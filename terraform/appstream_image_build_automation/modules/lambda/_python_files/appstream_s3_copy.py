import logging
import boto3
import json
import os
import winrm
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Beginning execution of appstream_s3_copy function.")

    # Setup Connections
    try:
        session = boto3.Session()
        app_stream_client = session.client('appstream')
        secrets_manager = session.client('secretsmanager')
    except Exception as e:
        print(f'Failed setting up connections')
        print(f'e: {e}')
        raise e

    # Retrieve S3 bucket for sourcefiles from event or environment variable
    logger.info("Querying for S3 bucket containing installation files.")
    if 'PackageS3Bucket' in event['AutomationParameters']:
        s3_bucket = event['AutomationParameters']['PackageS3Bucket']
    else:
        s3_bucket = os.environ['default_s3_bucket'].split('arn:aws:s3:::')[1]
    logger.info("Source S3 bucket found: %s.", s3_bucket)

    # Retrieve image builder IP address from event data
    logger.info("Querying for Image Builder instance IP address.")
    try:
        # host = event['BuilderStatus']['ImageBuilders'][0]['NetworkAccessConfiguration']['EniPrivateIpAddress'] ############################
        host = "172.20.64.174"
        logger.info("IP address found: %s.", host)
    except Exception as e:
        logger.error(e)
        logger.info("Unable to find IP address for Image Builder instance.")
        raise e

    # Get image builder administrator username and password from Secrets Manager
    try:
        logger.info("Get image builder administrator username and password from Secrets Manager.")
        secret_name = "appstream_image_builder_admin"
        secret_response = secrets_manager.get_secret_value(SecretId=secret_name)

        if 'SecretString' in secret_response:
            secret = json.loads(secret_response['SecretString'])
        else:
            secret = base64.b64decode(secret_response['SecretBinary'])

        user = secret['username']
        password = secret['password']
        logger.info("Remote access credentials obtained: %s", user)
    except Exception as e:
        logger.error("Error getting credentials from Secrets Manager")
        logger.error(e)
        raise e

    # Connect to remote image builder using pywinrm library
    try:
        logger.info("Connecting to host: %s", host)
        winrm_session = winrm.Session(host, auth=(user, password))
    except Exception as e:
        logger.error(e)
        logger.info("Unable to remotely connect to the Image Builder instance.")
        raise e

    # Copy s3 contents to local machine
    try:
        logger.info(f'Copy s3 contents to local machine')
        prefix = "Read-S3Object -BucketName "
        suffix = " -KeyPrefix * -Folder " \
                 "c:\\aws_build -ProfileName appstream_machine_role"
        command = prefix + s3_bucket + suffix
        logger.info(f'command: {command}')
        response = winrm_session.run_ps(command)
        logger.info(f'response: {response}')
    except Exception as e2:
        logger.error(f'e: {e2}')
        logger.error(f'Copy s3 contents to local machine')
        raise e2

    logger.info("Completed appstream_s3_copy function, returning to Step Function.")
    return {
        'Method': "Script",
        'Status': "Complete"
    }
