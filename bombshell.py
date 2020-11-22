#! python3.8
import os, sys, re

BOMBA = chr(0x1F4A3) # Bomb unicode character constant
inList, outList = [], [] # Used to store names and descriptors of redirect input and output files
std_fds = None # Used to store copied std file descriptors when using pipe


def restoreStdFds():
	if not std_fds: return
	for i in range(3): os.dup2(std_fds[i], i, True) # reopen std file descriptors


def changeDirectory(args):
	if len(args) < 2: args.append(os.environ['HOME'])
	else: args[1] = re.sub('^~', os.environ['HOME'], args[1]) # Replace tilde with home alias
	try: os.chdir(args[1])
	except FileNotFoundError: print(f'cd: no such file or directory: {args[1]}')
	except PermissionError: print('User does not have permission to access this directory.')
	except NotADirectoryError: print('Path is not a directory.')


def pipeItUp():
	pfds = os.pipe() # Create file descriptors for pipe io
	for fd in pfds: os.set_inheritable(fd, True)
	return pfds


def prompt():
	if os.getenv('PS1'): os.write(1, os.environ['PS1'].encode())
	else:
		promptStr = re.sub(f"^{os.environ['HOME']}", '~', f'{os.getcwd()} {BOMBA} ')
		os.write(1, promptStr.encode()) # Print current working directory and prompt symbol
	try:
		sys.stdin.flush()
		blocks = []
		while buffer := sys.stdin.readline():
			print(f'{buffer=}')
			if buffer[-1] == '\n':
				blocks.append(buffer[:-1])
				break
			else: blocks.append(buffer)
		inputStr = ''.join(blocks)
	except EOFError as err:
		print(err)
		sys.exit()
	except KeyboardInterrupt:
		print()
		sys.exit()
	return inputStr


def parseCommand(commStr: str):
	global inList, outList
	inList = list(map(lambda s: re.sub('< *', '', s.strip()),
                    re.findall('< *[^ ]+', commStr))) # Parse and store redirected inputs
	outList = list(map(lambda s: re.sub('> *', '', s.strip()),
                    re.findall('> *[^ ]+', commStr))) # Parse and store redirected outputs
	args = re.sub('(> *[^ ]+)|(< *[^ ]+)', '', commStr).strip().split() # Parse program arguments
	if not len(args): return
	return args


BUILT_INS = {'cd': changeDirectory, 'exit': sys.exit}


def runCommand(args: list, pipe: tuple=None, runBg: bool=False):
	if args[0] in BUILT_INS: # Run built in commands
		BUILT_INS[args[0]](args if args[0] != 'exit' else None)
		return

	pid = os.fork()
	if pid == 0: # Child fork
		try:
			if pipe: # Route output through pipe
				os.dup2(pipe[1], 1) # Assign pipe's file descriptor to stdout's
				for fd in pipe: os.close(fd)
			if inList: os.dup2(os.open(inList[-1], os.O_RDONLY), 0) # Redirect input
			if outList: os.dup2(os.open(outList[-1], os.O_CREAT | os.O_WRONLY | os.O_TRUNC), 1) # Redirect output
			os.execvp(args[0], args) # Execute program
		except FileNotFoundError: print(f'bombshell: {args[0]}: Command not found')
		sys.exit(1)
	elif pid > 0: # Parent fork
		if not runBg:
			try: os.wait() # Wait for child fork to finish before resuming execution
			except KeyboardInterrupt: os.abort()
		global std_fds
		if pipe:
			os.dup2(pipe[0], 0, True) # Close stdin, duplicate pipe read fd into stdin fd
			for fd in pipe: os.close(fd) # Close parent pipe file descriptors
		elif std_fds:
			restoreStdFds() # Reopen closed std file descriptors
			for fd in std_fds: os.close(fd) # Close duplicated std file descriptors
			std_fds = None
	else: raise OSError('Fork Error') # Fork error


if __name__ == "__main__":
	while True:
		inputStr = prompt()
		pipeStream = inputStr.split('|') # Parse command pipes
		if len(pipeStream) > 1: std_fds = os.dup(0), os.dup(1), os.dup(2)  # Duplicate std file descriptors; will be reopened when pipe ends

		while pipeStream:
			command = pipeStream.pop(0)
			bg = ' &' in command # Run in background flag
			command = re.sub(' &', '', command)
			args = parseCommand(command)
			pfds = pipeItUp() if len(pipeStream) >= 1 else None # Create pipe file descriptors
			try: runCommand(args, pfds, bg)
			except OSError as err:
				os.write(2, f'{err}\n'.encode())
				sys.exit(1)
