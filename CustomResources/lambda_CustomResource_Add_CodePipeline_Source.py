# Custom Resource; will copy codepipeline source to an s3 bucket

# Import Modules
import boto3
import logging
import json
import datetime
from datetime import datetime
import cfnresponse
import time


def lambda_handler(event, context):
    # Logging
    logger = logging.getLogger()
    # logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    session = boto3.Session()
    s3_client = session.client('s3')

    logger.debug(f'event: {event}')
    logger.debug(f'context: {context}')

    if 'Create' in event['RequestType']:
        # Ensure destination bucket exists
        try:
            # key = '_Deploy_New_CodePipeline.yml'
            key = 'deploy.zip'
            copy_destination = event['ResourceProperties']['SourceBucket']
            logger.debug(f'copy_destination: {copy_destination}')

            continue_running = True
            while continue_running:
                try:
                    time.sleep(5)
                    response = s3_client.head_bucket(
                        Bucket=copy_destination
                    )
                    print(f'response: {response}')
                    print(f'response: {response["ResponseMetadata"]["HTTPStatusCode"]}')
                    if "200" in str(response["ResponseMetadata"]["HTTPStatusCode"]):
                        continue_running = False
                except:
                    logger.debug(f'Waiting for bucket {copy_destination} to be created')

        except Exception as e:
            logger.error(f'Something happened attempting to verify the bucket exists.  It probably failed to create...')
            raise e

        # Copy pipeline.yaml to target bucket
        try:
            copy_source = {
                'Bucket': 's304618-s3-test',
                'Key': key
            }
            s3_client.copy(copy_source, copy_destination, key)
        except Exception as e:
            print("Caught an exception")

    # Send Signal
    response_data = dict()
    response_data['SUCCESS'] = "SUCCESS - This worked"
    logger.debug(f'response_data: {response_data}')

    cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, "CustomResourcePhysicalID")
