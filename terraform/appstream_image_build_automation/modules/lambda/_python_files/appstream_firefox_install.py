import logging
import boto3
import json
import winrm
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Beginning execution of appstream_firefox_install function.")

    # Setup Connections
    try:
        session = boto3.Session()
        secrets_manager = session.client('secretsmanager')
    except Exception as e:
        print(f'Failed setting up connections')
        print(f'e: {e}')
        raise e

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

    # Execute appstream_firefox_install.ps1
    try:
        logger.info(f"Execute appstream_firefox_install.ps1")
        response = winrm_session.run_ps(
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -ExecutionPolicy Bypass -File "
            "c:\\aws_build\\appstream_firefox_install.ps1"
        )
        logger.info(f'response: {response}')
    except Exception as e:
        logger.error(f'e: {e}')
        logger.error(f'Failed Execute appstream_firefox_install.ps1')
        raise e

    # Removes the DummyApp that was required for the creation of the non-domain joined base image.
    # logger.info("Removing DummyApp from image catalog (if present).")
    # command = '"c:\\Program Files\\Amazon\\Photon\\ConsoleImageBuilder\\image-assistant.exe" ' \
    #           'remove-application --name DummyApp'
    # response = winrm_session.run_cmd(command)
    # logger.info(f'response: {response}')

    # # Add Application to AppStream Console
    # # .\image-assistant.exe add-application --name "Wizer_Security_Training" --absolute-app-path "C:\Program Files\Mozilla Firefox\firefox.exe"
    # logger.info(f'Adding Application to image-assistant')
    # command = '"c:\\Program Files\\Amazon\\Photon\\ConsoleImageBuilder\\image-assistant.exe" add-application ' \
    #           '--name "Wizer_Security_Training" ' \
    #           '--display-name "Wizer_Security_Training" ' \
    #           '--absolute-app-path "C:\\Program Files\\Mozilla Firefox\\firefox.exe"'
    # print(f'command: {command}')
    # response = winrm_session.run_cmd(command)
    # logger.info(f'response: {response}')

    logger.info("Completed appstream_firefox_install function, returning to Step Function.")
    return {
        'Method': "Script",
        'Status': "Complete"
    }
