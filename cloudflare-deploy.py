#!/usr/bin/env python
import logging

import sys
import CloudFlare
import os
import re

from os import path
from certbot.plugins import dns_common

__author__ = "Endrigo Antonini"
__copyright__ = "Copyright 2020, Endrigo Antonini"
__license__ = "Apache License 2.0"
__version__ = "1.0"
__maintainer__ = "Endrigo Antonini"
__email__ = "eantonini@eidoscode.com"
__status__ = "Production"

logger = logging.getLogger(__name__)


DEFAULT_CERT_FOLDER = "/etc/letsencrypt/live"
CERTBOT_CONF_DIR = "/etc/letsencrypt/renewal"

PROPERTIES = {}


def read_file(filename):
  """
  Read a file from disk and return all the content

  :param str filename: File name of the file that is going to read.
  :raises Exception: if the file doesn't exists
  """
  if not path.isfile(filename):
    raise Exception("File {} doesn't exists!".format(filename))
  with open(filename) as f:
    return f.read()


def read_certificate(filename):
  return re.sub('\r?\n', '\\n', read_file(filename))


def read_properties_file(file):
  myvars = {}
  if not path.isfile(file):
    raise Exception("Config file {} doesn't exists!".format(file))
  with open(file) as myfile:
    for line in myfile:
      name, var = line.partition("=")[::2]
      myvars[name.strip()] = var.strip()
  return myvars


def read_domain_properties(domain):
  global PROPERTIES
  if domain in PROPERTIES:
    return PROPERTIES[domain]

  config_file="{}/{}.conf".format(CERTBOT_CONF_DIR, domain)
  myvars = read_properties_file(config_file)
  PROPERTIES[domain] = myvars
  return myvars


def connect_cloudflare(domain):
  print("Connection to Cloudflare of domain {}".format(domain))
  properties = read_domain_properties(domain)
  cred_file = None
  if not "dns_cloudflare_credentials" in properties:
    raise Exception("File {} doesn't have property dns_cloudflare_api_token on it.".format(cred_file))

  cred_file = properties["dns_cloudflare_credentials"]
  props = read_properties_file(cred_file)

  if not "dns_cloudflare_api_token" in props:
    raise Exception("File {} doesn't have property dns_cloudflare_api_token on it.".format(cred_file))

  api_key = props["dns_cloudflare_api_token"]

  return CloudFlare.CloudFlare(token=api_key)


def find_zone_id(cf, domain):
  zone_name_guesses = dns_common.base_domain_name_guesses(domain)
  zones = []  # type: List[Dict[str, Any]]
  code = msg = None

  for zone_name in zone_name_guesses:
    params = {'name': zone_name,
              'per_page': 1}

    try:
        zones = cf.zones.get(params=params)  # zones | pylint: disable=no-member
    except CloudFlare.exceptions.CloudFlareAPIError as e:
      code = int(e)
      msg = str(e)
      hint = None

      if code == 6003:
        hint = ('Did you copy your entire API token/key? To use Cloudflare tokens, '
                  'you\'ll need the python package cloudflare>=2.3.1.{}'
          .format(' This certbot is running cloudflare ' + str(CloudFlare.__version__)
        if hasattr(CloudFlare, '__version__') else ''))
      elif code == 9103:
        hint = 'Did you enter the correct email address and Global key?'
      elif code == 9109:
        hint = 'Did you enter a valid Cloudflare Token?'

      if hint:
        raise Exception('Error determining zone_id: {0} {1}. Please confirm '
                        'that you have supplied valid Cloudflare API credentials. ({2})'
                                                               .format(code, msg, hint))
      else:
        logger.debug('Unrecognised CloudFlareAPIError while finding zone_id: %d %s. '
                       'Continuing with next zone guess...', e, e)

    if zones:
      zone_id = zones[0]['id']
      logger.debug('Found zone_id of %s for %s using name %s', zone_id, domain, zone_name)
      return zone_id

  raise Exception('Unable to determine zone_id for {0} using zone names: {1}. '
                            'Please confirm that the domain name has been entered correctly '
                            'and is already associated with the supplied Cloudflare account.{2}'
                            .format(domain, domain, ' The error from Cloudflare was:'
                            ' {0} {1}'.format(code, msg) if code is not None else ''))


def upload_certificate(domain):
  cf = connect_cloudflare(domain)
  private_key = read_certificate("{}/{}/privkey.pem".format(DEFAULT_CERT_FOLDER, domain))
  fullchain = read_certificate("{}/{}/fullchain.pem".format(DEFAULT_CERT_FOLDER, domain))

  zone_id = find_zone_id(cf, domain)
  logger.debug("Cloudflare Zone id {} of domain {} ".format(zone_id, domain))

  data = {'certificate': fullchain,
        'private_key': private_key,
        'bundle_method': 'ubiquitous'}


  print("Going to deploy certificate.")
  try:
    cf.zones.custom_certificates.post(zone_id, data=data)
    print("Depoyed.")
  except CloudFlare.exceptions.CloudFlareAPIError as e:
    code = int(e)
    msg = str(e)
    hint = None
    if code == 1228:
      print("Cert already deployed.")
    else:
      logger.error(code)
      logger.error(msg)
      raise e
  return


def main():
  domains_str = os.environ['RENEWED_DOMAINS']
  domains_lst = domains_str.split()
  for domain in domains_lst:
    print("")
    print("Start domain {} checking".format(domain))
    zone_name_guesses = dns_common.base_domain_name_guesses(domain)
    zone_domain = None
    for temp_zone_domain in zone_name_guesses:
      temp_config_file = "{}/{}.conf".format(CERTBOT_CONF_DIR, temp_zone_domain)
      logger.debug("Checking zone {} -- {}".format(temp_zone_domain, temp_config_file))
      if path.isfile(temp_config_file):
        zone_domain = temp_zone_domain
        break
    if zone_domain is None:
      raise Exception("It wasn't possible to continue. There is no config file for domain {}.".format(domain))
    upload_certificate(zone_domain)


if __name__ == '__main__':
  main()