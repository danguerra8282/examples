# flask --app app --debug run

import boto3
import datetime
import time
from flask import Flask, render_template, request, redirect
app = Flask(__name__)


# CONST
DYNAMO_TABLE = 'ec2_disk_space'
NETWORK_ACCOUNT = 'update_me'
PROD_ACCOUNT = 'update_me'
ROLE_TO_ASSUME = 'update_me'

# Setup Connections
try:
    session = boto3.Session()
    ec2_client = session.client('ec2')
    dynamo_client = session.client('dynamodb')
    ce_client = session.client('ce')
    sts_client = session.client('sts')
    sts_client_us_west_2 = session.client('sts', region_name='us-west-2')
except Exception as e:
    print(f'Failed setting up connections')
    print(f'e: {e}')



############################################
################ WEBPAGES ##################
############################################

# Home Page
@app.route('/')
def home():
    info = '<h1><center>This website connects to the update_me AWS Accounts and returns information for centralized viewing.</center></h1>' \
        '<br>' \
        '<h3>Notes:</h3>' \
        '<div style="margin: 40px"><center> - EC2 Instances can be view in either a "Simple" or "Detailed" view.  \
            The "Detailed" view will take a little longer to populate.</center></div>'
    return render_template('home.html') + info

# Costs Page
@app.route('/costs/')
def costs():
    # # Check for Existing Data Already Stored (Limits API calls to Cost Explorer)
    # try:
    #     dynamo_data = dynamo_client.scan(
    #         TableName='account_costs'
    #     )
    #     # print(f'dynamo_data: {dynamo_data}')
    # except Exception as e:
    #     print(f'account_costs DynamoTable was not found')
    #     print(f'e: {e}')
    
    # network_data_found = True
    # non_prod_data_found = True
    # non_prod_data = None
    # prod_data_found = True
    
    # # Parse dynamo_data for Non-Prod info
    # try:
    #     for item in dynamo_data['Items']:
    #         if item['AccountName']['S'] == 'Non-Prod':
    #             non_prod_data = item['Data']['S']
    #         else:
    #             non_prod_data_found = False
    # except(Exception,):
    #     print(f'Non-Prod data not found in DynamoTable')
    
    # print(f'non_prod_data_found: {non_prod_data_found}')
    # print(f'non_prod_data: {non_prod_data}')

    time_array_daily, cost_array_daily = get_daily_costs(
        ce_client
    )

    network_cost_array_daily = get_daily_costs_cross_account(
        sts_client,
        NETWORK_ACCOUNT,
        NETWORK_ACCOUNT + ROLE_TO_ASSUME
    )

    production_cost_array_daily = get_daily_costs_cross_account(
        sts_client,
        PROD_ACCOUNT,
        PROD_ACCOUNT + ROLE_TO_ASSUME
    )

    labels_daily = time_array_daily
 
    data_non_prod_daily = cost_array_daily
    data_network_daily = network_cost_array_daily
    data_prod_daily = production_cost_array_daily

    time_array_monthly, cost_array_monthly = get_monthly_costs(
        ce_client
    )

    network_cost_array_monthly = get_monthly_costs_cross_account(
        sts_client,
        NETWORK_ACCOUNT,
        NETWORK_ACCOUNT + ROLE_TO_ASSUME
    )

    production_cost_array_monthly = get_monthly_costs_cross_account(
        sts_client,
        PROD_ACCOUNT,
        PROD_ACCOUNT + ROLE_TO_ASSUME
    )

    data_non_prod_monthly = cost_array_monthly
    data_prod_monthly = production_cost_array_monthly
    data_network_monthly = network_cost_array_monthly

    labels_monthly = time_array_monthly

    # # Write Data to DynamoTable
    # epoch_time = int(time.time())
    # response = dynamo_client.put_item(
    #     TableName='account_costs',
    #     Item={
    #         'AccountName': {
    #             'S': 'Non-Prod'
    #         },
    #         'TimeToExist': {
    #             'N': str(epoch_time + 28800)
    #         },
    #         'Data': {
    #             'S': str(data_non_prod_monthly)
    #         }
    #     }
    # )
 
    # Return the components to the HTML template
    return render_template(
        template_name_or_list='costs.html',
        data_prod_daily=data_prod_daily,
        data_non_prod_daily=data_non_prod_daily,
        data_network_daily=data_network_daily,
        labels_daily=labels_daily,
        data_non_prod_monthly=data_non_prod_monthly,
        data_network_monthly=data_network_monthly,
        data_prod_monthly=data_prod_monthly,
        labels_monthly=labels_monthly,
    )

# Security Events
@app.route('/security_events/')
def security_events():
    print(datetime.datetime.now())

    account_ids_array = []
    date_times_array = []
    security_alerts_array = []
    cloudtrail_event_ids_array = []

    #####################
    ### Local Account ###
    #####################

    # Check for DynamoTable
    try:
        dynamo_data = dynamo_client.scan(
            TableName='security_alerts'
        )
    except Exception as e:
        print(f'security_alerts DynamoTable was not found')
        print(f'e: {e}')

    # Parse DynamoTable for info
    try:
        for item in dynamo_data['Items']:
            # print(f'item: {item}')

            account_ids_array.append(item['Account_Id']['S'])
            date_times_array.append(item['DateTimeOccured']['S'])
            security_alerts_array.append(item['SecurityAlert']['S'])
            cloudtrail_event_ids_array.append(item['CloudTrailEventId']['S'])

            # print(f'account_ids_array: {account_ids_array}')
            # print(f'date_times_array: {date_times_array}')
            # print(f'security_alerts_array: {security_alerts_array}')
            # print(f'cloudtrail_event_ids_array: {cloudtrail_event_ids_array}')

    except Exception as e:
        print(f'In local account')
        print(f'e: {e}')

    ########################
    ### Network  Account ###
    ########################

    # Assume Credentials
    try:
        network_assumed_credentials = sts_client.assume_role(
            RoleArn=('arn:aws:iam::' + NETWORK_ACCOUNT + ':role/' + NETWORK_ACCOUNT + ROLE_TO_ASSUME),
            RoleSessionName='AssumedRole'
        )

        network_dynamo_client = session.client(
        'dynamodb',
        aws_access_key_id=network_assumed_credentials["Credentials"]['AccessKeyId'],
        aws_secret_access_key=network_assumed_credentials["Credentials"]['SecretAccessKey'],
        aws_session_token=network_assumed_credentials["Credentials"]['SessionToken'],
    )

    except Exception as e:
        print(f'Failed assuming role into Network Account')
        print(f'e: {e}')
        raise e
    
    # Check for DynamoTable
    try:
        dynamo_data = network_dynamo_client.scan(
            TableName='security_alerts'
        )
    except Exception as e:
        print(f'security_alerts DynamoTable was not found in Network Account')
        print(f'e: {e}')

    # Parse DynamoTable for info
    try:
        for item in dynamo_data['Items']:
            # print(f'item: {item}')

            account_ids_array.append(item['Account_Id']['S'])
            date_times_array.append(item['DateTimeOccured']['S'])
            security_alerts_array.append(item['SecurityAlert']['S'])
            cloudtrail_event_ids_array.append(item['CloudTrailEventId']['S'])

            # print(f'account_ids_array: {account_ids_array}')
            # print(f'date_times_array: {date_times_array}')
            # print(f'security_alerts_array: {security_alerts_array}')
            # print(f'cloudtrail_event_ids_array: {cloudtrail_event_ids_array}')

    except Exception as e:
        print(f'In Network account...')
        print(f'e: {e}')

    ###########################
    ### Production  Account ###
    ###########################

    # Assume Credentials
    try:
        prod_assumed_credentials = sts_client.assume_role(
            RoleArn=('arn:aws:iam::' + PROD_ACCOUNT + ':role/' + PROD_ACCOUNT + ROLE_TO_ASSUME),
            RoleSessionName='AssumedRole'
        )

        prod_dynamo_client = session.client(
        'dynamodb',
        aws_access_key_id=prod_assumed_credentials["Credentials"]['AccessKeyId'],
        aws_secret_access_key=prod_assumed_credentials["Credentials"]['SecretAccessKey'],
        aws_session_token=prod_assumed_credentials["Credentials"]['SessionToken'],
    )

    except Exception as e:
        print(f'Failed assuming role into Production Account')
        print(f'e: {e}')
        raise e
    
    # Check for DynamoTable
    try:
        dynamo_data = prod_dynamo_client.scan(
            TableName='security_alerts'
        )
    except Exception as e:
        print(f'security_alerts DynamoTable was not found in Production Account')
        print(f'e: {e}')

    # Parse DynamoTable for info
    try:
        for item in dynamo_data['Items']:
            # print(f'item: {item}')

            account_ids_array.append(item['Account_Id']['S'])
            date_times_array.append(item['DateTimeOccured']['S'])
            security_alerts_array.append(item['SecurityAlert']['S'])
            cloudtrail_event_ids_array.append(item['CloudTrailEventId']['S'])

            # print(f'account_ids_array: {account_ids_array}')
            # print(f'date_times_array: {date_times_array}')
            # print(f'security_alerts_array: {security_alerts_array}')
            # print(f'cloudtrail_event_ids_array: {cloudtrail_event_ids_array}')

    except Exception as e:
        print(f'In Production account...')
        print(f'e: {e}')

    # Return Info to page
    return render_template(
        'security_events.html',
        length = len(account_ids_array),
        account_ids = account_ids_array,
        date_times = date_times_array,
        security_alerts = security_alerts_array,
        cloudtrail_event_ids = cloudtrail_event_ids_array
    )

# Externally Exposed IPs
@app.route('/externally_exposed_ips/')
def externally_exposed_ips():
    public_ip_array = []
    account_name_array = []
    region_array = []
    interface_type_array = []
    resource_attachement_array = []

    ########################
    ### Non-Prod Account ###
    ########################
    
    # Get Public Facing IPs
    try:
        response = ec2_client.describe_network_interfaces()
        for networkinterface in response['NetworkInterfaces']:
            try:
                if networkinterface['Association']['PublicIp']:
                    public_ip_array.append(networkinterface['Association']['PublicIp'])
                    account_name_array.append('Non-Prod')
                    region_array.append('us-east-1')
                    interface_type_array.append(networkinterface['InterfaceType'])
                    resource_attachement_array.append(networkinterface['Description'])
            except (Exception,):
                do_nothing = True
    except Exception as e:
        print(f'Failed Get Public Facing IPs in Non-Prod Account')
        print(f'e: {e}')
        raise e
    
    ##########################
    ### Production Account ###
    ##########################

    # Assume Credentials
    try:
        network_assumed_credentials = sts_client.assume_role(
            RoleArn=('arn:aws:iam::' + PROD_ACCOUNT + ':role/' + PROD_ACCOUNT + ROLE_TO_ASSUME),
            RoleSessionName='AssumedRole'
        )

        prod_ec2_client = session.client(
        'ec2',
        aws_access_key_id=network_assumed_credentials["Credentials"]['AccessKeyId'],
        aws_secret_access_key=network_assumed_credentials["Credentials"]['SecretAccessKey'],
        aws_session_token=network_assumed_credentials["Credentials"]['SessionToken'],
    )
    except Exception as e:
        print(f'Failed assuming role into Network Account')
        print(f'e: {e}')
        raise e
    
    # Get Public Facing IPs
    try:
        response = prod_ec2_client.describe_network_interfaces()
        for networkinterface in response['NetworkInterfaces']:
            try:
                if networkinterface['Association']['PublicIp']:
                    public_ip_array.append(networkinterface['Association']['PublicIp'])
                    account_name_array.append('Production')
                    region_array.append('us-east-1')
                    interface_type_array.append(networkinterface['InterfaceType'])
                    resource_attachement_array.append(networkinterface['Description'])
            except (Exception,):
                do_nothing = True
    except Exception as e:
        print(f'Failed Get Public Facing IPs in Production Account')
        print(f'e: {e}')
        raise e

    ###################################
    ### Network Account - us-east-1 ###
    ###################################

    # Assume Credentials
    try:
        network_assumed_credentials = sts_client.assume_role(
            RoleArn=('arn:aws:iam::' + NETWORK_ACCOUNT + ':role/' + NETWORK_ACCOUNT + ROLE_TO_ASSUME),
            RoleSessionName='AssumedRole'
        )

        network_ec2_client = session.client(
        'ec2',
        aws_access_key_id=network_assumed_credentials["Credentials"]['AccessKeyId'],
        aws_secret_access_key=network_assumed_credentials["Credentials"]['SecretAccessKey'],
        aws_session_token=network_assumed_credentials["Credentials"]['SessionToken'],
    )
    except Exception as e:
        print(f'Failed assuming role into Network Account')
        print(f'e: {e}')
        raise e
    
    # Get Public Facing IPs
    try:
        response = network_ec2_client.describe_network_interfaces()
        for networkinterface in response['NetworkInterfaces']:
            try:
                if networkinterface['Association']['PublicIp']:
                    public_ip_array.append(networkinterface['Association']['PublicIp'])
                    account_name_array.append('Network')
                    region_array.append('us-east-1')
                    interface_type_array.append(networkinterface['InterfaceType'])
                    resource_attachement_array.append(networkinterface['Description'])
            except (Exception,):
                do_nothing = True
    except Exception as e:
        print(f'Failed Get Public Facing IPs in Network Account')
        print(f'e: {e}')
        raise e
    
    ###################################
    ### Network Account - us-west-2 ###
    ###################################

    # Assume Credentials
    try:
        network_assumed_credentials = sts_client.assume_role(
            RoleArn=('arn:aws:iam::' + NETWORK_ACCOUNT + ':role/' + NETWORK_ACCOUNT + ROLE_TO_ASSUME),
            RoleSessionName='AssumedRole'
        )

        network_ec2_client = session.client(
        'ec2',
        aws_access_key_id=network_assumed_credentials["Credentials"]['AccessKeyId'],
        aws_secret_access_key=network_assumed_credentials["Credentials"]['SecretAccessKey'],
        aws_session_token=network_assumed_credentials["Credentials"]['SessionToken'],
        region_name='us-west-2'
    )
    except Exception as e:
        print(f'Failed assuming role into Network Account')
        print(f'e: {e}')
        raise e
    
    # Get Public Facing IPs
    try:
        response = network_ec2_client.describe_network_interfaces()
        for networkinterface in response['NetworkInterfaces']:
            try:
                if networkinterface['Association']['PublicIp']:
                    public_ip_array.append(networkinterface['Association']['PublicIp'])
                    account_name_array.append('Network')
                    region_array.append('us-west-2')
                    interface_type_array.append(networkinterface['InterfaceType'])
                    resource_attachement_array.append(networkinterface['Description'])
                    print(networkinterface['Association']['PublicIp'])
            except (Exception,):
                do_nothing = True
    except Exception as e:
        print(f'Failed Get Public Facing IPs in Network Account')
        print(f'e: {e}')
        raise e
    
    # Return info to page
    return render_template(
        'externally_exposed_ips.html',
        length = len(public_ip_array),
        public_ips = public_ip_array,
        account_names = account_name_array,
        regions = region_array,
        interface_types = interface_type_array,
        resource_attachements = resource_attachement_array
    )

# EC2 Non-Prod Simple Page
@app.route('/ec2_non_prod/', methods=['GET', 'POST'])
def ec2_non_prod():

    # Button Actions
    if request.method == 'POST':

        # Start Button Click
        if request.form.get('start'):
            instance_id = request.form['start']
            ec2_client.start_instances(
                InstanceIds=[
                    instance_id,
                ]
            )
            time.sleep(2)

        # Stop Button Click
        elif request.form.get('stop'):
            instance_id = request.form['stop']
            ec2_client.stop_instances(
                InstanceIds=[
                    instance_id,
                ]
            )
            time.sleep(2)
        
        return redirect(request.url)
    
    # Default/GET page load
    else:
        # Get EC2 Instances
        try:
            ec2_instance_names, \
            ec2_instance_ids, \
            ec2_instance_private_ips, \
            ec2_instance_vcpu, \
            ec2_instance_state = get_ec2_instances_simple(
                ec2_client
            )
        except Exception as e:
            print('Error encountered during Get EC2 Instances')
            print('e: {e}')

        # Return Info to page
        return render_template(
            'ec2_non_prod.html', 
            length = len(ec2_instance_names),
            ec2_instance_names=ec2_instance_names,
            ec2_instance_ids=ec2_instance_ids,
            ec2_instance_private_ips=ec2_instance_private_ips,
            ec2_instance_vcpu=ec2_instance_vcpu,
            ec2_instance_state=ec2_instance_state
        )

# EC2 Non-Prod Detailed Page
@app.route('/ec2_non_prod_detailed/')
def ec2_non_prod_detailed():
    # Get EC2 Instances
    try:
        ec2_instance_names, \
        ec2_instance_ids, \
        ec2_instance_private_ips, \
        ec2_instance_vcpu, \
        ec2_instance_memory, \
        ec2_instance_disk_capacity, \
        ec2_instance_disk_usage, \
        ec2_instance_disk_percentage, \
        ec2_instance_state = get_ec2_instances_detailed(
            ec2_client,
            dynamo_client
        )
    except Exception as e:
        print('Error encountered during Get EC2 Instances')
        print('e: {e}')

    # Return Info to page
    return render_template(
        'ec2_non_prod_detailed.html', 
        length = len(ec2_instance_names),
        ec2_instance_names=ec2_instance_names,
        ec2_instance_ids=ec2_instance_ids,
        ec2_instance_private_ips=ec2_instance_private_ips,
        ec2_instance_vcpu=ec2_instance_vcpu,
        ec2_instance_memory=ec2_instance_memory,
        ec2_instance_disk_capacity=ec2_instance_disk_capacity,
        ec2_instance_disk_usage=ec2_instance_disk_usage,
        ec2_instance_disk_percentage=ec2_instance_disk_percentage,
        ec2_instance_state=ec2_instance_state
    )

# EC2 Prod Detailed Page
@app.route('/ec2_prod_detailed/')
def ec2_prod_detailed():
    # Assume Credentials
    try:
        prod_assumed_credentials = sts_client.assume_role(
            RoleArn=('arn:aws:iam::' + PROD_ACCOUNT + ':role/' + PROD_ACCOUNT + ROLE_TO_ASSUME),
            RoleSessionName='AssumedRole'
        )

        prod_ec2_client = session.client(
            'ec2',
            aws_access_key_id=prod_assumed_credentials["Credentials"]['AccessKeyId'],
            aws_secret_access_key=prod_assumed_credentials["Credentials"]['SecretAccessKey'],
            aws_session_token=prod_assumed_credentials["Credentials"]['SessionToken'],
        )

        prod_dynamo_client = session.client(
            'dynamodb',
            aws_access_key_id=prod_assumed_credentials["Credentials"]['AccessKeyId'],
            aws_secret_access_key=prod_assumed_credentials["Credentials"]['SecretAccessKey'],
            aws_session_token=prod_assumed_credentials["Credentials"]['SessionToken'],
        )
    except Exception as e:
        print(f'Failed assuming role into Production Account')
        print(f'e: {e}')
        raise e
    
    # Get EC2 Instances
    try:
        ec2_instance_names, \
        ec2_instance_ids, \
        ec2_instance_private_ips, \
        ec2_instance_vcpu, \
        ec2_instance_memory, \
        ec2_instance_disk_capacity, \
        ec2_instance_disk_usage, \
        ec2_instance_disk_percentage, \
        ec2_instance_state = get_ec2_instances_detailed(
            prod_ec2_client,
            prod_dynamo_client
        )
    except Exception as e:
        print('Error encountered during Get EC2 Instances')
        print('e: {e}')

    # Return Info to page
    return render_template(
        'ec2_prod_detailed.html', 
        length = len(ec2_instance_names),
        ec2_instance_names=ec2_instance_names,
        ec2_instance_ids=ec2_instance_ids,
        ec2_instance_private_ips=ec2_instance_private_ips,
        ec2_instance_vcpu=ec2_instance_vcpu,
        ec2_instance_memory=ec2_instance_memory,
        ec2_instance_disk_capacity=ec2_instance_disk_capacity,
        ec2_instance_disk_usage=ec2_instance_disk_usage,
        ec2_instance_disk_percentage=ec2_instance_disk_percentage,
        ec2_instance_state=ec2_instance_state
    )

# EC2 Network Detailed Page
@app.route('/ec2_network_detailed/')
def ec2_network_detailed():
    # Assume Credentials
    try:
        network_assumed_credentials = sts_client.assume_role(
            RoleArn=('arn:aws:iam::' + NETWORK_ACCOUNT + ':role/' + NETWORK_ACCOUNT + ROLE_TO_ASSUME),
            RoleSessionName='AssumedRole'
        )

        network_ec2_client = session.client(
            'ec2',
            aws_access_key_id=network_assumed_credentials["Credentials"]['AccessKeyId'],
            aws_secret_access_key=network_assumed_credentials["Credentials"]['SecretAccessKey'],
            aws_session_token=network_assumed_credentials["Credentials"]['SessionToken'],
        )

        network_dynamo_client = session.client(
            'dynamodb',
            aws_access_key_id=network_assumed_credentials["Credentials"]['AccessKeyId'],
            aws_secret_access_key=network_assumed_credentials["Credentials"]['SecretAccessKey'],
            aws_session_token=network_assumed_credentials["Credentials"]['SessionToken'],
        )
    except Exception as e:
        print(f'Failed assuming role into Network Account')
        print(f'e: {e}')
        raise e
    
    # Get EC2 Instances
    try:
        ec2_instance_names, \
        ec2_instance_ids, \
        ec2_instance_private_ips, \
        ec2_instance_vcpu, \
        ec2_instance_memory, \
        ec2_instance_disk_capacity, \
        ec2_instance_disk_usage, \
        ec2_instance_disk_percentage, \
        ec2_instance_state = get_ec2_instances_detailed(
            network_ec2_client,
            network_dynamo_client
        )
    except Exception as e:
        print('Error encountered during Get EC2 Instances')
        print('e: {e}')

    # Return Info to page
    return render_template(
        'ec2_network_detailed.html', 
        length = len(ec2_instance_names),
        ec2_instance_names=ec2_instance_names,
        ec2_instance_ids=ec2_instance_ids,
        ec2_instance_private_ips=ec2_instance_private_ips,
        ec2_instance_vcpu=ec2_instance_vcpu,
        ec2_instance_memory=ec2_instance_memory,
        ec2_instance_disk_capacity=ec2_instance_disk_capacity,
        ec2_instance_disk_usage=ec2_instance_disk_usage,
        ec2_instance_disk_percentage=ec2_instance_disk_percentage,
        ec2_instance_state=ec2_instance_state
    )

# Network Architecture us-east-1 Page
@app.route('/network_architecture_us_east_1/')
def network_architecture_us_east_1():
    # Return Info to page
    return render_template('network_architecture_us_east_1.html')

# Network Architecture us-west-2 Page
@app.route('/network_architecture_us_west_2/')
def network_architecture_us_west_2():
    # Return Info to page
    return render_template('network_architecture_us_west_2.html')

# Vendor Portal Architecture Page
@app.route('/vendor_portal_alb_architecture/')
def vendor_portal_alb_architecture():
    # Return Info to page
    return render_template('vendor_portal_alb_architecture.html')

# Get Crowdstrike Token Page
@app.route('/get_crowdstrike_token/')
def get_crowdstrike_token():
    # Return Info to page
    return render_template('get_crowdstrike_token.html')


############################################
################ FUNCTIONS #################
############################################

# Functions
def get_ec2_instances_simple(
        ec2_client
):
    '''
    Description: Gets EC2 Instance IDs
    param: ec2_client: (boto3.client)
    return: (Dict) EC2 Instance Names               -
            (Dict) EC2 Instance Ids                 -
            (Dict) EC2 Instance Private IPs         -
            (Dict) EC2 Instance vCPU allocation     -
            (Dict) EC2 Instance State               - 
    '''
    ec2_instance_names = []
    ec2_instance_ids = []
    ec2_instance_private_ips = []
    ec2_instance_vcpu = []
    ec2_instance_state = []

    response = ec2_client.describe_instances()
    for res in response['Reservations']:
        for ec2_instance in res['Instances']:
            # Instance_ID
            ec2_instance_ids.append(ec2_instance['InstanceId'])
            
            # Instance_Name
            for tag in ec2_instance['Tags']:
                if tag['Key'] == 'Name':
                    ec2_instance_names.append(tag['Value'])
                    # print(f"ec2_instance: {tag['Value']}")

            # Instance Private_IP
            try:
                ec2_instance_private_ips.append(ec2_instance['PrivateIpAddress'])
                # print(f"ec2_instance: {ec2_instance['PrivateIpAddress']}")
            except Exception:
                # print("This instance doesn't have a PrivateIpAddress available")
                ec2_instance_private_ips.append('N/A')

            # Instance vCPU
            cpu_count = int(ec2_instance['CpuOptions']['CoreCount']) * int(ec2_instance['CpuOptions']['ThreadsPerCore'])
            ec2_instance_vcpu.append(cpu_count)

            # Instance State
            ec2_instance_state.append(ec2_instance['State']['Name'])

    return \
        ec2_instance_names, \
        ec2_instance_ids, \
        ec2_instance_private_ips, \
        ec2_instance_vcpu, \
        ec2_instance_state


def get_ec2_instances_detailed(
        ec2_client,
        dynamo_client
):
    '''
    Description: Gets EC2 Instance IDs
    param: ec2_client: (boto3.client)
    return: (Dict) EC2 Instance Names               -
            (Dict) EC2 Instance Ids                 -
            (Dict) EC2 Instance Private IPs         -
            (Dict) EC2 Instance vCPU allocation     -
            (Dict) EC2 Instance Memory allocation   -
            (Dict) EC2 Instance Disk Capacity
            (Dict) EC2 Instance Disk Usage
            (Dict) EC2 Instance State               - 
    '''
    ec2_instance_names = []
    ec2_instance_ids = []
    ec2_instance_private_ips = []
    ec2_instance_vcpu = []
    ec2_instance_memory = []
    ec2_instance_disk_capacity = []
    ec2_instance_disk_usage = []
    ec2_instance_disk_percentage = []
    ec2_instance_state = []

    response = ec2_client.describe_instances()
    for res in response['Reservations']:
        for ec2_instance in res['Instances']:
            # Instance_ID
            ec2_instance_ids.append(ec2_instance['InstanceId'])

            # Instance_Name
            for tag in ec2_instance['Tags']:
                if tag['Key'] == 'Name':
                    ec2_instance_names.append(tag['Value'])

            # Instance Private_IP
            try:
                ec2_instance_private_ips.append(ec2_instance['PrivateIpAddress'])
            except Exception:
                # print("This instance doesn't have a PrivateIpAddress available")
                ec2_instance_private_ips.append('N/A')

            # Instance vCPU
            cpu_count = int(ec2_instance['CpuOptions']['CoreCount']) * int(ec2_instance['CpuOptions']['ThreadsPerCore'])
            ec2_instance_vcpu.append(cpu_count)

            # Instance Memory - This is causing slow responses on the page
            instance_type = ec2_client.describe_instance_attribute(Attribute='instanceType', InstanceId=ec2_instance['InstanceId'])
            instance_type = instance_type['InstanceType']['Value']
            details = ec2_client.describe_instance_types(InstanceTypes=[instance_type])
            memory = int(details['InstanceTypes'][0]['MemoryInfo']['SizeInMiB']) / 1024
            ec2_instance_memory.append(str(int(memory)) + ' GB')

            # # Instance Disk Storage - This is causing slow responses on the page
            # disk_sizes = []
            # volumes = ec2_instance['BlockDeviceMappings']
            # for volume in volumes:
            #     volume_ids = ec2_client.describe_volumes(
            #         VolumeIds=[
            #             volume['Ebs']['VolumeId']
            #         ]
            #     )
                
            #     for volume_id in volume_ids['Volumes']:
            #         # print(volume_id)
            #         disk_sizes.append(volume_id['Size'])
            # ec2_instance_disk_capacity.append(disk_sizes)

            # Instance Disk Storage - From DynamoTable
            try:
                dynamo_info = dynamo_client.get_item(
                    TableName=DYNAMO_TABLE,
                    Key={
                        'InstanceId': {
                            'S': ec2_instance['InstanceId']
                        }
                    }
                )
                if dynamo_info['Item']['Volume_Info']:
                    volume_capacity_array = []
                    volume_usage_array = []
                    percent_free_array = []
                    position = 0
                    
                    volume_letter_array = dynamo_info['Item']['Volume_Info']['M']['Volume_Letter']['S'].split(' | ')
                    max_size_array = dynamo_info['Item']['Volume_Info']['M']['Max_Size']['S'].split(' | ')
                    free_space_array = dynamo_info['Item']['Volume_Info']['M']['Free_Space']['S'].split(' | ')
                    percentage_array = dynamo_info['Item']['Volume_Info']['M']['Percent_Free']['S'].split(' | ')

                    for volume_letter in volume_letter_array:
                        volume_capacity_array.append(volume_letter + '-' + max_size_array[position])
                        volume_usage_array.append(volume_letter + '-' + free_space_array[position])
                        percent_free_array.append(volume_letter + '-' + percentage_array[position])
                        position += 1
                    
                    # Remove Trailing '-'
                    del volume_capacity_array[-1]
                    del volume_usage_array[-1]
                    del percent_free_array[-1]
                        
                    ec2_instance_disk_capacity.append(volume_capacity_array)
                    ec2_instance_disk_usage.append(volume_usage_array)
                    ec2_instance_disk_percentage.append(percent_free_array)
                else:
                    ec2_instance_disk_capacity.append('N/A')
                    ec2_instance_disk_usage.append('N/A')
                    ec2_instance_disk_percentage.append('N/A')

                # print(f'ec2_instance_disk_capacity: {ec2_instance_disk_capacity}')
            
            except Exception as e:
                # print(f'e: {e}')
                ec2_instance_disk_capacity.append('')
                ec2_instance_disk_usage.append('')
                ec2_instance_disk_percentage.append('')

            # Instance State
            ec2_instance_state.append(ec2_instance['State']['Name'])

    return \
        ec2_instance_names, \
        ec2_instance_ids, \
        ec2_instance_private_ips, \
        ec2_instance_vcpu, \
        ec2_instance_memory, \
        ec2_instance_disk_capacity, \
        ec2_instance_disk_usage, \
        ec2_instance_disk_percentage, \
        ec2_instance_state


def get_daily_costs(
        ce_client
):
    time_array_daily = []
    cost_array_daily = []

    today_date = datetime.datetime.today().strftime('%Y-%m-%d')
    thirty_days_ago_date = (datetime.datetime.today() - datetime.timedelta(30)).strftime('%Y-%m-%d')

    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': thirty_days_ago_date,
            'End': today_date
        },
        Granularity='DAILY',
        Metrics=[
            'UNBLENDED_COST'
        ]
    )
    for res in response['ResultsByTime']:
        time_array_daily.append(res['TimePeriod']['Start'])
        cost_array_daily.append(res['Total']['UnblendedCost']['Amount'])
    
    return time_array_daily, cost_array_daily


def get_daily_costs_cross_account(
    sts_client,
    account_id,
    role_to_assume 
):
    assumed_credentials = sts_client.assume_role(
        RoleArn=('arn:aws:iam::' + account_id + ':role/' + role_to_assume),
        RoleSessionName='AssumedRole'
    )

    ce_client = session.client(
        'ce',
        aws_access_key_id=assumed_credentials["Credentials"]['AccessKeyId'],
        aws_secret_access_key=assumed_credentials["Credentials"]['SecretAccessKey'],
        aws_session_token=assumed_credentials["Credentials"]['SessionToken'],
    )

    time_array_daily = []
    cost_array_daily = []

    today_date = datetime.datetime.today().strftime('%Y-%m-%d')
    thirty_days_ago_date = (datetime.datetime.today() - datetime.timedelta(30)).strftime('%Y-%m-%d')

    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': thirty_days_ago_date,
            'End': today_date
        },
        Granularity='DAILY',
        Metrics=[
            'UNBLENDED_COST'
        ]
    )
    for res in response['ResultsByTime']:
        time_array_daily.append(res['TimePeriod']['Start'])
        cost_array_daily.append(res['Total']['UnblendedCost']['Amount'])
    
    return cost_array_daily


def get_monthly_costs(
        ce_client
):
    time_array_monthly = []
    cost_array_monthly = []

    today_date = datetime.datetime.today().strftime('%Y-%m-%d')
    year_ago_date = (datetime.datetime.today() - datetime.timedelta(365)).strftime('%Y-%m-%d')

    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': year_ago_date,
            'End': today_date
        },
        Granularity='MONTHLY',
        Metrics=[
            'UNBLENDED_COST'
        ]
    )
    for res in response['ResultsByTime']:
        time_array_monthly.append(res['TimePeriod']['Start'])
        cost_array_monthly.append(res['Total']['UnblendedCost']['Amount'])
    
    return time_array_monthly, cost_array_monthly


def get_monthly_costs_cross_account(
    sts_client,
    account_id,
    role_to_assume
):
    assumed_credentials = sts_client.assume_role(
        RoleArn=('arn:aws:iam::' + account_id + ':role/' + role_to_assume),
        RoleSessionName='AssumedRole'
    )

    ce_client = session.client(
        'ce',
        aws_access_key_id=assumed_credentials["Credentials"]['AccessKeyId'],
        aws_secret_access_key=assumed_credentials["Credentials"]['SecretAccessKey'],
        aws_session_token=assumed_credentials["Credentials"]['SessionToken'],
    )

    time_array_monthly = []
    cost_array_monthly = []

    today_date = datetime.datetime.today().strftime('%Y-%m-%d')
    year_ago_date = (datetime.datetime.today() - datetime.timedelta(365)).strftime('%Y-%m-%d')

    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': year_ago_date,
            'End': today_date
        },
        Granularity='MONTHLY',
        Metrics=[
            'UNBLENDED_COST'
        ]
    )
    for res in response['ResultsByTime']:
        time_array_monthly.append(res['TimePeriod']['Start'])
        cost_array_monthly.append(res['Total']['UnblendedCost']['Amount'])

    return cost_array_monthly


# Call __main__
if __name__ == "__main__":
    app.run(debug=True)
