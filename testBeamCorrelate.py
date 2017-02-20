from MPAPlot import MPAPlot
import sys
from testBeamAnalysis import TBAnalysis

tb = TBAnalysis()


axis = sys.argv[3]

# Input

if len(sys.argv) == 5:
    offset = int(sys.argv[4])
elif len(sys.argv) == 6:
    offset = range(int(sys.argv[4]),int(sys.argv[5])+1)
else:
    offset = 0 

dutRaw = tb.parseFile(sys.argv[1])
refArray = tb.parseFile(sys.argv[2])

dutArray = tb.convertFormat(dutRaw, axis) 

plot = MPAPlot()

# Plot
if isinstance(offset,int):
    plot.createCorrelationPlot(dutArray, refArray, axis , offset) 
    plot.draw()
else:
    for iOff in offset:
        plot.createCorrelationPlot(dutArray, refArray, axis , iOff) 
    plot.save("output/correlations")

