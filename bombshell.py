#! python3.8
import os, sys, re

BOMBA = chr(0x1F4A3)
outList = sys.stdout

def changeDirectory(pathStr):
	try: os.chdir(pathStr)
	except FileNotFoundError: print('Directory does not exist.')
	except PermissionError: print('User does not have permission to access this directory.')
	except NotADirectoryError: print('Path is not a directory.')

BUILT_INS = {'cd': changeDirectory, 'exit': sys.exit}

def redirectOutput(path):
	os.set_inheritable(1, True)
	os.open(outList, os.O_CREAT | os.O_WRONLY)

def promptCommand():
	print(f'{os.getcwd()} {BOMBA}', end=' ')
	try: commStr = input()
	except KeyboardInterrupt:
		print()
		sys.exit()
	return commStr

def parseCommand(commStr: str):
	outputs = list(map(lambda x: re.sub('> *', '', x.strip()),
                    re.findall('> *[^ ]+', commStr))) # Parse and store redirected outputs
	args = re.split('[ ]+', re.sub('> *[^ ]+', '', commStr)) # Parse program arguments
	if not len(args): return
	return args

def runCommand(args):
	if commStr in BUILT_INS:
		if len(args): BUILT_INS[commStr](args[1])
		else: BUILT_INS[commStr]()
		return

	try:
		rc = os.fork()
	except OSError as err:
		print(f'{err}: Unable to fork')
		return

	if rc == 0: # Child branch
		# print('Child running...')
		try:
			# redirectOutput(outList)
			print(args)
			os.execvp(commStr, args)
			# os.write(1, sys.stdout)
		except FileNotFoundError: print(f'bombshell: {commStr}: Command not found')
		except ValueError as err: print(err)
		# print('Child done running.')
		sys.exit()
	elif rc > 0: # Parent branch
		# print('Parent waiting...')
		os.wait()
		# print('Parent done waiting.')
	else: raise OSError # Fork error

def runInBackground(command, args):
	pass

def pipeItUp():
	pass

if __name__ == "__main__":
	while True:
		commStr = promptCommand()
		args = parseCommand(commStr)
		runCommand(args)
