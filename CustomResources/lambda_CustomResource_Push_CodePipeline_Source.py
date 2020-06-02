# Custom Resource; will push a codepipeline's source files to the pipeline's git repo

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
import git
import shutil


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
    product_name = event['ResourceProperties']['ProductName']
    logger.debug(f'product_name: {product_name}')
    git_url = event['ResourceProperties']['GitHubRepoUrl']
    git_url = git_url.split("https://")[1]
    logger.debug(f'git_url: {git_url}')
    developer_token = event['ResourceProperties']['GitHubDeveloperToken']
    logger.debug(f'developer_token: {developer_token}')
    repo_name = git_url.split('/')[-1]
    logger.debug(f'repo_name: {repo_name}')

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
            directory_contents = os.listdir('/tmp')
            logger.debug(f'/tmp directory_contents before unzip: {directory_contents}')

            logger.info(f'Unzipping /tmp/deploy.zip')
            with zipfile.ZipFile('/tmp/deploy.zip', 'r') as zip_ref:
                zip_ref.extractall('/tmp')
            directory_contents = os.listdir('/tmp')
            logger.debug(f'/tmp directory_contents after unzip: {directory_contents}')
            directory_contents = os.listdir('/tmp/tmp')
            logger.debug(f'/tmp/tmp directory_contents after unzip: {directory_contents}')
        except Exception as e:
            logger.error(f'Failed unzipping deploy.zip')
            logger.error(e)
            raise e

        # Clone repo locally
        try:
            logger.info(f'Cloning repo locally...')
            response = git.exec_command(
                'clone', 'https://' + developer_token + ':x-oauth-basic@' + str(git_url) + '.git'
            )
            logger.debug(f'response: {response}')
            directory_contents = os.listdir('/tmp')
            logger.debug(f'/tmp directory_contents: {directory_contents}')
            directory_contents = os.listdir('/tmp/' + repo_name)
            logger.debug(f'/tmp/{repo_name} directory_contents: {directory_contents}')
            if 'iac' in directory_contents:
                logger.info(f'Removing previous iac folder from {repo_name}...')
                shutil.rmtree('/tmp/' + repo_name + '/iac')
                directory_contents = os.listdir('/tmp/' + repo_name)
                logger.debug(f'/tmp/{repo_name} directory_contents after iac folder removal: {directory_contents}')
        except Exception as e:
            logger.error(f'Failed cloning the repo')
            logger.error(f'e: {e}')

        # Copy files from s3 copy to git repo folder
        try:
            logger.info(f'Copying files from s3 extract to git repo folder...')
            shutil.copytree('/tmp/tmp/iac', '/tmp/' + repo_name + '/iac')
            directory_contents = os.listdir('/tmp/' + repo_name + '/iac')
            logger.debug(f'/tmp/{repo_name}/iac directory_contents: {directory_contents}')
        except Exception as e:
            logger.error(f'Failed copying files from s3 copied folder to git clone folder')
            logger.error(f'e: {e}')

        # Add files to git folder
        try:
            logger.info(f'Adding files to git repo...')
            response = git.exec_command(
                'add', '.', cwd='/tmp/' + repo_name
            )
            logger.debug(f'response: {response}')
            directory_contents = os.listdir('/tmp/' + repo_name)
            logger.debug(f'/tmp/{repo_name} directory_contents: {directory_contents}')
        except Exception as e:
            logger.error(f'Failed adding files to git repo')
            logger.error(f'e: {e}')

        # Commit files to git repo
        try:
            logger.debug(f'Committing files to git repo...')
            commit_env = os.environ
            commit_env['GIT_AUTHOR_NAME'] = 'Cloud_Transformation'
            commit_env['GIT_AUTHOR_EMAIL'] = 'cloud-transformation@aep.com'
            commit_env['GIT_COMMITTER_NAME'] = 'Cloud_Transformation_AWS_Lambda'
            commit_env['GIT_COMMITTER_EMAIL'] = 'cloud-transformation@aep.com'
            response = git.exec_command(
                'commit', '-am "CodePipeline Initial Commit"', cwd='/tmp/' + repo_name, env=commit_env
            )
            logger.debug(f'response: {response}')
        except Exception as e:
            logger.info(f'Branch already up-to-date.  Nothing to commit.')
            logger.debug(f'e: {e}')

        # Push source files to git repo
        try:
            logger.info(f'Pushing source files to {repo_name}...')
            response = git.exec_command(
                'push', cwd='/tmp/' + repo_name
            )
            logger.debug(f'response: {response}')
        except Exception as e:
            logger.error(f'Failed pushing source files to {repo_name}')
            logger.error(e)
            raise e

        # Cleanup
        try:
            logger.info(f'Starting cleanup...')
            logger.debug(f'Removing /tmp/{repo_name}')
            shutil.rmtree('/tmp/' + repo_name)
            logger.debug(f'Removing /tmp/deploy.zip')
            os.remove('/tmp/deploy.zip')
            logger.debug(f'Removing /tmp/iac')
            shutil.rmtree('/tmp/iac')
            directory_contents = os.listdir('/tmp')
            logger.debug(f'/tmp directory_contents: {directory_contents}')
        except Exception as e:
            logger.error(f'Failed cleaning up')
            logger.error(f'e: {e}')

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
