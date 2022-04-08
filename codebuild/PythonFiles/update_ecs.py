# Description:
#   - Updates ECS Task with new Container Image ID
#   - Updates ECS Service to use Updated ECS Task

# Import Modules
import boto3
import logging
import datetime
from datetime import datetime
import os
from botocore.config import Config

my_config = Config(
    region_name='us-east-1',
    signature_version='v4',
    retries={
        'max_attempts': 2,
        'mode': 'standard'
    }
)

# CONST
TASK_TO_FIND = 'info-cloud-rTaskDefinition-'
ECR_REPO = '_name_website'
ECS_CLUSTER = 'info-cloud'


def main():
    print()

    # username = '_user_name_'
    # path = '/Users/' + username + '/.AWS/credentials'
    # if os.path.exists(path):
    #     fp = open(path, 'r')
    #     profiles = [line for line in open(path) if '[' in line]
    #     fp.close()
    #     for profile in profiles:
    #         profile = profile.split('[')
    #         profile = profile[1].split(']')
    #         profile = profile[0]
    #         # print(profile)
    #
    #         if '_account_name_/CloudEngineer' in profile:
    #
    #             session = boto3.session.Session(profile_name=profile)

    # Setup Connections

    session = boto3.Session()
    ecs_client = session.client('ecs', config=my_config)
    ecr_client = session.client('ecr')

    # Get Latest ECR Image
    image_tag = ''
    try:
        image_tag = get_ecr_image(
            ecr_client,
            ECR_REPO
        )
        print(f'image_tag: {image_tag}')

        if 'latest' in image_tag:
            print(f'!!! FAILURE; IMAGE_TAG RETURNED WAS LATEST.  PLEASE INVESTIGATE!!!')
            exit(1)
    except Exception as e:
        print(f'Failed get_ecr_image')
        print(f'e: {e}')
        exit(1)

    # Get Task Definition
    last_task_definition = ''
    try:
        last_task_definition = get_task_definition(
            ecs_client,
            TASK_TO_FIND
        )
        print(f'last_task_definition: {last_task_definition}')
    except Exception as e:
        print(f'Failed get_task_definition')
        print(f'e: {e}')
        exit(1)

    # Describe last_task_definition
    family, name, image, cpu, memory, port_mappings, essential, log_configuration, task_role_arn, \
        execution_role_arn, network_mode, requires_compatibilities, tags = \
        '', '', '', '', '', '', '', '', '', '', '', '', ''
    try:
        family, name, image, cpu, memory, port_mappings, essential, log_configuration, task_role_arn, \
            execution_role_arn, network_mode, requires_compatibilities, tags = \
            describe_task_definition(
                ecs_client,
                last_task_definition
            )
    except Exception as e:
        print(f'Failed describe_task_definition')
        print(f'e: {e}')
        exit(1)

    # Create new image reference
    try:
        image = image.split(':')[0] + ':' + image_tag
        print(f'new image: {image}')
    except Exception as e:
        print(f'Failed Create New Image Reference')
        print(f'e: {e}')
        exit(1)

    # Create Task Definition
    new_task_definition = []
    try:
        new_task_definition = register_task_definition(
            ecs_client,
            family,
            name,
            image,
            cpu,
            memory,
            port_mappings,
            essential,
            log_configuration,
            task_role_arn,
            execution_role_arn,
            network_mode,
            requires_compatibilities,
            tags
        )

        new_task_definition = new_task_definition['taskDefinition']['taskDefinitionArn']
        print(f"new_task_definition: {new_task_definition}")

    except Exception as e:
        print(f'Failed register_task_definition')
        print(f'e: {e}')
        exit(1)

    # Update ECS Service to use new Task Definition
    try:
        ecs_services = ecs_client.list_services(
            cluster=ECS_CLUSTER
        )
        print(f"ecs_service: {ecs_services['serviceArns'][0]}")

        response = ecs_client.update_service(
            cluster=ECS_CLUSTER,
            service=ecs_services['serviceArns'][0],
            desiredCount=1,
            taskDefinition=new_task_definition
        )

        if response:
            print(f"ECS Service {ecs_services['serviceArns'][0]} has been successfully updated!")
        else:
            print(f"Failed updating {ecs_services['serviceArns'][0]}; exiting...")
            exit(1)

    except Exception as e:
        print(f'Failed Updating ECS Service')
        print(f'e: {e}')
        exit(1)


def get_ecr_image(
    ecr_client,
    ecr_repo
):
    """
    Gets the newest ECR Image
    :param ecr_client: boto3.client
    :param ecr_repo: The repo to search in
    :return: The newest image tag
    """
    # image_list = []
    image_tag = 'latest'
    images = ecr_client.list_images(
        repositoryName=ecr_repo
    )

    current_date = datetime.now()
    current_date = ('%02d' % current_date.day) + ('%02d' % current_date.month) + ('%04d' % current_date.year)

    for image in images['imageIds']:
        if current_date in image['imageTag']:
            image_tag = image['imageTag']

        # print(f"image: {image['imageTag']}")
        # image_list.append(image['imageTag'])

    # image_list.sort(reverse=True)

    # if 'latest' not in image_list[0]:
    #     image_tag = image_list[0]
    # else:
    #     image_tag = image_list[1]

    # if 'latest' not in images['imageIds'][0]['imageTag']:
    #     image_tag = images['imageIds'][0]['imageTag']
    # else:
    #     image_tag = images['imageIds'][1]['imageTag']

    return image_tag


def get_task_definition(
        ecs_client,
        task_to_find
):
    """
    Gets the most recent task definition
    :param ecs_client: boto3.client
    :param task_to_find: (String) Filter for the task to find
    :return: (Dict) The most recent task definition
    """
    definition_array = []
    all_tasks = ecs_client.list_task_definitions()
    # print(f'all_tasks: {all_tasks}')

    for task in all_tasks['taskDefinitionArns']:
        if task_to_find in task:
            definition_array.append(task)

    # print(f'definition_array: {definition_array}')
    last_task_definition = definition_array[-1]

    return last_task_definition


def describe_task_definition(
        ecs_client,
        last_task_definition
):
    """
    Gets values from the previous task definition
    :param ecs_client: boto3.client
    :param last_task_definition: (string) the task definition to get values from
    :return: (multiple strings) needed values for the new task definition
    """
    task_json = ecs_client.describe_task_definition(
        taskDefinition=last_task_definition,
        include=[
            'TAGS',
        ]
    )
    # print(f'task_json: {task_json}')
    family = task_json['taskDefinition']['family']
    name = task_json['taskDefinition']['containerDefinitions'][0]['name']
    image = task_json['taskDefinition']['containerDefinitions'][0]['image']  # Get this from codebuild?
    cpu = task_json['taskDefinition']['containerDefinitions'][0]['cpu']
    memory = task_json['taskDefinition']['containerDefinitions'][0]['memory']
    port_mappings = task_json['taskDefinition']['containerDefinitions'][0]['portMappings']
    essential = task_json['taskDefinition']['containerDefinitions'][0]['essential']
    log_configuration = task_json['taskDefinition']['containerDefinitions'][0]['logConfiguration']
    task_role_arn = task_json['taskDefinition']['taskRoleArn']
    execution_role_arn = task_json['taskDefinition']['executionRoleArn']
    network_mode = task_json['taskDefinition']['networkMode']
    requires_compatibilities = task_json['taskDefinition']['requiresCompatibilities']
    tags = task_json['tags']

    return family, name, image, cpu, memory, port_mappings, essential, log_configuration, task_role_arn, \
        execution_role_arn, network_mode, requires_compatibilities, tags


def register_task_definition(
        ecs_client,
        family,
        name,
        image,
        cpu,
        memory,
        port_mappings,
        essential,
        log_configuration,
        task_role_arn,
        execution_role_arn,
        network_mode,
        requires_compatibilities,
        tags
):
    """
    Creates a new ECS Task Definition
    :param ecs_client: boto3.client
    :param family: (string)
    :param name: (string)
    :param image: (string)
    :param cpu: (string)
    :param memory: (string)
    :param port_mappings: (string)
    :param essential: (string)
    :param log_configuration: (string)
    :param task_role_arn: (string)
    :param execution_role_arn: (string)
    :param network_mode: (string)
    :param requires_compatibilities: (string)
    :param tags: (string)
    :return: (dict) API response
    """
    response = ecs_client.register_task_definition(
        family=family,
        taskRoleArn=task_role_arn,
        executionRoleArn=execution_role_arn,
        networkMode=network_mode,
        containerDefinitions=[
            {
                'name': name,
                'image': image,
                'cpu': cpu,
                'memory': memory,
                'portMappings': port_mappings,
                'essential': essential,
                'logConfiguration': log_configuration,
            },
        ],
        requiresCompatibilities=requires_compatibilities,
        cpu=str(cpu),
        memory=str(memory),
        tags=tags
    )
    return response


main()
