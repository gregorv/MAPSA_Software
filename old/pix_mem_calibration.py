import sys
from classes import *
from array import array
from optparse import OptionParser



# Add options
parser = OptionParser()

parser.add_option('-w', '--shutterdur', metavar='F', type='int', action='store',
default	=	0xFF,
dest	=	'shutterdur',
help	=	'shutter duration')

parser.add_option('-t', '--trim', metavar='F', type='int', action='store',
default	=	30,
dest	=	'trimDAC',
help	=	'Global trim DAC (0-31)')

parser.add_option('-b', '--buffer', metavar='F', type='int', action='store',
default	=	1,
dest	=	'buffer',
help	=	'Select buffer (1-4)')

parser.add_option('-m', '--mpa', metavar='F', type='int', action='store',
default	=	1,
dest	=	'mpa',
help	=	'Select mpa (1-6)')

parser.add_option('-c', '--continuous', metavar='F', type='int', action='store',
default =       0,
dest    =       'continuous',
help    =       'Enable continuous datataking')

(options,args) = parser.parse_args()

#import root after optparse to get help page from optparse
from ROOT import TGraph, TCanvas, TLine, TColor

# Establish connection
a = uasic(connection="file://connections_test.xml",device="board0")
mapsa=MAPSA(a)
read = a._hw.getNode("Control").getNode('firm_ver').read()
a._hw.dispatch()
print "Running firmware version " + str(read)

# Reset control logic
a._hw.getNode("Control").getNode("logic_reset").write(0x1)
a._hw.dispatch()

#Write number of MPAs present (Doesn't work because mapsa.config expects 6 mpas)
#mpaAmount = 2
#a._hw.getNode("Configuration").getNode("num_MPA").write(mpaAmount)
#a._hw.getNode("Configuration").getNode("mode").write(0x5)
#a._hw.dispatch()
#config._spi_wait()

# Enable clock
a._hw.getNode("Control").getNode("MPA_clock_enable").write(0x1)
a._hw.dispatch()

# Calibration disable
CE = 0

# Resolution of threshold scan (only scan every 'res' steps)
res = 2


### Hacky workaround, should be solved using num_MPA
# Amount of MPAs on board
mpasPresent = [0, 1, 0, 0, 1, 0]  # MAPSA with 2 MPAs at middle positions
#mpasPresent = [1, 1, 1, 1, 1, 1] # fully equiped MAPSA with 6 MPAs

# MPA-register in which the ripple counter data can be found (ripple counter fills MPA registers from the back, if there are less than 6 MPAs options.mpa doesn't match where ripple counter stores data
rippleRegister = 6 - sum(mpasPresent) + sum(mpasPresent[:options.mpa])

# Load default config
config = mapsa.config(Config=1,string='default')
config.upload()

# Set voltage steps of threshold DAC and trimming DAC (in mV/Step)
thrVoltStep = 1.456
trimVoltStep = 3.75

# Modify config
confdict = {'OM':[3]*6,'RT':[0]*6,'SCW':[0]*6,'SH2':[0]*6,'SH1':[0]*6,'THDAC':[0]*6,'CALDAC':[30]*6,'PML':[1]*6,'ARL':[1]*6,'CEL':[CE]*6,'CW':[0]*6,'PMR':[1]*6,'ARR':[1]*6,'CER':[CE]*6,'SP':[0]*6,'SR':[1]*6,'TRIMDACL':[options.trimDAC]*6,'TRIMDACR':[options.trimDAC]*6}
config.modifyfull(confdict) 

# Synchronous Acquisition
eventArray = []
hitArrayMem = []
thrArray = []
bxArray = []

# Asynchronous Acquisition
hitArrayCounter = []

# Start threshold scan (only every 'res' threshold)
for thr in range(0,255,res):

    print thr

    # Apply threshold
    config.modifyperiphery('THDAC',[thr]*6)
    config.upload()
    config.write()

    # Start acquisition (sequencer)

    ##########################
    ### Begin of sequencer ###
    ##########################
    
    # Set shutter duration
    a._hw.getNode("Shutter").getNode("time").write(options.shutterdur)

    # Opens shutter (mode = 0x0 single shutter, 0x1 four (buffers) consequitive shutter) 
    a._hw.getNode("Control").getNode("Sequencer").getNode('datataking_continuous').write(options.continuous)

    # Write in first buffer (default and therefore not necessary to be defined)
    #a._hw.getNode("Control").getNode("Sequencer").getNode('buffers_index').write(0)

    # Readout has to be enabled in order to get the data
    a._hw.getNode("Control").getNode("readout").write(1)
    a._hw.dispatch()
    
    ########################
    ### End of sequencer ###
    ########################

    # Readout buffer (TRUE / FALSE : Wait for sequencer) and ripple counter
    # mem, counter = mpa[options.mpa].daq().read_raw(options.buffer,1,True) # Doesn't work for less than 6 MPAs due to ripple counter data in wrong registers 
        
    counter  = a._hw.getNode("Readout").getNode("Counter").getNode("MPA"+str(rippleRegister)).getNode("buffer_"+str(options.buffer)).readBlock(25) # Ignore '-m' option, ripple counter is always here for single MPA, no matter which one 
    mem = a._hw.getNode("Readout").getNode("Memory").getNode("MPA"+str(options.mpa)).getNode("buffer_"+str(options.buffer)).readBlock(216)
    a._hw.dispatch()
    		
    ### Synchronous Acquisition ###

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
    hitArrayMem.append(sumPixHits)
    thrArray.append(thr)
    bxArray.append(bx)
    
    ### Asynchronous ripple counter ###

    counterArray = []
    for x in range(1,len(counter)): # Skip header at [0]
            counterArray.append(counter[x] & 0xFFFF) # Mask to select left pixel 
            counterArray.append((counter[x] >> 16) & 0xFFFF) # Mask to select right pixel
    hitArrayCounter.append(counterArray)	
	
print "---END OF SCAN---"

for ithr in bxArray:
    print max(ithr)

# Generate new list [[pix1_ThScan],[pix2_ThScan],..] from synchronous acquisition
pxlVsThrMem = []
for ipix in range(0,len(hitArrayMem[0])):
    pxlVsThrMem.append([item[ipix] for item in hitArrayMem])

# Generate new list [[pix1_ThScan],[pix2_ThScan],..] from asynchronous acquisition (ripple counter)
pxlVsThrCounter = []
for ipix in range(0,len(hitArrayCounter[0])):
    pxlVsThrCounter.append([item[ipix] for item in hitArrayCounter])


##########################################################
### Begin plotting uncalibrated pixels over thresholds ###
##########################################################

# Generate graphs for each pixel in synchronous memory
graphsMem = []

for ipixScan in pxlVsThrMem:
    graphsMem.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))

# Generate graphs for each pixel in asynchronous memory (ripple counter)
graphsCounter = []

for ipixScan in pxlVsThrCounter:
    graphsCounter.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))


# Draw graphs on canvas
c1 = TCanvas("graph","graph",1024,768)
c1.cd()   

for i,graph in enumerate(graphsMem):
    if i==0:
        graph.SetTitle('Threshold Scan;Threshold (DAC);Number of Hits')
        graph.GetYaxis().SetRangeUser(0,max(eventArray)*1.1)
        graph.Draw("APL")
    else:
        graph.Draw("PL")

for graph in graphsCounter:
    graph.SetLineColor(3)
    graph.Draw("PL")

# Add line for nMax
line = TLine(0,max(eventArray),graphsMem[0].GetXaxis().GetXmax(),max(eventArray))
line.SetLineColor(2)
line.Draw()

print "Max number of events during scan: %s" %max(eventArray)


#########################
### Begin calibration ###
######################### 

calibconf = config._confs[options.mpa - 1]
calibconfxmlroot = config._confsxmlroot[options.mpa - 1]

### Calculate trim values
trimOffsetArray = []
for i,pxl in enumerate(pxlVsThrCounter): # configure each pixel separately, iterator needed to distinguish between left and right pixel
    if i%2==0: # get default trimming value of left pixel (config always for two pixels (32bit))
        configTrim = int(calibconfxmlroot[i/2+1].find('TRIMDACL').text)
    else: # same for right pixel
        configTrim = int(calibconfxmlroot[(i+1)/2].find('TRIMDACR').text)

    halfMax = max(pxl)/2.0 # half of maximum amount of hits seen for all thresholds 
    
    thrValueMaxHits = pxl.index(max(pxl)) * res # threshold value at which maximum number of hits was found (res is used because index of array doesn't necessarily match threshold value, only when res=1)
    for thrStep in range(len(pxl) - 1): # highest threshold can't be trimmed
        thrValue = thrStep * res # actual threshold value of this threshold step
        if (pxl[thrStep + 1] - halfMax) < 0 and thrValueMaxHits < thrValue : # Falling edge right before half maximum (first condition selects only thresholds with less hits than half maximum, second condition selects right side of peak.
            diffToHalfMaxLeft  = abs(pxl[thrStep] - halfMax)
            diffToHalfMaxRight = abs(pxl[thrStep + 1] - halfMax)
            
            thrOffset = thrValue + diffToHalfMaxRight / (diffToHalfMaxLeft + diffToHalfMaxRight) # offset of thresholds but in threshold steps
            trimOffset = 31 + configTrim - int(round(thrOffset*thrVoltStep/trimVoltStep)) # convert from thrSteps to trimSteps and subtract from trim in configuration file
            break #go to next pixel
    else: # no break, pixel can't be trimmed because there is no right edge
        trimOffset = configTrim # just apply trim from config file 
        print "UNTRIMMED"
    trimOffsetArray.append(trimOffset)

# Limit to 5 bit for trimDAC and split into left and right trimDAC
trimDacLeft = [max(0, min(31, trimOffsetArray[x])) for x in range(0,len(trimOffsetArray),2)]
trimDacRight = [max(0, min(31, trimOffsetArray[x])) for x in range(1,len(trimOffsetArray),2)]

print 'TRIMDACL'
print trimDacLeft

print 'TRIMDACR'
print trimDacRight

##################################################
##### New threshold scan, this time calibrated ###
##################################################

# Modify config
confdict = {'OM':[3]*6,'RT':[0]*6,'SCW':[0]*6,'SH2':[0]*6,'SH1':[0]*6,'THDAC':[0]*6,'CALDAC':[30]*6,'PML':[1]*6,'ARL':[1]*6,'CEL':[CE]*6,'CW':[0]*6,'PMR':[1]*6,'ARR':[1]*6,'CER':[CE]*6,'SP':[0]*6,'SR':[1]*6,'TRIMDACL':trimDacLeft*6,'TRIMDACR':trimDacRight*6}
config.modifyfull(confdict) 
# Synchronous Acquisition
eventArrayCalib = []
hitArrayMemCalib = []
thrArray = []
bxArrayCalib = []

# Asynchronous Acquisition
hitArrayCounterCalib = []

# Start threshold scan (only every second threshold)
for thr in range(0,255,res):

    print thr

    # Apply threshold
    config.modifyperiphery('THDAC',[thr]*6)
    config.upload()
    config.write()

    # Start acquisition (sequencer)

    ##########################
    ### Begin of sequencer ###
    ##########################
    
    # Set shutter duration
    a._hw.getNode("Shutter").getNode("time").write(options.shutterdur)

    # Opens shutter (mode = 0x0 single shutter, 0x1 four (buffers) consequitive shutter) 
    a._hw.getNode("Control").getNode("Sequencer").getNode('datataking_continuous').write(options.continuous)

    # Write in first buffer (default and therefore not necessary to be defined)
    #a._hw.getNode("Control").getNode("Sequencer").getNode('buffers_index').write(0)

    # Readout has to be enabled in order to get the data
    a._hw.getNode("Control").getNode("readout").write(1)
    a._hw.dispatch()
    
    ########################
    ### End of sequencer ###
    ########################

    # Readout buffer (TRUE / FALSE : Wait for sequencer) and ripple counter
    # mem, counter = mpa[options.mpa].daq().read_raw(options.buffer,1,True) # Doesn't work for less than 6 MPAs due to ripple counter data in wrong registers 
    
    
    counter  = a._hw.getNode("Readout").getNode("Counter").getNode("MPA"+str(rippleRegister)).getNode("buffer_"+str(options.buffer)).readBlock(25) # Ignore '-m' option, ripple counter is always here for single MPA, no matter which one 
    mem = a._hw.getNode("Readout").getNode("Memory").getNode("MPA"+str(options.mpa)).getNode("buffer_"+str(options.buffer)).readBlock(216)
    a._hw.dispatch()
    		
    ### Synchronous Acquisition ###

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

    eventArrayCalib.append(nEvents)        
    hitArrayMemCalib.append(sumPixHits)
    thrArray.append(thr)
    bxArrayCalib.append(bx)
    
    ### Asynchronous ripple counter ###

    counterArrayCalib = []
    for x in range(1,len(counter)): # Skip header at [0]
            counterArrayCalib.append(counter[x] & 0xFFFF) # Mask to select left pixel 
            counterArrayCalib.append((counter[x] >> 16) & 0xFFFF) # Mask to select right pixel
    hitArrayCounterCalib.append(counterArrayCalib)	
	
print "---END OF SCAN---"

for ithr in bxArray:
    print max(ithr)

# Generate new list [[pix1_ThScan],[pix2_ThScan],..] from synchronous acquisition
pxlVsThrMem = []
for ipix in range(0,len(hitArrayMem[0])):
    pxlVsThrMem.append([item[ipix] for item in hitArrayMemCalib])

# Generate new list [[pix1_ThScan],[pix2_ThScan],..] from asynchronous acquisition (ripple counter)
pxlVsThrCounter = []
for ipix in range(0,len(hitArrayCounter[0])):
    pxlVsThrCounter.append([item[ipix] for item in hitArrayCounterCalib])


########################################################
### Begin plotting calibrated pixels over thresholds ###
########################################################

# Generate graphs for each pixel in synchronous memory
graphsMemCalib = []

for ipixScan in pxlVsThrMem:
    graphsMemCalib.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))

# Generate graphs for each pixel in asynchronous memory (ripple counter)
graphsCounterCalib = []

for ipixScan in pxlVsThrCounter:
    graphsCounterCalib.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))


# Draw graphs on canvas
c2 = TCanvas("calibgraph","calibgraph",1024,768)
c2.cd()   

for i,graphCalib in enumerate(graphsMemCalib):
    if i==0:
        graphCalib.SetTitle('Threshold Scan;Threshold (DAC);Number of Hits')
        graphCalib.GetYaxis().SetRangeUser(0,max(eventArrayCalib)*1.1)
        graphCalib.Draw("APL")
    else:
        graphCalib.Draw("PL")

for graphCalib in graphsCounterCalib:
    graphCalib.SetLineColor(3)
    graphCalib.Draw("PL")

# Add line for nMax
line = TLine(0,max(eventArrayCalib),graphsMemCalib[0].GetXaxis().GetXmax(),max(eventArrayCalib))
line.SetLineColor(2)
line.Draw()






raw_input("Press any key to exit")

