import os
import json
import requests
import logging
import boto3
from PasteHunter.common import parse_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s:%(filename)s:%(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def lambda_handler(event, context):
    conf = parse_config()
    if not conf:
        raise Exception("Error: failed to parse config settings file")
    
    queue_name = os.environ["PASTEBIN_QUEUE_NAME"]
    if not queue_name:
        raise Exception("Error: no SQS name provided in environment")