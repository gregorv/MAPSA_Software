import sys
from classes import *

# Connection and GLIB 
a = uasic(connection="file://connections_test.xml",device="board0")
glib = a._hw

# Define MPA (1-6) (nMPA 2 or 5 for double assembly)
mpaDict = {0:2,1:5}
iMPA = 1

# Get all 6 MPAs and corresponding configs
# TODO: break down to two MPAs
mapsa = MAPSA(a)

mpa=[]
conf=[]

for i in range(0,6):
    mpa.append(MPA(a._hw,i+1))
    conf.append(mpa[i].config("data/Default_MPA.xml"))

# Set number of MPAs and start clock
glib.getNode("Control").getNode("MPA_clock_enable").write(0x1)
glib.getNode("Configuration").getNode("num_MPA").write(0x2)
glib.getNode("Configuration").getNode("mode").write(0x1)
glib.dispatch()

# Configure both MPAs
# TODO: break down to two MPAs

CE = 0

config = mapsa.config(Config=1,string='default')
config.upload()
confdict = {'OM':[3]*6,'RT':[0]*6,'SCW':[0]*6,'SH2':[0]*6,'SH1':[0]*6,'THDAC':[0]*6,'CALDAC':[30]*6,'PML':[1]*6,'ARL':[1]*6,'CEL':[CE]*6,'CW':[0]*6,'PMR':[1]*6,'ARR':[1]*6,'CER':[CE]*6,'SP':[0]*6,'SR':[1]*6,'TRIMDACL':[30]*6,'TRIMDACR':[30]*6}
config.modifyfull(confdict) 


#################
### START DAQ ###
#################

i=1

while True:
    i+=1

    glib.getNode("Shutter").getNode("time").write(0xFFFF)
    glib.getNode("Control").getNode("Sequencer").getNode("datataking_continuous").write(0x0)
#    glib.getNode("Control").getNode("readout").write(1)
    glib.dispatch()



    print i 
