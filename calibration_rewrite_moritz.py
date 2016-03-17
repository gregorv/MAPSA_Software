
from classes import *
from xml.dom import minidom
import xml.etree.ElementTree 
from xml.etree.ElementTree import Element, SubElement, Comment
import sys, select, os, array
from array import array
import ROOT
from ROOT import TGraph, TCanvas, gPad, TFile

import numpy as np

import matplotlib.pyplot as plt
from matplotlib.pyplot import show, plot

from optparse import OptionParser


######## Configuration start #######

parser = OptionParser()
parser.add_option('-s', '--setting', metavar='F', type='string', action='store',
default	=	'none',
dest	=	'setting',
help	=	'settings ie default, calibration, testbeam etc')

parser.add_option('-c', '--charge', metavar='F', type='int', action='store',
default	=	70,
dest	=	'calCharge',
help	=	'Charge for caldac')

parser.add_option('-w', '--shutterdur', metavar='F', type='int', action='store',
default	=	0xFFFFF,
dest	=	'shutterDur',
help	=	'shutter duration')


parser.add_option('-n', '--number', metavar='F', type='int', action='store',
default	=	0x5,
dest	=	'calNumber',
help	=	'number of calstrobe pulses to send')

parser.add_option('-l', '--strobelength', metavar='F', type='int', action='store',
default	=	50,
dest	=	'strobeLen',
help	=	'length of strobe')

parser.add_option('-i', '--strobedist', metavar='F', type='int', action='store',
default	=	50,
dest	=	'strobeDist',
help	=	'time between strobes')

parser.add_option('-d', '--strobedelay', metavar='F', type='int', action='store',
default	=	0xFF,
dest	=	'strobeDel',
help	=	'time before first strobe')

parser.add_option('-r', '--resolution ', metavar='F', type='int', action='store',
default	=	'1',
dest	=	'res',
help	=	'resolution')

parser.add_option('-y', '--string ', metavar='F', type='string', action='store',
default	=	'',
dest	=	'string',
help	=	'extra string')


(options, args) = parser.parse_args()


shutterMode = 0x0 # shutter options


buffnum = 1

if options.setting=='calibration':
	calEnbl = 1 # Set Calibration Enable bit
else:
	calEnbl = 0
signlPlt = 0 # Signal polarity


######## Configuration end ####

config = mapsa.config(Config=1,string='default') # load default cfg
config.upload()

a = uasic(connection="file://connections_test.xml",device="board0")
mapsa = MAPSA(a)
read = a._hw.getNode("Control").getNode('firm_ver').read()
a._hw.dispatch()
print "Running firmware version " + str(read)

a._hw.getNode("Control").getNode("MPA_clock_enable").write(0x1)
a._hw.dispatch()




confdict = {'OM':[3]*6,'RT':[0]*6,'SCW':[0]*6,'SH2':[0]*6,'SH1':[0]*6,'THDAC':[0]*6,'CALDAC':[options.calCharge]*6,'PML':[1]*6,'ARL':[1]*6,'CEL':[calEnbl]*6,'CW':[0]*6,'PMR':[1]*6,'ARR':[1]*6,'CER':[calEnbl]*6,'SP':[signlPlt]*6,'SR':[1]*6,'TRIMDACL':[30]*6,'TRIMDACR':[30]*6}
config.modifyfull(confdict) 

mapsa.daq().Strobe_settings(options.calNumber,options.strobeDel,options.strobeLen,options.strobeDist,cal=calEnbl)

x1 = array('d')
y1 = []
for x in range(0,256): # start threshold scan
	if x%options.res!=0:
		continue # skip threshold value due to resolution option 
	if x%10==0:
		print "THDAC " + str(x)

	config.modifyperiphery('THDAC',[x]*6) # change threshold for all 6 MPAs
	config.upload()
	config.write()

	mapsa.daq().Sequencer_init(shutterMode,options.shutterDur)

	pix,mem = mapsa.daq().read_data(buffnum) # pix = [[MPA1_header,MPA1_header,MPA1_pix1,..,MPA1_pix48],..,[MPA6]]
	ipix = 0

	for p in pix: # Loop over MPAs

			p.pop(0) # Drop double header
			p.pop(0)
			y1.append([]) # Append an empty array
			y1[ipix].append(array('d',p)) # Append array of 48 pixels for each MPA and THDAC [MPA1[THDAC1[Pix1,..,Pix48] , .. , THDAC256[Pix1,..,Pix48]],..,MPA6[],[][]..]

			ipix+=1

	x1.append(x) # Array of THDAC 0-255
	

print "Generating nominal per pixel trimDacPix values"

calibconfs = config._confs
calibconfsxmlroot = config._confsxmlroot

		
c1 = TCanvas('c1', '', 700, 900)
c1.Divide(2,3)
thldSteps =  np.array(x1)
trimDacMAPSA = []
yarrv = []
grarr = []
xdvals = []

for i in range(0,6): # loop over MPA
	backup=TFile("plots/backup_preCalibration_"+options.string+"_MPA"+str(i)+".root","recreate")
	calibconfxmlroot	=	calibconfsxmlroot[i]
	xdvals.append(0.)
	c1.cd(i+1)
	trimDacMPA = [] # Trimming values for each pixel for one MPA 
	yarr =  np.array(y1[i]) # [ THDAC1[Pix1,..,Pix48] , .. , THDAC256[Pix1,..,Pix48] ]
	grarr.append([])
	gr1 = []
	yarrv.append(yarr) # Equivalent to y1 without empty brackets at the end


	for iy1 in range(0,len(yarr[0,:])): # loop over 48 pixels
		onePixAllThlds = yarr[:,iy1] # loop over 256 THDAC for one pixel

		if max(onePixAllThlds)==0:
			print "zero"
		gr1.append(TGraph(len(x1)-1,array('d',thldSteps),array('d',onePixAllThlds)))
		if iy1==0: # draw curve for first pixel
			
			gr1[iy1].SetTitle(';DAC Value (1.456 mV);Counts (1/1.456)')
			grarr[i].append(gr1[iy1])
			grarr[i][iy1].Draw()
			gr1[iy1].Write(str(iy1))
		else: # draw other pixels
			grarr[i].append(gr1[iy1])
			grarr[i][iy1].Draw('same')
			gr1[iy1].Write(str(iy1))
			gPad.Update()


		halfmax = max(onePixAllThlds)/2.0
		maxbin = np.where(onePixAllThlds==max(onePixAllThlds)) # array with highest thresholds for one pixel 
		for thldValue in range(0,len(thldSteps)-1): # Loop over all THDAC

			if (onePixAllThlds[thldValue + 1] - halfmax)<0.0 and thldValue > maxbin[0][0]: # Falling edge right before half maximum 
				if iy1%2==0: # Left pixel (config always for two pixels (32bit))
					prev_trim = int(calibconfxmlroot[(iy1)/2+1].find('TRIMDACL').text)
				else: # Right pixel
					prev_trim = int(calibconfxmlroot[(iy1+1)/2].find('TRIMDACR').text)
				
				xdacval = (abs(onePixAllThlds[thldValue] - halfmax)*thldSteps[thldValue] + abs(onePixAllThlds[thldValue + 1]-halfmax)*thldSteps[thldValue + 1])/(abs(onePixAllThlds[thldValue]-halfmax) + abs(onePixAllThlds[thldValue + 1]-halfmax)) # calculate x @ half maximum

				trimDacPix = 31 + prev_trim - int(round(xdacval*1.456/3.75)) # x*th_step/trim_step  
				xdvals[i] += xdacval*1.456/3.75 
				
				if thldValue%100==0:
					print("halfmax: %s" %(halfmax))
					print("maxbin: %s" %(maxbin))
					print("prev_trim: %s" %(prev_trim))
					print("xdacval: %s" %(xdacval))
					print("trimDacPix: %s" %(trimDacPix))

				trimDacMPA.append(trimDacPix)
				break # go to next pixel (pixel trimmed)
	
			if thldValue==len(thldSteps)-2: # No curve, save old value
				if iy1%2==0: # Left pixel
					prev_trim = int(calibconfxmlroot[(iy1)/2+1].find('TRIMDACL').text)
				else: # Right pixel
					prev_trim = int(calibconfxmlroot[(iy1+1)/2].find('TRIMDACR').text)
	
				trimDacPix = int(prev_trim)
				trimDacMPA.append(trimDacPix)
				print "UNTRIMMED" # no trimmable threshold found
				break # go to next pixel (pixel not trimmed)
		
	trimDacMAPSA.append(trimDacMPA) # All MPAs (MAPSA)

	print trimDacMPA


ave = 0
for x in xdvals:
	ave+=x/48. # average per MPA
ave/=6. # average of all MPAs


offset = []
for i in range(0,6):
	ave15 = 0
	for j in trimDacMAPSA[i]:
		ave15+=j
	ave15/=len(trimDacMAPSA[i])
	avearr.append(ave15)
	mpacorr = xdvals[i]/48. - ave
	offset.append( 15 - int(round(ave15 + mpacorr)))

thdacvvorg = []
colors = [[],[],[],[],[],[]] 
for iy1 in range(0,len(yarrv[0][0,:])):
	thdacvvorg.append(np.array(trimDacMAPSA)[:,iy1])
	upldac = []
	for i in range(0,6):
		trimDacMPA  = trimDacMAPSA[i]
		upldac.append(trimDacMPA[iy1]+offset[i])


	for u in range(0,len(upldac)):
		upldac[u] = max(0,upldac[u])
		upldac[u] = min(31,upldac[u])
		if upldac[u]==31:
			colors[u].append(2) # red curve
		elif upldac[u]==0:
			colors[u].append(4) # blue curve
		else:
			colors[u].append(1) # black curve

	if iy1%2==0:
		config.modifypixel((iy1)/2+1,'TRIMDACL',upldac)
	else:
		config.modifypixel((iy1+1)/2,'TRIMDACR',upldac)


c1.Print('plots/Scurve_Calibration'+options.string+'_pre.root', 'root')
c1.Print('plots/Scurve_Calibration'+options.string+'_pre.pdf', 'pdf')
c1.Print('plots/Scurve_Calibration'+options.string+'_pre.png', 'png')
config.modifyperiphery('THDAC',[100]*6)
config.upload()
config.write()
for i in range(0,6):
	xmlrootfile = config._confsxmltree[i]
	print xmlrootfile
	a = config._confsxmlroot[i]
	print "writing data/Conf_calibrated_MPA"+str(i+1)+"_config1.xml"
	xmlrootfile.write("data/Conf_calibrated_MPA"+str(i+1)+"_config1.xml")


### Same threshold scan with calibrated pixel
print "Testing Calibration"

config1 = mapsa.config(Config=1,string='calibrated')
config1.upload()

config1.modifyperiphery('OM',[3]*6)
config1.modifyperiphery('RT',[0]*6)
config1.modifyperiphery('SCW',[0]*6)
config1.modifyperiphery('SH2',[0]*6)
config1.modifyperiphery('SH1',[0]*6)
config1.modifyperiphery('THDAC',[0]*6)
config1.modifyperiphery('CALDAC', [options.calCharge]*6)
for x in range(1,25):
	config1.modifypixel(x,'PML', [1]*6)
	config1.modifypixel(x,'ARL', [1]*6)
	config1.modifypixel(x,'CEL', [calEnbl]*6)
	config1.modifypixel(x,'CW', [0]*6)
	config1.modifypixel(x,'PMR', [1]*6)
	config1.modifypixel(x,'ARR', [1]*6)
	config1.modifypixel(x,'CER', [calEnbl]*6)
	config1.modifypixel(x,'SP',  [signlPlt]*6) 
	config1.modifypixel(x,'SR',  [1]*6) 


config1.write()


x1 = array('d')
y1 = []
for x in range(0,256):
			if x%options.res!=0:
				continue
			if x%10==0:
				print "THDAC " + str(x)

			config1.modifyperiphery('THDAC',[x]*6)
			config1.upload()
			config1.write()
	
			mapsa.daq().Sequencer_init(shutterMode,options.shutterDur)
			pix,mem = mapsa.daq().read_data(buffnum)
			ipix=0

			for p in pix:

				p.pop(0)
				p.pop(0)
				y1.append([])
				y1[ipix].append(array('d',p))

				ipix+=1
			x1.append(x)
			

c2 = TCanvas('c2', '', 700, 900)
c2.Divide(2,3)

thldSteps =  np.array(x1)
yarrv = []
gr2arr = []
means = []
for i in range(0,6):
		backup=TFile("plots/backup_postCalibration_"+options.string+"_MPA"+str(i)+".root","recreate")
		
		c2.cd(i+1)
		yarr =  np.array(y1[i])
		gr2arr.append([])
		gr2 = []
		means.append(0.)
		yarrv.append(yarr)
		for iy1 in range(0,len(yarr[0,:])):
			onePixAllThlds = yarr[:,iy1]

			gr2.append(TGraph(len(x1)-1,array('d',thldSteps),array('d',onePixAllThlds)))
			
			if iy1==0:

				gr2[iy1].SetTitle(';DAC Value (1.456 mV);Counts (1/1.456)')
				gr2arr[i].append(gr2[iy1])
				gr2arr[i][iy1].SetLineColor(colors[i][iy1])
				gr2arr[i][iy1].Draw()
				gr2[iy1].Write(str(iy1))

			else:
				gr2arr[i].append(gr2[iy1])
				gr2arr[i][iy1].SetLineColor(colors[i][iy1])
				gr2arr[i][iy1].Draw('same')
				gr2[iy1].Write(str(iy1))
				gPad.Update()
			means[i]+=gr2[iy1].GetMean(1)
print 'Means'
for m in means:
	print m/48.

c2.Print('plots/Scurve_Calibration'+options.string+'_post.root', 'root')
c2.Print('plots/Scurve_Calibration'+options.string+'_post.pdf', 'pdf')
c2.Print('plots/Scurve_Calibration'+options.string+'_post.png', 'png')

print ""
print "Done"



