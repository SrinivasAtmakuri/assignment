#!/bin/python3.6

from ansible.module_utils.basic import *
import ansible.errors
import requests

import sys
import libvirt

def main():

    fields = {
        "domain_name": {"required": True, "type": "str"}
    }

    module = AnsibleModule(argument_spec=fields)
    domain_name = module.params['domain_name']

    try:
        conn = libvirt.open('qemu:///system')
    except libvirt.libvirtError:
        raise AnsibleError('Failed to open connection to hypervisor')

    try:
        dom = conn.lookupByName(domain_name)

        if dom.isActive():
            result = "active"
        else:
            result = "not-active"
    except libvirt.libvirtError:
        #result = "Domain not found: no domain with matching name: " + domain_name
        result = "domain-not-found"

    conn.close()
    #exit(0)
    module.exit_json(meta=result)

if __name__ == '__main__':
    main()
