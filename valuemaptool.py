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
"""

from qgis.PyQt import QtCore, QtGui
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import QCursor, QPixmap

from qgis.gui import QgsMapTool

# cursor taken from QGIS qgscursors.cpp - these should be available in python api!
identify_cursor = [
  "16 16 3 1",
  "# c None",
  "a c #000000",
  ". c #ffffff",
  ".###########..##",
  "...########.aa.#",
  ".aa..######.aa.#",
  "#.aaa..#####..##",
  "#.aaaaa..##.aa.#",
  "##.aaaaaa...aa.#",
  "##.aaaaaa...aa.#",
  "##.aaaaa.##.aa.#",
  "###.aaaaa.#.aa.#",
  "###.aa.aaa..aa.#",
  "####..#..aa.aa.#",
  "####.####.aa.a.#",
  "##########.aa..#",
  "###########.aa..",
  "############.a.#",
  "#############.##"
]

class ValueMapTool(QgsMapTool):

    def __init__(self, canvas, button):
        QgsMapTool.__init__(self,canvas)
        self.canvas = canvas
        #self.cursor = QCursor(Qt.CrossCursor)
        self.cursor = QCursor(QPixmap(identify_cursor), 1, 1)
        self.button = button

    def activate(self):
        QgsMapTool.activate(self)
        self.canvas.setCursor(self.cursor)
        self.button.setCheckable(True)
        self.button.setChecked(True)
        
    def deactivate(self):
        if not self:
            return
        self.deactivate.emit()
        self.button.setCheckable(False)
        QgsMapTool.deactivate(self)

    def isZoomTool(self):
        return False

    def setCursor(self,cursor):
        self.cursor = QCursor(cursor)

    def canvasMoveEvent(self,event):
        self.moved.emit(QPoint(event.pos().x(), event.pos().y()))

    def canvasPressEvent(self,event):
        self.pressed.emit(QPoint(event.pos().x(), event.pos().y()))
