from PyQt4 import QtCore
from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
# from qgis.gui import *
from qgis.core import *  # QgsVectorLayer, QgsVectorFileWriter, QgsFeature, QgsRasterLayer, QgsGeometry, QgsMessageLog
from LCZ_fractions import *
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

    def __init__(self, lc_grid, poly, vlayer, prov, fields, idx, dir_poly, iface, plugin_dir,
                 folderPath, dlg):

        QtCore.QObject.__init__(self)
        self.killed = False
        self.lc_grid = lc_grid
        self.poly = poly
        self.vlayer = vlayer
        self.prov = prov  # provider
        self.fields = fields
        self.idx = idx
        self.dir_poly = dir_poly
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.folderPath = folderPath
        self.dlg = dlg

    def run(self):

        #Check OS and dep
        if sys.platform == 'darwin':
            gdalwarp_os_dep = '/Library/Frameworks/GDAL.framework/Versions/Current/Programs/gdalwarp'
        else:
            gdalwarp_os_dep = 'gdalwarp'

        ret = 0
        arrmat = np.empty((1, 8))
        pre = str(self.dlg.lineEdit.text())

        try:
            # j = 0
            for f in self.vlayer.getFeatures():  # looping through each grid polygon
                if self.killed is True:
                    break

                attributes = f.attributes()
                geometry = f.geometry()
                feature = QgsFeature()
                feature.setAttributes(attributes)
                feature.setGeometry(geometry)

                writer = QgsVectorFileWriter(self.dir_poly, "CP1250", self.fields, self.prov.geometryType(),
                                                 self.prov.crs(), "ESRI shapefile")

                if writer.hasError() != QgsVectorFileWriter.NoError:
                    self.iface.messageBar().pushMessage("Error when creating shapefile: ", str(writer.hasError()))
                
                writer.addFeature(feature)
                del writer

                provider = self.lc_grid.dataProvider()
                filePath_lc_grid = str(provider.dataSourceUri())
                
                gdalruntextlc_grid = gdalwarp_os_dep + ' -dstnodata -9999 -q -overwrite -cutline ' + self.dir_poly + \
                                           ' -crop_to_cutline -of GTiff "' + filePath_lc_grid + '" "' + \
                                           self.plugin_dir + '/data/clipdsm.tif"'

                if sys.platform == 'win32':
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    subprocess.call(gdalruntextlc_grid, startupinfo=si)
                else:
                    os.system(gdalruntextlc_grid)

                dataset = gdal.Open(self.plugin_dir + '/data/clipdsm.tif')
                lc_grid_array = dataset.ReadAsArray().astype(np.float)
                nd = dataset.GetRasterBand(1).GetNoDataValue()
                nodata_test = (lc_grid_array == nd)
                if np.sum(lc_grid_array) == (lc_grid_array.shape[0] * lc_grid_array.shape[1] * nd):
                    QgsMessageLog.logMessage("Grid " + str(f.attributes()[self.idx]) + " not calculated. Includes Only NoData Pixels", level=QgsMessageLog.CRITICAL)
                    cal = 0
                else:
                    lc_grid_array[lc_grid_array == nd] = 0
                    cal = 1

                if cal == 1:
                    lczfractions = LCZ_fractions(lc_grid_array,self.dlg)
#                    lczfractions = self.resultcheck(lczfractions)

                    # save to file
                    header = 'Wd Paved Buildings EvergreenTrees DecidiousTrees Grass Baresoil Water'
                    numformat = '%3d %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f'
                    arr = lczfractions["lcz_frac"]
                    np.savetxt('LCFG_anisotropic_result_' + str(f.attributes()[self.idx]) + '.txt', arr,delimiter=' ', header=header, comments='')
#                    np.savetxt(self.folderPath[0] + '/' + pre + '_' + 'LCFG_anisotropic_result_' + str(f.attributes()[self.idx]) + '.txt', arr,fmt=numformat, delimiter=' ', header=header, comments='')


                    arr2 = np.array([f.attributes()[self.idx], lczfractions["lcz_frac"][0], lczfractions["lcz_frac"][1],
                                      lczfractions["lcz_frac"][2], lczfractions["lcz_frac"][3], lczfractions["lcz_frac"][4],
                                     lczfractions["lcz_frac"][5], lczfractions["lcz_frac"][6]])

                    arrmat = np.vstack([arrmat, arr2])

                dataset = None
                dataset2 = None
                dataset3 = None
                self.progress.emit()

            header = 'ID Paved Buildings EvergreenTrees DecidiousTrees Grass Baresoil Water'
            numformat = '%3d %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f'
            arrmatsave = arrmat[1: arrmat.shape[0], :]
            np.savetxt(self.folderPath[0] + '/' +'LCFG_isotropic.txt', arrmatsave,
                                fmt=numformat, delimiter=' ', header=header, comments='')

            #when files are saved through the np.savetext method the values are rounded according to the information in
            #the numformat variable. This can cause the total sum of the values in a line in the text file to not be 1
            #this method reads through the text file after it has been generated to make sure every line has a sum of 1.
            self.textFileCheck(pre)

            if self.dlg.checkbox_2.isChecked():
                self.addattributes(self.vlayer, arrmatsave, header, pre)

            if self.killed is False:
                self.progress.emit()
                ret = 1

        except Exception, e:
            ret = 0
            #self.error.emit(e, traceback.format_exc())
            errorstring = self.print_exception()
            self.error.emit(errorstring)

        self.finished.emit(ret)
        # self.finished.emit(self.killed)

    def print_exception(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION IN {}, \nLINE {} "{}" \nERROR MESSAGE: {}'.format(filename, lineno, line.strip(), exc_obj)

    def addattributes(self, vlayer, matdata, header, pre):
        # vlayer = self.vlayer
        current_index_length = len(vlayer.dataProvider().attributeIndexes())
        caps = vlayer.dataProvider().capabilities()

        if caps & QgsVectorDataProvider.AddAttributes:
            #vlayer.startEditing()
            line_split = header.split()
            for x in range(1, len(line_split)):

                vlayer.dataProvider().addAttributes([QgsField(pre + '_' + line_split[x], QVariant.Double)])

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

    def resultcheck(self, landcoverresult):
        total = 0.
        arr = landcoverresult["lcz_frac"]

        for x in range(0, len(arr)):
            total += arr[x]

        if total != 1.0:
            diff = total - 1.0

            maxnumber = max(arr[0])

            for x in range(0, len(arr[0])):
                if maxnumber == arr[0, x]:
                    arr[0, x] -= diff
                    break

        landcoverresult["lc_frac_all"] = arr

        return landcoverresult

    def textFileCheck(self, pre):
        try:
            file_path = self.folderPath[0] + '/' + pre + '_' + 'LCFG_isotropic.txt'
            if os.path.isfile(file_path):
                wrote_header = False
                for line in fileinput.input(file_path, inplace=1):
                    if not wrote_header:
                        print line,
                        wrote_header = True
                    else:
                        line_split = line.split()
                        total = 0.
                        # QgsMessageLog.logMessage(str(line), level=QgsMessageLog.CRITICAL)
                        for x in range(1, len(line_split)):
                            total += float(line_split[x])

                        if total == 1.0:
                            print line,
                        else:
                            diff = total - 1.0
                            # QgsMessageLog.logMessage("Diff: " + str(diff), level=QgsMessageLog.CRITICAL)
                            max_number = max(line_split[1:])
                            # QgsMessageLog.logMessage("Max number: " + str(max_number), level=QgsMessageLog.CRITICAL)

                            for x in range(1, len(line_split)):
                                if float(max_number) == float(line_split[x]):
                                    line_split[x] = float(line_split[x]) - diff
                                    break
                            if int(line_split[0]) < 10:
                                string_to_print = '  '
                            elif int(line_split[0]) < 100:
                                string_to_print = ' '
                            else:
                                string_to_print = ''

                            for element in line_split[:-1]:
                                string_to_print += str(element) + ' '
                            string_to_print += str(line_split[-1])
                            string_to_print += '\n'

                            print string_to_print,
                fileinput.close()
        except Exception, e:
            errorstring = self.print_exception()
            QgsMessageLog.logMessage(errorstring, level=QgsMessageLog.CRITICAL)
            fileinput.close()

    def kill(self):
        self.killed = True
