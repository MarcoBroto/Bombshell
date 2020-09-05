#! python3.8
import sys, os, re

BOMBA = chr(0x1F4A3)

def promptCommand() -> str:
	print(BOMBA, end='')
	commStr = input()
	return commStr

def parseCommand(commStr: str):
	commStr = re.split('[ ]+', commStr)

def runCommand(commStr: str, args):
	try:
		rc = os.fork()
	except OSError as err:
		print(f'{err}: Unable to fork')
		return

	if rc == 0: # Child branch
		print('Child running.')
		os.execvp(commStr, args)
	elif rc > 0: # Parent branch
		print('Parent waiting...')
		os.wait()
		print('Parent done waiting.')
	else: # Fork error
		raise OSError

if __name__ == "__main__":
	parseCommand(input())