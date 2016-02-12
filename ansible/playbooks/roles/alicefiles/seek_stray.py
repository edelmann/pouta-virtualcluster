#!/usr/bin/env python
# vim: expandtab ts=4 sw=4

import subprocess
import re

class Proc:
    def __init__(self, ppid, cmd, uid):
        self.ppid = ppid
        self.cmd = cmd
        self.uid = uid
        self.has_kid = False

    def has_parent(self, procs, parent_cmd):
        pattern = re.compile(parent_cmd)
        tmp = self
        while tmp.ppid != 0:
            parent = procs[tmp.ppid]
            if pattern.match(parent.cmd):
                return True
            tmp = parent
        return False

watched_users = [501]

process = subprocess.Popen(['ps', 'ajx'], stdout=subprocess.PIPE)
stdout, stderr = process.communicate()

procs = {}
for line in stdout.decode('ascii').splitlines()[1:]:
    f = line.split()
    ppid = int(f[0])
    pid = int(f[1])
    uid = int(f[7])
    cmd = f[9]
    procs[pid] = Proc(ppid, cmd, uid)

for pid,p in procs.iteritems():
    if p.ppid in procs:
        procs[p.ppid].has_kid = True

for pid,p in procs.iteritems():
    if p.has_kid: continue
    if p.uid not in watched_users:
        #print p.uid, " not in watched_users"
        continue
    if p.has_parent(procs, "sge_"):
        #print pid, " has parent sge_"
        continue
    if p.has_parent(procs, "ssh"):
        #print pid, " has parent ssh"
        continue

    print pid
     
