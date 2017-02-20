import sys
from classes import *
from array import array
from optparse import OptionParser

#import root after optparse to get help page from optparse
from ROOT import TGraph, TCanvas, TLine, TColor


# Add options
parser = OptionParser()

parser.add_option('-w', '--shutterdur', metavar='F', type='int', action='store',
default    =    0xFFFF,
dest    =    'shutterdur',
help    =    'shutter duration')

parser.add_option('-t', '--trim', metavar='F', type='int', action='store',
default    =    30,
dest    =    'trimDAC',
help    =    'Global trim DAC (0-31)')

parser.add_option('-b', '--buffer', metavar='F', type='int', action='store',
default    =    1,
dest    =    'buffer',
help    =    'Select buffer (1-4)')

parser.add_option('-m', '--mpa', metavar='F', type='int', action='store',
default    =    1,
dest    =    'mpa',
help    =    'Select mpa (1-mpaAmount)')

parser.add_option('-c', '--continuous', metavar='F', type='int', action='store',
default =       0,
dest    =       'continuous',
help    =       'Enable continuous datataking')

parser.add_option('-d', '--threshold', metavar='F', type='int', action='store',
default =       50,
dest    =       'threshold',
help    =       'Set threshold for DAC')
(options,args) = parser.parse_args()

# Establish connection
a = uasic(connection="file://connections_test.xml",device="board0")
mapsa=MAPSA(a)
read = a._hw.getNode("Control").getNode('firm_ver').read()
a._hw.dispatch()
print "Running firmware version " + str(read)

# Enable clock
a._hw.getNode("Control").getNode("MPA_clock_enable").write(0x1)
a._hw.dispatch()

# Calibration disable
CE = 0


# MPA Amount

mpaAmount = 6

# Load default config
config = mapsa.config(Config=1,string='default')
config.upload()

# Modify config
confdict = {'OM':[3]*mpaAmount,'RT':[0]*mpaAmount,'SCW':[0]*mpaAmount,'SH2':[0]*mpaAmount,'SH1':[0]*mpaAmount,'THDAC':[0]*mpaAmount,'CALDAC':[30]*mpaAmount,'PML':[1]*mpaAmount,'ARL':[1]*mpaAmount,'CEL':[CE]*mpaAmount,'CW':[0]*mpaAmount,'PMR':[1]*mpaAmount,'ARR':[1]*mpaAmount,'CER':[CE]*mpaAmount,'SP':[0]*mpaAmount,'SR':[1]*mpaAmount,'TRIMDACL':[options.trimDAC]*mpaAmount,'TRIMDACR':[options.trimDAC]*mpaAmount}
config.modifyfull(confdict) 
# Synchronous Acquisition
eventArray = []
hitArrayMem = []
thrArray = []
bxArray = []

# Asynchronous Acquisition
hitArrayCounter = []

thr = options.threshold
# Apply threshold
config.modifyperiphery('THDAC',[thr]*mpaAmount)
config.upload()
# config.write()

a._hw.getNode("Configuration").getNode("num_MPA").write(0x2)
a._hw.getNode("Configuration").getNode("mode").write(0x5)
a._hw.dispatch()
config.spi_wait()

    
# Start acquisition (sequencer)

##########################
### Begin of sequencer ###
##########################

# Set shutter duration
a._hw.getNode("Shutter").getNode("time").write(options.shutterdur)

# Opens shutter (mode = 0x0 single shutter, 0x1 four (buffers) consequitive shutter) 
a._hw.getNode("Control").getNode("Sequencer").getNode('datataking_continuous').write(options.continuous)

# Write in first buffer (default and therefore not necessary to be defined)
a._hw.getNode("Control").getNode("Sequencer").getNode('buffers_index').write(0)

# Readout has to be enabled in order to get the data
a._hw.getNode("Control").getNode("readout").write(1)
a._hw.dispatch()

########################
### End of sequencer ###
########################

# Readout buffer (TRUE / FALSE : Wait for sequencer) and ripple counter
#mem, counter = mpa[options.mpa].daq().read_raw(options.buffer,options.mpa+1,False)
#counter_data  = a._hw.getNode("Readout").getNode("Counter").getNode("MPA"+str(options.mpa)).getNode("buffer_"+str(options.buffer)).readBlock(25)
#memory_data = a._hw.getNode("Readout").getNode("Memory").getNode("MPA"+str(options.mpa)).getNode("buffer_"+str(options.buffer)).readBlock(216)

counter_data  = a._hw.getNode("Readout").getNode("Counter").getNode("MPA" + str(options.mpa)).getNode("buffer_"+str(options.buffer)).readBlock(25)
memory_data = a._hw.getNode("Readout").getNode("Memory").getNode("MPA"+str(options.mpa)).getNode("buffer_"+str(options.buffer)).readBlock(216)
a._hw.dispatch()
            

# Mem integer array to binary string in readable order (header,bx,pix) 
binMemStr= ""
for i in range(0,216):
    binMemStr = binMemStr + '{0:032b}'.format(memory_data[215-i])

# String to binary array
binMem = [binMemStr[x:x+72] for x in range(0,len(binMemStr),72)]

counterArray = []
for x in range(0,len(counter_data)):
    counterArray.append(counter_data[x] & 0xFFFF) # Mask to select left pixel 
    counterArray.append((counter_data[x] >> 16) & 0xFFFF) # Mask to select right pixel

print counterArray 
for x in range(0,len(binMem)):
    print binMem[x]


print 'Binary representation of ripple counter:'
for x in range(0, len(counterArray)):
    print bin(counterArray[x])
