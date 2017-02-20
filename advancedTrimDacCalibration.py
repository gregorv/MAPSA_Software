from MPACalibration import MPACalibration
from MPAPlot import MPAPlot
import xml.etree.ElementTree as ET
import argparse
import errno
import os

parser = argparse.ArgumentParser(description="MaPSA DAQ")
parser.add_argument("--assembly", "-a", metavar="NAME",
                    help="Name of the assembly, used to differentiate trimming configurations", default="default")
parser.add_argument("--mpa-index", "-i", metavar="IDX", type=int, choices=range(1, 7),
                    action="append", help="Specify the indices of the MPAs in the SPI chain", default=[])
parser.add_argument("--config", "-c", metavar="FILEFORMAT",
                    help="Filename format string for trimming and masking MPA configuration. The variables {assembly} and {mpa} are available.", default="Conf-{assembly}_MPA-{mpa}.xml")
parser.add_argument("--config-dir", metavar="DIR", default="data/", help="Configuration directory.")
parser.add_argument("--force", "-f", default="false", action="store_true", help="Force overriding of existing trim configurations.")

args = parser.parse_args()

# Importing ROOT before parsing argument messes up the help output. Well
# done, root.
from ROOT import gStyle, TGraph, TCanvas, TLine, TF1, TFile

if args.mpa_index:
    assembly = list(sorted(args.mpa_index))
else:
    assembly = [2, 5]
calibration = MPACalibration(assembly)
mpaConfig = []

print """Command Line Configuration
--------------------------
  MPA Indices   = \x1b[1m{0}\x1b[m
  Assembly Name = \x1b[1m{1}\x1b[m
""".format(assembly,
           args.assembly,
           )

for MPA in assembly:
    # Construct list of XML files, one for each MPA
    filename = os.path.join(args.config_dir,
        args.config.format(mpa=MPA, assembly=args.assembly))
    if os.path.exists(filename):
        if args.force:
            print "WARNING! Overwrite existing config {0}!".format(filename)
        else:
            args.error("Configuration file {0} exists. Please use --force or delete the file.")
    mpaConfig.append(filename)

calibration.thresholdScan(calEnbl=True)
calibration.writeCalibrationToMPA()

calibration.thresholdScan()
counter, _ = calibration.getThrScanPerPix()
preScanEdges = calibration.findFallingEdges()

rootFile = TFile("plots_kit/Trim_Scan_results.root", "recreate")

RMS = []

for iMPA, edge in enumerate(preScanEdges):
    plot = MPAPlot()
    plot.fillHisto(edge)
    plot.setTitle('Falling edges of MPA ' + str(assembly[
                  iMPA]) + ' after calibration with fixed ThrDAC/TrimDAC-ratio; Threshold (DAC);# of Pixels')
    plot.draw()
    histo = plot.getPlot(0)
    RMS.append(histo.GetRMS())
    histo.Write()


calibration.trimScan(resolution=1)

trimScanEdges = calibration.getTrimScanEdges()  # MPA[trim[pix]]
trimArray = calibration.getTrimScanMetadata()

fitvalsMPA = []
for nMPA, MPA in enumerate(trimScanEdges):
    # Turn trim[pix] into pix[trim] for easier plotting
    MPA = [list(pix) for pix in zip(*MPA)]
    plot = MPAPlot()
    for pix in MPA:
        plot.createGraph(trimArray, pix)
    plot.draw()

    graphs = plot.getPlot()
    fitFunc = TF1("fa1", "[0]+x*[1]", 0, 32)
    fitvals = []
    mpaDir = rootFile.mkdir(
        "Edges vs Trim " + str(assembly[nMPA]), "Edges vs Trim" + str(assembly[nMPA]))
    print graphs
    for i, graph in enumerate(graphs):
        graph.SetLineColor(i + 1)
        graph.SetMarkerStyle(8)
        fitFunc.SetName("Fit for pixel " + str(i + 1))
        result = graph.Fit(fitFunc.GetName(), "S")
        graph.GetYaxis().SetRangeUser(0, 255)
        graph.GetXaxis().SetRangeUser(0, 220)
        if i == 0:
            graph.SetTitle(
                'Trim Scan of MPA ' + str(assembly[nMPA]) + ';Trim (DAC);Falling Edge (Threshold)')
            mpaDir.Add(graph)
            graph.Draw("APL")
        else:
            graph.SetTitle('Pixel ' + str(i + 1))
            mpaDir.Add(graph)
            graph.Draw("PL")
        fitvals.append(1 / result.Parameter(1))

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

calibration.thresholdScan(calEnbl=True)

trimDac = calibration.getTrimBits(ratioThrTrim=fitvalsMPA)

calibration.writeCalibrationToMPA(trimDAC=trimDac)

# loop over configs for individual MPAs
for iMPA, MPAtree in enumerate(mpaConfig):
    MPA = MPAtree.getroot()
    for iPix, pixel in enumerate(MPA.findall('pixel')):
        pixel.find('TRIMDACL').text = str(trimDac[iMPA][2 * iPix])
        pixel.find('TRIMDACR').text = str(trimDac[iMPA][2 * iPix + 1])
        if pixel.find('THRTRIMRATIOL') is None:
            ET.SubElement(pixel, 'THRTRIMRATIOL')
        if pixel.find('THRTRIMRATIOR') is None:
            ET.SubElement(pixel, 'THRTRIMRATIOR')
        pixel.find('THRTRIMRATIOL').text = '{0:.5}'.format(
            str(fitvalsMPA[iMPA][2 * iPix]))
        pixel.find('THRTRIMRATIOR').text = '{0:.5}'.format(
            str(fitvalsMPA[iMPA][2 * iPix + 1]))

    MPAtree.write('data/Conf_trimcalib_MPA' +
                  str(assembly[iMPA]) + '_config1.xml')


calibration.thresholdScan()

counter, _ = calibration.getThrScanPerPix()
postScanEdges = calibration.findFallingEdges()

for mpa in counter:
    plot = MPAPlot()
    for pix in mpa:
        plot.createGraph(range(0, 255), pix)
    graphs = plot.getPlot()
    for i, graph in enumerate(graphs):
        graph.SetTitle('Pixel ' + str(i + 1))
        if i == 0:
            graph.Draw("APL")
        else:
            graph.Draw("PL")

raw_input()

for iMPA, edge in enumerate(postScanEdges):
    plot = MPAPlot()
    plot.fillHisto(edge)
    plot.setTitle('Falling edges of MPA ' + str(assembly[
                  iMPA]) + ' after calibration with ThrDAC/TrimDAC-ratios from trim scan; Threshold (DAC);# of Pixels')
    histo = plot.getPlot(0)
    RMS.append(histo.GetRMS())
    histo.Write()
    plot.draw()
rootFile.Close()

print trimDac

print "Root mean squares before trim scan: %s and %s. Root mean squares after trim scan: %s and %s." % (RMS[0], RMS[1], RMS[2], RMS[3])
