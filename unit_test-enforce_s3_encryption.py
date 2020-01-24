import boto3
import datetime
import time


def main():
    print('Starting Enforce_S3_Encryption Unit Test')

    # Setup Connections
    try:
        session = boto3.Session()
        s3_client = session.client('s3')
    except Exception as e:
        print('Failed to create session and connections')
        raise e

    # Variables
    bucket_name = 'unit-test-enforce-s3-encryption'

    # Create an un-encrypted s3 bucket
    try:
        s3_client.create_bucket(
            Bucket=bucket_name
        )
    except Exception as e:
        print(f'Failed creating s3 bucket: {bucket_name}')
        print(f'e: {e}')
        raise e

    # Verify KMS encryption has been added
    try:
        print('Checking bucket encryption')
        continue_running = True
        counter = 0
        while continue_running:
            try:
                # Recreate connection because this was caching contents and not finding the new bucket for some reason
                session = boto3.Session()
                s3_client = session.client('s3')

                # Check for bucket encryption
                response = s3_client.get_bucket_encryption(
                    Bucket=bucket_name
                )
                if 'aws:kms' in response['ServerSideEncryptionConfiguration']['Rules'][0]\
                        ['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']:
                    print()
                    print(f'PASSED - KMS encryption has been applied')
                    continue_running = False
                else:
                    print('KMS encryption not applied.  Checking again in 5 seconds...')
                    counter += 1
                    if counter > 12:
                        print('FAILED - KMS encryption has not been applied after 1 minute')
                        exit(1)
                    time.sleep(5)
            except:
                print('KMS encryption not applied.  Checking again in 5 seconds...')
                counter += 1
                if counter > 12:
                    print('FAILED - KMS encryption has not been applied after 1 minute')
                    exit(1)
                time.sleep(5)

        # Cleanup after testing
        try:
            print(f'Deleting s3 bucket:  {bucket_name}')
            s3_client.delete_bucket(
                Bucket=bucket_name
            )
            print(f'Successfully deleted s3 bucket: {bucket_name}')
        except Exception as e:
            print('Fail to clean up after testing')
            print(f'e: {e}')
            exit(1)

    except Exception as e:
        print('Failed verifying bucket encryption')
        print(f'e: {e}')
        raise e


main()
