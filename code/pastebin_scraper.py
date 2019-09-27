import os
import json
import logging
import requests
import boto3
import common
import PasteHunter.inputs.pastebin as pb

ddb = boto3.resource('dynamodb')
table_name = os.environ['PASTEBIN_TABLE_NAME']
table = ddb.Table(table_name)
#_lambda = boto3.client('lambda')

logger = logging.getLogger("pastehunter-serverless")

def main(event, context):
    conf = common.parse_config()
    if not conf:
        raise Exception("Error: failed to parse config settings file")
    
    # we ignore history but it is required for PB inputs script
    dummy_history = []
    pastes, _ = pb.recent_pastes(conf, dummy_history)

    if len(pastes) > 0:
        logger.debug(f"Received {len(pastes)} from pastebin.com")
        
        prepared_pastes = common.prepare_paste_items(pastes)
        for paste in prepared_pastes:
            table.put_item(Item=paste, ConditionExpression='attribute_not_exists(Id)')
    
    return {'status_code': 200, 'paste_count': len(pastes)}