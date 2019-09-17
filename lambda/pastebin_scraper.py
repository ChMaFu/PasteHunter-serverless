import os
import json
import requests
import boto3
import util
from PasteHunter.common import parse_config


def main(event, context):
    conf = parse_config()
    if not conf:
        raise Exception("Error: failed to parse config settings file")
    
    table_name = os.environ["PASTEBIN_TABLE_NAME"]
    if not table_name:
        raise Exception("Error: no DynamoDB table name provided in environment")
    
    api_scrape = conf["inputs"]["pastebin"]["api_scrape"]
    paste_limit = conf['inputs']['pastebin']['paste_limit']
    query_params = {'limit': paste_limit}
    r = requests.get(api_scrape, params=query_params)

    if r.status_code == 200:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        pastes = r.json()
        if len(pastes) > 0:
            prepared_pastes = util.prepare_paste_items(pastes)
            for paste in prepared_pastes:
                table.put_item(Item=json.dumps(paste))
        return {'status_code': 200, 'paste_count': len(pastes)}
    else:
        return {'status_code': r.status_code, 'message': r.text}