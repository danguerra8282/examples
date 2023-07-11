import boto3
import logging
import json
import os
import time


def lambda_handler(event, context):
    # Logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # logger.setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    logger.debug(f'event: {event}')
    logger.debug(f'context: {context}')
    bucket_modified = event['detail']['requestParameters']['bucketName']
    logger.info(f"S3 Bucket modification detected: {bucket_modified}")

    # Setup Connection
    try:
        session = boto3.Session()
        s3_client = session.client('s3')
    except Exception as e:
        logger.error(f'Failed creating session')
        logger.error(f'e: {e}')
        raise e

    # Check if bucket exists
    try:
        bucket_exists = False
        buckets = s3_client.list_buckets()
        for bucket in buckets['Buckets']:
            if bucket['Name'] == bucket_modified:
                bucket_exists = True
    except Exception as e:
        logger.error(f'Failed Check if bucket exists')
        logger.error(f'e: {e}')
        raise e

    # Get Bucket Policy
    add_policy_ssl = True
    add_policy_org_only = True
    current_policy = False
    if bucket_exists:
        # Evaluate for SSL
        try:
            policy = s3_client.get_bucket_policy(
                Bucket=bucket_modified
            )
            current_policy = json.loads(policy['Policy'])
            logger.debug(f"current_policy: {current_policy}")

            successful_evaluation = compare_policy_ssl(
                current_policy
            )
            logger.info(f'successful_evaluation for SSL: {successful_evaluation}')
            if successful_evaluation:
                add_policy_ssl = False

        except (Exception,):
            logger.warning(f'bucket_modified does not have required policies attached')

        # Evaluate for Org Only Access
        try:
            time.sleep(1)
            policy = s3_client.get_bucket_policy(
                Bucket=bucket_modified
            )
            current_policy = json.loads(policy['Policy'])
            logger.debug(f"current_policy: {current_policy}")

            successful_evaluation = compare_policy_org_only(
                current_policy
            )
            logger.info(f'successful_evaluation for Org Only: {successful_evaluation}')
            if successful_evaluation:
                add_policy_org_only = False

        except (Exception,):
            logger.warning(f'bucket_modified does not have required policies attached')

    # Add SSL Bucket Policy
    reevaluate_ssl = False
    if add_policy_ssl:
        try:
            logger.info(f'Adding SSL Policy to {bucket_modified}...')
            add_ssl_policy(
                s3_client,
                bucket_modified,
                current_policy
            )
            reevaluate_ssl = True
        except Exception as e:
            logger.error(f'Failed adding SSL Bucket Policy')
            logger.error(f'e: {e}')
            raise e

    # Add Org Only Bucket Policy
    reevaluate_org_only = False
    if add_policy_org_only:
        try:
            logger.info(f'Adding Org Only Policy to {bucket_modified}...')
            add_org_only_policy(
                s3_client,
                bucket_modified,
                current_policy
            )
            reevaluate_org_only = True
        except Exception as e:
            logger.error(f'Failed adding Org Only Bucket Policy')
            logger.error(f'e: {e}')
            raise e

    # Reevaluate for ssl
    if reevaluate_ssl:
        try:
            logger.info(f'Reevaluating for SSL...')
            policy = s3_client.get_bucket_policy(
                Bucket=bucket_modified
            )
            current_policy = json.loads(policy['Policy'])
            successful_evaluation = compare_policy_ssl(
                current_policy
            )
            logger.info(f'successful_evaluation for SSL: {successful_evaluation}')
        except Exception as e:
            logger.error(f'Failed reevaluating Bucket Policy')
            logger.error(f'e: {e}')
            raise e

    # Reevaluate for org only
    if reevaluate_org_only:
        try:
            logger.info(f'Reevaluating for Org Only...')
            policy = s3_client.get_bucket_policy(
                Bucket=bucket_modified
            )
            current_policy = json.loads(policy['Policy'])
            successful_evaluation = compare_policy_ssl(
                current_policy
            )
            logger.info(f'successful_evaluation for Org Only: {successful_evaluation}')
        except Exception as e:
            logger.error(f'Failed reevaluating Bucket Policy')
            logger.error(f'e: {e}')
            raise e


def compare_policy_ssl(
        current_policy
):
    """
    Evaluates a bucket policy to identify if it contains the requirement defined
    :param current_policy: (dict) the current bucket policy
    :return: (Bool) if the evaluation was successful
    """
    deny = False
    action = False
    ssl_required = False
    successful_evaluation = False

    # Evaluate Statements
    for statement in current_policy['Statement']:
        logging.debug(f"statement['Effect']: {statement['Effect']}")
        if statement['Effect'] == 'Deny':
            deny = True
            logging.debug(f'deny: {deny}')

        logging.debug(f"statement['Action']: {statement['Action']}")
        if statement['Action'] == 's3:*':
            action = True
            logging.debug(f'action: {action}')

        try:
            logging.debug(f"statement['Condition']['Bool']['aws:SecureTransport']: "
                          f"{statement['Condition']['Bool']['aws:SecureTransport']}")
            if statement['Condition']['Bool']['aws:SecureTransport'] == 'false':
                ssl_required = True
                logging.debug(f'ssl_required: {ssl_required}')
        except (Exception,):
            ssl_required = False

        if deny and action and ssl_required:
            successful_evaluation = True

    return successful_evaluation


def compare_policy_org_only(
        current_policy
):
    """
    Evaluates a bucket policy to identify if it contains the requirement defined
    :param current_policy: (dict) the current bucket policy
    :return: (Bool) if the evaluation was successful
    """
    deny = False
    action = False
    org_only_required = False
    successful_evaluation = False

    # Evaluate Statements
    for statement in current_policy['Statement']:
        logging.debug(f"statement['Effect']: {statement['Effect']}")
        if statement['Effect'] == 'Deny':
            deny = True
            logging.debug(f'deny: {deny}')

        logging.debug(f"statement['Action']: {statement['Action']}")
        if statement['Action'] == 's3:*':
            action = True
            logging.debug(f'action: {action}')

        try:
            logging.debug(f"statement['Condition']['StringNotEquals']['aws:ResourceOrgID']: "
                          f"{statement['Condition']['StringNotEquals']['aws:ResourceOrgID']}")
            if statement['Condition']['StringNotEquals']['aws:ResourceOrgID'] == os.environ['orgId']:
                org_only_required = True
                logging.debug(f'org_only_required: {org_only_required}')
        except (Exception,):
            org_only_required = False

        if deny and action and org_only_required:
            successful_evaluation = True

    return successful_evaluation


def add_ssl_policy(
        s3_client,
        bucket,
        current_policy
):
    """
    Adds the defined policy or policy statement to S3 bucket
    :param s3_client: boto3.client
    :param bucket: (String) the bucket name to add the policy
    :param current_policy: (dict) the current bucket policy to add to
    :return: None
    """
    ssl_statement = {
        "Sid": "AllowSSLRequestsOnly",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [
            "arn:aws:s3:::" + bucket,
            "arn:aws:s3:::" + bucket + "/*"
        ],
        "Condition": {
            "Bool": {
                "aws:SecureTransport": "false"
            }
        }
    }

    new_policy = {
        "Version": "2012-10-17",
        "Statement": [
            ssl_statement
        ]
    }

    if current_policy:
        current_policy['Statement'].append(ssl_statement)
        logging.debug(current_policy)
        current_policy = json.dumps(current_policy)
        s3_client.put_bucket_policy(
            Bucket=bucket,
            Policy=current_policy
        )
    else:
        new_policy = json.dumps(new_policy)
        s3_client.put_bucket_policy(
            Bucket=bucket,
            Policy=new_policy
        )


def add_org_only_policy(
        s3_client,
        bucket,
        current_policy
):
    """
    Adds the defined policy or policy statement to S3 bucket
    :param s3_client: boto3.client
    :param bucket: (String) the bucket name to add the policy
    :param current_policy: (dict) the current bucket policy to add to
    :return: None
    """
    org_only_statement = {
        "Sid": "DenyS3AccessOutsideOrg",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [
            "arn:aws:s3:::" + bucket,
            "arn:aws:s3:::" + bucket + "/*"
        ],
        "Condition": {
            "StringNotEquals": {
                "aws:ResourceOrgID": os.environ['orgId']
            }
        }
    }

    new_policy = {
        "Version": "2012-10-17",
        "Statement": [
            org_only_statement
        ]
    }

    if current_policy:
        current_policy['Statement'].append(org_only_statement)
        logging.debug(current_policy)
        current_policy = json.dumps(current_policy)
        s3_client.put_bucket_policy(
            Bucket=bucket,
            Policy=current_policy
        )
    else:
        new_policy = json.dumps(new_policy)
        s3_client.put_bucket_policy(
            Bucket=bucket,
            Policy=new_policy
        )
