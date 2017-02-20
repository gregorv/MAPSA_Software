import sys
from classes import *
from array import array
from ROOT import TGraph, TCanvas, TLine, TTree, TFile
import time

assembly = [2,5]

bufferEnabled = 4 

# Connection and GLIB 
a = uasic(connection="file://connections_test.xml",device="board0")
glib = a._hw 

glib.getNode("Control").getNode("logic_reset").write(0x1)
glib.dispatch()

# Source all classes
mapsaClasses = MAPSA(a)

conf = []
mpa = []
for iMPA, nMPA  in enumerate(assembly):
    mpa.append(MPA(glib, iMPA+1)) # List of instances of MPA, one for each MPA. SPI-chain numbering!
#    conf.append(mpa[iMPA].config("data/Conf_trimcalib_MPA" + str(nMPA)+ "_config1.xml")) # Use trimcalibrated config
    conf.append(mpa[iMPA].config("data/Conf_default_MPA" + str(nMPA)+ "_config1.xml"))



# Enable clock on MPA
glib.getNode("Control").getNode("MPA_clock_enable").write(0x1)
glib.dispatch()

threshold = 70 

# Define default config
for iMPA in range(0,len(assembly)):
    conf[iMPA].modifyperiphery('THDAC',threshold) # Write threshold to MPA 'iMPA'
    conf[iMPA].modifypixel(range(1,25), 'SR', 1)
    conf[iMPA].upload()
glib.getNode("Configuration").getNode("mode").write(len(assembly) - 1)
conf[iMPA].spi_wait() # includes dispatch

glib.getNode("Configuration").getNode("num_MPA").write(len(assembly))
glib.getNode("Configuration").getNode("mode").write(len(assembly) - 1) # This is a 'write' and pushes the configuration to the glib. Write must happen before starting the sequencer.
conf[0].spi_wait() # includes dispatch
glib.getNode("Control").getNode('testbeam_clock').write(0x1) # Enable external clock 
glib.getNode("Configuration").getNode("mode").write(len(assembly) - 1)
glib.dispatch()
#glib.getNode("Control").getNode("Sequencer").getNode("buffers_index").write(bufferEnabled - 1)
#glib.getNode("Configuration").getNode("mode").write(len(assembly) - 1)
#glib.getNode("Custom").getNode("tel_busy_enable").write(0x1)
glib.dispatch()

shutterDur =  0xFFFFFFF #0xFFFFFFFF is maximum, in clock cycles
mapsaClasses.daq().Sequencer_init(0x1,shutterDur, mem=1, ibuff = 3) # Start sequencer in continous daq mode. Already contains the 'write'

ibuffer = 1
shutterCounter = 0
counterArray = []
memoryArray = []
try:
    while True:
        
        freeBuffers = glib.getNode("Control").getNode('Sequencer').getNode('buffers_num').read()
        glib.dispatch()
        if freeBuffers < 3: # Only read buffers if at least two are full. If set to 4 duplicate entries appear.	
            MAPSACounter = []
            MAPSAMemory = []
            for iMPA, nMPA in enumerate(assembly):
                counterData  = glib.getNode("Readout").getNode("Counter").getNode("MPA"+str(iMPA + 1)).getNode("buffer_"+str(ibuffer)).readBlock(25)
                memoryData = glib.getNode("Readout").getNode("Memory").getNode("MPA"+str(nMPA)).getNode("buffer_"+str(ibuffer)).readBlock(216)
                glib.dispatch()

                print "Buffer: %s iMPA: %s nMPA: %s" %(ibuffer, iMPA, nMPA)
                print counterData
                #print '{0:032b}'.format(counterData[0])
                #print memoryData
                #print "\n"

                MAPSACounter.append(counterData.value())
                MAPSAMemory.append(memoryData.value())

            ibuffer += 1
            if ibuffer > 4:
                ibuffer = 1

            shutterCounter+=1
            
            # Only contains valVectors:
            counterArray.append(MAPSACounter) 
            memoryArray.append(MAPSAMemory)
            print "Shutter counter: %s Free buffers: %s " %(shutterCounter, freeBuffers)

            if shutterCounter > 1:
                break
        
except KeyboardInterrupt:
    pass

finally:
    print "Turning off continous datataking"
    glib.getNode("Control").getNode('Sequencer').getNode('datataking_continuous').write(0)
    glib.dispatch()
    #glib.getNode("Configuration").getNode("mode").write(len(assembly) - 1) # This is a 'write' and pushes the configuration to the glib. Write must happen before starting the sequencer.
    #conf[0].spi_wait() # includes dispatch

    for endBuffer in range(0,2): # Read remaining two buffer
        freeBuffers = glib.getNode("Control").getNode('Sequencer').getNode('buffers_num').read()
        glib.dispatch()
        MAPSACounter = []
        MAPSAMemory = []
        for iMPA, nMPA in enumerate(assembly):
            counterData  = glib.getNode("Readout").getNode("Counter").getNode("MPA"+str(iMPA + 1)).getNode("buffer_"+str(ibuffer)).readBlock(25)
            memoryData = glib.getNode("Readout").getNode("Memory").getNode("MPA"+str(nMPA)).getNode("buffer_"+str(ibuffer)).readBlock(216)
            glib.dispatch()
            
            print "Buffer: %s iMPA: %s nMPA: %s" %(ibuffer, iMPA, nMPA)
            print counterData
            #print memoryData
            
            MAPSACounter.append(counterData.value())
            MAPSAMemory.append(memoryData.value())

        shutterCounter += 1        
        ibuffer += 1
        if ibuffer > 4:
            ibuffer = 1

        # Only contains valVectors:
        counterArray.append(MAPSACounter) 
        memoryArray.append(MAPSAMemory)
        print "Shutter counter: %s Buffers num: %s " %(shutterCounter, freeBuffers)

freeBuffers = glib.getNode("Control").getNode('Sequencer').getNode('buffers_num').read()
lastBuffer = glib.getNode("Control").getNode('Sequencer').getNode('buffers_index').read()
glib.dispatch()
print freeBuffers
print lastBuffer + 1
print len(counterArray)

            
nHitMax = 95
nPixMax = 48
nMPA = 2

###############

counter = 0

buffTest = counterArray[:4]
cycleIndex = 0 

for k in range(len(counterArray)/4):
    for i, buff in enumerate(buffTest):
        if cycleIndex == k:
            continue
        if buff == counterArray[k*4+i]: 
            print "Error, buffer %s from cycle %s and cycle %s are the same" %(i, cycleIndex, k)
            print counterArray[k*4+i]
        else:
            buff = counterArray[k*4+i]
            cycleIndex = k

