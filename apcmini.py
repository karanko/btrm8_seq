#! /usr/bin/python
import sys
import time
import socket
#from midi import MidiConnector #py-midi
import rtmidi #python-rtmidi
import numpy

class Page:
	def __init__(self, name):
		self.name=  name
		self.grid = [False] * 64
		self.h_splits = 1
		self.outputarray = []
		self.__press_callbacks = []
		self.__data_callbacks = []
	def pressgrid(self, x):
		if len(self.__press_callbacks) < 1:
			self.outputarray = self.grid
		else:
			for cb in self.__data_callbacks:
					cb(self,x)
		if len(self.__press_callbacks) < 1:
			self.grid[x] = not self.grid[x]
		else:
			for cb in self.__press_callbacks:
				cb(self,x)
	def addpresscallback(self,externalcallback):
		self.__press_callbacks.append(externalcallback);
	def adddatacallback(self,externalcallback):
		self.__data_callbacks.append(externalcallback);	
class PageManager:
	def __init__(self):
		##other stuff
		self.pages = []
		self.currentpage_index = 0
		self.shiftdown = False
		self.udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		midiin.set_callback(self.midiin_callback)
	def sendfudi(self,message='',port=3000):
		try:
			self.udpsocket.sendto( message + ";\n", ("127.0.0.1", port))
		except socket.error as e:
			print e
	def addpage(self,name,datacallback=None,presscallback=None,h_splits=1):
		workingpage = Page(name)
		self.pages.append(workingpage)
		workingpage.h_splits = h_splits
		if datacallback:
			workingpage.adddatacallback(datacallback)
		if presscallback:
			workingpage.addpresscallback(presscallback)
		return workingpage
	def currentpage(self):
		return self.pages[self.currentpage_index]
	def setpage(self,number):
		res = False
		if 0 <= number < len(self.pages):
			self.currentpage_index = number
			print("Page %s (%s) selected"%(self.currentpage().name,self.currentpage_index))
			res = True
		else:
			print("Page %s does not exist only"% (number))	
		self.draw()
		return res
	def senddatatopd(self, index):
		try:
			page = self.pages[index]
			ugly_data = str( numpy.matrix(page.outputarray)).replace('[','').replace(']','').split('\n')
			suffix = ""
			if index > 4:
				suffix = "2"
			for i in range(len(ugly_data)):
				self.sendfudi("apcmini " + page.name + suffix+" " + str(i) + " data " + ugly_data[i] ,3000)
		except Exception, e:
			print("An exception occurred: %s" % (e))
	def draw(self):
		try:
			for i in range(len(self.currentpage().grid)):
				if self.currentpage().grid[i]:
					sub_page_offset = i / (64 / self.currentpage().h_splits ) 
					self.setbuttonstate(i,((((self.currentpage_index + sub_page_offset) % 3) + 1) * 2)-1 )
				else:
					self.setbuttonstate(i,0)
			for x in range(68, 72):
				self.setbuttonstate( x , 0 )
			if self.currentpage_index > 3:
				self.setbuttonstate(68+(self.currentpage_index%4), 2 )
			else:
				self.setbuttonstate(68+(self.currentpage_index%4), 1 )
			#not sure if this is the right place
			self.senddatatopd(self.currentpage_index)
		except Exception, e:
			print("An exception occurred: %s" % (e))
	def setbuttonstate(self,pad,state):
			#we only need to send note ons to avoid traffic
			midiout.send_message([144 & 0xF0 | 0 & 0xF, pad & 0x7F , state& 0x7F])
	def stopallclips(self,isdown):
			self.sendfudi("apcmini stopallclips " + str(int(isdown == True)) + " " +  str(int(self.shiftdown == True))   )
	def midiin_callback(self,event, data=None):
		message, deltatime = event
		try:
			if message[0] in [128,144] and message[1] == 98:
					self.shiftdown = message[0] == 144
			elif message[0] in [128,144]:
				if 0 <= message[1] <= 63 and message[0] == 128:
					pm.currentpage().pressgrid(message[1])
					self.draw()
				elif 68 <= message[1] <= 71 and message[0] == 144:
					##page selcection
					if self.shiftdown :
						self.setpage(message[1] - 68 + 4)
					else:
						self.setpage(message[1] - 68 )					
				elif message[1] == 84:
					if self.shiftdown and message[0] == 128:
						return
					self.swappages()
				elif message[1] == 89:
					self.stopallclips(message[0] == 144)
					self.setbuttonstate( message[1] , int( message[0] == 144) )
				elif 64 <= message[1] <= 67 and message[0] == 128:
					dir = message[1]-64
				else:
					print("note %r" % ( message))
			elif message[0] == 176:             	
				self.sendfudi("apcmini fader " + str(message[1] - 48) + " " + str(message[2])  , 3000)
			else:
				print("PageManager: Unhandled msg: %r" % ( message ))
		except Exception, e:
			print("An exception occurred: %s" % (e))
	def swappages(self):
		for i in range(4):
			cpi= i
			npi =  (i + 4 ) %8
			cp = self.pages[cpi]
			self.pages[cpi] = self.pages[npi]
			self.pages[npi] = cp
		for i in range(len(self.pages)):
			self.senddatatopd(i)
		#self.currentpage_index =npi
		self.draw()
		#print("c:%s n:%s" % (cp,np))

def metro_rep_press_cb(page,pad):
	for p in range(64):
		col = p % 8
		row = (p / 8) 
		page.grid[p] = row <= page.outputarray[col]
def metro_rep_data_cb(page,pad):
	if len(page.outputarray) ==0:
		page.outputarray = [0] * 8
	col = pad % 8
	row = (pad / 8) 
	page.outputarray[col] = row
def metro_gate_press_cb(page,pad):
	for p in range(64):
		col = p % 8
		row = (p / 8) % 4
		sec =  int(p < 32) 
		page.grid[p] = row <= page.outputarray[sec][col]
def metro_gate_data_cb(page,pad):
	if len(page.outputarray) ==0:
		page.outputarray = [[]] * 2
		for x in range(len(page.outputarray)):
			page.outputarray[x] = [0] * 8
	col = pad % 8
	row = (pad / 8) % 4
	sec =  int(pad < 32)
	page.outputarray[sec][col] = row
def std_press_cb(page,pad):
	for p in range(64):
		col = p % 16
		sec =  p / 16
		page.grid[p] = page.outputarray[sec][col]
def std_data_cb(page,pad):
	if len(page.outputarray) ==0:
		page.outputarray = [[]] * 4
		for x in range(len(page.outputarray)):
			page.outputarray[x] = [0] * 16
	col = pad % 16
	sec = pad / 16 
	page.outputarray[sec][col] = int(not bool(page.outputarray[sec][col]))


## setup out
midiout = rtmidi.MidiOut()
for i, j in enumerate(midiout.get_ports()):
	if "APC MINI" in j:
		print("OUT: %s" % j)
		try:
			midiout.open_port(midiout.get_ports().index(j))
			break
		except (EOFError, KeyboardInterrupt):
			sys.exit()
		

## setup in
midiin = rtmidi.MidiIn()
for i, j in enumerate(midiin.get_ports()):
	if "APC MINI" in j:
		print("IN: %s" % j)
		try:
			midiin.open_port(midiin.get_ports().index(j))
			break
		except (EOFError, KeyboardInterrupt):
			sys.exit()
					
pm = PageManager()		
pm.addpage("metropolis_repeats",metro_rep_data_cb,metro_rep_press_cb)
pm.addpage("metropolis_gate_dual",metro_gate_data_cb,metro_gate_press_cb,2)
pm.addpage("metropolis_pitch",metro_rep_data_cb,metro_rep_press_cb)
pm.addpage("std_seq_x4",std_data_cb,std_press_cb,4)

pm.addpage("metropolis_repeats",metro_rep_data_cb,metro_rep_press_cb)
pm.addpage("metropolis_gate_dual",metro_gate_data_cb,metro_gate_press_cb,2)
pm.addpage("metropolis_pitch",metro_rep_data_cb,metro_rep_press_cb)
pm.addpage("std_seq_x4",std_data_cb,std_press_cb,4)

pm.setpage(0)

##main loop
print("Entering main loop. Press Control-C to exit.")
try:
	while True:
		time.sleep(1)       	
except (EOFError, KeyboardInterrupt):
	print('')
finally:
	print("Exit.")
	midiin.close_port()
	midiout.close_port()
	del midiin
	del midiout
