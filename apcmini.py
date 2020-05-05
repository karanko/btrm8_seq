import sys
import time
import socket
#from midi import MidiConnector #py-midi
import rtmidi #python-rtmidi

class Page:
	def __init__(self, name):
		self.name=  name
		self.grid = [False] * 64
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

		print("grid %r %s" % ( x,self.grid[x]) )
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
	def addpage(self,name):
		workingpage = Page(name)
		self.pages.append(workingpage)
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
		
	def draw(self):
		for i in range(len(self.currentpage().grid)):
			if self.currentpage().grid[i]:
				self.setbuttonstate(i,(((self.currentpage_index  % 3) + 1) * 2)-1 )
			else:
				self.setbuttonstate(i,0)
		for x in range(68, 72):
			self.setbuttonstate( x , 0 )
		self.setbuttonstate(68+self.currentpage_index, 1 )

	def setbuttonstate(self,pad,state):
			#we only need to send note ons to avoid traffic
			midiout.send_message([144 & 0xF0 | 0 & 0xF, pad & 0x7F , state& 0x7F])
	def stopallclips(self,isdown):
			self.sendfudi("apcmini stopallclips " + str(int(isdown == True)) + " " +  str(int(self.shiftdown == True))   )
	def midiin_callback(self,event, data=None):
		message, deltatime = event

		if message[0] in [128,144] and message[1] == 98:
				self.shiftdown = message[0] == 144
		elif message[0] in [128,144]:
			if 0 <= message[1] <= 64 and message[0] == 128:
				pm.currentpage().pressgrid(message[1])
				self.draw()
			elif 68 <= message[1] <= 71 and message[0] == 144:
				##page selcection
				self.setpage(message[1] - 68)
			elif message[1] == 89:
				self.stopallclips(message[0] == 144)
				self.setbuttonstate( message[1] , int( message[0] == 144) )
			else:
				print("note %r" % ( message))
		elif message[0] == 176:             	
			self.sendfudi("apcmini fader " + str(message[1] - 48) + " " + str(message[2])  , 3000)
		else:
			print("PageManager: Unhandled msg: %r" % ( message ))


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

##build metropolis class to tidy things up??

## let the bodge begin
pm = PageManager()
##rpage 0
mr = pm.addpage("metropolis_repeats")
def metro_rep_press_cb(page,pad):
	for p in range(64):
		col = p % 8
		row = (p / 8) 
		page.grid[p] = row <= page.outputarray[col]
mr.addpresscallback(metro_rep_press_cb)

def metro_rep_data_cb(page,pad):
	if len(page.outputarray) ==0:
		page.outputarray = [0] * 8
	col = pad % 8
	row = (pad / 8) 
	print("r:%s c:%r" % (row, col))
	page.outputarray[col] = row
	print(page.outputarray)
mr.adddatacallback( metro_rep_data_cb)

##rpage 1
dg = pm.addpage("metropolis_gate_dual")
def metro_gate_press_cb(page,pad):
	for p in range(64):
		col = p % 8
		row = (p / 8) % 4
		sec =  int(p < 32) 

		page.grid[p] = row <= page.outputarray[sec][col]

dg.addpresscallback(metro_gate_press_cb)

def metro_gate_data_cb(page,pad):
	if len(page.outputarray) ==0:
		page.outputarray = [[]] * 2
		page.outputarray[0] = [0] * 8
		page.outputarray[1] = [0] * 8
	col = pad % 8
	row = (pad / 8) % 4
	sec =  int(pad < 32) 
	print("r:%s c:%r s:%s " % (row, col, sec))
	page.outputarray[sec][col] = row
	print(page.outputarray[0])
	print(page.outputarray[1])
dg.adddatacallback( metro_gate_data_cb)

##rpage 2
p = pm.addpage("metropolis_pitch")

def metro_rep_press_cb(page,pad):
	for p in range(64):
		col = p % 8
		row = (p / 8) 
		page.grid[p] = row <= page.outputarray[col]
p.addpresscallback(metro_rep_press_cb)

def metro_rep_data_cb(page,pad):
	if len(page.outputarray) ==0:
		page.outputarray = [0] * 8
	col = pad % 8
	row = (pad / 8) 
	print("r:%s c:%r" % (row, col))
	page.outputarray[col] = row
	print(page.outputarray)
p.adddatacallback( metro_rep_data_cb)

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
	s.close()
	midiin.close_port()
	midiout.close_port()
	del midiin
	del midiout
