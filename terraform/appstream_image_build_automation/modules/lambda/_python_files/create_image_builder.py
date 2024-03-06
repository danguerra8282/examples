import logging
import boto3
import os
import botocore

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Setup Connections
try:
    session = boto3.Session()
    app_stream_client = session.client('appstream')
except Exception as e:
    print(f'Failed setting up connections')
    print(f'e: {e}')
    raise e

def lambda_handler(event, context):
    logger.info("Beginning execution of create_image_builder function.")

    # Retrieve starting parameters from event data
    # If parameter not found, inject default values defined in Lambda function
    if 'ImageBuilderName' in event:
        ib_name = event['ImageBuilderName']
    else:
        ib_name = os.environ['default_ib_name']

    if 'ImageBuilderImage' in event:
        ib_image = event['ImageBuilderImage']
    else:
        ib_image = os.environ['default_image']

    if 'ImageBuilderType' in event:
        ib_type = event['ImageBuilderType']
    else:
        ib_type = os.environ['default_type']

    if 'ImageBuilderSubnet' in event:
        ib_subnet = event['ImageBuilderSubnet']
    else:
        ib_subnet = os.environ['default_subnet']

    if 'ImageBuilderSecurityGroup' in event:
        ib_sg = event['ImageBuilderSecurityGroup']
    else:
        ib_sg = os.environ['default_security_group']

    if 'ImageBuilderIAMRole' in event:
        ib_role = event['ImageBuilderIAMRole']
    else:
        ib_role = os.environ['default_role']

    if 'ImageBuilderDomain' in event:
        ib_domain = event['ImageBuilderDomain']
    else:
        ib_domain = os.environ['default_domain']

    if 'ImageBuilderOU' in event:
        ib_ou = event['ImageBuilderOU']
    else:
        ib_ou = os.environ['default_ou']

    if 'ImageBuilderDisplayName' in event:
        ib_display_name = event['ImageBuilderDisplayName']
    else:
        ib_display_name = os.environ['default_display_name']

    if 'ImageBuilderDescription' in event:
        ib_description = event['ImageBuilderDescription']
    else:
        ib_description = os.environ['default_description']

    if 'ImageBuilderInternetAccess' in event:
        ib_internet = event['ImageBuilderInternetAccess']
    else:
        ib_internet = False

    if 'ImageOutputPrefix' in event:
        ib_prefix = event['ImageOutputPrefix']
    else:
        ib_prefix = os.environ['default_prefix']

    if 'ImageTags' in event:
        image_tags = event['ImageTags']
    else:
        image_tags = False

    if 'use_latest_agent' in event:
        use_latest_agent = event['UseLatestAgent']
    else:
        use_latest_agent = True

    if 'delete_builder' in event:
        delete_builder = event['DeleteBuilder']
    else:
        delete_builder = False

    if 'deploy_method' in event:
        deploy_method = event['DeployMethod']
    else:
        deploy_method = os.environ['default_method']

    if 'image_builder_extra_commands' in event:
        image_builder_extra_commands = event['ImageBuilderCommands']
    else:
        image_builder_extra_commands = False

    if 'PackageS3Bucket' in event:
        package_s3_bucket = event['PackageS3Bucket']
    else:
        package_s3_bucket = os.environ['default_s3_bucket']

    if 'notify_arn' in event:
        notify_arn = event['NotifyARN']
    else:
        notify_arn = False

    try:
        # Checking for existing Image Builder with same name   
        logger.info("Checking for existing Image Builder: %s.", ib_name)
        response = app_stream_client.describe_image_builders(
            Names=[
                ib_name,
            ],
            MaxResults=1
        )

        logger.info(
            "Builder already exists, skipping creation and reconfiguring input parameters to match existing builder.")

        # Reconfigure variables to values from existing Image Builder
        builder_name = ib_name
        ib_type = response['ImageBuilders'][0]['InstanceType']
        ib_image = response['ImageBuilders'][0]['ImageArn']
        ib_subnet = response['ImageBuilders'][0]['VpcConfig']['SubnetIds'][0]
        ib_sg = response['ImageBuilders'][0]['VpcConfig']['SecurityGroupIds'][0]
        ib_role = response['ImageBuilders'][0]['IamRoleArn']
        if 'DomainJoinInfo' in response['ImageBuilders'][0]:
            ib_domain = response['ImageBuilders'][0]['DomainJoinInfo']['DirectoryName']
            ib_ou = response['ImageBuilders'][0]['DomainJoinInfo']['OrganizationalUnitDistinguishedName']
        else:
            ib_domain = "none"
            ib_ou = "none"
        ib_display_name = response['ImageBuilders'][0]['DisplayName']
        ib_description = response['ImageBuilders'][0]['Description']
        ib_internet = response['ImageBuilders'][0]['EnableDefaultInternetAccess']
        builder_state = response['ImageBuilders'][0]['State']

        pre_existing_builder = True

    except (Exception,):
        logger.info("Image Builder does not exist, beginning creation of new Image Builder.")
        try:
            if ib_domain == 'none' or ib_ou == 'none':
                logger.info("Creating Image Builder without joining an AD domain.")
                response = app_stream_client.create_image_builder(
                    Name=ib_name,
                    ImageName=ib_image,
                    InstanceType=ib_type,
                    Description=ib_description,
                    DisplayName=ib_display_name,
                    VpcConfig={
                        'SubnetIds': [
                            ib_subnet,
                        ],
                        'SecurityGroupIds': [
                            ib_sg,
                        ]
                    },
                    IamRoleArn=ib_role,
                    EnableDefaultInternetAccess=ib_internet,
                    AppstreamAgentVersion='LATEST',
                    Tags={
                        'Automated': 'True'
                    }
                )
            else:
                logger.info("Creating Image Builder in specified AD domain: %s.", ib_domain)
                response = app_stream_client.create_image_builder(
                    Name=ib_name,
                    ImageName=ib_image,
                    InstanceType=ib_type,
                    Description=ib_description,
                    DisplayName=ib_display_name,
                    VpcConfig={
                        'SubnetIds': [
                            ib_subnet,
                        ],
                        'SecurityGroupIds': [
                            ib_sg,
                        ]
                    },
                    IamRoleArn=ib_role,
                    EnableDefaultInternetAccess=ib_internet,
                    DomainJoinInfo={
                        'DirectoryName': ib_domain,
                        'OrganizationalUnitDistinguishedName': ib_ou
                    },
                    AppstreamAgentVersion='LATEST',
                    Tags={
                        'Automated': 'True'
                    }
                )

            builder_name = response['ImageBuilder']['Name']
            builder_arn = response['ImageBuilder']['Arn']

            logger.info("Created new Image Builder with ARN: %s.", builder_arn)

            pre_existing_builder = False

        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                logger.error(error)
                logger.info("Image Builder Already Exists, moving on to next step.")
                builder_name = ib_name
            else:
                logger.error(error)
                raise error

        except Exception as e:
            logger.error(e)
            raise e

    logger.info("Completed AS2_Automation_Windows_Create_Builder function, returning to Step Function.")
    return {
        "AutomationParameters": {
            'ImageBuilderName': builder_name,
            'ImageBuilderType': ib_type,
            'ImageBuilderImage': ib_image,
            'ImageBuilderSubnet': ib_subnet,
            'ImageBuilderSecurityGroup': ib_sg,
            'ImageBuilderIAMRole': ib_role,
            'ImageBuilderDomain': ib_domain,
            'ImageBuilderOU': ib_ou,
            'ImageBuilderDisplayName': ib_display_name,
            'ImageBuilderDescription': ib_description,
            'ImageBuilderInternetAccess': ib_internet,
            'image_builder_extra_commands': image_builder_extra_commands,
            'ImageOutputPrefix': ib_prefix,
            'ImageTags': image_tags,
            'UseLatestAgent': use_latest_agent,
            'DeployMethod': deploy_method,
            'DeleteBuilder': delete_builder,
            'PreExistingBuilder': pre_existing_builder,
            'PackageS3Bucket': package_s3_bucket,
            'notify_arn': notify_arn
        }
    }