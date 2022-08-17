"""
===================================================
| DELIVERY PIPELINE LAMBDAS | CreateFileGateway   |
===================================================

This lambda is a custom resource that creates a file gateway in the specified account.

Sample CFN call:
  rFileGateway:
    Type: Custom::CreateFileGateway
    Properties:
      ServiceToken: !Sub arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:CreateFileGateway
      AccountNumber: !GetAtt rGetAccountInfo.oAccountID
      AccountName: !Sub "${pEnvironment}${pBusinessUnit}"
      UniqueName: !Ref pUniqueName
      DisbursementCode: !Ref pDisbursementCode
      ResourceOwner: !Ref pResourceOwner
"""

from urllib.parse import urlparse, parse_qs
import json
import sys
import time
import requests
from common import aws_credential_helper, cfnresponse

######## GLOBALS ##############
IN_ACCOUNT_ROLE_NAME = 'DELIVERY-PIPELINE-LAMBDA-AWS'
JOIN_USER = 'asdfasdf'
ROUTE53_HOSTED_ZONE = 'asdfasdfasdf'

######### LOGGING ###############
from common.custom_logging import CustomLogger
logger = CustomLogger().logger


def lambda_handler(event, context):
    """Main function, triggered by CloudFormation on use of this custom resource"""

    logger.info(json.dumps(event))

    response_data = dict()

    try:
        account_number = event['ResourceProperties']['AccountNumber']
        account_name = event['ResourceProperties']['AccountName']
        unique_name = event['ResourceProperties']['UniqueName']
        disbursement_code = event['ResourceProperties']['DisbursementCode']
        resource_owner = event['ResourceProperties']['ResourceOwner']
    except KeyError:
        logger.error("Missing a required property, should have AccountNumber, AccountName, and UniqueName.")
        response_data['ERROR'] = "Missing a required property, should have AccountNumber, AccountName, and UniqueName."
        cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
        return

    # Define variables used by multiple operation types
    sg_name = f"{unique_name}-{account_name}"
    stack_name = f"StorageGateway-{sg_name}"

    try:
        # Assume role into destination account and create boto3 clients
        assumed_credentials = aws_credential_helper.assume_role(account_number, IN_ACCOUNT_ROLE_NAME)

        cfn_client = aws_credential_helper.boto3_client('cloudformation', assumed_credentials=assumed_credentials)
        sg_client = aws_credential_helper.boto3_client('storagegateway', assumed_credentials=assumed_credentials)
    except KeyError:
        logger.error(f"Failed to assume into {IN_ACCOUNT_ROLE_NAME} in {account_number}...")
        response_data['ERROR'] = f"Failed to assume into {IN_ACCOUNT_ROLE_NAME} in {account_number}..."
        cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
        return

    # Delete operation
    if event['RequestType'] == "Delete":
        logger.info(f"Deleting storage gateway: {sg_name}")
        try:
            # Get the gateway arn from Export stack before deleting
            gateway_arn = ""
            paginator = cfn_client.get_paginator('list_exports')
            for page in paginator.paginate():
                for item in page['Exports']:
                    if item['Name'] == sg_name:
                        gateway_arn = item['Value']

            # Delete the CFN export and instance stacks
            cfn_client = aws_credential_helper.boto3_client('cloudformation', assumed_credentials=assumed_credentials)

            cfn_client.delete_stack(
                StackName=f"{stack_name}-Export"
            )

            cfn_client.delete_stack(
                StackName=stack_name
            )

            # Delete the storage gateway instance
            if gateway_arn:
                sg_client.delete_gateway(
                    GatewayARN=gateway_arn
                )
            else:
                logger.error("Failed to delete the storage gateway instance, could not find ARN...")

            cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, "CustomResourcePhysicalID")
            return
        except Exception as e:
            response_data['ERROR'] = str(e)
            logger.error(f"Failed to delete {sg_name} in {account_name}")
            logger.error(str(e))
            cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
            return

    # Update operation
    if event['RequestType'] == "Update":
        logger.error("This function does not currently support the updating operation, returning success.")
        cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, "CustomResourcePhysicalID")

    # Create operation
    try:
        # Create storage gateway...
        with open(f'{sys.path[0]}/storageGateway.yaml', 'r') as f:
            cfn_template = f.read()

        with open(f'{sys.path[0]}/storageGatewayExport.yaml', 'r') as f:
            export_template = f.read()

        logger.info(f"Creating storage gateway in {account_name}({account_number}) named {sg_name}...")

        # Create the storage gateway ec2 instance
        gateway_ip = create_storage_gateway_instance(
            cfn_client,
            account_name,
            cfn_template,
            stack_name,
            sg_name,
            disbursement_code,
            resource_owner
        )

        # Get the activation id of the file gateway
        activation_id = get_activation_id(gateway_ip)

        # Activate the storage gateway
        logger.info(f"Activating the storage gateway into the account with id: {activation_id}")
        gateway_arn = sg_client.activate_gateway(
            ActivationKey=activation_id,
            GatewayName=sg_name,
            GatewayTimezone='GMT-5:00',
            GatewayRegion='us-east-1',
            GatewayType='FILE_S3'
        )['GatewayARN']
        logger.info(f"Gateway activated, ARN: {gateway_arn}")

        # Add cache disk to storage gateway
        logger.info("Waiting a few minutes for gateway to become fully active...")
        time.sleep(200)

        logger.info(f"Adding cache disk /dev/sdf to gateway: {gateway_arn}...")
        disk_id = sg_client.list_local_disks(
            GatewayARN=gateway_arn
        )['Disks'][0]['DiskId']

        _ = sg_client.add_cache(
            GatewayARN=gateway_arn,
            DiskIds=[disk_id]
        )

        # Set SMB guest password
        logger.info(f"Setting SMB guest password for storage gateway to standard...")
        _ = sg_client.set_smb_guest_password(
            GatewayARN=gateway_arn,
            Password='domainGuestSMB!'
        )

        # Join storage gateway to the domain
        join_to_domain(gateway_arn, sg_client)

        # Create export stack for global oStorageGatewayARN value
        cfn_client.create_stack(
            StackName=f"{stack_name}-Export",
            TemplateBody=export_template,
            Parameters=[
                {
                    'ParameterKey': 'pStorageGatewayName',
                    'ParameterValue': sg_name
                },
                {
                    'ParameterKey': 'pStorageGatewayArn',
                    'ParameterValue': gateway_arn
                }
            ]
        )

        # Create cname for the storage gateway to simplify connectivity
        create_cname(sg_name, gateway_ip)

        logger.info(f"All operations completed, Storage Gateway in {account_name} is ready for use.")

        cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, "CustomResourcePhysicalID")
    except Exception as e:
        response_data['ERROR'] = str(e)
        logger.error(str(e))
        cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
        return


def create_storage_gateway_instance(
        cfn_client: object,
        account_name: str,
        cfn_template: str,
        stack_name: str,
        sg_name: str,
        disbursement_code: str,
        resource_owner: str
) -> str:
    """
    Creates the storage gateway Ec2 instance using CFN file packaged with the function.

    :param cfn_client: CFN boto3 client to use to create the stack
    :param account_name: Name of the account the SG is being created in
    :param cfn_template: Template body of the CFN file packaged with the function
    :param stack_name: Name of the CFN stack to use
    :param sg_name: Name of the storage gateway
    :param disbursement_code: Disbursement code the instance should be billed to
    :param resource_owner: ID of the owner of the resource
    :return: Private IP address of the EC2 instance
    """
    logger.info(f"Launching CloudFormation stack {stack_name} to create instance, role, and security group...")

    # Launch cloudformation stack
    stack_id = cfn_client.create_stack(
        StackName=stack_name,
        TemplateBody=cfn_template,
        Parameters=[
            {
                'ParameterKey': 'pProductName',
                'ParameterValue': sg_name
            },
            {
                'ParameterKey': 'pEnvironment',
                'ParameterValue': account_name
            },
            {
                'ParameterKey': 'pDisbursementCode',
                'ParameterValue': disbursement_code
            },
            {
                'ParameterKey': 'pResourceOwner',
                'ParameterValue': resource_owner
            },
            {
                'ParameterKey': 'pResourceName',
                'ParameterValue': sg_name
            }
        ],
        Capabilities=['CAPABILITY_NAMED_IAM']
    )['StackId']

    # Wait for stack to finish creation
    logger.info(f"Waiting for stack {stack_name} to complete..")
    waiter = cfn_client.get_waiter('stack_create_complete')
    waiter.wait(
        StackName=stack_name
    )

    # Get outputs from stack
    response = cfn_client.describe_stacks(
        StackName=stack_name
    )

    gateway_ip = ""

    for item in response['Stacks'][0]['Outputs']:
        if item['OutputKey'] == 'oInstancePrivateIp':
            gateway_ip = item['OutputValue']
            break

    logger.info("Stack creation completed with the following values: ")
    logger.info(f"StackName: {account_name}-StorageGateway")
    logger.info(f"Stackid: {stack_id}")
    logger.info(f"Gateway IP Address: {gateway_ip}")

    return gateway_ip


def get_activation_id(gateway_ip: str) -> str:
    """
    Uses requests to hit the storage gateway appliance's API to get its activation ID

    :param gateway_ip: IP address of the storage gateway ec2 instance
    :return: Activation ID received from the EC2 instance
    """
    logger.info("Waiting a few minutes for instance to finish booting...")
    time.sleep(200)

    logger.info(f"Getting activation id from instance with IP: {gateway_ip}...")

    try:
        response = requests.get(f'http://{gateway_ip}')
        url = response.url

        if "activationKey" in url:
            url = urlparse(url)
            params = parse_qs(url.query)

            logger.info(f"Found activation key: {params['activationKey'][0]}")

            return params['activationKey'][0]
        else:
            logger.info(f"Did not find activationKey in redirected URL: {url}")
            raise Exception(f"Did not find activationKey in redirected URL: {url}")
    except Exception:
        logger.info(f"Did not find activationKey in redirected URL: {url}")
        raise Exception(f"Did not find activationKey in redirected URL: {url}")


def create_cname(sg_name: str, gateway_ip: str) -> None:
    """
    Creates a Cname for the storage gateway appliance of storagegateway-SGNAME.aws.e1.domain.net

    :param sg_name: Name of the storage gateway appliance
    :param gateway_ip: IP address of the storage gateway instance
    :return: None
    """
    logger.info(f"Creating CNAME for gateway of storagegateway-{sg_name.lower()}.aws.e1.domain.net. -> {gateway_ip}...")

    client = aws_credential_helper.boto3_client('route53')

    wait_time = 1
    while True:
        try:
            _ = client.change_resource_record_sets(
                HostedZoneId=ROUTE53_HOSTED_ZONE,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': "UPSERT",
                            'ResourceRecordSet': {
                                'Name': f'storagegateway-{sg_name.lower()}.aws.e1.domain.net.',
                                'Type': 'A',
                                'TTL': 300,
                                'ResourceRecords': [
                                    {
                                        'Value': gateway_ip
                                    }
                                ]
                            }
                        }
                    ]
                }
            )
            break
        except Exception as e:
            if "Throttling" in str(e):
                time.sleep(wait_time)
                wait_time += wait_time
                continue
            elif "PriorRequestNotComplete" in str(e):
                time.sleep(wait_time)
                wait_time += wait_time
                continue
            else:
                logger.info(f"Failed to create CNMAME: {str(e)}")
                exit(2)


def join_to_domain(gateway_arn: str, sg_client: object) -> None:
    """
    Joins the storage gateway instance to the domain to allow for domain auth on SMB file shares

    :param gateway_arn: ARN of the storage gateway instance
    :param sg_client: Boto3 storagegateway client to use for SG modification
    :return: None
    """
    client = aws_credential_helper.boto3_client('ssm')

    response = client.get_parameters(
        Names=['domain_srvinstl_password'],
        WithDecryption=True
    )
    bind_password = response['Parameters'][0]['Value']

    logger.info("Joining storage gateway to domain.net domain...")

    sg_client.join_domain(
        GatewayARN=gateway_arn,
        DomainName='domain.net',
        OrganizationalUnit='ou=1,ou=2,ou=3,dc=domain,dc=com',
        # DomainControllers=[
        #     '1.2.3.4',
        #     '5.6.7.8'
        # ],
        UserName=JOIN_USER,
        Password=bind_password
    )
