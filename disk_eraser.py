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

def call_eraser(cmd, parent_process_pipe, my_name, log_file):
    cmd = cmd.split('&&')
    process_zeros = subprocess.Popen(cmd[0].strip(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process_zeros.communicate()
    log_file.write("Process name: {0}; Finished writing zeros\n".format(my_name))
    process_ones = subprocess.Popen(cmd[1].strip(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process_ones.communicate()
    log_file.write("Process name: {0}; Finished writing ones\n".format(my_name))
    process_random = subprocess.Popen(cmd[2].strip(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process_random.communicate()
    log_file.write("Process name: {0}; Finished writing random\n".format(my_name))
    PID = str(os.getpid())
    codes = "writing zeros: {0}; writing_ones: {1}; writing random: {2}".format(process_zeros.returncode, process_ones.returncode, process_random.returncode)
    message = [PID, my_name, codes, ' && '.join(cmd)]
    message = message if len(message) > 0 else ["No information"]
    parent_process_pipe.send(message)
    return 0


script_log = os.getcwd() + '/disk_eraser.log'
log = open(script_log, 'w')

try:

    lsblk = subprocess.Popen('lsblk', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    disks = lsblk.communicate()
    disks = list(set(re.findall('sd[a-z]', disks[0])))
    disks.sort()
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
        if "-l" in sys.argv:
            limit = int(sys.argv[sys.argv.index("-l") + 1])
        else:
            limit = -1
        print("Starting subprocesses")
	procs = []
	parent_pipe, child_pipe = multiprocessing.Pipe()
	count = 1
	for c in commands:
            if limit > 0:
                limit -= 1
            elif limit == 0:
                break
            proc_name = "subprocess_{0}".format(len(commands) - len(commands) + count)
            proc = multiprocessing.Process(target=call_eraser, name=proc_name, args=(c, child_pipe, proc_name, log))
	    count += 1
            procs.append(proc)
	    proc.start()
        processes_returned_message = []
        print("Monitoring child processes")
	while len(procs) > 0:
            response = parent_pipe.recv()
	    if len(response) == 4:
                results.append("PID: {0}, exit code {1}, process name: {2}, command: {3}".format(response[0], response[2], response[1], response[3]))
                processes_returned_message.append(response[1])
            elif len(response) > 0:
                results.append(' '.join(response))
            for p in procs:
                if not p.is_alive() or p.name in processes_returned_message:
                    procs.pop(procs.index(p))
    else:
        print("Invalid input: Type 'y' or 'n'")
        sys.exit(1)
   
except subprocess.CalledProcessError as err:
    print("One of child processes failed:\n command: {0}\n return code: {1}\n output: {2}\n".format(err.cmd, err.returncode, err.output))
    sys.exit(1)

print("Checking results")
if len(results) > 0:
    print("Writing log file...")
    for res in results:
        log.write(res + '\n')
log.close()

print("Finished. Exiting.")
sys.exit(0)

