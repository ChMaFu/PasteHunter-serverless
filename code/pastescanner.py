
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
from common import load_yara_rules

logger = logging.getLogger("pastehunter")

PASTEBIN_CACHE_RETRY_PERIOD_SEC = 5
PASTEBIN_CACHE_RETRY_COUNT = 3

def paste_scanner(paste_data, conf):
    """ 
    Modified version of the original 'paste_scanner()' function from the original PasteHunter project 
    
    :param paste_data: the paste item metadata dictionary
    :param conf: the PasteHunter configuration dictionary
    :returns: None
    """

    logger.debug("Found New {0} paste {1}".format(paste_data['pastesite'], paste_data['pasteid']))

    if paste_data['confname'] == 'pastebin':
        raw_paste_data = pastebin_scanner(paste_data, conf)
    elif paste_data['confname'] == 'gists':
        raw_paste_data = gists_scanner(paste_data, conf)
    elif paste_data['confname'] == 'stackexchange':
        raw_paste_data = stackexchange_scanner(paste_data, conf)
    else:
        # not implemented
        logger.debug("Paste scanner not implemented for pastesite = {paste_data['confname']}")

    final_paste = post_process_paste(paste_data, conf, raw_paste_data)

def pastebin_scanner(paste_data, conf):
    """
    PasteBin specific retriever that retrieves the paste item content based on the 'scrape_url' value

    :param paste_data: PasteBin paste item metadata dictionary
    :param conf: the PasteHunter configuration dictionary
    :returns: the raw paste data from Pastebin.com
    """
    logger.debug(f"Processing paste as 'pastebin' item for pastid = {paste_data['pasteid']}")

    retry_count = 0
    while retry_count < PASTEBIN_CACHE_RETRY_COUNT:
        try:
            raw_paste_uri = paste_data['scrape_url']
            raw_paste_data = requests.get(raw_paste_uri).text

        # Cover fetch site SSLErrors
        except requests.exceptions.SSLError as e:
            logger.error("Unable to scan raw paste : {0} - {1}".format(paste_data['pasteid'], e))
            raw_paste_data = ""
        
        # General Exception 
        except Exception as e:
            logger.error("Unable to scan raw paste : {0} - {1}".format(paste_data['pasteid'], e))
            raw_paste_data = ""

        # Pastebin Cache
        if raw_paste_data == "File is not ready for scraping yet. Try again in 1 minute.":
            logger.info("Paste is still cached sleeping to try again")
            time.sleep(PASTEBIN_CACHE_RETRY_PERIOD_SEC)

        retry_count += 1
        
        if raw_paste_data and len(raw_paste_data) > 0:
            return raw_paste_data


def gists_scanner(paste_data, conf):
    """
    Github gists specific retriever that retrieves the paste item content based on the 'scrape_url' value

    :param paste_data: PasteBin paste item metadata dictionary
    :param conf: the PasteHunter configuration dictionary
    :returns: the raw paste/gist data from Github
    """
    logger.debug(f"Processing paste as 'gists' item for pastid = {paste_data['pasteid']}")

    return ""

def stackexchange_scanner(paste_data, conf):
    """
    Stackexchange specific content retriever that retrieves the paste item content based on the 'scrape_url' value

    :param paste_data: PasteBin paste item metadata dictionary
    :param conf: the PasteHunter configuration dictionary
    :returns: the raw paste/gist data from Github
    """    
    logger.debug(f"Processing paste as 'stackexchange' item for pastid = {paste_data['pasteid']}")

    # Stack questions dont have a raw endpoint
    if ('stackexchange' in conf['inputs']) and (paste_data['pastesite'] in conf['inputs']['stackexchange']['site_list']):
        # The body is already included in the first request so we do not need a second call to the API. 
        
        # Unescape the code block strings in the json body. 
        raw_body = paste_data['body']
        raw_paste_data = unquote_plus(raw_body)
        
        # now remove the old body key as we dont need it any more
        del paste_data['body']
    return raw_paste_data

def post_process_paste(paste_data, conf, raw_paste_data):
    """
    Post processing includes checking paste against all active Yara rules for content of interest

    :param paste_data: PasteBin paste item metadata dictionary
    :param conf: the PasteHunter configuration dictionary
    :returns: None
    """
    rules = load_yara_rules()
    try:
        matches = rules.match(data=raw_paste_data)
    except Exception as e:
        logger.error("Unable to scan raw paste : {0} - {1}".format(paste_data['pasteid'], e))

    results = []
    for match in matches:
        # For keywords get the word from the matched string
        if match.rule == 'core_keywords' or match.rule == 'custom_keywords':
            for s in match.strings:
                rule_match = s[1].lstrip('$')
                if rule_match not in results:
                    results.append(rule_match)
            results.append(str(match.rule))
        # Else use the rule name
        else:
            results.append(match.rule)

    # Store all OverRides other options. 
    paste_site = paste_data['confname']
    store_all = conf['inputs'][paste_site]['store_all']
    # remove the confname key as its not really needed past this point
    del paste_data['confname']

    # Blacklist Check
    # If any of the blacklist rules appear then empty the result set
    blacklisted = False
    if conf['yara']['blacklist'] and 'blacklist' in results:
        results = []
        blacklisted = True
        logger.info("Blacklisted {0} paste {1}".format(paste_data['pastesite'], paste_data['pasteid']))


    # Post Process

    # If post module is enabled and the paste has a matching rule.
    post_results = paste_data
    for post_process, post_values in conf["post_process"].items():
        if post_values["enabled"]:
            if any(i in results for i in post_values["rule_list"]) or "ALL" in post_values["rule_list"]:
                if not blacklisted:
                    logger.info("Running Post Module {0} on {1}".format(post_values["module"], paste_data["pasteid"]))
                    post_module = importlib.import_module(post_values["module"])
                    post_results = post_module.run(results,
                                                    raw_paste_data,
                                                    paste_data
                                                    )

    # Throw everything back to paste_data for ease.
    paste_data = post_results


    # If we have a result add some meta data and send to storage
    # If results is empty, ie no match, and store_all is True,
    # then append "no_match" to results. This will then force output.

    if store_all is True:
        if len(results) == 0:
            results.append('no_match')
            
    if len(results) > 0:

        encoded_paste_data = raw_paste_data.encode('utf-8')
        md5 = hashlib.md5(encoded_paste_data).hexdigest()
        sha256 = hashlib.sha256(encoded_paste_data).hexdigest()
        paste_data['MD5'] = md5
        paste_data['SHA256'] = sha256
        paste_data['raw_paste'] = raw_paste_data
        paste_data['YaraRule'] = results
        # Set the size for all pastes - This will override any size set by the source
        paste_data['size'] = len(raw_paste_data)

    return paste_data
