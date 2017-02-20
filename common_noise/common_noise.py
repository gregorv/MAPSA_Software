from ROOT import TH2S, TCanvas, TAxis, gStyle
from MPAPlot import MPAPlot

MPANum = 4 # Number of MPA, 0-indexed
memory = [event for event in open('data/synchronous_data_noise_MPA'+str(MPANum+1)).read().splitlines() if event] # Reads events from file and skips empty lines after each shutter
plot = MPAPlot()

memoryArray =[]
for event in memory:
    eventArray = []
    for pix in event:
        eventArray.append(int(pix)) 
    memoryArray.append(eventArray)

hitsPerPixel = [sum(pix) for pix in zip(*memoryArray)]

plot.createHisto(hitsPerPixel, 0, len(hitsPerPixel), len(hitsPerPixel))   

plot.draw()
