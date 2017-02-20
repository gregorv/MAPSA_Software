import sys
import time
from array import array
from MPACalibration import MPACalibration
from MPAPlot import MPAPlot

#iMPA = 1 # Only do this for MPA 5, the 2nd MPA in the SPI-chain (0-indexed)
#MPANum = 4 # 0-indexed absolute number of MPA 5 

hitFile = open('data/synchronous_data_xray', 'a')

# Calibrate MPA (only use MPA 5 as it has confirmed failed bonds)
calibration = MPACalibration([2,5]) # Argument reflects assembly which is actually on board 
calibration.thresholdScan(calEnbl = 1) 
calibration.writeCalibrationToMPA()

# Take connection, GLIB and MPA from calibration 
glib = calibration._glib 
mapsaClasses = calibration._mapsaClasses

mpa = calibration._mpa 
conf = calibration._conf 

# Define default config
calibration.thresholdScan()

counter, _ = calibration.getThrScanPerPix()
_,_,thresholds = calibration.getThrScanMetadata()

for iMPA in range(0,2):
    plot = MPAPlot()
    for pix in counter[iMPA]:
        plot.createGraph(thresholds[iMPA], pix)
    #plot.draw()

    #threshold = input("Which global threshold should be set?")
    threshold = 150
    calibration._conf[iMPA].modifyperiphery('THDAC',threshold) # Write threshold to MPA 'iMPA'
    calibration._conf[iMPA].upload()
    calibration._glib.getNode("Configuration").getNode("mode").write(calibration._nMPA - 1)
    calibration._conf[iMPA].spi_wait() # includes dispatch

shutterDur = 0xFFFFF  #0xFFFFFFFF is maximum, in clock cycles

eventArray = []
bxArray = []

raw_input("SHUTTER!!???")
hitArrayCounter = []
for i in range(0,100):
    ##########################
    ### Begin of sequencer ###
    ##########################
    
    mapsaClasses.daq().Sequencer_init(0, shutterDur)
    mpaArrayCounter = []
    for iMPA in range(0,2): 

        counter  = glib.getNode("Readout").getNode("Counter").getNode("MPA"+str(iMPA + 1)).getNode("buffer_1").readBlock(25) 
        glib.dispatch()
        
        counterArray = []
        for x in range(1,len(counter)): # Skip header at [0]
                counterArray.append(counter[x] & 0x7FFF) # Mask to select left pixel 
                counterArray.append((counter[x] >> 16) & 0x7FFF) # Mask to select right pixel
        mpaArrayCounter.append(counterArray)

    hitArrayCounter.append(mpaArrayCounter)
    time.sleep(0.1)

mpaRunPix =  [list(run) for run in zip(*hitArrayCounter)] # MPA[Run[Pix]] (swap highest and second-highest order of nesting)

mpaSumRun = []
for mpa in mpaRunPix:
    sumRun = [0]*48
    for run in mpa:
        for i,pix in enumerate(run):
            sumRun[i] += pix
    mpaSumRun.append(sumRun)

mpaTotal = []
for mpa in mpaSumRun:
    mpaTotal.append(sum(mpa))
    plot = MPAPlot()
    plot.createHitMap(mpa)
    plot.draw()

shutterDurInSeconds = shutterDur*len(hitArrayCounter) * 1/(160e6) # For frequency of hits

frequency = sum(mpaTotal)/shutterDurInSeconds
print "Total number of hits: %s" %sum(mpaTotal)
#print "Hits for each pixel, summed over %s readout cycles: %s \n" %(len(hitArrayCounter), sumPixArray)
print "Total readout time: %s seconds \n" %shutterDurInSeconds
print "Frequency of hits: %s" %(sum(mpaTotal)/shutterDurInSeconds) 

hitFile.write(str(frequency)+'\n')
hitFile.close()
