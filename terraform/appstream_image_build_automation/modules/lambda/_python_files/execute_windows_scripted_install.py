import logging
import boto3
import json
import os
import winrm
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Setup Connections
try:
    session = boto3.Session()
    app_stream_client = session.client('appstream')
    secrets_manager = session.client('secretsmanager')
except Exception as e:
    print(f'Failed setting up connections')
    print(f'e: {e}')
    raise e

def lambda_handler(event, context):
    logger.info("Beginning execution of execute_windows_scripted_install function.")

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
        host = "172.20.64.217"
        logger.info("IP address found: %s.", host)
    except Exception as e2:
        logger.error(e2)
        logger.info("Unable to find IP address for Image Builder instance.")
        raise e2

    try:
        # Read image builder administrator username and password from Secrets Manager
        logger.info("Retreiving instance username and password from Secrets Manager.")
        secret_name = "appstream_image_builder_admin"
        secret_response = secrets_manager.get_secret_value(SecretId=secret_name)

        if 'SecretString' in secret_response:
            secret = json.loads(secret_response['SecretString'])
        else:
            secret = base64.b64decode(secret_response['SecretBinary'])

        user = secret['username']
        password = secret['password']
        logger.info("Remote access credentials obtained: %s", user)
    except Exception as e2:
        logger.error("Error getting credentials from Secrets Manager")
        logger.error(e2)
        raise e2

    # Connect to remote image builder using pywinrm library
    try:
        logger.info("Connecting to host: %s", host)
        winrm_session = winrm.Session(host, auth=(user, password))
    except Exception as e2:
        logger.error(e2)
        logger.info("Unable to remotely connect to the Image Builder instance.")
        raise e2

    # Copy appstream_image_configuration.ps1 from s3 to local machine
    try:
        logger.info(f'Copy appstream_image_configuration.ps1 from s3 to local machine')
        prefix = "Read-S3Object -BucketName "
        suffix = " -Key appstream_image_configuration.ps1 -File " \
                 "c:\\aws_build\\appstream_image_configuration.ps1 -ProfileName appstream_machine_role"
        command = prefix + s3_bucket + suffix
        logger.info(f'command: {command}')
        response = winrm_session.run_ps(command)
        logger.info(f'response: {response}')
    except Exception as e2:
        logger.error(f'e: {e2}')
        logger.error(f'Failed Copy appstream_image_configuration.ps1 from s3 to local machine')
        raise e2

    # Execute appstream_image_configuration.ps1
    try:
        logger.info(f"Execute appstream_image_configuration.ps1")
        response = winrm_session.run_ps(
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -ExecutionPolicy Bypass -File "
            "c:\\aws_build\\appstream_image_configuration.ps1"
        )
        logger.info(f'response: {response}')
    except Exception as e2:
        logger.error(f'e: {e2}')
        logger.error(f'Failed Execute appstream_image_configuration.ps1')
        raise e2

    # # Removes the DummyApp that was required for the creation of the non-domain joined base image.
    # logger.info("Removing DummyApp from image catalog (if present).")
    # # command = '"c:\\Program Files\\Amazon\\Photon\\ConsoleImageBuilder\\image-assistant.exe" remove-application --name DummyApp'
    # # response = winrm_session.run_cmd(command)
    # response = winrm_session.run_ps("New-Item -Path c:\\ -Name \"lambda_made_this\" -ItemType \"directory\" -force")
    # logger.info(f'response: {response}')

    # # Copy files from s3
    # try:
    #     prefix = "Read-S3Object -BucketName "
    #     suffix = " -KeyPrefix NotepadPP -Folder c:\\temp\\NotepadPP -ProfileName appstream_machine_role"
    #     command = prefix + s3_bucket + suffix
    #     response = winrm_session.run_ps(command)
    #     logger.info(f'copy files from s3 response: {response}')
    # except Exception as e:
    #     logger.error(f'Failed copy files from s3')
    #     logger.error(f'e: {e}')

    logger.info("Completed execute_windows_scripted_install function, returning to Step Function.")
    return {
        'Method': "Script",
        'Status': "Complete"
    }
