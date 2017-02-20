import sys
from classes import *
from array import array
from optparse import OptionParser

# Connection and GLIB 
a = uasic(connection="file://connections_test.xml",device="board0")
glib = a._hw

single = True

# Get all 6 MPAs and corresponding configs
mpa=[]
conf=[]

for i in range(0,6):
    mpa.append(MPA(a._hw,i+1))
    conf.append(mpa[i].config("data/Conf_default_MPA" + str(i+1) +"_config1.xml"))
    conf[i].clean_conf()
    conf[i].upload(1)
    glib.dispatch()
    
#conf[confMPA-1].upload(1)
#glib.dispatch()
    
# Define MPA (1-6) (nMPA 2 or 5 for double assembly)

confMPA = 1
#readMPA = 
mode = 0x5

print 'confMPA'
print confMPA
#print 'readMPA'
#print readMPA
print 'Mode'
print mode

glib.getNode("Control").getNode("logic_reset").write(0x1)
glib.dispatch()

# Before write
dataConf = []
for impa in range(1,7):
    dataConf.append(glib.getNode("Configuration").getNode("Memory_DataConf").getNode("MPA"+str(impa)).getNode("config_1").readBlock(0x19))

glib.dispatch()

print "\nDataConf before write: \n"
for impa in range(1,7):
    print("MPA"+str(impa)+":\n %s" %dataConf[impa-1])

#a = glib.getNode("Configuration").getNode("Memory_DataConf").getNode("MPA"+str(readMPA)).getNode("config_1").readBlock(0x19)
#glib.dispatch()
#print("Dataconf:\n %s \n" %a)

outConf = []
for impa in range(1,7):
    outConf.append(glib.getNode("Configuration").getNode("Memory_OutConf").getNode("MPA"+str(impa)).getNode("config_1").readBlock(0x19))
glib.dispatch()

print "\nOutConf before write\n"
for impa in range(1,7):
    print("MPA"+str(impa)+":\n %s" %outConf[impa-1])

# WRITE Config
glib.getNode("Configuration").getNode("num_MPA").write(0x2)
glib.getNode("Configuration").getNode("mode").write(mode)
glib.dispatch()

# Wait for SPI
busy = glib.getNode("Configuration").getNode("busy").read()
glib.dispatch()
while busy:
    time.sleep(0.001)
    busy = glib.getNode("Configuration").getNode("busy").read()
    glib.dispatch()

dataConf = []
for impa in range(1,7):
    dataConf.append(glib.getNode("Configuration").getNode("Memory_DataConf").getNode("MPA"+str(impa)).getNode("config_1").readBlock(0x19))

glib.dispatch()

print "\nDataConf after write\n"
for impa in range(1,7):
    print("MPA"+str(impa)+":\n %s" %dataConf[impa-1])

#a = glib.getNode("Configuration").getNode("Memory_DataConf").getNode("MPA"+str(readMPA)).getNode("config_1").readBlock(0x19)
#glib.dispatch()
#print("Dataconf:\n %s \n" %a)

outConf = []
for impa in range(1,7):
    outConf.append(glib.getNode("Configuration").getNode("Memory_OutConf").getNode("MPA"+str(impa)).getNode("config_1").readBlock(0x19))
glib.dispatch()

print "\nOutConf after write\n"
for impa in range(1,7):
    print("MPA"+str(impa)+":\n %s" %outConf[impa-1])

#b =  glib.getNode("Configuration").getNode("Memory_OutConf").getNode("MPA"+str(readMPA)).getNode("config_1").readBlock(0x19)
#glib.dispatch()
#print("MemConf:\n %s \n" %b)

print "\n"

#conf[confMPA-1].upload(1)
#glib.dispatch()


# Wait for SPI
busy = glib.getNode("Configuration").getNode("busy").read()
glib.dispatch()
while busy:
    time.sleep(0.001)
    busy = glib.getNode("Configuration").getNode("busy").read()
    glib.dispatch()
    print busy


#c =  glib.getNode("Configuration").getNode("Memory_OutConf").getNode("MPA"+str(readMPA)).getNode("config_1").readBlock(0x19)
#glib.dispatch()
#print("MemConf:\n %s \n" %c)

raw_input("Press any key to exit")

