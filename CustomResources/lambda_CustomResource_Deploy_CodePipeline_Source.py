# Custom Resource; will modify and deploy the codepipeline source in an s3 bucket

# Import Modules
import boto3
import logging
import json
import datetime
from datetime import datetime
import cfnresponse
import time
import zipfile
import os


def lambda_handler(event, context):
    # Logging
    logger = logging.getLogger()
    # logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    session = boto3.Session()
    s3_client = session.client('s3')
    cloudformation_client = session.client('cloudformation')

    logger.debug(f'event: {event}')
    logger.debug(f'context: {context}')
    product_name = event['ResourceProperties']['ProductName']
    logger.debug(f'product_name: {product_name}')

    if 'Create' in event['RequestType']:
        # Ensure bucket exists
        try:
            key = 'deploy.zip'
            source_bucket = event['ResourceProperties']['SourceBucket']
            logger.debug(f'source_bucket: {source_bucket}')

            response = s3_client.head_bucket(
                Bucket=source_bucket
            )
            print(f'response: {response}')
            print(f'response: {response["ResponseMetadata"]["HTTPStatusCode"]}')
        except Exception as e:
            logger.error(f'Something happened attempting to verify the bucket exists.  It probably failed to create...')
            raise e

        # Download deploy.zip to local container
        try:
            logger.info(f'Downloading {key} from {source_bucket}')
            downloaded_file = s3_client.download_file(
                    source_bucket,
                    key,
                    '/tmp/deploy.zip'
            )
        except Exception as e:
            logger.error(f'Failed downloading {key} from {source_bucket}')
            logger.error(e)
            raise e

        # Unzip local deploy.zip
        try:
            logger.info(f'Unzipping /tmp/deploy.zip')
            with zipfile.ZipFile('/tmp/deploy.zip', 'r') as zip_ref:
                zip_ref.extractall('/tmp/')
        except Exception as e:
            logger.error(f'Failed unzipping deploy.zip')
            logger.error(e)
            raise e

        # Update CodePipeline.json with info passed in
        try:
            logger.info(f'Updating CodePipeline.json')
            contents = open('/tmp/iac/CodePipeline.json', 'r').read()
            logger.debug(f'before contents: {contents}')

            # file = open('/tmp/iac/CodePipeline.json', 'r')
            # file_data = file.read()
            # file.close()
            # new_data = file_data.replace('"temporary_value"', '"' + product_name + '"')
            # file = open('/tmp/iac/CodePipeline.json', 'w')
            # file.write(new_data)
            # file.close()

            update_file(
                '/tmp/iac/CodePipeline.json',
                '"temporary_value"',
                '"' + product_name + '"'
            )

            contents = open('/tmp/iac/CodePipeline.json', 'r').read()
            logger.debug(f'after contents: {contents}')
        except Exception as e:
            logger.error(f'Failed updating CodePipeline.json')
            logger.error(e)
            raise e

        # Zip up files
        try:
            logger.info(f'Zipping up files')
            directory_contents = os.listdir('/tmp/')
            logger.debug(f'directory_contents before: {directory_contents}')
            os.remove('/tmp/deploy.zip')
            directory_contents = os.listdir('/tmp/')
            logger.debug(f'directory_contents during: {directory_contents}')
            zip_ref = zipfile.ZipFile('/tmp/deploy.zip', 'w')
            for dirname, subdirs, files in os.walk('/tmp/iac/'):
                zip_ref.write(dirname)
                for filename in files:
                    zip_ref.write(os.path.join(dirname, filename))
            zip_ref.close()
            directory_contents = os.listdir('/tmp/')
            logger.debug(f'directory_contents after: {directory_contents}')
        except Exception as e:
            logger.error(f'Failed zipping files')
            logger.error(e)
            raise e

        # Push deploy.zip back to the source s3 bucket
        try:
            logger.info(f'Pushing updated deploy.zip to {source_bucket}')
            s3_client.upload_file(
                '/tmp/deploy.zip',
                source_bucket,
                key
            )
        except Exception as e:
            logger.error(f'Failed uploading deploy.zip to {source_bucket}')
            logger.error(e)
            raise e

        # Deploy CodePipeline.yaml
        try:
            stack_name = product_name + '-codepipeline'
            contents = open('/tmp/iac/CodePipeline.yml', 'r').read()
            logger.info(f'Deploying {stack_name}')
            response = cloudformation_client.create_stack(
                StackName=stack_name,
                TemplateBody=contents,
                Parameters=[
                    {
                        'ParameterKey': 'pProductName',
                        'ParameterValue': product_name
                    }
                ]
            )
        except Exception as e:
            logger.error(f'Failed deploying {product_name}-codepipeline')
            logger.error(e)
            raise e

    # Send Signal
    response_data = dict()
    response_data['SUCCESS'] = "SUCCESS - This worked"
    logger.debug(f'response_data: {response_data}')

    cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, "CustomResourcePhysicalID")


def update_file(
        file_name,
        search_string,
        replace_string
):
    file = open(file_name, 'r')
    file_data = file.read()
    file.close()
    new_data = file_data.replace(search_string, replace_string)
    file = open(file_name, 'w')
    file.write(new_data)
    file.close()
