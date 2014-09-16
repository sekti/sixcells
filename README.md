# SixCells

Level editor for [Hexcells](http://store.steampowered.com/sub/50074/).

Work in progress.

*SixCells Editor* allows creation of levels and outputs them in a JSON format.
These levels can be played using *SixCells Player*.  
It does not actually interact with *Hexcells* in any way.

![Logo](https://raw.githubusercontent.com/BlaXpirit/sixcells/master/logo.png)

## How to Use

### Editor

Left click on empty space to add a black cell.
Double click on empty space to add a blue cell.  
(hold Alt to ignore collision between side-by-side cells, as seen in "FINISH" levels)  
Double click a cell to toggle blue/black.  
Left click a cell to switch between 3 information display modes.  
Alt+click a cell to mark it as revealed.  

Drag from inside a cell to outside the cell to add a column number marker.  
Left click a column marker to toggle information display.  

Right click an item to remove it.  

Press and drag mouse wheel to navigate.  
Scroll to zoom.  

Shift+drag on empty space to start a freehand selection.  
Shift+click a cell to add or remove it from current selection.  
Shift+click on empty space to clear selection.  
Drag one of the selected cells to relocate them.  

Press TAB to switch to playtest mode (open *Player*).  

### Player

*Open* a level created in the *Editor* and play it.

Some basic auto-solving capabilities are present (press *Solve* to attempt one action).  

If you use the *Player* to playtest right from *Editor*, it will save state between sessions.  
You can press left and right mouse button at the same time to revert a cell to yellow.  


## Level File Structure

### *.sixcells format

```python
{
  "cells": [ # Hexagonal cells
    {
      "id": integer,
      # Unique number that can be used to refer to this cell.
      
      "kind": integer,
      # 0: black, 1: blue, -1: yellow (never used).
      
      "neighbors": [integers],
      # List of IDs of cells that touch this cell
      # ordered clockwise.
      
      "members": [integers],
      # List of IDs of cells that are related to this cell:
      # same as neighbors for black, nearby in 2-radius for blue.
      # This key is present only for cells that have a number in them.
      
      "revealed": boolean,
      # Should this cell be initially revealed?
      # true: yes, (absent): no
      
      "value": integer,
      # The number written on the cell (absent if there is no number).
      # This is redundant; it may be deduced from "members",
      # but presence/absence of it still matters.

      "together": boolean,
      # Are the blue "members" all grouped together (touching)?
      # true: yes, false: no, (absent): no information given.
      # Can be present only if "value" is present.

      "x": number,
      "y": number
      # Absolute coordinates of the center of this cell.
    },
    ...
  ], 
  "columns": [ # Column numbers
    {
      "members": [integers],
      # List of IDs of cells that are in this column
      # ordered from nearest to farthest.
      
      "value": integer,
      # The number written on the column.
      # This is redundant; it may be deduced from "members".

      "together": boolean,
      # Are the blue cells in this column all grouped together?
      # true: yes, false: no, (absent): no information given.
      
      "x": number,
      "y": number,
      # Absolute coordinates of the center
      # of the imaginary hexagon that contains this number.
      
      "angle": number,
      # Angle of rotation in degrees
      # (only -90, -60, 0, 60, 90 are possible).
    },
    ...
  ]
}
```


## Installation

- **Windows**

  Download the latest [release](https://github.com/BlaXpirit/sixcells/releases), extract the folder and you're ready to go!

- **Linux**

  Go to a folder where you would like *SixCells* to be and execute this (you will need `git`):

  ```bash
  git clone --recursive https://github.com/BlaXpirit/sixcells
  ```
  
  ...or just download the `win32` [release](https://github.com/BlaXpirit/sixcells/releases) and extract it. It works because the binary release also contains full source code.
  
  Install the library `python-pyside` or `python-pyqt4`.

- **Mac**
  
  *SixCells* should work under Mac if the needed libraries are available. Try to adapt the instructions for Linux.

  
## Technical Details

*SixCells* is written using [Python](http://python.org/) and [Qt](http://qt-project.org/).

It is guaranteed to work on Python 3.4 and later; Versions 2.7 and 3.* should also work.

*SixCells* supports Qt 4 and Qt 5, and can work with either [PySide](http://pyside.org/), [PyQt4](http://www.riverbankcomputing.co.uk/software/pyqt/download) or [PyQt5](http://www.riverbankcomputing.co.uk/software/pyqt/download5).  
(There are currently some problems with Qt 5...)

License: GNU General Public License Version 3.0 (GPLv3)
