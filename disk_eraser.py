#!/usr/bin/env python

import subprocess
import multiprocessing
import sys
import re
import os


def dcfldd(disk):
    return 'dcfldd pattern=00 errlog=/tmp/dcfldd_write_zeros.log of=/dev/{0} bs=1024 &&'\
    'dcfldd pattern=FF errlog=/tmp/dcfldd_write_ones.log of=/dev/{0} bs=1024 &&'\
    'dcfldd errlog=/tmp/dcfldd_write_rand.log if=/dev/urandom of=/dev/{0} bs=1024'.format(disk)

def call_eraser(cmd):
    return subprocess.call([cmd], stdin=subprocess.PIPE, stderr=subprocess.PIPE)

script_log = os.getcwd() + '/disk_eraser.log'

try:

   lsblk = subprocess.Popen(['lsblk'], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
   disks = lsblk.communicate()
   disks = set(re.findall('sd[a-z]', disks[0]))
   print("Found the following disks:")
   for disk in disks:
       print('/dev/' + disk)
   print("Building a list of dcfldd commands")
   commands = map(dcfldd, disks)
   
   results = []

   print("Building a process pool")
   pool = multiprocessing.Pool(processes=len(commands))
   eraser_pool = pool.map_async(call_eraser, commands, callback=results.append)
   print("Running dcfldd commands...")
   eraser_pool.wait()
   
except subprocess.CallProcessError as err:
   print("One of child processes failed:\n command: {0}\n return code: {1}\n output: {2}\n".format(err.cmd, err.returncode, err.output))
   sys.exit(1)

if len(results) > 0:
    print("Writing log file...")
    f = open(script_log, 'w')
    for res in results:
	    f.write(res + '\n')
	f.close()
   
sys.exit(0)

