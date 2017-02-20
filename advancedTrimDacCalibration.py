from MPACalibration import MPACalibration
from MPAPlot import MPAPlot
from ROOT import gStyle, TGraph, TCanvas, TLine, TF1, TFile
import xml.etree.ElementTree as ET

assembly = [2,5]
calibration = MPACalibration(assembly)
mpaConfig = []  

for MPA in assembly:
    mpaConfig.append(ET.parse("data/Conf_default_MPA"+str(MPA)+"_config1.xml")) # Construct list of XML files, one for each MPA

calibration.thresholdScan(calEnbl = True)
calibration.writeCalibrationToMPA()

calibration.thresholdScan()
counter, _ = calibration.getThrScanPerPix()
preScanEdges = calibration.findFallingEdges()

rootFile = TFile("plots_kit/Trim_Scan_results.root", "recreate")

RMS = []

for iMPA, edge in enumerate(preScanEdges):
    plot = MPAPlot()
    plot.fillHisto(edge)
    plot.setTitle('Falling edges of MPA ' + str(assembly[iMPA]) + ' after calibration with fixed ThrDAC/TrimDAC-ratio; Threshold (DAC);# of Pixels')
    plot.draw()
    histo = plot.getPlot(0)
    RMS.append(histo.GetRMS())
    histo.Write()
    

calibration.trimScan(resolution = 1)

trimScanEdges = calibration.getTrimScanEdges() # MPA[trim[pix]]
trimArray = calibration.getTrimScanMetadata()

fitvalsMPA = []
for nMPA, MPA in enumerate(trimScanEdges):
    MPA = [list(pix) for pix in zip(*MPA)] #Turn trim[pix] into pix[trim] for easier plotting
    plot = MPAPlot()
    for pix in MPA: 
        plot.createGraph(trimArray, pix)
    plot.draw()

    graphs = plot.getPlot()
    fitFunc = TF1("fa1","[0]+x*[1]",0,32)
    fitvals = []
    mpaDir = rootFile.mkdir("Edges vs Trim "+str(assembly[nMPA]), "Edges vs Trim"+str(assembly[nMPA]))
    print graphs
    for i,graph in enumerate(graphs):
        graph.SetLineColor(i+1) 
        graph.SetMarkerStyle(8)
        fitFunc.SetName("Fit for pixel "+str(i+1))
        result = graph.Fit(fitFunc.GetName(), "S")
        graph.GetYaxis().SetRangeUser(0,255)
        graph.GetXaxis().SetRangeUser(0,220)
        if i==0:
            graph.SetTitle('Trim Scan of MPA '+str(assembly[nMPA])+';Trim (DAC);Falling Edge (Threshold)')
            mpaDir.Add(graph)
            graph.Draw("APL")
        else:
            graph.SetTitle('Pixel ' +str(i+1))
            mpaDir.Add(graph)
            graph.Draw("PL")
        fitvals.append(1/result.Parameter(1))

    mpaDir.Write()
    raw_input("Press any key to proceed")
    fitvalsMPA.append(fitvals)

for MPA in fitvalsMPA:
    plot = MPAPlot()
    plot.fillHisto(MPA, 0.3, 0.5, 50)
    plot.setTitle("Ratio of ThrDAC and TrimDAC; Ratio; Number of Pixels")
    plot.draw()
    histo = plot.getPlot(0)
    histo.Write()

calibration.thresholdScan(calEnbl = True)

trimDac = calibration.getTrimBits(ratioThrTrim = fitvalsMPA)

calibration.writeCalibrationToMPA(trimDAC = trimDac)

for iMPA, MPAtree in enumerate(mpaConfig): # loop over configs for individual MPAs
    MPA = MPAtree.getroot()
    for iPix,pixel in enumerate(MPA.findall('pixel')):
        pixel.find('TRIMDACL').text = str(trimDac[iMPA][2*iPix])
        pixel.find('TRIMDACR').text = str(trimDac[iMPA][2*iPix+1])
        if pixel.find('THRTRIMRATIOL') is None:
            ET.SubElement(pixel, 'THRTRIMRATIOL')
        if pixel.find('THRTRIMRATIOR') is None:
            ET.SubElement(pixel, 'THRTRIMRATIOR')
        pixel.find('THRTRIMRATIOL').text = '{0:.5}'.format(str(fitvalsMPA[iMPA][2*iPix]))
        pixel.find('THRTRIMRATIOR').text = '{0:.5}'.format(str(fitvalsMPA[iMPA][2*iPix + 1 ]))
    
    MPAtree.write('data/Conf_trimcalib_MPA'+str(assembly[iMPA])+'_config1.xml')


calibration.thresholdScan()

counter, _ = calibration.getThrScanPerPix()
postScanEdges =  calibration.findFallingEdges()

for mpa in counter:
    plot = MPAPlot()
    for pix in mpa:
        plot.createGraph(range(0,255), pix)
    graphs = plot.getPlot()
    for i, graph in enumerate(graphs):
        graph.SetTitle('Pixel ' +str(i+1))
        if i == 0:
            graph.Draw("APL")
        else:
            graph.Draw("PL")
    
raw_input()

for iMPA,edge in enumerate(postScanEdges):
    plot = MPAPlot()
    plot.fillHisto(edge)
    plot.setTitle('Falling edges of MPA ' + str(assembly[iMPA]) + ' after calibration with ThrDAC/TrimDAC-ratios from trim scan; Threshold (DAC);# of Pixels')
    histo = plot.getPlot(0)
    RMS.append(histo.GetRMS())
    histo.Write()
    plot.draw()
rootFile.Close()

print trimDac

print "Root mean squares before trim scan: %s and %s. Root mean squares after trim scan: %s and %s." %(RMS[0], RMS[1], RMS[2], RMS[3])
