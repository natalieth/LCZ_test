from PyQt4 import QtCore
from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
# from qgis.gui import *
from qgis.core import *  # QgsVectorLayer, QgsVectorFileWriter, QgsFeature, QgsRasterLayer, QgsGeometry, QgsMessageLog
import traceback
import numpy as np
from osgeo import gdal
import subprocess
import sys
import linecache
import os
import fileinput

class Worker(QtCore.QObject):

    finished = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal()

    def __init__(self,lc_grid,poly,vlayer,prov,fields,idx,iface,plugin_dir,folderPath,dlg):

        QtCore.QObject.__init__(self)
        self.killed = False
        self.lc_grid = lc_grid
        self.poly = poly
        self.vlayer = vlayer
        self.prov = prov
        self.fields = fields
        self.LCZs = [1,2,3,4,5,6,7,8,9,10,101,102,103,104,105,106,107]
        
    def run(self):
        QMessageBox.critical(None, "running", "got to this point")
        if sys.platform == 'darwin':
            gdalwarp_os_dep = '/Library/Frameworks/GDAL.framework/Versions/Current/Programs/gdalwarp'
        else:
            gdalwarp_os_dep = 'gdalwarp'
        sizex = self.lc_grid.shape[0]
        sizey = self.lc_grid.shape[1]
        lcz_grids = np.zeros((sizex, sizey,len(self.LCZs)))

        ret = 0
        arrmat = np.empty((1, 8))
        pre = str(self.dlg.lineEdit.text())

        try:
            # j = 0
            for l in range(len(self.LCZs)):
                for x in range(sizex):
                    for y in range(sizey):
                        if lc_grid[x,y] is self.LCZs[l]:
                            lcz_grids[x,y,l] = 1
                        else:
                            lcz_grids[x,y,l] = 0   
            for f in self.vlayer.getFeatures():
                if self.killed is True:
                    break            
                QMessageBox.critical(None, "running", "Yeah!")
                
        except Exception, e:
            ret = 0
            #self.error.emit(e, traceback.format_exc())
            errorstring = self.print_exception()
            self.error.emit(errorstring)

        self.finished.emit(ret)
  
    def addattributes(self, vlayer, matdata, header, pre):
        # vlayer = self.vlayer
        current_index_length = len(vlayer.dataProvider().attributeIndexes())
        caps = vlayer.dataProvider().capabilities()

        if caps & QgsVectorDataProvider.AddAttributes:
            #vlayer.startEditing()
            line_split = header.split()
            for x in range(1, len(line_split)):

                vlayer.dataProvider().addAttributes([QgsField( line_split[x], QVariant.Double)])

            attr_dict = {}

            for y in range(0, matdata.shape[0]):
                attr_dict.clear()
                idx = int(matdata[y, 0])
                for x in range(1, matdata.shape[1]):
                    attr_dict[current_index_length + x - 1] = float(matdata[y, x])
                #QMessageBox.information(None, "Error", str(line_split[x]))
                vlayer.dataProvider().changeAttributeValues({idx: attr_dict})

            #vlayer.commitChanges()
            vlayer.updateFields()
        else:
            QMessageBox.critical(None, "Error", "Vector Layer does not support adding attributes")
    
    def kill(self):
        self.killed = True