"""
Description:
  This script will check all EC2 instances in an account and will report back their Metadata Versions.
  This can be used to identify if any instance is still on Metadata Version 1.
"""

import boto3
from colorama import Fore


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
            metadata_version = metadata_version['Reservations'][0]['Instances'][0]['MetadataOptions']['HttpTokens']
            print(instance_id)
            if metadata_version == 'optional':
                print(Fore.RED + '   metadata: v1' + Fore.RESET)
            elif metadata_version == 'required':
                print('   metadata: v2')
            print()
        except (Exception,):
            print()


if __name__ == "__main__":
    main()
