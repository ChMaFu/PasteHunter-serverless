import os
import json
import requests
import logging
import boto3

GETIP_URL = "http://ifconfig.me" # "http://checkip.amazonaws.com"

logger = logging.getLogger('pastehunter')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s:%(filename)s:%(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def lambda_handler(event, context):
    conf = parse_config()
    if not conf:
        raise Exception("Error parseing config settings file")
    
    q_url = os.environ["SQS_URL"]
    if not q_url:
        raise Exception("Error: no SQS URL provided in environment")
    
    api_scrape = conf["inputs"]["pastebin"]["api_scrape"]
    paste_limit = conf['inputs']['pastebin']['paste_limit']
    scrape_uri = '{0}?limit={1}'.format(api_scrape, paste_limit)
    logger.info(f"Scrape URI: {scrape_uri}")
    r = requests.get(scrape_uri)

    if r.status_code == 200:
        sqsclient = boto3.client("sqs")
        pastes = r.json()
        for paste in pastes:
            sqsclient.send_message(QueueUrl=q_url, MessageBody=json.dumps(paste))
        return {'status_code': 200, 'paste_count': len(pastes)}
    else:
        return {'status_code': r.status_code, 'message': r.text}

def parse_config():
    conf_file = 'settings.json'
    conf = None
    try:
        with open(conf_file, 'r') as read_conf:
            conf = json.load(read_conf)
    except Exception as e:
        logger.error("Unable to parse config file: {0}".format(e))

    return conf

if __name__ == "__main__":
    lambda_handler(None, None)