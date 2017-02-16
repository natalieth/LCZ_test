import numpy as np
from PyQt4.QtGui import * 
from PyQt4.QtCore import * 
from qgis.core import QgsMessageLog

def LCZ_fractions(lc_grid,dlg):
    LCZs = [1.,2.,3.,4.,5.,6.,7.,8.,9.,10.,101.,102.,103.,104.,105.,106.,107.]
    lc_frac_all = np.zeros((1, 7))
    rows = dlg.tableWidget.rowCount()
    pavedf = np.zeros(len(LCZs))
    buildingsf = np.zeros(len(LCZs))
    grassf = np.zeros(len(LCZs))
    dtreesf = np.zeros(len(LCZs))
    etreesf = np.zeros(len(LCZs))
    bsoilf = np.zeros(len(LCZs))
    waterf = np.zeros(len(LCZs))
    lczraster = np.round(lc_grid)
    countlcz = np.zeros(len(LCZs))
    lczfrac = np.zeros(len(LCZs))
    lczraster[lczraster<1.]= 0.
    countall = np.count_nonzero(lczraster)

    for l in range(len(LCZs)): 
        countlcz[l] = np.count_nonzero(lczraster[lczraster==LCZs[l]])
        lczfrac[l] = countlcz[l]/countall   #calculates fractions of each LCZ
        pavedx = float(dlg.tableWidget.item(0,l).text())
        buildingsx = float(dlg.tableWidget.item(1,l).text())
        grassx = float(dlg.tableWidget.item(2,l).text())
        dtreesx = float(dlg.tableWidget.item(3,l).text())
        etreesx = float(dlg.tableWidget.item(4,l).text())
        bsoilx = float(dlg.tableWidget.item(5,l).text())
        waterx = float(dlg.tableWidget.item(6,l).text())
        if not(((pavedx + buildingsx+ grassx + dtreesx + etreesx +bsoilx +waterx)>0.9999) and((pavedx + buildingsx+ grassx + dtreesx + etreesx +bsoilx +waterx)<1.00001)):
            QgsMessageLog.logMessage("Fractions in LCZ " + str(LCZs[l])+ " were " + str((pavedx + buildingsx+ grassx + dtreesx + etreesx +bsoilx +waterx)) + " and do not add up to 1.0", level=QgsMessageLog.CRITICAL)
            break
        pavedf[l] = pavedx*lczfrac[l]
        grassf[l] = grassx*lczfrac[l]
        buildingsf[l] = buildingsx*lczfrac[l]
        dtreesf[l] = dtreesx*lczfrac[l]
        etreesf[l] = etreesx*lczfrac[l]
        bsoilf[l] = bsoilx*lczfrac[l]
        waterf[l] = waterx*lczfrac[l]
    lc_frac_all[0,0] = pavedf.sum(axis=0)
    lc_frac_all[0,1] = buildingsf.sum(axis=0)
    lc_frac_all[0,4] = grassf.sum(axis=0)
    lc_frac_all[0,3] = dtreesf.sum(axis=0)
    lc_frac_all[0,2] = etreesf.sum(axis=0)
    lc_frac_all[0,5] = bsoilf.sum(axis=0)
    lc_frac_all[0,6] = waterf.sum(axis=0)
    
    lczfractions = {'lcz_frac': lczfrac,'lc_frac_all': lc_frac_all  ,  'count_all': countall }
    return lczfractions
