#! python3.8
import os, sys, re

BOMBA = chr(0x1F4A3)

def changeDirectory(pathStr):
	try: os.chdir(pathStr)
	except FileNotFoundError: print('Directory does not exist.')
	except PermissionError: print('User does not have permission to access this directory.')
	except NotADirectoryError: print('Path is not a directory.')

def promptCommand():
	print(f'{os.getcwd()} {BOMBA}', end=' ')
	try: commStr = input()
	except KeyboardInterrupt:
		print()
		exit()
	return commStr

def parseCommand(commStr: str):
	args = re.split('[ ]+', commStr)
	if not len(args): return
	return args[0], args

def runCommand(commStr: str, args):
	try:
		rc = os.fork()
	except OSError as err:
		print(f'{err}: Unable to fork')
		return

	if rc == 0: # Child branch
		# print('Child running...')
		try: os.execvp(commStr, args)
		except FileNotFoundError:
			print(f'bombshell: {commStr}: Command not found')
		# print('Child done running.')
		exit()
	elif rc > 0: # Parent branch
		# print('Parent waiting...')
		os.wait()
		# print('Parent done waiting.')
	else: raise OSError # Fork error

def redirectOutput(writeData):
	pass

def runInBackground(command, args):
	pass

if __name__ == "__main__":
	while True:
		commStr = promptCommand()
		command, args = parseCommand(commStr)
		runCommand(commStr, args)
