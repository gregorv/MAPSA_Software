from MPACalibration import MPACalibration
from MPAPlot import MPAPlot
from KeithleyControl.keithleyControl import keithley
from ROOT import TFile

voltSource = keithley()
voltSource.init()
voltSource.setVoltage(110)
print voltSource.readCurrent()

rootFile = TFile("plots_kit/CalDAC_test_results.root", "recreate")
assembly = [2,5]
calibration = MPACalibration(assembly)
calibration.thresholdScan(calEnbl = True)
calibration.writeCalibrationToMPA()

## Data from measurement with Sr90 source on MPA5 to allow comparison with confirmed dead pixels
hits = [24535, 15100, 16743, 14068, 17042, 14568, 22333, 17551, 0, 19322, 0, 19147, 0, 0, 19984, 24712, 24401, 15963, 15078, 16422, 13774, 14310, 13577, 15085, 11354, 14313, 13706, 14324, 12457, 14413, 14432, 23665, 24579, 12675, 13340, 12612, 15251, 10976, 15562, 0, 16572, 0, 16463, 13214, 15304, 13793, 15967, 24799]
colors = [1 if pix > 10 else 2 for pix in hits] 

calScanEdges = []
for calDAC in range(0,255, 10):
    
    calibration.thresholdScan(calEnbl = True, calCharge = calDAC)

    calScanEdges.append(calibration.findFallingEdges())


MAPSACalPix = [list(cal) for cal in zip(*calScanEdges)]

MAPSAPixCal = []
for MPA in MAPSACalPix:

    MAPSAPixCal.append([list(pix) for pix in zip(*MPA)]) 

for i,MPA in enumerate(MAPSAPixCal):
    plot = MPAPlot()

    for pix in MPA:
        plot.createGraph(range(0,255,10), pix)
    if i == 1: 
        plot.setLineColor(colors)
    plot.setTitle("Caldac linearity scan for MPA "+str(assembly[i])+"; Calibration charge / calDACs; Falling edge position / thrDACs")
    plot.draw() 

    graphs = plot.getPlot()
    mpaDir = rootFile.mkdir("MPA "+str(assembly[i]), "MPA "+str(assembly[i]))
    for graph in graphs:
        mpaDir.Add(graph) 
    mpaDir.Write()

rootFile.Close()
