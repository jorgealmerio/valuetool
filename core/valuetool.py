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
from qgis.PyQt.QtWidgets import QAction, QDockWidget
from qgis.core import *

from .valuewidget import ValueWidget
from .valuemaptool import ValueMapTool

#from selectPointTool import *
# initialize Qt resources from file resouces.py
from . import resources_rc

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

    # create the widget to display information
    self.valuewidget = ValueWidget(self.iface)
    self.valuewidget.cbxClick.setVisible(False) #Almerio: disabled until find error cause on using it
    
    #self.tool.moved.connect(self.valuewidget.toolMoved) #Almerio: desativei essa linha
    #self.tool.pressed.connect(self.valuewidget.toolPressed) #Almerio: desativei essa linha
    self.valuewidget.cbxEnable.clicked.connect(self.toggleTool)
    self.valuewidget.cbxClick.clicked.connect(self.toggleMouseClick)

    # create the dockwidget with the correct parent and add the valuewidget
    self.valuedockwidget=QDockWidget("Value Tool" , self.iface.mainWindow() )
    self.valuedockwidget.setObjectName("Value Tool")
    self.valuedockwidget.setWidget(self.valuewidget)
    #QObject.connect(self.valuedockwidget, SIGNAL('visibilityChanged ( bool )'), self.showHideDockWidget)
    
    # add the dockwidget to iface
    self.iface.addDockWidget(Qt.LeftDockWidgetArea,self.valuedockwidget)
    #self.valuewidget.show()

  def unload(self):
    QSettings().setValue('plugins/valuetool/mouseClick', self.valuewidget.cbxClick.isChecked())
    self.valuedockwidget.close()
    #self.deactivateTool() #Almerio: error on unload plugin, so I disabled this line
    # remove the dockwidget from iface
    self.iface.removeDockWidget(self.valuedockwidget)
    # remove the plugin menu item and icon
    #self.iface.removePluginMenu("Analyses",self.action)
    self.iface.removeToolBarIcon(self.action)

  def toggleTool(self, active):
    self.activateTool() if active else self.deactivateTool()

  def toggleMouseClick(self, toggle):
    if toggle:
      self.activateTool(False)
    else:
      self.deactivateTool(False)
    self.valuewidget.changeActive(False, False)
    self.valuewidget.changeActive(True, False)
      
  def activateTool(self, changeActive=True):
    if self.valuewidget.cbxClick.isChecked():
      self.saveTool=self.canvas.mapTool()
      self.canvas.setMapTool(self.tool)
    if not self.valuedockwidget.isVisible():
      self.valuedockwidget.show()
    if changeActive:
      self.valuewidget.changeActive(True)

  def deactivateTool(self, changeActive=True):
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
        
