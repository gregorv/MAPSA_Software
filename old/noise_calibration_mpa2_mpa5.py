import sys
from classes import *
from array import array
from optparse import OptionParser
from thresholdscan import thresholdScan

# Add options
parser = OptionParser()

parser.add_option('-w', '--shutterdur', metavar='F', type='int', action='store',
default	=	0xFFFF,
dest	=	'shutterdur',
help	=	'shutter duration')

parser.add_option('-b', '--buffer', metavar='F', type='int', action='store',
default	=	1,
dest	=	'buffer',
help	=	'Select buffer (1-4)')

parser.add_option('-m', '--mpa', metavar='F', type='int', action='store',
default	=	1,
dest	=	'mpa',
help	=	'Select mpa (1-6)')

parser.add_option('-c', '--continuous', metavar='F', type='int', action='store',
default =       0,
dest    =       'continuous',
help    =       'Enable continuous datataking')

(options,args) = parser.parse_args()

#import root after optparse to get help page from optparse
from ROOT import TGraph, TCanvas, TLine, TColor

# Establish connection
a = uasic(connection="file://connections_test.xml",device="board0")
mapsa=MAPSA(a)
read = a._hw.getNode("Control").getNode('firm_ver').read()
a._hw.dispatch()
print "Running firmware version " + str(read)


mpa = []
conf = []
for i in range(1,7):
    mpa.append(mapsa.getMPA(i))
    conf.append(mpa[i-1].config("data/Conf_default_MPA"+str(i)+"_config1.xml"))            

# Reset control logic
a._hw.getNode("Control").getNode("logic_reset").write(0x1)
a._hw.dispatch()

# Enable clock
a._hw.getNode("Control").getNode("MPA_clock_enable").write(0x1)
a._hw.dispatch()

# Calibration disable
CE = 0

# Resolution of threshold scan (only scan every 'res' steps)
res = 1 

# Load default config
config = mapsa.config(Config=1,string='default')
config.upload()

# Set voltage steps of threshold DAC and trimming DAC (in mV/Step)
thrVoltStep = 1.456
trimVoltStep = 3.75

# Modify config
confdict = {'OM':[3]*6,'RT':[0]*6,'SCW':[0]*6,'SH2':[0]*6,'SH1':[0]*6,'THDAC':[0]*6,'CALDAC':[30]*6,'PML':[1]*6,'ARL':[1]*6,'CEL':[CE]*6,'CW':[0]*6,'PMR':[1]*6,'ARR':[1]*6,'CER':[CE]*6,'SP':[0]*6,'SR':[1]*6,'TRIMDACL':[30]*6,'TRIMDACR':[30]*6}
config.modifyfull(confdict) 


############################
### Start Threshold Scan ###
############################

thrArray, pxlVsThrCounterAllMPAs = thresholdScan(res, options.shutterdur) # Array with threshold values and array [MPA1[[[pix1_ThScan], [pix2_ThScan],....], MPA2[[..],[..],...]]]

print pxlVsThrCounterAllMPAs

pxlVsThrCounter2 = pxlVsThrCounterAllMPAs[0] # Split into one array for each MPA
pxlVsThrCounter5 = pxlVsThrCounterAllMPAs[1] 


##########################################################
### Begin plotting uncalibrated pixels over thresholds ###
##########################################################

# Generate graphs for each pixel in asynchronous memory (ripple counter)
graphsCounter2 = []

for ipixScan in pxlVsThrCounter2:
    graphsCounter2.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))

graphsCounter5 = []

for ipixScan in pxlVsThrCounter5:
    graphsCounter5.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))


# Draw graphs on canvas
c1 = TCanvas("graph","graph",1024,768)
c1.Divide(2)

c1.cd(1)   

for i,graph2 in enumerate(graphsCounter2):
    if i==0:
        graph2.SetTitle('Threshold Scan;Threshold (DAC);Number of Hits')
        graph2.Draw("APL")
    else:
        graph2.Draw("PL")

c1.cd(2)

for i,graph5 in enumerate(graphsCounter5):
    if i==0:
        graph5.SetTitle('Threshold Scan;Threshold (DAC);Number of Hits')
        graph5.Draw("APL")
    else:
        graph5.Draw("PL")



##################################
### Begin calibration on noise ###
##################################

# Find pixel with lowest threshold
thrArrayFallingEdge = []
for pxl in pxlVsThrCounter2:

    pxl = [hits if hits < 10000 else 0 for hits in pxl]
    halfMax = max(pxl)/2

    pxlDiff = [abs(x - halfMax) for x in pxl] # Difference of hits for each threshold to half maximum of hits
    thrRightOfHalfMaxFalling = max([             # Highest threshold to get threshold right after halfmax of falling edge
                                thrArray[pxlDiff.index(pxlDiffI)] # Match differences of hits to threshold values
                                for pxlDiffI in sorted(pxlDiff)[:4] # Four threshold values with smallest distance to halfmax (left/right of rising edge and left/right of falling edge)
                                ])
    thrArrayFallingEdge.append(thrRightOfHalfMaxFalling)

pxlLowestThreshold =  thrArrayFallingEdge.index(min(thrArrayFallingEdge))

trimDacToTheLeft = [(pxl - pxlLowestThreshold) * (thrVoltStep/trimVoltStep)
             for pxl in thrArrayFallingEdge]

# Normalize trimDac and take into account that we started with trimDac set to 30
trimDac = [max(0, (30 - int(pxlTrimDac))) for pxlTrimDac in trimDacToTheLeft]

# Split into left and right pixels
trimDacLeftPxl = [trimDac [x] for x in range(0,len(trimDac),2)]
trimDacRightPxl = [trimDac [x] for x in range(1,len(trimDac),2)]

# Modify pixels with new trimDac values (Using the trimming values from MPA 2 for all MPAs, just for now)

a._hw.getNode("Configuration").getNode("num_MPA").write(0x2)

for i in range(0,24):
        conf[0].modifypixel(i+1,'TRIMDACL',[trimDacLeftPxl[i]]*6)
        conf[0].modifypixel(i+1,'TRIMDACR',[trimDacRightPxl[i]]*6)
#config.modifyperiphery('OM',[3]*6)
#config.modifyperiphery('RT',[0]*6)
#config.modifyperiphery('SCW',[0]*6)
#config.modifyperiphery('SH2',[0]*6)
#config.modifyperiphery('SH1',[0]*6)
#config.modifyperiphery('THDAC',[0]*6)
#config.modifyperiphery('CALDAC', [30]*6)
#for x in range(1,25):
#	config.modifypixel(x,'PML', [1]*6)
#	config.modifypixel(x,'ARL', [1]*6)
#	config.modifypixel(x,'CEL', [CE]*6)
#	config.modifypixel(x,'CW', [0]*6)
#	config.modifypixel(x,'PMR', [1]*6)
#	config.modifypixel(x,'ARR', [1]*6)
#	config.modifypixel(x,'CER', [CE]*6)
#	config.modifypixel(x,'SP',  [0]*6) 
#	config.modifypixel(x,'SR',  [1]*6) 
#config.upload()
#config.write()

a._hw.getNode("Configuration").getNode("mode").write(0x1)
a._hw.dispatch()
    


#for i in range(0,24):
    

### Start new threshold scan, this time with calibrated pixels
thrArray, pxlVsThrCounterAllMPAs = thresholdScan(res, options.shutterdur) # Array with threshold values and array [MPA1[[[pix1_ThScan], [pix2_ThScan],....], MPA2[[..],[..],...]]]

pxlVsThrCounter2 = pxlVsThrCounterAllMPAs[0] # Split into one array for each MPA
pxlVsThrCounter5 = pxlVsThrCounterAllMPAs[1] 

##########################################################
### Begin plotting calibrated pixels over thresholds ###
##########################################################

# Generate graphs for each pixel in asynchronous memory (ripple counter)
graphsCounter2 = []
for ipixScan in pxlVsThrCounter2:
    graphsCounter2.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))

graphsCounter5 = []
for ipixScan in pxlVsThrCounter5:
    graphsCounter5.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))


# Draw graphs on canvas
c2 = TCanvas("graph2","Calibrated graph",1024,768)
c2.Divide(2)

c2.cd(1)

for i,graph2 in enumerate(graphsCounter2):
    if i==0:
        graph2.SetTitle('Threshold Scan;Threshold (DAC);Number of Hits')
        graph2.Draw("APL")
    else:
       graph2.Draw("PL")

c2.cd(2)

for i,graph5 in enumerate(graphsCounter5):
    if i==0:
        graph5.SetTitle('Threshold Scan;Threshold (DAC);Number of Hits')
        graph5.Draw("APL")
    else:
        graph5.Draw("PL")



raw_input("Press any key to exit")
