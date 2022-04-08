"""
Description:    Shares an AWS AMI (EC2 image) to specified Business Unit accounts.  Business Unit accounts are pulled
                from the AWS Environments DynamoTable that the team maintains centrally.

Usage:           python encrypt_and_share_ami.py /
                    source-ami123 /
                    account123,account456,account789 /
                    destination-ami123 /
                    arn:aws:kms:us-east-1:123412341234:key/asdf-1234-qwer /
                    us-east-1
"""

import boto3
import os
import datetime
from datetime import datetime
import time
import sys
# import aep_aws_helper


def main():
    ami_to_share = sys.argv[1]
    account_numbers = sys.argv[2]
    encrypted_ami_name = sys.argv[3]
    kms_key = sys.argv[4]
    region = sys.argv[5]

    print('Attempting to share AMI# ' + ami_to_share + ' to ' + account_numbers)
    date_time = datetime.now()
    time_stamp = str(date_time.date()) + '_' + str(date_time.time())
    time_stamp = time_stamp.replace('-', '')
    time_stamp = time_stamp.replace(':', '')
    print(f'time_stamp: {time_stamp}')

    # Setup Connections
    try:
        # session = boto3.session.Session(profile_name=profile)
        session = boto3.Session()
        ec2_client = session.client('ec2')
        dynamo_client = session.client('dynamodb')

        print(f'ec2_client: {ec2_client}')

    except Exception as e:
        print('Failed to create session and connections')
        raise e

    # Encrypt Source AMI
    try:
        print(f'Encrypting ami...')
        response = ec2_client.copy_image(
            Encrypted=True,
            KmsKeyId=kms_key,
            Name=encrypted_ami_name + '-' + time_stamp,
            SourceImageId=ami_to_share,
            SourceRegion=region
        )
        print(f'response: {response}')
        new_ami = response['ImageId']
    except Exception as e:
        print('Error:  Failed encrypting ami')
        print(f'e: {e}')
        raise e

    # Wait for Encrypted AMI to be Available
    try:
        print()
        complete = False
        while not complete:
            print(f'Waiting for Encrypted AMI {new_ami} to be Available...')
            state = ec2_client.describe_images(
                ImageIds=[
                    new_ami,
                ],
            )
            state = state['Images'][0]['State']
            if state == 'available':
                print(f'{new_ami} is now Available')
                complete = True
            elif state == 'invalid' or state == 'deregistered' or state == 'failed' or state == 'error':
                print(f'Failed to encrypt AMI')
                exit(1)
            else:
                complete = False
                time.sleep(20)
    except Exception as e:
        print(f'e: {e}')
        raise e

    # Tag new_ami with source_ami information
    try:
        ec2_client.create_tags(
            Resources=[
                new_ami,
            ],
            Tags=[
                {
                    'Key': 'Built from Source AMI',
                    'Value': ami_to_share
                },
            ]
        )
    except Exception as e:
        print(f'Failed adding source_ami tags to {new_ami}')
        print(f'e: {e}')
        raise e

    # Share Encrypted AMI to accounts
    try:
        account_numbers = account_numbers.split(',')
        new_amis = []
        for account in account_numbers:
            resp = share_ami(
                ec2_client,
                new_ami,
                account
            )
            if resp:
                print(f'{new_ami} shared to {account} successfully')
                new_amis.append(new_ami)
                print(f'new_amis: {new_amis}')
    except Exception as e:
        print(f'Failed sharing {new_ami} to {account_numbers}')
        print(f'e: {e}')
        raise e

    # Add Encrypted AMIs to Approved_AMI DynamoTable
    try:
        print(f'Adding AMIs to Approved_AMI DynamoTable')
        for ami in new_amis:
            put_value_in_dynamo_column(
                dynamo_client,
                'Approved_AMIs',
                'ami_id',
                'S',
                ami,
                'ami_name',
                'S',
                encrypted_ami_name + '-' + time_stamp
            )
            print(f'---> {ami} has been added to dynamo <---')

    except Exception as e:
        print(f'Failed adding AMIs to Approved_AMI DynamoTable')
        print(f'e: {e}')
        raise e


def share_ami(
        ec2_client,
        ami_number,
        account_number
):
    """
    Shares an AMI to the provided account
    :param ec2_client: boto3 client
    :param ami_number: the AMI to share
    :param account_number: the account to share to
    :return: bool
    """
    snapshot_info = ec2_client.describe_images(
        ImageIds=[ami_number]
    )
    images = snapshot_info['Images']
    for i in images:
        for b in i['BlockDeviceMappings']:
            if b.get('Ebs'):
                snapshot_id = b['Ebs']['SnapshotId']
                print(f'Sharing SnapshotId:{snapshot_id} to account {account_number}')
                ec2_client.modify_snapshot_attribute(
                    SnapshotId=snapshot_id,
                    CreateVolumePermission={
                        'Add': [
                            {
                                'UserId': account_number
                            }
                        ]
                    }
                )
    ec2_client.modify_image_attribute(
        ImageId=ami_number,
        LaunchPermission={
            'Add': [
                {
                    'UserId': account_number
                }
            ]
        }
    )
    return True


def put_value_in_dynamo_column(
        dynamo_client,
        table_name,
        primary_column_name,
        primary_data_type,
        primary_data_value,
        secondary_column_name,
        secondary_data_type,
        secondary_data_value
):
    """
    Adds information to a dynamo table.  WARNING: This will overwrite any previously existing record.
    :param dynamo_client: boto3.client
    :param table_name: the dynamo table name
    :param primary_column_name: the index column name
    :param primary_data_type: the index column data type [S, N, B, SS, NS, BB, M, L]
    :param primary_data_value: the value to store in the index column
    :param secondary_column_name: other data column name
    :param secondary_data_type: the other data column data type [S, N, B, SS, NS, BB, M, L]
    :param secondary_data_value: the value to store in the other column
    :return dict: API call response
    """
    response = dynamo_client.put_item(
        TableName=table_name,
        Item={
            primary_column_name: {
                primary_data_type: primary_data_value
            },
            secondary_column_name: {
                secondary_data_type: secondary_data_value
            }
        }
    )
    return response


main()
