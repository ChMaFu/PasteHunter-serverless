import os
import sys
import hashlib
import time
import json
import logging
import yara
import requests
import datetime
from urllib.parse import unquote_plus

logger = logging.getLogger("pastehunter")

def parse_serverless_config():
    """ Returns PasteHunter serverless specific configuration; separate from PasteHunter project config values
        Depnds on environment variables being set:
            export PH_SERVERLESS_ROOT=(root folder for serverless project)
            export PASTEHUNTER_ROOT=(root folder for PasteHunter submodule project)
    """
    pastehunter_config = parse_pastehunter_config()

    config = {}
    config['code_root'] = os.path.join(os.environ['PH_SERVERLESS_ROOT'], "code")
    config['pastehunter_root'] = os.environ['PASTEHUNTER_ROOT']
    config['pastehunter_settings_file'] = os.path.join(config['code_root'], "settings.json")
    config['pastehunter_default_settings_file'] = os.path.join(config['pastehunter_root'], "settings.json.sample")
    config['yara_rule_path'] = os.path.join(config['pastehunter_root'], pastehunter_config['yara']['rule_path'])
    
    return config

def parse_pastehunter_config():
    """ Wrapper for original name for PH config parser """
    conf_file = os.path.join(os.environ['PASTEHUNTER_ROOT'], 'settings.json')
    return _parse_config(conf_file)

def store_pastehunter_config(conf):
    """ Write back to the 'settings.json' file with updated settings values """
    conf_file = os.path.join(os.environ['PASTEHUNTER_ROOT'], 'settings.json')
    with open(conf_file, 'w') as f:
        json.dump(conf, fp=f, indent=2)

def _parse_config(conf_file = 'settings.json'):
    """ Parse the PasteHunter config file in to a dict """
    conf = None
    try:
        with open(conf_file, 'r') as read_conf:
            conf = json.load(read_conf)
    except Exception as e:
        logger.error("Unable to parse config file: {0}".format(e))

    return conf

def prepare_paste_items(pastes):
    """ Prepare 'raw' list of Pastebin paste items for insert to DynamoDB table """
    
    new_pastes = []
    int_values = ['date', 'size']
    str_values = ['title', 'user', 'syntax']
    
    for paste in pastes:
        # make sure date values are int, not string
        for key in int_values:
            if key in paste:
                paste[key] = int(paste[key])
        
        # DynamoDB does not accept empty/null string values
        for key in str_values:         
            if key in paste and len(paste[key]) == 0:
                del paste[key]

        new_pastes.append(paste)
        
    return new_pastes

def yara_index(rule_path, blacklist, test_rules):
    """ Generate 'index.yar' file for all Yara rule files in the given folder based on PasteHunter rules """
    index_file = os.path.join(rule_path, 'index.yar')
    with open(index_file, 'w') as yar:
        for filename in os.listdir(rule_path):
            if filename.endswith('.yar') and filename != 'index.yar':
                if filename == 'blacklist.yar':
                    if blacklist:
                        logger.info("Enable Blacklist Rules")
                    else:
                        continue
                if filename == 'test_rules.yar':
                    if test_rules:
                        logger.info("Enable Test Rules")
                    else:
                        continue
                include = 'include "{0}"\n'.format(filename)
                yar.write(include)

def load_yara_rules(rule_path=None):
    """ Load the 'index.yar' file from the given path and return a Yara Rules object for the referenced rules"""
    
    if rule_path is None:
        c = parse_serverless_config()
        rule_path = c['yara_rule_path']

    index_file = os.path.join(rule_path, 'index.yar')
    rules = yara.compile(index_file)
    return rules

def unpack_ddb_paste_records(records):
    logger.info("Unpacking len(records) records from DDB")

    cleaned_records = []

    for record in records:
        if record['eventName'] == 'INSERT':
            ddb_item = record['dynamodb']['NewImage']

            rec = {}
            rec['pasteid'] = ddb_item['pasteid']['S']
            rec['scrape_url'] = ddb_item['scrape_url']['S']
            rec['date'] = datetime.datetime.fromtimestamp(int(ddb_item['date']['N'])).isoformat()
            rec['size'] = int(ddb_item['size']['N'])
            rec['syntax'] = ddb_item['syntax']['S']
            rec['expire'] = int(ddb_item['expire']['N'])
            cleaned_records.append(rec)

    return cleaned_records

