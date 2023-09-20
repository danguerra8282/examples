import boto3
from flask import Flask, render_template
app = Flask(__name__)


# Setup Connections
try:
    session = boto3.Session()
    ec2_client = session.client('ec2')
except Exception as e:
    print(f'Failed setting up connections')
    print(f'e: {e}')

# Home Page
@app.route('/')
def home():
    info = '<h1>This is the beginning</h1>'
    return render_template('home.html') + info

# Non-Prod Page
@app.route('/ec2_non_prod/')
def ec2_non_prod():

    # Get EC2 Instances
    ec2_instance_names, ec2_instance_ids, ec2_instance_private_ips, ec2_instance_state = get_ec2_instances(
        ec2_client
    )

    # Return Info to page
    return render_template(
        'ec2_non_prod.html', 
        length = len(ec2_instance_names),
        ec2_instance_names=ec2_instance_names,
        ec2_instance_ids=ec2_instance_ids,
        ec2_instance_private_ips=ec2_instance_private_ips,
        ec2_instance_state=ec2_instance_state
    )

# About Page
@app.route('/about/')
def about():
    return render_template('about.html')


# Functions
def get_ec2_instances(
        ec2_client
):
    '''
    Description: Gets EC2 Instance IDs
    param: ec2_client: (boto3.client)
    return: (Dict) EC2 Instance Names
            (Dict) EC2 Instance Ids
    '''
    ec2_instance_names = []
    ec2_instance_ids = []
    ec2_instance_private_ips = []
    ec2_instance_state = []

    response = ec2_client.describe_instances()
    for res in response['Reservations']:
        for ec2_instance in res['Instances']:
            ec2_instance_ids.append(ec2_instance['InstanceId'])

            for tag in ec2_instance['Tags']:
                if tag['Key'] == 'Name':
                    ec2_instance_names.append(tag['Value'])

            ec2_instance_private_ips.append(ec2_instance['PrivateIpAddress'])
            ec2_instance_state.append(ec2_instance['State']['Name'])

    return \
        ec2_instance_names, \
        ec2_instance_ids, \
        ec2_instance_private_ips, \
        ec2_instance_state


if __name__ == "__main__":
    app.run(debug=True)
