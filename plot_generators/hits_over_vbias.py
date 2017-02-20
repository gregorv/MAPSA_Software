from MPACalibration import MPACalibration
import xml.etree.ElementTree as ET
from MPAPlot import MPAPlot
from KeithleyControl.keithleyControl import keithley
import time

shutterDur = 0x1FFFFF
resolution = 10
assembly = [2,5]
calibration = MPACalibration(assembly)
voltSource = keithley()
voltSource.init()
voltSource.setVoltage(110)

mpaConfig = []  
conf = calibration._conf 
mapsaClasses = calibration._mapsaClasses
glib = calibration._glib

for MPA in assembly:
    mpaConfig.append(ET.parse("data/Conf_trimcalib_MPA"+str(MPA)+"_config1.xml")) # Construct list of roots of XML files, one for each MPA

trimDACMAPSA = []
for MPAtree in mpaConfig:
    MPA = MPAtree.getroot()
    trimDAC = []
    for pixel in MPA.findall('pixel'):
        trimDAC.append(int(pixel.find('TRIMDACL').text))
        trimDAC.append(int(pixel.find('TRIMDACR').text))
    trimDACMAPSA.append(trimDAC)
calibration.writeCalibrationToMPA(trimDAC = trimDACMAPSA) 

#calibration.thresholdScan()
#counterThrScan,  _ = calibration.getThrScanPerPix()
#_,_,thresholds = calibration.getThrScanMetadata()
#counterRaw, _  = calibration.getThrScanRawHits()

#globalThreshold = []
#for iMPA, MPA in enumerate(counterThrScan):
#    maxPix = []
#    plot = MPAPlot()
#    for pix in MPA:
#        plot.createGraph(thresholds[iMPA], pix)
#        maxPix.append(pix.index(max(pix)))
#    plot.setRange(yRange = [0, max([max(pix) for pix in MPA])]) 
#    plot.draw()
#    print sum(maxPix)/len(maxPix) 
#    globalThreshold.append(int(raw_input("Which global threshold should be set? \n")))

globalThreshold = [150,150]
for iMPA, MPA in enumerate(assembly):
    conf[iMPA].modifyperiphery('THDAC',globalThreshold[iMPA]) # Write threshold to MPA 'iMPA'
    conf[iMPA].upload()
    glib.getNode("Configuration").getNode("mode").write(len(assembly) - 1)
    conf[iMPA].spi_wait() # includes dispatch

#for iMPA, MPA in enumerate(counterRaw):
#    print MPA[globalThreshold[iMPA]]


calibration.writeCalibrationToMPA(trimDAC = trimDACMAPSA) 

hitArrayVolt = []
voltArray = []

for voltStep in range(0, 111, resolution):

    voltSource.setVoltage(voltStep)
    voltArray.append(voltStep)
    
    mapsaClasses.daq().Sequencer_init(0, shutterDur)
    mpaArrayCounter = []
    for iMPA, _ in enumerate(assembly): 

        counter  = glib.getNode("Readout").getNode("Counter").getNode("MPA"+str(iMPA + 1)).getNode("buffer_1").readBlock(25) 
        glib.dispatch()
        
        counterArray = []
        for x in range(1,len(counter)): # Skip header at [0]
                counterArray.append(counter[x] & 0x7FFF) # Mask to select left pixel 
                counterArray.append((counter[x] >> 16) & 0x7FFF) # Mask to select right pixel
        mpaArrayCounter.append(counterArray)

    hitArrayVolt.append(mpaArrayCounter)
    time.sleep(2)
    print voltSource.readVoltage()
    print voltSource.readCurrent()

voltSource.close()
hitArrayMAPSA = [list(MPA) for MPA in zip(*hitArrayVolt)] # Swap highest and second-higest order of nesting 
print hitArrayMAPSA[0]
print hitArrayMAPSA[1]


for MPA in hitArrayMAPSA:
    plot = MPAPlot()
    for pix in MPA:
        plot.createGraph(voltArray, pix)
    plot.setRange(yRange = [0,50])
    plot.draw()
