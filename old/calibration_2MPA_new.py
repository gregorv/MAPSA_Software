import sys
from ROOT import TGraph, TCanvas, TLine
from classes import *
from array import array
from optparse import OptionParser

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


# File to which trimming values are written
trimFile = open('trimDac_MPA'+str(iMPA+1), 'w')

# File to which THDAC values of falling edges after trimming are written
fallingEdgeFile = open('data/fallingEdgeTrimmed_MPA'+str(iMPA+1), 'w')


# Modify config

glib.getNode("Control").getNode("MPA_clock_enable").write(0x1)
glib.dispatch()

glib.getNode("Configuration").getNode("num_MPA").write(0x2)

# Define default config

defaultPixelCfg = {'PML':1,'ARL':1,'CEL':int(options.calEnbl),'CW':0,'PMR':1,'ARR':1,'CER':int(options.calEnbl),'SP':0,'SR':1,'TRIMDACL':30,'TRIMDACR':30}
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


print "---END OF SCAN---"

numOfEvents = []
for ithr in bxArray:
#    print 'Total clock cycles per threshold: %s' %max(ithr) # Events without a hit aren't saved but number of clock cycles until memory is full can be constructed from BX-Id
    numOfEvents.append(max(ithr))


print "Average number of clock cycles until memory is full: %s" %(sum(numOfEvents)/len(numOfEvents))



# Generate new list [[pix1_ThScan],[pix2_ThScan],..] from memory
pxlVsThrMem = []
for ipix in range(0,len(hitArray[0])):
    pxlVsThrMem.append([item[ipix] for item in hitArray])

# Generate new list [[pix1_ThScan],[pix2_ThScan],..] from ripple counter
pxlVsThrCounter = []
for ipix in range(0,len(hitArrayCounter[0])):
    pxlVsThrCounter.append([item[ipix] for item in hitArrayCounter])

# Generate graphs for each pixel
graphsMem = []
for ipixScan in pxlVsThrMem:
    graphsMem.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))

graphsCounter = []
maxHitsPerPix = [] # For scaling of graph
for ipixScan in pxlVsThrCounter:
    graphsCounter.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))
    maxHitsPerPix.append(max(ipixScan))


# Draw graphs on canvas
c1 = TCanvas("graph","graph",1024,768)
c1.cd()    

for i,graph in enumerate(graphsMem):
    graph.SetLineColor(3)
    if i==0:
        graph.SetTitle('Threshold Scan;Threshold (DAC);Number of Hits')
        graph.GetYaxis().SetRangeUser(0,max(maxHitsPerPix)*1.1)
        graph.Draw("APL")
    else:
        graph.Draw("PL")

for graph in graphsCounter:
    graph.Draw("PL")

# Add line for nMax
line = TLine(0,max(eventArray),graphsMem[0].GetXaxis().GetXmax(),max(eventArray))
line.SetLineColor(2)
line.Draw()

print "Max number of events during scan: %s" %max(eventArray)


###########################################
########### Begin calibration #############
###########################################

# Find noisy pixels
noisyPixels = []
for i,pxl in enumerate(pxlVsThrCounter):
    if max(pxl) > 10000:
        print "Pixel %s is very noisy at %s hits" %(i,max(pxl))
        noisyPixels.append(0)
    else:
        noisyPixels.append(1)

# Find falling edges on which is calibrated
thrArrayFallingEdge = []
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

print "Falling edges at %s" %list(enumerate(thrArrayFallingEdge, start=1))

pxlLowestThreshold =  min(thrArrayFallingEdge)
trimDacToTheLeft = [(pxl - pxlLowestThreshold) * (thrVoltStep/trimVoltStep) for pxl in thrArrayFallingEdge]

# Normalize trimDac and take into account that we started with trimDac set to 30
trimDac = [max(0, (30 - int(round(pxlTrimDac)))) for pxlTrimDac in trimDacToTheLeft]

print "Lower all trimDACs by %s" %min(trimDac)
# Set all trimDac as low as possible
trimDac = [pix - min(trimDac) for pix in trimDac]

# Write trimDac values to MPA
for pix in range(0,24):
    conf[iMPA].modifypixel(pix + 1,'TRIMDACL',trimDac[2*pix])
    conf[iMPA].modifypixel(pix + 1,'TRIMDACR',trimDac[2*pix + 1])

conf[iMPA].upload()
glib.getNode("Configuration").getNode("mode").write(0x1)
conf[iMPA].spi_wait() # includes dispatch


# Write twice to push config to Memory_OutConf to check what has been written 
glib.getNode("Configuration").getNode("mode").write(0x1)
conf[iMPA].spi_wait()

outConf = glib.getNode("Configuration").getNode("Memory_OutConf").getNode("MPA"+str(iMPA + 1)).getNode("config_1").readBlock(0x19) # Get written config
glib.dispatch()
readconf = []
for pix in outConf: # Format this config to extract trimDac values
#    print '{0:020b}'.format(pix)
    readconf.append((pix >> 2) & 0b11111)
    readconf.append((pix >> 12) & 0b11111)

eventArray = []
hitArray = []
thrArray = []
bxArray = []
hitArrayCounter = []


# Start threshold scan for calibrated pixels
for thr in range(0,255, options.resolution):

    #print thr

    # Apply threshold
    
    conf[iMPA].modifyperiphery('THDAC',thr)
    conf[iMPA].upload()
    
    glib.getNode("Configuration").getNode("mode").write(0x1)
    conf[iMPA].spi_wait() # includes dispatch
    
    # Start acquisition (sequencer) (Enable single (0) or four (4) consequitive buffers for shutter. Set Shutter duration and do final 'write' to push config to MPA)
    mapsa.daq().Sequencer_init(0,options.shutterDur)

    counter  = glib.getNode("Readout").getNode("Counter").getNode("MPA"+str(iMPA + 1)).getNode("buffer_1").readBlock(25) 
    glib.dispatch()

    counterArray = []
    for x in range(1,len(counter)): # Skip header at [0]
            counterArray.append(counter[x] & 0x7FFF) # Mask to select left pixel. First bit is not considered as this seems sometimes to be set erronously. (Lots of entries with 0b1000000000000000)  
            counterArray.append((counter[x] >> 16) & 0x7FFF) # Mask to select right pixel. Same as above

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


print "---END OF SCAN---"
numOfEvents = []
for ithr in bxArray:
#    print 'Cycles per threshold: %s' %max(ithr)
    numOfEvents.append(max(ithr))


print "Average number of clock cycles until memory is full: %s" %(sum(numOfEvents)/len(numOfEvents))

# Generate new list [[pix1_ThScan],[pix2_ThScan],..] from memory
pxlVsThrMem = []
for ipix in range(0,len(hitArray[0])):
    pxlVsThrMem.append([item[ipix] for item in hitArray])

# Generate new list [[pix1_ThScan],[pix2_ThScan],..] from ripple counter
pxlVsThrCounter = []
for ipix in range(0,len(hitArrayCounter[0])): # Loop over pixels
    pxlVsThrCounter.append([item[ipix] for item in hitArrayCounter])

# Generate graphs for each pixel
graphsMem = []

for ipixScan in pxlVsThrMem:
    graphsMem.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))

graphsCounter = []
maxHitsPerPix = []
for ipixScan in pxlVsThrCounter:
    graphsCounter.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))
    maxHitsPerPix.append(max(ipixScan))


# Draw graphs on canvas
c2 = TCanvas("graph2","graph",1024,768)
c2.cd()    

for i,graph in enumerate(graphsMem):
    graph.SetLineColor(3)
    if i==0:
        graph.SetTitle('Threshold Scan;Threshold (DAC);Number of Hits')
        graph.GetYaxis().SetRangeUser(0,max(maxHitsPerPix)*1.1)
        graph.Draw("APL")
    else:
        graph.Draw("PL")

for graph in graphsCounter:
    graph.Draw("PL")

# Add line for nMax
line = TLine(0,max(eventArray),graphsMem[0].GetXaxis().GetXmax(),max(eventArray))
line.SetLineColor(2)
line.Draw()

print "Max number of events during scan: %s" %max(eventArray)


####################################################################
########### Check if calibration was successful ####################
####################################################################

# Find pixel with lowest threshold
thrArrayFallingEdge = []
thrArrayPeak = []

for pxl in pxlVsThrCounter:
    
    thresholdValueAndPxl = zip(thrArray,pxl) # Match thresholds to amount of hits and create list of tuples
    pxlMax = max(pxl)

    maxBin = pxl.index(pxlMax) # Find lowest threshold with maximum amount of hits
    pxlRightOfPeak = thresholdValueAndPxl[maxBin:] # Get rid of rising edge (less hits than maxbin)
     
    halfMax = pxlMax/2 # Middle of falling edge
    for threshold in pxlRightOfPeak: # Find first threshold with less hits than middle of falling edge, then break
        if threshold[1] < halfMax: 
            thrArrayFallingEdge.append(threshold[0])
            break
    
    ## Find peak
    thrArrayPeak.append(maxBin)

meanThrArrayPeak = sorted(thrArrayPeak)[len(thrArrayPeak)/2] # Mean threshold of noise 

print "Falling edges at %s" %list(enumerate(thrArrayFallingEdge, start=1)) # Enumerate to make matching value to pixel number easier

untrimmableMask = [] # Mask of untrimmable pixels (e.g. trimDac is too small), 1 is ok and 0 is untrimmable
for i, pix in enumerate(thrArrayFallingEdge):
    if abs(pix -  pxlLowestThreshold) > 5:
        print "Untrimmable pixel %s with falling edge at %s" %(i + 1,pix)
        untrimmableMask.append(0) # Mask this pixel as it can't be trimmed far enough
    else:
        untrimmableMask.append(1)

# Write twice to push config to Memory_OutConf to check what has been written 
glib.getNode("Configuration").getNode("mode").write(0x1)
conf[iMPA].spi_wait()

outConf = glib.getNode("Configuration").getNode("Memory_OutConf").getNode("MPA"+str(iMPA + 1)).getNode("config_1").readBlock(0x19) # Get written config
glib.dispatch()
readconf = []
for pix in outConf: # Format this config to extract trimDac values
#    print '{0:020b}'.format(pix)
    readconf.append((pix >> 2) & 0b11111)
    readconf.append((pix >> 12) & 0b11111)

#print "Written Trim DAC: %s" %list(enumerate(readconf[2:], start=1)) # Skip periphery config (first two entries)


# Write trimDac files to file 'trimDac' for later use 
for pxl in trimDac:
    trimFile.write(str(pxl))
    trimFile.write('\n')
trimFile.close()

# Write falling edges of trimmed peaks to file to do detection of untrimmable pixels
for pxl in thrArrayFallingEdge:
    fallingEdgeFile.write(str(pxl))
    fallingEdgeFile.write('\n')
fallingEdgeFile.close() 

# Write graph with calibrated pixels to file

c2.Print('plots/MPA_'+str(iMPA+1)+'_Calibration_post.pdf', 'pdf')


print "Trimming on threshold %s" %pxlLowestThreshold
print "Untrimmable pixel mask: %s" %untrimmableMask
print "Noisy pixel mask: %s" %noisyPixels
print "Trimming bits: %s" %list(enumerate(trimDac, start=1))
print "Average peak at %s" %(meanThrArrayPeak)

raw_input("Press any key to exit")
