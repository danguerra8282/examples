"""
Description:
  This script will set all EC2 instances in an account to the specified Metadata Version.
  For security purposes this should be set to Metadata Version 2.
"""

import boto3
from colorama import Fore

# CONST
METADATA_VERSION = 2


def main():

    # Setup Connections
    try:
        session = boto3.Session()
        ec2_client = session.client('ec2')
    except Exception as e:
        print(f'Failed setting up connections')
        print(f'e: {e}')
        raise e

    # Get EC2 Instance Ids
    try:
        instance_ids = []
        response = ec2_client.describe_instances()
        for res in response['Reservations']:
            for instance_id in res['Instances']:
                instance_ids.append(instance_id['InstanceId'])
    except Exception as e:
        print(f'Failed getting EC2 instance_ids')
        print(f'e: {e}')
        raise e

    # Get Instance Metadata Versions
    for instance_id in instance_ids:
        try:
            metadata_version = ec2_client.describe_instances(
                InstanceIds=[
                    instance_id,
                ],
            )
            instance_state = metadata_version['Reservations'][0]['Instances'][0]['State']['Name']
            metadata_version = metadata_version['Reservations'][0]['Instances'][0]['MetadataOptions']['HttpTokens']

            print(instance_id)
            if metadata_version == 'optional':
                print(Fore.RED + '   metadata: v1' + Fore.RESET)
                if instance_state != 'terminated':
                    print(Fore.RED + '   Setting metadata to: v' + str(METADATA_VERSION) + Fore.RESET)
                    change_metadata_versions(
                        ec2_client,
                        instance_id,
                        METADATA_VERSION
                    )
            elif metadata_version == 'required':
                print('   metadata: v2')
            print()
        except (Exception,):
            print()


def change_metadata_versions(
        ec2_client,
        instance_id,
        metadata_version
):
    if metadata_version == 1:
        http_token = 'optional'
    elif metadata_version == 2:
        http_token = 'required'
    else:
        print('Error: !!! Invalid Metadata Version Specified !!!')
        print('Defaulting to Metadata v2 for Security Best Practices')
        http_token = 'required'

    ec2_client.modify_instance_metadata_options(
        InstanceId=instance_id,
        HttpTokens=http_token
    )


if __name__ == "__main__":
    main()
