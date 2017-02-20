# Start threshold scan (only every 'res' thresholds)
from classes import *

a = uasic(connection="file://connections_test.xml",device="board0")
mapsa=MAPSA(a)
config = mapsa.config(Config=1,string='default')

def thresholdScan(res, shutterdur): 
    mpaAmount = 2 
    thrArray = []
    hitArrayCounter = []
    for thr in range(0,255,res):

        print thr

        # Apply threshold
        config.modifyperiphery('THDAC',[thr]*6)
        config.upload()
        config.write()
        
        thrArray.append(thr)
        # Start acquisition (sequencer)

        ##########################
        ### Begin of sequencer ###
        ##########################
        
        # Set shutter duration
        a._hw.getNode("Shutter").getNode("time").write(shutterdur)

        # Opens shutter (mode = 0x0 single shutter, 0x1 four (buffers) consequitive shutter) 
        a._hw.getNode("Control").getNode("Sequencer").getNode('datataking_continuous').write(0x0)

        # Write in first buffer (default and therefore not necessary to be defined)
        #a._hw.getNode("Control").getNode("Sequencer").getNode('buffers_index').write(0)

        # Readout has to be enabled in order to get the data
        a._hw.getNode("Control").getNode("readout").write(1)
        a._hw.dispatch()
        
        ########################
        ### End of sequencer ###
        ########################

        # Readout buffer (TRUE / FALSE : Wait for sequencer) and ripple counter (Names don't match because ripples are in wrong registers)
        mpaArrayCounter = []
        for i in range(0,mpaAmount): 
            counter  = a._hw.getNode("Readout").getNode("Counter").getNode("MPA" + str(5 + i)).getNode("buffer_1").readBlock(25) 
            a._hw.dispatch()
                        
            counterArray = []
            for x in range(1,len(counter)): # Skip header at [0]
                    counterArray.append(counter[x] & 0xFFFF) # Mask to select left pixel 
                    counterArray.append((counter[x] >> 16) & 0xFFFF) # Mask to select right pixel
            
            mpaArrayCounter.append(counterArray)

        hitArrayCounter.append(mpaArrayCounter)	

    print "--- END OF SCAN ---"

    # Generate new list [MPA1[[[pix1_ThScan],[pix2_ThScan]],MPA2[...], ..] from asynchronous acquisition (ripple counter)
    mpaPxlVsThrCounter = []
    for i in range(0,mpaAmount):
        pxlVsThrCounter = []
        for ipix in range(0,len(hitArrayCounter[i][0])):
            pxlVsThrCounter.append([item[i][ipix] for item in hitArrayCounter])
        mpaPxlVsThrCounter.append(pxlVsThrCounter) 

    return thrArray, mpaPxlVsThrCounter
