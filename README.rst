============
Poutacluster
============

**NOTE: This is a work in progress**

Pouta-virtualcluster is a helper script and a set of Ansible playbooks to
quickly setup an ALICE cluster in **pouta.csc.fi** IaaS service. It draws
heavily from the *ElastiCluster* by *Grid Computing Competence Center,
University of Zurich*, especially most of the Ansible playbooks are based
on ElastiCluster. Provisioning code, however, is written from scratch to
support volumes (persistent storage), server affinity and security group
relations. It runs directly against OpenStack Python API.

Currently poutacluster can provision:

* A cluster suitable for ALICE computing on top of CentOS witth one frontend and N compute nodes

  - frontend and compute nodes can have different images, flavors and keys
  - frontend has a public IP
  - there can be a volume for local persistent data
  - frontend has a separate shared volume, exported with NFS to the worker nodes from */mnt/shared_data*
  - GridEngine for batch processing

How it works
============

There are two separate parts:

- provisioning the VMs and related resources
- configuring the VMs with Ansible

Provisioning
------------

Provisioning VMs for cluster goes roughly like this:

* The cluster configuration is read from YAML file provided by the user.
* The current state of provisioned resources is loaded using OpenStack APIs from pouta.csc.fi
* Missing VMs are provisioned

  - first frontend, then appropriate number of nodes
  - naming: *[cluster-name]-tron and *[cluster-name]-node[number]*. If your
    cluster name was be *alice*, you would get

      + alice-tron
      + alice-node01
      + alice-node02
      + ...

  - VMs are launched from the specified image with specified flavor. They are placed in an OpenStack server group with
    anti-affinity policy to distribute them on separate hosts for better
    fault tolerance. (the latter sentecne isn'nt true right now)
  - volumes are created or reused and attached
  - template security groups are created if these don't exist already

* Ansible host inventory file is created, mapping VMs to assigned roles

Shutdown is done in reverse order, starting with the last nodes and finally shutting down frontend. Only after the cluster
has been shut down, you can wipe the persistent storage for the cluster.

See the example below.

Configuration
-------------

There is a collection of Ansible playbooks in *ansible/playbooks* directory, all collected to *ansible/playbooks/site.yml*.
Based on the role/group assignment in Ansible inventory (which in turn is generated from provisioning state and cluster
configuration in cluster.yml by poutacluster script) a set of tasks is launched on each VM.

The playbooks are designed to be idempotent, so that you should be able to run them at any time, and they will only make
changes in the configuration if necessary. Also, if you change the number of nodes in the cluster, playbooks can be
re-applied to reflect the change.

Prerequisites
=============

Getting started with pouta.csc.fi
---------------------------------

To use CSC Pouta cloud environment you will need

* credentials for Pouta
* basic knowledge of Pouta and OpenStack

See https://research.csc.fi/pouta-user-guide for details

Setting up an admin node
-------------------------

Note: Here we assume that you are already past the basic steps mentioned above.

Create a small management VM to act as an admin node and Squid proxy server
(for CVMFS)

* Edit admin/group_vars/all.yml

* Run the ansible playbook in admin/setup-admin.yml.

  This will do most of the work

* create a new key for cluster access (keeping bastion access and cluster access separate is a good practice)::

    ssh-keygen

* import the key::

    nova keypair-add  --pub-key .ssh/id_rsa.pub cluster-key

* make a backup copy of the keypair, so you don't lose it if something bad happens to your bastion host

    [me@workstation]$ scp -r cloud-user@86.50.168.XXX:.ssh dot_ssh_from_bastion


Cluster life-cycle walk-through
-------------------------------

Log in to the admin node, source the openrc.sh and start deploying the cluster:

* Go the alice-cluster dir (created by the admin ansible scripts mentioned
  above)

    cd ~/alice-cluster

* Check the cluster.yml and groupvars/all.yml files, and edit it if needed

    vim cluster.yml
    vim groupvars_all.yml


* bring the cluster up with a frontend and two nodes::

    poutacluster up 2

  Note: In theory, any number of nodes should work. In practice, it's
  fairly common for problems to occur if the number of nodes is large (>
  5). Therefore it's better to start small, and add more nodes sin smaller
  batches until desired size is achieved.  If something gioes wrong, the
  eaiest option is usually to remove all the VMs and start over.

* Add more nodes to the cluster::

   poutacluster add 4

  Same applies here: Usually a good idea to add only a few nodes at a time.
  If adding the nodes fail, remove the newly added VMs, and try again.

* check what *info* shows about the state::

    poutacluster info

* bring the cluster down to save credits (permanent data on volumes is still preserved)::

    poutacluster down

* destroy the cluster by first bringing it down and then getting rid of the volumes::

    poutacluster down
    poutacluster destroy_volumes


Some usefull stuff:
-------------------

Check uptime on all the hosts on cluster frontend::

    pdsh -w mycluster-node[01-04] uptime

Reboot the nodes::

    sudo pdsh -w mycluster-node[01-04] reboot


* If a node becomes unaccessible:

  1. Reboot the node::

       openstack server list # Check the ID of the node
       openstack server reboot <ID>

     and wait for a few minutes.

     You may have to log in and (re-)start the sge_execd raemon::

      sudo /etc/init.d/sge_execd status
      sudo /etc/init.d/sge_execd start  # if down

  2. If rebooting didn't help remove the node and create a new one::

      openstack server list  # check the ID of the node
      openstack server delete <ID>
      poutacluster add 1



