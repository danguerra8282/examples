import logging
import boto3
import datetime
from datetime import datetime

######### LOGGING ###############
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger("botocore").setLevel(logging.ERROR)


#########  MAIN  ###############
def lambda_handler(event, _context):
    #  Get Current DateTime
    utcDateTime = datetime.utcnow()
    logger.debug(f'utcDateTime: {utcDateTime}')

    #  Get all EC2 instances
    session = boto3.Session()
    ec2Client = session.client('ec2', region_name='us-east-1')

    try:
        logger.debug(f'Describing All Instances...')
        allInstances = ec2Client.describe_instances()
        # logger.debug(f'allInstances: {allInstances}')
    except Exception as e:
        logger.error(f'Failed to describe_instances')
        raise e

    #  Check each EC2 instance and take action for Shutdowns
    logger.info('### Checking for ShutDown Tags ###')
    for instances in allInstances['Reservations']:
        for instance in instances['Instances']:
            try:
                if instance['InstanceId'] == 'i-0de01bff49c78f2ee':
                    instanceId = instance['InstanceId']

                    for tag in instance['Tags']:
                        #  Check AutoShutDown8pm Tag Value (Old way)
                        if 'AutoShutDown8pm' in (tag.get('Key')):
                            autoShutDownValue = (tag.get('Value'))

                            logger.info(f'AutoShutDown8pm Tag found on: {instanceId}')
                            #  Shutdown if AutoShutDown == EST (currentTime +4)
                            if 'EST' in autoShutDownValue and utcDateTime.hour == 00:
                                logger.info(f'Shutting down instance: {instanceId}')
                                ec2Client.stop_instances(InstanceIds=[instanceId])
                                ec2Client.create_tags(Resources=[instanceId], Tags=[{'Key': 'LastAutomatedShutdown',
                                     'Value': str(
                                         utcDateTime) + ' - The server was requested to be shutdown at 8pm EST'}])
                            #  Shutdown if AutoShutDown == EST (currentTime +5)
                            elif 'CST' in autoShutDownValue and utcDateTime.hour == 1:
                                logger.info(f'Shutting down instance: {instanceId}')
                                ec2Client.stop_instances(InstanceIds=[instanceId])
                                ec2Client.create_tags(Resources=[instanceId], Tags=[{'Key': 'LastAutomatedShutdown',
                                     'Value': str(
                                         utcDateTime) + ' - The server was requested to be shutdown at 8pm CST'}])
                            #  Shutdown if AutoShutDown == EST (currentTime +6)
                            elif 'MST' in autoShutDownValue and utcDateTime.hour == 2:
                                logger.info(f'Shutting down instance: {instanceId}')
                                ec2Client.stop_instances(InstanceIds=[instanceId])
                                ec2Client.create_tags(Resources=[instanceId], Tags=[{'Key': 'LastAutomatedShutdown',
                                     'Value': str(
                                         utcDateTime) + ' - The server was requested to be shutdown at 8pm MST'}])
                            #  Shutdown if AutoShutDown == EST (currentTime +7)
                            elif 'PST' in autoShutDownValue and utcDateTime.hour == 3:
                                logger.info(f'Shutting down instance: {instanceId}')
                                ec2Client.stop_instances(InstanceIds=[instanceId])
                                ec2Client.create_tags(Resources=[instanceId], Tags=[{'Key': 'LastAutomatedShutdown',
                                     'Value': str(
                                         utcDateTime) + ' - The server was requested to be shutdown at 8pm PST'}])
                            else:
                                logger.info(f'No Shutdown Action take on: {instanceId}')

                            #  Delete Variable
                            del autoShutDownValue

                        #  Check ShutDownInstanceAt Tag Value (New way)
                        if 'ShutDownInstanceAt' in (tag.get('Key')):
                            logger.info(f'ShutDownInstanceAt Tag found on: {instanceId}')
                            ShutDownInstanceAtValue = (tag.get('Value'))
                            logger.debug(f'ShutDownInstanceAtValue: {ShutDownInstanceAtValue}')
                            shutDownInstanceAtHour = ShutDownInstanceAtValue.split(' ')[0]
                            logger.debug(f'shutDownInstanceAtHour: {shutDownInstanceAtHour}')

                            if 'pm' in shutDownInstanceAtHour:
                                shutDownInstanceAtHour = (int(shutDownInstanceAtHour.split('pm')[0]) + 12)
                                logger.debug(f'shutDownInstanceAtHour: {shutDownInstanceAtHour}')

                            elif 'am' in shutDownInstanceAtHour:
                                shutDownInstanceAtHour = int(shutDownInstanceAtHour.split('am')[0])
                                logger.debug(f'shutDownInstanceAtHour: {shutDownInstanceAtHour}')

                            logger.debug(f'utcDateTime.hour: {utcDateTime.hour}')
                            #  Shutdown instance if the current UTC hour == the shutDownInstanceHour
                            if shutDownInstanceAtHour == utcDateTime.hour:
                                logger.info(f'Shutting down instance: {instanceId}')
                                ec2Client.stop_instances(InstanceIds=[instanceId])
                                ec2Client.create_tags(Resources=[instanceId], Tags=[{'Key': 'LastAutomatedShutdown',
                                     'Value': str(utcDateTime) + ' - The server was requested to be shutdown at ' +
                                              ShutDownInstanceAtValue}])
                            else:
                                logger.info(f'No Shutdown Action take on: {instanceId}')

                            #  Delete Variable
                            del ShutDownInstanceAtValue

            except Exception as e:
                logger.error(f'Failed executing Shutdown actions')
                raise e

    #  Check each EC2 instance and take action for PowerOn
    logger.info('### Checking for PowerOn Tags ###')
    for instances in allInstances['Reservations']:
        for instance in instances['Instances']:
            try:
                if instance['InstanceId'] == 'i-0de01bff49c78f2ee':
                    instanceId = instance['InstanceId']

                    for tag in instance['Tags']:
                        #  Check PowerOnInstanceAt Tag Value
                        if 'PowerOnInstanceAt' in (tag.get('Key')):
                            logger.info(f'PowerOnInstanceAt Tag found on: {instanceId}')
                            PowerOnInstanceAtValue = (tag.get('Value'))
                            logger.debug(f'PowerOnInstanceAtValue: {PowerOnInstanceAtValue}')
                            PowerOnInstanceAtHour = PowerOnInstanceAtValue.split(' ')[0]
                            logger.debug(f'PowerOnInstanceAtHour: {PowerOnInstanceAtHour}')

                            if 'pm' in PowerOnInstanceAtHour:
                                PowerOnInstanceAtHour = (int(PowerOnInstanceAtHour.split('pm')[0]) + 12)
                                logger.debug(f'PowerOnInstanceAtHour: {PowerOnInstanceAtHour}')

                            elif 'am' in PowerOnInstanceAtHour:
                                PowerOnInstanceAtHour = int(PowerOnInstanceAtHour.split('am')[0])
                                logger.debug(f'PowerOnInstanceAtHour: {PowerOnInstanceAtHour}')

                            logger.debug(f'utcDateTime.hour: {utcDateTime.hour}')
                            #  PowerOn instance if the current UTC hour == the PowerOnInstanceAtHour
                            if PowerOnInstanceAtHour == utcDateTime.hour:
                                logger.info(f'Powering on instance: {instanceId}')
                                response = ec2Client.start_instances(InstanceIds=[instanceId])
                                logger.debug(f'response: {response}')
                                ec2Client.create_tags(Resources=[instanceId], Tags=[{'Key': 'LastAutomatedPowerOn',
                                     'Value': str(utcDateTime) + ' - The server was requested to be powered on at ' +
                                              PowerOnInstanceAtValue}])
                            else:
                                logger.info(f'No PowerOn Action take on: {instanceId}')

                            #  Delete Variable
                            del PowerOnInstanceAtValue

            except Exception as e:
                logger.error(f'Failed executing PowerOn actions')
                raise e
