#!/bin/python3.6

import libvirt
import libxml2
from argparse import ArgumentParser
from typing import Tuple
import sys
import time
import os

def if_conn_is_alive(conn: libvirt.virConnect) -> bool:
    try:
        return conn.isAlive()
    except libvirt.libvirtError as ex:
        error_code = ex.get_error_code()
        if error_code == libvirt.VIR_ERR_INVALID_CONN:
            print("ERROR: Invalid Connection Object")
        elif error_code == libvirt.VIR_ERR_NO_CONNECT:
            print("ERROR: Cannot connect too hypervisor")

def read_domain(fdomain_name: str) -> Tuple[str, str]:
    fp = open(fdomain_name, "r")
    domain_xmldesc = fp.read()
    fp.close()

    doc = libxml2.parseDoc(domain_xmldesc)
    domain_name = doc.xpathNewContext().xpathEval("/domain/name")[0].content
    return (domain_name, domain_xmldesc)

def define_xml(conn: libvirt.virConnect, domain_name: str, domain_xmldesc: str) -> None:
    print("Defining XML for " +domain_name, file=sys.stdout)
    try:
        dom = conn.defineXML(domain_xmldesc)
    except libvirt.libvirtError as ex:
        print('Failed to define a domain from an XML definition.', file=sys.stderr)
        error_code = ex.get_error_code()
        if error_code == libvirt.VIR_ERR_XML_ERROR:
            print('ERROR: XML description is not well formed or broken %s' % ex, file=sys.stderr)
        elif error_code == libvirt.VIR_ERR_XML_INVALID_SCHEMA:
            print('ERROR: invalid schema %s' % ex, file=sys.stderr)
        elif error_code == libvirt.VIR_ERR_XML_DETAIL:
            print('ERROR: Details of XML Error %s' % ex, file=sys.stderr)
        elif error_code == libvirt.VIR_ERR_DOM_EXIST:
            print('ERROR: Try to create an already existing domain %s' % ex, file=sys.stderr)
        exit(1)

def launch_instance(conn: libvirt.virConnect, domain_name: str, domain_xmldesc: str) -> bool:
    print("Creating domain %s ... " % domain_name)
    try:
        dom = conn.createLinux(domain_xmldesc, 0)
    except libvirt.libvirtError as ex:
        error_code = ex.get_error_code()
        if error_code == libvirt.VIR_ERR_DOM_EXIST:
            print('ERROR: Try to create an already existing domain %s' % ex, file=sys.stderr)
        elif error_code == libvirt.VIR_ERR_OPERATION_TIMEOUT:
            print('ERROR: Timed-out while trying to create', file=sys.stderr)
        
    return False if dom is None else True

def start_instance(dom: libvirt.virDomain, domain_name: str) -> bool:
    print("Starting domain %s ... " % domain_name)
    dom.create()
    return False if dom is None else True

def print_dom_ifaces(conn: libvirt.virConnect, domain_name: str) -> str:
    IP = ""
    dom = domain_lookupByName(conn, domain_name)
    ifaces = dom.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)
    if ifaces is None:
        print("Failed to get domain interfaces")
        exit(0)

    for val in ifaces.values():
        if val['addrs']:
            for ip in val['addrs']:
                IP = ip['addr']
    return IP

def loopcalling(dom: libvirt.virDomain, desired_state: int, current_state: int, time_lapsed: float, timeout: float) -> int:
    if time_lapsed < timeout:
        current_state, reason = dom.state()
        if desired_state == current_state:
            return desired_state
        else:
            time.sleep(10)
            time_lapsed = time_lapsed + 10.0
            loopcalling(dom, desired_state, current_state, time_lapsed, timeout)
    return current_state

def print_current_state(current_state: int) -> None:
    if current_state == libvirt.VIR_DOMAIN_NOSTATE:
        print('The state is VIR_DOMAIN_NOSTATE')
    elif current_state == libvirt.VIR_DOMAIN_RUNNING:
        print('The state is RUNNING')
    elif current_state == libvirt.VIR_DOMAIN_BLOCKED:
        print('The state is VIR_DOMAIN_BLOCKED')
    elif current_state == libvirt.VIR_DOMAIN_PAUSED:
        print('The state is VIR_DOMAIN_PAUSED')
    elif current_state == libvirt.VIR_DOMAIN_SHUTDOWN:
        print('The state is VIR_DOMAIN_SHUTDOWN')
    elif current_state == libvirt.VIR_DOMAIN_SHUTOFF:
        print('The state is VIR_DOMAIN_SHUTOFF')
    elif current_state == libvirt.VIR_DOMAIN_CRASHED:
        print('The state is VIR_DOMAIN_CRASHED')
    elif current_state == libvirt.VIR_DOMAIN_PMSUSPENDED:
        print('The state is VIR_DOMAIN_PMSUSPENDED')
    else:
        print(' The state is unknown.')

def check_if_domains_is_defined(conn: libvirt.virConnect, domain_name: str) -> bool:
    try:
        defined_domains = conn.listDefinedDomains()
    except libvirt.libvirtError as ex:
        print('Failed to get a list of domain names', file=sys.stderr)
        print('ERROR %s' % ex, file=sys.stderr)
        exit(1)
    if domain_name in defined_domains:
        print("Domain %s is already defined, checking if running" % domain_name, file=sys.stdout)
        return True
    else:
        print("Domain %s is undefined, creating the domain" % domain_name, file=sys.stdout)
        return False

def domain_lookupByName(conn: libvirt.virConnect, domain_name: str) -> libvirt.virDomain:
    error_code = libvirt.VIR_ERR_OK
    try:
        dom = conn.lookupByName(domain_name)
    except libvirt.libvirtError as ex:
        error_code = ex.get_error_code()
        if error_code == libvirt.VIR_ERR_NO_DOMAIN:
            print("Domain not found: no domain with matching domain_name %s:" % domain_name, file=sys.stderr)
            print("WARNING: %s" % ex, file=sys.stdout)
    return dom

def fetch_active_domain_details(dom: libvirt.virDomain) -> None:
    try:
        print("Domain: id %d running %s." % (dom.ID(), dom.OSType()), file=sys.stdout)
        print("Domain info: %s" % dom.info(), file=sys.stdout)
    except libvirt.libvirtError as ex:
        error_code = ex.get_error_code()
        if error_code == libvirt.VIR_ERR_NO_OS:
            print("WARNING: Missing domain OS inforamtion %s" % ex, file=sys.stdout)
        elif error_code == libvirt.VIR_ERR_OS_TYPE:
            print("WARNING: Unknown OS Type %s" % ex, file=sys.stdout)

def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("file", metavar="DOMAIN.XML", help="XML configuration of the domain in libvirt's XML format")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        raise FileNotFoundError(args.file)

    (domain_name, domain_xmldesc) = read_domain(args.file)

    status = None
    error_code = libvirt.VIR_ERR_OK
    desired_state = libvirt.VIR_DOMAIN_RUNNING

    try:
        conn = libvirt.open('qemu:///system')
    except libvirt.libvirtError as ex:
        error_code = ex.get_error_code()
        if error_code == libvirt.VIR_ERR_INTERNAL_ERROR:
            print('Failed to open connection to the hypervisor', file=sys.stderr)
            print('ERROR: %s' % ex, file=sys.stderr)
        else:
            print('Failed to open connection to the hypervisor', file=sys.stderr)
        exit(1)

    print("Checking if domain is defined")
    if check_if_domains_is_defined(conn, domain_name):
            
        dom = domain_lookupByName(conn, domain_name)

        if dom.isActive():
            print("The domain %s is active" % domain_name, file=sys.stdout)
            fetch_active_domain_details(dom)
        else:
            print("The domain %s is not active" % domain_name, file=sys.stdout)
            #define_xml(conn,domain_name,domain_xmldesc)
            status = start_instance(dom,domain_name)
    else:
            status = launch_instance(conn,domain_name,domain_xmldesc)

    if status == "True":
        print("Launch Success", file=sys.stdout)
        current_state = loopcalling(dom, desired_state, 0, time.time(), time.time() + 120.0)
        print_current_state(current_state)
        IP = print_dom_ifaces(conn,domain_name)
    elif status == "False":
        print("Launch Failed", file=sys.stderr)
        exit(1)

    conn.close()
    exit(0)

if __name__ == "__main__":
    main()