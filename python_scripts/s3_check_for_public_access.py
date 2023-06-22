"""
Description:
  This script will check all S3 buckets in an account and will
  report back the Public Access configurations.
"""

import boto3
from colorama import Fore


def main():

    # Setup Connections
    try:
        session = boto3.Session()
        s3_client = session.client('s3')
    except Exception as e:
        print(f'Failed setting up connections')
        print(f'e: {e}')
        raise e

    # Get All Buckets
    try:
        bucket_names = []
        buckets = s3_client.list_buckets()
        for bucket in buckets['Buckets']:
            bucket_names.append(bucket['Name'])
    except Exception as e:
        print(f'Failed listing buckets')
        print(f'e: {e}')
        raise e

    # Get Bucket Public Access Configuration
    try:
        for bucket_name in bucket_names:
            print(bucket_name)
            block_public_acls, ignore_public_acls, block_public_policy, restrict_public_buckets =\
                get_public_access_block(
                    s3_client,
                    bucket_name
                )

            if block_public_acls:
                print(f'    BlockPublicAcls: {block_public_acls}')
            else:
                print(Fore.RED + f'    BlockPublicAcls: {block_public_acls}' + Fore.RESET)

            if ignore_public_acls:
                print(f'    IgnorePublicAcls: {ignore_public_acls}')
            else:
                print(Fore.RED + f'    IgnorePublicAcls: {ignore_public_acls}' + Fore.RESET)

            if block_public_policy:
                print(f'    BlockPublicPolicy: {block_public_policy}')
            else:
                print(Fore.RED + f'    BlockPublicPolicy: {block_public_policy}' + Fore.RESET)

            if restrict_public_buckets:
                print(f'    RestrictPublicBuckets: {restrict_public_buckets}')
            else:
                print(Fore.RED + f'    RestrictPublicBuckets: {restrict_public_buckets}' + Fore.RESET)

            print()

    except Exception as e:
        print(f'Failed getting Bucket Public Access Configuration')
        print(f'e: {e}')
        raise e


def get_public_access_block(
        s3_client,
        bucket_name
):
    """
    Gets the public_access_block configurations of a bucket.  If the bucket has
    Block All Public Access 'Off' then all configurations are set to False.
    :param s3_client: boto3.client
    :param bucket_name: (string) the name of the bucket to retrieve configurations on
    :return: Boolean
    """
    try:
        setting = s3_client.get_public_access_block(
            Bucket=bucket_name
        )
        try:
            block_public_acls = setting['PublicAccessBlockConfiguration']['BlockPublicAcls']
        except (Exception,):
            block_public_acls = False
        try:
            ignore_public_acls = setting['PublicAccessBlockConfiguration']['IgnorePublicAcls']
        except (Exception,):
            ignore_public_acls = False
        try:
            block_public_policy = setting['PublicAccessBlockConfiguration']['BlockPublicPolicy']
        except (Exception,):
            block_public_policy = False
        try:
            restrict_public_buckets = setting['PublicAccessBlockConfiguration']['RestrictPublicBuckets']
        except (Exception,):
            restrict_public_buckets = False
    except (Exception,):
        block_public_acls = False
        ignore_public_acls = False
        block_public_policy = False
        restrict_public_buckets = False

    return block_public_acls, ignore_public_acls, block_public_policy, restrict_public_buckets


if __name__ == "__main__":
    main()
