#!/usr/bin/python
from classes import *
import sys
import time

class MPACalibration(object):

    # DAC steps in mV
    thrVoltStep = 1.456
    trimVoltStep = 3.75
    
    
    def __init__(self, assembly):

        assembly = self.__wrap(assembly, 1) # Either pass single MPA as integer or array of ints for MAPSA
        self._assembly = sorted(assembly) # Array with MPAs on board (e.g. [2,6] for two MPAs at positions 2 and 6). This is needed because how SPI chain is constructed depends on MPAs present. 
        self._nMPA = len(assembly) # Number of MPAs on the board. This is then also the length of the SPI chain 
        self._iMPA = range(self._nMPA) # This is the SPI-chain

        self._hitArraysMAPSA = None
        self._trimScanHits = None
        self._thrScanMAPSA = None 

        # Connection and GLIB 
        a = uasic(connection="file://connections_test.xml",device="board0")
        self._glib = a._hw 

        # Source all classes
        self._mapsaClasses = MAPSA(a)

        # Get all 6 MPAs and corresponding configs
        self._mpa=[]
        self._conf=[]

        for i in range(0,6):
            self._mpa.append(MPA(self._glib,i+1)) # List of instances of MPA, one for each MPA

        for SPI in self._iMPA: # Config is written via the SPI-chain, therefore only an array with maximum length of chain is necessary
            self._conf.append(self._mpa[SPI].config("data/Default_MPA.xml"))
  
        # Modify config

        self._glib.getNode("Control").getNode("MPA_clock_enable").write(0x1)
        self._glib.dispatch()

        self._glib.getNode("Control").getNode('testbeam_clock').write(0x0) # Enable glib clock
        self._glib.dispatch()

        self._glib.getNode("Configuration").getNode("num_MPA").write(self._nMPA)
        self._glib.dispatch

        # Define default config

        self._prevTrim = 30 # Trimming value with which threshold scan is executed

        defaultPixelCfg = {'PML':1,'ARL':1,'CEL':0,'CW':0,'PMR':1,'ARR':1,'CER':0,'SP':0,'SR':1,'TRIMDACL':self._prevTrim,'TRIMDACR':self._prevTrim}
        defaultPeripheryCfg = {'OM':3,'RT':0,'SCW':0,'SH2':0,'SH1':0,'THDAC':0,'CALDAC':0}

        # Upload (works for all MPAs, even if not all are present. Which ones is not critical as they all get the same config) 
        for SPI in self._iMPA: 
            for key in defaultPeripheryCfg:
                self._conf[SPI].modifyperiphery(key,defaultPeripheryCfg[key])
            for pix in range(0,24):
                for key in defaultPixelCfg:
                    self._conf[SPI].modifypixel(pix + 1,key,defaultPixelCfg[key])

            self._conf[SPI].upload()
        self._glib.getNode("Configuration").getNode("mode").write(self._nMPA - 1)
        self._glib.dispatch()


    def __wrap(self, arg, level): # This function is used to allow supplying single MPAs as arguments in the class methods. ( e.g. 5 instead of [5] to use only MPA5)

        def depth(l): 
            if isinstance(l, list):
                return 1 + max(depth(item) for item in l)
            else:
                return 0

        if level <= depth(arg):
            return arg
        
        if level > depth(arg):
            return(self.__wrap([arg], level))


    def thresholdScan(self, MAPSA=None, shutterDur=0xFFFF, calEnbl=False, calCharge=50, calNum=1000 , resolution=1, conf = None ):
        
        if MAPSA == None:
            MAPSA = self._assembly
        
        MAPSA = self.__wrap(MAPSA,1) 

        self._thrScanMAPSA = MAPSA # self.writeCalibrationToMPAs needs to know to which MPAs to apply the trimDACs.

        if len(MAPSA) > self._nMPA:
            print "Can't do threshold scans on MPAs not declared for this assembly. Please do that when initializing"


        if conf is not None:
            self._conf = conf

        # Write to board whether calibration charge is wanted or not 
        #self._mapsaClasses.daq().Strobe_settings(calNum,0x8F,40,40,cal=int(calEnbl)) # Push number of pulses, delay between shutter open and first pulse, length of pulses, time between pulses, enable calibration (on GLIB) to GLIB (all MPAs)
        self._mapsaClasses.daq().Strobe_settings(calNum,0x8F,40,40,cal=int(calEnbl))
        for SPI in self._iMPA:
            self._conf[SPI].modifyperiphery('CALDAC',calCharge)
            self._conf[SPI].upload()
            for pix in range(0,24): # These are not the real pixel numbers because the middle row (pixel 17 - 32) is not flipped (see MPA-Light manual).
                self._conf[SPI].modifypixel(pix+1, 'CER', int(calEnbl))
                self._conf[SPI].modifypixel(pix+1, 'CEL', int(calEnbl))
            self._conf[SPI].upload()

        self._glib.getNode("Configuration").getNode("mode").write(self._nMPA - 1)
        self._glib.dispatch()
    
        # Arrays containing sub-arrays for each MPA, may contain only one MPA: [MPA1[Thld1[Pix1, Pix2,.., Pix48],Thld2[Pix1,...,Pix48]], MPA2[[],..,[]],...]
        self._eventArrayMAPSA = [] # Total number of recorded events per threshold
        self._bxArrayMAPSA = [] # Number of clock cycles until memory is filled 
        self._hitArrayCounterMAPSA = [] # Hits in ripple counter (asynchronous acquisition, usually more than synchronous)
        self._hitArrayMemoryMAPSA = [] # Hits in memory (synchronous acquisition)
        self._thrArrayMAPSA = [] # Thresholds over which will be scanned


        for MPA in MAPSA: #  MPA are absolute numbers for the actual MPAs on the board
            SPI = self._assembly.index(MPA) # relative numbers, used for SPI chain

            # Arrays to be filled by threshold scan    
            eventArray = []
            bxArray = []
            hitArrayCounter = []
            hitArrayMemory = []
            thrArray = []

            # Start threshold scan
            for thr in range(0,255, resolution): # Only every 'resolution'-steps, reflected in precision of falling edges after trimming

                #time.sleep(0.1)
                
                self._conf[SPI].modifyperiphery('THDAC',thr)
                self._conf[SPI].upload()
                
                self._glib.getNode("Configuration").getNode("mode").write(self._nMPA - 1)
                self._conf[SPI].spi_wait() # includes dispatch
                

                ##########################
                ####### Sequencer ########
                ##########################
                # Opens shutter (mode = 0x0 single shutter, 0x1 four (buffers) consequitive shutter) 
                # Set shutter duration
                # Write in first buffer (default and therefore not necessary to be defined)
                # Readout has to be enabled in order to get the data. Default.
                self._mapsaClasses.daq().Sequencer_init(0, shutterDur )

                counter  = self._glib.getNode("Readout").getNode("Counter").getNode("MPA"+str(SPI + 1)).getNode("buffer_1").readBlock(25) # Place in SPI-Chain is needed for ripple counter but 1-indexed 
                self._glib.dispatch()

                # Readout ripple counter 
                counterArray = []
                for x in range(1,len(counter)): # Skip header at [0]
                        counterArray.append(counter[x] & 0x7FFF) # Mask to select left pixel. First bit is not considered as this seems sometimes to be set erronously. (Lots of entries with 0b1000000000000000)  
                        counterArray.append((counter[x] >> 16) & 0x7FFF) # Mask to select right pixel. Same as above.

                # Readout buffer (TRUE / FALSE : Wait for sequencer) with absolute MPA-values in array index. Parameter 'dcindex' in read_raw() has no function as it only affects ripple counter return
                mem = self._mpa[MPA -1].daq().read_raw(1,1,True)[0]
                

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
                for entry in binMem[:-1]: # Discard last entry in memory as here the 48th - pixel is always set. This is intended as a workaround, the maximum number of hits per pixel and memory is now 95.
                    hd.append(entry[:8])
                    bx.append(entry[8:24])
                    pix.append(entry[24:40]+ "".join(reversed([entry[40:56][i:i+2] for i in range(0, 16, 2)])) + entry[56:]) # Row 2 is numbered from right to left while Rows 1 and 3 are numbered left-to-right. Therefore middle of array must be reversed in blocks of 2 

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
                bxArray.append(bx)
                hitArrayMemory.append(sumPixHits)
                hitArrayCounter.append(counterArray)
                thrArray.append(thr)


            print "---END OF SCAN MPA: %s---" %MPA

            self._eventArrayMAPSA.append(eventArray)
            self._bxArrayMAPSA.append(bxArray)
            self._hitArrayCounterMAPSA.append(hitArrayCounter)
            self._hitArrayMemoryMAPSA.append(hitArrayMemory)
            self._thrArrayMAPSA.append(thrArray)

        self._hitArraysMAPSA = [self._hitArrayCounterMAPSA, self._hitArrayMemoryMAPSA]

        return True

    def getThrScanRawHits(self):
        if self._hitArraysMAPSA == None:
            print "No threshold scan done, nothing to return \n"
        return self._hitArraysMAPSA 

    def getThrScanMetadata(self):
        return self._eventArrayMAPSA, self._bxArrayMAPSA, self._thrArrayMAPSA

    # Returns list of asynchronous and synchronous acquisition (counter, memory), each containing data for all MPAs (6 or less). Example for full assembly: [Counter[MPA1[Threshold1[Pix1,..,Pix48], Threshold2[...]],...,MPA6[]], Memory[MPA1, MPA2, ... , MPA6]]
    def getThrScanPerPix(self):        
        pxlVsThrPixMem = []
        for i,hitArrayMAPSA in enumerate(self._hitArraysMAPSA): # Loop over data from asynchronous and synchronous acquisition
            pxlVsThr = [] 
            for hitArray in hitArrayMAPSA: # Loop over hit arrays for each MPA
               pxlVsThr.append([list(pix) for pix in zip(*hitArray)]) # Transpose sub-array [threshold1[pix1, pix2,...,pix48], threshold2[...], ..., threshold255[...]] to [pix1[threshold1, threshold2, ..., threshold255], pix2[...],...,pix48[...]]
            pxlVsThrPixMem.append(pxlVsThr)
        return pxlVsThrPixMem

                
    def findHalfMaxEdges(self, counter = None): # Supply data from ripple counter in format [Pix1[Thr1, Thr2..], Pix2[..], Pix48[..]] or in format [MPA1[Pix1[Thr1, Thr2,...], Pix2[...],...], MPA2[...],...]
        if counter == None: 
            counter, _ = self.getThrScanPerPix() # Returns data from ripple counter and from memory but memory is not needed for finding edges

        counter = self.__wrap(counter,3)  # Wrap counter in list to allow iterating over it once

        edgesMAPSA = []
        for i,pxlVsThrCounter in enumerate(counter): # Loop over MAPSA (single MPAs)
            risingEdges = [] 
            fallingEdges = []
            for pxlNum,pxl in enumerate(pxlVsThrCounter):
                pxlMax = max(pxl)
                thresholdValueAndPxl = zip(self._thrArrayMAPSA[i],pxl) # Match thresholds to amount of hits and create list of tuples

                maxBin = len(pxl) - pxl[::-1].index(pxlMax) - 1 # Find highest threshold with maximum number of hits, right before falling edge
                halfMax = pxlMax/2 # Half maximum, either on rising or on falling edge 

                pxlLeftOfPeak  = thresholdValueAndPxl[:maxBin + 1] # Get rid of falling edge which has higher thresholds than maxBin
                pxlRightOfPeak = thresholdValueAndPxl[maxBin:] # Get rid of rising edge which has lower thresholds than maxBin 
                
                for thrIdx,threshold in enumerate(pxlLeftOfPeak): # Find first threshold with more hits than middle of rising edge, then get the one left of that. 
                    if threshold[1] > halfMax: 
                        risingEdges.append(pxlLeftOfPeak[thrIdx-1][0])
                        break # Only one threshold is needed, leave loop
                else: #nobreak
                    print "Something went wrong for pixel %s, not possible to find rising edge" %pxlNum
                    print pxl
                    risingEdges.append(None)

                for threshold in pxlRightOfPeak: # Find first threshold with less hits than middle of falling edge, then break
                    if threshold[1] < halfMax: 
                        fallingEdges.append(threshold[0])
                        break # Only one threshold is needed, leave loop
                else: # nobreak, break condition has never been met as graph keeps rising constantly
                    print "Graph for Pixel %s has no falling edge, appending '254' as dummy value" %pxlNum 
                    fallingEdges.append(254)
            edgesMAPSA.append(zip(risingEdges, fallingEdges))
        return edgesMAPSA

    def findFallingEdges(self, counter = None):
        edgesMAPSA = self.findHalfMaxEdges(counter)

        fallingEdgesMAPSA = []
        for edges in edgesMAPSA:
           fallingEdgesMAPSA.append(list(zip(*edges)[1])) # Undo the zip in findHalfMaxEdges() as we only need the falling edges.

        return fallingEdgesMAPSA



    def getTrimBits(self, fallingEdgesMAPSA = None, trimThresholdMAPSA = None, minimize = True, ratioThrTrim = None ) : 
        if fallingEdgesMAPSA == None: # By default get falling edges from last threshold scan 
            fallingEdgesMAPSA = self.findFallingEdges()
            print "Getting falling edges from last threshold scan"

        
        if trimThresholdMAPSA == None: # Allow forcing a threshold on which to trim.
            trimThresholdMAPSA = [min(fallingEdges) for fallingEdges in fallingEdgesMAPSA]
        else:
            minimize = False # When using minimizing it's not possible to guarantee a threshold on which is trimmed as all trimDACs are set as low as possible. Therefore disable minimizing when using explicit trimThreshold.

        fallingEdgesMAPSA = self.__wrap(fallingEdgesMAPSA, 2)
        trimThresholdMAPSA = self.__wrap(trimThresholdMAPSA, 1)

        if ratioThrTrim is None: # As default, trim every pixel using the same ratio from the MPA manual
            ratioThrTrim = self.thrVoltStep/self.trimVoltStep

        if isinstance(ratioThrTrim, int) or isinstance(ratioThrTrim, float): # If passed value is an int or a float the ratio is applied to all pixels and mpas
            ratioThrTrim = [[ratioThrTrim] * len(fallingEdgesMAPSA[0])]*len(fallingEdgesMAPSA)


        if len(trimThresholdMAPSA) != len(fallingEdgesMAPSA):
            print "Number of supplied thresholds doesn't match number of given falling edges (%s thresholds and %s falling edges)." %(len(trimThresholdMAPSA), len(fallingEdgesMAPSA))


        trimDACMAPSA = []
        for nMPA,fallingEdges in enumerate(fallingEdgesMAPSA):
            trimDACToTheLeft = [(edge - trimThresholdMAPSA[nMPA]) * ratioThrTrim[nMPA][pxl] for pxl, edge in enumerate(fallingEdges)]

            trimDAC = [max(0, (self._prevTrim - int(round(pxlTrimDac)))) for pxlTrimDac in trimDACToTheLeft]  # Normalize trimDAC and take into account that we started with trimDAC set to some value 'self._prevTrim' (default 30) 

            if minimize:
                trimDAC = [pix - min(trimDAC) for pix in trimDAC] # Set all trimDAC as low as possible
            trimDACMAPSA.append(trimDAC)

        return trimDACMAPSA
        

    def writeCalibrationToMPA(self,  MAPSA = None, trimDAC = None, debug = False):    # Write trimDAC values to MPA
        # Default: Write calibration values to all MPAs given in initialization and use trimDACs derived from threshold scan
        if trimDAC == None:
            trimDAC = self.getTrimBits() 
            print "Getting trim bits from last threshold scan"
            if MAPSA == None:
                MAPSA = self._thrScanMAPSA # If neither trimDAC nor MAPSA are supplied get them from the last threshold scan 
        else:   # If trimDAC but no MAPSA is supplied use full assembly
            if MAPSA == None:
                MAPSA = self._assembly

        # Allow supplying only data for one MPA without unnecessary nested lists 
        MAPSA = self.__wrap(MAPSA,1)
        trimDAC = self.__wrap(trimDAC, 2)

        if len(MAPSA) != len(trimDAC):
            print "Error: Number of trimDACs doesn't match number of MPAs" 
        iMPA = []
        for MPA in MAPSA:
            iMPA.append(self._assembly.index(MPA)) # construct SPI chain 
        for i,MPA in enumerate(iMPA):
            for pix in range(0,24):
                self._conf[MPA].modifypixel(pix + 1,'TRIMDACL',trimDAC[i][2*pix])
                self._conf[MPA].modifypixel(pix + 1,'TRIMDACR',trimDAC[i][2*pix + 1])

            self._conf[MPA].upload()
            self._glib.getNode("Configuration").getNode("mode").write(self._nMPA - 1)
            self._conf[MPA].spi_wait() # includes dispatch


        # Debug mode, verify written TrimDACs
        if debug == True:
            readconfMAPSA = []
            for iMPA, _ in enumerate(MAPSA):
                    readconf = []

                    # Write twice to push config to Memory_OutConf to check what has been written 
                    self._glib.getNode("Configuration").getNode("mode").write(self._nMPA - 1)
                    self._conf[iMPA].spi_wait()
                    self._glib.getNode("Configuration").getNode("mode").write(self._nMPA - 1)
                    self._conf[iMPA].spi_wait()
                    outConf = self._glib.getNode("Configuration").getNode("Memory_OutConf").getNode("MPA"+str(iMPA + 1)).getNode("config_1").readBlock(0x19) # Get written config
                    self._glib.dispatch()
                    for pix in outConf: # Format this config to extract trimDac values
                        readconf.append((pix >> 2) & 0b11111)
                        readconf.append((pix >> 12) & 0b11111)
                    readconfMAPSA.append(readconf[2:]) # Drop header, append one config for each MPA

            return trimDAC, readconfMAPSA
        else:
            return True


    def trimScan(self, MAPSA = None, resolution = 1):

        if MAPSA == None:
            MAPSA = self._assembly
        MAPSA = self.__wrap(MAPSA, 1)

        self._trimScanHits = [] 
        self._trimScanTrimDACs = []
        for trimDAC in range(0,32, resolution):
            print "Setting all trimDACs to %s" %trimDAC
            self.writeCalibrationToMPA(MAPSA, [[trimDAC]*48]*len(MAPSA)) # Write same trimDAC to all pixels and to number of MPAs specified in MAPSA
            self.thresholdScan(MAPSA, calEnbl = True)
            counter, _ = self.getThrScanPerPix()
            self._trimScanHits.append(counter)
            self._trimScanTrimDACs.append(trimDAC)
        return True
            
    def getTrimScanHits(self):
        
        MAPSAtrimScan =  [list(mpa) for mpa in zip(*self._trimScanHits)] # MPA[Trim[ThrScanPerPix]] (swap highest and second-highest order of nesting)
        return MAPSAtrimScan 

    def getTrimScanEdges(self):
        trimScanEdges = []
        for trim in self._trimScanHits:
           trimScanEdges.append(self.findFallingEdges(trim)) 
        MAPSAtrimScanEdges = [list(mpa) for mpa in zip(*trimScanEdges)] # MPA[Trim[Pix]]
        return MAPSAtrimScanEdges 

    def getTrimScanMetadata(self):
        return self._trimScanTrimDACs

    def voltTest(self, MAPSA = None):

        if MAPSA == None:
            MAPSA = self._assembly


        MAPSA = self.__wrap(MAPSA, 1)
        self.thresholdScan(MAPSA) 
        edgesMAPSA = self.findHalfMaxEdges()
        fwhmMAPSA = []
        for edges in edgesMAPSA:
            fwhm = [pix[1] - pix[0] for pix in edges] # Loop over edge-tuples for each pixel and subtract rising edges from falling edge. This is the full width at half maximum.
            fwhmMAPSA.append(fwhm)
        
        return fwhmMAPSA


    def automaticBondTest(self, MAPSA = None, resolution = 5, voltMin = 5):

        if MAPSA == None:
            MAPSA = self._assembly

        try:
            from KeithleyControl.keithleyControl import keithley
        except ImportError:
            print "No automatic bond test without power supply with RS232"
            return False # Can't do automatic bond test without variable bias voltage. 

        MAPSA = self.__wrap(MAPSA, 1) 

        voltSource = keithley()
        voltSource.init()

        self._counterArray = []
        self._edgesVoltScan = []
        self._voltArray = []


        for voltStep in range(voltMin, 111, resolution): # Loop over bias voltage in steps of 'resolution'. Start with 5V to avoid strange behaviour of sensor. 

            self._voltArray.append(voltStep)
            voltSource.setVoltage(voltStep)
            
            self.thresholdScan(MAPSA)
           
            self._counterArray.append(self.getThrScanPerPix()[0]) 
            self._edgesVoltScan.append(self.findHalfMaxEdges())

            print voltSource.readVoltage()
        voltSource.close()

        return True 
    
    def bondTestGetThrScanPerVolt(self):
        
        return self._counterArray 
        

    def bondTestGetFwhmPerVolt(self):

        fwhmMAPSAVolt = [] # Volt[MPA[Pix]]

        for edgesMAPSA in self._edgesVoltScan:
            fwhmVolt = []
            for edges in edgesMAPSA:
                fwhm = [pix[1] - pix[0] for pix in edges] # Loop over edge-tuples for each pixel and subtract rising edges from falling edge. This is the full width at half maximum.
                fwhmVolt.append(fwhm)
            fwhmMAPSAVolt.append(fwhmVolt)

        MAPSAVoltFWHM =  [list(volt) for volt in zip(*fwhmMAPSAVolt)] # MPA[Volt[Pix]] (swap highest and second-highest order of nesting)

        MAPSAFWHMVolt = [] 
        for MPA in MAPSAVoltFWHM: # MPA[Pix[Volt]] (swap third-highest and second-highest order of nesting)
           MAPSAFWHMVolt.append([list(pix) for pix in zip(*MPA)]) 

        return self._voltArray, MAPSAFWHMVolt

    def bondTestGetDiff(self):

        _, MAPSAFWHMVolt = self.bondTestGetFwhmPerVolt()


        fwhmDiffMAPSA = []
        for MPA in MAPSAFWHMVolt:
            fwhmDiff = []
            for pix in MPA:
                fwhmDiff.append(sum(sorted(pix)[-2:])/2 - sum(sorted(pix)[:2])/2) # Average two highest and two lowest fwhms
            fwhmDiffMAPSA.append(fwhmDiff)
        
        return fwhmDiffMAPSA 

             
if __name__ == "__main__":

    from MPAPlot import MPAPlot
    plot = MPAPlot()
    assembly = [2,5]
    nMPA = 2

    calibration = MPACalibration(assembly)
    calibration.thresholdScan(None, calEnbl = False, shutterDur=0xFFFF, calCharge = 100, calNum = 10000)
    
    
    counter, mem = calibration.getThrScanPerPix()
    _,_,threshold = calibration.getThrScanMetadata()
    for pix in counter[0]:
        plot.createGraph(threshold[0], pix)
    plot.draw()
    plot.clear()
    trimDac = calibration.getTrimBits()
    print trimDac
    calibration.writeCalibrationToMPA(None, trimDAC = trimDac)

    calibration.thresholdScan(None)
    counter, mem = calibration.getThrScanPerPix()
    _,_,threshold = calibration.getThrScanMetadata()
    for pix in counter[0]:
        plot.createGraph(threshold[0], pix)
    plot.draw()
