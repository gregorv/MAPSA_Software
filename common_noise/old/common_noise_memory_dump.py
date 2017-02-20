import sys
from classes import *
from array import array
from optparse import OptionParser
from ROOT import TGraph, TCanvas, TLine

# Connection and GLIB 
a = uasic(connection="file://connections_test.xml",device="board0")
glib = a._hw 

# Source all classes
mapsa = MAPSA(a)

# Get all 6 MPAs and corresponding configs
mpa=[]
conf=[]

for i in range(0,6):
    mpa.append(MPA(glib,i+1))
    conf.append(mpa[i].config("data/Default_MPA.xml"))


# Define MPA (1-6) (iMPA 2 or 5 for double assembly)
mpaDict = {0:2,1:5}

iMPA = 1 # Zero-indexed (from 0 to 5 on full assembly) 

# File to which data from synchronous acquision will be written
memoryFile = open('data/synchronous_data_noise_MPA'+str(iMPA+1),'w')

# Set voltage steps of threshold DAC and trimming DAC (in mV/Step)
thrVoltStep = 1.456
trimVoltStep = 3.75

# Modify config

glib.getNode("Control").getNode("MPA_clock_enable").write(0x1)
glib.dispatch()
glib.getNode("Configuration").getNode("num_MPA").write(0x2)

##### Define default config
threshold = 47

# Load trimDac config and convert to int 
trimDac = open('trimDac_MPA'+str(iMPA+1)).read().splitlines()
trimDac = [int(pxl) for pxl in trimDac]

shutterDur = 0xFFF #0xFFFF is maximum, in clock cycles

defaultPixelCfg = {'PML':1,'ARL':1,'CEL':0,'CW':0,'PMR':1,'ARR':1,'CER':0,'SP':0,'SR':1,'TRIMDACL':30,'TRIMDACR':30}
defaultPeripheryCfg = {'OM':3,'RT':0,'SCW':0,'SH2':0,'SH1':0,'THDAC':threshold,'CALDAC':30}


# Upload
for key in defaultPeripheryCfg:
    conf[iMPA].modifyperiphery(key,defaultPeripheryCfg[key])
for pix in range(0,24):
    for key in defaultPixelCfg:
        conf[iMPA].modifypixel(pix + 1,key,defaultPixelCfg[key])


# Write trimDac values to MPA
for pix in range(0,24):
    conf[iMPA].modifypixel(pix + 1,'TRIMDACL',trimDac[2*pix])
    conf[iMPA].modifypixel(pix + 1,'TRIMDACR',trimDac[2*pix + 1])

conf[iMPA].upload()
glib.getNode("Configuration").getNode("mode").write(0x1)
glib.dispatch()


# Write twice to push config to Memory_OutConf to check what has been written 
glib.getNode("Configuration").getNode("mode").write(0x1)
conf[iMPA].spi_wait()

outConf = glib.getNode("Configuration").getNode("Memory_OutConf").getNode("MPA"+str(iMPA + 1)).getNode("config_1").readBlock(0x19) # Get written config
glib.dispatch()
readconf = []
for pix in outConf: # Format this config to extract trimDac values
#    print '{0:020b}'.format(pix)
    readconf.append((pix >> 2) & 0b11111)
    readconf.append((pix >> 12) & 0b11111)

print "Written TrimDAC: %s" %readconf

hitArray = []
sumArray = []
emptyEvents = []
for i in range(0,500):

    # Start acquisition (sequencer) (Enable single (0) or four (4) consequitive buffers for shutter. Set Shutter duration and do final 'write' to push config to MPA)
    mapsa.daq().Sequencer_init(0,shutterDur)

    # Read data from memory (sync acquisition)
    mem = mpa[mpaDict[iMPA]-1].daq().read_raw(1,1,True)[0]
    # Mem integer array to binary string in readable order (header,bx,pix) 
    binMemStr= ""
    for i in range(0,216):
        binMemStr = binMemStr + '{0:032b}'.format(mem[215-i])

    # String to binary array
    binMem = [binMemStr[x:x+72] for x in range(0,len(binMemStr),72)]
    
    emptyEvents.append(int(binMem[-1][9:24],2)) # Get total number of events in this iteration, convert it to an int from binary string and append. First bit of BX-Id is skipped as this can be faulty

    # Get elements of binary string
    for entry in binMem:
        memoryFile.write(entry[24:72]) 
        memoryFile.write('\n')
    
    time.sleep(0.1) # If this is not here strange values appear in array, maybe GLIB isn't ready

memoryFile.write(str(sum(emptyEvents))) # Sum empty events and write to file
memoryFile.close()


