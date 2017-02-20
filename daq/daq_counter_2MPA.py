import sys
from classes import *
from array import array
from optparse import OptionParser
from ROOT import TGraph, TCanvas, TLine

# Connection and GLIB 
a = uasic(connection="file://connections_test.xml",device="board0")
glib = a._hw 

# Get all 6 MPAs and corresponding configs
mpa=[]
conf=[]

for i in range(0,6):
    mpa.append(MPA(glib,i+1))
    conf.append(mpa[i].config("data/Default_MPA.xml"))

# Define MPA (1-6) (iMPA 2 or 5 for double assembly)

mpaDict = {0:2,1:5}

iMPA = 0 # Zero-indexed (from 0 to 5 on full assembly) 

# Set voltage steps of threshold DAC and trimming DAC (in mV/Step)
thrVoltStep = 1.456
trimVoltStep = 3.75

# Modify config

glib.getNode("Control").getNode("MPA_clock_enable").write(0x1)
glib.dispatch()
glib.getNode("Configuration").getNode("num_MPA").write(0x2)

# Define default config
threshold = 70 

## Load trimDac config 
trimDac = open('trimDac_MPA'+str(iMPA+1)).read().splitlines() # Open file with trimDac values for MPA
trimDac = [int(pxl) for pxl in trimDac]


shutterDur = 0xFF #0xFFFF is maximum, in clock cycles

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

print "Written Trim DAC: %s" %readconf[2:] # Skip periphery config (first two entries)

hitArrayCounter = []
sumArray = []
for i in range(0,500000):
    ##########################
    ### Begin of sequencer ###
    ##########################
    
    # Set shutter duration
    glib.getNode("Shutter").getNode("time").write(shutterDur)
    
    # Opens shutter (mode = 0x0 single shutter, 0x1 four (buffers) consequitive shutter) 
    glib.getNode("Control").getNode("Sequencer").getNode('datataking_continuous').write(0)
    
    # Write in first buffer (default and therefore not necessary to be defined)
    #glib.getNode("Control").getNode("Sequencer").getNode('buffers_index').write(0)
    
    # Readout has to be enabled in order to get the data
    glib.getNode("Control").getNode("readout").write(1)
    conf[iMPA].spi_wait()
    
    
    ########################
    ### End of sequencer ###
    ########################
    counter  = glib.getNode("Readout").getNode("Counter").getNode("MPA"+str(iMPA + 1)).getNode("buffer_1").readBlock(25) 
    glib.dispatch()
    
    counterArray = []
    for x in range(1,len(counter)): # Skip header at [0]
            counterArray.append(counter[x] & 0xFFFF) # Mask to select left pixel 
            counterArray.append((counter[x] >> 16) & 0xFFFF) # Mask to select right pixel
    counterArray = [pix if pix < 20000 else 0 for pix in counterArray]
    hitArrayCounter.append(counterArray)
    sumArray.append(sum(counterArray))
    #time.sleep(0.5) # If this is not here strange values appear in array, maybe GLIB isn't ready


####################
### Analyse hits ###
####################


# Sum over all loops for each pixel
sumPixArray = hitArrayCounter[1] 
for i in range(1,len(hitArrayCounter)):
    for j in range(len(hitArrayCounter[i])):
        sumPixArray[j] += hitArrayCounter[i][j]

shutterDurInSeconds = shutterDur*len(hitArrayCounter) * 1/(160e6) # For frequency of hits

print hitArrayCounter
print "Hits for each pixel, summed over %s readout cycles: %s \n" %(len(hitArrayCounter), sumPixArray)
print "Average hits for all pixels: %s  Total readout time: %s seconds \n" %((sum(sumPixArray)/len(sumPixArray)), shutterDurInSeconds)
print "Frequency of hits: %s" %(sum(sumArray)/shutterDurInSeconds) 
