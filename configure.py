from classes import *
import sys, select, os, array
from array import array
from optparse import OptionParser

parser = OptionParser()


parser.add_option('-s', '--setting', metavar='F', type='string', action='store', 
default	=	'default',
dest	=	'setting',
help	=	'configuration setting (e.g. default, calibrated)')

parser.add_option('-n', '--number', metavar='F', type='int', action='store',
default	=	1,
dest	=	'number',
help	=	'configuration number (e.g. 1, 2, ..)')

parser.add_option('-m', '--mpa', metavar='F', type='int', action='store',
default	=	0,
dest	=	'mpa',
help	=	'mpa to configure (0 for all)')

(options, args) = parser.parse_args()

# Create MAPSA object
a = uasic(connection="file://connections_test.xml",device="board0")
mapsa = MAPSA(a)
read = a._hw.getNode("Control").getNode('firm_ver').read()
a._hw.dispatch()
print "Running firmware version " + str(read)

mpa_number = options.mpa
if mpa_number ==0: # all MPAs
	config = mapsa.config(Config=options.number,string=options.setting)  
	config.upload(show = 0) # upload configuration to all MPAs
	config.write() # set cfg mode and write changes
	print ""
	print "checking config"
	for i in range(1,7):
		print i
       		read = a._hw.getNode("Configuration").getNode("Memory_OutConf").getNode("MPA"+str(i)).getNode("config_1").read()	
		a._hw.dispatch()
		print read
else: # single MPA
	mpa_index = mpa_number-1
	
	mpa = []  
	for i in range(1,7):
		mpa.append(mapsa.getMPA(i))

	Confnum=options.number
	configarr = []

	writesetting=6-mpa_number

	print "Configuring MPA number " + str(mpa_number)

	curconf = mpa[mpa_index].config(xmlfile="data/Conf_"+options.setting+"_MPA"+str(mpa_number)+"_config"+str(Confnum)+".xml")
	curconf.upload()
	a._hw.dispatch() # ??? why not curconf.write()
	
	print ""
	print "Done"
