import os
import numpy as np
import pickle
import copy
from scipy import stats
from math import floor, log10
from UGParameterEstimator import FreeSurfaceTimeDependentEvaluation, FreeSurfaceEquilibriumEvaluation
from datetime import datetime

# helper functions to write numbers in scientific notation
def fexp(f):
    return int(floor(log10(abs(f)))) if f != 0 else 0

def fman(f):
    return f/10**fexp(f)

# A class containing the result of the calibration operation
#
# This class contains all logentries and all data written away during the iterations of the calibration.
# The data can be saved by calling save() and will be written to a .pkl file.
class Result:

    def __init__(self,filename=None):
        self.iterations = []
        self.logentries = []

        self.currentIteration = {}

        self.metadata = {}

        self.filename = filename

        if filename:
            directory = os.path.dirname(self.filename)
            os.makedirs(directory, exist_ok=True)

    @property
    def iterationCount(self):
        return len(self.iterations)

    # writes the iteration data as a simple tab-separated-text file for postprocessing
    def writeTable(self, file, metadata):

        pm = self.metadata["parametermanager"]
        with open(file,"w") as f:
            
            # write table header
            f.write("step" + "\t")
            for p in pm.parameters:
                f.write(p.name+"\t")
            for p in metadata:
                f.write(p[0]+"\t")

            f.write("\n")

            i = 0
            for iteration in self.iterations:
                f.write(str(i) + "\t")
                for j in range(len(pm.parameters)):
                    f.write(str(iteration["parameters"][j]) + "\t")

                for p in metadata:
                    if p[1] in iteration:
                        f.write(str(iteration[p[1]]) + "\t")
                    else:
                        f.write("NaN\t")
                
                f.write("\n")
                i += 1
    
    # writes the iteration data as a latex table.
    #   file - the name of the file the result should be written to
    #   metadata - the metadata fields to include in the table as columns, additionally to the parameters
    #   nameoverride - allows the user to provide better readable names as parameter names
    def writeLatexTable(self, file, metadata, nameoverride=None):

        pm = self.metadata["parametermanager"]
        with open(file,"w") as f:
            
            # write table header
            f.write("\\begin{tabular}{")
            
            count = len(pm.parameters) + len(metadata)
            f.write("c||")
            for i in range(count-1):
                f.write("c|")
            f.write("c}\\\\\n")

            f.write("Schritt $l$" + " & ")  
            for i in range(len(pm.parameters)):
                if nameoverride is None:
                    p = pm.parameters[i].name
                    f.write("$\\hat{\\theta}_"+str(i+1)+"^{(l)}$ (\\verb|"+p+"|) & ")
                else:
                    f.write("$\\hat{\\theta}_"+str(i+1)+"^{(l)}$ (" + nameoverride[i] + ") & ")

            for i in range(len(metadata)-1):
                f.write(metadata[i][0]+"&")            
            f.write(metadata[-1][0]+"\\\\\hline\n")

            i = 0
            for iteration in self.iterations:
                f.write(str(i+1) + " & ")
                for j in range(len(pm.parameters)):
                    entry = pm.parameters[j].getTransformedParameter(iteration["parameters"][j])
                    f.write("$" + Result.getLatexString(entry) + "$"+ " & ")

                for j in range(len(metadata)):
                    p = metadata[j][1]
                    if p in iteration:
                        f.write("$" + Result.getLatexString(iteration[p]) + "$" )
                    else:
                        f.write("--")
                    if j == len(metadata)-1:
                        f.write("\\\\\n")
                    else:
                        f.write(" & ")
                
                i += 1

            f.write("\\end{tabular}")

    def writeSimpleErrorTable(self, file, metadata, nameoverride=None):

        pm = self.metadata["parametermanager"]
        with open(file,"w") as f:
            
            # write table header
            f.write("\\begin{tabular}{")
            
            count = 2*len(pm.parameters) + len(metadata)
            f.write("c||")
            for i in range(count-1):
                f.write("c|")
            f.write("c}\\\\\n")

            f.write("Schritt $l$" + " & ")  
            for i in range(len(pm.parameters)):
                if nameoverride is None:
                    p = pm.parameters[i].name
                    f.write("$\\hat{\\theta}_"+str(i+1)+"^{(l)}$ (\\verb|"+p+"|) & ")
                else:
                    f.write("$\\hat{\\theta}_"+str(i+1)+"^{(l)}$ (" + nameoverride[i] + ") & ")
                
                f.write("se($\\theta_" + str(i+1) + "^{(l)}$) & ")

            for i in range(len(metadata)-1):
                f.write(metadata[i][0]+"&")            
            f.write(metadata[-1][0]+"\\\\\hline\n")

            i = 0
            for iteration in self.iterations:
                f.write(str(i+1) + " & ")
                for j in range(len(pm.parameters)):
                    entry = pm.parameters[j].getTransformedParameter(iteration["parameters"][j])
                    f.write("$" + Result.getLatexString(entry) + "$"+ " & ")
                    error = iteration["errors"][j]
                    f.write("$" + Result.getLatexString(error) + "$ & ")                    

                for j in range(len(metadata)):
                    p = metadata[j][1]
                    if p in iteration:
                        f.write("$" + Result.getLatexString(iteration[p]) + "$" )
                    else:
                        f.write("--")
                    if j == len(metadata)-1:
                        f.write("\\\\\n")
                    else:
                        f.write(" & ")
                
                i += 1

            f.write("\\end{tabular}")
    
    def writeErrorTable(self, file, confidence=0.95):

        pm = self.metadata["parametermanager"]
        with open(file,"w") as f:
            
            # write table header
            f.write("\\begin{tabular}{")
            
            count = len(pm.parameters)*2
            f.write("c||")
            for i in range(count-1):
                f.write("c|")
            f.write("c}\n")

            f.write("step" + " & ")
            for i in range(len(pm.parameters)-1):
                p = pm.parameters[i].name
                f.write("$\\beta_"+str(i)+"$ ("+p+") & ")
                f.write("se($\\beta_" + str(i) + "$) & ")
        
            i = len(pm.parameters)-1
            f.write("$\\beta_"+str(i)+"$ (\\verb|"+pm.parameters[-1].name+"|) & ")
            f.write("se($\\beta_" + str(i) + "$) \\\\\hline\n")
            

            i = 0
            for iteration in self.iterations:
                f.write(str(i+1) + " & ")
                for j in range(len(pm.parameters)):
                    entry = pm.parameters[j].getTransformedParameter(iteration["parameters"][j])
                    error = iteration["errors"][j]
                    if "confidenceinterval" in iteration:
                        interval = iteration["confidenceinterval"][j]
                        f.write("$" + Result.getLatexString(entry) + "\\pm" + Result.getLatexString(interval) + "$"+ " & ")
                    else:
                        f.write("$" + Result.getLatexString(entry) + "$"+ " & ")

                    error = iteration["errors"][j]
                    f.write("$" + Result.getLatexString(error) + "$")

                    if j == len(pm.parameters)-1:
                        f.write("\\\\\n")
                    else:
                        f.write(" & ")
                
                i += 1

            f.write("\\end{tabular}")

    def writeMatrix(self, file, name, symbol, iterations_to_print=[-1]):
        
        with open(file,"w") as f:
            for i in iterations_to_print:

                if i == -1:
                    i = self.iterationCount-1

                data = self.iterations[i][name]

                f.write("$$" + symbol + "^{(" + str(i+1) + ")} = \\begin{pmatrix}\n")
            
                for x in range(np.shape(data)[0]):
                    for y in range(np.shape(data)[1]):

                        f.write(Result.getLatexString(data[x][y]))

                        if(y == np.shape(data)[1]-1):
                            f.write("\\\\\n")
                        else:
                            f.write("&")
                
                f.write("\\end{pmatrix}$$\n")

    def writeSensitivityPlots(self, filename, iteration, extended=True, zlabel=lambda i: "$\\frac{\\partial \\vec{m}}{\delta \\theta_"+ str(i+1) + "}$ {[m]}"):

        pm = self.metadata["parametermanager"]
        if iteration == -1:
            iteration = self.iterationCount-1

        if len(self.iterations) <= iteration or iteration < 0:
            print("Illegal iteration index")
            return

        iterationdata = self.iterations[iteration]
        jacobi = iterationdata["jacobian"]
        p = iterationdata["parameters"]
        m = iterationdata["measurement"]

        if len(pm.parameters) != jacobi.shape[1]:
            print("Mismatch of parameter count!")
            return

        for i in range(len(pm.parameters)):
            dg = jacobi[:,i]
            partial = (p[i]/(np.max(m)))*dg
            if isinstance(self.metadata["target"], FreeSurfaceTimeDependentEvaluation):
                partial_series = FreeSurfaceTimeDependentEvaluation.fromNumpyArray(partial, self.metadata["target"])
                
                if extended:
                    partial_series.writeCSVAveragedOverTimesteps(filename + "-" + pm.parameters[i].name + "-over-time.csv")
                    partial_series.writeCSVAveragedOverLocation(filename + "-" + pm.parameters[i].name + "-over-location.csv")
                
                    with open(filename + "-" + pm.parameters[i].name + ".tex","w") as f:                    
                        f.write("\\begin{center}\n")
                        f.write("\\begin{minipage}{0.4\\textwidth}\n")
                        f.write("\t\\begin{tikzpicture}[scale=0.8]\n")
                        f.write("	\\begin{axis}[\n")
                        f.write("	xlabel=Zeit,\n")
                        f.write("	ylabel=$\\frac{\\delta m}{\\delta \\theta_"+ str(i) + "}$,\n")
                        f.write("	legend style={\n")
                        f.write("		at={(0,0)},\n")
                        f.write("		anchor=north,at={(axis description cs:0.5,-0.18)}}]\n")
                        f.write("	\\addplot [thick] table [x={time}, y={value}] {"+filename + "-" + pm.parameters[i].name + "-over-location.csv"+"};\n")
                        f.write("	\\end{axis}\n")
                        f.write("	\\end{tikzpicture}\n")
                        f.write("\\end{minipage}	 \n")
                        f.write("\\begin{minipage}{0.4\\textwidth}\n")
                        f.write("		\\begin{tikzpicture}[scale=0.8]\n")
                        f.write("		\\begin{axis}[\n")
                        f.write("		xlabel=Ort,\n")
                        f.write("		ylabel=$\\frac{\\delta m}{\delta \\beta_"+ str(i) + "}$,\n")
                        f.write("		legend style={\n")
                        f.write("			at={(0,0)},\n")
                        f.write("			anchor=north,at={(axis description cs:0.5,-0.18)}} ]\n")
                        f.write("		\\addplot [thick] table [x={location}, y={value}] {"+filename + "-" + pm.parameters[i].name + "-over-time.csv};\n")
                        f.write("		\\end{axis}\n")
                        f.write("		\\end{tikzpicture}\n")
                        f.write("\\end{minipage}\\\\\n")  
                        f.write("\\end{center}")
                else:
                    partial_series.write3dPlot(filename + "-" + pm.parameters[i].name.replace("_","-") + ".tex", zlabel(i), scale=0.8)
            elif isinstance(self.metadata["target"], FreeSurfaceEquilibriumEvaluation):
                partial_series = FreeSurfaceEquilibriumEvaluation.fromNumpyArray(partial, self.metadata["target"])
                FreeSurfaceEquilibriumEvaluation.writePlots({"Sensitivität":{"eval":partial_series}}, filename + "-" + pm.parameters[i].name.replace("_","-") + ".tex", zlabel(i))
                
    def plotComparison(self, filename, force2d=False):

        target = self.metadata["target"]
        result = self.iterations[self.iterationCount-1]["measurementEvaluation"]
        start = self.iterations[0]["measurementEvaluation"]

        if isinstance(target, FreeSurfaceEquilibriumEvaluation):
            result = FreeSurfaceEquilibriumEvaluation.fromTimedependentTimeseries(result)
            start = FreeSurfaceEquilibriumEvaluation.fromTimedependentTimeseries(start)
            FreeSurfaceEquilibriumEvaluation.writePlots({"Nach Kalibrierung":{"eval":result}, "Kalibrierungsziel":{"eval":target, "dashed":True}, "Startparameter":{"eval":start}}, filename) 
        else:
            if force2d:
                result = FreeSurfaceEquilibriumEvaluation.fromTimedependentTimeseries(result)
                start = FreeSurfaceEquilibriumEvaluation.fromTimedependentTimeseries(start)
                target = FreeSurfaceEquilibriumEvaluation.fromTimedependentTimeseries(target)
                FreeSurfaceEquilibriumEvaluation.writePlots({"Nach Kalibrierung":{"eval":result}, "Kalibrierungsziel":{"eval":target, "dashed":True}, "Startparameter":{"eval":start}}, filename) 
            else:
                with open(filename,"w") as f:
                    f.write("\\begin{center}\n")
                    f.write("\\begin{minipage}{0.3\\textwidth}\n")                    
                    f.write(target.write3dPlot(None, scale=0.4)) 
                    f.write("\\\ntarget")                     
                    f.write("\\end{minipage}	 \n")
                    f.write("\\begin{minipage}{0.3\\textwidth}\n")                    
                    f.write(start.write3dPlot(None, scale=0.4)) 
                    f.write("\\\nstart")                     
                    f.write("\\end{minipage}	 \n")
                    f.write("\\begin{minipage}{0.3\\textwidth}\n")                 
                    f.write(result.write3dPlot(None, scale=0.4))
                    f.write("\\\nresult")  
                    f.write("\\end{minipage}\\\\\n")  
                    f.write("\\end{center}")

    @staticmethod
    def getLatexString(number):

        if number is None:
            return "--"
        exp = fexp(number)
        man = fman(number)

        man = round(man, 3)

        if exp >= -1 and exp <= 1:
            return str(round(number,4))
        else:
            return str(man) + "\\cdot 10^{" + str(exp) + "} "

    def addRunMetadata(self, name, value):
        self.metadata[name] = value

    def addEvaluations(self, evaluations, tag=None):
        if "evaluations" not in self.currentIteration:
            self.currentIteration["evaluations"] = []
        self.currentIteration["evaluations"].append((copy.deepcopy(evaluations), tag, self.iterationCount))

    def addMetric(self, name, value):
        self.currentIteration[name] = value
        
    def commitIteration(self):
        self.iterations.append(copy.deepcopy(self.currentIteration))
        self.currentIteration.clear()
        self.save()

    def save(self,filename=None):
        if filename is None:            
            filename = self.filename

        if filename is None:
            return

        with open(filename,"wb") as f:
            pickle.dump(self.__dict__,f)
    
    def log(self, text):
        logtext = "[" + str(datetime.now()) + "] " + text
        print(logtext)        
        self.logentries.append(logtext)
        with open(self.filename + "_log","a") as f:
            f.write(logtext + "\n")
                
    def printlog(self):
        for l in self.logentries:
            print(l)

    @classmethod
    def load(cls, filename, printInfo=True):
        result = cls()
        with open(filename, "rb") as f:
            result.__dict__.update(pickle.load(f))

        if printInfo:
            print(result)

        return result
    
    @staticmethod
    def plotMultipleRuns(resultnames, outputfilename, log=True, paramnames=None):

        with open(outputfilename, "w") as f:
            f.write("\t\\begin{tikzpicture}[scale=0.9]\n")
            f.write("	\\begin{axis}[\n")
            f.write("	xlabel=Iteration,\n")
            f.write("	ylabel=$f$,\n")

            if log:
                f.write("	ymode=log,\n")

            f.write("	legend style={\n")
            f.write("		at={(0,0)},\n")
            f.write("		anchor=north,at={(axis description cs:0.5,-0.3)}}]\n")

            for resultfilename in resultnames:
                result = Result.load(resultfilename)
            
                f.write("\t\t\\addplot+[thick]\n")
                f.write("\t\t table [x={it}, y={f}]{ \n")
                f.write("it\t f\n")

                for t in range(result.iterationCount):
                    f.write(str(t) + "\t" + str(result.iterations[t]["residualnorm"]) + "\n")
                f.write("};\n")

                legtext = ""
                pm = result.metadata["parametermanager"]
                paramcount = len(pm.parameters)
                for p in range(paramcount):
                    if paramnames is None:
                        legtext += "$\\theta^{(1)}_"+ str(p) + "=" + Result.getLatexString(pm.parameters[p].startvalue)+ "$"
                    else:
                        legtext += "$" + paramnames[p] + "^{(1)} =" + Result.getLatexString(pm.parameters[p].startvalue) + "$"
                    if p != paramcount-1:
                        legtext += ", "
                f.write("\\addlegendentry{" + legtext + "};\n")
            
            f.write("	\\end{axis}\n")
            f.write("	\\end{tikzpicture}\n")

    def __str__(self):
        
        res = "######################################################\n"
        res += "filename: " + self.filename + "\n"
        res += "iterationCount: " + str(self.iterationCount)+ "\n"
        res += "paramcount: " + str(len(self.metadata["parametermanager"].parameters)) + "\n"
        res += "first res norm: " + str(self.iterations[0]["residualnorm"]) + "\n"
        res += "last res norm: " + str(self.iterations[self.iterationCount-1]["residualnorm"]) + "\n"

        for k in self.metadata:
            res += k + ": " + str(self.metadata[k]) + "\n"

        res += "######################################################"

        return res