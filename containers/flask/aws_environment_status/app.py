import boto3
import datetime
from flask import Flask, render_template
app = Flask(__name__)


# Setup Connections
try:
    session = boto3.Session()
    ec2_client = session.client('ec2')
    ce_client = session.client('ce')
except Exception as e:
    print(f'Failed setting up connections')
    print(f'e: {e}')

# Home Page
@app.route('/')
def home():
    info = '<h1><center>This website connects to AWS Accounts and returns information for centralized viewing.</center></h1>' \
        '<br>' \
        '<h3>Notes:</h3>' \
        '<div style="margin: 40px"><center> - EC2 Instances can be view in either a "Simple" or "Detailed" view.  \
            The "Detailed" view will take a little longer to populate.</center></div>'
    return render_template('home.html') + info

# Costs Page
@app.route('/costs/')
def costs():
    time_array_daily, cost_array_daily = get_daily_costs(
        ce_client
    )

    labels_daily = time_array_daily
 
    # data_non_prod = [0, 10, 15, 8, 22, 18, 25]
    data_non_prod_daily = cost_array_daily
    data_prod = [1000, 940, 500, 1111, 800, 1000, 1050]
    data_network = [0, 10, 15, 8, 22, 18, 25]

    time_array_monthly, cost_array_monthly = get_monthly_costs(
        ce_client
    )

    # data_non_prod = [0, 10, 15, 8, 22, 18, 25]
    data_non_prod_monthly = cost_array_monthly
    data_prod = [1000, 940, 500, 1111, 800, 1000, 1050]
    data_network = [0, 10, 15, 8, 22, 18, 25]

    labels_monthly = time_array_monthly
 
    # Return the components to the HTML template
    return render_template(
        template_name_or_list='costs.html',
        data_prod=data_prod,
        data_non_prod_daily=data_non_prod_daily,
        data_network=data_network,
        labels_daily=labels_daily,
        # data_prod=data_prod,
        data_non_prod_monthly=data_non_prod_monthly,
        # data_network=data_network,
        labels_monthly=labels_monthly,
    )

# EC2 Non-Prod Simple Page
@app.route('/ec2_non_prod/')
def ec2_non_prod():
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
        ec2_instance_state = get_ec2_instances_detailed(
            ec2_client
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
        ec2_instance_state=ec2_instance_state
    )


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

            # Instance Private_IP
            ec2_instance_private_ips.append(ec2_instance['PrivateIpAddress'])

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
        ec2_client
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
            ec2_instance_private_ips.append(ec2_instance['PrivateIpAddress'])

            # Instance vCPU
            cpu_count = int(ec2_instance['CpuOptions']['CoreCount']) * int(ec2_instance['CpuOptions']['ThreadsPerCore'])
            ec2_instance_vcpu.append(cpu_count)

            # Instance Memory - This is causing slow responses on the page
            instance_type = ec2_client.describe_instance_attribute(Attribute='instanceType', InstanceId=ec2_instance['InstanceId'])
            instance_type = instance_type['InstanceType']['Value']
            details = ec2_client.describe_instance_types(InstanceTypes=[instance_type])
            memory = int(details['InstanceTypes'][0]['MemoryInfo']['SizeInMiB']) / 1024
            ec2_instance_memory.append(str(int(memory)) + ' GB')

            # Instance Disk Storage - This is causing slow responses on the page
            disk_sizes = []
            volumes = ec2_instance['BlockDeviceMappings']
            for volume in volumes:
                volume_ids = ec2_client.describe_volumes(
                    VolumeIds=[
                        volume['Ebs']['VolumeId']
                    ]
                )
                
                for volume_id in volume_ids['Volumes']:
                    # print(volume_id)
                    disk_sizes.append(volume_id['Size'])
            ec2_instance_disk_capacity.append(disk_sizes)

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


# Call __main__
if __name__ == "__main__":
    app.run(debug=True)
