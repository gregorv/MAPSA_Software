from MPACalibration import MPACalibration
from MPAPlot import MPAPlot
from ROOT import TCanvas,TFile, TLine, gStyle, TDirectory

assembly = [2,5]
gStyle.SetOptFit()
rootFile = TFile("plots_kit/Threshold_scan_before_and_after_calibration.root", "recreate")

calibration = MPACalibration(assembly)
calibration.thresholdScan(calEnbl = 1, calNum = 5000)

counter, mem = calibration.getThrScanPerPix()
_,_,threshold = calibration.getThrScanMetadata()
for nMPA, MPA in enumerate(assembly):
    mpaDir = rootFile.mkdir("Threshold scans before calibration with MPA "+str(MPA), "Threshold scans before calibration with MPA "+str(MPA))
    plot = MPAPlot()
    for pix in counter[nMPA]:
        plot.createGraph(threshold[nMPA], pix)
    plot.setTitle('MPA ' + str(MPA) + ' threshold scan before calibration; Threshold (DAC);Number of Hits')
    plot.draw()
    graphList = plot.getPlot()
    for graph in graphList:
        mpaDir.Add(graph)
    mpaDir.Write()

edgesBeforeCal = calibration.findFallingEdges()
trimDac = calibration.getTrimBits(minimize = False)
calibration.writeCalibrationToMPA(trimDAC = trimDac)

for nMPA, MPA in enumerate(assembly):
    plot = MPAPlot()
    plot.fillHisto(edgesBeforeCal[nMPA] )
    plot.fitHisto()
    plot.setTitle('Falling edges of MPA '+str(MPA)+' before calibration; Threshold (DAC); Number of Pixels')
    plot.draw()
    histo = plot.getPlot(0) 
    histo.Write()


calibration.thresholdScan(calEnbl = 1, calNum = 5000)
counter, mem = calibration.getThrScanPerPix()
_,_,threshold = calibration.getThrScanMetadata()

for nMPA, MPA in enumerate(assembly):
    mpaDir = rootFile.mkdir("Threshold scans after calibration with MPA "+str(MPA), "Threshold scans after calibration with MPA "+str(MPA))

    plot = MPAPlot()
    for pix in counter[nMPA]:
        plot.createGraph(threshold[nMPA], pix)
    plot.setTitle('MPA ' + str(MPA) + ' threshold scan after calibration on thld ' + str(min(edgesBeforeCal[nMPA])) + '; Threshold (DAC);Number of Hits')

    graphList = plot.getPlot()
    for graph in graphList:
        mpaDir.Add(graph)
            
    c1 = TCanvas("hist", "hist", 1024, 768) 
    c1.cd()
    for i,graph in enumerate(graphList):
        if i == 0:
            graph.Draw("APL")
        else:
            graph.Draw("PL")


    # Add line for edge on which was trimmed
    line = TLine(min(edgesBeforeCal[nMPA]), 0, min(edgesBeforeCal[nMPA]), 5000)
    line.SetLineColor(2)
    line.Draw()
    mpaDir.Add(line)

    mpaDir.Write()
    
    raw_input() 

edgesAfterCal = calibration.findFallingEdges()

for nMPA, MPA in enumerate(assembly):
    plot = MPAPlot()
    plot.fillHisto(edgesAfterCal[nMPA] )
    plot.fitHisto()
    plot.setTitle('Falling edges of MPA '+str(MPA)+' after calibration; Threshold (DAC); Number of Pixels')
    histo = plot.getPlot(0) 
    histo.Write()
    plot.draw()
    


for nMPA, MPA in enumerate(assembly):
    plot = MPAPlot()
    plot.fillHisto(trimDac[nMPA], 0, 30)
    plot.fitHisto()
    plot.setTitle('TrimDACs of MPA '+str(MPA)+' after calibration; Trim (DAC); Number of Pixels')
    histo = plot.getPlot(0) 
    histo.Write()
    plot.draw()

rootFile.Close()
