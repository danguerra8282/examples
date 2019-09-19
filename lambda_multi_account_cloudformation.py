# Deploys all lambdas found in aep-lambda-functions-bucket-test
# Triggers off of CloudWatch event
# This requires a Lambda role that has the following permissions:
#   - STS
#   - Cloudformation
#   - Lambda

# Import Modules
import boto3
import logging
import datetime
from datetime import datetime
import json

# Logging
logger = logging.getLogger()
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)
logging.getLogger("botocore").setLevel(logging.ERROR)

# CONSTANTS
ACCOUNTS_TO_SKIP = []
TEMPLATES_TO_SKIP = [
    'AllAccounts/deploy_lambdas/cloudformation_deploy_lambdas.yaml',
    'Shared-Services/multi_account_cloudformation/',
    'Shared-Services/multi_account_cloudformation/cloudformation_multi_account_cloudformation.yml',
    'Shared-Services/multi_account_cloudformation/lambda_multi_account_cloudformation.zip'
    ]
ROLE_TO_ASSUME = 'CloudLambda'


# MAIN #
def lambda_handler(_event, _context):
    logger.info(f'Starting Lambda Deployments')
    logger.info(f'_event: {_event}')
    # logger.debug(f'_event: {_event}')

    # Extract the Job ID for CodePipeline
    try:
        job_id = _event['CodePipeline.job']['id']
        logger.info(f'job_id: {job_id}')
    except Exception as e:
        logger.info(f'CodePipeline job_id not found')
        job_id = ''

    # Extract the Job Data
    try:
        job_data = _event['CodePipeline.job']['data']
        # logger.debug(f'job_data: {job_data}') # contains access keys, obfuscate this!
    except Exception as e:
        logger.info(f'CodePipeline job_data not found')
        job_data = ''

    # Extract the UserParameters for CodePipeline
    try:
        user_parameters = json.loads(job_data['actionConfiguration']['configuration']['UserParameters'])
        logger.debug(f'user_parameters: {user_parameters}')
        environment = user_parameters['environment']
        logger.info(f'environment: {environment}')
        # logger.info(f'environment type: {type[environment]}')
        template_params = user_parameters['templateParams']
        logger.info(f'template_params: {template_params}')
        product = user_parameters['product']
        logger.info(f'product: {product}')
        s3_bucket = user_parameters['s3Bucket']
        logger.info(f's3_bucket: {s3_bucket}')
        s3_subfolder = user_parameters['s3Subfolder']
        logger.info(f's3_subfolder: {s3_subfolder}')
        exact_match = user_parameters['exact_match']
        logger.info(f'exact_match: {exact_match}')
    except Exception as e:
        logger.info(f'CodePipeline user_parameters not found')
        user_parameters = ''
        environment = ''
        template_params = ''
        product = ''
        exact_match = None

    # Setup Connections
    session = boto3.Session()
    dynamo_client = session.client('dynamodb')
    sts_client = session.client('sts')
    codepipeline_client = session.client('codepipeline')

    #  Get Current DateTime
    utc_date_time = datetime.utcnow()
    logger.debug(f'utc_date_time: {utc_date_time}')

    # Verify Environment Table is Available
    try:
        response = dynamo_client.describe_table(TableName='Environments')
        logger.debug(f'response: {response}')
        logger.info(f'Environments Dynamo Table found')
    except Exception as e:
        logger.error(f'Environments Dynamo Table not found')
        if job_id:
            codepipeline_client.put_job_failure_result(
                jobId=job_id,
                failureDetails={
                    'type': 'JobFailed',
                    'message': 'Environments Dynamo Table not found'
                }
            )
        raise e

    # Get information from dynamo table
    try:
        account_ids = get_values_from_dynamo_column(dynamo_client,
                                                    "Environments",
                                                    "AccountId",
                                                    environment,
                                                    'S',
                                                    exact_match)
        logger.info(f'AccountIds found in Environments dynamo: {account_ids}')
    except Exception as e:
        logger.error(f'Failed while getting information from dynamo table')
        if job_id:
            codepipeline_client.put_job_failure_result(
                jobId=job_id,
                failureDetails={
                    'type': 'JobFailed',
                    'message': 'Failed while getting info from dynamo table'
                }
            )
        raise e

    # Option to skip specified accounts
    try:
        logger.info(f'Identifying accounts to skip...')
        for account_to_skip in ACCOUNTS_TO_SKIP:
            if account_to_skip in account_ids:
                account_ids.remove(account_to_skip)
        logger.info(f'Updated accounts list: {account_ids}')
    except Exception as e:
        logger.error(f'Failed while identifying accounts to skip')
        if job_id:
            codepipeline_client.put_job_failure_result(
                jobId=job_id,
                failureDetails={
                    'type': 'JobFailed',
                    'message': 'Failed while identifying accounts to skip'
                }
            )
        raise e

    # Loop through all accounts
    logger.info(f'Starting deployments...')
    for account_id in account_ids:
        logger.info(f'Starting actions in {account_id}')

        # Get credentials for account_id (Turn into a function?)
        try:
            assumed_credentials = sts_client.assume_role(
                RoleArn=('arn:aws:iam::' + account_id + ':role/' + ROLE_TO_ASSUME),
                RoleSessionName='AssumedRole'
                )
            logger.debug(f'assumed_credentials: {assumed_credentials}')
        except Exception as e:
            logger.error(f'Failed getting credentials for {account_id}')
            if job_id:
                response = codepipeline_client.put_job_failure_result(
                    jobId=job_id,
                    failureDetails={
                        'type': 'JobFailed',
                        'message': 'Failed assuming credentials'
                    }
                )
            raise e

        # Setup connection in specified account
        try:
            cloudformation_client = session.client('cloudformation',
                aws_access_key_id=assumed_credentials["Credentials"]['AccessKeyId'],
                aws_secret_access_key=assumed_credentials["Credentials"]['SecretAccessKey'],
                aws_session_token=assumed_credentials["Credentials"]['SessionToken'],)
            logger.debug(f'cloudformation_client: {cloudformation_client}')
            s3_client = session.client('s3',
                aws_access_key_id=assumed_credentials["Credentials"]['AccessKeyId'],
                aws_secret_access_key=assumed_credentials["Credentials"]['SecretAccessKey'],
                aws_session_token=assumed_credentials["Credentials"]['SessionToken'],)
            logger.debug(f's3_client: {s3_client}')
        except Exception as e:
            logger.error(f'Failed creating session connection')
            if job_id:
                response = codepipeline_client.put_job_failure_result(
                    jobId=job_id,
                    failureDetails={
                        'type': 'JobFailed',
                        'message': 'Failed creating session connections'
                    }
                )
            raise e

        # Get Contents of S3 Bucket
        try:
            # s3_bucket = 'aep-lambda-functions-bucket-test'  #
            # s3_subfolder = 'AllAccounts/'                   #
            logger.info(f'Getting templates from {s3_bucket}')
            cloudformation_templates = get_s3_contents(s3_client,
                                                       s3_bucket,
                                                       'cloudformation')
            logger.info(f'Cloudformation templates found: \
                {cloudformation_templates}')
        except Exception as e:
            logger.error(f'Failed getting information from {s3_bucket}')
            if job_id:
                response = codepipeline_client.put_job_failure_result(
                    jobId=job_id,
                    failureDetails={
                        'type': 'JobFailed',
                        'message': 'Failed getting information from s3'
                    }
                )
            raise e

        # Remove templates not in s3_subfolder
        try:
            logger.info(f'Removing templates not found in {s3_subfolder}')
            updated_cloudformation_templates = []
            for cloudformation_template in cloudformation_templates:
                if s3_subfolder in cloudformation_template:
                    updated_cloudformation_templates.append(cloudformation_template)
            cloudformation_templates = updated_cloudformation_templates
            logger.info(f'Updated cloudformation_templates list: {cloudformation_templates}')
        except Exception as e:
            logger.error(f'Failed removing templates not in {s3_subfolder} \
                subfolder')
            if job_id:
                response = codepipeline_client.put_job_failure_result(
                    jobId=job_id,
                    failureDetails={
                        'type': 'JobFailed',
                        'message': 'Failed removing templates'
                    }
                )
            raise e

        # Option to skip specified Templates
        try:
            logger.info(f'Identifying templates to skip...')
            logger.warning(f'TEMPLATES_TO_SKIP: {TEMPLATES_TO_SKIP}')
            for template in TEMPLATES_TO_SKIP:
                if template in cloudformation_templates:
                    cloudformation_templates.remove(template)
        except Exception as e:
            logger.error(f'Failed while identifying templates to skip')
            if job_id:
                response = codepipeline_client.put_job_failure_result(
                    jobId=job_id,
                    failureDetails={
                        'type': 'JobFailed',
                        'message': 'Failed identifying templates to skip'
                    }
                )
            raise e

        # Download templates
        for cloudformation_template in cloudformation_templates:
            logger.info(f'Downloading cloudformation_template: \
            {cloudformation_template}')
            cloudformation_template_key = cloudformation_template.split('/')
            template = s3_client.download_file(
                s3_bucket,
                cloudformation_template,
                '/tmp/' + cloudformation_template_key[1])

        # Deploy Cloudformation templates
        for cloudformation_template in cloudformation_templates:
            try:
                logger.info(f'Deploying {cloudformation_template} in {account_id}')
                cloudformation_template_key = cloudformation_template.split('/')
                stack_name = str(cloudformation_template_key).split('cloudformation_')[1]
                stack_name = stack_name.split('.')[0]
                if '_' in stack_name:
                    stack_name = stack_name.replace('_', '-')
                print('stack_name: ' + stack_name)
                cloudformation_template_url = 'https://' + s3_bucket + \
                    '.s3.amazonaws.com/' + stack_name + '/' + cloudformation_template
                logger.debug(f'cloudformation_template_url: {cloudformation_template_url}')
                contents = open('/tmp/' + cloudformation_template_key[1], 'r').read()
                logger.debug(f'contents: {contents}')

                # Get Object ID of code (this will force the code update)
                print('cloudformation_template: ' + cloudformation_template)
                template_code_key = cloudformation_template.replace(
                    'cloudformation_',
                    'lambda_'
                )
                template_code_key = template_code_key.replace(
                    '.yaml',
                    '.zip'
                )
                template_code_key = template_code_key.replace(
                    '.yml',
                    '.zip'
                )
                logger.debug(f'template_code_key: {template_code_key}')
                logger.info(f'Bucket={s3_bucket}, Key={str(template_code_key)}')

                try:
                    s3_object_version = s3_client.get_object(
                        Bucket=s3_bucket,
                        Key=template_code_key
                    )
                except Exception as e:
                    logger.info(f'template_code_key {template_code_key} ' \
                        'not found')
                    logger.info('Assuming cloudformation is not for a ' \
                        'lambda function')
                    # s3_object_version = None
                    template_code_key = cloudformation_template
                    s3_object_version = s3_client.get_object(
                        Bucket=s3_bucket,
                        Key=template_code_key
                    )

                logger.info(f's3_object_version: {s3_object_version}')

                response = deploy_cloudformation(cloudformation_client,
                                                 cloudformation_template_url,
                                                 stack_name,
                                                 contents,
                                                 s3_object_version['VersionId'])

                logger.info(f'cloudformation execution response: {response}')

            except Exception as e:
                logger.error(f'Failed executing cloudfomation \
                    {cloudformation_template} in account_id {account_id}')
                if job_id:
                    response = codepipeline_client.put_job_failure_result(
                        jobId=job_id,
                        failureDetails={
                            'type': 'JobFailed',
                            'message': 'Failed executing cloudformation'
                        }
                    )
                raise e

    # # Intentional Failure
    # if job_id:
    #     codepipeline_client.put_job_failure_result(
    #         jobId=job_id,
    #         failureDetails={
    #             'type': 'JobFailed',
    #             'message': 'Intentional Failure'
    #         }
    #     )

    # Complete codepipeline job
    if job_id:
        codepipeline_client.put_job_success_result(jobId=job_id)


def get_values_from_dynamo_column(
                                dynamo_client,
                                table_name,
                                column_name,
                                filter=None,
                                filter_type=None,
                                exact_match=None):
    """
    Searches and returns anything with the filter from dynamo
    :param dynamo_client: boto3.client
    :param table_name: (string) dynamo table to search
    :param column_name: (string) dynamo column to return data from
    :param filter: (string) optional filter string
    :param filter_type: (String) required type data type of optional filter
    :param exact_match: (String) optional for filter to be exact & not fuzzy
    :return files: array of strings
    """
    try:
        response = dynamo_client.scan(TableName=table_name)
        logger.debug(f'response: {response}')
    except Exception as e:
        logger.error(f'Failed to retreive data from table')
        raise e

    if filter:
        filtered_array = []
        for resp in response['Items']:
            try:
                if filter in resp['AccountName'][filter_type]:
                    if exact_match:
                        # print('--- ' + str(resp['AccountName'][filter_type]))
                        if resp['AccountName'][filter_type] == filter:
                            for value in resp[column_name]:
                                filtered_array.append(resp[column_name][value])
                    else:
                        for value in resp[column_name]:
                            filtered_array.append(resp[column_name][value])
            except Exception as e:
                logger.error(f'filtering failed: column_name: {column_name} \
                    not found in {table_name} dynamo table')
                raise e
        logger.debug(f'filtered_array: {filtered_array}')
        return filtered_array
    else:
        array = []
        for resp in response['Items']:
            try:
                if column_name in resp:
                    for value in resp[column_name]:
                        array.append(resp[column_name][value])
            except Exception as e:
                logger.error(f'column_name: {column_name} not found in \
                            {table_name} dynamo table')
                raise e
        logger.debug(f'array: {array}')
        return array


def get_s3_contents(s3_client,
                    s3_bucket,
                    search_string):
    """
    Searches and returns anything with the search_string in the s3_bucket
    :param s3_client: boto3.client
    :param s3_bucket: (string) bucket to search
    :param search_string: (string) index to search for in bucket
    :return files: array of strings
    """
    files = []
    print("#############################################")
    s3_contents = s3_client.list_objects(Bucket=s3_bucket)
    print("#############################################")
    logger.debug(f's3_contents: {s3_contents}')
    for obj in s3_contents['Contents']:
        if search_string in obj['Key']:
            file = obj['Key']
            # file = file.split('/')
            logger.debug(f'file: {file}')
            # files.append(file[1])
            files.append(file)
            # files.append(file)
    return files


def deploy_cloudformation(cloudformation_client,
                          cloudformation_template_url,
                          stack_name,
                          contents,
                          parameters=None):
    # Update stack if it already exists
    try:
        response = cloudformation_client.describe_stacks(
            StackName=stack_name
        )
        logger.debug(f'****** response: {response}')
    except Exception as e:
        logger.info(f'stack_name: {stack_name} does not exists')
        response = None

    try:
        if(response):
            logger.info(f'stack_name: {stack_name} already exists.  Updating...')
            response = cloudformation_client.update_stack(
                StackName=stack_name,
                TemplateBody=contents,
                Parameters=[{
                    'ParameterKey': 'pS3ObjectVersion',
                    'ParameterValue': parameters
                }],
                Capabilities=['CAPABILITY_NAMED_IAM']
            )
    except Exception as e:
        logger.info(f'No updates to be performed on stack_name: {stack_name}')

    try:
        if not (response):
            logger.info(f'Creating stack_name: {stack_name}')
            response = cloudformation_client.create_stack(
                StackName=stack_name,
                TemplateBody=contents,
                Parameters=[{
                    'ParameterKey': 'pS3ObjectVersion',
                    'ParameterValue': parameters
                }],
                Capabilities=['CAPABILITY_NAMED_IAM'])
                # TemplateURL=cloudformation_template_url)
            logger.debug(f'response: {response}')
    except Exception as e:
        logger.error(f'Failed creating stack_name: {stack_name}')
        raise e
