#!/usr/bin/env python

import subprocess
import multiprocessing
import sys
import re
import os


def dcfldd(disk):
    return 'dcfldd pattern=00 errlog=/tmp/dcfldd_write_zeros.log of=/dev/{0} bs=1024 && '\
    'dcfldd pattern=FF errlog=/tmp/dcfldd_write_ones.log of=/dev/{0} bs=1024 && '\
    'dcfldd errlog=/tmp/dcfldd_write_rand.log if=/dev/urandom of=/dev/{0} bs=1024'.format(disk)

def call_eraser(cmd, parent_process_pipe):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    parent_process_pipe.send([os.getpid(), process.returncode, stderr])
	

script_log = os.getcwd() + '/disk_eraser.log'

try:

    lsblk = subprocess.Popen('lsblk', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    disks = lsblk.communicate()
    disks = set(re.findall('sd[a-z]', disks[0]))
    print("Found the following disks:")
    for disk in disks:
        print('/dev/' + disk)
    print("Building a list of dcfldd commands")
    commands = map(dcfldd, disks)
   
    results = []
   
    if "-f" in sys.argv:
        run_process = 'y'
    else:
        run_process = str(raw_input("Ready to erase all disks? There is no turning back! (y/n): "))
		
    if run_process == 'n':
        print('Exiting')
        sys.exit(0)
    elif run_process == 'y': 
        print("Starting subprocesses")
	procs = []
	parent_pipe, child_pipe = multiprocessing.Pipe()
	count = 1
	for c in commands:
            proc = multiprocessing.Process(target=call_eraser, name="subprocess_{0}_command: {1}".format(len(commands) - len(commands) + count, c), args=(c, child_pipe))
	    count += 1
            procs.append(proc)
	    proc.start()
	for p in procs:
	    p.join()
	child_processes = len(procs)
	while child_processes > 0:
            response = parent_pipe.recv()
	    if len(response) > 0:
	        results.append("PID: {0}, exit code {1}, sterr: {2}".format(response[0], response[1], response[2]))
		child_processes -= 1
	    else: continue
    else:
        print("Invalid input: Type 'y' or 'n'")
        sys.exit(1)
   
except subprocess.CalledProcessError as err:
    print("One of child processes failed:\n command: {0}\n return code: {1}\n output: {2}\n".format(err.cmd, err.returncode, err.output))
    sys.exit(1)

if len(results) > 0:
    print("Writing log file...")
    f = open(script_log, 'w')
    for res in results:
        f.write(res + '\n')
    f.close()

print("Finished. Exiting.")
sys.exit(0)

