import sys, select, os, array
import numpy as np
from argparse import ArgumentParser
from classes import *
from xml.dom import minidom
#import xml.etree.ElementTree 
from xml.etree.ElementTree import Element, SubElement, Comment
from array import array
#import ROOT
from ROOT import TGraph, TCanvas, gPad, TFile

### Define settings ###

# Global
sgnlPlty = 0 # Count on pos/neg calstrobe signal
buffNum = 1

# Asynchronous readout enable
asyncROEnbl = 1

# default Trim DAC
trimDAC = 0

# Shutter options
shtMode = 0x0

# Disable calibration as default
calEnbl = 0

## Command-line options ##

parser = ArgumentParser()
parser.add_argument('-s', '--setting', metavar='F', type='string', action='store',
default	=	'none',
dest	=	'setting',
help	=	'Settings ie default, calibration, testbeam etc')


# Calibration strobe settings
parser.add_argument('-n', '--number', metavar='F', type='int', action='store',
default	=	1000,
dest	=	'StrbN',
help	=	'Number of calstrobe pulses to send')

parser.add_argument('-c', '--charge', metavar='F', type='int', action='store',
default	=	70,
dest	=	'calCharge',
help	=	'Charge for caldac')

parser.add_argument('-l', '--strobelength', metavar='F', type='int', action='store',
default	=	50,
dest	=	'strbLen',
help	=	'Length of each pulse (in system clock cycles)')

parser.add_argument('-d', '--strobedist', metavar='F', type='int', action='store',
default	=	50,
dest	=	'strbDist',
help	=	'Time between pulses (in system clock cycles)')

parser.add_argument('-j', '--strobedelay', metavar='F', type='int', action='store',
default	=	0xFF,
dest	=	'strbDel',
help	=	'Time between shutter open and first pulse (in system clock cycles)')

# Shutter settings

parser.add_argument('-w', '--shutterdur', metavar='F', type='int', action='store',
default	=	0xFFFF,
dest	=	'shtDur',
help	=	'shutter duration (in system clock cycles) (ignored if "--setting" set to "calibration")')

# Aquisition settings
parser.add_argument('-r', '--resolution', metavar='F', type='int', action='store',
default	=	1,
dest	=	'ThldRes',
help	=	'Scan threshold for each r-th step')

args = parser.parse_args()

#######################

# Establish connection
a = uasic(connection="file://connections_test.xml",device="board0")
mapsa = MAPSA(a)
read = a._hw.getNode("Control").getNode('firm_ver').read()
a._hw.dispatch()
print "Running firmware version " + str(read)

# Enable clock
a._hw.getNode("Control").getNode("MPA_clock_enable").write(0x1)
a._hw.dispatch()

# Load default cfg
config = mapsa.config(Config=1,string='default') 
config.upload()

# Check if in calibration-mode 

if args.setting == 'calibration':
	calEnbl = 1

# Define cfg for calibration
confdict = {'OM':[3]*6,'RT':[0]*6,'SCW':[0]*6,'SH2':[0]*6,'SH1':[0]*6,'THDAC':[0]*6,'CALDAC':[calCharge]*6,'PML':[1]*6,'ARL':[1]*6,'CEL':[calEnbl]*6,'CW':[0]*6,'PMR':[1]*6,'ARR':[asyncROEnbl]*6,'CER':[calEnbl]*6,'SP':[sgnlPlty]*6,'SR':[1]*6,'TRIMDACL':[trimDAC]*6,'TRIMDACR':[trimDAC]*6}
config.modifyfull(confdict) 

# Apply strobe and shutter settings
mapsa.daq().Strobe_settings(strbN,strbDel,strbLen,strbDist,cal=calEnbl)

# Threshold scan
x1 = array('d')
y1 = []
for x in range(0,256): 
	if x%10==0:
		print "THDAC " + str(x)

	config.modifyperiphery('THDAC',[x]*6) # change threshold for all 6 MPAs
	config.upload()
	config.write()

	mapsa.daq().Sequencer_init(shtMode,shtDur)

	pix,mem = mapsa.daq().read_data(buffNum) # pix = [[MPA1_header,MPA1_header,MPA1_pix1,..,MPA1_pix48],..,[MPA6]]

	ipix=0
	for p in pix: # Loop over MPAs

			p.pop(0) # Drop double header
			p.pop(0)
			y1.append([]) # Append an empty array
			y1[ipix].append(array('d',p)) # Append array of 48 pixels for each MPA and THDAC [MPA1[THDAC1[Pix1,..,Pix48] , .. , THDAC256[Pix1,..,Pix48]],..,MPA6[],[][]..]

			ipix+=1
        	
        x1.append(x) # Array of THDAC 0-255

#	if x==100:
#		print y1[0]

	for i in y1[0]:
		print i[45]
	
