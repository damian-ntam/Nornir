#!/usr/local/bin/python3

'''
This script is used to collect discovery information from IOS devices. 

'''

from nornir import InitNornir
from nornir.core.filter import F
from nornir.plugins.tasks import text, files
from nornir.plugins.functions.text import print_result
from nornir.plugins.tasks.networking import netmiko_send_command

def grab_info(task):

    # show commands to be run
    commands = [
        "show version",
        "show run",
        "show vlan brief",
        "show interface trunk",
        "show ip interface brief",
        "show ip route",
        "show cdp neighbors",
        "show cdp neighbors detail"
        ]

    # loop over commands
    for cmd in commands:
        # send command to device
        task.host.output = task.run(task=netmiko_send_command, command_string=cmd)
        

def main():

    # initialize The Norn
    nr = InitNornir()

    # filter The Norn to nxos
    nr = nr.filter(platform="nxos")

    result = nr.run(task=grab_info)

    print_result(result)


if __name__ == "__main__":
    main()