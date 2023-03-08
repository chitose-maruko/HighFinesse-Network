import random
import math

class wlmTest:
    def __init__(self):
        self.SwitcherMode =False
        self.activeChannel=8*[False]
        self.wavelength = [450+random.randint(-10,10)]*8
        self.expTimes=8*[1]
        self.patternList=8*[1000*[0]]
    
    def randomWL(self):
        wlList=self.wavelength
        for i in range(8):
            wlList[i]+=random.randint(-10,10)
    
    def SetSwitcherMode(self,num):
        if num==1:
            self.SwitcherMode=True
        elif num==0:
            self.SwitcherMode=False
        else:
            print("Invalid input")
    
    def SetExposureNum(self,channel,num,expIn):
        self.expTimes[channel-1]=expIn
    
    def SetSwitcherSignalStates(self,channel,num,intInput):
        if intInput==1:
            self.activeChannel[channel-1]=True
        elif intInput==0:
            self.activeChannel[channel-1]=False
        else:
            print("Invalid input")
    
    def GetWavelengthNum(self,channel,option):
        self.wavelength[channel-1]+=random.randint(-5,5)/10
        return self.wavelength[channel-1]
    
    def randomPattern(self,channel):
        for num in range(1000):
            self.patternList[channel-1][num]=math.sin(num+random.randint(-5,5)/10)*random.randint(0,100)/100
    

