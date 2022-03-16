import pandas as pd
import matplotlib.pyplot as plt
import tqdm 
import argparse
import os
import dataclasses 
import numpy 

from pathlib import Path 

from util import TensorCollectionSuiteSparse, ScipyTensorShifter, PydataMatrixMarketTensorLoader, ScipyMatrixMarketTensorLoader, SuiteSparseTensor, safeCastPydataTensorToInts

SS_PATH = os.getenv('SUITESPARSE_PATH')

ssMtx = dataclasses.make_dataclass("SS", [("name", str), ("nnz", int), \
          ("dim1", int), ("dim2", int), ("sparsity", float), ("seg_size", int), \
          ("crd_size", int)])

# UfuncInputCache attempts to avoid reading the same tensor from disk multiple
# times in a benchmark run.
class UfuncInputCache:
    def __init__(self):
        self.lastLoaded = None
        self.lastName = None
        self.tensor = None

    def load(self, tensor, suiteSparse, cast):
        if self.lastName == str(tensor):
            return self.tensor, self.other
        else:
            if suiteSparse:
                self.lastLoaded = tensor.load(ScipyMatrixMarketTensorLoader("csr"))
            else:
                self.lastLoaded = tensor.load()
            self.lastName  = str(tensor)
            if cast:
              self.tensor = safeCastPydataTensorToInts(self.lastLoaded)
            else:
              self.tensor = self.lastLoaded
            return self.tensor
inputCache = UfuncInputCache()


def stats_tile(filename, args):
 
    tensor = SuiteSparseTensor(os.path.join(SS_PATH, filename))
    ssTensor = inputCache.load(tensor, True, False)

    if not isinstance(ssTensor, numpy.ndarray):
        tensor_list = []
        nx = int(ssTensor.shape[0] / args.tilewidth) + 1
        ny = int(ssTensor.shape[1] / args.tileheight) + 1
        for i in range(nx):
            for j in range(ny):
                startx = i*args.tilewidth
                stopx = min((i+1)*args.tilewidth, ssTensor.shape[0])
                starty = j*args.tileheight
                stopy = min((j+1)*args.tileheight, ssTensor.shape[1])

                if args.debug:
                    print(i, startx, stopx)
                    print(j, starty, stopy)

                subTensor = ssTensor[startx:stopx, starty:stopy] 
                
                name = str(tensor) + "_t"+str(i*ny+j)+"_"+str(args.tilewidth)+"x"+str(args.tileheight)

                if args.debug:
                  print(name)
                  print("NNZ:", subTensor.nnz, "\tShape:", subTensor.shape) 
                  print(subTensor.indices)
                  print(subTensor.indptr)      

                tensor_list.append(ssMtx(name, subTensor.nnz, \
                    subTensor.shape[0], subTensor.shape[1] , \
                    float(subTensor.nnz)/float(subTensor.shape[0]*subTensor.shape[1]), \
                    len(subTensor.indptr), len(subTensor.indices)))
            
        outname = str(tensor) + "_"+str(args.tilewidth)+"x"+str(args.tileheight)
        dfss = pd.DataFrame(tensor_list)
        
        hist = dfss.hist(bins=20)
        plt.savefig('./logs/'+outname+'_figure.pdf')

        tile_out_filepath = Path('./logs/'+outname+'.csv')  
        tile_out_filepath.parent.mkdir(parents=True, exist_ok=True)
        dfss.to_csv(tile_out_filepath)
        

def stats_overall(args):
    print("Processing Overall Stats")

    filenames = sorted([f for f in os.listdir(SS_PATH) if f.endswith(".mtx")])
    if args.num is not None and args.numstop is not None:
        filenames = filenames[args.num:args.numstop]
    elif args.num is not None:
        filenames = filenames[args.num:]
    elif args.numstop is not None: 
        filenames = filenames[:args.numstop]

    tensor_list = []
    pbar = tqdm.tqdm(filenames)
    for filename in pbar:

        pbar.set_description("Processing %s" % filename)

        tensor = SuiteSparseTensor(os.path.join(SS_PATH, filename))
        ssTensor = inputCache.load(tensor, True, False)

        tensor_list.append(ssMtx(str(tensor), ssTensor.nnz, \
            ssTensor.shape[0], ssTensor.shape[1] , \
            float(ssTensor.nnz)/float(ssTensor.shape[0]*ssTensor.shape[1]), \
            len(ssTensor.indptr), len(ssTensor.indices)))


    dfss = pd.DataFrame(tensor_list)
    
    hist = dfss.hist(bins=70)
    plt.savefig('./logs/overall_figure.pdf')

    outpath = Path('./logs/overall_out.csv')  
    outpath.parent.mkdir(parents=True, exist_ok=True)
    if outpath.is_file():
        dfss.to_csv(outpath, mode='a', index=False, header=False)
    else:
        dfss.to_csv(outpath, index=False)



def main():
    parser = argparse.ArgumentParser(description="Process some suitesparse matrix statistics")
    parser.add_argument('--overall', action='store_true', help='Get overall statistics on all matrices (overall). By defalt false')
    parser.add_argument('--tile', action='store_true', help='Get tile statistics on one or all matrices. By default false')
    parser.add_argument('-nstart', '--num', metavar='N', type=int, action='store', help='Start number of SS matrices to process (--overall=true)')
    parser.add_argument('-nstop', '--numstop', metavar='N', type=int, action='store', help='Stop number of SS matrices to process (--overall=true)')
    parser.add_argument('-tw', '--tilewidth', metavar='N', type=int, action='store', default=64, help='Size of width (1st) tile dimension')
    parser.add_argument('-th', '--tileheight', metavar='N', type=int, action='store', default=64, help='Size of height (2nd) tile dimension')
    parser.add_argument('-t', '--tensor', metavar='ssname', type=str, action='store', help='tensor name to run tile analysis on one SS tensor')
    parser.add_argument('-g', '--debug', action='store_true', help='Print debug statements')

    args = parser.parse_args()

    log_path = Path('./logs/')  
    log_path.mkdir(parents=True, exist_ok=True)
    if args.overall:
        stats_overall(args)
    
    if args.tile:
        print("Processing Tile Stats")
        if args.tensor is None:
            filenames = sorted([f for f in os.listdir(SS_PATH) if f.endswith(".mtx")])
            if args.num is not None:
                filenames = filenames[:args.num]

            tensor_list = []
            pbar = tqdm.tqdm(filenames)
            for filename in pbar:
                pbar.set_description("Processing %s" % filename)
                stats_tile(filename, args)
        else:
            filename = args.tensor + ".mtx"
            print("Processing %s" % filename)
            stats_tile(filename, args) 
    
    
    


    

  

  
if __name__=='__main__':
  main()


