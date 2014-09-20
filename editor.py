#!/usr/bin/env python

# Copyright (C) 2014 Oleh Prypin <blaxpirit@gmail.com>
# 
# This file is part of SixCells.
# 
# SixCells is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# SixCells is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with SixCells.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import division, print_function

import sys
import math
import itertools
import contextlib
import weakref
import io
import os.path

import common
from common import *

from qt.core import QPointF, QRectF, QSizeF, QTimer, QByteArray
from qt.gui import QPolygonF, QPen, QPainter, QMouseEvent, QTransform, QPainterPath, QKeySequence, QClipboard
from qt.widgets import QApplication, QGraphicsView, QMainWindow, QMessageBox, QFileDialog, QGraphicsItem, QGraphicsPathItem, QInputDialog, QAction, QActionGroup, QVBoxLayout, QDialog, QLineEdit, QDialogButtonBox, QLabel



class Cell(common.Cell):
    def __init__(self):
        self._revealed = False
        self._show_info = 0
        self.preview = None
        self.columns = weakref.WeakSet()

        common.Cell.__init__(self)

    @event_property
    def show_info(self):
        self.upd()

    @event_property
    def revealed(self):
        self.upd()

    @property
    def selected(self):
        return self in self.scene().selection
    @selected.setter
    def selected(self, value):
        if value:
            self.scene().selection.add(self)
            self.setOpacity(0.5)
        else:
            try:
                self.scene().selection.remove(self)
            except KeyError: pass
            self.setOpacity(1)

    @property
    def neighbors(self):
        if not self.scene():
            return
        return (it for it in self.scene().collidingItems(self) if isinstance(it, Cell))
    
    @property
    def flower_neighbors(self):
        if not self.scene():
            return
        poly = QPolygonF()
        l = 1.7
        for i in range(6):
            a = i*tau/6
            poly.append(QPointF(self.x()+l*math.sin(a), self.y()+l*math.cos(a)))
        for it in self.scene().items(poly):
            if isinstance(it, Cell) and it is not self:
                yield it
    
    @property
    def members(self):
        return (self.flower_neighbors if self.kind is Cell.full else self.neighbors)

    @property
    def together(self):
        if self.show_info==2:
            full_items = {it for it in self.members if it.kind is Cell.full}
            return all_grouped(full_items, key=Cell.is_neighbor)
    @together.setter
    def together(self, value):
        if value is not None:
            self.show_info = 2
        else:
            self.show_info = min(self.show_info, 1)

    @property
    def value(self):
        if self.show_info:
            return sum(1 for it in self.members if it.kind is Cell.full)
    @value.setter
    def value(self, value):
        if value is not None:
            self.show_info = max(self.show_info, 1)
        else:
            self.show_info = 0

    def is_neighbor(self, other):
        return self.collidesWithItem(other)
    
    def overlaps(self, other, allow_horz=False):
        if self.collidesWithItem(other):
            dist = distance(self, other)
            if allow_horz and dist>0.85 and abs(self.y()-other.y())<1e-3:
                return False
            if dist<0.98:
                return True
        return False

    def upd(self, first=True):
        if not self.scene():
            return
        
        common.Cell.upd(self)
        
        if self.revealed:
            self.setBrush(Color.revealed_border)
        #pen = QPen(Color.revealed_border if self.revealed else Color.border, 0.03)
        #pen.setJoinStyle(qt.MiterJoin)
        #self.setPen(pen)

        if first:
            with self.upd_neighbors():
                pass

    @contextlib.contextmanager
    def upd_neighbors(self):
        neighbors = list(self.flower_neighbors)
        scene = self.scene()
        yield
        for it in neighbors:
            it.upd(False)
        for it in scene.all(Column):
            it.upd()

    def mousePressEvent(self, e):
        if e.button()==qt.LeftButton and e.modifiers()&qt.ShiftModifier:
            self.selected = not self.selected
            e.ignore()
        if self.scene().selection:
            self.last_tried = None
            return
        if e.button()==qt.LeftButton and e.modifiers()&qt.AltModifier:
            self.revealed = not self.revealed
            e.ignore()
        
    def mouseMoveEvent(self, e):
        if self.scene().selection:
            if self.selected:
                x, y = convert_pos(e.scenePos().x(), e.scenePos().y())
                dx = x-self.x()
                dy = y-self.y()
                if not self.last_tried or not (distance((x, y), self.last_tried)<1e-3):
                    self.last_tried = x, y
                    for it in self.scene().selection:
                        it.original_pos = it.pos()
                        it.setX(it.x()+dx)
                        it.setY(it.y()+dy)
                        for col in it.columns:
                            col.original_pos = col.pos()
                            col.setX(col.x()+dx)
                            col.setY(col.y()+dy)
                    for it in self.scene().selection:
                        bad = False
                        for x in it.collidingItems():
                            if x.overlaps(it) and isinstance(x, (Cell, Column)) and x is not it:
                                bad = True
                                break
                        for c in it.columns:
                            for x in c.collidingItems():
                                if isinstance(x, (Cell, Column)):
                                    bad = True
                                    break
                        if bad:
                            for it in self.scene().selection:
                                it.setPos(it.original_pos)
                                for col in it.columns:
                                    col.setPos(col.original_pos)
                
        elif not self.contains(e.pos()): # mouse was dragged outside
            if not self.preview:
                self.preview = Column()
                self.scene().addItem(self.preview)

            a = angle(e.pos())*360/tau
            if -30<a<30:
                self.preview.setX(self.x())
                self.preview.setY(self.y()-1)
                self.preview.setRotation(1e-3) # not zero so font doesn't look different from rotated variants
            elif -90<a<-30:
                self.preview.setX(self.x()-cos30)
                self.preview.setY(self.y()-0.5)
                self.preview.setRotation(-60)
            elif 30<a<90:
                self.preview.setX(self.x()+cos30)
                self.preview.setY(self.y()-0.5)
                self.preview.setRotation(60)
            #elif -120<a<-90:
                #self.preview.setX(self.x()-cos30*1.3)
                #self.preview.setY(self.y())
                #self.preview.setRotation(-90+1e-3)
            #elif 90<a<120:
                #self.preview.setX(self.x()+cos30*1.3)
                #self.preview.setY(self.y())
                #self.preview.setRotation(90-1e-3)
            else:
                self.scene().removeItem(self.preview)
                self.preview = None
    
    def mouseReleaseEvent(self, e):
        if self.scene().supress:
            return
        if self.scene().selection:
            self.scene().full_upd()

        if e.modifiers()&(qt.ShiftModifier|qt.AltModifier) or self.scene().selection:
            e.ignore()
            return
        if not self.preview:
            if self.contains(e.pos()): # mouse was not dragged outside
                if e.button()==qt.LeftButton:
                    try:
                        self.show_info = (self.show_info+1)%3
                        #if self.show_info==2 and self.value<=1:
                            #self.show_info = (self.show_info+1)%3
                    except TypeError:
                        pass
                elif e.button()==qt.RightButton:
                    for col in self.columns:
                        self.scene().removeItem(col)
                    with self.upd_neighbors():
                        self.scene().removeItem(self)
        else:
            for it in self.preview.collidingItems():
                self.scene().removeItem(self.preview)
                self.preview = None
                break
            else:
                self.preview.upd()
                self.preview.cell = self
            self.preview = None


class Column(common.Column):
    def __init__(self):
        common.Column.__init__(self)
        
        self._show_info = False

    @property
    def members(self):
        try:
            sr = self.scene().sceneRect()
        except AttributeError:
            return
        poly = QPolygonF(QRectF(-0.001, 0.05, 0.002, 2*max(sr.width(), sr.height())))
        if abs(self.rotation())>1e-2:
            poly = QTransform().rotate(self.rotation()).map(poly)
        poly.translate(self.scenePos())
        items = self.scene().items(poly)
        for it in items:
            if isinstance(it, Cell):
                if not poly.containsPoint(it.pos(), qt.OddEvenFill):
                    continue
                yield it
    
    @event_property
    def show_info(self):
        self.upd()
    
    @property
    def value(self):
        return sum(1 for it in self.members if it.kind is Cell.full)
    
    @setter_property
    def cell(self, value):
        try:
            self.cell.columns.remove(self)
        except (AttributeError, KeyError):
            pass
        yield value
        value.columns.add(self)
    
    @property
    def together(self):
        if self.show_info:
            items = sorted(self.members, key=lambda it: (it.y(), it.x()))
            groups = itertools.groupby(items, key=lambda it: it.kind is Cell.full)
            return sum(1 for kind, _ in groups if kind is Cell.full)<=1
    @together.setter
    def together(self, value):
        self.show_info = value is not None

    def mousePressEvent(self, e):
        pass
    
    def mouseReleaseEvent(self, e):
        if self.scene().supress:
            return
        if self.contains(e.pos()): # mouse was not dragged outside
            if e.button()==qt.LeftButton:
                self.show_info = not self.show_info
            elif e.button()==qt.RightButton:
                self.scene().removeItem(self)



def convert_pos(x, y):
    x = round(x/cos30)
    y = round(y*2)/2.0
    #if x%2==0:
        #y = round(y)
    #else:
        #y = round(y+0.5)-0.5
    x *= cos30
    return x, y


class Scene(common.Scene):
    def __init__(self):
        common.Scene.__init__(self)
        self.reset()
        self.swap_buttons = False
        self.use_rightclick = False
    
    def reset(self):
        self.clear()
        self.preview = None
        self.selection = set()
        self.selection_path_item = None
        self.supress = False
        self.title = self.author = self.information = ''
    
    def place(self, p, kind=Cell.unknown):
        if not self.preview:
            self.preview = Cell()
            self.preview.kind = kind
            self.preview.setOpacity(0.4)
            self.addItem(self.preview)
        x, y = convert_pos(p.x(), p.y())
        self.preview.setPos(x, y)
        self.preview.upd(False)
        self.preview.text = ''
        
    
    def mousePressEvent(self, e):
        if self.supress:
            return

        self.last_press = self.itemAt(e.scenePos(), QTransform())

        if self.selection:
            if (e.button()==qt.LeftButton and not self.itemAt(e.scenePos(), QTransform())) or e.button()==qt.RightButton:
                old_selection = self.selection
                self.selection = set()
                for it in old_selection:
                    try:
                        it.selected = False
                    except AttributeError:
                        pass
        if not self.itemAt(e.scenePos(), QTransform()):
            if e.button()==qt.LeftButton:
                if e.modifiers()&qt.ShiftModifier:
                    self.selection_path_item = QGraphicsPathItem()
                    self.selection_path = path = QPainterPath()
                    self.selection_path_item.setPen(QPen(Color.selection, 0, qt.DashLine))
                    path.moveTo(e.scenePos())
                    self.selection_path_item.setPath(path)
                    self.addItem(self.selection_path_item)
            if e.button()==qt.LeftButton or (self.use_rightclick and e.button()==qt.RightButton):
                if not e.modifiers()&qt.ShiftModifier:
                    self.place(e.scenePos(), Cell.full if (e.button()==qt.LeftButton)^self.swap_buttons else Cell.empty)
        
        QGraphicsScene.mousePressEvent(self, e)

    def mouseMoveEvent(self, e):
        if self.supress:
            return
        if self.selection_path_item:
            p = self.selection_path
            p.lineTo(e.scenePos())
            p2 = QPainterPath(p)
            p2.lineTo(p.pointAtPercent(0))
            self.selection_path_item.setPath(p2)
        elif self.preview:
            self.place(e.scenePos())
        else:
            QGraphicsScene.mouseMoveEvent(self, e)

    
    def mouseReleaseEvent(self, e):
        if self.supress:
            return
        if self.selection_path_item:
            p = self.selection_path
            p.lineTo(p.pointAtPercent(0))
            for it in self.items(p, qt.IntersectsItemShape):
                if isinstance(it, Cell):
                    it.selected = True
            self.removeItem(self.selection_path_item)
            self.selection_path_item = None

        elif self.preview:
            col = None
            for it in self.collidingItems(self.preview):
                pass
                if isinstance(it, Column) and distance(it, self.preview)<1e-3:
                    col = it
                    continue
                if self.preview.overlaps(it, allow_horz=e.modifiers()&qt.AltModifier):
                    with self.preview.upd_neighbors():
                        self.removeItem(self.preview)
                    self.preview = None
                    break
            else:
                self.preview.setOpacity(1)
                self.preview.show_info = self.preview.kind==Cell.empty
                if col:
                    if not self.itemAt(col.pos()-col.cell.pos()+self.preview.pos()):
                        old_cell = col.cell
                        col.cell = self.preview
                        col.setPos(col.pos()-old_cell.pos()+self.preview.pos())
                        col.upd()
                    else:
                        with self.preview.upd_neighbors():
                            self.removeItem(self.preview)
            self.preview = None
        else:
            QGraphicsScene.mouseReleaseEvent(self, e)
    
    def mouseDoubleClickEvent(self, e):
        it = self.itemAt(e.scenePos(), QTransform())
        if not it:
            self.mousePressEvent(e)
            return
        if not isinstance(it, Cell):
            return
        if self.last_press is None and not self.use_rightclick:
            if it.kind is Cell.full:
                it.kind = Cell.empty
                it.show_info = 1
            else:
                it.kind = Cell.full
                it.show_info = 0
        QGraphicsScene.mouseDoubleClickEvent(self, e)




class View(QGraphicsView):
    def __init__(self, scene):
        QGraphicsView.__init__(self, scene)
        self.scene = scene
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setRenderHints(self.renderHints()|QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(qt.ScrollBarAlwaysOff)
        inf = -1e10
        self.setSceneRect(QRectF(QPointF(-inf, -inf), QPointF(inf, inf)))
        self.scale(50, 50)


    def mousePressEvent(self, e):
        if e.button()==qt.MidButton or (e.button()==qt.RightButton and not self.scene.use_rightclick and not self.scene.itemAt(self.mapToScene(e.pos()), QTransform())):
            fake = QMouseEvent(e.type(), e.pos(), qt.LeftButton, qt.LeftButton, e.modifiers())
            self.scene.supress = True
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            QGraphicsView.mousePressEvent(self, fake)
        else:
            QGraphicsView.mousePressEvent(self, e)
    
    def _ensure_visible(self):
        self.ensureVisible(QRectF(self.scene.itemsBoundingRect().center(), QSizeF(1e-10, 1e-10)))
    
    def resizeEvent(self, e):
        QGraphicsView.resizeEvent(self, e)
        self._ensure_visible()
    
    def mouseReleaseEvent(self, e):
        if e.button()==qt.MidButton or (e.button()==qt.RightButton and self.scene.supress):
            fake = QMouseEvent(e.type(), e.pos(), qt.LeftButton, qt.LeftButton, e.modifiers())
            QGraphicsView.mouseReleaseEvent(self, fake)
            self.setDragMode(QGraphicsView.NoDrag)
            self._ensure_visible()
            self.scene.supress = False
        else:
            QGraphicsView.mouseReleaseEvent(self, e)

    def wheelEvent(self, e):
        try:
            d = e.angleDelta().y()
        except AttributeError:
            d = e.delta()
        d = 1.0015**d
        
        self.scale(d, d)
        self._ensure_visible()


class MainWindow(QMainWindow):
    title = "SixCells Editor"
    
    def __init__(self):
        QMainWindow.__init__(self)

        self.resize(1280, 720)
            
        self.scene = Scene()

        self.view = View(self.scene)
        self.setCentralWidget(self.view)
        
        menu = self.menuBar().addMenu("&File")
        menu.addAction("New", self.close_file, QKeySequence.New)
        menu.addAction("Open...", self.load_file, QKeySequence.Open)
        menu.addAction("Save", lambda: self.save_file(self.current_file), QKeySequence.Save)
        menu.addAction("Save As...", self.save_file, QKeySequence('Ctrl+Shift+S'))
        menu.addSeparator()
        menu.addAction("Set Level Information", self.set_information, QKeySequence('Ctrl+D'))
        menu.addSeparator()
        menu.addAction("Copy to Clipboard", self.copy, QKeySequence('Ctrl+C'))
        menu.addSeparator()
        menu.addAction("Quit", self.close, QKeySequence.Quit)

        menu = self.menuBar().addMenu("Preference&s")
        
        group = QActionGroup(self)
        group.setExclusive(True)
        action = make_check_action("Left Click Places Blue", self)
        group.addAction(action)
        action.setChecked(True)
        menu.addAction(action)
        self.swap_buttons_action = action = make_check_action("Left Click Places Black", self, self.scene, 'swap_buttons')
        menu.addAction(action)
        group.addAction(action)
        menu.addSeparator()
        group = QActionGroup(self)
        self.secondary_rightclick_action = action = make_check_action("Right Click Places Secondary", self, self.scene, 'use_rightclick')
        group.setExclusive(True)
        group.addAction(action)
        action.setChecked(True)
        menu.addAction(action)
        self.secondary_doubleclick_action = action = make_check_action("Double Click Places Secondary", self)
        menu.addAction(action)
        group.addAction(action)
        

        menu = self.menuBar().addMenu("&Play")
        menu.addAction("From Start", self.play, QKeySequence('Ctrl+Tab'))
        menu.addAction("Resume", lambda: self.play(resume=True), QKeySequence('Tab'))
        
        
        menu = self.menuBar().addMenu("&Help")
        menu.addAction("Instructions", help, QKeySequence.HelpContents)
        menu.addAction("About", lambda: about(self.title))
        

        self.current_file = None
        self.any_changes = False
        self.scene.changed.connect(self.changed)

        self.last_used_folder = None
        self.swap_buttons = False
        self.default_author = None
        
        try:
            with open('editor.cfg') as cfg_file:
                cfg = cfg_file.read()
        except OSError:
            pass
        else:
            load_config(self, self.config_format, cfg)
    
    config_format = '''
        swap_buttons = swap_buttons_action.isChecked(); swap_buttons_action.setChecked(v)
        secondary_cell_action = 'double' if secondary_doubleclick_action.isChecked() else 'right'; secondary_doubleclick_action.setChecked(v=='double')
        default_author
        last_used_folder
        window_geometry_qt = save_geometry_qt(); restore_geometry_qt(v)
    '''
    def save_geometry_qt(self):
        return str(self.saveGeometry().toBase64().data().decode('ascii'))
    def restore_geometry_qt(self, value):
        self.restoreGeometry(QByteArray.fromBase64(value.encode('ascii')))
    
    
    def changed(self, rects=None):
        if rects is None or any((rect.width() or rect.height()) for rect in rects):
            self.any_changes = True
    def no_changes(self):
        self.any_changes = False
        def no_changes():
            self.any_changes = False
        QTimer.singleShot(0, no_changes)
        
    
    @event_property
    def current_file(self):
        title = self.title
        if self.current_file:
            title = os.path.basename(self.current_file)+' - '+title
        self.setWindowTitle(title)
    
    def close_file(self):
        result = False
        if not self.any_changes:
            result = True
        else:
            if self.current_file:
                msg = "The level \"{}\" has been modified. Do you want to save it?".format(self.current_file)
            else:
                msg = "Do you want to save this level?"
            btn = QMessageBox.warning(self, "Unsaved changes", msg, QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel, QMessageBox.Save)
            if btn==QMessageBox.Save:
                if self.save_file(self.current_file):
                    result = True
            elif btn==QMessageBox.Discard:
                result = True
        if result:
            self.current_file = None
            self.scene.reset()
            self.no_changes()
        return result

    
    def set_information(self, desc=None):
        dialog = QDialog()
        dialog.setWindowTitle("Level Information")
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        layout.addWidget(QLabel("Level title:"))
        title_field = QLineEdit(self.scene.title or '')
        layout.addWidget(title_field)
        
        layout.addWidget(QLabel("Author name:"))
        author_field = QLineEdit(self.scene.author or self.default_author or '')
        layout.addWidget(author_field)
        old_author = author_field.text()
        
        information = (self.scene.information or '').splitlines()
        layout.addWidget(QLabel("Custom text hints:"))
        layout.addWidget(QLabel("This text will be displayed within the level"))
        information1_field = QLineEdit(information[0] if information else '')
        layout.addWidget(information1_field)
        information2_field = QLineEdit(information[1] if len(information)>1 else '')
        layout.addWidget(information2_field)
        
        def accepted():
            self.scene.title = title_field.text().strip()
            self.scene.author = author_field.text().strip()
            if self.scene.author and self.scene.author!=old_author:
                self.default_author = self.scene.author
            self.scene.information = '\n'.join(line for line in [information1_field.text().strip(), information2_field.text().strip()] if line)
            self.changed()
            dialog.close()
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        button_box.rejected.connect(dialog.close)
        button_box.accepted.connect(accepted)
        layout.addWidget(button_box)
        
        dialog.exec_()
        
    
    
    def save_file(self, fn=None):
        if not fn:
            try:
                dialog = QFileDialog.getSaveFileNameAndFilter
            except AttributeError:
                dialog = QFileDialog.getSaveFileName
            fn, _ = dialog(self, "Save", self.last_used_folder,
                "Hexcells level (*.hexcells);;SixCells format (JSON) (*.sixcells);;SixCells format (JSON, gzipped) (*.sixcellz)"
            )
        if not fn:
            return
        if fn.endswith('.hexcells'):
            try:
                return save_hexcells(fn, self.scene)
            except ValueError as e:
                QMessageBox.warning(None, "Error", str(e))
                return
        try:
            gz = fn.endswith('.sixcellz')
        except AttributeError:
            gz = False
        save_file(fn, self.scene, pretty=True, gz=gz)
        self.no_changes()
        self.last_used_folder = os.path.dirname(fn)
        return True
    
    def load_file(self, fn=None):
        if not self.close_file():
            return
        if not fn:
            try:
                dialog = QFileDialog.getOpenFileNameAndFilter
            except AttributeError:
                dialog = QFileDialog.getOpenFileName
            fn, _ = dialog(self, "Open", self.last_used_folder, "Hexcells/SixCells Level (*.hexcells *sixcells *.sixcellz)")
        if not fn:
            return
        if fn.endswith('.hexcells'):
            try:
                load_hexcells(fn, self.scene, Cell=Cell, Column=Column)
            except ValueError as e:
                QMessageBox.warning(None, "Error", str(e))
                return
        else:
            load_file(fn, self.scene, gz=fn.endswith('.sixcellz'), Cell=Cell, Column=Column)
        for it in self.scene.all(Column):
            it.cell = min(it.members, key=lambda m: (m.pos()-it.pos()).manhattanLength())
        self.view.fitInView(self.scene.itemsBoundingRect().adjusted(-0.5, -0.5, 0.5, 0.5), qt.KeepAspectRatio)
        if isinstance(fn, basestring):
            self.current_file = fn
            self.last_used_folder = os.path.dirname(fn)
        self.no_changes()
        return True
    
    def copy(self):
        f = io.BytesIO()
        save_hexcells(f, self.scene)
        f.seek(0)
        s = f.read().decode('utf-8')
        s = '\t'+s.replace('\n', '\n\t')
        app.clipboard().setText(s)

    
    def play(self, resume=False):
        import player
        
        player.app = app
        struct, cells_by_id, columns_by_id = save(self.scene, resume=resume)
        
        window = player.MainWindow(playtest=True)
        window.setWindowModality(qt.ApplicationModal)
        window.setGeometry(self.geometry())

        def delayed():
            window.load(struct)
            window.view.setSceneRect(self.view.sceneRect())
            window.view.setTransform(self.view.transform())
            window.view.horizontalScrollBar().setValue(self.view.horizontalScrollBar().value())
            window.view.verticalScrollBar().setValue(self.view.verticalScrollBar().value())
            
        windowcloseevent = window.closeEvent
        def closeevent(e):
            windowcloseevent(e)
            for it in window.scene.all(player.Cell):
                cells_by_id[it.id].revealed_resume = it.kind is not Cell.unknown
        window.closeEvent = closeevent

        window.show()
        QTimer.singleShot(0, delayed)
    
    def closeEvent(self, e):
        if not self.close_file():
            e.ignore()
            return
        
        cfg = save_config(self, self.config_format)
        with open('editor.cfg', 'w') as cfg_file:
            cfg_file.write(cfg)



def main(f=None):
    global app, window

    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()

    if not f and len(sys.argv[1:])==1:
        f = sys.argv[1]
    if f:
        f = os.path.abspath(f)
        QTimer.singleShot(50, lambda: window.load_file(f))
    
    app.exec_()

if __name__=='__main__':
    main()