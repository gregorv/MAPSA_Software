import sys
import numpy as np
from classes import *
from array import array
from optparse import OptionParser
from ROOT import TGraph, TCanvas, TLine, TTree, TFile
from MPACalibration import MPACalibration

assembly = [2,5]

# Connection and GLIB 
a = uasic(connection="file://connections_test.xml",device="board0")
glib = a._hw 

# Source all classes
mapsaClasses = MAPSA(a)

conf = []
mpa = []
for iMPA, nMPA  in enumerate(assembly):
    mpa.append(MPA(glib, nMPA)) # List of instances of MPA, one for each MPA
    conf.append(mpa[iMPA].config("data/Conf_trimcalib_MPA" + str(nMPA)+ "_config1.xml")) # Use trimcalibrated config

threshold = 120

# Define default config
for iMPA in range(len(assembly)):
    conf[iMPA].modifyperiphery('THDAC',threshold) # Write threshold to MPA 'iMPA'
    conf[iMPA].upload()
    glib.getNode("Configuration").getNode("mode").write(nMPA - 1)
    conf[iMPA].spi_wait() # includes dispatch


glib.getNode("Control").getNode('testbeam_clock').write(0x1) # Enable external clock 
glib.dispatch()


shutterDur = 0xFFFFFFFF #0xFFFFFFFF is maximum, in clock cycles
mapsaClasses.daq().Sequencer_init(0x1,shutterDur, mem=1) # Start sequencer in continous daq mode

ibuffer = 1
shutterCounter = 0 
counterArray = []
memoryArray = []
try:
    while True:
       
        freeBuffers = glib.getNode("Control").getNode('Sequencer').getNode('buffers_num').read()
        glib.dispatch()
        if freeBuffers < 4:	
            MAPSACounter = []
            MAPSAMemory = []
            for iMPA, MPA in enumerate(assembly):
		counterData  = glib.getNode("Readout").getNode("Counter").getNode("MPA"+str(MPA)).getNode("buffer_"+str(ibuffer)).readBlock(25)
		memoryData = glib.getNode("Readout").getNode("Memory").getNode("MPA"+str(MPA)).getNode("buffer_"+str(ibuffer)).readBlock(216)

                MAPSACounter.append(counterData)
                MAPSAMemory.append(memoryData)
            glib.dispatch()
                
            shutterCounter += 1
            ibuffer += 1
            if ibuffer > 4:
                ibuffer = 1

            # Only contains valVectors:
            counterArray.append(MAPSACounter) 
            memoryArray.append(MAPSAMemory)
            print "Shutter counter: %s Buffers num: %s " %(shutterCounter, freeBuffers)

        # if shutterCounter > 1:
        #     print shutterCounter
        #     break
except KeyboardInterrupt:
    
    print len(counterArray)
    print len(memoryArray)

    ttree = TTree("Events","MPA event tree")
    
    eventArray = np.array([0])
    bxArray = np.array([0])
    hitArrayMemory = np.array([0])
    hitArrayCounter = np.array([0])
    iMPA = np.array([0])
    headerArray = np.array([0])
    nHits = np.array([0])

    ttree.Branch("header", headerArray, "header/I")
    ttree.Branch("bx", bxArray, "bx/I")
    ttree.Branch("pixelHits", hitArrayMemory, "pixelHits/I")
    ttree.Branch("mpa", impa, "mpa/I")
    ttree.Branch("nHits", nHits, "nHits/I")
    
    for event in memoryArray:
        for i,mpa in enumerate(event):

            iMPA[0] = assembly[i]
            
            # Mem integer array to binary string in readable order (header,bx,pix) 
            binMemStr= ""
            for i in range(0,216):
                binMemStr = binMemStr + '{0:032b}'.format(mem[215-i])

            # String to binary array
            binMem = [binMemStr[x:x+72] for x in range(0,len(binMemStr),72)]

            # Get elements of binary string
            hd = np.array()
            bx = np.array()
            pix = np.array()
                
            for entry in binMem[:-1]: # Discard last entry in memory as here the 48th - pixel is always showing a hit, even if pixel is disabled. This is intended as a workaround, the maximum number of hits per pixel and memory is now 95.
                hd.append(entry[:8])
                bx.append(entry[8:24])
                pix.append(entry[24:])

            headerArray[0]=[int(ihd,2) for ihd in hd]
            bxArray[0]=[int(ibx,2) for ibx in bx]
                
        i+=1
    
    #memoryArrayMAPSA = [list(mpa) for mpa in zip(*memoryArray)] # Switch hierarchy so that Shutter[MPA[Mem]] becomes MPA[Shutter[Mem]]

    #for mpa in memoryArrayMAPSA:
    #    for run in mpa:
    #        hitArrayShutter = []
    #        for mem in run:
    #            ## Mem integer array to binary string in readable order (header,bx,pix) 
    #            binMemStr= ""
    #            for i in range(0,216):
    #                binMemStr = binMemStr + '{0:032b}'.format(mem[215-i])

    #            # String to binary array
    #            binMem = [binMemStr[x:x+72] for x in range(0,len(binMemStr),72)]

    #            # Get elements of binary string
    #            hd = []
    #            bx = []
    #            pix = []
    #            
    #            for entry in binMem[:-1]: # Discard last entry in memory as here the 48th - pixel is always showing a hit, even if pixel is disabled. This is intended as a workaround, the maximum number of hits per pixel and memory is now 95.
    #                hd.append(entry[:8])
    #                bx.append(entry[8:24])
    #                pix.append(entry[24:])

    #            # Put event string into lists, one entry per pixel 
    #            hitArrayShutter = []
    #            for event in hits:
    #                hitArrayEvent = [] 
    #                for pix in event:
    #                    hitArrayEvent.append(int(pix))
    #                hitArrayShutter.append(hitArrayEvent)

    #            # Count number of Events
    #            nHitss = 0
    #            for hit in hd:
    #                if hit == "11111111":
    #                    nHits+=1

    #            # bunch crossing from binary to int
    #            bx=[int(ibx,2) for ibx in bx]

    #            hitNumberArray.append(nHits)        
    #            bxArray.append(bx)
    #            hitArrayMemory.append(hitArrayShutter)
    #    

    #for mpa in counterArray:
    #    for counter in mpa:

    #        pix.append(entry[24:40]+ "".join(reversed([entry[40:56][i:i+2] for i in range(0, 16, 2)])) + entry[56:]) # Row 2 is numbered from right to left while Rows 1 and 3 are numbered left-to-right. Therefore middle of array must be reversed in blocks of 2 

