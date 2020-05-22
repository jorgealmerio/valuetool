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
from __future__ import print_function
from builtins import str
from builtins import range

import logging
# change the level back to logging.WARNING(the default) before releasing
logging.basicConfig(level=logging.DEBUG)

from qgis.PyQt import QtCore, QtGui
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.core import *

from .ui_valuewidgetbase import Ui_ValueWidgetBase as Ui_Widget

hasqwt=True
try:
    from PyQt.Qwt5 import QwtPlot,QwtPlotCurve,QwtScaleDiv,QwtSymbol
except:
    hasqwt=False

#test if matplotlib >= 1.0
hasmpl=True
try:
    import matplotlib
    import matplotlib.pyplot as plt 
    import matplotlib.ticker as ticker
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
except:
    hasmpl=False
if hasmpl:
    if int(matplotlib.__version__[0]) < 1:
        hasmpl = False

debug=0

class ValueWidget(QWidget, Ui_Widget):

    def __init__(self, iface):

        self.hasqwt=hasqwt
        self.hasmpl=hasmpl
        self.layerMap=dict()
        self.statsChecked=False
        self.ymin=0
        self.ymax=250
        self.isActive=False

        # Statistics (>=1.9)
        self.statsSampleSize = 2500000
        self.stats = {} # stats per layer

        self.layersSelected=[]
        self.layerBands=dict()

        self.iface=iface
        self.canvas=self.iface.mapCanvas()
        self.updateLayersAll() #self.iface.legendInterface()
        self.logger = logging.getLogger('.'.join((__name__, 
                                        self.__class__.__name__)))

        QWidget.__init__(self)
        self.setupUi(self)
        self.tabWidget.setEnabled(False)
        self.cbxClick.setChecked( QSettings().value('plugins/valuetool/mouseClick', False, type=bool ) )

        #self.setupUi_plot()
        #don't setup plot until Plot tab is clicked - workaround for bug #7450
        #qgis will still crash in some cases, but at least the tool can be used in Table mode
        self.qwtPlot = None
        self.mplPlot = None
        self.mplLine = None

        self.plotSelector.currentIndexChanged .connect(self.changePlot)
        self.tabWidget.currentChanged .connect(self.tabWidgetChanged)
        self.cbxLayers.currentIndexChanged .connect(self.updateLayers)
        self.cbxBands.currentIndexChanged .connect(self.updateLayers)
        self.tableWidget2.cellChanged .connect(self.layerSelected)

    def setupUi_plot(self):

        # plot
        self.plotSelector.setVisible( False )
        self.cbxStats.setVisible( False )
        # stats by default because estimated are fast
        self.cbxStats.setChecked( True )
        self.plotSelector.addItem( 'Qwt' )
        self.plotSelector.addItem( 'mpl' )

        # Page 2 - qwt
        if self.hasqwt:
            self.qwtPlot = QwtPlot(self.stackedWidget)
            self.qwtPlot.setAutoFillBackground(False)
            self.qwtPlot.setObjectName("qwtPlot")
            self.curve = QwtPlotCurve()
            self.curve.setSymbol(
                QwtSymbol(QwtSymbol.Ellipse,
                          QBrush(Qt.white),
                          QPen(Qt.red, 2),
                          QSize(9, 9)))
            self.curve.attach(self.qwtPlot)
        else:
            self.qwtPlot = QLabel("Need Qwt >= 5.0 or matplotlib >= 1.0 !")

        sizePolicy = QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.qwtPlot.sizePolicy().hasHeightForWidth())
        self.qwtPlot.setSizePolicy(sizePolicy)
        self.qwtPlot.updateGeometry()
        self.stackedWidget.addWidget(self.qwtPlot)

        #Page 3 - matplotlib
        self.mplLine = None #make sure to invalidate when layers change
        if self.hasmpl:
            # mpl stuff
            # should make figure light gray
            self.mplBackground = None #http://www.scipy.org/Cookbook/Matplotlib/Animations
            self.mplFig = plt.Figure(facecolor='w', edgecolor='w')
            self.mplFig.subplots_adjust(left=0.1, right=0.975, bottom=0.13, top=0.95)
            self.mplPlt = self.mplFig.add_subplot(111)   
            self.mplPlt.tick_params(axis='both', which='major', labelsize=12)
            self.mplPlt.tick_params(axis='both', which='minor', labelsize=10)                           
            # qt stuff
            self.pltCanvas = FigureCanvasQTAgg(self.mplFig)
            self.pltCanvas.setParent(self.stackedWidget)
            self.pltCanvas.setAutoFillBackground(False)
            self.pltCanvas.setObjectName("mplPlot")
            self.mplPlot = self.pltCanvas
        else:
            self.mplPlot = QLabel("Need Qwt >= 5.0 or matplotlib >= 1.0 !")

        sizePolicy = QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.mplPlot.sizePolicy().hasHeightForWidth())
        self.mplPlot.setSizePolicy(sizePolicy)
        self.mplPlot.updateGeometry()
        self.stackedWidget.addWidget(self.mplPlot)

        if (self.hasqwt and self.hasmpl):
            self.plotSelector.setEnabled(True)
            self.plotSelector.setVisible(True)
            self.plotSelector.setCurrentIndex(0);
        else:
            if self.hasqwt:
                self.plotSelector.setCurrentIndex(0);
            else:
                self.plotSelector.setCurrentIndex(1);
        self.changePlot()

    def keyPressEvent( self, e ):
      if ( e.modifiers() == Qt.ControlModifier or e.modifiers() == Qt.MetaModifier ) and e.key() == Qt.Key_C:
        items = ''
        for rec in range( self.tableWidget.rowCount() ):
          items += '"' + self.tableWidget.item( rec, 0 ).text() + '",' + self.tableWidget.item( rec, 1 ).text() + "\n"
        if not items == '':
          clipboard = QApplication.clipboard()
          clipboard.setText( items )
      else:
        QWidget.keyPressEvent( self, e )

    def changePlot(self):
        if (self.plotSelector.currentText()=='mpl'):
            self.stackedWidget.setCurrentIndex(1)
        else:
            self.stackedWidget.setCurrentIndex(0)

    def changeActive(self,active,gui=True):
        self.isActive=active
        
        if (active):
            self.cbxEnable.setCheckState(Qt.Checked)
            self.canvas.layersChanged .connect(self.invalidatePlot)
            if not self.cbxClick.isChecked():
                self.canvas.xyCoordinates.connect(self.printValue)
        else:
            self.cbxEnable.setCheckState(Qt.Unchecked)
            self.canvas.layersChanged.disconnect(self.invalidatePlot)
            self.canvas.xyCoordinates.disconnect(self.printValue)

        if gui:
            self.tabWidget.setEnabled(active)
            if active:
                self.labelStatus.setText(self.tr("Value tool is enabled"))
                if self.tabWidget.currentIndex()==2:
                    self.updateLayers()
            else:
                self.labelStatus.setText(self.tr(""))
                #use this to clear plot when deactivated
                #self.values=[]
                #self.showValues()

    def activeRasterLayers(self, index=None):
        layers=[]
        allLayers=[]

        if not index: 
            index=self.cbxLayers.currentIndex()
        if index == 0: #visible layers
            allLayers=self.canvas.layers()            
        elif index == 1: #all layers
            allLayers=self.legend
        elif index == 2:
            for layer in self.legend:
                if layer.id() in self.layersSelected:
                    allLayers.append(layer)

        for layer in allLayers:
            if layer!=None and layer.isValid() and \
                    layer.type()==QgsMapLayer.RasterLayer and \
                    layer.dataProvider() and \
                    (layer.dataProvider().capabilities() & QgsRasterDataProvider.IdentifyValue):
                  layers.append(layer)

        return layers

    def activeBandsForRaster(self,layer):
        activeBands=[]

        if self.cbxBands.currentIndex() == 1 and layer.renderer():
            activeBands = layer.renderer().usesBands()                 
        elif self.cbxBands.currentIndex() == 2:
            if layer.bandCount()==1:
                activeBands=[1]
            else:
                activeBands = self.layerBands[layer.id()] if (layer.id() in self.layerBands) else []
        else:
            activeBands = list(range(1,layer.bandCount()+1))
        
        return activeBands

    def printValue(self,position):

        if debug > 0:
            print(position)

        if not position:
            return
        if self.tabWidget.currentIndex()==2:
            return

        if debug > 0:
            print("%d active rasters, %d canvas layers" %(len(self.activeRasterLayers()),self.canvas.layerCount()))
        layers = self.activeRasterLayers()
        if len(layers) == 0:
            if self.canvas.layerCount() > 0:
                self.labelStatus.setText(self.tr("No valid layers to display - change layers in options"))
            else:
                self.labelStatus.setText(self.tr("No valid layers to display"))
            self.values=[]         
            self.showValues()
            return
        
        self.labelStatus.setText(self.tr('Coordinate:') + ' (%f, %f)' % (position.x(), position.y()))

        needextremum = (self.tabWidget.currentIndex()==1) # if plot is shown

        # count the number of requires rows and remember the raster layers
        nrow=0
        rasterlayers=[]
        layersWOStatistics=[]

        for layer in layers:

            nrow+=layer.bandCount()
            rasterlayers.append(layer)

            # check statistics for each band
            if needextremum:
                for i in range( 1,layer.bandCount()+1 ):
                    has_stats = self.getStats ( layer, i ) is not None
                    if not layer.id() in self.layerMap and not has_stats\
                            and not layer in layersWOStatistics:
                        layersWOStatistics.append(layer)

        if layersWOStatistics and not self.statsChecked:
          self.calculateStatistics(layersWOStatistics)
                  
        irow=0
        self.values=[]
        self.ymin=1e38
        self.ymax=-1e38

        mapCanvasSrs = self.iface.mapCanvas().mapSettings().destinationCrs() #era self.iface.mapCanvas().mapRenderer().destinationCrs()

        # TODO - calculate the min/max values only once, instead of every time!!!
        # keep them in a dict() with key=layer.id()
                
        for layer in rasterlayers:
            layername=str(layer.name())
            layerSrs = layer.crs()

            pos = position         

            # if given no position, get dummy values
            if position is None:
                pos = QgsPoint(0,0)
            # transform points if needed
            elif not mapCanvasSrs == layerSrs: #Almerio: and self.iface.mapCanvas().hasCrsTransformEnabled(): 
              srsTransform = QgsCoordinateTransform(mapCanvasSrs, layerSrs, QgsProject.instance())
              try:
                pos = srsTransform.transform(position)
              except QgsCsException as err:
                # ignore transformation errors
                continue

            if True: # for QGIS >= 1.9
              if not layer.dataProvider():
                continue

              ident = None
              if position is not None:
                canvas = self.iface.mapCanvas()

                # first test if point is within map layer extent 
                # maintain same behaviour as in 1.8 and print out of extent
                if not layer.dataProvider().extent().contains( pos ):
                  ident = dict()
                  for iband in range(1,layer.bandCount()+1):
                    ident[iband] = str(self.tr('out of extent'))
                # we can only use context if layer is not projected
                elif layer.dataProvider().crs() != canvas.mapSettings().destinationCrs(): #Almerio: tinha no inicio: "canvas.hasCrsTransformEnabled() and " but it is always enabled
                  ident = layer.dataProvider().identify(pos, QgsRaster.IdentifyFormatValue ).results()
                else:
                  extent = canvas.extent()
                  width = round(extent.width() / canvas.mapUnitsPerPixel());
                  height = round(extent.height() / canvas.mapUnitsPerPixel());

                  extent = canvas.mapSettings().mapToLayerCoordinates( layer, extent );

                  ident = layer.dataProvider().identify(pos, QgsRaster.IdentifyFormatValue, canvas.extent(), width, height ).results()
                if not len( ident ) > 0:
                    continue

              # if given no position, set values to 0
              if position is None and ident is not None and iter(ident.keys()) is not None:
                  for key in ident.keys():
                      ident[key] = layer.dataProvider().noDataValue(key)

              # bands displayed depends on cbxBands (all / active / selected)
              activeBands = self.activeBandsForRaster(layer) 
                  
              for iband in activeBands: # loop over the active bands
                layernamewithband=layername
                if ident is not None and len(ident)>1:
                    layernamewithband+=' '+layer.bandName(iband)

                if not ident or iband not in ident: # should not happen
                  bandvalue = "?"
                else:
                  bandvalue = ident[iband]
                  if bandvalue is None:
                      bandvalue = "no data"
             
                self.values.append((layernamewithband,str(bandvalue)))

                if needextremum:
                  # estimated statistics
                  stats = self.getStats ( layer, iband )
                  if stats:
                    self.ymin=min(self.ymin,stats.minimumValue)
                    self.ymax=max(self.ymax,stats.maximumValue)

        if len(self.values) == 0:
            self.labelStatus.setText(self.tr("No valid bands to display"))

        self.showValues()

    def showValues(self):
        if self.tabWidget.currentIndex()==1:
            #TODO don't plot if there is no data to plot...
            self.plot()
        else:
            self.printInTable()

    def calculateStatistics(self,layersWOStatistics):
        
        self.invalidatePlot(False)

        self.statsChecked = True

        layerNames = []
        for layer in layersWOStatistics:
            if not layer.id() in self.layerMap:
                layerNames.append(layer.name())

        if ( len(layerNames) != 0 ):
            if not self.cbxStats.isChecked():
                for layer in layersWOStatistics:
                    self.layerMap[layer.id()] = True
                return
        else:
            print('ERROR, no layers to get stats for')
        
        save_state=self.isActive
        self.changeActive(False, False) # deactivate

        # calculate statistics
        for layer in layersWOStatistics:
            if not layer.id() in self.layerMap:
                self.layerMap[layer.id()] = True
                for i in range( 1,layer.bandCount()+1 ):
                    self.getStats ( layer, i , True )

        if save_state:
            self.changeActive(True, False) # activate if necessary

    # get cached statistics for layer and band or None if not calculated
    def getStats ( self, layer, bandNo, force = False ):
      if layer in self.stats:
        if bandNo in self.stats[layer] : 
          return self.stats[layer][bandNo]
      else:
        self.stats[layer] = {}
      
      if force or layer.dataProvider().hasStatistics( bandNo, QgsRasterBandStats.Min | QgsRasterBandStats.Min, QgsRectangle(), self.statsSampleSize ):
        self.stats[layer][bandNo] = layer.dataProvider().bandStatistics( bandNo, QgsRasterBandStats.Min | QgsRasterBandStats.Min, QgsRectangle(), self.statsSampleSize )
        return self.stats[layer][bandNo]

      return None

    def printInTable(self):

        # set table widget row count
        self.tableWidget.setRowCount(len(self.values))

        irow=0
        for row in self.values:
          layername,value=row
          
          # limit number of decimal places if requested
          if self.cbxDigits.isChecked():
              try:
                  value = str("{0:."+str(self.spinDigits.value())+"f}").format(float(value))
              except ValueError:
                  pass

          if (self.tableWidget.item(irow,0)==None):
              # create the item
              self.tableWidget.setItem(irow,0,QTableWidgetItem())
              self.tableWidget.setItem(irow,1,QTableWidgetItem())

          self.tableWidget.item(irow,0).setText(layername)
          self.tableWidget.item(irow,1).setText(value)
          irow+=1


    def plot(self):
        numvalues=[]
        if ( self.hasqwt or self.hasmpl ):
            for row in self.values:
                layername,value=row
                try:
                    numvalues.append(float(value))
                except:
                    numvalues.append(0)

        ymin = self.ymin
        ymax = self.ymax
        if self.leYMin.text() != '' and self.leYMax.text() != '': 
            ymin = float(self.leYMin.text())
            ymax = float(self.leYMax.text())        

        if ( self.hasqwt and (self.plotSelector.currentText()=='Qwt') ):

            self.qwtPlot.setAxisMaxMinor(QwtPlot.xBottom,0)
            #self.qwtPlot.setAxisMaxMajor(QwtPlot.xBottom,0)
            self.qwtPlot.setAxisScale(QwtPlot.xBottom,1,len(self.values))
            #self.qwtPlot.setAxisScale(QwtPlot.yLeft,self.ymin,self.ymax)
            self.qwtPlot.setAxisScale(QwtPlot.yLeft,ymin,ymax)
            
            self.curve.setData(list(range(1,len(numvalues)+1)), numvalues)
            self.qwtPlot.replot()
            self.qwtPlot.setVisible(len(numvalues)>0)

        elif ( self.hasmpl and (self.plotSelector.currentText()=='mpl') ):

            self.mplPlt.clear()
            self.mplPlt.plot(list(range(1,len(numvalues)+1)), numvalues, marker='o', color='k', mfc='b', mec='b')
            self.mplPlt.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            self.mplPlt.yaxis.set_minor_locator(ticker.AutoMinorLocator())
            self.mplPlt.set_xlim( (1-0.25,len(self.values)+0.25 ) )
            self.mplPlt.set_ylim( (ymin, ymax) ) 
            self.mplFig.canvas.draw()

    def invalidatePlot(self,replot=True):
        if self.tabWidget.currentIndex()==2:
            self.updateLayers()
        if not self.isActive:
            return
        self.statsChecked = False
        if self.mplLine is not None:
            del self.mplLine
            self.mplLine = None
        #update empty plot
        if replot and self.tabWidget.currentIndex()==1:
            #self.values=[]
            self.printValue( None )

    def resizeEvent(self, event):
        self.invalidatePlot()

    def tabWidgetChanged(self):
        if self.tabWidget.currentIndex()==1 and not self.qwtPlot:
            self.setupUi_plot()
        if self.tabWidget.currentIndex()==2:
            self.updateLayers()
    
    # update list of All project layers
    def updateLayersAll(self):
        self.legend= list(QgsProject.instance().mapLayers().values())
    
    # update active layers in table
    def updateLayers(self):
        self.updateLayersAll()
        if self.tabWidget.currentIndex()!=2:
            return

        if self.cbxLayers.currentIndex() == 0:
            layers = self.activeRasterLayers(0)
        else:
            layers = self.activeRasterLayers(1)

        self.tableWidget2.blockSignals(True)
        self.tableWidget2.clearContents()
        self.tableWidget2.setRowCount(len(layers))
        self.tableWidget2.horizontalHeader().resizeSection(0, 20)
        self.tableWidget2.horizontalHeader().resizeSection(2, 20)

        j=0
        for layer in layers:

            item = QTableWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if self.cbxLayers.currentIndex() != 2:
                item.setFlags(item.flags() &~ Qt.ItemIsEnabled)
                item.setCheckState(Qt.Checked)
            else:
                if layer.id() in self.layersSelected:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
            self.tableWidget2.setItem(j, 0, item)
            item = QTableWidgetItem(layer.name())
            item.setData(Qt.UserRole, layer.id())
            self.tableWidget2.setItem(j, 1, item)
            activeBands = self.activeBandsForRaster(layer) 
            button = QToolButton()
            button.setText("#") # TODO add edit? icon
            button.setPopupMode(QToolButton.InstantPopup)
            group=QActionGroup(button)
            group.setExclusive( False )
            group.triggered.connect(self.bandSelected)
            if self.cbxBands.currentIndex()==2 and layer.bandCount()>1:
                menu=QMenu()
                menu.installEventFilter(self)

                for iband in range(1,layer.bandCount()+1):
                    action = QAction(str(layer.bandName(iband)),group)
                    action.setData([layer.id(),iband,j,False])
                    action.setCheckable(True)
                    action.setChecked(iband in activeBands)
                    menu.addAction(action)
                if layer.bandCount() > 1:
                    action = QAction(str(self.tr("All")),group)
                    action.setData([layer.id(),-1,j,True])
                    action.setCheckable(False)
                    menu.addAction(action)
                    action = QAction(str(self.tr("None")),group)
                    action.setData([layer.id(),-1,j,False])
                    action.setCheckable(False)
                    menu.addAction(action)

                button.setMenu(menu)
            else:
                button.setEnabled(False)
            self.tableWidget2.setCellWidget(j, 2, button)
            item = QTableWidgetItem(str(activeBands))
            item.setToolTip(str(activeBands))
            self.tableWidget2.setItem(j, 3, item)
            j=j+1

        self.tableWidget2.blockSignals(False)

    # slot for when active layer selection has changed
    def layerSelected(self, row, column):
        if column != 0:
            return

        self.layersSelected=[]
        for i in range(0, self.tableWidget2.rowCount()):
            item=self.tableWidget2.item(i,0)
            layerID=self.tableWidget2.item(i,1).data(Qt.UserRole)
            if item and item.checkState()==Qt.Checked:
                self.layersSelected.append(layerID)
            elif layerID in self.layersSelected:
                self.layersSelected.remove(layerID)

    # slot for when active band selection has changed
    def bandSelected(self,action):
        layerID=action.data()[0]
        layerBand=action.data()[1]
        j=action.data()[2]
        toggleAll=action.data()[3]
        activeBands = self.layerBands[layerID] if (layerID in self.layerBands) else []

        # special actions All/None
        if layerBand == -1:
            for layer in self.legend.layers():
                if layer.id() == layerID:
                    if toggleAll:
                        activeBands = list(range(1,layer.bandCount()+1))
                    else:
                        activeBands = []
                    # toggle all band# actions
                    group=action.parent()
                    if group and not isinstance(group, QActionGroup):
                        group=None
                    if group:
                        group.blockSignals(True)
                        for a in group.actions():
                            if a.isCheckable():
                                a.setChecked(toggleAll)
                        group.blockSignals(False)

        # any Band# action
        else:
            if action.isChecked():
                activeBands.append(layerBand)
            else:
                if layerBand in activeBands:
                    activeBands.remove(layerBand)
            activeBands.sort()

        self.layerBands[layerID]=activeBands

        # update UI
        item = QTableWidgetItem(str(activeBands))
        item.setToolTip(str(activeBands))
        self.tableWidget2.setItem(j, 3, item)


    # event filter for band selection menu, do not close after toggling each band
    def eventFilter(self, obj, event):
        if event.type() in [QtCore.QEvent.MouseButtonRelease]:
            if isinstance(obj, QMenu):
                if obj.activeAction():
                    if not obj.activeAction().menu(): #if the selected action does not have a submenu
                        #eat the event, but trigger the function
                        obj.activeAction().trigger()
                        return True    
        return super(ValueWidget, self).eventFilter(obj, event)

    def shouldPrintValues(self):
        return  self.isVisible() and not self.visibleRegion().isEmpty() \
                and self.isActive and self.tabWidget.currentIndex()!=2 

    def toolMoved(self, position):
        if self.shouldPrintValues() and not self.cbxClick.isChecked():
            self.printValue(self.canvas.getCoordinateTransform().toMapCoordinates(position))

    def toolPressed(self, position):
        if self.shouldPrintValues() and self.cbxClick.isChecked():
            self.printValue(self.canvas.getCoordinateTransform().toMapCoordinates(position))


