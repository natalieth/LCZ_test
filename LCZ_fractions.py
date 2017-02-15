import numpy as np
from PyQt4.QtGui import * 
from PyQt4.QtCore import * 
import sys

def LCZ_fractions(lc_grid,dlg):
    LCZs = [1,2,3,4,5,6,7,8,9,10,101,102,103,104,105,106,107]
    rows = dlg.tableWidget.rowCount()
    paved = []
    lczraster = np.round(lc_grid)
    countall = np.count_nonzero(lczraster)
    countlcz = np.zeros(len(LCZs))
    lczfrac = np.zeros(len(LCZs))
    for l in range(len(LCZs)): 
        countlcz[l] = np.count_nonzero(lczraster[lczraster==LCZs[l]])
        lczfrac[l] = countlcz[l]/countall   #calculates fractions of each LCZ
        
        paved = dlg.tableWidget.cellWidget(row,l)
    
    lczfractions= {'lcz_frac': lczfrac , 'lcz_count': countlcz, 'count_all': countall }
    return lczfractions
