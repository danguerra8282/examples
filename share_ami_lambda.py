"""
=============================================================
| DELIVERY PIPELINE LAMBDAS | Share_AMI                     |
=============================================================
This Delivery Pipeline lambda is meant to "Share" an Amazon Machine Image (AMI) to other accounts.
To 'Share' ami means: Modify the AMI attributes to add the new account to the LaunchPermission for the AMI
                      Also give the new account permission to use AMI snapshots

This lambda is meant to be called via CodePipeline after the Bake_AMI step. The general flow of the functional AMI
creation process goes:
    1) Bake the AMI in the shared services account (happens in InfraSvcsProd)
    2) (THIS LAMBDA) Share the AMI to the target BSA account e.g. DevCDT01, TestCDT01, ProdCDT01
    3) Encrypt the AMI (lambda runs in InfraSvcsProd, but the AMI is being encrypted in the target BSA account)
    4) Now the AMI is usable by resources in BSA accounts


This lambda takes in an InputArtifact, Package. In this artifact, it looks for the manifest.json file produced in
the Bake_AMI step to get the actual AMI id produced. If it cannot find this file, it attempts to look up the AMI
id from the Delivery_Pipeline_Catalog table.

This lambda takes in an (Optional) UserParamter 'environments'. In this environments parameter, this lambda expects
to find a list


Sample CodePipeline.yaml action configuration:
            - Name: Share_AMI
              ActionTypeId:
                Category: Invoke
                Owner: AWS
                Provider: Lambda
                Version: '1'
              Configuration:
                FunctionName: Share_AMI
                UserParameters: !Sub '{"environments":["Prod${pBusinessUnit}","Test${pBusinessUnit}","Dev${pBusinessUnit}"]}'
              InputArtifacts:
                - Name: Package
              OutputArtifacts: []
              RunOrder: 5
"""

from common.aws_helper import get_pipeline_info, get_user_params, get_codepipeline_artifact, get_column_from_dynamodb, \
    get_all_account_numbers
from common.aws_api_wrapper import exceptions, put_job_failure, put_job_success, boto3_client, get_resource_tags, \
                                   set_resource_tags, assume_role
from common.custom_logging import set_logger_format
import copy
import logging
import os
import json

# =============== LOGGING SETUP =================== #
logger = logging.getLogger("Share_Ami")
logging.getLogger("botocore").setLevel(logging.ERROR)
logger.setLevel(logging.DEBUG)
logger.info("Function container starting up...")

# =========== CONSTANT GLOBAL VARIABLES =========== #
# Accounts we do not want to share
CURRENT_ACCOUNT = os.environ['CurrentAccount']
ACCOUNTS_TO_SKIP = [
                    "937891257447",  # MASTER ACCOUNT
                    "245564243137",  # SEC TOOLS ACCOUNT
                    CURRENT_ACCOUNT  # InfraSvcsProd
                    ]
# TEMPORARY ACCOUNTS TO SKIP, accounts in the middle of being set up,
# AMIs to (mainly new accounts that don't have IAM done yet)
TEMPORARY_SKIP = []
ACCOUNTS_TO_SKIP = ACCOUNTS_TO_SKIP + TEMPORARY_SKIP
SENSITIVE_PARAMETERS = ['artifactCredentials', 'webhook_secret']

def lambda_handler(event, _context):
    # reset logger format so it does not print previous execution pipeline name
    set_logger_format(pipeline_name="")

    # print lambda start message
    logger.info("=========================START SHARE_AMI LAMBDA=======================================")

    # dump triggering event to console
    print_event = copy.deepcopy(event)
    # Removing sensitive data
    try:
        for parameter in SENSITIVE_PARAMETERS:
            if print_event['CodePipeline.job']['data'].get(parameter):
                print_event['CodePipeline.job']['data'][parameter] = "*****"
        logger.debug(json.dumps(print_event, indent=4, sort_keys=True, default=str))
    except KeyError as e:
        logger.warning(e)
        logger.warning("Problem creating print event, continuing...")

    # Extract the Job ID
    job_id = event['CodePipeline.job']['id']
    # Extract the Job Data
    job_data = event['CodePipeline.job']['data']

    # If the account parameters were passed in userparameters, use. otherwise, use bucket tags
    try:
        logger.debug(f'job_data: {job_data}')
        user_parameters = json.loads(job_data['actionConfiguration']['configuration']['UserParameters'])
        logger.debug(f'user_parameters: {user_parameters}')
    except Exception:
        user_parameters = {}
        logger.debug(f'No user_parameter data returned')

    try:

        # ===================== Get Pipeline Information
        try:
            pipeline_name, stage_name, exec_uid = get_pipeline_info(job_id)

            # Setup logging so every line includes the pipeline name
            set_logger_format(pipeline_name=pipeline_name)
            logger.info(f"=============       PIPELINE NAME:      {pipeline_name}         ==============")

            if user_parameters:
                if "baked_encrypted" in user_parameters:
                    manifest_contents = get_codepipeline_artifact(job_data, 'encrypted_ami.json')
                    logger.debug(f'manifest_contents (from encrypted_ami.json): {manifest_contents}')
                else:
                    manifest_contents = get_codepipeline_artifact(job_data, 'manifest.json')
                    logger.debug(f'manifest_contents (from manifest.json): {manifest_contents}')
            else:
                manifest_contents = get_codepipeline_artifact(job_data, 'manifest.json')
                logger.debug(f'manifest_contents (from manifest.json): {manifest_contents}')
        except exceptions.JobException as e:
            log_and_fail(job_id, f"ERROR: Failed to get information on Job ID {job_id}: {str(e)}")
            raise e
        except exceptions.CodePipelineException as e:
            log_and_fail(job_id, f"ERROR: Failed to get pipeline information: {str(e)}")
            raise e
        except exceptions.S3ObjectException as e:
            log_and_fail(job_id, f"ERROR: Failed to get pipeline manifest.json from S3: {str(e)}")
            raise e

        # ===================== Find the AMI id to share
        # See if the Package:manifest.json file exists
        if manifest_contents is not None:
            logger.info("Found manifest.json file in InputArtifact")
            try:
                if user_parameters:
                    try:
                        ami_id = manifest_contents['encrypted_ami']
                        logger.debug(f'ami_id (from encrypted_ami.json): {ami_id}')

                    except Exception:
                        ami_id = manifest_contents['builds'][0]['artifact_id'].split(':')[1]
                        logger.debug(f'ami_id (from manifest.json): {ami_id}')

                else:
                    ami_id = manifest_contents['builds'][0]['artifact_id'].split(':')[1]
            except Exception as e:
                raise Exception(f"manifest.json file found in Package artifact is invalid. Error: {e}")
        # if manifest.json does not exist, get AMI from dynamodb
        else:
            logger.info("No manifest.json file found in InputArtifacts, "
                        "try to get Functional_AMI from Delivery_Pipeline_Catalog table")
            try:
                ami_id = get_column_from_dynamodb(exec_uid, pipeline_name, 'Functional_AMI', 'S')
            except exceptions.DynamoDBReadException as e:
                log_and_fail(
                    job_id,
                    f"ERROR: Failed to get Functional_AMI column from DeliveryPipelineCatalog: {str(e)}"
                )
                raise e

        logger.info('AMI_Id found:{}'.format(ami_id))

        # ===================== Finally share the AMI
        # Allow users to specify the environments they would like to share to
        if 'UserParameters' in job_data['actionConfiguration']['configuration'] and 'environments' in job_data['actionConfiguration']['configuration']['UserParameters']:
            # ======= Case: share to specifc environments
            required_param_list = ['environments']
            try:
                params = get_user_params(job_data, required_param_list)
            except Exception as e:
                log_and_fail(job_id, f"ERROR: Failed to decode pipeline UserParameters: {str(e)}")
                raise e
            if not isinstance(params['environments'], list):
                raise Exception(f"Invalid format of environments UserParameter. This parameter should be a list "
                                f"of BSA account names. Parameter recieved: {params['environments']}")

            for environment in params['environments']:
                try:
                    account_number = get_account_number(environment)
                    if account_number is None:
                        raise Exception(f"{environment} is not valid account name. "
                                        f"It should be something like: 'ProdBSA01'")
                except Exception as e:
                    log_and_fail(job_id, f"Could not get account number for {environment} environment, error:{e}")
                    raise e

                share_ami(ami_id=ami_id, account_number=account_number)

        # Share AMI to all environments
        else:
            # ======= Case: share to all environments
            logger.info(f"Sharing ami {ami_id} to all accounts...")
            for account_number in get_all_account_numbers():
                if account_number not in ACCOUNTS_TO_SKIP:
                    share_ami(ami_id, account_number)
        put_job_success(job_id, 'AMI:{} completed sharing'.format(ami_id))

    except Exception as e:
        # If any other exceptions which we didn't expect are raised
        # then fail the job and log the exception message.
        log_and_fail(job_id, f"ERROR: An unexpected error has occurred: {str(e)}")
        raise e

    logger.info('Function complete.')
    return "Complete."




def log_and_fail(job_id, message):
    """
    Quick function to send a message to the logger and put a failure to the pipeline
    """

    logger.error(message)
    put_job_failure(job_id, message)

    return


def get_account_number(environment):
    logger.info("Getting environment information from DynamoDB Table")
    client = boto3_client('dynamodb')

    response = client.scan(
        TableName='Environments',
        FilterExpression='#Environment_Name_Key = :Environment_Name_Value',
        ExpressionAttributeValues={
            ":Environment_Name_Value": {"S": environment}
        },
        ExpressionAttributeNames={
            "#Environment_Name_Key": "envName",
        }
    )
    print(response)
    for i in response['Items']:
        return i['oAccountID']['S']


def share_ami(ami_id: str, account_number: str, assumed_credentials=None)->None:
    """
    Shares an ami to another account.
    To 'Share' ami means: Modify the AMI attributes to add the new account to the LaunchPermission for the AMI
                          Also give the new account permission to use AMI snapshots

    :param ami_id: ID of ami to be shared
    :param account_number:  the number of the target account the ami will be shared to
    :param assumed_credentials: AWS Credentials for the target account
    :return: None
    """
    try:
        ec2 = boto3_client('ec2', assumed_credentials)
        logging.info('Sharing AmiId:{} to account {}'.format(ami_id, account_number))
        logger.debug('Getting AMI Information')
        tags = get_resource_tags(ami_id)
        logger.debug('Tags Found:{}'.format(tags))
        snapshot_info = ec2.describe_images(
            ImageIds=[ami_id]
        )
        images = snapshot_info['Images']
        for i in images:
            for b in i['BlockDeviceMappings']:
                if b.get('Ebs'):
                    snapshot_id = b['Ebs']['SnapshotId']
                    logging.info('Sharing SnapshotId:{} to account {}'.format(snapshot_id, account_number))
                    ec2.modify_snapshot_attribute(
                        SnapshotId=snapshot_id,
                        CreateVolumePermission={
                            'Add': [
                                {
                                    'UserId': account_number
                                }
                            ]
                        }
                    )
        ec2.modify_image_attribute(
            ImageId=ami_id,
            LaunchPermission={
                'Add': [
                    {
                        'UserId': account_number
                    }
                ]
            }
        )
        # Since Shared AMIs to another account does NOT copy tags we
        #  need to get and re-add the tags to the shared account
        # @TODO this is tech debt, 'DELIVERY-PIPELINE-LAMBDA-AWS' role is too generic might be smited later
        assumed_credentials = assume_role(
            account_number,
            'DELIVERY-PIPELINE-LAMBDA-AWS'
        )
        set_resource_tags(tags, ami_id, assumed_credentials)
    except Exception as e:
        raise Exception(f"Failed to share ami {ami_id} to account {account_number}, error: {e}")
