from classes import *
from MPACalibration import MPACalibration
from MPAPlot import MPAPlot

assembly = [2,5]

# Connection and GLIB 
a = uasic(connection="file://connections_test.xml",device="board0")
glib = a._hw 

# Enable clock on MPA
glib.getNode("Control").getNode("MPA_clock_enable").write(0x1)
glib.dispatch()

# Reset all logic on GLIB
glib.getNode("Control").getNode("logic_reset").write(0x1)
glib.dispatch()

# Source all classes
mapsaClasses = MAPSA(a)

calibration = MPACalibration(assembly)

conf = []
mpa = []
for iMPA, nMPA  in enumerate(assembly):
    mpa.append(MPA(glib, iMPA+1)) # List of instances of MPA, one for each MPA. SPI-chain numbering!
    conf.append(mpa[iMPA].config("data/Conf_trimcalib_MPA" + str(nMPA)+ "_masked.xml")) # Use trimcalibrated config

calibration.thresholdScan(calEnbl = False, conf = conf)


counter, mem = calibration.getThrScanPerPix()
_,_,threshold = calibration.getThrScanMetadata()

for i, nMPA in enumerate(counter):
    plot = MPAPlot()
    for pix in nMPA[1:]:
        plot.createGraph(threshold[i], pix)
    plot.draw()


