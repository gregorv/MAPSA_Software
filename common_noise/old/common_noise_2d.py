from ROOT import TH2S, TCanvas, TAxis, gStyle

iMPA = 1 # Number of MPA, 0-indexed
memory = open('data/synchronous_data_noise_MPA'+str(iMPA+1)).read().splitlines()
#memory = open('data/test').read().splitlines()

histo = TH2S("h1","Common noise analysis for MPA" +str(iMPA+1),len(memory[0]), 0.5, len(memory[0])+0.5, len(memory), 0.5, len(memory)+0.5)

for eventnum,event in enumerate(memory):
    for channel,hit in enumerate(event):
        if int(hit):
            histo.Fill(channel, eventnum)

histo.GetXaxis().SetTitle("pixel number")
histo.GetYaxis().SetTitle("event number")

c1 = TCanvas("hist", "hist", 1024, 768) 
c1.cd()
histo.SetFillColor(1);
histo.Draw("BOX")

c1.Print('plots/common_noise_2d_MPA'+str(iMPA+1)+'.pdf', 'pdf')
raw_input()
