import boto3
import datetime
import time


def main():
    print('Starting _S3_Check_for_Public_Buckets Unit Test')

    # Setup Connections
    try:
        session = boto3.Session()
        s3_client = session.client('s3')
    except Exception as e:
        print('Failed to create session and connections')
        raise e

    # Make a public bucket
    try:
        response = s3_client.create_bucket(
            ACL='public-read',
            Bucket='unit-test-public-bucket'
        )
        bucket_created = response["Location"].split("/", 1)[1]
        print(f'bucket_created: {bucket_created}')

    except Exception as e:
        print('Failed creating test bucket')
        print(f'e: {e}')
        raise e

    # Verify bucket ACL is updated so it is not public
    try:
        response = s3_client.get_bucket_acl(
            Bucket=bucket_created
        )
        continue_running = True
        counter = 0
        while continue_running:
            for grant in response['Grants']:
                if 'URI' in grant['Grantee']:
                    continue_running = True
                    if 'http://acs.amazonaws.com/groups/global/AllUsers' in grant['Grantee']['URI']:
                        print(f'Public Access found in {grant}')
                        time.sleep(5)
                        response = s3_client.get_bucket_acl(
                            Bucket=bucket_created
                        )
                        counter += 1
                        if counter > 60:
                            print('FAILED - public access has not been removed after 5 minutes')
                            exit(1)
                else:
                    continue_running = False

    except Exception as e:
        print('Failed getting test bucket ACLs')
        print(f'e: {e}')
        raise e

    # Delete unit-test-public-bucket
    try:
        print('Public access has been removed from s3 bucket: unit-test-public-bucket')
        print('Deleting s3 bucket:  unit-test-public-bucket')
        s3_client.delete_bucket(
            Bucket='unit-test-public-bucket'
        )
    except Exception as e:
        print('Fail to clean up after testing')
        print(f'e: {e}')
        exit(1)

    print('PASSED - _S3_Check_for_Public_Buckets')


main()
