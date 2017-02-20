#!/usr/bin/python
import sys
import ROOT

class MPAPlot(object):

    def __init__(self):
        ROOT.gStyle.SetPalette(55)
        self.__plots = []
        
    def createHitMap(self, hitArray):
        
        x = [ix for ix in range(0,16)]
        y = [0,1,2]
        
        hits = []
        
        if len(hitArray) is 48:
            hits.append(hitArray[:16])
            hits.append(list(reversed(hitArray[16:32])))
            hits.append(hitArray[32:])
        else:
            sys.exit("Hit array must contain 48 entries")

        histo = ROOT.TH2F("h1","HitMap",16,0.5,16.5,3,0.5,3.5)
        mask = [(12,1)]
        mask = []

        for iy in y:
            for ix in x:
                masked = False
                for m in mask:
                    if ix == m[0] and iy == m[1]:
                        masked = True
                        break
                if masked:
                    continue
                binNo = histo.FindBin(ix+0.5, iy+0.5)
                histo.SetBinContent(binNo, hits[iy][ix])
        histo.Rebuild()
        histo.GetYaxis().SetNdivisions(3)

        self.__plots.append(histo)

    def createCorrelationPlot(self, mpa, ref, axis, offset=0):
        
        if axis == "Y":
            histo = ROOT.TH2F("h1",axis + " Correlation of MPA and REF ;MPA (DUT); REF",3,0.5,3.5,80,0.5,80.5)
        else:
            histo = ROOT.TH2F("h1",axis + " Correlation of MPA and REF ;MPA (DUT); REF",16,0.5,16.5,52,0.5,52.5)

        for iEvent,event in enumerate(ref):
            for refHit in event:
               if iEvent+offset < len(mpa) and iEvent+offset > 0: 
                    for mpaHit in range(len(mpa[iEvent+offset])):
                        histo.Fill(mpa[iEvent+offset][mpaHit]+0.5, refHit+0.5)

        self.__plots.append(histo)
        
    def fillHisto(self, hitArray, xMin=0, xMax=255, nBins=255):
         
        histo = ROOT.TH1F("h1","Histogram",nBins,xMin,xMax)

        for hit in hitArray:
            histo.Fill(hit)

        self.__plots.append(histo)
            
    def createHisto(self, hitArray, xMin=0, xMax=255, nBins=255):
       
        histo = ROOT.TH1F("h1","Histogram",nBins,xMin,xMax)

        for ibin, hit in enumerate(hitArray):
            histo.SetBinContent(ibin,hit)

        self.__plots.append(histo)

    def fitHisto(self, fitparam = "gaus"):
        for plot in self.__plots:
            if isinstance(plot, ROOT.TH1F):
                result = plot.Fit(fitparam, "S") 
            else:
                print "Not a TH1F histogram"
                return False
        return result 
            
    def createGraph(self, x, y):

        if isinstance(x,list) or isinstance(y, list): 
            from array import array 
            if isinstance(x,list): 
                x = array('d',x)
            if isinstance(y,list): 
                y = array('d',y)

        self.__plots.append(ROOT.TGraph(len(x),x,y))
            
    def getPlot(self, iPlot=None):

        if iPlot is None:
            return self.__plots
        else:
            return self.__plots[iPlot]
        
    def draw(self, arg="APL", name="c1"):

        if isinstance(self.__plots[0],ROOT.TH2F):
            c1 = ROOT.TCanvas(name, "Canvas", 600, 800)
        else:
            c1 = ROOT.TCanvas(name, "Canvas", 800, 600)
        c1.cd()
        ROOT.gPad.SetLogz(True)
        
        if isinstance(self.__plots[0],ROOT.TH2F):
            c1.SetRightMargin(0.15)
            for plot in self.__plots:
                plot.Draw("colz")
        elif isinstance(self.__plots[0],ROOT.TH1F):
            for i,plot in enumerate(self.__plots):
                if i is 0:
                    plot.Draw()
                else:
                    plot.Draw("SAME")
        elif isinstance(self.__plots[0],ROOT.TGraph):

            for i,plot in enumerate(self.__plots):
                if i is 0:
                    plot.Draw(arg)
                else:
                    plot.Draw(arg.replace("A","") + "SAME")
                
        else:
            sys.exit("Unknown plot type")
        
        img = ROOT.TImage.Create()
        img.FromPad(c1)
        img.WriteImage("plots/hitmap.png")
            
        raw_input()

    def setLineColor(self, colors):

        if len(colors) is not len(self.__plots):
            sys.exit("Not enough or too many colors! Colors has length %s and there are %s plots" %(len(colors), len(self.__plots)))
        else:
            for i,plot in enumerate(self.__plots):
                plot.SetLineColor(colors[i])
        return True
    
    def setTitle(self, title):
	self.__plots[0].SetTitle(title)

        return True

    def setRange(self, xRange = None, yRange = None, zRange = None):
    
        if xRange is not None:
            self.__plots[0].GetXaxis().SetRangeUser(xRange[0],xRange[1])
        if yRange is not None:
            self.__plots[0].GetYaxis().SetRangeUser(yRange[0],yRange[1])
        if zRange is not None:
            self.__plots[0].GetZaxis().SetRangeUser(zRange[0],zRange[1])
            

        return True
        
    def clear(self):
        self.__plots = []

    def save(self, fileName):
        for i, plot in enumerate(self.__plots):
            plot.SaveAs(fileName+("%s.png" %i))

            
        
if __name__ == "__main__":
    
    plot = MPAPlot()
    
    if len(sys.argv)>1:
        print("Reading file {0} ...".format(sys.argv[1]))
        fname = sys.argv[1]
        hits = [0]*48
        with open(fname) as f:
            for line in f:
                line = line[1:-2].split(",") # remove [ and ], split by ,
                for i, count in enumerate(line):
                    hits[i] += int(count)
        print(" ... done!")
    else:
        hits = [80, 40, 44, 43, 30, 34, 0, 46, 0, 64, 0, 75, 0, 0, 59, 108, 88, 27, 25, 38, 34, 30, 39, 28, 23, 30, 28, 30, 35, 35, 31, 54, 61, 28, 31, 30, 35, 41, 41, 0, 43, 0, 48, 38, 40, 36, 35, 83]
        #hits = [89, 32, 33, 49, 35, 34, 28, 38, 55, 37, 38, 35, 25, 22, 43, 92, 70, 35, 35, 31, 22, 23, 21, 24, 23, 32, 26, 31, 34, 39, 45, 103, 107, 42, 41, 29, 21, 30, 27, 33, 30, 34, 34, 24, 28, 44, 41, 63]
    plot.createHitMap(hits)
    #plot.fillHisto(hits)
    plot.draw()
