#!/bin/python3.6

from ansible.module_utils.basic import *
import ansible.errors
import requests

import libvirt
import libxml2
from argparse import ArgumentParser
from typing import Tuple
import sys

def read_domain(fdomain_xml: str) -> Tuple[str, str]:
    fp = open(fdomain_xml, "r")
    domain_xmldesc = fp.read()
    fp.close()

    doc = libxml2.parseDoc(domain_xmldesc)
    domain_name = doc.xpathNewContext().xpathEval("/domain/name")[0].content
    return (domain_name, domain_xmldesc)

def main():

    fields = {
        "domain_xml": {"required": True, "type": "str"}
    }

    module = AnsibleModule(argument_spec=fields)
    domain_xml = module.params['domain_xml']
    (domain_name, domain_xmldesc) = read_domain(domain_xml)

    conn = libvirt.open('qemu:///system')

    dom = conn.createLinux(domain_xmldesc, 0)
    if dom is None:
        run_status = "Success"
    else:
        run_status = "Failed"

    conn.close()
    module.exit_json(meta=run_status)

if __name__ == '__main__':
    main()

