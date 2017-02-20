import pickle
import sys
from ROOT import TGraph, TCanvas, TLine, TF1
from array import array

pxlTrimFallingEdge = pickle.load(open(str(sys.path[0])+"/trimDacFallingEdge.pickle","r"))
# Draw graphs on canvas
c1 = TCanvas("graph","graph",1024,768)
c1.SetGrid()

graphs = []
for pxl in pxlTrimFallingEdge:
    graphs.append(TGraph(32,array('d',range(32)),array('d',pxl))) # Generate graph with trimDACs on x-axis and falling edge position (in threshold-steps) on y-axis

fitFunc = TF1("fa1","[0]+x*[1]",0,32)
fitvals = []
for i,graph in enumerate(graphs):
    graph.SetLineColor(i+1) 
    graph.SetMarkerStyle(8)
    if i==0:
        fitFunc.SetName("Fit for pixel "+str(i+1))
        result = graph.Fit(fitFunc.GetName(), "S")
        graph.SetTitle('Trim Scan;Trim (DAC);Falling Edge (Threshold)')
        graph.GetYaxis().SetRangeUser(0,255)
        graph.Draw("APL")
    else:
        fitFunc.SetName("Fit for pixel "+str(i+1))
        result = graph.Fit(fitFunc.GetName(), "S")
        graph.SetTitle('Pixel ' +str(i+1))
        graph.GetYaxis().SetRangeUser(0,255)
        graph.Draw("PL")
    fitvals.append(result.Parameter(1))

fitvals = sorted(enumerate(fitvals, start=1), key=lambda x: x[1])
for i, fit in fitvals:
    print "Pixel %s with %s" %(i,'{0:.3f}'.format(fit))

raw_input("Press any key to exit")
