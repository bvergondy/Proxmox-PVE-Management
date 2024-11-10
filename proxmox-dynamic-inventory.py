#!/usr/bin/env python3
import json
import requests
import os

# upload personal variable from config.json
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "r") as config_file:
        config = json.load(config_file)
    return config

config = load_config()
PROXMOX_API_URL = config["PROXMOX_API_URL"]
USERNAME = config["USERNAME"]
PASSWORD = config["PASSWORD"]
VERIFY_SSL = config["VERIFY_SSL"]
ANSIBLE_USER = config["ANSIBLE_USER"]
DEFAULT_VM_IP_PREFIX = config["DEFAULT_VM_IP_PREFIX"]
OS_KEYWORDS = config["OS_KEYWORDS"]

def get_token():
    """Get the authentication token from Proxmox."""
    url = f"{PROXMOX_API_URL}/access/ticket"
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    response = requests.post(url, data=data, verify=VERIFY_SSL)
    response.raise_for_status()
    result = response.json()
    return {
        "ticket": result['data']['ticket'],
        "CSRFPreventionToken": result['data']['CSRFPreventionToken']
    }

def get_nodes_and_vms():
    """Retrieve nodes and VMs from Proxmox API."""
    auth = get_token()
    headers = {
        "Cookie": f"PVEAuthCookie={auth['ticket']}",
        "CSRFPreventionToken": auth['CSRFPreventionToken']
    }

    # Initialize inventory structure with groups based on OS_KEYWORDS
    inventory = {
        "all": {
            "hosts": [],
            "children": {
                "proxmox_nodes": {
                    "hosts": [],
                    "vars": {
                        "ansible_user": ANSIBLE_USER
                    }
                }
            }
        }
    }
    # Initialize groups for each OS type
    for os_group in OS_KEYWORDS.keys():
        inventory["all"]["children"][os_group] = {
            "hosts": [],
            "vars": {
                "ansible_user": ANSIBLE_USER
            }
        }

    # Get nodes
    nodes_url = f"{PROXMOX_API_URL}/nodes"
    nodes_response = requests.get(nodes_url, headers=headers, verify=VERIFY_SSL)
    nodes_response.raise_for_status()
    nodes = nodes_response.json()['data']

    for node in nodes:
        node_name = node['node']
        # Add each node to the proxmox_nodes group
        inventory["all"]["children"]["proxmox_nodes"]["hosts"].append(node_name)

        # Get VMs for each node
        vms_url = f"{PROXMOX_API_URL}/nodes/{node_name}/qemu"
        vms_response = requests.get(vms_url, headers=headers, verify=VERIFY_SSL)
        vms_response.raise_for_status()
        vms = vms_response.json()['data']

        for vm in vms:
            vm_name = vm['name']
            # Use default IP address if no IP address is found
            vm_ip = vm.get('ip', DEFAULT_VM_IP_PREFIX)

            # Detect OS group based on keywords in VM name
            assigned_group = "other_vms"  # Default value if no OS is detected
            for group, keywords in OS_KEYWORDS.items():
                if any(keyword.lower() in vm_name.lower() for keyword in keywords):
                    assigned_group = group
                    break

            # Add the VM to the detected group
            inventory["all"]["children"][assigned_group]["hosts"].append(vm_ip)

    return inventory

if __name__ == "__main__":
    try:
        inventory = get_nodes_and_vms()
        print(json.dumps(inventory, indent=4))
    except requests.RequestException as e:
        print(f"Error connecting to Proxmox API: {e}")
        exit(1)
