import sys
from ROOT import TH2F, TCanvas, gStyle, TAxis

class MPAPlot:
    
    def __init__(self):
        
        self.plot = None
        
    def pixelHits(self, hitArray):    

        gStyle.SetOptStat(0)
        gStyle.SetPalette(55)

        x = [ix for ix in range(0,16)]
        y = [0,1,2]
        
        hits = []

        if len(hitArray) is 48:
            hits.append(hitArray[:16])
            hits.append(list(reversed(hitArray[16:32])))
            hits.append(hitArray[32:])
        else:
            sys.exit("Hit array must contain 48 entries")
        
        histo = TH2F("h1","HitMap",16,0.5,16.5,3,0.5,3.5)
        
        for iy in y:
            for ix in x:                
                for iHit in range(0,hits[iy][ix]):
                    histo.Fill(ix+0.5,iy+0.5)

        histo.GetYaxis().SetNdivisions(3)
                    
        self.plot = histo
        return self.plot

    def draw(self):

        c1 = TCanvas("c1", "Canvas", 768, 1280)
        c1.SetRightMargin(0.15)
        c1.cd()
        self.plot.Draw("colz")
        
        raw_input()
        
if __name__ == "__main__":

    plot = MPAPlot()
    if len(sys.argv)>1:
        hits = sys.argv[1]
    else:
        #hits = [80, 40, 44, 43, 30, 34, 0, 46, 0, 64, 0, 75, 0, 0, 59, 108, 88, 27, 25, 38, 34, 30, 39, 28, 23, 30, 28, 30, 35, 35, 31, 54, 61, 28, 31, 30, 35, 41, 41, 0, 43, 0, 48, 38, 40, 36, 35, 83]
        hits = [89, 32, 33, 49, 35, 34, 28, 38, 55, 37, 38, 35, 25, 22, 43, 92, 70, 35, 35, 31, 22, 23, 21, 24, 23, 32, 26, 31, 34, 39, 45, 103, 107, 42, 41, 29, 21, 30, 27, 33, 30, 34, 34, 24, 28, 44, 41, 63]
    plot.pixelHits(hits)
    plot.draw()
