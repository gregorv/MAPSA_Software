from ROOT import TCanvas, TH1F, gStyle, TAxis  

iMPA =1 

gStyle.SetOptFit()

# Load falling edges from threshold scan after trimming and convert to int
fallingEdges = open('data/fallingEdgeTrimmed_MPA'+str(iMPA+1)).read().splitlines()
fallingEdges = [int(edge) for edge in fallingEdges]


histData = [[edge,fallingEdges.count(edge)] for edge in set(fallingEdges)] # Calculate how often each number of hits occurs

histo = TH1F("h1","Falling edges after trimming for MPA " +str(iMPA+1), max(fallingEdges), 0, max(fallingEdges))
for threshold in histData:
    for i in range(0,threshold[1]):
        histo.Fill(threshold[0])

XRange = int(histo.GetMean() * 2)
histo.SetBins(XRange, 0, XRange)
histo.GetYaxis().SetTitle("Number of pixels")
histo.GetXaxis().SetTitle("Threshold value for falling edge")

c1 = TCanvas("hist", "hist", 1024, 768) 
c1.cd()

# Gauss fit
fit = histo.Fit("gaus")
histo.Draw()

c1.Print('plots/fallingEdgeHistogram_MPA'+str(iMPA+1)+'.pdf', 'pdf')
raw_input()
