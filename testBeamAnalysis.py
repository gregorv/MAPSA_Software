import os
import sys
import ast
import numpy as np

class TBAnalysis(object):

    def __init__(self):
        pass


    def counterDecode(self, counterArray):

        counterData = []

        for pix in counterArray[1:]: # Skip header at [0]
            counterData.append(pix & 0x7FFF) # Mask to select left pixel. First bit is not considered as this seems sometimes to be set erronously. (Lots of entries with 0b1000000000000000) 
            counterData.append((pix >> 16) & 0x7FFF) # Mask to select right pixel. Same as above.

        return counterData
        

    def memoryDecode(self, memoryArray, zeroSup = True):

        binMemStr= ""
        for j in range(0,216):
            binMemStr = binMemStr + '{0:032b}'.format(memoryArray[215-j])

        # String to binary array
        binMem = [binMemStr[x:x+72] for x in range(0,len(binMemStr),72)]

        if zeroSup:
            binMem = self.memoryZeroSuppress(binMem)

        return binMem

    def memoryZeroSuppress(self, event):
        
        noZeroEvent = [entry for entry in event if int(entry) > 0]

        return noZeroEvent
        
    def memoryContent(self, memoryData):


        hd = []
        bx = []
        pix = []

        for entry in memoryData[:-1]: # Discard last entry in memory as here the 48th - pixel is always showing a hit, even if pixel is disabled. This is intended as a workaround, the maximum number of hits per pixel and memory is now 95.
            hd.append(entry[:8])
            bx.append(entry[8:24])
            pix.append(entry[24:])

        return {'header':hd, 'bx':bx, 'hits':pix}

    
    def parseFile(self, fileName):

        data = []
        
        with open(fileName, 'r') as iFile:
            for line in iFile:
                data.append(ast.literal_eval(line))
                
        return data


    def getData(self, dataArray, nMPA = 2):

        data = [[] for i in range(0,nMPA)]
        
        if len(dataArray[0]) == 25: # unprocessed counter array
            for i, entry in enumerate(dataArray):
                data[i%nMPA].append(self.counterDecode(entry))
                if i%1000 == 0:
                    print "Decoding event %s" %(i/2)
        elif len(dataArray[0]) == 216: # unprocessed memory array
            for i, entry in enumerate(dataArray):
                data[i%nMPA].append(self.memoryDecode(entry))
                if i%1000 == 0:
                    print "Decoding event %s" %(i/2)
        else:
            sys.exit("Wrong data format")
            
        return data


    def loadFile(self, fileName):

        rawData = self.parseFile(fileName)
        data = self.getData(rawData)

        return data


    def saveDecoded(self, fileName, outPath="decoded"):
        
        data = self.loadFile(fileName)

        if not os.path.exists(os.path.dirname(fileName)+"/"+outPath):
            os.makedirs(os.path.dirname(fileName)+"/"+outPath)

        for i,mpa in enumerate(data):
            with open("%s/%s/%s_%s" %(os.path.dirname(fileName), outPath, os.path.basename(fileName), i),'w+') as outFile:
                for line in mpa:
                    outFile.write(str(line)+'\n')

        return True
        
        
    def convertFormat(self, dutRaw, axis = "X"):
       
        dutArray = []
 
        for eventNum in range(len(dutRaw)):
            
            dutEvent = []

            for pixNum,pix in enumerate(dutRaw[eventNum]):
                if pix > 0: 
                    if axis == "X": 
                        if pixNum > 15 and pixNum < 32:
                            for i in range(pix):
                                dutEvent.append(31 - pixNum)
                        else:
                            for i in range(pix):
                                dutEvent.append(pixNum%16)

                    elif axis == "Y": 
                        for i in range(pix):
                            dutEvent.append(pixNum/16)

                    else:
                        sys.exit("This axis doesn't exist")

            dutArray.append(dutEvent)

        return dutArray



if __name__ == "__main__":

    from MPAPlot import MPAPlot

    tb = TBAnalysis()
    
    #if len(sys.argv) == 2:
    #    data = tb.loadFile(sys.argv[1])
    #else:
    #    sys.exit("No input file specified")

    #if sys.argv[1].split("/")[0] == "decoded":
    #    pass
    #else:
    #    tb.saveDecoded(sys.argv[1])

    try:
        if not sys.stdin.isatty():
            for line in sys.stdin:
                tb.saveDecoded(line)
        elif len(sys.argv) > 1:
            for line in sys.argv[1:]:
                tb.saveDecoded(line)
                print "Decoded file %s" %line
        else:
            print "Need a file to decode"
    except:
        sys.exit("Raw file not found")
        
    #if len(sys.argv) == 2:
    #    data = tb.loadFile(sys.argv[1])
    #
    #    runHits = []
    #    
    #    for mpa in data:
    #        runHits.append(np.sum(mpa,0))

    #    for mpa in runHits:
    #        plt = MPAPlot()
    #        plt.createHitMap(mpa)
    #        plt.draw() 

    #refArray = tb.parseFile(sys.argv[2])
    #
    #dutRaw = tb.parseFile(sys.argv[1])

    #dutArray = tb.convertFormat(dutRaw) 

    #plot = MPAPlot()

    #plot.createCorrelationPlot(dutArray, refArray, "X" , -1)

    #plot.draw()

