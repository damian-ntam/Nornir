#!/usr/local/bin/python3

from pprint import pprint
from csv import DictReader
from nornir import InitNornir
from nornir.core.filter import F
from nornir.plugins.tasks import text, files
from nornir.plugins.tasks.networking import netmiko_send_command
from jinja2 import Template, Environment, FileSystemLoader

# add stuff 

# create VLAN mapping table from CSV file
def create_mapping_table():
    # init mapping dict
    mapping_dict = {}

    #csv_file = input("Please enter the CSV file name: ")
    csv_file = "vlan_mapping.csv"

    with open(csv_file, newline='', encoding='utf-8-sig') as csvfile:
        # open and read CSV
        reader = DictReader(csvfile)
        for row in reader:
            # write row to mapping dict
            mapping_dict[row['old_vlan']] = row['new_vlan']
    
    # return mapping dict
    return mapping_dict

# create dictionry of interfaces and settings
def create_intf_dict(results):
    # init all hosts dict
    all_hosts_intf = {}

    # loop through host results
    for host in results:
        # init per-host interface dict
        intf_out = {}
        # set CLI result to dictionary
        interfaces = results[host].result

        # loop through interfaces
        for intf in interfaces:    
            # set interface name and mode
            intf_name = intf['interface']
            intf_mode = intf['mode']

            # IOS switch uses "static access" | NXOS uses "access"
            if intf_mode == "access" or intf_mode == "static access":
                # if access VLAN isn't 1 add interface details to dictionary
                if intf['access_vlan'] != "1":
                    vlans = intf['access_vlan']
                    voice = intf['voice_vlan']
                    intf_out[intf_name] = {'mode': intf_mode, 'vlans': vlans, 'voice': voice}

            # if trunk port add interface details to dictionary
            elif intf_mode == "trunk":
                vlans = intf['trunking_vlans']
                native = intf['native_vlan']
                intf_out[intf_name] = {'mode': intf_mode, 'vlans': vlans, 'native': native}

        # add dict entry for host with all interfaces
        all_hosts_intf.update({host: intf_out})

    # return completed dictionary
    return all_hosts_intf

# function to remap VLAN ID's
def vlan_mapper(mapping_dict, vlan):
    # function to map old VLAN to new VLAN
    if vlan in mapping_dict.keys():
        return mapping_dict.get(vlan)
    else:
        return vlan

# remap VLAN ID's in interface dictionary
def remap_vlans(mapping_dict, all_hosts_intf):
   # loop over all host results
    for host in all_hosts_intf.values():
        # loop over interfaces
        for intf in host.values():
            # if port is access mode
            if intf['mode'] == 'access':
                # translate VLAN with mapping function
                intf['vlans'] = vlan_mapper(mapping_dict, intf['vlans'])

                # translate voice VLAN if it exists
                if intf['voice'] != 'none':
                    intf['voice'] = vlan_mapper(mapping_dict, intf['voice'])

            # if port is trunk mode
            if intf['mode'] == 'trunk':
                # convert string of VLANs to list
                vlans = intf['vlans'].split(",")
                # loop over VLAN list
                for i, v in enumerate(vlans):
                    # translate VLAN with mapping function
                    vlans[i] = vlan_mapper(mapping_dict ,v)
                # convert VLAN list back to string        
                intf['vlans'] = ",".join(vlans)
                # translate native vlan
                intf['native'] = vlan_mapper(mapping_dict, intf['native'])

    
    return all_hosts_intf

# render new interface configs
def render_configs(int_dict):

    # set Jinja2 templates directory
    file_loader = FileSystemLoader('templates/')
    
    # set Jinja2 envirnment 
    env = Environment(loader=file_loader)

    # voice access mode interface template
    v_template = env.get_template("access_v_int.j2")

    # access mode interface template
    a_template = env.get_template("access_int.j2")

    # trunk mode interface templae
    t_template = env.get_template("trunk_int.j2")

    # loop through inteface dictionary
    for host, intfs in int_dict.items():

        # do something for each host
        print(host)

        # loop through interface dictionarys
        for intf in intfs.items():
            
            # access mode templates
            if intf[1]['mode'] == 'access':
                
                # voice access mode templates
                if intf[1]['voice'] != 'none':
                    cfg = v_template.render(
                        interface=intf[0], 
                        vlan=intf[1]['vlans'], 
                        voice=intf[1]['voice']
                    )

                else:
                    cfg = a_template.render(
                        interface=intf[0], 
                        vlan=intf[1]['vlans']
                    )

            # trunk mode templates
            elif intf[1]['mode'] == 'trunk':
                cfg = t_template.render(
                    interface=intf[0], 
                    vlan=intf[1]['vlans'], 
                    native=intf[1]['native']
                )

            # do stuff with interface configs
            print(cfg)

        print("~"*40)

# TODO write new config files
def write_configs(task):
    pass
 

# TODO push new configs to devices
def push_configs(task):
    pass

def main():
    # initialize The Norn
    nr = InitNornir()

    # filter The Norn to nxos
    nr = nr.filter(platform="nxos")

    # send command to device; use TextFSM
    results = nr.run(
        task=netmiko_send_command,
        command_string="show interface switchport",
        use_textfsm=True,
    )

    # create mapping dict
    mapping_dict = create_mapping_table()
    
    # connect to devices and create JSON output of results
    all_hosts_intf = create_intf_dict(results)

    # print old stuff
    print("\nOld VLANS:")
    print("~"*10)
    pprint(all_hosts_intf)

    # remap vlans and return new JSON
    all_remapped_intf = remap_vlans(mapping_dict, all_hosts_intf)        
 
    # print new stuff
    print("\nNew VLANS:")
    print("~"*10)
    pprint(all_remapped_intf)


    # print rendered configs
    print("\nNew configs:")
    print("~"*10)

    # render new configs
    render_configs(all_remapped_intf)

if __name__ == "__main__":
    main()