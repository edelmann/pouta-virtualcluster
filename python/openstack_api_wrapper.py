"""
Wrapper against OpenStack nova and cinder APIs

@author: Olli Tourunen
@author: Harri Hamalainen
"""

import os
import time
import itertools
from novaclient import client
from novaclient.exceptions import NotFound
from cinderclient import client as cinderclient
import subprocess
import json


def get_clients():
    version = os.environ['OS_IDENTITY_API_VERSION']
    un = os.environ['OS_USERNAME']
    pw = os.environ['OS_PASSWORD']
    project_id = os.environ['OS_PROJECT_ID']
    project_name = os.environ['OS_PROJECT_NAME']
    auth_url = os.environ['OS_AUTH_URL']
    user_domain_name = os.environ['OS_USER_DOMAIN_NAME']
    nova_client = client.Client("2.0", un, pw, project_id, auth_url, user_domain_name=user_domain_name)
    cinder_client = cinderclient.Client(version, un, pw, project_name, auth_url, user_domain_name=user_domain_name)
    return nova_client, cinder_client


def wait_for_state(client, type, instance_id, tgt_state):
    tgt_states = tgt_state.split('|')
    while True:
        cur_state = getattr(client, type).get(instance_id).status
        if cur_state in tgt_states:
            print('    state now %s' % cur_state)
            break

        if cur_state == 'error':
            raise RuntimeError('Instance in "error" state, launch failed')

        print('    current state: %s, waiting for: %s' % (cur_state, tgt_state))
        time.sleep(5)

def exec_cmd(cmd, split=True):
    """
    Execute the shell command 'cmd', and return the output
    """
    print("Running the command '%s'" % cmd)

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    data, _ = process.communicate()
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    if split:
        return data.strip().split('\n')
    else:
        return data


def openstack_find(object_type, name):
    output = exec_cmd("openstack %s list" % object_type)
    for line in output:
        if line[0] == '+': continue

        fields = line.split(' ')
        if fields[1] == 'ID': continue

        o_id = fields[1]
        o_name = fields[3]

        if o_name == name:
            return o_id, o_name
        elif o_id == name:
            return o_id, o_name
    return None, None


def check_image_exists(client, image):
    img_id = openstack_find("image", image)[0]
    if not img_id:
        raise RuntimeError('Requested images "%s" does not exist' % image)
    return img_id


def find_image_name_by_id(client, image_id):
    for img in client.images.list():
        if img.id == image_id:
            return img.name
    return image_id


def check_flavor_exists(client, flavor):
    for fl in client.flavors.list():
        if fl.name == flavor:
            return fl.id
        elif fl.id == flavor:
            return fl.id
    raise RuntimeError('Requested flavor "%s" does not exist' % flavor)


def find_flavor_name_by_id(client, flavor_id):
    for fl in client.flavors.list():
        if fl.id == flavor_id:
            return fl.name

    return flavor_id


def check_secgroup_exists(client, secgroup):
    sg_id = openstack_find("security group", secgroup)[0]
    if not sg_id:
        raise RuntimeError('Requested security group "%s" does not exist' % secgroup)
    return sg_id


def check_network_exists(client, network):
    net_id = openstack_find("network", network)[0]
    if not net_id:
        raise RuntimeError('Requested network "%s" does not exist' % network)
    return net_id


def create_sec_group(client, name, description):
    output = exec_cmd("openstack security group create --description '%s' %s -f json" % (description, name), split=False)
    sg = json.loads(output)
    return sg['id'], sg['name']


def add_sec_group_rule(client, sec_group_id, ip_protocol, from_port, to_port, cidr):
    exec_cmd("openstack security group rule create --protocol %s --dst-port %s:%s --remote-ip %s %s"
             % (ip_protocol, from_port, to_port, cidr, sec_group_id))


def find_security_group_by_name(nova_client, name):
    try:
        return check_secgroup_exists(nova_client, name)
    except RuntimeError:
        return None

def security_group_rule_create(protocol, group_id, remote_group_id, port_range):
    exec_cmd("openstack security group rule create --protocol %s --remote-group %s --dst-port %s %s"
             % (protocol, remote_group_id, port_range, group_id))

def create_local_access_rules(client, to_sec_group_name, from_sec_group_name):
    sg_to = find_security_group_by_name(client, to_sec_group_name)
    sg_from = find_security_group_by_name(client, from_sec_group_name)

    security_group_rule_create(remote_group_id=sg_from, group_id=sg_to, protocol='tcp', port_range="1:65535")
    security_group_rule_create(remote_group_id=sg_from, group_id=sg_to, protocol='udp', port_range="1:65535")
    security_group_rule_create(remote_group_id=sg_from, group_id=sg_to, protocol='icmp', port_range="0:0")


def delete_sec_group(client, name):
    sg = find_security_group_by_name(client, name)
    if sg:
        client.security_groups.delete(sg)
        return sg


def delete_sec_group_rules(nova_client, name):
    sg = find_security_group_by_name(nova_client, name)
    if not sg:
        print("    No security group %s found, no rules deleted" % name)
        return
    for rule in sg.rules:
        print("    deleting rule %s " % rule['id'])
        nova_client.security_group_rules.delete(rule['id'])


def check_server_group_exists(client, name, policies):
    sgs = client.server_groups.list()

    for sg in sgs:
        if sg.name == name and len(sg.policies) == len(policies):
            for pol in sg.policies:
                if pol not in policies:
                    continue
            for pol in policies:
                if pol not in sg.policies:
                    continue

            return sg.id

    raise RuntimeError('Requested server group "%s" with given policies (%s) does not exist' % (name, policies))


def create_server_group(client, name, policies):
    sg = client.server_groups.create(name=name, policies=policies)
    return sg.id


def delete_server_group(client, name):
    sgs = client.server_groups.list()

    for sg in sgs:
        if sg.name == name:
            client.server_groups.delete(sg.id)
            return sg.id

    raise RuntimeError('Requested server group "%s" does not exist' % name)


def create_vm(client, name, image_id, flavor_id, key_name, sec_groups, network_id=None, server_group_id=None):
    nics = None
    if network_id:
        nics = [{'net-id': network_id}]

    scheduler_hints = {}
    if server_group_id:
        scheduler_hints['group'] = server_group_id

    instance = client.servers.create(name, image_id, flavor_id, key_name=key_name, security_groups=sec_groups,
                                     nics=nics, scheduler_hints=scheduler_hints)

    return instance.id


def delete_vm(instance):
    instance.delete()
    print("    deleted instance %s" % instance.id)


def wait_for_deletion(client, object_type, instance_id):
    while True:
        try:
            getattr(client, object_type).get(instance_id)
            print('    object %s still exists' % instance_id)
            time.sleep(5)
        except:
            # object not found anymore
            break


def shutdown_vm(nova_client, node):
    if node.status == 'ACTIVE':
        node.reboot()
        wait_for_state(nova_client, 'servers', node.id, 'REBOOT|ERROR')
        wait_for_state(nova_client, 'servers', node.id, 'SHUTOFF|ACTIVE|ERROR')
        node.stop()


def get_instance(client, instance_id):
    try:
        return client.servers.get(instance_id)
    except:
        raise RuntimeError('Instance %s not found' % instance_id)


def get_volume(client, volume_id):
    try:
        return client.volumes.get(volume_id)
    except:
        raise RuntimeError('Volume %s not found' % volume_id)


def create_and_attach_volume(nova_client, cinder_client, prov_state, instance,
                             name, size, dev, a_sync=False):
    volume = cinder_client.volumes.create(size, name=name)
    prov_state['volume.%s.id' % name] = volume.id
    print('    created volume %s' % volume.id)

    wait_for_state(cinder_client, 'volumes', volume.id, 'available')
    print('    attaching volume %s to %s' % (volume.id, instance.id))
    nova_client.volumes.create_server_volume(instance.id, volume.id, dev)
    if not a_sync:
        wait_for_state(cinder_client, 'volumes', volume.id, 'in-use')

    return volume


def attach_volume(nova_client, cinder_client, instance, volume, dev, a_sync=False):
    wait_for_state(cinder_client, 'volumes', volume.id, 'available')
    print('    attaching volume %s to %s' % (volume.id, instance.id))
    nova_client.volumes.create_server_volume(instance.id, volume.id, dev)
    if not a_sync:
        wait_for_state(cinder_client, 'volumes', volume.id, 'in-use')


def delete_volume_by_id(client, vol_id, wait_for_deletion=False):
    # XXX: Cinder API has a potential race condition where a
    # call for volume.delete will not actually delete the
    # volume, which is why persistent polling is required
    volume = get_volume(client, vol_id)
    while True:
        if volume.status == 'deleting':
            break
        volume.delete()
        time.sleep(5)
        try:
            # volumes in 'deleted' state will raise an exception with get_volume()
            volume = get_volume(client, vol_id)
        except:
            break

    if wait_for_deletion:
        status = 'deleting'
        while status == 'deleting':
            print("    waiting for deletion")
            status = ''
            for vol in client.volumes.list():
                if vol.id == vol_id:
                    status = vol.status
                    break
            time.sleep(10)


def get_addresses(instance, ip_type='fixed'):
    networks = instance.addresses
    return [x['addr'] for x in itertools.chain.from_iterable(networks.values())
            if x['OS-EXT-IPS:type'] == ip_type]


def list_floating_ips():
    output = exec_cmd("openstack floating ip list -f json", split=False)
    return json.loads(output)

def find_free_floating_ip(nova_client):
    fips = list_floating_ips()
    for fip in fips:
        if not fip['Fixed IP Address']:
            return fip
    return None


def add_floating_ip(server, floating_ip):
    exec_cmd("openstack server add floating ip %s %s" % (server, floating_ip))


def associate_floating_address(nova_client, vm, floating_ip='auto'):
    # statically selected floating ip
    if floating_ip != 'auto':
        fips = list_floating_ips()
        for fip in fips:
            if fip['Floating IP Address'] == floating_ip:
                if fip['Fixed IP Address']:
                    raise RuntimeError('Selected floating IP is already in use: %s' % floating_ip)
                else:
                    add_floating_ip(vm.id, fip['Floating IP Address'])
                    return fip

        raise RuntimeError('Selected floating IP is not allocated to project: %s' % floating_ip)

    # automatically assigned
    if floating_ip == 'auto':
        while True:
            # find a free address
            free_fip = find_free_floating_ip(nova_client)

            # if all are taken, allocate a new one
            if not free_fip:
                free_fip = nova_client.floating_ips.create(nova_client.floating_ip_pools.list()[0].name)
                print('    no free IPs, allocated a new IP for the project: %s' % free_fip['Floating IP Address'])

            print('    selected free IP: %s' % free_fip['Floating IP Address'])

            # associate the ip with the server
            # there is a potential race here, so minimize the risk by checking if we actually got the ip
            # after a short sleep and if not, try again
            vm.add_floating_ip(free_fip)
            time.sleep(5)
            fips = nova_client.floating_ips.list()
            for fip in fips:
                if fip.ip == free_fip.ip:
                    if fip.instance_id == vm.id:
                        return fip
                    else:
                        print('    selected IP was grabbed for another VM: %s %s' % (fip.ip, fip.instance_id))
                        print('    retrying to auto-associate')
                        break

    raise RuntimeError('Invalid floating IP specified: %s' % floating_ip)
