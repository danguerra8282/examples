import boto3
import datetime
from datetime import datetime
import time


def main():
    print('Starting Required_Tags Unit Test')

    # Setup Connections
    try:
        session = boto3.Session()
        ec2_client = session.client('ec2')
        # org_client = session.client('organizations')
    except Exception as e:
        print('Failed to create session and connections')
        raise e

    # Get Account ID
    # Hard code for now
    owner_account = '123456789'
    # try:
    #     response = org_client.list_accounts()
    #     print(f'response: {response}')
    # except Exception as e:
    #     print(f'Failed to get Account ID')
    #     raise e

    # Get AMI
    try:
        response = ec2_client.describe_images(
            Owners=[owner_account]
            # Owners=['self']
        )
        # print(f'response: {response}')
        images_dict = {}
        for image in response['Images']:
            images_dict.update({image['CreationDate']: image['ImageId']})
        print(f'images_dict: {images_dict}')

        # Sort by newest image
        sorted_images_dict = (sorted(images_dict.items(), key=lambda x: x[1]))
        ami_to_use = sorted_images_dict[0][1]
        print(f'ami_to_use: {ami_to_use}')

    except Exception as e:
        print('Failed getting AMI to deploy')
        raise e

    # Get Subnet for EC2 instance to use
    subnet = ec2_client.describe_subnets(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [
                    'xxx_subnet_name'
                ]
            },
        ]
    )
    subnet = subnet['Subnets'][0]['SubnetId']

    # Get Security Group for EC2 instance to use
    security_group = ec2_client.describe_security_groups(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [
                    'xxx_Security_Group'
                ]
            }
        ]
    )
    security_group = security_group['SecurityGroups'][0]['GroupId']

    # Create EC2 Instance with Valid Tags
    try:
        print('Creating EC2 Instance with Valid Tags...')
        response = ec2_client.run_instances(
            ImageId=ami_to_use,
            InstanceType='t2.medium',
            MaxCount=1,
            MinCount=1,
            SubnetId=subnet,
            SecurityGroupIds=[
                security_group,
            ],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'unit_test_required_tags - valid_tags'
                        },
                        {
                            'Key': 'Team',
                            'Value': 'xxx'
                        },
                        {
                            'Key': 'BusinessUnit',
                            'Value': 'xxx'
                        },
                        {
                            'Key': 'Owner',
                            'Value': 'xxx'
                        },
                        {
                            'Key': 'AutoShutDown',
                            'Value': '20'
                        }
                    ]
                }
            ]
        )
        # print(f'response: {response}')
        for instances in response['Instances']:
            instance_id = instances['InstanceId']
            print(f'EC2 instance created: {instance_id}')

        # Wait for instance to be created
        try:
            instance_state = wait_for_instance_creation(
                instance_id,
                ec2_client
            )
            print(f'instance_state: {instance_state}')

        except Exception as e:
            print(f'Failed identifying instance state for {instance_id}')
            try:
                clean_up_after_test(
                    instance_id,
                    ec2_client
                )
            except Exception as e:
                print('Failed to cleanup instance during failed test')
                raise e
            raise e

        # Check if test was passed/failed and cleanup from testing
        if 'running' in instance_state:
            print('PASSED - Required_Tags Unit Test for correctly tagged EC2 instance')
            try:
                clean_up_after_test(
                    instance_id,
                    ec2_client
                )

            except Exception as e:
                print('Failed to cleanup instance during failed test')
                raise e
        else:
            print('FAILED - Required_Tags Unit Test for correctly tagged EC2 instance')
            try:
                clean_up_after_test(
                    instance_id,
                    ec2_client
                )
                exit(1)
            except Exception as e:
                print('Failed to cleanup instance during failed test')
                raise e

    except Exception as e:
        print('Failed during EC2 instance creation')
        clean_up_after_test(
            instance_id,
            ec2_client
        )
        raise e

    # Create EC2 Instance with Missing Tags
    try:
        print('Creating EC2 Instance with Missing Tags...')
        response = ec2_client.run_instances(
            ImageId=ami_to_use,
            InstanceType='t2.medium',
            MaxCount=1,
            MinCount=1,
            SubnetId=subnet,
            SecurityGroupIds=[
                security_group,
            ],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'unit_test_required_tags - missing_tags'
                        }
                    ]
                }
            ]
        )
        # print(f'response: {response}')
        for instances in response['Instances']:
            instance_id = instances['InstanceId']
            print(f'EC2 instance created: {instance_id}')

        # Wait for instance to be created
        try:
            instance_state = wait_for_instance_creation(
                instance_id,
                ec2_client
            )
            print(f'instance_state: {instance_state}')

        except Exception as e:
            print(f'Failed identifying instance state for {instance_id}')
            try:
                clean_up_after_test(
                    instance_id,
                    ec2_client
                )
            except Exception as e:
                print('Failed to cleanup instance during failed test')
                raise e
            raise e

        # Check if test was passed/failed and cleanup from testing
        if 'stopped' in instance_state:
            print('PASSED - Required_Tags Unit Test for missing tags on an EC2 instance')
            try:
                clean_up_after_test(
                    instance_id,
                    ec2_client
                )
            except Exception as e:
                print('Failed to cleanup instance during failed test')
                raise e
        else:
            print('FAILED - Required_Tags Unit Test for missing tags on an EC2 instance')
            try:
                clean_up_after_test(
                    instance_id,
                    ec2_client
                )
            except Exception as e:
                print('Failed to cleanup instance during failed test')
                exit(1)
                raise e

    except Exception as e:
        print('Failed during EC2 instance creation')
        try:
            clean_up_after_test(
                instance_id,
                ec2_client
            )
        except Exception as e:
            print('Failed to cleanup instance during failed test')
            exit(1)
            raise e
        raise e


def wait_for_instance_creation(
        instance_id,
        ec2_client
):
    """
    Searches for an EC2 instance.
    :param instance_id: (string) InstanceId to search for
    :param ec2_client: boto3.client
    :return state: (string) of the instance's power state (running or stopped)
    """

    time.sleep(2)
    response = ec2_client.describe_instances(
        InstanceIds=[instance_id]
    )
    state = response['Reservations'][0]['Instances'][0]['State']['Name']

    while 'running' not in state:
        if 'pending' in state:
            print(f'{instance_id} still in pending state.  Checking again in 120 seconds...')
            time.sleep(120)
            response = ec2_client.describe_instances(
                InstanceIds=[instance_id]
            )
            state = response['Reservations'][0]['Instances'][0]['State']['Name']
        elif 'stopped' in state:
            print(f'{instance_id} is in a {state} state')
            return state
        elif 'running' in state:
            print(f'{instance_id} is in a {state} state')
            return state
        else:
            print(f'Waiting for instance state change to complete.  Checking again in 5 seconds...')
            time.sleep(5)
            response = ec2_client.describe_instances(
                InstanceIds=[instance_id]
            )
            state = response['Reservations'][0]['Instances'][0]['State']['Name']
    return state


def clean_up_after_test(
        instance_id,
        ec2_client
):
    print(f'Cleaning up {instance_id}')
    ec2_client.terminate_instances(
        InstanceIds=[instance_id]
    )


# Run main function
main()
