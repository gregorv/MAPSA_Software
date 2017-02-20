import sys
from classes import *
from array import array
from optparse import OptionParser
from ROOT import TGraph, TCanvas, TLine

# Connection and GLIB 
a = uasic(connection="file://connections_test.xml",device="board0")
glib = a._hw

single = True

# Get all 6 MPAs and corresponding configs
mpa=[]
conf=[]

for i in range(0,6):
    mpa.append(MPA(a._hw,i+1))
    conf.append(mpa[i].config("data/Default_MPA.xml"))

# Define MPA (1-6) (nMPA 2 or 5 for double assembly)

mpaDict = {0:2,1:5}
iMPA = 1

# Modify config

glib.getNode("Control").getNode("MPA_clock_enable").write(0x1)
glib.dispatch()

if single:

    glib.getNode("Configuration").getNode("num_MPA").write(0x2)

    # Define default config
    defaultPixelCfg = {'PML':1,'ARL':1,'CEL':0,'CW':0,'PMR':1,'ARR':1,'CER':0,'SP':0,'SR':1,'TRIMDACL':30,'TRIMDACR':30}
    defaultPeripheryCfg = {'OM':3,'RT':0,'SCW':0,'SH2':0,'SH1':0,'THDAC':0,'CALDAC':30}

    # Upload
    for key in defaultPeripheryCfg:
        conf[iMPA].modifyperiphery(key,defaultPeripheryCfg[key])
    for pix in range(0,24):
        for key in defaultPixelCfg:
            conf[iMPA].modifypixel(pix,key,defaultPixelCfg[key])

    conf[iMPA].upload()
    glib.getNode("Configuration").getNode("mode").write(0x1)
    glib.dispatch()
    
else:

    CE = 0
    
    mapsa = MAPSA(a)
    for i in range(1,7):
        mpa.append(mapsa.getMPA(i))

    config = mapsa.config(Config=1,string='default')
    config.upload()
    confdict = {'OM':[3]*6,'RT':[0]*6,'SCW':[0]*6,'SH2':[0]*6,'SH1':[0]*6,'THDAC':[0]*6,'CALDAC':[30]*6,'PML':[1]*6,'ARL':[1]*6,'CEL':[CE]*6,'CW':[0]*6,'PMR':[1]*6,'ARR':[1]*6,'CER':[CE]*6,'SP':[0]*6,'SR':[1]*6,'TRIMDACL':[30]*6,'TRIMDACR':[30]*6}
    config.modifyfull(confdict) 

    
eventArray = []
hitArray = []
thrArray = []
bxArray = []


# Start threshold scan
for thr in range(0,255):

    if thr%2 == 0:
        print thr

        # Apply threshold
        
        if single:
            conf[iMPA].modifyperiphery('THDAC',thr)
            conf[iMPA].upload()
            
	    glib.getNode("Configuration").getNode("mode").write(0x1)
            conf[iMPA].spi_wait()
        else:
            config.modifyperiphery('THDAC',[thr]*6)
            config.upload()
            config.write()
        
        # Start acquisition (sequencer)
        #mapsa.daq().Sequencer_init(options.continuous,options.shutterdur)

        ##########################
        ### Begin of sequencer ###
        ##########################
        
        # Set shutter duration
        a._hw.getNode("Shutter").getNode("time").write(0xFFFF)

        # Opens shutter (mode = 0x0 single shutter, 0x1 four (buffers) consequitive shutter) 
	a._hw.getNode("Control").getNode("Sequencer").getNode('datataking_continuous').write(0)

        # Write in first buffer (default and therefore not necessary to be defined)
        #a._hw.getNode("Control").getNode("Sequencer").getNode('buffers_index').write(0)
        
        # Readout has to be enabled in order to get the data
        a._hw.getNode("Control").getNode("readout").write(1)
        a._hw.dispatch()
        
        ########################
        ### End of sequencer ###
        ########################
        
        # Readout buffer (TRUE / FALSE : Wait for sequencer)
        mem = mpa[mpaDict[iMPA]-1].daq().read_raw(1,1,True)[0]

        # Mem integer array to binary string in readable order (header,bx,pix) 
        binMemStr= ""
        for i in range(0,216):
            binMemStr = binMemStr + '{0:032b}'.format(mem[215-i])

        # String to binary array
        binMem = [binMemStr[x:x+72] for x in range(0,len(binMemStr),72)]

        # Get elements of binary string
        hd = []
        bx = []
        pix = []
        for entry in binMem:
            hd.append(entry[0:8])
            bx.append(entry[8:24])
            pix.append(entry[24:72])

        # Count number of Events
        nEvents = 0
        for event in hd:
            if event == "11111111":
                nEvents+=1

        # Sum hits per pixel
        sumPixHits = [0]*48
        for event in pix:
            for i, ipix in enumerate(event):
                sumPixHits[i]+=int(ipix)

        # bunch crossing from binary to int
        bx=[int(ibx,2) for ibx in bx]

        eventArray.append(nEvents)        
        hitArray.append(sumPixHits)
        thrArray.append(thr)
        bxArray.append(bx)


print "---END OF SCAN---"

for ithr in bxArray:
    print max(ithr)

# Generate new list [[pix1_ThScan],[pix2_ThScan],..]
pxlVsThr = []
for ipix in range(0,len(hitArray[0])):
    pxlVsThr.append([item[ipix] for item in hitArray])

# Generate graphs for each pixel
graphs = []

for ipixScan in pxlVsThr:
    graphs.append(TGraph(len(thrArray),array('d',thrArray),array('d',ipixScan)))

# Draw graphs on canvas
c1 = TCanvas("graph","graph",1024,768)
c1.cd()    

for i,graph in enumerate(graphs):
    if i==0:
        graph.SetTitle('Threshold Scan;Threshold (DAC);Number of Hits')
        graph.GetYaxis().SetRangeUser(0,max(eventArray)*1.1)
        graph.Draw("APL")
    else:
        graph.Draw("PL")

# Add line for nMax
line = TLine(0,max(eventArray),graphs[0].GetXaxis().GetXmax(),max(eventArray))
line.SetLineColor(2)
line.Draw()

print "Max number of events during scan: %s" %max(eventArray)

raw_input("Press any key to exit")




