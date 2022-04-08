# AWS Helper Functions

# pip install requests
import botocore
import json
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# CONST
TIME_ZONE_ADJUSTMENT = 5


def create_client_connection(
        resource_type,
        session,
        assumed_credentials
):
    """
    Creates an AWS client connection to the AWS resource provided
    :param resource_type: (string) AWS resource type
    :param session: (object) AWS session connection
    :param assumed_credentials: (object) AWS credentials object
    :return: specified client connection
    """
    client = session.client(
        resource_type,
        aws_access_key_id=assumed_credentials["Credentials"]['AccessKeyId'],
        aws_secret_access_key=assumed_credentials["Credentials"]['SecretAccessKey'],
        aws_session_token=assumed_credentials["Credentials"]['SessionToken'],
    )
    return client


def get_dynamo_table(
        dynamo_client,
        table_name
):
    """
    Gets value of a dynamo table
    :param dynamo_client: boto3.client
    :param table_name: the table to get
    :return: table values
    """
    dynamo_table_exists = dynamo_client.describe_table(
        TableName=table_name
    )
    if dynamo_table_exists:
        return dynamo_table_exists
    else:
        return False


def get_values_from_dynamo_column(
        dynamo_client,
        table_name,
        column_name,
        filter=None,
        filter_type=None
):
    """
    Searches and returns anything with the filter from dynamo
    :param dynamo_client: boto3.client
    :param table_name: (string) table to search
    :param column_name: (string) column to search
    :param filter: (string) optional value to filter on
    :param filter_type: (string) required if filter!=None;
        object type for the filter string
    :return array: array of strings
    """
    try:
        response = dynamo_client.scan(TableName=table_name)
    except Exception as e:
        raise e

    if filter:
        filtered_array = []
        for resp in response['Items']:
            try:
                if filter in resp['AccountName'][filter_type]:
                    for value in resp[column_name]:
                        filtered_array.append(resp[column_name][value])
            except Exception as e:
                raise e
        return filtered_array
    else:
        array = []
        for resp in response['Items']:
            try:
                if column_name in resp:
                    for value in resp[column_name]:
                        array.append(resp[column_name][value])
            except Exception as e:
                raise e
        return array


def put_value_in_dynamo_column(
        dynamo_client,
        table_name,
        primary_column_name,
        primary_data_type,
        primary_data_value,
        secondary_column_name,
        secondary_data_type,
        secondary_data_value,
        tertiary_column_name,
        tertiary_data_type,
        tertiary_data_value
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
    :param tertiary_column_name: other data column name
    :param tertiary_data_type: the other data column data type [S, N, B, SS, NS, BB, M, L]
    :param tertiary_data_value: the value to store in the other column
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
            },
            tertiary_column_name: {
                tertiary_data_type: tertiary_data_value
            }
        }
    )
    return response


def get_ecs_service_tag(
        ecs_client,
        ecs_service,
        searched_tag
):
    """
    Searches ECS Service
    :param ecs_client: boto3 client
    :param ecs_service: ECS Service to search
    :param searched_tag: the tag to search for
    :return: The value of the searched tag if found, else null value
    """
    response = None
    searched_tag = str(searched_tag).lower()
    tags = ecs_client.list_tags_for_resource(
        resourceArn=ecs_service
    )
    for tag in tags['tags']:
        tag_lowered = str(tag['key']).lower()
        if searched_tag == tag_lowered:
            response = tag.get('value')
    return response


def get_start_stop_time():
    """
    Gets the appropriate time to be assigned to the start/stop tag.  Adjusts by 2 minutes if too close to the hour.
    :return: (int) auto_startup_time, (int) auto_shutdown_time
    """
    current_time = datetime.datetime.now()
    if (60 - int(current_time.minute)) < 3:
        auto_shutdown_time = current_time.hour + 1
        # CodeBuild containers use UTC...so adjust the time
        auto_shutdown_time = auto_shutdown_time - TIME_ZONE_ADJUSTMENT
        if auto_shutdown_time < 0:
            auto_shutdown_time = 24 + auto_shutdown_time  # + because its a double negative...
        auto_startup_time = auto_shutdown_time
    else:
        auto_shutdown_time = current_time.hour
        # CodeBuild containers use UTC...so adjust the time
        auto_shutdown_time = auto_shutdown_time - TIME_ZONE_ADJUSTMENT
        if auto_shutdown_time < 0:
            auto_shutdown_time = 24 + auto_shutdown_time  # + because its a double negative...
        auto_startup_time = auto_shutdown_time
    return auto_startup_time, auto_shutdown_time


def delete_ecs_service(
        ecs_client,
        ecs_cluster,
        ecs_service,
        force_switch=False
):
    """
    Deletes an ECS Service and then verifies the Service is deleted before returning a response.
    :param ecs_client: boto3.client
    :param ecs_cluster: (string) ECS Cluster Name
    :param ecs_service: (string) ECS Service Name
    :param force_switch: Defaults to False.  Only True if using REPLICA scheduling strategy.
    :return: (bool) response once the service has been deleted
    """
    # Stop Tasks
    response = ecs_client.update_service(
            cluster=ecs_cluster,
            service=ecs_service,
            desiredCount=0
    )
    counter = 0
    while counter < 120:
        try:
            response = ecs_client.describe_services(
                cluster=ecs_cluster,
                services=[ecs_service]
            )
            if response['services'][0]['runningCount'] != 0:
                counter += 1
                time.sleep(5)
            else:
                counter = 121
        except:
            counter = 121
            return False

    # Delete Service
    response = ecs_client.delete_service(
        cluster=ecs_cluster,
        service=ecs_service,
        force=force_switch
    )
    if response:
        return True
    else:
        return False


def validate_required_tags(
        object_tags
):
    """
    Compares an array of tags passed in against the required_tags defined in the function.  All tags are
    lowered for comparision (it is not case sensitive).
    :param object_tags: (Array) The tag list from the object needing to be validated
    :return: (Array) A list of missing tags.  NULL (FALSE) value if none are missing
    """
    required_tags = [
        'ProductName',
        'Team',
        'BusinessUnit',
        'Owner'
    ]

    try:
        present_tags_array = []
        required_tags_missing = required_tags
        # print(f'In function object_tags: {object_tags}')
        for required_tag in required_tags:
            # required_tag_present = False
            # print(f'Checking for required_tag: {required_tag}')
            for tag in object_tags:
                if str(required_tag).lower() in str(tag['key']).lower():
                    if tag['value']:
                        # required_tag_present = True
                        present_tags_array.append(required_tag)
        # print(f'present_tags_array: {present_tags_array}')
        for item in present_tags_array:
            if item in required_tags:
                required_tags_missing.remove(item)
        return required_tags_missing
    except Exception as e:
        print(f'Failed validating tags')
        print(f'e: {e}')
        raise e


def send_email(
        email_send_to,
        email_subject,
        email_body,
        email_sender
):
    """
    Sends an email via mail servers.  The calling function MUST be running inside an VPC and IP space
    :param email_send_to: (String) The email address of the recipient
    :param email_subject: (String) The subject line for the email
    :param email_body: (String) The body/contents of the email
    :param email_sender: (String) The email address of the sender of the email
    :return: None
    """
    address_book = [email_send_to]
    msg = MIMEMultipart()
    subject = email_subject
    body = email_body

    msg['From'] = email_sender
    msg['To'] = ','.join(address_book)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    text = msg.as_string()
    print(text)

    # Send the message via our SMTP server
    s = smtplib.SMTP('mail.domain.com')
    s.sendmail(email_sender, address_book, text)
    s.quit()
