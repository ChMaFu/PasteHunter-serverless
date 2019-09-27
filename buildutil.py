import pprint
import os
import sys
import yara
import logging
import shutil
import code.common as common

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("buildutil")
logger.setLevel(logging.INFO)

def main():

    logger.info("Starting build process")
    serverless_config = common.parse_serverless_config()

    logger.info("Copying sample config file to runtime location")    
    shutil.copyfile(serverless_config['pastehunter_default_settings_file'], serverless_config['pastehunter_settings_file'])

    logging.info(f"Using settings file: {serverless_config['pastehunter_settings_file']}")
    pastehunter_config = common.parse_pastehunter_config()
    if pastehunter_config is None:
        logger.info("Error: failed to load pastehunter config file. Exitting.")
        sys.exit(1)

    logger.info("Configuration settings loaded")

    logger.info("General->run_frequency: {} sec".format(pastehunter_config["general"]["run_frequency"]))
    
    logger.info("Updating PasteHunter config settings to preferred values...")
    update_setting_values(pastehunter_config)
    common.store_pastehunter_config(pastehunter_config)
    print_config_summary(pastehunter_config)
    logger.info("PasteHunter config values updated and saved")

    # generate the index.yar file prior to build
    yara_rule_path = os.path.join(serverless_config['pastehunter_root'], pastehunter_config['yara']['rule_path'])
    common.yara_index(yara_rule_path, pastehunter_config['yara']['blacklist'], pastehunter_config['yara']['test_rules'])
    logger.info("Yara rules index generated")

    # confirm Yara syntax is valid
    try:
        rules = common.load_yara_rules(yara_rule_path)
        logger.info("Yara rules compiled successfully")
    except Exception as e:
        logger.info("Error validating Yara file syntax.")
        logger.info(e)
        sys.exit(1)        

def print_config_summary(conf):
    logger.info("Inputs enabled status")
    for k in conf['inputs'].keys():
        input = k
        enabled = conf['inputs'][input]['enabled']
        logger.info(f"> Input '{input}', enabled = {enabled}")


def update_setting_values(conf):
    """ Update settings to our preferred values 
    
        :param conf: PasteHunter configuration dictionary to be updated
        :return: Update configuration dictionary
    """
    
    # inputs
    conf['inputs']['pastebin']['enabled'] = True
    conf['inputs']['dumpz']['enabled'] = False
    conf['inputs']['gists']['enabled'] = True
    conf['inputs']['slexy']['enabled'] = False
    conf['inputs']['stackexchange']['enabled'] = False

    # outputs
    conf['outputs']['elastic_output']['enabled'] = False
    conf['outputs']['json_output']['enabled'] = False
    conf['outputs']['csv_output']['enabled'] = False
    conf['outputs']['syslog_output']['enabled'] = False
    conf['outputs']['smtp_output']['enabled'] = False
    conf['outputs']['slack_output']['enabled'] = False
    conf['outputs']['twilio_output']['enabled'] = False

    # post processing
    conf['post_process']['post_email']['enabled'] = True
    conf['post_process']['post_b64']['enabled'] = True
    conf['post_process']['post_b64']['viper']['enabled'] = False
    conf['post_process']['post_b64']['cuckoo']['enabled'] = False
    conf['post_process']['post_entropy']['enabled'] = True

    return conf


if __name__ == '__main__':
    main()