from MPACalibration import MPACalibration
from MPAPlot import MPAPlot
from ROOT import TCanvas

assembly = [2,5]

calibration = MPACalibration(assembly)

calibration.thresholdScan(calEnbl = 1)
calibration.writeCalibrationToMPA()

fwhm = []
raw_input("Please make sure HV is not connected to sensor")

fwhm.append(calibration.voltTest())

raw_input("Please plug in HV now and set to specified voltage")
fwhm.append(calibration.voltTest())


## Data from measurement with Sr90 source on MPA5 to allow comparison with confirmed dead pixels
hits = [24535, 15100, 16743, 14068, 17042, 14568, 22333, 17551, 0, 19322, 0, 19147, 0, 0, 19984, 24712, 24401, 15963, 15078, 16422, 13774, 14310, 13577, 15085, 11354, 14313, 13706, 14324, 12457, 14413, 14432, 23665, 24579, 12675, 13340, 12612, 15251, 10976, 15562, 0, 16572, 0, 16463, 13214, 15304, 13793, 15967, 24799]
colors = [1 if pix > 10 else 2 for pix in hits] 

fwhmMAPSA = [list(volt) for volt in zip(*fwhm)]

fwhmPerVolt = []
for mpa in fwhmMAPSA:
   fwhmPerVolt.append([list(pix) for pix in zip(*mpa)]) 


voltArray = [0, 110]

for nMPA, MPA in enumerate(fwhmPerVolt): # Loop over MPAs
    plot = MPAPlot() 
    for fwhm in MPA: # Loop over pix
        plot.createGraph(voltArray, fwhm)
    plot.setTitle("Bond test for MPA" + str(assembly[nMPA]) +" ; Bias voltage / V ; FWHM of noise from threshold scan / thrDACs")
    if nMPA == 1: # Mark MPA5 with confirmed bad bonds
        plot.setLineColor(colors)
    plot.setRange(yRange =  [0,100])
    plot.draw()

#
#maxMPA = max([max(mpa) for mpa in diffs])
#print maxMPA
#
#scaledDiffs = []
#for mpa in diffs:
#    scaledDiffs.append([(pix*1000/maxMPA) for pix in mpa])
#print scaledDiffs
#
#for mpa in scaledDiffs:
#    plot = MPAPlot()
#    plot.createHitMap(mpa)
#    plot.setRange(zRange = [0,1000])
#    plot.draw()
