#!/usr/bin/env python
# Copyright 2019, 2020 archive-ravello-bp.py Authors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations under
# the License.

# Report Bugs: ashish.k.shah@gmail.com

import ravello_sdk
import sys
import os
import json
import copy
import random
from argparse import ArgumentParser
from common import *
import time
import base64
import getpass
import configparser

def mkparser():
    parser = ArgumentParser()
    parser.add_argument("-b", dest="bp_name",default=None,help='Name of the blueprint to be archived')
    parser.add_argument("--start", dest="start_status",action='store_true',default=False,help='Start all the VMs in the application (Optional argument to be used with -b option)')
    parser.add_argument("--set-login", dest="set_login",action='store_true',default=False,help='Set Ravello login credentials to be used by this script (This option is exclusive, do not combine with other options)')
    parser.add_argument("--image", dest="image_name",default=None,help='Get details of Ravello disk image to configure /etc/archive-ravello-bp.ini file (This option is exclusive, do not combine with other options)')
    parser.add_argument("-u", dest="username",default=None,help='Ravello user account name (Optional argument to be used use with -b option)')
    return parser

parser = mkparser()
args = parser.parse_args()

if len(sys.argv)==1:
    parser.print_help(sys.stderr)
    sys.exit(1)

if args.username is None:
    login_file = os.path.expanduser("~/.ravello_login")
    if os.path.isfile(login_file) is False:
        print ("ERROR: No user credentials provided\nUse -u option to provide Ravello username or set the login credentials using --set-login argument")
        sys.exit(1)
    else:
        print ("DEBUG: Reading login credentials from: " + login_file)

#Get user credentials
username, password  = get_user_credentials(args.username)
if not username or not password:
    print ("ERROR: no user pass")
    sys.exit(1)

#global client
#Connect to Ravello
client = connect(username, password)
if not client:
    print ("ERROR: no client")
    sys.exit (1)

config = configparser.ConfigParser()
try:
    with open('/etc/archive-ravello-bp.ini') as f:
        print ("DEBUG: Reading configuration file /etc/archive-ravello-bp.ini")
        config.readfp(f)
except IOError:
    print ("ERROR: Configuration file /etc/archive-ravello-bp.ini not found")
    sys.exit (1)

### Pulled from ravello api examples
if args.set_login is True:
    if len(sys.argv) > 2:
        parser.print_help(sys.stderr)
        sys.exit(1)
    py3 = sys.version_info[0] > 2
    if py3:
        username = input("Enter username: ")
    else:
        username = raw_input("Enter username: ")
    password = getpass.getpass('Enter a Password: ')

    encryped_password = base64.b64encode(password.encode('utf-8'))

    with open(os.path.expanduser("~/.ravello_login"),"wb") as f:
        f.write(str(username+'\n').encode())
        f.write(encryped_password)
        print("Login credentials are set, you may now use this script for archiving your blueprints")
        sys.exit(0)

if args.image_name is not None:
    if len(sys.argv) > 3:
        parser.print_help(sys.stderr)
        sys.exit(1)
    for image in client.get_diskimages():
        if image['name'].lower() == args.image_name.lower():
            found_image = args.image_name
            print ("Image name: " + image['name'])
            print ("Image id: " + str(image['id']))
            print ("Image size: " + str(image['size']['value']))
            print ("Image size unit: " + str(image['size']['unit']))
            sys.exit(0)

    print("Image %s not found" % args.image_name)
    sys.exit(1)

optimization_level = 'PERFORMANCE_OPTIMIZED'
region = config.get('general','region',fallback='us-east-5') 
exp_time = config.getint('general','expTime',fallback=7200)
name_suffix = config.get('general','name_suffix',fallback='-ARCHIVE')

exp_correct = 60
exp_time = exp_time + exp_correct
# region = 'us-east-5'
TOTAL_DISK_SIZE = 0
TOTAL_DISK_SIZE_VLAUE = 0
TOTAL_DISK_SIZE_UNIT = "GB"
separator = "======"
app_name = ""
app_desc = "#archive\n#save"
app_id = 0
bp_id = 0

def get_bp_data(bp_name,client):
    global bp_id
    found_pb = None
    if bp_id == 0:                 # If blueprint ID is unknown find the blueprint by name
        for bp in client.get_blueprints():
            if bp['name'].lower() == bp_name.lower():
                found_pb = bp
                break
    else:
                for bp in client.get_blueprints():
                    if bp['id'] == bp_id:
                        found_bp = bp
                        break
    return found_pb

def create_app(app_name,bp_id,client):
    global app_id
    app_id = get_app_id(app_name,client)
    if app_id > 0:  #Application found
        print ("ERROR: Application for archiving this blueprint already exists\n Review it and delete the application to retry")
        sys.exit (1)

    new_app=None
    if (app_name and bp_id!=0):
        app={'name':app_name,'description':app_desc,'baseBlueprintId':bp_id}
        print ("DEBUG: Creating application: " + app_name)
        new_app = client.create_application(app)
    return new_app


def get_app_data(app_id,client):
    app = None
    if app_id != 0:
        app = client.get_application(app_id)
    return app

#Get Blue Print ID
bp = get_bp_data(args.bp_name,client)
if bp:
    #Create application
    app_name = bp['name'] + name_suffix
    new_app = create_app(app_name,bp['id'],client)
    if new_app:             #publish application
        print ("DEBUG: Application created")

        #global app_id
        app_id = get_app_id(app_name,client)
        if app_id:
            print ("DEBUG: ID of application " + app_name + " is: " + str(app_id))
        else:
            print("Error: Application " + app_name + " not found")
                    
        app_data_orig = get_app_data(app_id,client)
        #app_data = get_app_data(app_id,client)
        app_data = copy.deepcopy(app_data_orig)

else:
    print ("ERROR: Blueprint not found")
    sys.exit(1)


def connect(username, password):
    client = RavelloClient()
    try:
        client.login(username, password)
    except Exception as e:
        sys.stderr.write('Error: {!s}\n'.format(e))
        print('Error: Invalid user credentials, username {0}'.format(username))
        return None
    return client
    
#global app_data
app_data_orig = get_app_data(app_id,client)
app_data = get_app_data(app_id,client)
#app_data = copy.deepcopy(app_data_orig)

def add_total_disk_size(value,unit):
    global TOTAL_DISK_SIZE
    global TOTAL_DISK_SIZE_VALUE
    global TOTAL_DISK_SIZE_UNIT
    if unit.lower() == "kb":
        size = value * 1024
    if unit.lower() == "mb":
        size = value * 1024 * 1024
    if unit.lower() == "gb":
        size = value * 1024 * 1024 * 1024
    else:
        print ("WARNING: Invalid disk size")
    TOTAL_DISK_SIZE = TOTAL_DISK_SIZE + size

def print_total_disk_size():
    global TOTAL_DISK_SIZE
    global TOTAL_DISK_SIZE_VALUE
    global TOTAL_DISK_SIZE_UNIT
    if TOTAL_DISK_SIZE/(1024*1024) > 0 :
        TOTAL_DISK_SIZE_VALUE = TOTAL_DISK_SIZE/1024
        TOTAL_DISK_SIZE_UNIT = "KB"
        DISK_SIZE_STR = str(TOTAL_DISK_SIZE_VALUE) + TOTAL_DISK_SIZE_UNIT
    if TOTAL_DISK_SIZE/(1024*1024) > 0 :
        TOTAL_DISK_SIZE_VALUE = TOTAL_DISK_SIZE/(1024*1024)
        TOTAL_DISK_SIZE_UNIT = "MB"
        DISK_SIZE_STR = str(TOTAL_DISK_SIZE_VALUE) + TOTAL_DISK_SIZE_UNIT
    if TOTAL_DISK_SIZE/(1024*1024*1024) > 0 :
        TOTAL_DISK_SIZE_VALUE = TOTAL_DISK_SIZE/(1024*1024*1024)
        TOTAL_DISK_SIZE_UNIT = "GB"
        DISK_SIZE_STR = str(TOTAL_DISK_SIZE_VALUE) + TOTAL_DISK_SIZE_UNIT

    print ("DEBUG: total disk size required for migration data: " + DISK_SIZE_STR)

def update_app():
    global app_data_orig
    global app_data
    print ("DEBUG: Updating application data")
    new_app = client.update_application(app_data)
    print ("DEBUG: Publishing application")
    client.publish_application_updates(new_app,False)

def write_files():
    global app_data_orig
    global app_data
    app_orig_file = str(app_name) + "-orig.json" 
    app_new_file = str(app_name) + "-new.json" 
    print("DEBUG: Writing files")
    with open(app_orig_file,'w') as f:
        f.write(json.dumps(app_data_orig,indent=4))
    with open(app_new_file,'w') as f:
        f.write(json.dumps(app_data,indent=4))

def attach_iso():
    global TOTAL_DISK_SIZE
    #Get user credentials
    global client
    global config
    
    #global app_data_orig
    global app_data

    ### NOTE:
    ### Below are few rules based on observation:
    ### baseDiskImageName and baseDiskImageId belongs to the ISO image file, check it manually and use it.
    ### only IDE cdrom is supported

    ### controller ID should be same as IDE controller if available in the VM
    ### If IDE controller is not available on vm then use any random controller ID
    
    ### If single IDE drive, use same controller ID and same controllerIndex
    ### if two IDE drives, use different controller ID (any random number) and increment controllerIndex

    ### If no IDE controller then use any random controller ID and controller index 0

    ### controllerIndex shows number of controllers for the VM
    ### For same controller ID do not increment controllerIndex

    ### Make sure disk_to_add contents are going in the appropriate VM in deployment and design section (not applicable after code re-write)

    n_of_vms = len(app_data['design']['vms'])
    print ("DEBUG: number of vms in the application: " + str(n_of_vms))

    for vm in range(n_of_vms):
        ##ide_cnt = 0
        dta_ctrl_id = 0
        dta_index = 0
        dta_ctrl_index = 0
        dta_ctrl_id_list = []
        n_of_hardDrives = len(app_data['design']['vms'][vm]['hardDrives'])
        random_disk_id = random.randint(1,99999999)
        random_ctrl_id = random.randint(1,99999999)
        print (separator)
        print ("DEBUG: vm " + str(vm) + " has " + str(n_of_hardDrives) + " hardDrives")
        for hd in range(n_of_hardDrives):
            print ("DEBUG: VM " + str(vm) + " disk " + str(hd) + " size is " + str(app_data['design']['vms'][vm]['hardDrives'][hd]['size']['value']) + app_data['design']['vms'][vm]['hardDrives'][hd]['size']['unit'])
            add_total_disk_size(app_data['design']['vms'][vm]['hardDrives'][hd]['size']['value'],app_data['design']['vms'][vm]['hardDrives'][hd]['size']['unit'])
            dta_ctrl_id_list.append(app_data['design']['vms'][vm]['hardDrives'][hd]['controllerId'])
            ### Mark all drives in design section as non-bootable because VM will be booted with custom iso image
            app_data['design']['vms'][vm]['hardDrives'][hd]['boot'] = False

            if app_data['design']['vms'][vm]['hardDrives'][hd]['controller'] == 'ide':
                if dta_ctrl_id_list.count(app_data['design']['vms'][vm]['hardDrives'][hd]['controllerId']) < 2:
                    dta_ctrl_id = app_data['design']['vms'][vm]['hardDrives'][hd]['controllerId']
                    dta_ctrl_index = app_data['design']['vms'][vm]['hardDrives'][hd]['controllerIndex']
                    
                if dta_ctrl_id_list.count(app_data['design']['vms'][vm]['hardDrives'][hd]['controllerId']) == 2:
                    dta_ctrl_index = len(dta_ctrl_id_list) - 1
                    dta_ctrl_id = random_ctrl_id
            else:
                if dta_ctrl_id == 0:
                    dta_ctrl_id = random_ctrl_id
                    dta_ctrl_index = len(dta_ctrl_id_list) - 1
            dta_index = dta_index + 1
        dta_did = random_disk_id
        if dta_ctrl_id_list.count(dta_ctrl_id) == 0:
            dta_ctrl_id_list.append(dta_ctrl_id)
            dta_ctrl_index = len(dta_ctrl_id_list) - 1

        ### Change the hard coded values for baseDiskImageName and baseDiskImageId below and make sure value of size of disk is correct.
	### discard the dta_index calculation above use hardcoded index value to compensate the 'lb' vm with few apps
	### assume there will not be 100 disks attached to any vm
	dta_index = 99
        disk_to_add = {
                "index": dta_index,
                "imageFetchMode": "LAZY",
                "name": "archive-client",
                "controllerId": dta_ctrl_id,
                "boot": True,
                "baseDiskImageName": "archive-client.iso",
                "controller": "ide",
                "baseDiskImageId": 1234567890,
                "loadingPercentage": 100,
                "controllerIndex": dta_ctrl_index,
                "loadingStatus": "DONE",
                "type": "CDROM",
                "id": dta_did,
                "size": {
                    "unit": "KB",
                    "value": 0
                    }
                }
        ## Fetch configuration for bootable iso from config file
        print ("DEBUG: Loading client boot disk image configuration from config file..")
        disk_to_add['name'] = config.get('disk_client','name',fallback='archive-client') 
        disk_to_add['baseDiskImageName'] = config.get('disk_cleint','baseDiskImageName',fallback='archive-client.iso')
        disk_to_add['baseDiskImageId'] = config.get('disk_client','baseDiskImageId')
        disk_to_add['size']['unit'] = config.get('disk_client','size_unit',fallback='KB') 
        disk_to_add['size']['value'] = config.getint('disk_client','size_value')

        print ("DEBUG: appending disk to vm" + str(vm) + " - " + app_data['design']['vms'][vm]['name'])
        app_data['design']['vms'][vm]['hardDrives'].append(disk_to_add)

    print (separator)
    print_total_disk_size()
    #print ("DEBUG: total disk size required for migration data: " + str(TOTAL_DISK_SIZE))
    print (separator)


def delete_network():
    global app_data
    print ("DEBUG: Handling design section for networking")
    n_of_vms = len(app_data['design']['vms'])
    print ("DEBUG: number of vms in the application: " + str(n_of_vms))
    try:
        del (app_data['design']['network'])
    except KeyError:
        print ("DEBUG: no network section found in design section")
    for vm in range(n_of_vms):
        try:
            del (app_data['design']['vms'][vm]['networkConnections'])
        except KeyError:
            print ("DEBUG: no network connections found for design vm " + str(vm) + " - " + app_data['design']['vms'][vm]['name'])

        try:
            del (app_data['design']['vms'][vm]['suppliedServices'])
        except KeyError:
            print ("DEBUG: no network services found for design vm "  + str(vm) + " - " + app_data['design']['vms'][vm]['name'])

    app_data['design']['network']={"services": {"externalGateway": {"securityRules": [{"accessPolicy": "DENY","anySource": True,"id": 6107797944751172608}],"customRulesEnabled": False},"dnsServers": [{"id": 2691329854350401536}]}}


def create_network ():
    network_section = '''
	{
	"network": {
               "switches": [
                    {
                         "networkSegments": [
                              {
                                   "id": 5446821999124372, 
                                   "vlanId": 1
                              }
                         ], 
                         "id": 1993915473817783, 
                         "ports": [
                              {
                                   "index": 0, 
                                   "networkSegmentReferences": [
                                        {
                                             "anyNetworkSegment": false, 
                                             "id": 608035931329583, 
                                             "networkSegmentId": 5446821999124372, 
                                             "egressPolicy": "UNTAGGED"
                                        }
                                   ], 
                                   "deviceType": "SERVICES", 
                                   "id": 8003777535252463, 
                                   "deviceId": 371088502585836
                              }
                         ]
                    }, 
                    {
                         "networkSegments": [
                              {
                                   "id": 8591712982068699, 
                                   "vlanId": 1
                              }
                         ], 
                         "id": 2009382523952892, 
                         "ports": [
                              {
                                   "index": 0, 
                                   "networkSegmentReferences": [
                                        {
                                             "anyNetworkSegment": false, 
                                             "id": 2970240296981584, 
                                             "networkSegmentId": 8591712982068699, 
                                             "egressPolicy": "UNTAGGED"
                                        }
                                   ], 
                                   "deviceType": "SERVICES", 
                                   "id": 4856966956970031, 
                                   "deviceId": 3662757059022700
                              } 
                         ]
                    }
               ], 
               "subnets": [
                    {
                         "networkSegmentId": 8591712982068699, 
                         "ipConfigurationIds": [
                              4461198660600635, 
                              3763592806596256, 
                              6767359268569091
                         ], 
                         "mask": "255.255.0.0", 
                         "ipVersion": "IPV4", 
                         "net": "10.0.0.0", 
                         "id": 6869723559939109
                    }
               ], 
               "services": {
                    "routers": [
                         {
                              "ipConfigurationIds": [
                                   6767359268569091
                              ], 
                              "id": 1227593318561241, 
                              "wan": true
                         }
                    ], 
                    "externalGateway": {
                         "natRules": [
                              {
                                   "serviceId": 2486368537820634
                              }
                         ], 
                         "securityRules": [
                              {
                                   "accessPolicy": "DENY", 
                                   "anySource": true, 
                                   "id": 3120871334550312960
                              }
                         ], 
                         "customRulesEnabled": false
                    }, 
                    "dnsServers": [
                         {
                              "ipConfigurationIds": [
                                   4461198660600635
                              ], 
                              "id": 2599907477985249, 
                              "entries": [
                                   {
                                        "ipConfigurationId": 3763592806596256, 
                                        "type": "A", 
                                        "id": 5810762489332968448, 
                                        "index": 0, 
                                        "name": "archiveserver-ceesk135v10archive-nzxzori9.srv.ravcloud.com"
                                   }
                              ]
                         }
                    ], 
                    "networkInterfaces": [
                         {
                              "id": 371088502585836
                         }, 
                         {
                              "id": 3662757059022700, 
                              "ipConfigurations": [
                                   {
                                        "staticIpConfig": {
                                             "ip": "10.0.0.1", 
                                             "mask": "255.255.0.0"
                                        }, 
                                        "id": 4461198660600635
                                   }, 
                                   {
                                        "staticIpConfig": {
                                             "ip": "10.0.0.2", 
                                             "mask": "255.255.0.0"
                                        }, 
                                        "id": 6767359268569091
                                   }
                              ]
                         }
                    ]
               }
          } 
	  }
    '''
    network_object = json.loads(network_section)
    app_name = app_data['name']
    app_data['design'].update(network_object)
    n_of_vms = len(app_data['design']['vms'])
    for vm in range(n_of_vms):
        nta_index = vm
        nta_prefix = str(10+vm)
        nta_mac = "2c:c2:60:6b:bd:" + nta_prefix
        nta_ip = "10.0.0." + nta_prefix
        nta_ipid = random.randint(1,99999999)
        nta_netid = random.randint(1,99999999)
        vm_name = app_data['design']['vms'][vm]['name']
        ## creates basic network settings for all the vms in the application
        # network_to_add = "networkConnections": [
        network_to_add = {
                    "device": {
                        "index": 0,
                        "useAutomaticMac": False,
                        "mac": nta_mac,
                        "deviceType": "virtio"
                        },
                    "ipConfig": {
                        "staticIpConfig": {
                            "ip": nta_ip,
                            "mask": "255.255.0.0"
                            },
                        "id": nta_ipid
                        },
                    "id": nta_netid,
                    "name": "nic1"
                },
        print ("DEBUG: adding network to design section of vm" + str(vm) + " - " + app_data['design']['vms'][vm]['name'])
        app_data['design']['vms'][vm].update({"networkConnections": network_to_add})


        print ("DEBUG: Injecting user data script to vm" + str(vm) + " with IP " + nta_ip + " and MAC " + nta_mac)
        user_data_script = "#!/bin/bash\ncat << EOF > /etc/sysconfig/network-scripts/ifcfg-eth0\nNAME=\"eth0\"\nHWADDR=\""
        user_data_script = user_data_script + str(nta_mac)
        user_data_script = user_data_script + "\"\nONBOOT=yes\nBOOTPROTO=static\nTYPE=Ethernet\nIPADDR=\""
        user_data_script = user_data_script + str(nta_ip)
        user_data_script = user_data_script + "\"\nNETMASK=\"255.255.0.0\"\nEOF\n\ncat << EOF > /root/app_data\nAPPNAME=\""
        user_data_script = user_data_script + str(app_name)
        user_data_script = user_data_script + "\"\nVMNAME=\""
        user_data_script = user_data_script + str(vm_name)
        user_data_script = user_data_script + "\"\nEOF\n"
        app_data['design']['vms'][vm]['supportsCloudInit'] = True

        app_data['design']['vms'][vm]['userData'] = user_data_script



def attach_data_vm():
    global app_data

    vm_to_add = {
            "privateCloudImage": False,
            "supportsCloudInit": False,
            "supportsCloudInit": True,
            "networkConnections": [
                {
                    "device": {
                        "index": 0,
                        "useAutomaticMac": False,
                        "generatedMac": "2c:c2:60:66:a2:74",
                        "mac": "2c:c2:60:6b:bd:05",
                        "pciSlot": 1,
                        "deviceType": "virtio"
                        },
                    "ipConfig": {
                        "needElasticIp": False,
                        "hasPublicIp": False,
                        "fqdn": "archiveserver.srv.ravcloud.com",
                        "externalAccessState": "ALWAYS_PORT_FORWARDING",
                        "staticIpConfig": {
                            "ip": "10.0.0.5",
                            "mask": "255.255.0.0",
                            },
                        "id": 3793603119677956
                        },
                    "id": 3141450133137398,
                    "name": "eth0"
                    }
                ],
            "applicationId": 3125679066191,
            "id": 7695743400963113,
            "powerOffOnStopTimeOut": True,
            "useCdn": False,
            "rcu": 4.0,
            "suppliedServices": [
                {
                    "useLuidForIpConfig": True,
                    "protocol": "TCP",
                    "name": "ssh",
                    "ip": "10.0.0.5",
                    "ipConfigLuid": 3793603119677956,
                    "external": True,
                    "portRange": "22",
                    "id": 2486368537820633
                    }
                ],
            "memorySize": {
                "unit": "GB",
                "value": 8
                },
            "platform": "default",
    "hardDrives": [
            ],
    "userData": "#!/bin/bash\ncat << EOF > /etc/sysconfig/network-scripts/ifcfg-eth0\nNAME=\"eth0\"\nHWADDR=\"2c:c2:60:6b:bd:05\"\nONBOOT=yes\nBOOTPROTO=static\nTYPE=Ethernet\nIPADDR=\"10.0.0.5\"\nNETMASK=\"255.255.0.0\"\nGATEWAY=\"10.0.0.2\"\nEOF\n",
    "requiresHvm": False,
    "busTopology": {},
    "legacyMode": False,
    "externalFqdn": "archiveserver-epcoviet.srv.ravcloud.com",
    "requiresKeypair": False,
    "loadingStatus": "PENDING",
    "loadingPercentage": 0,
    "firstTimePublished": "1562748456064",
    "numCpus": 4,
    "name": "archive-server",
    "allowNested": False,
    "creationTime": 1562748456064,
    "usingNewNetwork": True,
    "baseVmId": 3242723893804,
    "bootOrder": [
            "CDROM",
            "DISK"
            ],
    "bootType": "BIOS",
    "os": "default",
    "monitorState": "OK"
    }

    app_data['design']['vms'].append(vm_to_add)

def add_disks_to_data_vm():
    global app_data
    global TOTAL_DISK_SIZE_VALUE
    global TOTAL_DISK_SIZE_UNIT

    n_of_vms = len(app_data['design']['vms'])
    for vmno in range(n_of_vms):
        if app_data['design']['vms'][vmno]['name'] == "archive-server":
            print ("DEBUG: appending disk to design section of archive-server vm")

            # Hardcoded values for archive server's boot disk
            disk_to_add = { 
                    "index": 0,
                    "imageFetchMode": "LAZY",
                    "name": "vol",
                    "controllerId": 1636321956224519168,
                    "boot": True,
                    "baseDiskImageName": "archive-server",
                    "controller": "virtio",
                    "baseDiskImageId": 3123532497099,
                    "loadingPercentage": 100,
                    "controllerIndex": 0,
                    "controllerPciSlot": 1,
                    "loadingStatus": "DONE",
                    "type": "DISK",
                    "id": 4463123901840118,
                    "size": {
                        "unit": "GB",
                        "value": 0
                        }
                    }
            ## Fetch configuration for server's boot disk image from config file
            print ("DEBUG: Loading server boot disk image configuration from config file..")
            disk_to_add['name'] = config.get('disk_server','name',fallback='archive-server-image')
            disk_to_add['baseDiskImageName'] = config.get('disk_server','baseDiskImageName',fallback='archive-server-image')
            disk_to_add['baseDiskImageId'] = config.get('disk_server','baseDiskImageId')
            disk_to_add['size']['unit'] = config.get('disk_server','size_unit',fallback='GB')
            disk_to_add['size']['value'] = config.getint('disk_server','size_value')

            print ("DEBUG: appending disk to vm" + str(vmno) + " - " + app_data['design']['vms'][vmno]['name'])
            app_data['design']['vms'][vmno]['hardDrives'].append(disk_to_add)

            # Hardcoded values for archive server's data disk
            disk_to_add = {
                        "index": 1,
                        "imageFetchMode": "LAZY",
                        "name": "Archive-Data-Disk",
                        "controllerId": 1636321956224519168,
                        "boot": False,
                        "controller": "virtio",
                        "loadingPercentage": 100,
                        "controllerIndex": 0,
                        "loadingStatus": "DONE",
                        "type": "DISK",
                        "id": 2549959233952428,
                        "size": {
                            "unit": TOTAL_DISK_SIZE_UNIT,
                            "value": TOTAL_DISK_SIZE_VALUE
                            }
                        }

            app_data['design']['vms'][vmno]['hardDrives'].append(disk_to_add)

def publish_app():
    print ("DEBUG: Updating application data")
    new_app = client.update_application(app_data)

    param = {'preferredRegion':region, 'optimizationLevel':optimization_level, 'startAllVms':args.start_status}
    print ("DEBUG: Publishing application to region " + region)
    client.publish_application(new_app,param)
    print ("DEGUG: Setting application stop time to " + str(exp_time - exp_correct) + " seconds")
    client.set_application_expiration(new_app,exp_time)



def main ():
    global app_data
    ### Add user data script before publishing
    ###publish_app(new_app,client)
    ## Attach iso image (containing script for backing-up all disks) to all VMs
    attach_iso()
    ## Delete network configuration of all VMs
    delete_network()
    ## Create basic network configuration for all VMs
    create_network()
    ## Attach NFS server VM to the application 
    attach_data_vm()
    add_disks_to_data_vm()
    write_files()
    publish_app()
    

main()

