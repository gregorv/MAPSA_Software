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
default    =    'none',
dest    =    'setting',
help    =    'settings ie default, calibration, testbeam etc')

parser.add_option('-c', '--charge', metavar='F', type='int', action='store',
default    =    70,
dest    =    'calCharge',
help    =    'Charge for caldac')

parser.add_option('-w', '--shutterdur', metavar='F', type='int', action='store',
default    =    0xFFFFF,
dest    =    'shutterDur',
help    =    'shutter duration')


parser.add_option('-n', '--number', metavar='F', type='int', action='store',
default    =    0x5,
dest    =    'calNumber',
help    =    'number of calstrobe pulses to send')

parser.add_option('-l', '--strobelength', metavar='F', type='int', action='store',
default    =    50,
dest    =    'strobeLen',
help    =    'length of strobe')

parser.add_option('-i', '--strobedist', metavar='F', type='int', action='store',
default    =    50,
dest    =    'strobeDist',
help    =    'time between strobes')

parser.add_option('-d', '--strobedelay', metavar='F', type='int', action='store',
default    =    0xFF,
dest    =    'strobeDel',
help    =    'time before first strobe')

parser.add_option('-r', '--resolution ', metavar='F', type='int', action='store',
default    =    '1',
dest    =    'res',
help    =    'resolution, skip each r-th threshold step to speed up threshold scan')

parser.add_option('-y', '--string ', metavar='F', type='string', action='store',
default    =    '',
dest    =    'string',
help    =    'extra string')


(options, args) = parser.parse_args()


shutterMode = 0x0 # shutter options


buffnum = 1

if options.setting=='calibration':
    calEnbl = 1 # Set Calibration Enable bit
else:
    calEnbl = 0
signlPlt = 0 # Signal polarity



######## Configuration end ####

a = uasic(connection="file://connections_test.xml",device="board0")
mapsa = MAPSA(a)
read = a._hw.getNode("Control").getNode('firm_ver').read()
a._hw.dispatch()
print "Running firmware version " + str(read)

a._hw.getNode("Control").getNode("MPA_clock_enable").write(0x1)
a._hw.dispatch()

config = mapsa.config(Config=1,string='default') # load default cfg
config.upload()





confdict = {'OM':[3]*6,'RT':[0]*6,'SCW':[0]*6,'SH2':[0]*6,'SH1':[0]*6,'THDAC':[0]*6,'CALDAC':[options.calCharge]*6,'PML':[1]*6,'ARL':[1]*6,'CEL':[calEnbl]*6,'CW':[0]*6,'PMR':[1]*6,'ARR':[1]*6,'CER':[calEnbl]*6,'SP':[signlPlt]*6,'SR':[1]*6,'TRIMDACL':[30]*6,'TRIMDACR':[30]*6}
config.modifyfull(confdict) 

mapsa.daq().Strobe_settings(options.calNumber,options.strobeDel,options.strobeLen,options.strobeDist,cal=calEnbl)

x1 = array('d')
y1 = []
for x in range(0,256): # start threshold scan
    if x%options.res!=0:
        continue # skip some threshold values due to resolution option 
    if x%10==0:
        print "THDAC " + str(x)

    config.modifyperiphery('THDAC',[x]*6) # change threshold for all 6 MPAs
    config.upload()
    config.write()

    mapsa.daq().Sequencer_init(shutterMode,options.shutterDur)

    pix,mem = mapsa.daq().read_data(buffnum) # pix = [[MPA1_header,MPA1_header,MPA1_pix1,..,MPA1_pix48],..,[MPA6]]

#    pixMatrixNoHeaders = np.delete(np.array(pix), [:2] , 1) # Create numpy array and delete headers    
    
        
        
    ipix = 0

    for mpa in pix: # Loop over MPAs

        del mpa[0:2] # Drop double header
        y1.append([]) # Append an empty array
        y1[ipix].append(array('d',mpa)) # Append array of 48 pixels for each MPA and THDAC [MPA1[THDAC1[Pix1,..,Pix48] , .. , THDAC256[Pix1,..,Pix48]],..,MPA6[],[][]..]

        ipix += 1

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
    calibconfxmlroot    =    calibconfsxmlroot[i]
    xdvals.append(0.)
    c1.cd(i+1)
    trimDacMPA = [] # Trimming values for each pixel for one MPA 
    yarr =  np.array(y1[i]) # [ THDAC1[Pix1,..,Pix48] , .. , THDAC256[Pix1,..,Pix48] ]
    grarr.append([])
    gr1 = []
    yarrv.append(yarr) # Equivalent to y1 without empty brackets at the end


    for pxl in range(0,len(yarr[0,:])): # loop over 48 pixels
        onePixAllThlds = yarr[:,pxl] # loop over 256 THDAC for one pixel
        

        if max(onePixAllThlds)==0:
            print "zero"
        gr1.append(TGraph(len(x1)-1,array('d',thldSteps),array('d',onePixAllThlds)))
        if pxl==0: # draw curve for first pixel
            
            gr1[pxl].SetTitle(';DAC Value (1.456 mV);Counts (1/1.456)')
            grarr[i].append(gr1[pxl])
            grarr[i][pxl].Draw()
            gr1[pxl].Write(str(pxl))
        else: # draw other pixels
            grarr[i].append(gr1[pxl])
            grarr[i][pxl].Draw('same')
            gr1[pxl].Write(str(pxl))
            gPad.Update()
        
        halfmax = max(onePixAllThlds)/2.0
        maxbin = np.where(onePixAllThlds==max(onePixAllThlds)) # array with threshold with most hits for single pixel, given as nested 2d array with usually 1 entry

        for thldValue in range(0,len(thldSteps)-1): # Loop over all THDAC

            if (onePixAllThlds[thldValue + 1] - halfmax)<0.0 and thldValue > maxbin[0][0]: # Falling edge right before half maximum (first condition selects only thresholds with less hits than half maximum, second condition selects right side of peak. Runs only once due to break.)
                if pxl%2==0: # get trimming value of left pixel (config always for two pixels (32bit)) (initially set to 30)
                    prev_trim = int(calibconfxmlroot[(pxl)/2+1].find('TRIMDACL').text)
                else: # same for right pixel
                    prev_trim = int(calibconfxmlroot[(pxl+1)/2].find('TRIMDACR').text)
               
                diffToHalfMaxFromLeft  = abs(onePixAllThlds[thldValue] - halfmax)
                diffToHalfMaxFromRight = abs(onePixAllThlds[thldValue +1] - halfmax)
                xdacval = thldValue + diffToHalfMaxFromRight/(diffToHalfMaxFromLeft + diffToHalfMaxFromRight)
                
                trimDacPix = 31 + prev_trim - int(round(xdacval*1.456/3.75)) # x*th_step/trim_step . Result can be bigger than 31 which hardware can't do, this will be checked later. 
                xdvals[i] += xdacval*1.456/3.75 
                trimDacMPA.append(trimDacPix)
                break # go to next pixel (pixel trimmed)
    
            if thldValue==len(thldSteps)-2: # No curve, save old value
                if pxl%2==0: # Left pixel
                    prev_trim = int(calibconfxmlroot[(pxl)/2+1].find('TRIMDACL').text)
                else: # Right pixel
                    prev_trim = int(calibconfxmlroot[(pxl+1)/2].find('TRIMDACR').text)
    
                trimDacPix = int(prev_trim)
                trimDacMPA.append(trimDacPix)
                print "UNTRIMMED" # no trimmable threshold / no falling edge found
                break # go to next pixel (pixel not trimmed in relation to previous pixel)
    trimDacMAPSA.append(trimDacMPA) # All MPAs (MAPSA)
print trimDacMAPSA
ave = 0
for x in xdvals:
    ave+=x/48. # average per MPA
ave/=6. # average of all MPAs ### MUST BE CHANGED TO ACCOUNT FOR DIFFERENT NUMBER OF MPAs!

# Calculate an offset for each MPA to account for differences
offset = []
for i in range(0,6):
    ave15 = 0
    for j in trimDacMAPSA[i]:
        ave15+=j
    ave15/=len(trimDacMAPSA[i])
    mpacorr = xdvals[i]/48. - ave
    offset.append( 15 - int(round(ave15 + mpacorr)))

colors = [[],[],[],[],[],[]] 
for iy1 in range(0,len(yarrv[0][0,:])): # Loop over pixels twice
    upldac = []
    for i in range(0,6):
        trimDacMPA  = trimDacMAPSA[i]
        upldac.append(trimDacMPA[iy1]+offset[i])
    
    ## Normalize trimming values uploaded to MPA to fit in 5-bit TRIMDAC
    for u in range(0,len(upldac)):
        upldac[u] = max(0,upldac[u])
        upldac[u] = min(31,upldac[u])
        if upldac[u]==31:
            colors[u].append(2) # red curve (can't trim enough because TRIMDAC has only 5 bit)
        elif upldac[u]==0:
            colors[u].append(4) # blue curve (can't trim enough, wrong direction)
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
#                print trimDacMPA
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
########## Plot calibrated thresholds

allMPAsFallingEdges = []
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



######################################################
########## Get falling edges after calibration #######
######################################################

        # Find pixel with lowest threshold
        thrArrayFallingEdge = []
        pxlVsThrCounter = []
        for i in range(0,len(yarr[0,:])): # loop over pixels
            pxlVsThrCounter.append(yarr[:,i].tolist())
        for pxl in pxlVsThrCounter:
            ## Find falling edge
            halfMax = max(pxl)/2
            pxlDiff = [abs(x - halfMax) for x in pxl] # Difference of hits for each threshold to half maximum of hits
            thrRightOfHalfMaxFalling = max([             # Highest threshold to get threshold right after halfmax of falling edge
                                        pxlDiff.index(pxlDiffI) # Match differences of hits to threshold values
                                        for pxlDiffI in sorted(pxlDiff)[:4] # Four threshold values with smallest distance to halfmax (left/right of rising edge and left/right of falling edge)
                                        ])
            thrArrayFallingEdge.append(thrRightOfHalfMaxFalling)
        allMPAsFallingEdges.append(thrArrayFallingEdge)

print "Falling edges at %s" %allMPAsFallingEdges

print 'Means'
for m in means:
    print m/48.

c2.Print('plots/Scurve_Calibration'+options.string+'_post.root', 'root')
c2.Print('plots/Scurve_Calibration'+options.string+'_post.pdf', 'pdf')
c2.Print('plots/Scurve_Calibration'+options.string+'_post.png', 'png')

print ""
print "Done"



