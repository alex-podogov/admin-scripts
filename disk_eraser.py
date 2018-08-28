#!/usr/bin/env python

import subprocess
import multiprocessing
import sys
import re
import os


'''
This script was created for Linux platforms, specifically for RHEL-based distributions.
In order to use this script, you should have a 'dcfldd' tool installed on the system where you are running it.
This script will detect SSD and exlude them from the list of drives to wipe, since to "wipe" an SSD you should
use TRIM command after deleting files from the file system.
Usage:
Set 'exec' permission on the script first: chmod 755 disk_eraser.py
"./disk_eraser.py -f" - use this to skip a prompt for confirmation and force wiping;
"./disk_eraser.py -l 2" - use '-l' option to limit a number of disks to wipe (2 disks in this example);
"./disk_eraser.py" - this will request a confirmation and will wipe all disks it can find.
'''

# Prepare shell commands to wipe disks: this script makes use of a 'dcfldd', which is an enhanced version of a standard 'dd' tool.
# It was developed for forensics needs.
def dcfldd(disk):
    return 'dcfldd pattern=00 errlog=/tmp/dcfldd_write_zeros.log of=/dev/{0} bs=8192 conv=noerror && '\
    'dcfldd pattern=FF errlog=/tmp/dcfldd_write_ones.log of=/dev/{0} bs=8192 conv=noerror && '\
    'dcfldd errlog=/tmp/dcfldd_write_rand.log if=/dev/urandom of=/dev/{0} bs=8192 conv=noerror'.format(disk)

# This function will spawn subprocesses running 'dcfldd'.
def call_eraser(cmd, parent_process_pipe, my_name):
    cmd = cmd.split('&&')
    process_zeros = subprocess.Popen(cmd[0].strip(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process_zeros.communicate()
    process_ones = subprocess.Popen(cmd[1].strip(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process_ones.communicate()
    process_random = subprocess.Popen(cmd[2].strip(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process_random.communicate()
    PID = str(os.getpid())
    codes = "writing zeros: {0}; writing_ones: {1}; writing random: {2}".format(process_zeros.returncode, process_ones.returncode, process_random.returncode)
    message = [PID, my_name, codes, ' && '.join(cmd)]
    message = message if len(message) > 0 else ["No information"]
    parent_process_pipe.send(message)
    return 0


script_log = os.getcwd() + '/disk_eraser.log'
log = open(script_log, 'w')

try:

    # Open up a child-parent pipe which is used to exchange messages between the main script and its child processes.
    lsblk = subprocess.Popen('lsblk', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    disks = lsblk.communicate()
    disks = list(set(re.findall('[hs]d[a-z]', disks[0])))
    disks.sort()
    print("Found the following disks:")
    for disk in disks:
        print('/dev/' + disk)
    ssd = []
    for disk in disks:
	# Run a shell command to detect a disks' types and exclude SSD from the wiping process.
        determine_type = subprocess.Popen('cat /sys/block/{0}/queue/rotational'.format(disk), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	disk_type, err = determine_type.communicate()
	if str(disk_type).strip() == '0':
	    print('Disk {0} is an SSD and will be excluded from the list of disks being wiped'.format(disk))
            ssd.append(disk)
    disks = [d for d in disks if d not in ssd]
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
        if "-l" in sys.argv:
            limit = int(sys.argv[sys.argv.index("-l") + 1])
        else:
            limit = -1
        print("Starting subprocesses")
	procs = []
	parent_pipe, child_pipe = multiprocessing.Pipe()
	count = 1
	# Generate a list of subprocesses which will run instances of call_eraser function
	for c in commands:
            if limit > 0:
                limit -= 1
            elif limit == 0:
                break
            proc_name = "subprocess_{0}".format(count)
            proc = multiprocessing.Process(target=call_eraser, name=proc_name, args=(c, child_pipe, proc_name))
	    count += 1
            procs.append(proc)
	    # Start subprocesses
	    proc.start()
	# Child process monitoring cycle
        processes_returned_message = []
        print("Monitoring child processes")
	while len(procs) > 0:
	    # Listen for incoming messages from child processes
            response = parent_pipe.recv()
	    if len(response) == 4:
                results.append("PID: {0}, exit code {1}, process name: {2}, command: {3}".format(response[0], response[2], response[1], response[3]))
                processes_returned_message.append(response[1])
            elif len(response) > 0:
                results.append(' '.join(response))
            for p in procs:
		# Check if a particular child process has terminated or returned a message already
                if not p.is_alive() or p.name in processes_returned_message:
                    procs.pop(procs.index(p))
    else:
        print("Invalid input: Type 'y' or 'n'")
        sys.exit(1)
   
except subprocess.CalledProcessError as err:
    print("One of child processes failed:\n command: {0}\n return code: {1}\n output: {2}\n".format(err.cmd, err.returncode, err.output))
    sys.exit(1)

# Write log file
print("Checking results")
if len(results) > 0:
    print("Writing log file...")
    for res in results:
        log.write(res + '\n')
log.close()

print("Finished. Exiting.")
sys.exit(0)

