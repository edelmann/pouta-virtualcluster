#!/usr/bin/env python

import sys
import os 


def Exec(cmd):
     p = os.popen(cmd, "r")
     return p.readlines()


all_specialusers = ["alicecaf", "alicedaq", "alicemdc", "alice_upb", "alidaq", "alieniss", "alienmaster", "aliprod", "alirec", "alishift", "alitrain"]
specialusers = ["aliprod", "alitrain", "alidaq"]
all_sites = ["ALICE::SNIC::SLURM", "ALICE::LUNARC::SLURM", "ALICE::DCSC_KU::ARC", "ALICE::UIB::ARC", "ALICE::HIP::SGE"]


if len(sys.argv) == 1:
     sites = all_sites
else:
     sites = sys.argv[1:]


for s in sites:
     out = Exec("alien login -exec top -site %s | sed '1d' | wc -l" % s)
     n_all = int(out[0])

     n_su = {}
     n_rest = n_all
     for u in specialusers:
          out = Exec("alien login -exec top -site %s -user %s | sed '1d' | wc -l" % (s, u))
          n_su[u] = int(out[0])
          n_rest -= n_su[u]

     print s,
     print n_all,
     for u in specialusers:
          print n_su[u],
     print n_rest
