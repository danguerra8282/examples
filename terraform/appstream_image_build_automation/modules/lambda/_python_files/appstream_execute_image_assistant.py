import logging
import boto3
import json
import winrm
import base64
import sys
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Beginning execution of appstream_execute_image_assistant function.")

    # Setup Connections
    try:
        session = boto3.Session()
        app_stream_client = session.client('appstream')
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

    # Image Creation
    try:
        # Retrieve image name from event data
        try:
            image_name = event['AutomationParameters']['ImageOutputPrefix']
            logger.info("Image name prefix found in event data: %s.", image_name)
        except (Exception,):
            image_name = 'Wizer-Image'
            logger.info("No image name prefix found in event data, defaulting to Wizer-Image.")

        # Retrieve use_latest_agent from event data, default to True
        try:
            use_latest_agent = event['AutomationParameters']['use_latest_agent']
            logger.info("use_latest_agent found in event data, setting to %s.", use_latest_agent)
        except (Exception,):
            use_latest_agent = True
            logger.info("use_latest_agent not found in event data, defaulting to True")

        if use_latest_agent:
            latest_agent = ' --use-latest-agent-version'
        else:
            latest_agent = ' --no-use-latest-agent-version'

        # Retrieve image tags from event data
        try:
            image_tags = event['AutomationParameters']['image_tags']
            if image_tags:
                logger.info("Image Tags found in event data: %s.", image_tags)
            else:
                logger.info("No Image Tags found in event data, generated image will not be tagged.")
        except (Exception,):
            image_tags = False
            logger.info("No Image Tags found in event data, generated image will not be tagged.")

        if image_tags:
            tag_image = ' --tags ' + str(image_tags)
        else:
            tag_image = ''

            # Base image assistant command
        prefix = 'C:/PROGRA~1/Amazon/Photon/ConsoleImageBuilder/image-assistant.exe create-image --name '

        # Generate full image name using image name prefix and timestamp
        now = datetime.now()
        dt_string = now.strftime("-%Y-%m-%d-%H-%M-%S")
        full_image_name = image_name + dt_string

        # Final image assistant command
        command = prefix + full_image_name + latest_agent + tag_image

        # Connect to remote image builder using pywinrm library
        logger.info("Connecting to host: %s", host)
        session = winrm.Session(host, auth=(user, password))
        logger.info("Session connection result: %s", session)

        # Run image assistant command to create image
        logger.info("Executing Image Assistant command: %s", command)
        result = session.run_cmd(command)
        logger.info("Results from image assistant command: %s", result.std_out)

        if b"ERROR" in result.std_out:
            logger.info("ERROR running Image Assistant!")
            sys.exit(1)
        else:
            logger.info("Completed execution of Image Assistant command.")

    except Exception as e:
        logger.error(f'Failed Image Creation')
        logger.error(f'e: {e}')
        full_image_name = "Not Found"

    logger.info("Completed appstream_execute_image_assistant function, returning values to Step Function.")
    return {
        "Images": [
            {
                "Name": full_image_name
            }
        ]
    }