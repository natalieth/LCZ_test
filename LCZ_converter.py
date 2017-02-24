# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LCZ_test
                                 A QGIS plugin
 Converts LCZ raster to input for SUEWS
                              -------------------
        begin                : 2017-02-03
        git sha              : $Format:%H$
        copyright            : (C) 2017 by University of Reading
        email                : n.e.theeuwes@reading.ac.uk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import os
import os.path
from osgeo import gdal
from qgiscombomanager import *
# Initialize Qt resources from file resources.py
import resources
import webbrowser
import qgis.analysis
# Import the code for the dialog
from LCZ_converter_dialog import LCZ_testDialog
from LCZworker import Worker
import numpy as np

class LCZ_test:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'LandCoverFractionGrid_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = LCZ_testDialog()
        self.dlg.pushButton.clicked.connect(self.LCZ_selection)
        self.dlg.pushButton_2.clicked.connect(self.updatetable)
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonSelect.clicked.connect(self.folder_path)
        self.dlg.tableWidget.setEnabled(False)
        self.dlg.checkBox.toggled.connect(self.text_enable)
        self.dlg.progressBar.setValue(0)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)  # Save
        
        self.layerComboManagerPolygrid = VectorLayerCombo(self.dlg.comboBox_2)
        fieldgen = VectorLayerCombo(self.dlg.comboBox_2, initLayer="", options={"geomType": QGis.Polygon})
        self.layerComboManagerLCgrid = RasterLayerCombo(self.dlg.comboBox)
        RasterLayerCombo(self.dlg.comboBox, initLayer="")

        self.folderPath = 'None'
        self.steps = 0

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&LCZ_converter')
        self.toolbar = self.iface.addToolBar(u'LCZ_test')
        self.toolbar.setObjectName(u'LCZ_test')

        if not (os.path.isdir(self.plugin_dir + '/data')):
            os.mkdir(self.plugin_dir + '/data')

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LCZ_test', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/LCZ_test/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'LCZ converter'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&LCZ_converter'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
        
    def text_enable(self):
        if self.dlg.checkBox.isChecked():
            self.dlg.tableWidget.setEnabled(True)
        else:
            self.dlg.tableWidget.setEnabled(False)
    def folder_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.lineEdit_2.setText(self.folderPath[0])
    def LCZ_selection(self):
        lcz_grid = self.layerComboManagerLCgrid.getLayer()
        provider = lcz_grid.dataProvider()
        filepath_lc_grid= str(provider.dataSourceUri())
        gdal_lc_grid = gdal.Open(filepath_lc_grid)
        lcz_grid = gdal_lc_grid.ReadAsArray().astype(np.float)
        LCZs = [1.,2.,3.,4.,5.,6.,7.,8.,9.,10.,101.,102.,103.]
        heightfr = [str(0),str(0.1),str(0.25),str(0.5),str(1.0),str(1.5),str(2.0)]
        countlcz = np.zeros(len(LCZs))
        for l in range(len(LCZs)): 
            countlcz[l] = np.count_nonzero(lcz_grid[lcz_grid==LCZs[l]])
        sortcountLCZ = [(str(int(LCZs))) for countlcz, LCZs in sorted(zip(countlcz, LCZs),reverse=True)]
        self.dlg.comboBox_3.insertItems(0,sortcountLCZ)
        self.dlg.comboBox_4.insertItems(0,sortcountLCZ)
        self.dlg.comboBox_5.insertItems(0,sortcountLCZ)
        self.dlg.comboBox_6.insertItems(0,sortcountLCZ)
        self.dlg.comboBox_7.insertItems(0,sortcountLCZ)
        self.dlg.comboBox_8.insertItems(0,sortcountLCZ)
        self.dlg.comboBox_15.insertItems(0,sortcountLCZ)
        self.dlg.comboBox_16.insertItems(0,sortcountLCZ)
        self.dlg.comboBox_19.insertItems(0,heightfr)
        self.dlg.comboBox_20.insertItems(0,heightfr)
        self.dlg.comboBox_21.insertItems(0,heightfr)
        self.dlg.comboBox_22.insertItems(0,heightfr)
        self.dlg.comboBox_23.insertItems(0,heightfr)
        self.dlg.comboBox_24.insertItems(0,heightfr)
        self.dlg.comboBox_25.insertItems(0,heightfr)
        self.dlg.comboBox_26.insertItems(0,heightfr)
        self.dlg.comboBox_3.activated.connect(self.pervious_select1)
        self.dlg.comboBox_4.activated.connect(self.pervious_select2)
        self.dlg.comboBox_5.activated.connect(self.pervious_select3)
        self.dlg.comboBox_6.activated.connect(self.pervious_select4)
        self.dlg.comboBox_7.activated.connect(self.pervious_select5)
        self.dlg.comboBox_8.activated.connect(self.pervious_select6)
        self.dlg.comboBox_15.activated.connect(self.pervious_select7)
        self.dlg.comboBox_16.activated.connect(self.pervious_select8)
        
    def pervious_select1(self):
        self.urbanchoices = ['100% grass','100% decidious trees','100% evergreen trees','100% bare soil','100% water','50% grass, 25% dec. trees, 25% ev. trees','Each 20%']
        self.treechoices = ['100% evergreen', '100% decidious', '50% evergreen, 50% decidious','30% evergreen, 70% decidious','70% evergreen, 30% decidious']
        self.dlg.comboBox_9.clear()
        if (int(self.dlg.comboBox_3.currentText())<=10):
            self.dlg.comboBox_9.addItems(self.urbanchoices)
        if (int(self.dlg.comboBox_3.currentText())>100 and int(self.dlg.comboBox_3.currentText())<=103):
            self.dlg.comboBox_9.addItems(self.treechoices)
    def pervious_select2(self):
        self.dlg.comboBox_10.clear()
        if (int(self.dlg.comboBox_4.currentText())<=10):
            self.dlg.comboBox_10.addItems(self.urbanchoices)
        if (int(self.dlg.comboBox_4.currentText())>100 and int(self.dlg.comboBox_4.currentText())<=103):
            self.dlg.comboBox_10.addItems(self.treechoices)
    def pervious_select3(self):
        self.dlg.comboBox_11.clear()
        if (int(self.dlg.comboBox_5.currentText())<=10):
            self.dlg.comboBox_11.addItems(self.urbanchoices)
        if (int(self.dlg.comboBox_5.currentText())>100 and int(self.dlg.comboBox_5.currentText())<=103):
            self.dlg.comboBox_11.addItems(self.treechoices)
    def pervious_select4(self):
        self.dlg.comboBox_12.clear()
        if (int(self.dlg.comboBox_6.currentText())<=10):
            self.dlg.comboBox_12.addItems(self.urbanchoices)
        if (int(self.dlg.comboBox_6.currentText())>100 and int(self.dlg.comboBox_6.currentText())<=103):
            self.dlg.comboBox_12.addItems(self.treechoices)
    def pervious_select5(self):
        self.dlg.comboBox_13.clear()
        if (int(self.dlg.comboBox_7.currentText())<=10):
            self.dlg.comboBox_13.addItems(self.urbanchoices)
        if (int(self.dlg.comboBox_7.currentText())>100 and int(self.dlg.comboBox_7.currentText())<=103):
            self.dlg.comboBox_13.addItems(self.treechoices)
    def pervious_select6(self):
        self.dlg.comboBox_14.clear()
        if (int(self.dlg.comboBox_8.currentText())<=10):
            self.dlg.comboBox_14.addItems(self.urbanchoices)
        if (int(self.dlg.comboBox_8.currentText())>100 and int(self.dlg.comboBox_8.currentText())<=103):
            self.dlg.comboBox_14.addItems(self.treechoices)
    def pervious_select7(self):
        self.dlg.comboBox_17.clear()
        if (int(self.dlg.comboBox_15.currentText())<=10):
            self.dlg.comboBox_17.addItems(self.urbanchoices)
        if (int(self.dlg.comboBox_15.currentText())>100 and int(self.dlg.comboBox_15.currentText())<=103):
            self.dlg.comboBox_17.addItems(self.treechoices)
    def pervious_select8(self):
        self.dlg.comboBox_18.clear()
        if (int(self.dlg.comboBox_16.currentText())<=10):
            self.dlg.comboBox_18.addItems(self.urbanchoices)
        if (int(self.dlg.comboBox_16.currentText())>100 and int(self.dlg.comboBox_16.currentText())<=103):
            self.dlg.comboBox_18.addItems(self.treechoices)
    def updatetable(self):
        lczboxes = [self.dlg.comboBox_3,self.dlg.comboBox_4,self.dlg.comboBox_5,
                    self.dlg.comboBox_6,self.dlg.comboBox_7,self.dlg.comboBox_8,self.dlg.comboBox_15,self.dlg.comboBox_16]
        lcfrboxes = [self.dlg.comboBox_9,self.dlg.comboBox_10,self.dlg.comboBox_11,
                     self.dlg.comboBox_12,self.dlg.comboBox_13,self.dlg.comboBox_14,self.dlg.comboBox_17,self.dlg.comboBox_18]
        heightboxes = [self.dlg.comboBox_19,self.dlg.comboBox_20,self.dlg.comboBox_21,
                       self.dlg.comboBox_22,self.dlg.comboBox_23,self.dlg.comboBox_24,self.dlg.comboBox_25,self.dlg.comboBox_26]
        for x in range(len(lczboxes)): 
            lcz = int(lczboxes[x].currentText())
            if lcz>10:
                if (lcfrboxes[x].currentText()==self.treechoices[0] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-91).text())+float(self.dlg.tableWidget.item(1,lcz-91).text())+float(self.dlg.tableWidget.item(2,lcz-91).text())+float(self.dlg.tableWidget.item(5,lcz-91).text())+float(self.dlg.tableWidget.item(6,lcz-91).text())
                    self.dlg.tableWidget.setItem(4,lcz-91, QTableWidgetItem(str(1.-iperv)))
                    self.dlg.tableWidget.setItem(3,lcz-91, QTableWidgetItem(str(0.00)))
                if (lcfrboxes[x].currentText()==self.treechoices[1] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-91).text())+float(self.dlg.tableWidget.item(1,lcz-91).text())+float(self.dlg.tableWidget.item(2,lcz-91).text())+float(self.dlg.tableWidget.item(5,lcz-91).text())+float(self.dlg.tableWidget.item(6,lcz-91).text())
                    self.dlg.tableWidget.setItem(3,lcz-91, QTableWidgetItem(str(1.-iperv)))
                    self.dlg.tableWidget.setItem(4,lcz-91, QTableWidgetItem(str(0.00)))
                if (lcfrboxes[x].currentText()==self.treechoices[2] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-91).text())+float(self.dlg.tableWidget.item(1,lcz-91).text())+float(self.dlg.tableWidget.item(2,lcz-91).text())+float(self.dlg.tableWidget.item(5,lcz-91).text())+float(self.dlg.tableWidget.item(6,lcz-91).text())
                    self.dlg.tableWidget.setItem(3,lcz-91, QTableWidgetItem(str((1.-iperv)*0.5)))
                    self.dlg.tableWidget.setItem(4,lcz-91, QTableWidgetItem(str((1.-iperv)*0.5)))
                if (lcfrboxes[x].currentText()==self.treechoices[3] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-91).text())+float(self.dlg.tableWidget.item(1,lcz-91).text())+float(self.dlg.tableWidget.item(2,lcz-91).text())+float(self.dlg.tableWidget.item(5,lcz-91).text())+float(self.dlg.tableWidget.item(6,lcz-91).text())
                    self.dlg.tableWidget.setItem(3,lcz-91, QTableWidgetItem(str((1.-iperv)*0.7)))
                    self.dlg.tableWidget.setItem(4,lcz-91, QTableWidgetItem(str((1.-iperv)*0.3)))   
                if (lcfrboxes[x].currentText()==self.treechoices[4] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-91).text())+float(self.dlg.tableWidget.item(1,lcz-91).text())+float(self.dlg.tableWidget.item(2,lcz-91).text())+float(self.dlg.tableWidget.item(5,lcz-91).text())+float(self.dlg.tableWidget.item(6,lcz-91).text())
                    self.dlg.tableWidget.setItem(3,lcz-91, QTableWidgetItem(str((1.-iperv)*0.3)))
                    self.dlg.tableWidget.setItem(4,lcz-91, QTableWidgetItem(str((1.-iperv)*0.7)))
            if lcz<=10:
                if (lcfrboxes[x].currentText()==self.urbanchoices[0] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-1).text())+float(self.dlg.tableWidget.item(1,lcz-1).text())
                    self.dlg.tableWidget.setItem(2,lcz-1, QTableWidgetItem(str(1.-iperv)))
                    self.dlg.tableWidget.setItem(3,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(4,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(5,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(6,lcz-1, QTableWidgetItem(str(0.00)))
                if (lcfrboxes[x].currentText()==self.urbanchoices[1] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-1).text())+float(self.dlg.tableWidget.item(1,lcz-1).text())
                    self.dlg.tableWidget.setItem(3,lcz-1, QTableWidgetItem(str(1.-iperv)))
                    self.dlg.tableWidget.setItem(2,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(4,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(5,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(6,lcz-1, QTableWidgetItem(str(0.00)))
                if (lcfrboxes[x].currentText()==self.urbanchoices[2] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-1).text())+float(self.dlg.tableWidget.item(1,lcz-1).text())
                    self.dlg.tableWidget.setItem(4,lcz-1, QTableWidgetItem(str(1.-iperv)))
                    self.dlg.tableWidget.setItem(2,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(3,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(5,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(6,lcz-1, QTableWidgetItem(str(0.00)))
                if (lcfrboxes[x].currentText()==self.urbanchoices[3] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-1).text())+float(self.dlg.tableWidget.item(1,lcz-1).text())
                    self.dlg.tableWidget.setItem(5,lcz-1, QTableWidgetItem(str(1.-iperv)))
                    self.dlg.tableWidget.setItem(2,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(3,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(4,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(6,lcz-1, QTableWidgetItem(str(0.00)))
                if (lcfrboxes[x].currentText()==self.urbanchoices[4] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-1).text())+float(self.dlg.tableWidget.item(1,lcz-1).text())
                    self.dlg.tableWidget.setItem(6,lcz-1, QTableWidgetItem(str(1.-iperv)))
                    self.dlg.tableWidget.setItem(2,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(3,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(4,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(5,lcz-1, QTableWidgetItem(str(0.00)))
                if (lcfrboxes[x].currentText()==self.urbanchoices[5] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-1).text())+float(self.dlg.tableWidget.item(1,lcz-1).text())
                    self.dlg.tableWidget.setItem(2,lcz-1, QTableWidgetItem(str((1.-iperv)*0.5)))
                    self.dlg.tableWidget.setItem(3,lcz-1, QTableWidgetItem(str((1.-iperv)*0.25)))
                    self.dlg.tableWidget.setItem(4,lcz-1, QTableWidgetItem(str((1.-iperv)*0.25)))
                    self.dlg.tableWidget.setItem(5,lcz-1, QTableWidgetItem(str(0.00)))
                    self.dlg.tableWidget.setItem(6,lcz-1, QTableWidgetItem(str(0.00)))
                if (lcfrboxes[x].currentText()==self.urbanchoices[6] ):
                    iperv=float(self.dlg.tableWidget.item(0,lcz-1).text())+float(self.dlg.tableWidget.item(1,lcz-1).text())
                    self.dlg.tableWidget.setItem(2,lcz-1, QTableWidgetItem(str((1.-iperv)*0.2)))
                    self.dlg.tableWidget.setItem(3,lcz-1, QTableWidgetItem(str((1.-iperv)*0.2)))
                    self.dlg.tableWidget.setItem(4,lcz-1, QTableWidgetItem(str((1.-iperv)*0.2)))
                    self.dlg.tableWidget.setItem(5,lcz-1, QTableWidgetItem(str((1.-iperv)*0.2)))
                    self.dlg.tableWidget.setItem(6,lcz-1, QTableWidgetItem(str((1.-iperv)*0.2)))

    def start_progress(self):
        self.steps = 0
        poly = self.layerComboManagerPolygrid.getLayer()
        if poly is None:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return
        if not poly.geometryType() == 2:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return
        vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")
        prov = vlayer.dataProvider()
        fields = prov.fields()
        idx = vlayer.fieldNameIndex('id')
        typetest = fields.at(idx).type()
        if typetest == 10:
            QMessageBox.critical(None, "ID field is sting type", "ID field must be either integer or float")
            return
        self.dlg.progressBar.setMaximum(vlayer.featureCount())
        dir_poly = self.plugin_dir + '/data/poly_temp.shp'

        lc_grid = self.layerComboManagerLCgrid.getLayer()
        if lc_grid is None:
            QMessageBox.critical(None, "Error", "No valid raster layer is selected")
            return
        if self.folderPath == 'None':
            QMessageBox.critical(None, "Error", "Select a valid output folder")
            return
        # self.iface.messageBar().pushMessage("test: ", str(test))

        self.startWorker(lc_grid, poly, vlayer, prov, fields, idx, dir_poly, self.iface,
                         self.plugin_dir, self.folderPath, self.dlg)
        
    def startWorker(self, lc_grid, poly, vlayer, prov, fields, idx, dir_poly, iface, plugin_dir,
                    folderPath, dlg):

        worker = Worker(lc_grid, poly, vlayer, prov, fields, idx, dir_poly, iface,
                        plugin_dir, folderPath, dlg)

        self.dlg.runButton.setText('Cancel')
        self.dlg.runButton.clicked.disconnect()
        self.dlg.runButton.clicked.connect(worker.kill)
        self.dlg.pushButton_3.setEnabled(False)

        thread = QThread(self.dlg)
        worker.moveToThread(thread)
        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        worker.progress.connect(self.progress_update)
        thread.started.connect(worker.run)
        thread.start()
        self.thread = thread
        self.worker = worker

    def workerFinished(self, ret):
        try:
            self.worker.deleteLater()
        except RuntimeError:
            pass
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()

        if ret == 1:
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.pushButton_3.setEnabled(True)
            self.dlg.progressBar.setValue(0)
            # QMessageBox.information(None, "Image Morphometric Parameters",
            #                         "Process finished! Check General Messages (speech bubble, lower left) "
            #                         "to obtain information of the process.")
            self.iface.messageBar().pushMessage("Land Cover Fraction Grid",
                                    "Process finished! Check General Messages (speech bubble, lower left) "
                                    "to obtain information of the process.", duration=5)
        else:
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.pushButton_3.setEnabled(True)
            self.dlg.progressBar.setValue(0)
            QMessageBox.information(None, "Land Cover Fraction Grid", "Operations cancelled, "
                                                                           "process unsuccessful! See the General tab in Log Meassages Panel (speech bubble, lower right) for more information.")

    def workerError(self, errorstring):
        #strerror = "Worker thread raised an exception: " + str(e)
        QgsMessageLog.logMessage(errorstring, level=QgsMessageLog.CRITICAL)

    def progress_update(self):
        self.steps +=1
        self.dlg.progressBar.setValue(self.steps)
    #
    # def saveraster(self, gdal_data, filename, raster):
    #     rows = gdal_data.RasterYSize
    #     cols = gdal_data.RasterXSize
    #     outDs = gdal.GetDriverByName("GTiff").Create(filename, cols, rows, int(1), GDT_Float32)
    #     outBand = outDs.GetRasterBand(1)
    #     outBand.WriteArray(raster, 0, 0)
    #     outBand.FlushCache()
    #     outBand.SetNoDataValue(-9999)
    #     outDs.SetGeoTransform(gdal_data.GetGeoTransform())
    #     outDs.SetProjection(gdal_data.GetProjection())
    #     del outDs, outBand

    def run(self):
        self.dlg.show()
        self.dlg.exec_()
        gdal.UseExceptions()
        gdal.AllRegister()

    def help(self):
        # url = "file://" + self.plugin_dir + "/help/Index.html"
        url = 'http://www.urban-climate.net/umep/UMEP_Manual#Urban_Land_Cover:_Land_Cover_Fraction_.28Grid.29'
        webbrowser.open_new_tab(url)
