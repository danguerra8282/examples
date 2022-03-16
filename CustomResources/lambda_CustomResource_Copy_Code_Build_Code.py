"""
Description:
    Custom Resource; Copies CodeBuild code from s3 bucket 123 to the destination bucket.
                     Used by ServuceCatalog_Product-ecs_codebuild_environment.


rCustomResource:
  Type: Custom::CopyCodeBuildCode
  Properties:
    ServiceToken: !Sub "arn:aws:lambda:us-east-1:${AWS::AccountId}:function:lambda_CustomResource_Copy_Code_Build_Code"
    DestinationBucket: codebuild-testing-02-s3-bucket
    GithubRepoName: !Ref pGitRepoName
    DeveloperToken: !Ref pDeveloperToken
    AccountId: !Sub "${AWS::AccountId}"
    EcsCodeBuildEnvironment: !Ref pAppName
    EcrRepo: !Ref pAppName
    TaskDefinition: !Ref rTaskDefinition
"""

# Import Modules
import boto3
import logging
import json
import datetime
from datetime import datetime
import cfnresponse  # <--- Required for custom_resource
import time
import zipfile
import os


ROLE_TO_ASSUME = 'role_name'
ASSUME_ACCOUNT_ID = '123412341234'


def lambda_handler(event, context):
    # Logging
    logger = logging.getLogger()
    # logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    session = boto3.Session()
    # s3_client = session.client('s3')
    sts_client = session.client('sts')

    logger.info(f'event: {event}')  # <--- Input from CloudFormation
    logger.debug(f'context: {context}')
    response_data = 'False'

    destination_bucket = event['ResourceProperties']['DestinationBucket']
    git_hub_repo_name = event['ResourceProperties']['GithubRepoName']
    developer_token = event['ResourceProperties']['DeveloperToken']
    account_id = event['ResourceProperties']['AccountId']
    ecs_code_build_environment = event['ResourceProperties']['EcsCodeBuildEnvironment']
    ecr_repo = event['ResourceProperties']['EcrRepo']
    task_definition = event['ResourceProperties']['TaskDefinition']
    logger.info(f'destination_bucket: {destination_bucket}')
    logger.info(f'git_hub_repo_name: {git_hub_repo_name}')
    logger.info(f'developer_token: {developer_token}')
    logger.info(f'account_id: {account_id}')
    logger.info(f'ecs_code_build_environment: {ecs_code_build_environment}')
    logger.info(f'ecr_repo: {ecr_repo}')
    logger.info(f'task_definition: {task_definition}')

    if 'Create' in event['RequestType']:
        try:
            print(f'--- Attempting to assume this role:  arn:aws:iam::' + ASSUME_ACCOUNT_ID + ':role/' + ROLE_TO_ASSUME)
            assumed_credentials = sts_client.assume_role(
                RoleArn=('arn:aws:iam::' + ASSUME_ACCOUNT_ID + ':role/' + ROLE_TO_ASSUME),
                RoleSessionName='AssumedRole'
                )
            s3_client = session.client('s3',
                aws_access_key_id=assumed_credentials["Credentials"]['AccessKeyId'],
                aws_secret_access_key=assumed_credentials["Credentials"]['SecretAccessKey'],
                aws_session_token=assumed_credentials["Credentials"]['SessionToken'],)
        except Exception as e:
            logger.error(f'Failed to assume role')
            logger.error(f'e: {e}')
            cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
            raise e

        # Download buildspec.yml for current project
        try:
            logger.info(f'Downloading files needed for CodeBuild Project')
            s3_client.download_file(
                'service-catalog-product-ecs-codebuild-environment',
                'CodeBuildSource/buildspec.yml',
                '/tmp/buildspec-temp.yml'
            )
            s3_client.download_file(
                'service-catalog-product-ecs-codebuild-environment',
                'CodeBuildSource/PythonFiles.zip',
                '/tmp/PythonFiles.zip'
            )
            directory_contents = os.listdir('/tmp/')
            logger.debug(f'directory_contents after download: {directory_contents}')
        except Exception as e:
            logger.error(f'Failed downloading PythonFiles & buildspec.yml')
            logger.error(f'e: {e}')
            cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
            raise e

        # Unzip local PythonFiles.zip
        try:
            logger.info(f'Unzipping /tmp/PythonFiles.zip')
            with zipfile.ZipFile('/tmp/PythonFiles.zip', 'r') as zip_ref:
                zip_ref.extractall('/tmp/')
            directory_contents = os.listdir('/tmp/PythonFiles/')
            logger.debug(f'directory_contents after unzip: {directory_contents}')
        except Exception as e:
            logger.error(f'Failed unzipping downloaded file')
            logger.error(f'e: {e}')
            cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
            raise e

        # Modify buildspec.yml for the specific project
        try:
            logger.info(f'Attempting to modify buildspec-temp.yml for the specific project')
            with open('/tmp/buildspec-temp.yml', 'r+') as f:
                text = f.read()
                print(f'before edit: {text}')
                text = text.replace('%_git_developer_token_%', developer_token)
                text = text.replace('%_git_repo_name_%', git_hub_repo_name)
                text = text.replace('%_account_id_%', account_id)
                text = text.replace('%_ecs-codebuild-environment_%', ecs_code_build_environment)
                text = text.replace('%_ecr_repo_%', ecr_repo)
                text = text.replace('%_task_definition_%', task_definition)
                # f.seek(0)
                print(f'after edit: {text}')
            with open('/tmp/buildspec.yml', 'x') as x:
                x.write(text)
            ##################################################
            # with open('/tmp/buildspec.yml', 'r+') as x:
            #     updated_text = x.read()
            #     updated_text = updated_text.replace('NT $ECR_REPO', '')
            #     print(f'updated_text: {updated_text}')
            #     x.seek(0)
            #     x.write(updated_text)
            ##################################################
        except Exception as e:
            logger.error(f'Failed modifying buildspec.yml for the specific project')
            logger.error(f'e: {e}')
            cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
            raise e

        # Zip up files
        try:
            logger.info(f'Zipping up CodeBuild files into Source.zip')
            new_source_zip = zipfile.ZipFile("/tmp/Source.zip", "w")
            os.chdir("/tmp")
            new_source_zip.write("buildspec.yml")

            for dirname, subdirs, files in os.walk('PythonFiles'):
                new_source_zip.write(dirname)
                for filename in files:
                    new_source_zip.write(os.path.join(dirname, filename))
            new_source_zip.close()
        except Exception as e:
            logger.error(f'Failed zipping up the files')
            logger.error(f'e: {e}')
            cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
            raise e

        # Copy .zip back into s3 destination_bucket
        try:
            logger.info(f'Copying files into')
            s3_client = session.client('s3')
            s3_client.upload_file(
                '/tmp/Source.zip',
                destination_bucket,
                'Source.zip'
            )
        except Exception as e:
            logger.error(f'Failed copying the zip back to the destination_bucket')
            logger.error(f'e: {e}')
            cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
            raise e

    # Send Signal   <--- Send Signal back to CloudFormation saying the custom_resource is complete.
    # REQUIRED or the cloudformation will never complete
    response_data = dict()
    response_data['success'] = 'True'
    logger.info(f'response_data: {response_data}')
    cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, "CustomResourcePhysicalID")
