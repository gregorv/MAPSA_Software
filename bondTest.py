from MPACalibration import MPACalibration
from MPAPlot import MPAPlot
from KeithleyControl.keithleyControl import keithley
from ROOT import TCanvas

k = keithley()
k.init()
k.setVoltage(110)
assembly = [2,5]

calibration = MPACalibration(assembly)

calibration.thresholdScan(calEnbl = 1)
k.close()
calibration.writeCalibrationToMPA()


calibration.automaticBondTest(resolution = 2, voltMin = 0)

voltArray, fwhmPerVolt = calibration.bondTestGetFwhmPerVolt() # MPA[Pix[Volt]]

## Data from measurement with Sr90 source on MPA5 to allow comparison with confirmed dead pixels
hits = [24535, 15100, 16743, 14068, 17042, 14568, 22333, 17551, 0, 19322, 0, 19147, 0, 0, 19984, 24712, 24401, 15963, 15078, 16422, 13774, 14310, 13577, 15085, 11354, 14313, 13706, 14324, 12457, 14413, 14432, 23665, 24579, 12675, 13340, 12612, 15251, 10976, 15562, 0, 16572, 0, 16463, 13214, 15304, 13793, 15967, 24799]
colors = [1 if pix > 10 else 2 for pix in hits] 

for nMPA, MPA in enumerate(fwhmPerVolt): # Loop over MPAs
    plot = MPAPlot() 
    for fwhm in MPA: # Loop over pix
        plot.createGraph(voltArray, fwhm)
    plot.setTitle("Bond test for MPA" + str(assembly[nMPA]) +" ; Bias voltage / V ; FWHM of noise from threshold scan / thrDACs")
    if nMPA == 1: # Mark MPA5 with confirmed bad bonds
        plot.setLineColor(colors)
    plot.setRange(yRange =  [0,100])
    plot.draw()

#thrScansPerBiasVolt = calibration.bondTestGetThrScanPerVolt() 
#
#bondTestGraphs = []
#for volt in thrScansPerBiasVolt:
#    plot = MPAPlot()
#    for pix in volt[0]:
#        plot.createGraph(pix, range(0,255)) 
#    bondTestGraphs.append(plot.getPlot())

diffs = calibration.bondTestGetDiff()
print diffs[0]
print diffs[1]

maxMPA = max([max(mpa) for mpa in diffs])
print maxMPA

scaledDiffs = []
for mpa in diffs:
    scaledDiffs.append([(pix*1000/maxMPA) for pix in mpa])
print scaledDiffs

for mpa in scaledDiffs:
    plot = MPAPlot()
    plot.createHitMap(mpa)
    plot.setRange(zRange = [0,1000])
    plot.draw()
