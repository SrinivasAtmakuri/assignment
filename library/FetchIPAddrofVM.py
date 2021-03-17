#!/bin/python3.6

from ansible.module_utils.basic import *
import ansible.errors
import requests

import libvirt
from argparse import ArgumentParser

def main():
    conn = libvirt.open("qemu:///system")

    fields = {
        "domain_name": {"required": True, "type": "str"}
    }

    IP = "0.0.0.0"

    module = AnsibleModule(argument_spec=fields)
    domain_name = module.params['domain_name']

    domain = conn.lookupByName(domain_name)
    ifaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)
    if ifaces is None:
        print("Failed to get domain interfaces")
        exit(0)

    for val in ifaces.values():
        if val['addrs']:
            for ip in val['addrs']:
                IP = ip['addr']
    
    conn.close()
    module.exit_json(meta=IP)

if __name__ == '__main__':
    main()
