import boto3
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# CONST
SEND_FROM = "dguerra@rgbarry.com"
SUBJECT = "Newly Created User"
SMTP_SERVER = 'rgbexc01.rgbarry.local'


def lambda_handler(event, context):
    # Logging
    logger = logging.getLogger()
    # logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    logger.debug(f'event: {event}')
    logger.debug(f'context: {context}')

    # Get info from event
    try:
        executing_user = event['detail']['userIdentity']['principalId']
        executing_user = executing_user.split(':')[1]
        logger.info(f'executing_user: {executing_user}')

        user_created = event['detail']['requestParameters']['userName']
        logger.info(f'user_created: {user_created}')
    except Exception as e:
        logger.error(f'Error getting information from event')
        logger.error(f'e: {e}')
        raise e

    # Send Email
    try:
        body = 'Your ID ' + executing_user + ' has been detected to have created a new ' \
            'AWS IAM User (' + user_created + '). This is not the prefered means of providing ' \
            'access to AWS.  Someone from IT NET OPS (itnetops@) will be reaching out to you ' \
            'shortly to identify if this type of access is necessary.'
        send_email(
            executing_user,
            SEND_FROM,
            'Non-Prod Account - ' + SUBJECT,
            body
        )
    except Exception as e:
        logger.error(f'Failed sending email')
        logger.error(f'e: {e}')
        raise e


def send_email(
        send_to,
        send_from,
        subject,
        body
):
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = send_to + '; dguerra@rgbarry.com'
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    text = msg.as_string()
    s = smtplib.SMTP(SMTP_SERVER)
    s.sendmail(send_from, send_to, text)
    s.quit()
