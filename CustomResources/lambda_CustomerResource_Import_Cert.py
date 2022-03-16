# Import Modules
import boto3
import logging
import json
import datetime
from datetime import datetime
import cfnresponse  # <--- Required for custom_resource
import time
import os
import subprocess
import base64


def lambda_handler(event, context):
    # Logging
    logger = logging.getLogger()
    # logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    session = boto3.Session()
    acm_client = session.client('acm')

    logger.debug(f'event: {event}')  # <--- Input from CloudFormation
    logger.debug(f'context: {context}')

    if 'Create' in event['RequestType']:
        try:
            # Get values from Cloudformation properties
            cert_body = event['ResourceProperties']['CertificateBody']
            print(f"cert_body: {cert_body}")
            private_key = event['ResourceProperties']['PrivateKey']
            print(f"private_key: {private_key}")
            cert_chain = event['ResourceProperties']['CertificateChain']
            print(f"cert_chain: {cert_chain}")
            product_name = event['ResourceProperties']['ProductName']
            print(f"product_name: {product_name}")
            owner = event['ResourceProperties']['Owner']
            print(f"owner: {owner}")
            business_unit = event['ResourceProperties']['BusinessUnit']
            print(f"business_unit: {business_unit}")
            team = event['ResourceProperties']['Team']
            print(f"team: {team}")

            directory_contents = os.listdir('/tmp')
            logger.debug(f'INITIAL /tmp directory_contents: {directory_contents}')

            # Format cert_body
            response = format_cert(
                cert_body,
                "/tmp/cert_body.pem"
            )
            if response:
                logger.debug(f'cert_body formatted successfully')
            else:
                # Send Failure
                send_failure(
                    event,
                    context,
                    "Failed to format certs"
                )

            # Format private_key
            response = format_private_key(
                private_key,
                "/tmp/private_key.pem"
            )
            if response:
                logger.debug(f'private_key formatted successfully')
            else:
                # Send Failure
                send_failure(
                    event,
                    context,
                    "Failed to format certs"
                )

            # Format cert_chain
            response = format_cert(
                cert_chain,
                "/tmp/cert_chain.pem"
            )
            if response:
                logger.debug(f'cert_chain formatted successfully')
            else:
                # Send Failure
                send_failure(
                    event,
                    context,
                    "Failed to format certs"
                )

            directory_contents = os.listdir('/tmp')
            logger.debug(f'/tmp directory_contents: {directory_contents}')

            with open("/tmp/cert_body.pem", "rb") as cert_body_file:
                import_cert_body = cert_body_file.read()
                print(f'import_cert_body: {import_cert_body}')
            with open("/tmp/private_key.pem", "rb") as private_key_file:
                import_private_key = private_key_file.read()
                print(f'import_private_key: {import_private_key}')
            with open("/tmp/cert_chain.pem", "rb") as cert_chain_file:
                import_cert_chain = cert_chain_file.read()
                print(f'import_cert_chain: {import_cert_chain}')

            response = acm_client.import_certificate(
                Certificate=import_cert_body,
                PrivateKey=import_private_key,
                CertificateChain=import_cert_chain,
                Tags=[
                    {
                        'Key': 'ProductName',
                        'Value': product_name
                    },
                    {
                        'Key': 'Owner',
                        'Value': owner
                    },
                    {
                        'Key': 'Team',
                        'Value': team
                    },
                    {
                        'Key': 'BusinessUnit',
                        'Value': business_unit
                    },
                ]
            )
            print(f"cert_arn: {response['CertificateArn']}")

            # Send Success
            send_success(
                event,
                context,
                response['CertificateArn']
            )

        except Exception as e:
            logger.error(f'Certificate failed to import.  Please see logs...')

            # Send Failure
            send_failure(
                event,
                context,
                "Failed Creation functionality"
            )
            raise e

    elif 'Update' in event['RequestType']:
        try:
            print('Update function hit')

            # Get values from Cloudformation properties
            cert_arn = event['ResourceProperties']['CertificateArn']
            print(f"cert_arn: {cert_arn}")
            cert_body = event['ResourceProperties']['CertificateBody']
            print(f"cert_body: {cert_body}")
            private_key = event['ResourceProperties']['PrivateKey']
            print(f"private_key: {private_key}")
            cert_chain = event['ResourceProperties']['CertificateChain']
            print(f"cert_chain: {cert_chain}")
            product_name = event['ResourceProperties']['ProductName']
            print(f"product_name: {product_name}")
            owner = event['ResourceProperties']['Owner']
            print(f"owner: {owner}")
            business_unit = event['ResourceProperties']['BusinessUnit']
            print(f"business_unit: {business_unit}")
            team = event['ResourceProperties']['Team']
            print(f"team: {team}")

            # Execute Update only if cert_arn was provided
            if cert_arn:
                # Format cert_body
                response = format_cert(
                    cert_body,
                    "/tmp/cert_body.pem"
                )
                if response:
                    logger.debug(f'cert_body formatted successfully')
                else:
                    # Send Failure
                    send_failure(
                        event,
                        context,
                        "Failed to format certs"
                    )

                # Format private_key
                response = format_private_key(
                    private_key,
                    "/tmp/private_key.pem"
                )
                if response:
                    logger.debug(f'private_key formatted successfully')
                else:
                    # Send Failure
                    send_failure(
                        event,
                        context,
                        "Failed to format certs"
                    )

                # Format cert_chain
                response = format_cert(
                    cert_chain,
                    "/tmp/cert_chain.pem"
                )
                if response:
                    logger.debug(f'cert_chain formatted successfully')
                else:
                    # Send Failure
                    send_failure(
                        event,
                        context,
                        "Failed to format certs"
                    )

                with open("/tmp/cert_body.pem", "rb") as cert_body_file:
                    import_cert_body = cert_body_file.read()
                    print(f'import_cert_body: {import_cert_body}')
                with open("/tmp/private_key.pem", "rb") as private_key_file:
                    import_private_key = private_key_file.read()
                    print(f'import_private_key: {import_private_key}')
                with open("/tmp/cert_chain.pem", "rb") as cert_chain_file:
                    import_cert_chain = cert_chain_file.read()
                    print(f'import_cert_chain: {import_cert_chain}')

                # Update Previously Existing Cert
                acm_client.import_certificate(
                    CertificateArn=cert_arn,
                    Certificate=import_cert_body,
                    PrivateKey=import_private_key,
                    CertificateChain=import_cert_chain
                )

                # Update Cert Tags if needed
                try:
                    acm_client.add_tags_to_certificate(
                        CertificateArn=cert_arn,
                        Tags=[
                            {
                                'Key': 'ProductName',
                                'Value': product_name
                            },
                            {
                                'Key': 'Owner',
                                'Value': owner
                            },
                            {
                                'Key': 'Team',
                                'Value': team
                            },
                            {
                                'Key': 'BusinessUnit',
                                'Value': business_unit
                            },
                        ]
                    )
                except Exception as e:
                    logger.error(f'Failed Update Tags functionality...')

                    # Send Failure
                    send_failure(
                        event,
                        context,
                        "Failed Update Tags functionality"
                    )
                    raise e

                # Send Success
                send_success(
                    event,
                    context,
                    cert_arn
                )
            else:
                logger.debug(f'cert_arn was not provided.  Do nothing.')

                # Send Success
                send_success(
                    event,
                    context,
                    "CertificateArn was not provided during the last Update attempt.  Nothing was changed."
                )
                exit(0)

        except Exception as e:
            logger.error(f'Failed Update functionality...')

            # Send Failure
            send_failure(
                event,
                context,
                "Failed Update functionality"
            )
            raise e

    elif 'Delete' in event['RequestType']:
        try:
            print('Delete function hit')

            # Get values from Cloudformation properties
            cert_arn = event['ResourceProperties']['CertificateArn']
            print(f"cert_arn: {cert_arn}")

            # Execute Update only if cert_arn was provided
            if cert_arn:
                acm_client.delete_certificate(
                    CertificateArn=cert_arn
                )

                # Send Success
                send_success(
                    event,
                    context,
                    "Certificate has been deleted"
                )
            else:
                logger.debug(f'cert_arn was not provided.  Do nothing.')

                # Send Success
                send_success(
                    event,
                    context,
                    "CertificateArn was not provided during the last Update attempt.  Nothing was changed."
                )
                exit(0)

        except Exception as e:
            logger.error(f'Failed Delete functionality...')

            # Send Failure
            send_failure(
                event,
                context,
                "Failed Delete functionality"
            )
            raise e

    else:
        # Send Success
        send_success(
            event,
            context,
            "SUCCESS - Nothing Happened?"
        )


def format_cert(
        contents,
        cert_path
):
    os.chdir('/tmp')
    if os.path.exists(cert_path):
        os.remove(cert_path)
    f = open(cert_path, "a")
    contents = contents.replace('-----BEGIN CERTIFICATE-----', '')
    contents = contents.replace('-----END CERTIFICATE-----', '')
    contents = contents.replace(' ', '\n')
    contents = '-----BEGIN CERTIFICATE-----' + contents + '-----END CERTIFICATE-----\n'
    f.write(contents)
    f.close()

    return True


def format_private_key(
        contents,
        cert_path
):
    os.chdir('/tmp')
    if os.path.exists(cert_path):
        os.remove(cert_path)
    f = open(cert_path, "a")
    contents = contents.replace('-----BEGIN RSA PRIVATE KEY-----', '')
    contents = contents.replace('-----END RSA PRIVATE KEY-----', '')
    contents = contents.replace(' ', '\n')
    contents = '-----BEGIN RSA PRIVATE KEY-----' + contents + '-----END RSA PRIVATE KEY-----\n'
    f.write(contents)
    f.close()

    return True


def send_success(
        event,
        context,
        message
):
    response_data = dict()
    response_data['cert_arn'] = message
    cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, "CustomResourcePhysicalID")


def send_failure(
        event,
        context,
        message
):
    response_data = dict()
    response_data['FAILED'] = message
    cfnresponse.send(event, context, cfnresponse.FAILED, response_data, "CustomResourcePhysicalID")
