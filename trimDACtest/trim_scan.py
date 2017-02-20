# Change trimDAC, then do threshold scan. Repeat for all trimDACs to identify nonlinear behaviour etc 

import sys
from ROOT import TGraph, TCanvas, TLine
from classes import *
from array import array
from optparse import OptionParser
import pickle

parser = OptionParser()

# General options

parser.add_option('-m', '--MPA', metavar='N', type='int',
default	=	'1',
dest	=	'mpanum',
help	=	'Calibrate MPA N')

parser.add_option('-r', '--resolution',metavar='N', type='int',
default =       '1',
dest    =       'resolution',
help    =       'Only scan every N thresholds to speed up scan. Results in lower precision of TrimDACs')

# CALDAC options (setting charge also enables calDAC) 

parser.add_option('-e', '--enable', action='store_true',
dest    =       'calEnbl',
default =       False,
help    =       'Enable calibration')

parser.add_option('-c', '--charge',metavar='C', type='int',
dest    =       'calCharge',
help    =       'Enable calibration with charge C (0 - 0xFF). If not set CalDAC is disabled.')

parser.add_option('-n', '--number',metavar='N', type='int',
dest    =       'calNum',
help    =       'Number of calibration pulses')

parser.add_option('-l', '--strobelength',metavar='N', type='int',
dest    =       'calLen',
help    =       'Length of calibration pulses')

# Shutter length

parser.add_option('-s', '--shutterdur',metavar='N', type='int',
default =       '0xFFFF',
dest    =       'shutterDur',
help    =       'Shutter open time (0 - 0xFFFF).')

(options, args) = parser.parse_args()

if options.calEnbl == None and (options.calCharge != None or options.calNum != None or options.calLen !=None): # Check if user has forgotten to enable calibration
    print "Calibration isn't enabled, setting charge, number or length will have no effect."
    quit()
else: # Defaults for calibration but no explicit charge, number or strobe length
    options.calCharge = 80
    options.calNum = 1000
    options.calLen = 40


# Connection and GLIB 
a = uasic(connection="file://connections_test.xml",device="board0")
glib = a._hw 

# Source all classes
mapsa = MAPSA(a)

# Get all 6 MPAs and corresponding configs
mpa=[]
conf=[]

for i in range(0,6):
    mpa.append(MPA(glib,i+1))
    conf.append(mpa[i].config("data/Default_MPA.xml"))

# Define MPA (1-6) (iMPA 2 or 5 for double assembly)

mpaDict = {0:2,1:5}
iMPA = options.mpanum - 1  # Zero-indexed (from 0 to 5 on full assembly) 

# Set voltage steps of threshold DAC and trimming DAC (in mV/Step)
thrVoltStep = 1.456
trimVoltStep = 3.75

# Modify config

glib.getNode("Control").getNode("MPA_clock_enable").write(0x1)
glib.dispatch()

glib.getNode("Configuration").getNode("num_MPA").write(0x2)

# Define default config

defaultPixelCfg = {'PML':1,'ARL':1,'CEL':int(options.calEnbl),'CW':0,'PMR':1,'ARR':1,'CER':int(options.calEnbl),'SP':0,'SR':1,'TRIMDACL':0,'TRIMDACR':0}
defaultPeripheryCfg = {'OM':3,'RT':0,'SCW':0,'SH2':0,'SH1':0,'THDAC':0,'CALDAC':options.calCharge}
if options.calEnbl:
    mapsa.daq().Strobe_settings(options.calNum,0x8F,options.calLen,40,cal=1) # Push number of pulses, delay between shutter open and first pulse, length of pulses, time between pulses, enable calibration (on GLIB) to GLIB

# Upload
for key in defaultPeripheryCfg:
    conf[iMPA].modifyperiphery(key,defaultPeripheryCfg[key])
for pix in range(0,24):
    for key in defaultPixelCfg:
        conf[iMPA].modifypixel(pix + 1,key,defaultPixelCfg[key])

conf[iMPA].upload()
glib.getNode("Configuration").getNode("mode").write(0x1)
glib.dispatch()
    


# Arrays to be filled by trim scan. In the end they contain a threshold scan for each trimming value
eventTrimArray = []
hitTrimArray = []
thrTrimArray = []
bxTrimArray = []
hitTrimArrayCounter = []

for trim in range(0, 32): 
    for pix in range(0,24): # No dispatch, upload or write necessary as that happens in first threshold scan
        conf[iMPA].modifypixel(pix + 1,'TRIMDACL',trim)
        conf[iMPA].modifypixel(pix + 1,'TRIMDACR',trim)

    # Arrays to be filled by threshold scan    
    eventArray = []
    hitArray = []
    thrArray = []
    bxArray = []
    hitArrayCounter = []
    
    # Start threshold scan
    for thr in range(0,255, options.resolution): # Only every 'options.resolution'-steps, reflected in precision of falling edges after trimming
    
        #print thr
        # Apply threshold
        
        conf[iMPA].modifyperiphery('THDAC',thr)
        conf[iMPA].upload()
        
        glib.getNode("Configuration").getNode("mode").write(0x1)
        conf[iMPA].spi_wait() # includes dispatch
        
    
        ##########################
        ####### Sequencer ########
        ##########################
        # Opens shutter (mode = 0x0 single shutter, 0x1 four (buffers) consequitive shutter) 
        # Set shutter duration
        # Write in first buffer (default and therefore not necessary to be defined)
        # Readout has to be enabled in order to get the data. Default.
        mapsa.daq().Sequencer_init(0, options.shutterDur )
    
        counter  = glib.getNode("Readout").getNode("Counter").getNode("MPA"+str(iMPA + 1)).getNode("buffer_1").readBlock(25) 
        glib.dispatch()
        
    
        # Readout ripple counter 
        counterArray = []
        for x in range(1,len(counter)): # Skip header at [0]
                counterArray.append(counter[x] & 0x7FFF) # Mask to select left pixel. First bit is not considered as this seems sometimes to be set erronously. (Lots of entries with 0b1000000000000000)  
                counterArray.append((counter[x] >> 16) & 0x7FFF) # Mask to select right pixel. Same as above.
    
        # Readout buffer (TRUE / FALSE : Wait for sequencer)
        mem = mpa[mpaDict[iMPA]-1].daq().read_raw(1,1,True)[0]
    
        # Mem integer array to binary string in readable order (header,bx,pix) 
        binMemStr= ""
        for i in range(0,216):
            binMemStr = binMemStr + '{0:032b}'.format(mem[215-i])
    
        # String to binary array
        binMem = [binMemStr[x:x+72] for x in range(0,len(binMemStr),72)]
    
        # Get elements of binary string
        hd = []
        bx = []
        pix = []
        for entry in binMem:
            hd.append(entry[0:8])
            bx.append(entry[8:24])
            pix.append(entry[24:72])
    
        # Count number of Events
        nEvents = 0
        for event in hd:
            if event == "11111111":
                nEvents+=1
    
        # Sum hits per pixel
        sumPixHits = [0]*48
        for event in pix:
            for i, ipix in enumerate(event):
                sumPixHits[i]+=int(ipix)
    
        # bunch crossing from binary to int
        bx=[int(ibx,2) for ibx in bx]
    
        eventArray.append(nEvents)        
        hitArray.append(sumPixHits)
        thrArray.append(thr)
        bxArray.append(bx)
        hitArrayCounter.append(counterArray)
    
    
    print "---END OF SCAN--- of trim %s" %trim

    eventTrimArray.append(eventArray)
    hitTrimArray.append(hitArray)
    thrTrimArray.append(thrArray)
    bxTrimArray.append(bxArray)
    hitTrimArrayCounter.append(hitArrayCounter)

# New arrays with threshold scan for each trim
pxlVsThrMemTrim = []
pxlVsThrCounterTrim = []

graphsMemTrim = []
graphsCounterTrim = []
maxHitsPerPixTrim = [] # For scaling of graphs
for trim in range(0,len(hitTrimArray)):
    # Generate new list [TrimDAC1[[pix1_ThScan],[pix2_ThScan],..],TrimDAC1[[..]],...] from memory
    pxlVsThrMem = []
    for ipix in range(0,len(hitTrimArray[trim][0])):
        pxlVsThrMem.append([item[ipix] for item in hitTrimArray[trim]])
    pxlVsThrMemTrim.append(pxlVsThrMem)

    # Generate new list [[pix1_ThScan],[pix2_ThScan],..] from ripple counter
    pxlVsThrCounter = []
    for ipix in range(0,len(hitTrimArrayCounter[trim][0])):
        pxlVsThrCounter.append([item[ipix] for item in hitTrimArrayCounter[trim]])
    pxlVsThrCounterTrim.append(pxlVsThrCounter)
    
# Find falling edges for each trim value and each pixel
trimFallingEdge = []
for pxlVsThrCounter in pxlVsThrCounterTrim:
    thrArrayFallingEdge = [] # Falling edges for this trimming value

    for pxl in pxlVsThrCounter:
        
        pxlMax = max(pxl)
        thresholdValueAndPxl = zip(thrArray,pxl) # Match thresholds to amount of hits and create list of tuples
    
        maxBin = pxl.index(pxlMax) # Find lowest threshold with maximum amount of hits
        pxlRightOfPeak = thresholdValueAndPxl[maxBin:] # Get rid of rising edge (less hits than maxbin)
         
        halfMax = pxlMax/2 # Middle of falling edge
        for threshold in pxlRightOfPeak: # Find first threshold with less hits than middle of falling edge, then break
            if threshold[1] < halfMax: 
                thrArrayFallingEdge.append(threshold[0])
                break # Only one threshold is needed, leave loop

    trimFallingEdge.append(thrArrayFallingEdge)

# Turn array of trimming value arrays with pixels in the sub array into transposed array ( Pix1(trimDac[0-31]), Pix2(),.,,,Pix48(trimDac[0-31]))
pxlTrimFallingEdge = [list(trim) for trim in zip(*trimFallingEdge)]

# Draw graphs on canvas
c1 = TCanvas("graph","graph",1024,768)

graphs = []
for pxl in pxlTrimFallingEdge:
    graphs.append(TGraph(32,array('d',range(32)),array('d',pxl))) # Generate graph with trimDACs on x-axis and falling edge position (in threshold-steps) on y-axis

for i,graph in enumerate(graphs):
    graph.SetLineColor(i) 
    if i==0:
        graph.SetTitle('Trim Scan;Trim (DAC);Falling Edge (Threshold)')
        #graph.GetYaxis().SetRangeUser(0,max(maxHitsPerPixTrim[trim])*1.1)
        graph.Draw("APL")
    else:
        graph.Draw("PL")

pickle.dump(pxlTrimFallingEdge, open(str(sys.path[0])+"/trimDacFallingEdge.pickle", "w"))


raw_input("Press any key to exit")
