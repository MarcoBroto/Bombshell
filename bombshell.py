#! python3.8
import os, sys, re

BOMBA = chr(0x1F4A3) # Bomb character constant
inList, outList = [], [] # Used to store names and descriptors of redirect input and output files
std_fds = None # Used to store copied std file descriptors when using pipe


def restoreStdFds():
	if not std_fds: return
	for i in range(3): # reopen std file descriptors
		os.dup2(std_fds[i], i)
		os.set_inheritable(i, True)


def changeDirectory(args):
	if len(args) < 2: args.append(os.environ['HOME'])
	else: args[1] = re.sub('^~', os.environ['HOME'], args[1]) # Replace tilde with home alias
	try: os.chdir(args[1])
	except FileNotFoundError: print(f'asdfacd: no such file or directory: {args[1]}')
	except PermissionError: print('User does not have permission to access this directory.')
	except NotADirectoryError: print('Path is not a directory.')


def runInBackground(command, args): pass #TODO: Implement run program in background


def redirectOutput():
	global outList
	try:
		if not outList: return
		outList = [os.open(file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC) for file in outList] # Store open file descriptors
		for line in sys.stdin: map(lambda fd: os.write(fd, line.encode()), outList)
		for fd in outList: os.close(fd)
	except OSError as err: print(err)


def pipeItUp():
	pfds = os.pipe() # Create file descriptors for pipe io
	for fd in pfds: os.set_inheritable(fd, True)
	return pfds


def promptCommand():
	promptStr = re.sub(f"^{os.environ['HOME']}", '~', f'{os.getcwd()} {BOMBA} ')
	os.write(1, promptStr.encode()) # Print current working directory and prompt symbol
	try:
		inputStr = sys.stdin.readline()
		if not inputStr: sys.exit()
	except KeyboardInterrupt:
		print()
		sys.exit()
	return inputStr.strip()


def parseCommand(commStr: str):
	global inList, outList
	inList = list(map(lambda s: re.sub('< *', '', s.strip()),
                    re.findall('< *[^ ]+', commStr))) # Parse and store redirected inputs
	outList = list(map(lambda s: re.sub('> *', '', s.strip()),
                    re.findall('> *[^ ]+', commStr))) # Parse and store redirected outputs
	args = re.split('[ ]+', re.sub('(> *[^ ]+)|(< *[^ ]+)', '', commStr).strip()) # Parse program arguments
	if not len(args): return
	return args


BUILT_INS = {'cd': changeDirectory, 'exit': sys.exit}


def runCommand(args: [str], pipe: tuple=None):
	if args[0] in BUILT_INS: # Run built in commands
		BUILT_INS[args[0]](args if args[0] != 'exit' else None)
		return

	rc = os.fork()
	if rc == 0: # Child branch
		try:
			if inList: os.dup2(os.open(inList[-1], os.O_RDONLY), 0) # Redirect input
			if pipe: # Route output through pipe
				os.dup2(pipe[1], 1) # Assign pipe's file descriptor to stdout's
				os.set_inheritable(1, True)
				for fd in pipe: os.close(fd)
			if outList: os.dup2(os.open(outList[-1], os.O_CREAT | os.O_WRONLY | os.O_TRUNC), 1) # Redirect output
			os.execvp(args[0], args) # Execute program
		except FileNotFoundError: print(f'bombshell: {args[0]}: Command not found')
		sys.exit()
	elif rc > 0: # Parent branch
		os.wait()
		global std_fds
		if pipe:
			os.dup2(pipe[0], 0) # Close stdin, duplicate pipe read fd into stdin fd
			os.set_inheritable(0, True)
			for fd in pipe: os.close(fd) # Close parent pipe file descriptors
		elif std_fds:
			restoreStdFds() # Reopen closed std file descriptors
			for fd in std_fds: os.close(fd) # Close duplicated std file descriptors
			std_fds = None
	else: raise OSError('Fork Error') # Fork error


if __name__ == "__main__":
	while True:
		inputStr = promptCommand()
		# print(f'{inputStr=}')
		if not inputStr: continue
		pipeStream = re.split('[|]', inputStr) # Parse command pipes
		if len(pipeStream) > 1: std_fds = os.dup(0), os.dup(1), os.dup(2)  # Duplicate std file descriptors; will be reopened when pipe ends
		# print(f'{pipeStream=}')
		if len(pipeStream) <= 0: continue

		while pipeStream:
			args = parseCommand(pipeStream.pop(0))
			pfds = pipeItUp() if len(pipeStream) >= 1 else None # Create pipe file descriptors
			try: runCommand(args, pipe=pfds)
			except OSError as err:
				os.write(2, f'{err}\n'.encode())
				sys.exit(1)
