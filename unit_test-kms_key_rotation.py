import boto3
import datetime
from datetime import datetime
import time


def main():
    print('Starting KMS_Key_Rotation Unit Test')

    # CONST
    TEST_ALIAS = 'UNIT_TEST_KMS_KEY_ROTATION'

    # Setup Connections
    try:
        session = boto3.Session()
        kms_client = session.client('kms')
    except Exception as e:
        print('Failed to create session and connections')
        raise e

    try:
        # Check for previously existing Unit_Test KMS key
        key_deletion_response, alias_deletion_response = remove_previous_unit_test_key(
            TEST_ALIAS,
            kms_client
        )
        if key_deletion_response:
            print(f'{TEST_ALIAS} key is scheduled to be deleted.  key_deletion_response: {key_deletion_response}')
        else:
            print(f'{TEST_ALIAS} key was not found.  Continuing with test...')
        if alias_deletion_response:
            print(f'{TEST_ALIAS} alias has been deleted.  alias_deletion_response: {alias_deletion_response}')
        else:
            print(f'{TEST_ALIAS} alias was not found.  Continuing with test...')

        # Create a new Unit_Test KMS key
        key_creation_response, key_alias_response = create_unit_test_key(
            TEST_ALIAS,
            kms_client
        )
        if key_creation_response:
            print(f'{TEST_ALIAS} key has been created.  key_creation_response: {key_creation_response}')
        if key_alias_response:
            print(f'{TEST_ALIAS} alias has been created.  key_alias_response: {key_alias_response}')

        # Verify KMS Key Rotation is Enabled
        key_rotation_status = kms_client.get_key_rotation_status(
            KeyId=str(key_creation_response['KeyMetadata']['KeyId'])
        )
        if not key_rotation_status['KeyRotationEnabled']:
            counter = 0
            while not key_rotation_status['KeyRotationEnabled']:
                time.sleep(2)
                key_rotation_status = kms_client.get_key_rotation_status(
                    KeyId=str(key_creation_response['KeyMetadata']['KeyId'])
                )
                counter += 1
                if counter > 30:
                    print('FAILED - KMS Key Rotation has not been enabled after 1 minute')
                    print(f'{TEST_ALIAS} will not be cleaned up so it can be used for troubleshooting')
                    exit(1)
        if key_rotation_status['KeyRotationEnabled']:
            print(f'SUCCESS - KMS Key Rotation is now enabled')
            key_deletion_response, alias_deletion_response = remove_previous_unit_test_key(
                TEST_ALIAS,
                kms_client
            )
            if key_deletion_response:
                print(f'{TEST_ALIAS} key is scheduled to be deleted.')
            if alias_deletion_response:
                print(f'{TEST_ALIAS} alias has been deleted.')
            print(f'PASSED - KMS_Key_Rotation Unit Test')

    except Exception as e:
        print('Failed KMS_Key_Rotation Unit Test')
        print(f'e: {e}')
        exit(1)
        raise e


def remove_previous_unit_test_key(
        kms_key_alias,
        kms_client
):
    """
    Searches for a kms key & alias and deletes the them if found.  This attempts to keep the deletion to only
        one kms key so to prevent accidental key deletions.
    :param kms_key_alias: The alias name to search for
    :param kms_client: boto3.client
    :return: key_deletion_response, alias_deletion_response: null if no matching alias was found or the return result
             from the key deletion
    """

    key_deletion_response = ''
    alias_deletion_response = ''
    print(f'Checking for previously created {kms_key_alias} key...')
    kms_aliases = kms_client.list_aliases(
        Limit=1000
    )
    # print(f"kms_aliases: {kms_aliases}")
    for kms_alias in kms_aliases['Aliases']:
        if kms_key_alias in kms_alias['AliasName']:
            print(f"kms_alias found: {kms_alias['AliasName']}")
            try:
                print(f'Attempting to delete previous {kms_key_alias} key')
                key_deletion_response = kms_client.schedule_key_deletion(
                    KeyId=kms_alias['TargetKeyId']
                )
                print(f'Attempting to delete previous {kms_key_alias} alias')
                alias_deletion_response = kms_client.delete_alias(
                    AliasName=kms_alias['AliasName']
                )

            except Exception as e:
                print(f'Failed attempting to delete previously created {kms_key_alias} key or alias')
                print(f'e: {e}')
                raise e
            # Prevent deletion of more than 1 key
            return key_deletion_response, alias_deletion_response
    # No key found
    return key_deletion_response, alias_deletion_response


def create_unit_test_key(
        kms_key_alias,
        kms_client
):
    """
    Creates a new KMS key
    :param kms_key_alias: The alias name to assign to the newly created KMS key
    :param kms_client: boto3.client
    :return: key_creation_response, key_alias_response: the responses from the key & alias API creations
    """
    kms_key_alias = 'alias/' + kms_key_alias
    print(f'Creating a new {kms_key_alias} key...')
    key_creation_response = kms_client.create_key(
        Tags=[
            {
                'TagKey': 'Owner',
                'TagValue': 'KMS_Key_Rotation Unit Test'
            },
        ]
    )
    key_alias_response = kms_client.create_alias(
        AliasName=kms_key_alias,
        TargetKeyId=str(key_creation_response['KeyMetadata']['KeyId'])
    )

    return key_creation_response, key_alias_response


main()
