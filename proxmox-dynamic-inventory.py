#!/usr/bin/env python3
import json
import requests
import os

# Charger la configuration depuis le fichier config.json
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

    # Get nodes
    nodes_url = f"{PROXMOX_API_URL}/nodes"
    nodes_response = requests.get(nodes_url, headers=headers, verify=VERIFY_SSL)
    nodes_response.raise_for_status()
    nodes = nodes_response.json()['data']

    # Build inventory data
    inventory = {"all": {"hosts": [], "vars": {"ansible_user": ANSIBLE_USER}}}
    
    for node in nodes:
        node_name = node['node']
        # Add each node as a host
        inventory["all"]["hosts"].append(node_name)

        # Get VMs for each node
        vms_url = f"{PROXMOX_API_URL}/nodes/{node_name}/qemu"
        vms_response = requests.get(vms_url, headers=headers, verify=VERIFY_SSL)
        vms_response.raise_for_status()
        vms = vms_response.json()['data']

        for vm in vms:
            vm_name = vm['name']
            # Utiliser l'adresse IP par défaut si aucune adresse IP n'est trouvée
            vm_ip = vm.get('ip', DEFAULT_VM_IP_PREFIX)
            inventory["all"]["hosts"].append(vm_ip)

    return inventory

if __name__ == "__main__":
    try:
        inventory = get_nodes_and_vms()
        print(json.dumps(inventory))
    except requests.RequestException as e:
        print(f"Error connecting to Proxmox API: {e}")
        exit(1)
