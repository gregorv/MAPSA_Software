from ROOT import TH1F, TCanvas, TAxis, gStyle, gPad

gStyle.SetOptFit()
numMPA = 2 # Number of installed MPAs

c1 = TCanvas("hist", "hist", 1024, 768) 
c1.Divide(2)

histo = []
for iMPA in range(0, numMPA):
    c1.cd(iMPA+1)
    memory = open('data/asynchronous_data_noise_MPA'+str(iMPA+1)).read().splitlines()
    threshold = int(memory[1])
    events = [int(event) for event in memory[3:]] # Skip first 3 lines, here the threshold is stored
    
    histData = [[hits,events.count(hits)] for hits in set(events)] # Calculate how often each number of hits occurs
    print histData
    
    histo.append(TH1F("h1","Common noise analysis for MPA" +str(iMPA+1)+" at Threshold "+ str(threshold), max(events), 0, max(events)))
    for hits in histData:
        for i in range(0,hits[1]):
            histo[iMPA].Fill(hits[0])
    
    XRange = int(histo[iMPA].GetMean() * 2)
    histo[iMPA].SetBins(XRange, 0, XRange)
    histo[iMPA].GetYaxis().SetTitle("Number of events")
    histo[iMPA].GetXaxis().SetTitle("Number of hits")
    
    # Gauss fit
    fit = histo[iMPA].Fit("gaus")
    histo[iMPA].Draw()
    gPad.Update()

c1.Print('plots/common_noise_counter.pdf', 'pdf')
raw_input()
