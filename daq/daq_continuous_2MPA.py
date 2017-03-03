import sys
import os
from classes import *
from ctypes import *
import time
import argparse
import errno
import itertools

parser = argparse.ArgumentParser(description="MaPSA DAQ")
parser.add_argument("--external-clock", "-x", default=False,
                    help="Use external 40MHz clock, e.g. for testbeam operation.", action="store_true")
parser.add_argument("--threshold", "-t", type=int,
                    metavar="BYTE", help="Threshold value", default="100")
parser.add_argument("--assembly", "-a", metavar="NAME",
                    help="Name of the assembly, used to differentiate trimming configurations", default="default")
parser.add_argument("--mpa-index", "-i", metavar="IDX", type=int, choices=range(1, 7),
                    action="append", help="Specify the indices of the MPAs in the SPI chain", default=[])
parser.add_argument("--output-dir", "-o", metavar="DIR",
                    help="Directory where run data is stored", default="./data")
parser.add_argument("--config", "-c", metavar="FILEFORMAT",
                    help="Filename format string for trimming and masking MPA configuration. The variables {assembly} and {mpa} are available.", default="Conf-{assembly}_MPA-{mpa}.xml")
parser.add_argument("--config-dir", metavar="DIR", default="data/", help="Configuration directory.")
parser.add_argument("--num-triggers", "-n", metavar="NTRIG", default=500000, help="Number of trigger events to record. Set to 0 for user-interrupted, unlimited recording.", type=int)
parser.add_argument("--root", "-R", default=False, action="store_true",
    help="If set, write data to root file instead of plaintext output. It is"
    "written into the directory specified with --output-dir, while the"
    "name is specified with --root-fmt. The run numbering is used as with"
    "the plaintext output.")
parser.add_argument("--root-fmt", "-F", metavar="ROOTFILE", default="run{number:04d}.root",
    help="Format of the filename for ROOT file output. You can use the variables {number} and {assembly}.")

args = parser.parse_args()
runNumber = 0
runNumberFile = os.path.join(args.output_dir, 'currentRun.txt')
try:
    with open(runNumberFile, 'r') as runFile:
        runNumber = int(runFile.read())
except IOError:
    pass

# Importing ROOT before parsing argument messes up the help output. Well
# done, root.
from ROOT import TGraph, TCanvas, TLine, TTree, TFile

if args.mpa_index:
    assembly = list(sorted(args.mpa_index))
else:
    assembly = [2, 5]

# Connection and GLIB
a = uasic(connection="file://connections_test.xml", device="board0")
glib = a._hw

# Enable clock on MPA
glib.getNode("Control").getNode("MPA_clock_enable").write(0x1)
glib.dispatch()

# Reset all logic on GLIB
glib.getNode("Control").getNode("logic_reset").write(0x1)
glib.dispatch()

# Source all classes
mapsaClasses = MAPSA(a)

conf = []
mpa = []
try:
    for iMPA, nMPA in enumerate(assembly):
        # List of instances of MPA, one for each MPA. SPI-chain numbering!
        mpa.append(MPA(glib, iMPA + 1))
        # conf.append(mpa[iMPA].config("data/Conf_trimcalib_MPA" + str(nMPA)+
        # "_masked.xml")) # Use trimcalibrated config
        conf.append(mpa[iMPA].config(
            os.path.join(
                args.config_dir,
                args.config.format(mpa=nMPA, assembly=args.assembly))))
except IOError, e:
    if e.filename and e.errno == errno.ENOENT:
        parser.error(
            "Cannot open MPA configuration '{0}'.\nCheck --config and --assembly settings, or perform trimming.".format(e.filename))
    else:
        raise

# Define default config
for iMPA in range(0, len(assembly)):
    # Write threshold to MPA 'iMPA'
    conf[iMPA].modifyperiphery('THDAC', args.threshold)
    # Enable synchronous readout on all pixels
    conf[iMPA].modifypixel(range(1, 25), 'SR', 1)
    conf[iMPA].upload()  # Push configuration to GLIB
glib.getNode("Configuration").getNode("mode").write(len(assembly) - 1)
conf[iMPA].spi_wait()  # includes dispatch

glib.getNode("Configuration").getNode("num_MPA").write(len(assembly))
# This is a 'write' and pushes the configuration to the glib. Write must
# happen before starting the sequencer.
glib.getNode("Configuration").getNode("mode").write(len(assembly) - 1)
conf[0].spi_wait()  # includes dispatch

if args.external_clock:
    glib.getNode("Control").getNode('testbeam_clock').write(0x1)
else:
    glib.getNode("Control").getNode('testbeam_clock').write(0x0)
glib.getNode("Configuration").getNode("mode").write(len(assembly) - 1)
glib.dispatch()

# shutterDur = 0xFFFFFFFF #0xFFFFFFFF is maximum, in clock cycles
shutterDur = 0xFFFFFF  # 0xFFFFFFFF is maximum, in clock cycles
#shutterDur = 0xF  # 0xFFFFFFFF is maximum, in clock cycles
# Start sequencer in continous daq mode. Already contains the 'write'
mapsaClasses.daq().Sequencer_init(0x1, shutterDur, mem=1)


print """Command Line Configuration
--------------------------
  Clock source is \x1b[1m{0}\x1b[m
  Threshold     = \x1b[1m{1}\x1b[m
  MPA Indices   = \x1b[1m{2}\x1b[m
  Assembly Name = \x1b[1m{3}\x1b[m
  Output Dir    = \x1b[1m{4}\x1b[m
  Num Triggers  = \x1b[1m{5}\x1b[m
""".format("external" if args.external_clock else "internal",
           args.threshold,
           assembly,
           args.assembly,
           os.path.abspath(args.output_dir),
           args.num_triggers,
           )
def acquire(numTriggers, stopDelay=2):
    ibuffer = 0
    shutterCounter = 0
    frequency = float("NaN")
    while True:
        freeBuffers = glib.getNode("Control").getNode(
            'Sequencer').getNode('buffers_num').read()
        glib.dispatch()
        # When set to 4 this produces duplicate entries, 3 (= 2 full buffers)
        # avoids this.
        if freeBuffers < 3:
            if shutterCounter % 2000 == 0:
                startTime = time.time()
                shutterTimeStart = shutterCounter
            if shutterCounter % 100 == 0 and (shutterCounter - shutterTimeStart) >= 0.1:
                frequency = (shutterCounter - shutterTimeStart) / \
                    (time.time() - startTime)
            MAPSACounter = []
            MAPSAMemory = []
            for iMPA, nMPA in enumerate(assembly):
                counterData = glib.getNode("Readout").getNode("Counter").getNode(
                    "MPA" + str(iMPA + 1)).getNode("buffer_" + str(ibuffer+1)).readBlock(25)
                memoryData = glib.getNode("Readout").getNode("Memory").getNode(
                    "MPA" + str(nMPA)).getNode("buffer_" + str(ibuffer+1)).readBlock(216)
                glib.dispatch()
                MAPSACounter.append(counterData)
                MAPSAMemory.append(memoryData)
            ibuffer = (ibuffer + 1) % 4
            shutterCounter += 1
            yield shutterCounter, MAPSACounter, MAPSAMemory, freeBuffers, frequency

            # Continuous operation in bash loop
            if shutterCounter == numTriggers:
                endTimeStamp = time.time()
            # Required for automation! Do not stop DAQ until at least
            # 2 seconds after reaching the num trigger limit
            if shutterCounter > numTriggers:
                if time.time() - endTimeStamp > stopDelay:
                    break

class RippleCounterBranch(Structure):
    _fields_ = [
            ("header", c_uint),
            ("pixels", c_ushort*48)
        ]

class MemoryNoProcessingBranch(Structure):
    _fields_ = [
            ("pixelMatrix", c_ulonglong*96),
            ("bunchCrossingId", c_ushort*96),
            ("header", c_ubyte*96),
            ("numEvents", c_ubyte),
            ("corrupt", c_ubyte),
        ]


def recordPlaintext():
    counterArray = []
    memoryArray = []
    try:
        for shutter, counter, memory, freeBuffers, frequency in acquire(args.num_triggers):
            counterArray.append(counter)
            memoryArray.append(memory)
            print "Shutter counter: %s Free buffers: %s Frequency: %s " % (shutter, freeBuffers, frequency)
    except KeyboardInterrupt:
        pass
    if len(counterArray):
        with open(runNumberFile, 'w') as newRunFile:
            newRunFile.write(str(runNumber + 1))
        print "End of Run %s" % runNumber
        memoryFile = open(os.path.join(
            args.output_dir, 'run%s_memory.txt' % ('{0:04d}'.format(runNumber))), 'w')
        counterFile = open(os.path.join(
            args.output_dir, 'run%s_counter.txt' % ('{0:04d}'.format(runNumber))), 'w')
        for i, shutter in enumerate(counterArray):
            for j, mpa in enumerate(shutter):
                counterFile.write(str(mpa.value()) + "\n")
                memoryFile.write(str(memoryArray[i][j].value()) + "\n")
        counterFile.close()
        memoryFile.close()
        print "All files saved"
    else:
        print "\x1b[1mNo data acquired, ignore.\x1b[m"

def recordRoot():
    spinner = "--\\\\||//"
    progress = ["-"]*20
    filename = os.path.join(args.output_dir,
            args.root_fmt.format(number=runNumber, assembly=args.assembly))
    tFile = TFile(filename, "CREATE")
    with open(runNumberFile, 'w') as newRunFile:
        newRunFile.write(str(runNumber + 1))
    trees = []
    counterFormat = "pixel[48]/s"
    noProcessingFormat = "pixels[96]/l:bunchCrossingId[96]/s:header[96]/b:numEvents/b:corrupt/b"
    flood = [{
        "counter": RippleCounterBranch(),
        "noProcessing": MemoryNoProcessingBranch(),
    }]*len(assembly)
    for i, mpa in enumerate(assembly):
        tree = TTree("mpa{0}".format(mpa), "MPA{0} event tree".format(mpa))
        trees.append(tree)
        tree.Branch("rippleCounter", flood[i]["counter"], counterFormat)
        tree.Branch("memoryNoProcessing", flood[i]["noProcessing"], noProcessingFormat)
    try:
        totalEvents = 0
        for shutter, counters, memories, freeBuffers, frequency in acquire(args.num_triggers):
            for data, tree, counter, memory in zip(flood, trees, counters, memories):
                for i, val in enumerate(itertools.islice(counter, 1, len(counter))):
                    # According to Moritz:
                    # "Mask to select left pixel. First bit is not
                    # considered as this seems sometimes to be set
                    # erronously. (Lots of entries with
                    # 0b1000000000000000)"
                    data["counter"].pixels[i*2 + 0] = val & 0x7FFF # left
                    data["counter"].pixels[i*2 + 1] = (val >> 16) & 0x7FFF # right
                # convert memory from uhal-format to ctype bytes array
                memory_ints = (c_uint*216)(*memory)
                memory_bytes = cast(memory_ints, POINTER(c_ubyte))
                # reset fill array
                data["noProcessing"].pixelMatrix = (c_ulonglong*96)(0)
                data["noProcessing"].bunchCrossingId = (c_ushort*96)(0)
                data["noProcessing"].header = (c_ubyte*96)(0)
                data["noProcessing"].corrupt = c_ubyte(0)
                # iterate over memory in multipletts of 9 bytes (one 72 bit event)
                evtIdx = 0
                numEvents = 0
                for evtIdx in reversed(xrange(0, 96)):
                    evtData = tuple(
                        itertools.islice(memory_bytes,
                            evtIdx*9, evtIdx*9 + 9))
                    data["noProcessing"].header[95-evtIdx] = evtData[8]
                    if data["noProcessing"].header[95-evtIdx] == 0x00:
                        break
                    elif data["noProcessing"].header[95-evtIdx] != 0xFF:
                        data["noProcessing"].corrupt = c_ubyte(evtIdx + 1)
                        break
                    numEvents += 1
                    # bytes 1-8 as 64 bit integer, 1&2 are buch crossing id
                    pixelMatrix = ((evtData[5] << 40) | (evtData[4] << 32) |
                                   (evtData[3] << 24) | (evtData[2] << 16) |
                                   (evtData[1] << 8) | evtData[0])
                    bxid = ((evtData[7] << 8) | evtData[6])
                    data["noProcessing"].bunchCrossingId[95-evtIdx] = bxid
                    data["noProcessing"].pixelMatrix[95-evtIdx] = pixelMatrix
                totalEvents += numEvents
                data["noProcessing"].numEvents = c_ubyte(numEvents)
                tree.Fill()
            # Fancy shmancy visual output
            progress[int(len(progress)*float(shutter)/float(args.num_triggers)) % len(progress)] = "#"
            sys.stdout.write("\r\x1b[K [{3}] Shutter={0}  Free bufs={1}  freq={2:.0f} Hz  #events={6}  [{4}] {5:.0f}%".format(
                shutter, freeBuffers, frequency,
                spinner[shutter % len(spinner)],
                "".join(progress),
                float(shutter) / float(args.num_triggers) * 100,
                totalEvents
            ))
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    sys.stdout.write("\n")
    tFile.Write()
    tFile.Close()
    print "End of Run", runNumber

if args.root:
    recordRoot()
else:
    recordPlaintext()

# nHitMax = 95
# nPixMax = 48
# nMPA = 2

# # Create File

# tFile = TFile("output.root","RECREATE")

# # Initialize trees

# treeMPA1 = TTree("MPA1","MPA1 event tree")
# treeMPA2 = TTree("MPA2","MPA2 event tree")

# nEvents = [array('i',[0]) for x in range(0,nMPA)]
# nHits = [array('i',[0]) for x in range(0,nMPA)]
# headerArray = [array('i',[0 for x in range(0,nHitMax)]) for x in range(0,nMPA)]
# bxArray = [array('i',[0 for x in range(0,nHitMax)]) for x in range(0,nMPA)]
# hitArrayMemory = [array('i',[0 for x in range(0,nPixMax)]) for x in range(0,nMPA)]
# hitArrayCounter = [array('i',[0 for x in range(0,nPixMax)]) for x in range(0,nMPA)]


# print("Hd: %s" %len(headerArray[0]))
# print("Bx: %s" %len(bxArray[0]))
# print("Px: %s" %len(hitArrayMemory[0]))

# treeMPA1.Branch("nEvents", nEvents[0], "nEvents/I")
# treeMPA1.Branch("nHits", nHits[0], "nHits/I")
# treeMPA1.Branch("header", headerArray[0], "header[nHits]/I")
# treeMPA1.Branch("bx", bxArray[0], "bx[nHits]/I")
# treeMPA1.Branch("pixelHits", hitArrayMemory[0], "pixelHits[nHits]/I")
# treeMPA1.Branch("pixelCounter",hitArrayCounter[0],"pixelCounter[nHits]/I")

# treeMPA2.Branch("nEvents", nEvents[1], "nEvents/I")
# treeMPA2.Branch("nHits", nHits[1], "nHits/I")
# treeMPA2.Branch("header", headerArray[1], "header[nHits]/I")
# treeMPA2.Branch("bx", bxArray[1], "bx[nHits]/I")
# treeMPA2.Branch("pixelHits", hitArrayMemory[1], "pixelHits[nHits]/I")
# treeMPA2.Branch("pixelCounter",hitArrayCounter[1],"pixelCounter[nHits]/I")

# ###############

# counter = 0

# for k, event in enumerate(memoryArray):
#     for i,mpa in enumerate(event):

#         #############################################
#         ### Counter: Array[24] -> Array[48] (int) ###
#         #############################################
#         counterData = []

#         for x in range(1,len(counterArray[k][i])): # Skip header at [0]
#             counterData.append(counterArray[k][i][x] & 0x7FFF) # Mask to select left pixel. First bit is not considered as this seems sometimes to be set erronously. (Lots of entries with 0b1000000000000000)
# counterData.append((counterArray[k][i][x] >> 16) & 0x7FFF) # Mask to
# select right pixel. Same as above.

#         ##########################################################################################
#         ### Memory: 216x  32-Bit Words -> Array of Hits (Header,BunchCrossing,Pixarray) (Bits) ###
#         ##########################################################################################

#         # Mem integer array to binary string in readable order (header,bx,pix)
#         binMemStr= ""
#         for j in range(0,216):
#             binMemStr = binMemStr + '{0:032b}'.format(mpa[215-j])

#         # String to binary array
#         binMem = [binMemStr[x:x+72] for x in range(0,len(binMemStr),72)]

#         # Get elements of binary string
#         hd = []
#         bx = []
#         pix = []

#         for entry in binMem[:-1]: # Discard last entry in memory as here the 48th - pixel is always showing a hit, even if pixel is disabled. This is intended as a workaround, the maximum number of hits per pixel and memory is now 95.
#             hd.append(entry[:8])
#             bx.append(entry[8:24])
#             pix.append(entry[24:])

#         #####################################################################

#         # Tree stuff

#         nHitsTmp = 0
#         for hit in hd:
#             if hit == "11111111":
#                 nHitsTmp+=1

#         nHits[i][0] = 95
#         headerArray[i]=[int(ihd,2) for ihd in hd]
#         bxArray[i]=[int(ibx,2) for ibx in bx]
#         hitArrayMemory[i]=pix
#         hitArrayCounter[i]=counterData


#     treeMPA1.Fill()
#     treeMPA2.Fill()

# tFile.Write()
# tFile.Close()
