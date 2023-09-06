import boto3
import json


# CONST
DASHBOARD_NAME = 'Account_Health'


def main():
    # Setup Connections
    try:
        session = boto3.Session()
        ec2_client = session.client('ec2')
        lambda_client = session.client('lambda')
        sts_client = session.client('sts')
        cloudwatch_client = session.client('cloudwatch')
    except Exception as e:
        print(f'Failed setting up connections')
        print(f'e: {e}')
        raise e

    # Get EC2 Instances
    try:
        ec2_instance_ids = []
        ec2_instances = ec2_client.describe_instances()
        for reservation in ec2_instances['Reservations']:
            for ec2_instance in reservation['Instances']:
                ec2_instance_ids.append(ec2_instance['InstanceId'])
        print(f'ec2_instance_ids: {ec2_instance_ids}')
    except Exception as e:
        print(f'Failed Get EC2 Instances')
        print(f'e: {e}')
        raise e

    # Get Lambda Instances
    try:
        lambda_function_names = []
        lambda_functions = lambda_client.list_functions()
        for lambda_function in lambda_functions['Functions']:
            lambda_function_names.append(lambda_function['FunctionName'])
    except Exception as e:
        print(f'Failed Get Lambda Instances')
        print(f'e: {e}')
        raise e

    # Create Widgets
    try:
        ec2_cpu_utilization = create_widget_ec2_cpu_utilization(
            ec2_instance_ids
        )
        ec2_status_check_failed = create_widget_ec2_status_check_failed(
            ec2_instance_ids
        )

        lambda_function_invocations_and_errors = create_widget_lambda_function_invocations_and_errors(
            lambda_function_names
        )

        lambda_function_throttles = create_widget_lambda_function_throttles(
            lambda_function_names
        )

        lambda_function_duration = create_widget_lambda_function_duration(
            lambda_function_names
        )

        dashboard_body = {

            "start": "-PT6H",
            "periodOverride": "inherit",
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                     "height": 6,
                     "properties": {
                        "metrics": ec2_cpu_utilization,
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-1",
                        "title": "EC2 Instance CPU Utilization",
                        "liveData": False,
                        "legend": {
                            "position": "right"
                          }
                     }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": ec2_status_check_failed,
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-1",
                        "title": "EC2 Instance Status Checks Failed",
                        "liveData": False,
                        "legend": {
                            "position": "right"
                        }
                    }
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": lambda_function_invocations_and_errors,
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-1",
                        "title": "Lambda Function Invocations and Errors",
                        "liveData": False,
                        "legend": {
                            "position": "right"
                        }
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": lambda_function_throttles,
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-1",
                        "title": "Lambda Function Throttles",
                        "liveData": False,
                        "legend": {
                            "position": "right"
                        }
                    }
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 12,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": lambda_function_duration,
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-1",
                        "title": "Lambda Function Duration",
                        "liveData": False,
                        "legend": {
                            "position": "right"
                        }
                    }
                }
              # {
              #    "type": "text",
              #    "x": 0,
              #    "y": 7,
              #    "width": 3,
              #    "height": 3,
              #    "properties": {
              #       "markdown": "Hello world"
              #    }
              # }
            ]
        }
    except Exception as e:
        print(f'Failed Create Widget for each EC2_Instance')
        print(f'e: {e}')
        raise e

    # Create Dashboards
    try:
        dashboard_body = json.dumps(dashboard_body)
        dashboard = cloudwatch_client.put_dashboard(
            DashboardName=DASHBOARD_NAME + '_' + sts_client.get_caller_identity()['Account'],
            DashboardBody=dashboard_body
        )
        print(f'dashboard: {dashboard}')
    except Exception as e:
        print(f'Failed Create Dashboards')
        print(f'e: {e}')
        raise e


def create_widget_ec2_cpu_utilization(
        ec2_instance_ids
):
    metrics_array = []

    for ec2_instance_id in ec2_instance_ids:
        instance_metrics = [
            "AWS/EC2",
            "CPUUtilization",
            "InstanceId",
            ec2_instance_id
        ]
        metrics_array.append(instance_metrics)
    print(f'ec2_metrics_array: {metrics_array}')

    return metrics_array


def create_widget_ec2_status_check_failed(
        ec2_instance_ids
):
    metrics_array = []

    for ec2_instance_id in ec2_instance_ids:
        instance_metrics = [
            "AWS/EC2",
            "StatusCheckFailed",
            "InstanceId",
            ec2_instance_id
        ]
        metrics_array.append(instance_metrics)
    print(f'ec2_metrics_array: {metrics_array}')

    return metrics_array


def create_widget_lambda_function_invocations_and_errors(
        lambda_function_names
):
    metrics_array = []

    for lambda_function_name in lambda_function_names:
        instance_metrics = [
            "AWS/Lambda",
            "Invocations",
            "FunctionName",
            lambda_function_name
        ]
        metrics_array.append(instance_metrics)
    for lambda_function_name in lambda_function_names:
        instance_metrics = [
            "AWS/Lambda",
            "Errors",
            "FunctionName",
            lambda_function_name
        ]
        metrics_array.append(instance_metrics)
    print(f'lambdas_metrics_array: {metrics_array}')

    return metrics_array


def create_widget_lambda_function_throttles(
        lambda_function_names
):
    metrics_array = []

    for lambda_function_name in lambda_function_names:
        instance_metrics = [
            "AWS/Lambda",
            "Throttles",
            "FunctionName",
            lambda_function_name
        ]
        metrics_array.append(instance_metrics)
    print(f'lambdas_metrics_array: {metrics_array}')

    return metrics_array


def create_widget_lambda_function_duration(
        lambda_function_names
):
    metrics_array = []

    for lambda_function_name in lambda_function_names:
        instance_metrics = [
            "AWS/Lambda",
            "Duration",
            "FunctionName",
            lambda_function_name
        ]
        metrics_array.append(instance_metrics)
    print(f'lambdas_metrics_array: {metrics_array}')

    return metrics_array


if __name__ == "__main__":
    main()
