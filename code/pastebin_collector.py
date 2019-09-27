import os
import json
import logging
import requests
import boto3
import common
import pastescanner
import PasteHunter.inputs.pastebin as pb

ddb = boto3.resource('dynamodb')
table = ddb.Table(os.environ['PASTEBIN_TABLE_NAME'])
_lambda = boto3.client('lambda')

logger = logging.getLogger("pastehunter-serverless")

def main(event, context):
    conf = common.parse_config()
    if not conf:
        raise Exception("Error: failed to parse config settings file")

    # reproduce the original format of the paste item to preserve existing logic for retrieval and post processing
    paste_data_records = common.unpack_ddb_paste_records(event['Records'])
    for paste_data in paste_data_records:

        