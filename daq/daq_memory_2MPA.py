import sys
from classes import *
from array import array
from optparse import OptionParser
from ROOT import TGraph, TCanvas, TLine
from MPACalibration import MPACalibration

iMPA = 1 # Only do this for MPA 5, the 2nd MPA in the SPI-chain (0-indexed)
MPANum = 4 # 0-indexed absolute number of MPA 5 

hitFile = open('data/synchronous_data_noise_MPA'+str(MPANum+1),'w')

# Calibrate MPA (only use MPA 5 as it has confirmed failed bonds)
calibration = MPACalibration([2,5]) # Argument reflects assembly which is actually on board 
calibration.thresholdScan(MAPSA = 5, calEnbl = 1) 
calibration.writeCalibrationToMPA()

# Take connection, GLIB and MPA from calibration 
glib = calibration._glib 
mapsaClasses = calibration._mapsaClasses

conf = []
mpa = []
for i in range(0,6):
    mpa.append(MPA(glib,i+1)) # List of instances of MPA, one for each MPA
    conf.append(mpa[i].config("data/Default_MPA.xml"))

# Define default config
calibration.thresholdScan(MAPSA=5)
edges = calibration.findFallingEdges()[-1] #Get edges  for the last MPA in the chain
edges.sort()
length = len(edges)
threshold = (edges[length/2] + edges[(length+1)/2])/2 # Set global threshold at median of falling edges
calibration._conf[iMPA].modifyperiphery('THDAC',threshold) # Write threshold to MPA 'iMPA'
calibration._conf[iMPA].upload()
calibration._glib.getNode("Configuration").getNode("mode").write(calibration._nMPA - 1)
calibration._conf[iMPA].spi_wait() # includes dispatch

shutterDur = 0xFFF #0xFFFF is maximum, in clock cycles

eventArray = []
bxArray = []
hitArrayMemory = []
for i in range(0,1000):
    ##########################
    ### Begin of sequencer ###
    ##########################
    mapsaClasses.daq().Sequencer_init(0, shutterDur )
    
    ########################
    ### End of sequencer ###
    ########################

    # Readout buffer (TRUE / FALSE : Wait for sequencer) with absolute MPA-values
    mem = mpa[MPANum].daq().read_raw(1,1,True)[0]

    # Mem integer array to binary string in readable order (header,bx,pix) 
    binMemStr= ""
    for i in range(0,216):
        binMemStr = binMemStr + '{0:032b}'.format(mem[215-i])

    # String to binary array
    binMem = [binMemStr[x:x+72] for x in range(0,len(binMemStr),72)]

    # Get elements of binary string
    hd = []
    bx = []
    hits = []
    for entry in binMem:
        hd.append(entry[0:8])
        bx.append(entry[8:24])
        hits.append(entry[24:72])
    
    # Put event string into lists, one entry per pixel 
    hitArrayRun = []
    for event in hits:
        hitArrayEvent = [] 
        for pix in event:
            hitArrayEvent.append(int(pix))
        hitArrayRun.append(hitArrayEvent)

    # Count number of Events
    nEvents = 0
    for event in hd:
        if event == "11111111":
            nEvents+=1

    # bunch crossing from binary to int
    bx=[int(ibx,2) for ibx in bx]

    eventArray.append(nEvents)        
    bxArray.append(bx)
    hitArrayMemory.append(hitArrayRun)

    for hit in hits:
        hitFile.write(hit)
        hitFile.write('\n')
    hitFile.write('\n')
        
    time.sleep(0.1) # If this is not here strange values appear in array, maybe GLIB isn't ready

hitFile.close()
print sum(eventArray)/len(eventArray)

