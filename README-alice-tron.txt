
Alice-tron lives on pouta.csc.fi (https://docs.csc.fi/cloud/pouta/). It consists of

* One admin node called 'admin', 86.50.168.144

* One cluster front-end node called alice-tron, 86.50.169.219

* A number number of worker nodes called alice-nodeXX , where XX is a two digit number

* Currently (2026-11-12) theres 11 worker nodes

All nodes currently uses Almalinux.  The default user created by Pouta on all
of the nodes is therefore also called 'almalinux'.


Logging in
----------

* Log in to the admin node:
 
  ssh almalinux@86.50.168.144


* Log in to the cluster front-end or workr nodes:

  1. Log in to the admin node 

  2. Add the ssh key for the rest of the cluster
 
     ssh-add

     and give the passphrase


   3.  log in

     ssh alice-tron.hip.fi

     or

     ssh <ip-number of the node>


  

Adding new worker nodes
-----------------------

* Log in to the admin node

* "Log in" to openstack/pouta.csc.fi by sourcing the file openrc.sh:

  . ~almalinux/openrc.sh

  and give your username and pouta password

* Change to the alice-cluster directory

  cd ~almalinux/alice-cluster

* Use the command 'poutacluster add' to add <n> nodes:

  poutacluster add <n>


If nodes can't be created, because the project's limits on instances, VCPUs or
RAM is too limited, end an email to servicedesk@csc.fi, asking for raised
limits
  


Removing nodes:
---------------

The simplest way to remove nodes is to just delete them using Pouta's standard
interfaces; either the web interface, or using the openstack CLI tools:

* Log in to the admin node and openstack/pouta.csc.fi in the same was as for
  adding a node

* See a list of VMs:

  openstack server list 


* Delete a VM:

  openstack server delete <ID>



Recreating a worker node:
-------------------------

If a worker node misbehaves badly, the easiest way to fix can often be to
remove it, and create a new one, using the instructions above.


Rebooting a worker node:
------------------------

For rebooting a worker node, there are several options:

* Using the pouta web interface

* Using the openstack CLI tools:
  
  * Log in to the admin node and openstack/pouta.csc.fi in the same way as when addning a node
  * openstack reboot <ID>

* If you want to reboot all worker nodes, but not until currently running jobs
  are done, the easiest way to do it is via slurm:

  * Log in to the cluster front end node:
   
    ssh almalinux@alice-tron.hip.fi

  * Give the command

    sudo scontrol reboot ASAP nextstate=RESUME ALL


Keeping nodes updated
---------------------

* All nodes in the cluster are configured to run 'dnf upgrade' automatically once per day

* The admin node and front-end node will also be automatically rebooted if the kernel has been updated

* The worker nodes however, will *NOT* be autmatically rebooted.  If the kernel
  has been updated, they need to be rebotted e.g. via slurm, as deescribed
  above: Log in to alice-tron and do 'sudo scontrol reboot ASAP nextstate=RESUME ALL'


Useful slurm commands
---------------------

* Get a list of currently running and queueing jobs:

  squeue

  or

  squ

* See current status of the worker nodes:

  sinfo

* Set a node do draining, so that no new jobs will start on it

  sudo scontrol update NodeName=alice-nodeXX State=DRAIN Reason=draining

* Resume operations on a drained node, so that new jobs can be started again

  sudo scontrol update NodeName=alice-nodeXX State=RESUME



Accounting
----------

Records of all ALICE jobs that run on the cluster needs to be sent to NT1's SGAS system.

Currently, this is being done using BART (https://github.com/sgas/bart): A cron
jobs, defined in /etc/cron.d/bart runs once an hour, to collect data from
slurm, and send it to sgas.

Bart put logs into /var/log/bart-registration.log and /var/log/bart-logger.log

Numbers can be viewed on https://count.ndgf.org:6143/sgas/view/ e.g. 

https://count.ndgf.org:6143/sgas/view/custom/pledges_since_friday_alice

or

https://count.ndgf.org:6143/sgas/view/machines/alice-tron.hip.fi


*NOTE*: In the future (spring 2027 ?), this will be probably replaced by a
system called AUDITOR
