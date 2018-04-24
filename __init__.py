"""
/***************************************************************************
         Value Tool       - A QGIS plugin to get values at the mouse pointer
                             -------------------
    begin                : 2008-08-26
    copyright            : (C) 2008-2010 by G. Picard
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
# load valuetool class from file valuetool.py

def classFactory(iface): 
  from .valuetool import ValueTool
  return ValueTool(iface)

# Display the values of the raster layers at the current mouse position. Values are printed in a table or plotted on a graph. The plugin is dockable like overview or coordinate capture, go to View/Panels to activate it.
