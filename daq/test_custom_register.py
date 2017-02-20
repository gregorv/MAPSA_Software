import sys
from classes import *
from array import array
from optparse import OptionParser
from ROOT import TGraph, TCanvas, TLine, TTree, TFile
from MPACalibration import MPACalibration
import time

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
#    conf.append(mpa[iMPA].config("data/Conf_trimcalib_MPA" + str(nMPA)+ "_config1.xml")) # Use trimcalibrated config
    conf.append(mpa[iMPA].config("data/Conf_default_MPA" + str(nMPA)+ "_config1.xml"))
    
    
threshold = 70 

# Define default config
for iMPA in range(len(assembly)):
    conf[iMPA].modifyperiphery('THDAC',threshold) # Write threshold to MPA 'iMPA'
    conf[iMPA].upload()
    glib.getNode("Configuration").getNode("mode").write(nMPA - 1)
    conf[iMPA].spi_wait() # includes dispatch


glib.getNode("Control").getNode('testbeam_clock').write(0x1) # Enable external clock 
glib.dispatch()

r = glib.getNode("Custom").getNode("tel_busy_enable").read()
glib.dispatch()
print(r)
glib.getNode("Custom").getNode("tel_busy_enable").write(0x1)
glib.dispatch()
r = glib.getNode("Custom").getNode("tel_busy_enable").read()
glib.dispatch()
print(r)
sys.exit(0)

