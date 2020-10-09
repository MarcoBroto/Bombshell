#! python3.8
import os, sys, re

BOMBA = chr(0x1F4A3) # Bomb character constant
outList = [] # Used to store names and descriptors of redirect output files
std_fds = None # Used to store copied std file descriptors when using pipe


def restoreStdFds():
	if not std_fds: return
	for i in range(3): # reopen std file descriptors
		os.dup2(std_fds[i], i)
		os.set_inheritable(i, True)


def changeDirectory(args):
	if len(args) < 2: args.append(re.search('.{1}', os.getcwd()).group())
	try: os.chdir(args[1])
	except FileNotFoundError: print(f'asdfacd: no such file or directory: {args[1]}')
	except PermissionError: print('User does not have permission to access this directory.')
	except NotADirectoryError: print('Path is not a directory.')


def runInBackground(command, args): pass #TODO: Implement run program in background


def redirectOutput():
	global outList
	try:
		if not outList: return #TODO: fix bug that removes stdin data when read
		outList = [os.open(file, os.O_CREAT | os.O_WRONLY) for file in outList] # Store open file descriptors
		for line in sys.stdin:
			for fd in outList: os.write(fd, line.encode())
		for fd in outList: os.close(fd)
		sys.stdout.flush()
	except OSError as err: print(err)


def pipeItUp():
	pfds = os.pipe() # Create file descriptors for pipe io
	for fd in pfds: os.set_inheritable(fd, True)
	return pfds


def promptCommand():
	print(f'{os.getcwd()} {BOMBA}', end=' ')
	try: commStr = input()
	# except EOFError: sys.exit(1)
	except KeyboardInterrupt:
		print()
		sys.exit()
	return commStr


def parseCommand(commStr: str):
	sys.stdout.flush()
	global outList
	outList = list(map(lambda s: re.sub('> *', '', s.strip()),
                    re.findall('> *[^ ]+', commStr))) # Parse and store redirected outputs
	args = re.split('[ ]+', re.sub('> *[^ ]+', '', commStr).strip()) # Parse program arguments
	if not len(args): return
	return args


BUILT_INS = {'cd': changeDirectory, 'exit': sys.exit}


def runCommand(args: [str], pipe: tuple):
	# print(f'{args=}')
	# print(f'{outList=}')
	# print(f'{pipe=}')
	
	if args[0] in BUILT_INS:
		BUILT_INS[args[0]](args if args[0] != 'exit' else None)
		return

	try: rc = os.fork()
	except OSError as err:
		print(f'{err}: Unable to fork')
		sys.exit(1)

	if pipe: # Route output through pipe
		os.dup2(pipe[1], 1) # Assign pipe's file descriptor to stdout's
		os.set_inheritable(1, True)
		os.close(pipe[1])
		# for fd in pipe: os.close(fd)

	if rc == 0: # Child branch
		try:
			# if pipe: # Route output through pipe
			# 	os.dup2(pipe[1], 1) # Assign pipe's file descriptor to stdout's
			# 	os.set_inheritable(1, True)
			# 	for fd in pipe: os.close(fd)
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
	else: raise OSError # Fork error


if __name__ == "__main__":
	while True:
		inputStr = promptCommand()
		commandList = re.split('[|]', inputStr) # Parse command pipes
		if len(commandList) > 1: std_fds = os.dup(0), os.dup(1), os.dup(2)  # Duplicate std file descriptors; will be reopened when pipe ends
		# print(f'{commandList=}')

		while commandList:
			args = parseCommand(commandList.pop(0))
			pfds = pipeItUp() if len(commandList) >= 1 else None
			runCommand(args, pipe=pfds)
