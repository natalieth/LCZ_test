import numpy as np
from PyQt4.QtGui import * 
from PyQt4.QtCore import * 
import sys

def LCZ_fractions(lc_grid,dlg):
    LCZs = [1,2,3,4,5,6,7,8,9,10,101,102,103,104,105,106,107]
    lczraster = np.round(lc_grid)
    countall = np.count_nonzero(lczraster)
    countlcz = np.zeros(len(LCZs))
    lczfrac = np.zeros(len(LCZs))
    for l in range(len(LCZs)):
        countlcz[l] = np.count_nonzero(lczraster[lczraster==LCZs[l]])
        lczfrac[l] = countlcz[l]/countall
    
    rows = dlg.tableWidget.rowCount()
    paved = []
    for row in range(rows):
        paved = dlg.tableWidget.cellWidget(row,0)
    
    lczfractions= {'lcz_frac': lczfrac , 'lcz_count': countlcz, 'count_all': countall }
    return lczfractions
