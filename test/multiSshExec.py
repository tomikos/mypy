#!/usr/bin/env python

###########################
#  Developer: Tomer Iluz  #
###########################

import os, socket, subprocess
from sys import argv, stdout
from time import sleep, time
import threading
from optparse import Option, OptionParser, OptionGroup

try:
	import libssh2
except ImportError:
	print '\n[-] %s: Please install Pylibssh2 module.' % argv[0]
	exit(1)
	

############################

# Print total running duration
def totaltime():
	totaltime = int(time() - starttime)
	myprint('\n[+] Done - Total duration time: %s' % totaltime)

# Print to stdout if not quiet
def myprint(msg):
	if opts.quiet:
		opts.verbose=False

	if opts.verbose:
		print msg

# Print to log
def printlog(host, msg):

	if opts.verboselog:
		with open(opts.outfile, 'a') as Outfile:
			Outfile.write('%s:\n' % host)
			Outfile.write(str(msg) + "\n")
			Outfile.write('------------------------' + "\n")
	else:
		with open(opts.outfile, 'a') as Outfile:
			Outfile.write(str(msg) + "\n")

# Print to error log
def printerrlog(host, msg):

	with open(opts.errfile, 'a') as Errfile:
		Errfile.write(host + ': ' + str(msg) + "\n")
		Errfile.write('------------------------' + "\n")

# Remove empty logs
def removelog():
        logfiles = [opts.outfile, opts.errfile]
        for log in logfiles:
		try:
                	size = os.path.getsize(log)
                	if size == 0:
				os.remove(log)
        	except Exception, e:
			continue

# Check if can read/write to needed files
def checkfile(file, oper):

        if oper == 'r':
                msg = 'read'
        elif oper == 'a' or oper == 'w':
                msg = 'write to'

        try:

		with open(file, oper) as op_file:
			pass

        except IOError:
                myprint('\n[-] %s: Unable to %s file \'%s\'\n' % (argv[0], msg, file))
		exit(1)

        except Exception, e:
                myprint('\n[-] %s: Unknown error occurred while try to %s file \'%s\'\n' % (argv[0], msg, file))
		exit(1)

# Execute post script if needed
def postscript():
	if opts.post:
		if os.access(opts.post, os.X_OK):
			myprint('\n[+] Running post script: \'%s\'' % opts.post)

			if '/' not in opts.post:
				subprocess.call('./'+opts.post, shell=True)
			else:
				subprocess.call(opts.post, shell=True)
		else:
			myprint('\n[-] Unable to execute post script \'%s\'' % opts.post)

# Check platform
def platform(opts):

	if (opts.linux == 'YES'):
		opts.linux = True
	else:
		opts.linux = False

	if (opts.hpux == 'YES'):
		opts.hpux = True
	else:
		opts.hpux = False

	# Check if default has changed
	if (opts.linux) and (opts.hpux) and (opts.linuxver is None):
		return False

	# 'No Linux' is stronger than 'linux versions'
	if (not opts.linux):
		opts.linuxver = False

	# Only versions of Linux
	if (opts.linuxver) and (not opts.hpux):
		palatcheck='''KIND=`uname`
		if [ "$KIND" != 'Linux' ]; then exit 5; fi
		if [ ! -s "/etc/redhat-release" ]; then  exit 5; fi
		linuxver=$(echo %s | tr -dc "[:digit:]" | sed 's/./& /g')
		VER=`cat /etc/redhat-release | grep -o '[0-9]' | head -1 2>/dev/null`
		if [[ ! `echo "$linuxver" | grep "$VER"` ]]; then exit 5; fi
		''' % opts.linuxver
		return palatcheck

	# Versions of Linux and HPUX
	if (opts.linuxver) and (opts.hpux):
		palatcheck='''KIND=`uname`
		if [ "$KIND" != 'Linux' -a "$KIND" != 'HPUX' ]; then exit 5; fi
		if [ "$KIND" = 'Linux' ]; then
			if [ ! -s "/etc/redhat-release" ]; then  exit 5; fi
			linuxver=$(echo %s | tr -dc "[:digit:]" | sed 's/./& /g')
			VER=`cat /etc/redhat-release | grep -o '[0-9]' | head -1 2>/dev/null`
			if [[ ! `echo "$linuxver" | grep "$VER"` ]] &>/dev/null ; then exit 5; fi
		fi
		''' % opts.linuxver
		return palatcheck

	# No Linux and no HPUX
	if (not opts.linux) and (not opts.hpux):
		palatcheck='''KIND=`uname`
		if [ "$KIND" = 'Linux' -o "$KIND" = 'HPUX' ]; then exit 5; fi
		'''
		return palatcheck

	# Only HPUX 
	if (not opts.linux) and (opts.hpux):
		palatcheck='''KIND=`uname`
		if [ "$KIND" != 'HPUX' ]; then exit 5; fi
		'''
		return palatcheck
	
	# Only all Linux
	if (opts.linux) and (not opts.hpux) and (opts.linuxver is None):
		palatcheck='''KIND=`uname`
		if [ "$KIND" != 'Linux' ]; then exit 5; fi
		'''
		return palatcheck

	# All Linux and HPUX
	if (opts.linux) and (opts.hpux) and (opts.linuxver is None):
		palatcheck='''KIND=`uname`
		if [ "$KIND" != 'Linux' -a "$KIND" != 'HPUX' ]; then exit 5; fi
		'''
		return palatcheck

# Using for singel hostname
def singelTarget(opts):

	# Reset needed variables
	results = []
	opts.tcounter = 0
	opts.cun = 0
	opts.hostname = ''

	# Determine number of supplied hosts
	opts.totalhosts = len(opts.target)

	# Redefine threads number if it greater then the total of hosts
	if opts.totalhosts < opts.threads:
		opts.threads = opts.totalhosts

	# Determine chosen platform
	opts.platcheck = platform(opts)

	# Run on every host in target option
	for opts.hostname in opts.target:
		opts.cun += 1
		sleep(0.2)

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
	checkfile(opts.hostfile, 'r')

	# Determine number of supplied hosts
	opts.totalhosts = (len(open(opts.hostfile, 'r').read().split('\n')) -1)

	# Check if hostfile is empty
	if opts.totalhosts == 0:
		myprint('\n[-] The hostfile: \'%s\' is empty!' % opts.hostfile)
		exit(1)

	# Determine chosen platform
	opts.platcheck = platform(opts)

	# Redefine threads number if it greater then the total of hosts
	if opts.totalhosts < opts.threads:
		opts.threads = opts.totalhosts

	# Reset needed variables
	results = []
	opts.cun = 0
	opts.tcounter = 0
	opts.hostname = ''

	# Open hostlist for reading
	op_hostlist = open(opts.hostfile, 'r')

	# Run on every host in hostfile
	for host in op_hostlist.readlines():
		opts.hostname = host.strip()
		opts.cun += 1
		sleep(0.2)

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
		self.Cun = opts.cun
		self.Totalhosts = opts.totalhosts
		self.Platcheck = opts.platcheck

	# Establish connection
	def conn(self):
		try:
			self.session = libssh2.Session()
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.sock.setblocking(1)
			self.sock.settimeout(self.Timeout)
			self.sock.connect((self.Hostname, self.Port))
			self.session.startup(self.sock)
			self.session.userauth_publickey_fromfile(self.User, self.Pkey, self.Key, '')
  			self.channel = self.session.open_session()

		except Exception, e:
			sleep(1)
			myprint("[%s/%s] Connecting to: %s - Failed! " % (self.Cun, self.Totalhosts, self.Hostname))
			printerrlog(self.Hostname, e)
			exit(0)

	# Execute command
	def exe(self, CMD):
		try:
			# Excute command on the remote host
       			self.channel.execute(CMD)

		except Exception, e:
			printerrlog(self.Hostname, e)
			exit(0)

		data = self.channel.read(4096)

		try:
			# Close the channel & session
	        	self.channel.close()
			self.session.close()

		except Exception, e:
			myprint("[%s/%s] Connecting to: %s - Sucsess with error! " % (self.Cun, self.Totalhosts, self.Hostname))
			printerrlog(self.Hostname, e)
			exit(0)

		# Return data recived
		return data


	# Start running!
	def run(self):

		if (self.Platcheck):
			self.conn()
			output = self.exe(self.Platcheck)
			exitcode = self.channel.exit_status()

       			if exitcode != 0:
				myprint("[%s/%s] Connecting to: %s - Platform not support! " % (self.Cun, self.Totalhosts, self.Hostname))
				exit(0)

		self.conn()
		output = self.exe(self.Cmd)
		exitcode = self.channel.exit_status()
		
       		if exitcode != 0:
			myprint("[%s/%s] Connecting to: %s - Sucsess with error! " % (self.Cun, self.Totalhosts, self.Hostname))
		else:
			myprint("[%s/%s] Connecting to: %s - Sucsess! " % (self.Cun, self.Totalhosts, self.Hostname))

		if (not output == '') or (output is not None):
			printlog(self.Hostname, output.strip())


# Setup the parser
usage = "%prog [HOST] [COMMAND] [OPTIONS].."

description = '''Example: %prog -t Myhost -t Otherhost -c "uname -a" -T 20	
Example: %prog -H host.lst -S script.sh -w 5 -O results.log'''

version = '1.0'

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
        help='Nothing will be printed to stdout (default: %default)')

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
        help="Singel command to execute on remote host")
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
        help="Max wait time in seconds for response (default: %default)")
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

# Grab the command line options
(opts, args) = parser.parse_args()

############ Pre Checking Section ############
# Check for required options
if len(argv) < 2:
	parser.print_usage()
	exit(0)

# Check for required options -c / -S
if (not opts.cmd and not opts.script):
	parser.error("Missing command or script")
elif (opts.cmd and opts.script):
	parser.error("Only command or script can be handle")
elif (opts.script and not opts.cmd):
	checkfile(opts.script, 'r')
	with open(opts.script, "r") as myfile:
		opts.cmd=myfile.read()

# Check for required options -t / -H
if (not opts.target and not opts.hostfile):	
	parser.error("Missing hostname or hostlist")
elif (opts.target and opts.hostfile):
	parser.error("Only hostname or hostlist can be handle")

######### Calling Function Section ##########
# -Start-
try: 
	# Check for needed files
	checkfile(opts.outfile, 'w')
	checkfile(opts.errfile, 'w')

	# Start function depend if choose multihost or single
	if (opts.target and not opts.hostfile):
		singelTarget(opts)
	elif (opts.hostfile and not opts.target):
		multiTarget(opts)

# Handle user Ctrl+C keyboard
except KeyboardInterrupt, e:

        # Wating for all threads to finish
	if threading.active_count() > 1:
		sleep(2)
		myprint("\n[!] Stopped by user - Waiting for lasts threads to finish ..\n")

		while threading.active_count() > 1:
			pass
	else:
		myprint("\n[!] Stopped by user!")

	# Remove empty created logs
	removelog()

	# Print total running duration
	totaltime()

	# Exit with error
	exit(10)

# -Finish-

# Wating for all threads to finish
while threading.active_count() > 1:
	pass

# Execute post script if needed
postscript()

# Remove empty created logs
removelog()

# Print total running duration
totaltime()

# Exit
exit(0)
