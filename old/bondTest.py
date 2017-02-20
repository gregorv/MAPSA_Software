#!/usr/bin/python

from array import array
from MPACalibration import MPACalibration 
from MPAPlot import MPAPlot
from KeithleyControl.keithleyControl import keithley
import ROOT

k = keithley()
k.init()
plot = MPAPlot()
k.setVoltage(110)
# Calibrate MPA (only use MPA 5 as it has confirmed failed bonds)
calibration = MPACalibration([2,5]) # Argument reflects assembly which is actually on board 
calibration.thresholdScan(calEnbl = 1) 
calibration.writeCalibrationToMPA()


# Start scan
resolution = 30 

calibration.thresholdScan()
counter, _ = calibration.getThrScanPerPix()
_,_, threshold = calibration.getThrScanMetadata()
for pix in counter[0]:
    plot.createGraph(array('d',threshold[0]), array('d', pix))


maxHitsPerVolts = []
edgesPerVolt = []
thresholdScansPerBiasVolt = []
voltArray = []


for voltStep in range(5,111, resolution): # Loop over bias voltage in steps of 10
    voltArray.append(voltStep)
    plot.clear()
    k.setVoltage(voltStep)
    print k.readVoltage()
    
    calibration.thresholdScan()
    counter, _ = calibration.getThrScanPerPix() # No need to get memory, only ripple counter needed
    _,_,threshold  = calibration.getThrScanMetadata()
    edgesPerVolt.append(calibration.findHalfMaxEdges())

    maxHitsPerPix = []
    for pix in counter[0]:
        plot.createGraph(array('d', threshold[0]), array('d', pix))
        maxHitsPerPix.append(max(pix))
        
    thresholdScansPerBiasVolt.append(plot.getPlot()) 
    maxHitsPerVolts.append(max(maxHitsPerPix))
k.close()
print "Keithley closed"
c1 = ROOT.TCanvas("c1", "Canvas", 800, 600)

#c1.Divide(3,4)  
#
#for i,graphs in enumerate(thresholdScansPerBiasVolt):
#    c1.cd(i+1)
#    for j,graph in enumerate(graphs):
#        if j == 0:
#            graph.SetTitle("Threshold scan at "+ str(i*10)+"V")
#            graph.GetYaxis().SetRangeUser(0,maxHitsPerVolts[i]*1.1)
#            graph.Draw("APL") 
#        else:
#            graph.Draw("PL")

#plot.clear()

MAPSA = [2,5]
fwhmMAPSAVolt = [] # Volt[MPA[Pix]]

for edgesMAPSA in edgesPerVolt:
    fwhmVolt = []
    for edges in edgesMAPSA:
        fwhm = [pix[1] - pix[0] for pix in edges] # Loop over edge-tuples for each pixel and subtract rising edges from falling edge. This is the full width at half maximum.
        fwhmVolt.append(fwhm)
    fwhmMAPSAVolt.append(fwhmVolt)


MAPSAVoltfwhm = list(zip(*fwhmMAPSAVolt)) # Swap MAPSA and Volt in nested-list-hierarchy
MAPSAfwhmVolt = []
for a in MAPSAVoltfwhm: #iterate over MPAs
    MAPSAfwhmVolt.append(list(zip(*a))) # Swap Volt and Pixel in nested-list-hierarchy. Result: [MPA1[Pix1[Volt1,Volt2,...], Pix2[],...,Pix48[]], MPA2[],..]

MAPSAfwhmDiff = []
for MPA in MAPSAfwhmVolt:
    fwhmDiff = []
    for pix in MPA:
        pixSorted = sorted(pix)
        fwhmDiff.append(sum(pixSorted[-2:])/2 - sum(pixSorted[:2])/2) # Average two highest and two lowest fwhms
   MAPSAfwhmDiff.append(fwhmDiff) 
    
raw_input()
