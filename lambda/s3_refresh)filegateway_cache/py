import boto3
import logging


def lambda_handler(event, context):
    # Logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # logger.setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    logger.debug(f'event: {event}')
    logger.debug(f'context: {context}')

    # Get Info from Event
    try:
        file_share_name = event['file_share_name']
        logger.debug(f'file_share_name: {file_share_name}')
    except Exception as e:
        logger.error(f'Failed getting info from event')
        logger.error(f'e: {e}')
        raise e

    # Setup Connection
    try:
        session = boto3.Session()
        storage_gateway_client = session.client('storagegateway')
    except Exception as e:
        logger.error(f'Failed creating session')
        logger.error(f'e: {e}')
        raise e

    # List storage_gateways
    try:
        file_shares_to_refresh = []
        storage_gateways = storage_gateway_client.list_gateways()
        for gateway in storage_gateways['Gateways']:
            gateway_arn = gateway['GatewayARN']
            file_share_arn = get_gateway_file_share_arn(
                storage_gateway_client,
                gateway_arn,
                file_share_name
            )
            logger.debug(f'Found file_share_arn: {file_share_arn}')
            file_shares_to_refresh.append(file_share_arn)
    except Exception as e:
        logger.error(f'Failed getting storage_gateways')
        logger.error(f'e: {e}')
        raise e

    # Refresh file_shares
    try:
        logger.info(f'Refreshing File Share Caches...')
        for arn in file_shares_to_refresh:
            storage_gateway_client.refresh_cache(
                FileShareARN=arn,
                FolderList=[
                    '/',
                ],
                Recursive=True
            )
        logger.info(f'File Share Caches has been refreshed')
    except Exception as e:
        logger.error(f'Failed refresh file_shares')
        logger.error(f'e: {e}')
        raise e


def get_gateway_file_share_arn(
        storage_gateway_client,
        gateway_arn,
        file_share_name
):
    file_shares = storage_gateway_client.list_file_shares(
        GatewayARN=gateway_arn
    )
    for file_share in file_shares['FileShareInfoList']:
        response = storage_gateway_client.describe_smb_file_shares(
            FileShareARNList=[
                file_share['FileShareARN']
            ]
        )
        if file_share_name == response['SMBFileShareInfoList'][0]['FileShareName']:
            return response['SMBFileShareInfoList'][0]['FileShareARN']


