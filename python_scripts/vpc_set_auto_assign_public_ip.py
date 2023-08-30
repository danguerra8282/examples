import boto3
import time


def main():

    # Setup Connections
    try:
        session = boto3.Session()
        ec2_client = session.client('ec2')
    except Exception as e:
        print(f'Failed setting up connections')
        print(f'e: {e}')
        raise e

    # Get VPC IDs
    try:
        vpcs = ec2_client.describe_vpcs()
        print(f'VPC IDs found:')
        vpc_ids = []
        for vpc in vpcs['Vpcs']:
            print(f"    {vpc['VpcId']}")
            vpc_ids.append(vpc['VpcId'])
        print()
    except Exception as e:
        print(f'Failed Getting VPC Ids')
        print(f'e: {e}')
        raise e

    # Get Subnets per VPC_ID
    try:
        subnet_ids = []
        for vpc_id in vpc_ids:
            response = ec2_client.describe_subnets(
                Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': [
                            vpc_id,
                        ]
                    },
                ]
            )
            for subnet_id in response['Subnets']:
                subnet_ids.append(subnet_id['SubnetId'])
        # print(subnet_ids)
    except Exception as e:
        print(f'Failed Getting Subnets')
        print(f'e: {e}')
        raise e

    # Disable Auto-Assign Public IP Address
    try:
        for subnet_id in subnet_ids:
            disable_auto_assign_ip(
                ec2_client,
                subnet_id
            )
            print()
    except Exception as e:
        print(f'Failed Getting Subnets')
        print(f'e: {e}')
        raise e


def disable_auto_assign_ip(
        ec2_client,
        subnet_id
):
    print(subnet_id)
    print(f'    Disabling Auto-Assign IPv6 Addresses...')
    ec2_client.modify_subnet_attribute(
        AssignIpv6AddressOnCreation={
            'Value': False
        },
        SubnetId=subnet_id,
    )
    time.sleep(1)
    print(f'    Disabling Auto-Assign IPv4 Addresses...')
    ec2_client.modify_subnet_attribute(
        MapPublicIpOnLaunch={
            'Value': False
        },
        SubnetId=subnet_id,
    )


if __name__ == "__main__":
    main()
