import boto3
import logging
from datetime import datetime


def lambda_handler(event, context):
    # Logging
    logger = logging.getLogger()
    # logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    logger.debug(f'event: {event}')
    logger.debug(f'context: {context}')

    # Setup Connection
    try:
        session = boto3.Session()
        appstream_client = session.client('appstream')
    except Exception as e:
        logger.error(f'Failed creating session')
        logger.error(f'e: {e}')
        raise e

    # Calculate Day of Week and Current Hour
    try:
        day_int, day_string, hour = calculate_day_of_week()
        logger.debug(f'day_int, day_string, hour: {day_int}, {day_string}, {hour}')
        logger.info(f'Today is {day_string}')

        if hour == 0:
            hour = 24
        execute_start = False
        execute_stop = True

        # If Monday, Tuesday, Wednesday, Thursday, or Friday
        if day_int <= 4:

            # If between 6am and 6pm - Start
            if 10 <= hour < 22:
                execute_start = True
                execute_stop = False

        # If Saturday or Sunday - Stop
        elif day_int >= 5:
            execute_start = False
            execute_stop = True

        # Unhandled response returned - Do Nothing
        else:
            logger.error('---> Unhandled response returned - Do Nothing <---')

        logger.debug(f'execute_start: {execute_start}')
        logger.debug(f'execute_stop: {execute_stop}')

    except Exception as e:
        logger.error(f'Failed Calculating Day of Week and Current Hour')
        logger.error(f'e: {e}')
        raise e

    # Get AppStream Fleets
    try:
        fleets = appstream_client.describe_fleets()
        for fleet in fleets['Fleets']:
            fleet_name = fleet['Name']
            fleet_arn = fleet['Arn']

            # Start AppStream Fleets
            try:
                if execute_start:
                    logger.info(f'Starting AppStream Fleet: {fleet_name}')
                    start_fleet(
                        appstream_client,
                        fleet_name,
                        fleet_arn,
                        day_string
                    )
            except Exception as e:
                logger.error(f'Failed Starting AppStream Fleets')
                logger.error(f'e: {e}')

            # Stop AppStream Fleets
            try:
                if execute_stop:
                    logger.info(f'Stopping AppStream Fleet: {fleet_name}')
                    stop_fleet(
                        appstream_client,
                        fleet_name,
                        fleet_arn,
                        day_string
                    )
            except Exception as e:
                logger.error(f'Failed Stopping AppStream Fleets')
                logger.error(f'e: {e}')

    except Exception as e:
        logger.error(f'Failed getting AppStream Fleets')
        logger.error(f'e: {e}')
        raise e


def stop_fleet(
        appstream_client,
        fleet_name,
        fleet_arn,
        day_string
):
    """
    Stops an AppStream Fleet
    :param appstream_client: boto3 client
    :param fleet_name: (String) The name of the Fleet to stop
    :param fleet_arn: (String) The ARN of the Fleet
    :param day_string: (String) The Day the action was taken
    :return: None
    """
    appstream_client.stop_fleet(
        Name=fleet_name
    )
    appstream_client.tag_resource(
        ResourceArn=fleet_arn,
        Tags={
            'LastAutomatedStop': day_string + ' - ' + str(datetime.now()) + ' UTC'
        }
    )


def start_fleet(
        appstream_client,
        fleet_name,
        fleet_arn,
        day_string
):
    """
    Starts an AppStream Fleet
    :param appstream_client: boto3 client
    :param fleet_name: (String) The name of the Fleet to start
    :param fleet_arn: (String) The ARN of the Fleet
    :param day_string: (String) The Day the action was taken
    :return: None
    """
    appstream_client.start_fleet(
        Name=fleet_name
    )
    appstream_client.tag_resource(
        ResourceArn=fleet_arn,
        Tags={
            'LastAutomatedStart': day_string + ' - ' + str(datetime.now()) + ' UTC'
        }
    )


def calculate_day_of_week():
    """
    Calculates the day of the week as an int & string, and the hour of the day as an int.
    :return: (int) day_int, (string) day_string, (int) hour
    """
    day_int = datetime.today().weekday()
    if day_int == 0:
        day_string = 'Monday'
    elif day_int == 1:
        day_string = 'Tuesday'
    elif day_int == 2:
        day_string = 'Wednesday'
    elif day_int == 3:
        day_string = 'Thursday'
    elif day_int == 4:
        day_string = 'Friday'
    elif day_int == 5:
        day_string = 'Saturday'
    elif day_int == 6:
        day_string = 'Sunday'
    else:
        day_string = 'error'
    hour = datetime.now().hour

    return day_int, day_string, hour
