#!/usr/bin/env python

###########################
#  Developer: Tomer Iluz  #
###########################

import os, socket, subprocess
from sys import argv
from time import sleep, time
import threading
from optparse import Option, OptionParser, OptionGroup
from re import match

Prog = argv[0].split('/')[-1]

try:
	import libssh2
except ImportError:
	print '\n%s: Please install Pylibssh2-1.0.3 module:' % Prog
	print '\t      https://github.com/wallix/pylibssh2\n'
	exit(1)

if libssh2.version.__version__ != '1.0.3':
	print '\n%s: Please install Pylibssh2-1.0.3 module:' % Prog
	print '\t      https://github.com/wallix/pylibssh2\n'
	exit(1)

############################

# Print total running duration
def totaltime():
	totaltime = int(time() - starttime)
	myprint('[+] Done - Total duration time: %s seconds\n' % totaltime)

# Count connections
def Count():
        global count
        count += 1
        return count

# Print to stdout if not quiet
def myprint(msg):
	if opts.quiet:
		opts.verbose=False

	if opts.verbose:
		print msg

# Print to log
def printlog(host, data):

	if (data == '') or (data == 'None') or (data is None):
		return

	if opts.verboselog:
		with open(opts.outfile, 'a') as Outfile:
			Outfile.write('%s - Sucsess:\n' % host)
			Outfile.write(str(data) + "\n")
			Outfile.write('------------------------' + "\n")
	else:
		with open(opts.outfile, 'a') as Outfile:
			Outfile.write(str(data) + "\n")

# Print to error log
def printerrlog(section, data):

	if (data == '') or (data == 'None') or (data is None):
		return

	with open(opts.errfile, 'a') as Errfile:
		Errfile.write(section + ': ' + str(data) + "\n")
		Errfile.write('------------------------' + "\n")

# Print report
def printreport(opts):

	if not opts.quiet:
		# Clear the screen
		os.system('clear')

	# print the report
	myprint('Command: %s %s\n' % (Prog,' '.join(argv[1:])))

	myprint("- - - - - - - - - - - - - - - - - - - - - -")
	myprint("# Report:")
	myprint("#   Number of hosts: %s" % opts.thosts)
	myprint("#   Threads number: %s" % opts.threads)
	myprint("#   Platform: %s" % opts.reportplat)
	myprint("- - - - - - - - - - - - - - - - - - - - - -\n")
 
	if (opts.threads > 20):
		myprint('CAUTION: too many threads can harm your pc functionality!\n')

	if not opts.quiet:
		sleep(3)

# Remove empty logs
def removelog(finish):

	if finish:
		myprint("\n--------------------------------------------")

        logfiles = [opts.outfile, opts.errfile]
        for log in logfiles:
		try:
                	size = os.path.getsize(log)
                	if size == 0:
				os.remove(log)

			else:
				if finish:
					if (log is opts.outfile):
						myprint("[+] Output log: %s" % opts.outfile)
					elif (log is opts.errfile):
						myprint("[+] Error log: %s" % opts.errfile)
        	except Exception, e:
			continue
	if finish:
		myprint("")

# Check if can read/write to needed files
def checkfile(file, oper, act):

        if oper == 'r':
                msg = 'read'
        elif oper == 'w':
                msg = 'write to'

        try:
		with open(file, oper) as op_file:
			pass

        except IOError:
                myprint('\n%s: Unable to %s file \'%s\'\n' % (Prog, msg, file))	
		if (act == 'hard'):
			exit(0)
		else:
			return False

        except Exception, e:
                myprint('\n%s: Unknown error occurred while try to %s file \'%s\'\n' % (Prog, msg, file))
		if (act == 'hard'):
			exit(0)
		else:
			return False


# Redefine threads number if it more than hosts
def treadsnum(opts):

	if opts.thosts < opts.threads:
		opts.threads = opts.thosts

# Execute post script
def postscript():

	if opts.post:
		myprint('\n------------------- Post -------------------')
		if (checkfile(opts.post, 'r', 'soft') is False):
			return

		if os.access(opts.post, os.X_OK):
			myprint('[+] Running post script: \'%s\'\n' % opts.post)

			if '/' not in opts.post:
				subprocess.call('./'+opts.post, shell=True)
			else:
				subprocess.call(opts.post, shell=True)
		else:
			myprint('[-] Unable to execute post script \'%s\'' % opts.post)
			myprint('[!] Permission issue? (try: chmod +x %s)' % opts.post)

# Check platform
def platform(opts):

	if (opts.linux == 'YES'): opts.linux = True
	else: opts.linux = False

	if (opts.hpux == 'YES'): opts.hpux = True
	else: opts.hpux = False

	# Check if default has changed
	if (opts.linux) and (opts.hpux) and (opts.linuxver is None):
		opts.reportplat = 'ALL'
		return False

	# 'No Linux' is stronger than 'linux versions'
	if (not opts.linux):
		opts.linuxver = False

	# Only versions of Linux
	if (opts.linuxver) and (not opts.hpux):
		opts.reportplat = 'RHEL %s' % (' '.join(opts.linuxver))
		palatcheck='''#!/bin/bash
		KIND=`uname`
		if [ "$KIND" != 'Linux' ]; then exit 5; fi
		if [ ! -s "/etc/redhat-release" ]; then
			echo "/etc/redhat-release file not found" 2>&1
			exit 10
		fi
		linuxver=$(echo %s | tr -dc "[:digit:]" | sed 's/./& /g')
		VER=`cat /etc/redhat-release | grep -o '[0-9]' | head -1 2>/dev/null`
		if ! $(echo "$linuxver" | grep "$VER" >/dev/null 2>&1) ; then exit 5; fi
		exit 0
		''' % opts.linuxver
		return palatcheck

	# Versions of Linux and HPUX
	if (opts.linuxver) and (opts.hpux):
		opts.reportplat = 'RHEL %s And HPUX' % (' '.join(opts.linuxver))
		palatcheck='''#!/bin/bash
		KIND=`uname`
		if [ "$KIND" != 'Linux' -a "$KIND" != 'HP-UX' ]; then exit 5; fi
		if [ "$KIND" = 'HP-UX' ]; then exit 0; fi
		if [ ! -s "/etc/redhat-release" ]; then
			echo "/etc/redhat-release file not found" 2>&1
			exit 10
		fi
		linuxver=$(echo %s | tr -dc "[:digit:]" | sed 's/./& /g')
		VER=`cat /etc/redhat-release | grep -o '[0-9]' | head -1 2>/dev/null`
		if ! $(echo "$linuxver" | grep "$VER" >/dev/null 2>&1) ; then exit 5; fi
		exit 0
		''' % opts.linuxver
		return palatcheck

	# No Linux and no HPUX
	if (not opts.linux) and (not opts.hpux):
		opts.reportplat = 'All except Linux and HPUX'
		palatcheck='''#!/bin/bash
		KIND=`uname`
		if [ "$KIND" = 'Linux' -o "$KIND" = 'HP-UX' ]; then exit 5; fi
		exit 0
		'''
		return palatcheck

	# Only HPUX 
	if (not opts.linux) and (opts.hpux):
		opts.reportplat = 'Only HPUX'
		palatcheck='''#!/bin/bash
		KIND=`uname`
		if [ "$KIND" != 'HP-UX' ]; then exit 5; fi
		exit 0
		'''
		return palatcheck
	
	# Only all Linux
	if (opts.linux) and (not opts.hpux) and (opts.linuxver is None):
		opts.reportplat = 'Only Linux'
		palatcheck='''#!/bin/bash
		KIND=`uname`
		if [ "$KIND" != 'Linux' ]; then exit 5; fi
		exit 0
		'''
		return palatcheck

	# All Linux and HPUX
	if (opts.linux) and (opts.hpux) and (opts.linuxver is None):
		opts.reportplat = 'Linux and HPUX'
		palatcheck='''#!/bin/bash
		KIND=`uname`
		if [ "$KIND" != 'Linux' -a "$KIND" != 'HP-UX' ]; then exit 5; fi
		if [ "$KIND" = 'HP-UX' ]; then exit 0; fi
		if [ "$KIND" = 'Linux' ]; then exit 0; fi
		'''
		return palatcheck

# Using for singel hostname
def singelTarget(opts):

	# Reset needed variables
	results = []
	opts.tcounter = 0
	opts.hostname = ''

	# Determine number of supplied hosts
	opts.thosts = sum(1 for n in opts.target if match("^[a-zA-Z0-9]+.*", n))

	# Check if hostfile is empty
	if opts.thosts == 0:
		myprint('\n%s: No valid target has found!\n' % Prog)
		printerrlog('%s' % Prog, 'No valid target has found!')
		removelog(False)
		exit(1)

	# Check threads number
	treadsnum(opts)

	# Check for longest host
	opts.lenline = (len(max(opts.target, key=len).strip()) + 5)

	# Determine chosen platform
	opts.platcheck = platform(opts)

	# Print report
	printreport(opts)

	# Run on every host in target option
	for opts.hostname in opts.target:
		sleep(0.2)

		if not match("^[a-zA-Z0-9]+.*", opts.hostname):
			printerrlog("\'%s\'" % opts.hostname, 'Target not valid!')
			continue
		try:
			opts.t = SshExec(opts)
			results.append(opts.t)
			opts.t.start()
			opts.tcounter += 1

		except Exception, e:
			continue
	
		# Wait for thread series to finish
		if opts.tcounter == opts.threads:
			for result in results:
				result.join()
			opts.tcounter = 0

			# Delay time
			sleep(opts.delay)

# Using for hostlist file
def multiTarget(opts):

	# Check hostfile for reading
	checkfile(opts.hostfile, 'r', 'hard')

	# Determine number of supplied hosts
	with open(opts.hostfile, 'r') as hfile:
		opts.thosts = sum(1 for n in hfile if match("^[a-zA-Z0-9]+.*", n))

	# Check if hostfile is empty
	if opts.thosts == 0:
		myprint('\n%s: No valid target has found!\n' % Prog)
		printerrlog('%s' % Prog, 'No valid target has found!')
		removelog(False)
		exit(1)

	# Check for longest line in hostlist
	with open(opts.hostfile, 'r') as hlist:
		opts.lenline = (len(max(hlist, key=len).strip()) + 5)

	# Determine chosen platform
	opts.platcheck = platform(opts)

	# Check threads number
	treadsnum(opts)

	# Print report
	printreport(opts)

	# Reset needed variables
	results = []
	opts.tcounter = 0
	opts.hostname = ''

	# Open hostlist for reading
	op_hostlist = open(opts.hostfile, 'r')

	# Run on every host in hostfile
	for host in op_hostlist.readlines():
		opts.hostname = host.strip()
		sleep(0.2)

		if not match("^[a-zA-Z0-9]+.*", opts.hostname):
			printerrlog("\'%s\'" % opts.hostname, 'Target not valid!')
			continue

		try:
			opts.t = SshExec(opts)
			results.append(opts.t)
			opts.t.start()
			#opts.t.daemon=True
			opts.tcounter += 1

		except Exception, e:
			continue

		# Wait for thread series to finish
		if opts.tcounter == opts.threads:
			for result in results:
				result.join()
			opts.tcounter = 0

			# Delay time
			sleep(opts.delay)

	op_hostlist.close()

# pylibssh2 with Thread
class SshExec(threading.Thread):
        def __init__(self, opts):
                super(SshExec, self).__init__()

                # Define needed variables
                self.Hostname = opts.hostname
		self.Cmd = opts.cmd
		self.User = opts.user
		self.Timeout = opts.timeout
		self.Port = opts.port
		self.Key = opts.key
		self.Pkey = opts.pkey
		self.Platcheck = opts.platcheck
		self.Thosts = opts.thosts
		self.Lenline = opts.lenline

	# Establish connection
	def conn(self):
		try:
			if (self.Timeout < 1):
				self.Timeout = 1
			elif (self.Timeout > 300):
				self.Timeout = 300

			self.session = libssh2.Session()
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.sock.setblocking(1)
			self.sock.settimeout(self.Timeout)
			self.sock.connect((self.Hostname, self.Port))
			self.session.startup(self.sock)
			self.session.userauth_publickey_fromfile(self.User, self.Pkey, self.Key, '')
  			self.channel = self.session.open_session()
			
		except Exception, e:
			sleep(0.5)
			myprint("[%s/%s %s" % (Count(), self.out, '- Failed!'))
			printerrlog(self.Hostname, e)
			exit(0)


	# Execute command
	def executer(self, command):

		data = None
		dataerr = None
		exitcode = None

		# Excute command on the remote host
		try:
       			self.channel.execute(command)
			data = self.channel.read(4096)
			
		except Exception, e:
			myprint("[%s/%s %s" % (Count(), self.out, '- Execution failed!'))
			printerrlog(self.Hostname, e)
			exit(0)

		# Receive stdrr and exit code
		exitcode = self.channel.exit_status()
		dataerr = self.channel.read_stderr(4096)

		# Close the channel and session
		try:
	        	self.channel.wait_closed()
			self.session.close()

		except Exception, e:
			myprint("[%s/%s %s" % (Count(), self.out, '- Unknown error!'))
			printerrlog(self.Hostname, e)
			exit(0)

		# Return received stdout, stdrr, code
		return (data, exitcode, dataerr)


	# Start running!
	def run(self):

		self.out = str('%s] %s' % (self.Thosts, self.Hostname)).ljust(self.Lenline)

		# Check platform if needed
		if (self.Platcheck):
			self.conn()
			(data, exitcode, dataerr) = self.executer(self.Platcheck)

			if (exitcode != 0) and (dataerr):
				myprint("[%s/%s %s" % (Count(), self.out, '- Cannot determine platform!'))
				printerrlog(self.Hostname, 'Cannot determine platform: %s' % str(dataerr).strip())
				exit(0)
			
			if (exitcode != 0):
				myprint("[%s/%s %s" % (Count(), self.out, '- Platform excluded!'))
				printerrlog(self.Hostname, 'Platform excluded!')
				exit(0)

		# Call the execution
		self.conn()
		(data, exitcode, dataerr) = self.executer(self.Cmd)
		
       		if exitcode != 0:
			myprint("[%s/%s %s" % (Count(), self.out, '- Execution returned error!'))
			printerrlog(self.Hostname, str(data).strip())
			printerrlog(self.Hostname, str(dataerr).strip())
		else:
			myprint("[%s/%s %s" % (Count(), self.out, '- Sucsess!'))
			printlog(self.Hostname, str(data).strip())

		exit(0)


# Setup the parser
usage = "%prog [HOST] [COMMAND] [OPTIONS].."

description = '''Example: %prog -t Myhost -t Otherhost -c "uname -a" -T 20	
Example: %prog -H host.lst -S script.sh -w 5 -O results.log'''

version = '2.0.3'

parser = OptionParser(usage=usage, version=version, description=description)
parser.add_option("-v", "--verbose",
        action='store_true',
	default=True,
	dest='verbose',
        help='Verbose output (default: %default)')
parser.add_option("-l", "--verlog",
        action='store_true',
	default=False,
	dest='verboselog',
        help='Verbose logging (default: %default)')
parser.add_option("-q", "--quiet",
        action='store_true',
	default=False,
	dest='quiet',
        help='Nothing will printed to stdout (default: %default)')

group0 = OptionGroup(parser, "Hostname (required)")
group0.add_option("-t",
        metavar="<HOSTNAME>", dest="target",
	type='string',
	action="append",
        help="Multi hostname or ip address")
group0.add_option("-H",
        metavar="<HOSTFILE>",
	dest="hostfile",
	type='string',
        help="File containing hostname or ip each per line")

group1 = OptionGroup(parser, "Command (required)")
group1.add_option("-c",
        metavar="<COMMAND>",
	dest="cmd",
	type='string',
        help="Single command to execute on remote host")
group1.add_option("-S",
        metavar="<SCRIPT>",
	dest="script",
	type='string',
        help="Script to execute on remote host")

group2 = OptionGroup(parser, "Advanced")
group2.add_option("-T",
        metavar="<THREADS>",
	dest="threads",
	type='int',
	default=10,
        help="Number of connections in parallel (default: %default)")
group2.add_option("-d",
        metavar="<DELAY>",
	dest="delay",
	type='int',
	default=0,
        help="Delay time in seconds between thread series (default: %default)")
group2.add_option("-w",
        metavar="<TIMEOUT>",
	dest="timeout",
	type='int',
	default=15,
        help="Max wait time in seconds for response 1-300 (default: %default)")
group2.add_option("-u",
        metavar="<USER>",
	dest="user",
	type='string',
	default='root',
        help="Username to connect with (default: %default)")
group2.add_option("-p",
        metavar="<PORT>",
	dest="port",
	type='int',
	default=22,
        help="SSH port number (default: %default)")

group3 = OptionGroup(parser, "Files")
group3.add_option("-O",
        metavar="<OUTFILE>",
	dest="outfile",
        type='string',
        default='outfile.log',
        help="Output file (default: %default)")
group3.add_option("-E",
        metavar="<ERRFILE>",
	dest="errfile",
        type='string',
        default='errorfile.log',
        help="Error file (default: %default)")
group3.add_option("-P",
        metavar="<SCRIPT>",
	dest="post",
        type='string',
        help="Post script to execute locally after finish everything")
group3.add_option("--private",
        metavar="<KEY>",
	dest="key",
        type='string',
        default='/root/.ssh/id_dsa',
        help="Private key (default: %default)")
group3.add_option("--public",
        metavar="<KEY>",
	dest="pkey",
        type='string',
        default='/root/.ssh/id_dsa.pub',
        help="Public key (default: %default)")

group4 = OptionGroup(parser, "Platforms",
		"Beware that any additional changes from the default\t\t\t\t"
		"will double the number of connections per host.\t\t\t\t"
		"The default is ALL platforms")
group4.add_option("-L",
        metavar="<YES/NO>",
	default='YES',
	dest='linux',
        choices=['YES', 'NO'],
        help='Execute commands on Linux (default: %default)')
group4.add_option("-X",
        metavar="<YES/NO>",
	default='YES',
	dest='hpux',
        choices=['YES', 'NO'],
        help='Execute commands on HPUX (default: %default)')
group4.add_option("-V",
        metavar="<4/5/6>",
	dest="linuxver",
        action="append",
        choices=['4', '5', '6'],
        help='Multi RHEL version to execute commands on (default: ALL)')

parser.add_option_group(group0)
parser.add_option_group(group1)
parser.add_option_group(group2)
parser.add_option_group(group3)
parser.add_option_group(group4)

# Determine started time
starttime = time()
count = 0

# Grab the command line options
(opts, args) = parser.parse_args()

############ Pre Checking Section ############
if len(argv) < 2:
	parser.print_usage()
	exit(0)

# Check for required options -t / -H
if (not opts.target and not opts.hostfile):	
	parser.error("Missing hostname or hostlist")

elif (opts.target and opts.hostfile):
	parser.error("Only hostname or hostlist can be handle")

# Check for required options -c / -S
if (not opts.cmd and not opts.script):
	parser.error("Missing command or script")

elif (opts.cmd and opts.script):
	parser.error("Only command or script can be handle")

elif (opts.script and not opts.cmd):
	checkfile(opts.script, 'r', 'hard')
	with open(opts.script, "r") as myfile:
		opts.cmd=myfile.read()

######### Calling Function Section ##########
# -Start-
try: 
	# Check for needed files
	checkfile(opts.outfile, 'w', 'hard')
	checkfile(opts.errfile, 'w', 'hard')

	# Start function multihost or single
	if (opts.target and not opts.hostfile):
		singelTarget(opts)

	elif (opts.hostfile and not opts.target):
		multiTarget(opts)

	# --- Finish --- #

	# Wating for all threads to finish
	cun = -10
	while threading.active_count() > 1:
		cun += 1
		sleep(1)
		if cun > opts.timeout:
			myprint("\n[-] Exit forced - some threads seems to be stuck")
			printerrlog(Prog, 'Exit forced - some threads seems to be stuck')
			removelog(True)
			totaltime()
			os._exit(5)

	# Execute post script if needed
	postscript()

	# Remove empty created logs
	removelog(True)

	# Print total running duration
	totaltime()

	# Exit
	exit(0)

# Handle user Ctrl+C keyboard
except KeyboardInterrupt, e:

	try: sleep(1)
	except KeyboardInterrupt, e: pass

        # Wating for all threads to finish
	if threading.active_count() > 1:
		myprint("\n---------------------------------------")
		myprint("[!] Stopped by user - please wait for last threads to finish ..\n")
		printerrlog(Prog, 'Stopped by user!')

		try:
			while threading.active_count() > 1:
				pass

		except KeyboardInterrupt, e:
			myprint("\n[-] You don't have any patience, ah?")
			removelog(True)
			totaltime()
			os._exit(10)

	else:
		myprint("\n[!] Stopped by user!")
		printerrlog(Prog, 'Stopped by user!')

	# Remove empty created logs
	removelog(True)

	# Print total running duration
	totaltime()

	# Exit with error
	exit(10)
"""
except Exception, e:
	myprint("\n[!] Unknown error occurred, please try again")
	printerrlog(Prog, 'Unknown error occurred, please try again')
	exit(20)
"""
