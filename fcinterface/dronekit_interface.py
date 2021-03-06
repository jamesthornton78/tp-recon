#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 14 09:48:06 2018
Dronekit interface
Passes and recieves strings from dronekit_functions which interacts with dronekit
@author: OliG
"""

import subprocess
import time
import sys

class FCInterface:

	def __init__(self, moduleFolder=''):

		self.timeoutLines = 500
		self.notificationCallbacks = {} 	# dictionary, populated by setNotificationCallback
		self.notificationQueue = [] 		# last at end
		self.enableLogging = 1				# should be enabled by default

		# opens cli running python2 dronekit functions
		filePath = moduleFolder + 'dronekit_functions.py'
		self.py2 = subprocess.Popen(['python2', '-u', filePath], stdout=subprocess.PIPE, stdin=subprocess.PIPE, universal_newlines=True)

		print ("FCInterface initialised")

	def log(self, *objects):
		if self.enableLogging:
			print(*objects)

	def interface(self, command):
		"""
		pass a function name to dronekit_functions
		returns single line string resulting from function. When DONE is passed function is considered complete and 
		script moves on.
		"""

		self.log("")
		self.log('Sending cmd:', command)
		self.py2.stdin.write(command + '\n')
		self.py2.stdin.flush()
		#self.log('Listening...')

		returnLine = None 	# always the last line before the current one
		numLinesRead = 0
		stackHeight = 0 	# number of execution levels = number of COMMANDs printed - number of DONEs printed
		while numLinesRead < self.timeoutLines:
			# self.waypoint_reached = False     (no longer required)

			# read subprocess output
			read = self.py2.stdout.readline()[:-1] # removes final newline character
			
			# print line through to interface
			self.log(str(numLinesRead) + '| ' + read)

			# handles
			if read.startswith('NOTIFY'):
				self.notificationQueue.append(read[7:])

				# (approach removed because it breaks the command cycle, complicating interpretation)
				# try:
				# 	self.waypoint_reached_fn()
				# except:
				# 	pass

			elif 'COMMAND' in read: 	# first line so will begin with '...>'' meaning startswith doesnt work
				stackHeight += 1

			elif read.startswith('DONE'):
				stackHeight -= 1
				return returnLine
				break

			else:
				# check integrity of execution stack (not working for some reason)
				if not stackHeight == 1:
					self.log("Error: stack height is wrong = ", stackHeight)

			returnLine = read
			numLinesRead += 1

		# only reached if DONE is not returned
		self.log("Command timed out after", numLinesRead, "lines read")

	def setNotificationCallback(self, name, fn):
		self.notificationCallbacks[name] = fn

	def handleNotifications(self):
		while len(self.notificationQueue) > 0:
			note = self.notificationQueue.pop(0)
			self.log("Handling notification", note)

			if note in self.notificationCallbacks:
				self.notificationCallbacks[note]()

	def initSITL(self):
		self.interface('initSITL')
		return True

	def connection(self):
		"""
		connection to vehicle through interface and performs basic setup including setting home.
		won't complete until connection has complete
		"""
		self.interface('connection')
		return True

	def runTest(self):
		print("Running test... (will disarm)")
		ans = self.interface('runTest')
		return ans

	def getHeading(self):
		"""
		no args, returns heading in degress from North
		"""
		ans = self.interface('getHeading')
		return float(ans) 
	
	def getPosition(self):
		"""
		no args, returns lat and lon as two vars
		"""
		ans = self.interface('getPosition')

		try:
			position = ans.split()
			lat = float(position[0])
			lon = float(position[1])
			return lat, lon
		except:
			self.log('getPosition failed')
			return 0, 0
		
	def getAltitude(self):
		"""
		returns altitude above ground in meters, no args
		"""
		ans = self.interface('getAltitude')
		return float(ans)

	def setWaypoint(self, lat, lon, *args):
		"""
		IN: target LAT, LON and optional altitude, if no altittude passed it will use current altitude
		"""
		try:
			alt = args[0]
		except:
			alt = self.getAltitude()

		self.interface('setWaypoint' + ' ' + str(lat) + ' ' + str(lon) + ' ' + str(alt))

	def setHeading(self, heading):
		"""
		travels in set heading (in degrees from North.)
		"""
		print("Setting FCI heading to", heading, "deg")
		self.interface('setHeading' + ' ' + str(heading))

	def startTakeoffSequence(self):
		"""
		arms the copter then takes off to 10 meters
		"""
		print("FCI-I: starting take-off sequence")
		self.interface('startTakeoffSequence')

	def startLandingSequence(self):
		"""
		starts landing copter
		"""
		self.interface('startLandingSequence')

	def waitForArm(self):
		"""
		Blocks caller until vehicle is externally armed (e.g. by RC transmitter for remote take-off), or timeout is reached
		"""
		ans = self.interface('waitForArm')
		return int(ans) # convert to bool (int)

	def waitForModeArm(self):
		"""
		Blocks caller until vehicle is externally set to GUIDED mode (e.g. by RC transmitter for remote take-off), or timeout is reached
		"""
		ans = self.interface('waitForModeArm')
		return int(ans) # convert to bool (int)		
		
	# (superseded by notification system)
	# def onActionCompleted(self, fn):
	# 	self.waypoint_reached_fn = fn
	# 	# Non-blocking callback function
	# 	# Called once by command.py during aircraft boot
	# 	# Sets up a notification so that, every time a commanded action is completed (e.g. waypoint/heading reached, take-off completed), function fn will be called-back

# Testing
# -------
if __name__ == "__main__":
   # stuff only to run when not called via 'import' here

	print("Testing FCI...")

	approxDegsPerMetre = 9e-06

	flightStage = "flight"
	numWPsDone = 0
	def waypointReachedCallback():
		global numWPsDone, flightStage, lat, lon

		print("Waypoint reached (callback)")
		numWPsDone += 1
		print("WPs completed:", numWPsDone)

		if numWPsDone >= 5:
			print(numWPsDone, "WPs complete, starting landing...")
			fci.startLandingSequence()
			flightStage = "rtl"
		else:
			print("Setting next WP...")
			fci.setWaypoint(lat, lon + approxDegsPerMetre * 20)

	# init interface
	fci = FCInterface()
	fci.setNotificationCallback('waypointReached', waypointReachedCallback) # set callback reference
	time.sleep(4)

	# [TODO] do simulator here instead

	# connect and take off
	fci.connection()
	fci.startTakeoffSequence()
	time.sleep(1)

	# get current position
	lat, lon = fci.getPosition()
	print('Initial position:', lat, lon)

	# set initial waypoint
	fci.setWaypoint(lat, lon + approxDegsPerMetre * 10) # 9e-06 deg = 1 m

	# keep checking position and handling notifications
	for i in range(10000):
		if flightStage == "rtl":
			break

		# update position
		lat, lon = fci.getPosition()
		print('Pos checked cyclically:', lat, lon)

		# handle notifications raised
		fci.handleNotifications()

		# wait
		time.sleep(0.25)
