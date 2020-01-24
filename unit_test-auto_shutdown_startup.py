import boto3
import datetime
import time


def main():
    print('Starting Auto_Shutdown_Startup Unit Test')

    # CONSTANTS
    S3_BUCKET = '-lambda-functions-bucket-test'
    LAMBDA_TO_CLONE = 'lambda_auto_shutdown_startup.zip'
    TIME_ZONE_ADJUSTMENT = 5

    # Setup Connections
    try:
        session = boto3.Session()
        ec2_client = session.client('ec2')
        lambda_client = session.client('lambda')
    except Exception as e:
        print('Failed to create session and connections')
        raise e

    # Get time for setting AutoShutDown Tag and adjust if with 2 minutes of the hour
    try:
        current_time = datetime.datetime.now()
        if (60 - int(current_time.minute)) < 3:
            auto_shutdown_time = current_time.hour + 1
            # CodeBuild containers use UTC...so adjust the time
            auto_shutdown_time = auto_shutdown_time - TIME_ZONE_ADJUSTMENT
            if auto_shutdown_time < 0:
                auto_shutdown_time = 24 + auto_shutdown_time    # + because its a double negative...
            auto_startup_time = auto_shutdown_time
        else:
            auto_shutdown_time = current_time.hour
            # CodeBuild containers use UTC...so adjust the time
            auto_shutdown_time = auto_shutdown_time - TIME_ZONE_ADJUSTMENT
            if auto_shutdown_time < 0:
                auto_shutdown_time = 24 + auto_shutdown_time  # + because its a double negative...
            auto_startup_time = auto_shutdown_time
        print(f'auto_shutdown_time: {auto_shutdown_time}')
        print(f'auto_startup_time: {auto_startup_time}')
    except Exception as e:
        print('Failed identifying auto_shutdown_time & auto_startup_time')
        print(f'e: {e}')
        raise e

    ############################################################################
    # THIS SECTION IS NOT CURRENTLY BEING USED BUT MAY BE NEEDED IN THE FUTURE #
    ############################################################################
    # # Create a clone of the auto_shutdown_startup lambda
    # try:
    #     print()
    #     lambda_templates = get_s3_contents(
    #         s3_client,
    #         S3_BUCKET,
    #         LAMBDA_TO_CLONE
    #     )
    #     print(f'lambda_templates: {lambda_templates}')
    #
    #     # Verify only 1 template was found.  Otherwise FAIL
    #     if len(lambda_templates) > 1:
    #         print(f'FAILED - Multiple lambda_templates found.  {lambda_templates}')
    #         exit(1)
    #
    #     # Download and Modify the lambda
    #     downloaded_file = s3_client.download_file(
    #         Bucket=S3_BUCKET,
    #         Key=lambda_templates[0],
    #         Filename='/tmp/' + LAMBDA_TO_CLONE
    #     )
    #
    #     print(f'Unzipping: {LAMBDA_TO_CLONE}')
    #     #     with zipfile.ZipFile('/tmp/' + LAMBDA_TO_CLONE, 'r') as zip_ref:
    #     #         zip_ref.extractall('/tmp/unzipped')
    #     #     lambda_file = (LAMBDA_TO_CLONE.split('.', 1)[0]) + '.py'
    #     #
    #     #     print(f'Modifying: {lambda_file}')
    #
    # except Exception as e:
    #     print('Failed creating lambda clone')
    #     print(f'e: {e}')
    #     raise e
    ############################################################################

    # Get most recently created amazon ami
    try:
        ami_to_use = get_latest_public_ami(
            ec2_client,
            'amzn-ami-hvm-*'
        )
    except Exception as e:
        print('Failed getting latest public ami')
        print(f'e: {e}')
        raise e

    # Create EC2 Instance for Shutdown Test
    try:
        print('Creating EC2 Instance for Shutdown Test...')
        response = ec2_client.run_instances(
            ImageId=ami_to_use,
            InstanceType='t2.micro',
            MaxCount=1,
            MinCount=1,
            SubnetId='subnet-xxx',
            SecurityGroupIds=[
                'sg-xxx',
            ],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'unit_test-auto_shutdown_startup - Shutdown Test'
                        },
                        {
                            'Key': 'Team',
                            'Value': 'Cloud Transformation'
                        },
                        {
                            'Key': 'BusinessUnit',
                            'Value': 'Cloud Transformation'
                        },
                        {
                            'Key': 'Owner',
                            'Value': 'Cloud Transformation'
                        },
                        {
                            'Key': 'AutoShutDown',
                            'Value': str(auto_shutdown_time)
                        },
                        {
                            'Key': 'AutoStartup',
                            'Value': 'False'
                        }
                    ]
                }
            ]
        )
        # print(f'response: {response}')
        for instances in response['Instances']:
            shutdown_test_instance_id = instances['InstanceId']
            print(f'shutdown_test_instance_id created: {shutdown_test_instance_id}')

    except Exception as e:
        print('Failed creating EC2 instance to test shutdown action')
        print(f'e: {e}')
        raise e

    # Create EC2 Instance for Startup Test
    try:
        print('Creating EC2 Instance for Startup Test...')
        response = ec2_client.run_instances(
            ImageId=ami_to_use,
            InstanceType='t2.micro',
            MaxCount=1,
            MinCount=1,
            SubnetId='subnet-xxx',
            SecurityGroupIds=[
                'sg-xxx',
            ],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'unit_test-auto_shutdown_startup - Startup Test'
                        },
                        {
                            'Key': 'Team',
                            'Value': 'Cloud Transformation'
                        },
                        {
                            'Key': 'BusinessUnit',
                            'Value': 'Cloud Transformation'
                        },
                        {
                            'Key': 'Owner',
                            'Value': 'Cloud Transformation'
                        },
                        {
                            'Key': 'AutoShutDown',
                            'Value': 'False'
                        },
                        {
                            'Key': 'AutoStartup',
                            'Value': str(auto_shutdown_time)
                        }
                    ]
                }
            ]
        )
        # print(f'response: {response}')
        for instances in response['Instances']:
            startup_test_instance_id = instances['InstanceId']
            print(f'startup_test_instance_id created: {startup_test_instance_id}')

        # Wait for instance creation
        instance_state = wait_for_instance_creation(
            startup_test_instance_id,
            ec2_client
        )
        print(f'{startup_test_instance_id} is now in a {instance_state} state')

        # Stop the startup_test_instance_id for testing startup
        ec2_client.stop_instances(
            InstanceIds=[startup_test_instance_id]
        )
        response = ec2_client.describe_instances(
            InstanceIds=[startup_test_instance_id]
        )
        state = response['Reservations'][0]['Instances'][0]['State']['Name']

        while 'stopped' not in state:
            print(f'Waiting for {startup_test_instance_id} to stop.  Checking again in 5 seconds...')
            time.sleep(5)
            response = ec2_client.describe_instances(
                InstanceIds=[startup_test_instance_id]
            )
            state = response['Reservations'][0]['Instances'][0]['State']['Name']
        print(f'{startup_test_instance_id} is now in a stopped state')

    except Exception as e:
        print('Failed creating EC2 instance to test startup action')
        print(f'e: {e}')
        raise e

    # Trigger auto_shutdown_startup lambda
    try:
        trigger_lambda_function(
            lambda_client,
            'auto-shutdown-startup',
            current_time,
            auto_shutdown_time,
            TIME_ZONE_ADJUSTMENT
        )
    except Exception as e:
        print('Failed to invoke auto_shutdown_startup lambda')
        print(f'e: {e}')
        raise e

    # Verify that EC2 auto_shutdown action occurred
    try:
        response = ec2_client.describe_instances(
            InstanceIds=[shutdown_test_instance_id]
        )
        state = response['Reservations'][0]['Instances'][0]['State']['Name']
        counter = 0
        while 'stopped' not in state:
            print(f'Waiting for shutdown test instance {shutdown_test_instance_id} to stop.  /'
                  f'Checking again in 10 seconds...')
            time.sleep(10)
            response = ec2_client.describe_instances(
                InstanceIds=[shutdown_test_instance_id]
            )
            state = response['Reservations'][0]['Instances'][0]['State']['Name']
            if counter > 30:
                print(f'FAILED - auto_shutdown')
                clean_up_after_test(
                    shutdown_test_instance_id,
                    ec2_client
                )
                clean_up_after_test(
                    startup_test_instance_id,
                    ec2_client
                )
                exit(1)
            counter += 1
        print(f'{shutdown_test_instance_id} is now in a stopped state')
    except Exception as e:
        print('FAILED - failure encountered during auto_shutdown test validation')
        print(f'e: {e}')
        raise e

    # Verify that EC2 auto_startup action occurred
    try:
        response = ec2_client.describe_instances(
            InstanceIds=[startup_test_instance_id]
        )
        state = response['Reservations'][0]['Instances'][0]['State']['Name']
        counter = 0
        while 'running' not in state:
            print(f'Waiting for startup test instance {startup_test_instance_id} to be running.  /'
                  f'Checking again in 10 seconds...')
            time.sleep(10)
            response = ec2_client.describe_instances(
                InstanceIds=[startup_test_instance_id]
            )
            state = response['Reservations'][0]['Instances'][0]['State']['Name']
            if counter > 30:
                print(f'FAILED - auto_shutdown')
                clean_up_after_test(
                    startup_test_instance_id,
                    ec2_client
                )
                exit(1)
            counter += 1
        print(f'{startup_test_instance_id} is now in a running state')
    except Exception as e:
        print('FAILED - failure encountered during auto_startup test validation')
        print(f'e: {e}')
        raise e

    # Cleanup after testing
    try:
        clean_up_after_test(
            shutdown_test_instance_id,
            ec2_client
        )
        clean_up_after_test(
            startup_test_instance_id,
            ec2_client
        )
        print('PASSED - Auto_Shutdown_Startup Unit Test')
    except Exception as e:
        print('Failed to cleanup instance during failed test')
        exit(1)
        raise e


def get_latest_public_ami(
        ec2_client,
        ami_to_retrieve
):
    """
    Gets the most recent public ami from AWS.  Based on AWS's creation date.
    :param ec2_client: boto3.client
    :param ami_to_retrieve: (string) Fuzzy search of the ami to search.  This accepts wildcards(*).
    :return: the most recent ami found
    """
    response = ec2_client.describe_images(
        Filters=[
            {
                'Name': 'name',
                'Values': [ami_to_retrieve]
            }
        ]
    )
    # print(f'response: {response}')
    images_dict = {}
    for image in response['Images']:
        images_dict.update({image['CreationDate']: image['ImageId']})
    print(f'images_dict: {images_dict}')

    # Sort by newest image and get the latest ami
    sorted_images_dict = sorted(images_dict.items(), key=lambda x: x[0])
    array_length = len(sorted_images_dict)
    ami_to_use = (sorted_images_dict[array_length - 1])[1]
    print(f'ami_to_use: {ami_to_use}')
    return ami_to_use


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
            print(f'{instance_id} still in pending state.  Checking again in 5 seconds...')
            time.sleep(5)
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


def trigger_lambda_function(
        lambda_client,
        function_name_filter,
        current_time,
        auto_shutdown_time,
        TIME_ZONE_ADJUSTMENT
):
    """
    Triggers a lambda function
    :param lambda_client: boto3.client
    :param function_name_filter: (string) the function to find and trigger
    :param current_time: (string) the current date_time
    :param auto_shutdown_time: (string) the defined auto_shutdown_time from the calling function.  This is specific
        to this script.  I know, bad programming...
    :return: None
    """
    print('Getting current auto_shutdown_startup function name...')
    response = lambda_client.list_functions()
    # print(f'response: {response}')
    function_to_trigger = ''
    for function in response['Functions']:
        if function_name_filter in function['FunctionName']:
            function_to_trigger = function['FunctionName']
    if function_to_trigger:
        print(f'function_to_trigger: {function_to_trigger}')
    else:
        print('Failed to identify function_to_trigger')
        exit(1)

    # Check to see if the test needs to wait until the next hour
    if auto_shutdown_time == (current_time.hour - TIME_ZONE_ADJUSTMENT):
        print('Triggering auto_shutdown_startup lambda')
        response = lambda_client.invoke(
            FunctionName=function_to_trigger
        )
    else:
        print('It is within 3 minutes of the next hour.  Waiting until the next hour to conduct the test.')
        current_time = datetime.datetime.now()
        wait_time = (60 - current_time.minute) * 60
        print(f'wait_time: {wait_time}')
        time.sleep(wait_time)
        print('Triggering auto_shutdown_startup lambda')
        response = lambda_client.invoke(
            FunctionName=function_to_trigger
        )


def clean_up_after_test(
        instance_id,
        ec2_client
):
    print(f'Cleaning up {instance_id}')
    ec2_client.terminate_instances(
        InstanceIds=[instance_id]
    )


main()
