import sys
import time

n = 0

#print("Started py2 script")

def count():
	global n
	n += 1
	print("Counted to {!s}".format(n))
	return n

# listen for input
while 1:
	cmd = raw_input(">")

	if cmd == "count":
		count()
	elif cmd == "exit":
		sys.exit()
	else:
		print("Unkown cmd:", cmd)