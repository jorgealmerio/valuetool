"""
/***************************************************************************
         Value Tool       - A QGIS plugin to get values at the mouse pointer
                             -------------------
    begin                : 2008-08-26
    copyright            : (C) 2008 by G. Picard
    email                : 
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""
from __future__ import absolute_import
from builtins import object

from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QApplication
from qgis.core import *

from .valuewidget import ValueWidget
from .valuemaptool import ValueMapTool

#from selectPointTool import *
# initialize Qt resources from file resouces.py
from . import resources_rc


# To run TooltipRasterMapTool()
from qgis.core import QgsApplication, QgsRasterLayer, QgsRaster
from qgis.gui import QgsMapToolEmitPoint
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import ( QMessageBox, QIcon, QAction, QMenu, QActionGroup,
                          QWidgetAction, QToolTip )



class TooltipRasterMapTool(QgsMapToolEmitPoint):
  # Taken from https://gis.stackexchange.com/a/245398/
  def __init__(self, iface):
    self.iface = iface
    self.canvas = self.iface.mapCanvas()
    QgsMapToolEmitPoint.__init__(self, self.canvas)
    self.timerMapTips = QTimer( self.canvas )
    self.timerMapTips.timeout.connect(self.showMapTip)

  def canvasPressEvent(self, e):
    pass

  def canvasReleaseEvent(self, e):
    pass

  def canvasMoveEvent(self, e):
    if self.canvas.underMouse(): # Only if mouse is over the map
      self.timerMapTips.start(0) # time in milliseconds"""

  def deactivate(self):
    self.timerMapTips.stop()

  def showMapTip( self ):
    self.timerMapTips.stop()
    if self.canvas.underMouse():
      rLayer = self.iface.activeLayer()
      if type(rLayer) is QgsRasterLayer:
        ident = rLayer.dataProvider().identify( self.toMapCoordinates(self.canvas.mouseLastXY()), QgsRaster.IdentifyFormatValue )
        if ident.isValid():
          text = ", ".join(['{0:g}'.format(r) for r in ident.results().values() if r is not None] )
        else:
          text = "Non valid value"
        last_xy = self.canvas.mouseLastXY()
        posGlobal = self.canvas.mapToGlobal(last_xy)
        QToolTip.showText(posGlobal, text, self.canvas)


class ValueTool(object):
  def __init__(self, iface):
    # save reference to the QGIS interface
    self.iface = iface
    self.canvas=self.iface.mapCanvas()

  def initGui(self):
    # create action that will start plugin configuration
    #self.action = QAction(QIcon(":/plugins/valuetool/icon.png"), "Value Tool", self.iface.getMainWindow())
    #self.action.setWhatsThis("Value Tool")
    #QObject.connect(self.action, SIGNAL("activated()"), self.run)
    ## add toolbar button and menu item
    #self.iface.addToolBarIcon(self.action)
    #self.iface.addPluginMenu("Analyses", self.action)
    ## add the tool to select feature
    #self.tool = selectPointTool(self.iface.getMapCanvas(),self.action)

    # add action to toolbar
    self.action=QAction(QIcon(":/plugins/valuetool/icon.svg"), "Value Tool", self.iface.mainWindow())
    self.iface.addToolBarIcon(self.action)
    self.tool=ValueMapTool(self.canvas, self.action)
    self.saveTool=None
    self.action.triggered.connect(self.activateTool)
    #self.tool.deactivate.connect(self.deactivateTool) #Almerio: desativei essa linha
    self.tooltipRaster = TooltipRasterMapTool(self.iface)

    # create the widget to display information
    self.valuewidget = ValueWidget(self.iface)
    self.valuewidget.cbxClick.setVisible(False) #Almerio: disabled until find error cause on using it
    self.valuewidget.cbxEnableToolTip.setEnabled(False)
    
    #self.tool.moved.connect(self.valuewidget.toolMoved) #Almerio: desativei essa linha
    #self.tool.pressed.connect(self.valuewidget.toolPressed) #Almerio: desativei essa linha
    self.valuewidget.cbxEnable.clicked.connect(self.toggleTool)
    self.valuewidget.cbxEnableToolTip.clicked.connect(self.toggleToolTip)
    self.valuewidget.cbxClick.clicked.connect(self.toggleMouseClick)
    # self.valuewidget.btnSaveSettings.clicked.connect(self.saveSettings) #btn to save settings suppressed, save settings on unloading

    # create the dockwidget with the correct parent and add the valuewidget
    self.valuedockwidget=QDockWidget("Value Tool" , self.iface.mainWindow() )
    self.valuedockwidget.setObjectName("Value Tool")
    self.valuedockwidget.setWidget(self.valuewidget)
    #QObject.connect(self.valuedockwidget, SIGNAL('visibilityChanged ( bool )'), self.showHideDockWidget)
    
    # add the dockwidget to iface
    self.iface.addDockWidget(Qt.LeftDockWidgetArea,self.valuedockwidget)
    #self.valuewidget.show()
  
  #save settings
  def saveSettings(self):    
    QSettings().setValue('plugins/valuetool/cbxEnable', self.valuewidget.cbxEnable.isChecked())
    QSettings().setValue('plugins/valuetool/cbxDigits', self.valuewidget.cbxDigits.isChecked())
    QSettings().setValue('plugins/valuetool/spinDigits', self.valuewidget.spinDigits.value())
    QSettings().setValue('plugins/valuetool/tableWidget/Col0Width', self.valuewidget.tableWidget.columnWidth(0)) #first column 'Layer'
    QSettings().setValue('plugins/valuetool/tableWidget/Col1Width', self.valuewidget.tableWidget.columnWidth(1)) #second column 'value'
    #QSettings().setValue('plugins/valuetool/mouseClick', self.valuewidget.cbxClick.isChecked())
    ##self.iface.messageBar().pushMessage("Value Tool", "Settings saved!", level=Qgis.Info, duration=5)

  def unload(self):    
    self.saveSettings()
    self.valuedockwidget.close()
    #self.deactivateTool() #Almerio: error on unload plugin, so I disabled this line
    # remove the dockwidget from iface
    self.iface.removeDockWidget(self.valuedockwidget)
    # remove the plugin menu item and icon
    #self.iface.removePluginMenu("Analyses",self.action)
    self.iface.removeToolBarIcon(self.action)

  def toggleTool(self, active):
    self.activateTool() if active else self.deactivateTool()
  
  def toggleToolTip(self, active):
    if active:
      self.iface.mapCanvas().setMapTool(self.tooltipRaster)
    else:
      self.iface.mapCanvas().unsetMapTool(self.tooltipRaster) 

  def toggleMouseClick(self, toggle):
    if toggle:
      self.activateTool(False)
    else:
      self.deactivateTool(False)
    self.valuewidget.changeActive(False, False)
    self.valuewidget.changeActive(True, False)
      
  def activateTool(self, changeActive=True):
    self.canvas.setCursor(self.tool.cursor)
    if self.valuewidget.cbxClick.isChecked():
      self.saveTool=self.canvas.mapTool()
      self.canvas.setMapTool(self.tool)
    if not self.valuedockwidget.isVisible():
      self.valuedockwidget.show()
    if changeActive:
      self.valuewidget.changeActive(True)
      self.valuewidget.cbxEnableToolTip.setEnabled(True)
      if self.valuewidget.cbxEnableToolTip.isChecked():
        self.toggleToolTip(True)

  def deactivateTool(self, changeActive=True):
    QApplication.restoreOverrideCursor()
    if self.canvas.mapTool() and self.canvas.mapTool() == self.tool:
      # block signals to avoid recursion
      self.tool.blockSignals(True)
      if self.saveTool:
        self.canvas.setMapTool(self.saveTool)
        self.saveTool=None
      else:
        self.canvas.unsetMapTool(self.tool)
      self.tool.blockSignals(False)
    if changeActive:
      self.valuewidget.changeActive(False)
      self.valuewidget.cbxEnableToolTip.setEnabled(False)
      self.toggleToolTip(False)
        
