#!/usr/bin/env python

from numpy import zeros, array
import sys

fmt = "%10s: %3i (%6.2f)"

stat = {}
for line in sys.stdin.readlines():
     fields = line.split()
     site = fields[0]
     n_all = int(fields[1])
     n_aliprod = int(fields[2])
     n_alitrain = int(fields[3])
     n_alidaq = int(fields[4])
     n_other = int(fields[5])

     if site not in stat:
          stat[site] = zeros(5)
     
     stat[site] += array([n_all, n_aliprod, n_alitrain, n_alidaq, n_other])


for site in stat.keys():
     print site
     n_all = stat[site][0]
     print fmt % ("ALL", n_all, 100.0)
     print fmt % ("ALIPROD",  stat[site][1], 100*stat[site][1]/n_all)
     print fmt % ("ALITRAIN",  stat[site][2], 100*stat[site][2]/n_all)
     print fmt % ("ALIDAQ",  stat[site][3], 100*stat[site][3]/n_all)
     print fmt % ("OTHER",  stat[site][4], 100*stat[site][4]/n_all)
     print
