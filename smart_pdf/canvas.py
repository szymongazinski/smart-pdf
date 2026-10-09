from __future__ import annotations

import copy
import json
import math

from collections import OrderedDict

import pymupdf
from PySide6.QtCore import QEvent, QMimeData, QPointF, QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPainterPath, QPen, QPixmap, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsObject, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QMenu, QGraphicsTextItem, QStyle, QStyleOptionGraphicsItem,
)

from smart_pdf.model import make_object
from smart_pdf.painting import paint_object, rich_document

MIME = "application/x-smartpdf-objects"


class InlineTextItem(QGraphicsTextItem):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setDocument(rich_document(owner.obj))
        self.setTextWidth(owner.obj["w"])
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setDefaultTextColor(QColor("#243046"))
        self.setZValue(1)
        self.document().contentsChanged.connect(self.changed)
        self.document().undoCommandAdded.connect(lambda:owner.canvas.text_format_changed.emit())

    def paint(self,painter,option,widget=None):
        clean = QStyleOptionGraphicsItem(option)
        clean.state &= ~QStyle.State_HasFocus
        super().paint(painter,clean,widget)

    def shape(self):
        # Leave the surrounding frame to the object drag/resize handles.
        path = QPainterPath()
        path.addRect(self.boundingRect().adjusted(4,4,-4,-4))
        return path

    def changed(self):
        obj = self.owner.obj
        obj["html"] = self.toHtml()
        height = self.document().size().height()
        if height > obj["h"]:
            self.owner.prepareGeometryChange()
            obj["h"] = height+4
        self.owner.update()
        self.owner.canvas.text_format_changed.emit()

    def keyPressEvent(self, event):
        if event.key()==Qt.Key_Escape:
            self.owner.canvas.finish_text_edit()
            event.accept()
            return
        if event.modifiers() & Qt.ControlModifier and event.key() in {Qt.Key_B,Qt.Key_I,Qt.Key_U}:
            cursor = self.textCursor()
            old = cursor.charFormat()
            fmt = QTextCharFormat()
            if event.key()==Qt.Key_B: fmt.setFontWeight(QFont.Normal if old.fontWeight()>=QFont.Bold else QFont.Bold)
            elif event.key()==Qt.Key_I: fmt.setFontItalic(not old.fontItalic())
            else: fmt.setFontUnderline(not old.fontUnderline())
            cursor.mergeCharFormat(fmt)
            self.setTextCursor(cursor)
            self.owner.canvas.text_format_changed.emit()
            event.accept()
            return
        super().keyPressEvent(event)
        self.owner.canvas.text_format_changed.emit()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.owner.canvas.text_format_changed.emit()


class ObjectItem(QGraphicsObject):
    def __init__(self, obj, canvas, parent, page_index=0):
        super().__init__(parent)
        self.obj, self.canvas = obj, canvas
        self.page_index = page_index
        self.editor = None
        self.mode = None
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)
        self.setPos(obj["x"],obj["y"])
        self.setTransformOriginPoint(obj["w"]/2,obj["h"]/2)
        self.setRotation(obj["rotation"])
        self.setZValue(10)

    def boundingRect(self):
        pad = max(8,self.obj["width"])
        return QRectF(-pad,-30,self.obj["w"]+2*pad,self.obj["h"]+30+pad)

    def paint(self, painter, option, widget=None):
        painter.save()
        if self.editor is None:
            paint_object(painter,self.obj)
        if self.obj["kind"] in {"text","replacement"} and not self.canvas.reading:
            doc = self.editor.document() if self.editor else rich_document(self.obj)
            if not doc.toPlainText().strip():
                painter.setOpacity(1)
                painter.setPen(QPen(QColor("#b4c5df"),.7,Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(QRectF(0,0,self.obj["w"],self.obj["h"]))
                placeholder = rich_document({"html":'<span style="font-family:Arial;font-size:11pt;color:#71839d">Kliknij, aby napisać notatkę</span>',"w":self.obj["w"]})
                placeholder.drawContents(painter,QRectF(0,0,self.obj["w"],self.obj["h"]))
        painter.restore()
        if self.isSelected() and not self.canvas.reading:
            painter.setOpacity(1)
            pen = QPen(QColor("#2365ee"),1,Qt.DashLine)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            w,h = self.obj["w"],self.obj["h"]
            painter.drawRect(QRectF(0,0,w,h))
            painter.drawLine(QPointF(w/2,0),QPointF(w/2,-20))
            painter.setBrush(QColor("white"))
            painter.drawEllipse(QPointF(w/2,-20),5,5)
            painter.drawRect(QRectF(w-5,h-5,10,10))

    def hoverMoveEvent(self, event):
        if self.isSelected():
            p = event.pos()
            if (p-QPointF(self.obj["w"],self.obj["h"])).manhattanLength() < 15:
                self.setCursor(Qt.SizeFDiagCursor)
            elif (p-QPointF(self.obj["w"]/2,-20)).manhattanLength() < 15:
                self.setCursor(Qt.CrossCursor)
            else:
                self.setCursor(Qt.IBeamCursor if self.obj["kind"] in {"text","replacement"} and QRectF(4,4,self.obj["w"]-8,self.obj["h"]-8).contains(p) else Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        self.canvas.activate_page(self.page_index)
        self.canvas.finish_text_edit()
        self.canvas.begin_edit()
        p = event.pos()
        if self.isSelected() and (p-QPointF(self.obj["w"],self.obj["h"])).manhattanLength() < 15:
            self.mode = "resize"
            event.accept()
            return
        if self.isSelected() and (p-QPointF(self.obj["w"]/2,-20)).manhattanLength() < 15:
            self.mode = "rotate"
            event.accept()
            return
        if self.obj["kind"] in {"text","replacement"} and QRectF(4,4,self.obj["w"]-8,self.obj["h"]-8).contains(p):
            self.canvas.start_text_edit(self.obj["id"],p)
            event.accept()
            return
        self.mode = "move"
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mode == "resize":
            p = self.mapFromScene(event.scenePos())
            self.prepareGeometryChange()
            self.obj["w"],self.obj["h"] = max(16,p.x()),max(16,p.y())
            self.setTransformOriginPoint(self.obj["w"]/2,self.obj["h"]/2)
            self.update()
            event.accept()
        elif self.mode == "rotate":
            center = self.mapToParent(QPointF(self.obj["w"]/2,self.obj["h"]/2))
            p = self.parentItem().mapFromScene(event.scenePos())-center
            angle = math.degrees(math.atan2(p.y(),p.x()))+90
            if event.modifiers() & Qt.ShiftModifier:
                angle = round(angle/15)*15
            self.setRotation(angle)
            self.obj["rotation"] = angle
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mode == "move":
            super().mouseReleaseEvent(event)
        self.mode = None
        self.canvas.sync_items()
        self.canvas.finish_edit("Przesunięcie / rozmiar / obrót")
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if self.obj["kind"] in {"text","replacement"}:
            self.canvas.start_text_edit(self.obj["id"],event.pos())
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class Canvas(QGraphicsView):
    committed = Signal(object,object,str)
    text_add_requested = Signal(float,float)
    edit_text_requested = Signal(str)
    selection_changed = Signal()
    file_dropped = Signal(str)
    zoom_changed = Signal(int)
    page_changed = Signal(int)
    text_editing_changed = Signal(bool)
    text_format_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QColor("#e9edf3"))
        self.setAlignment(Qt.AlignCenter)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.project = None
        self.index = 0
        self.tool = "select_text"
        self.reading = False
        self.color = "#2864ed"
        self.mark_color = "#ffcf40"
        self.stroke_width = 2.5
        self.fill = ""
        self.opacity = 1.0
        self.before = None
        self.gesture = None
        self.preview = None
        self.selection_items = []
        self.selected_words = []
        self.words = []
        self.items_by_id = {}
        self.roots = []
        self.backgrounds = {}
        self.mask_items = []
        self.tile_cache = OrderedDict()
        self.tile_bytes = 0
        self.render_queue = []
        self.layout_signature = None
        self.editing = None
        self.text_before = None
        self.render_timer = QTimer(self)
        self.render_timer.setInterval(1)
        self.render_timer.timeout.connect(self.render_next_tile)
        self.view_timer = QTimer(self)
        self.view_timer.setSingleShot(True)
        self.view_timer.setInterval(35)
        self.view_timer.timeout.connect(self.update_visible_pages)
        self.verticalScrollBar().valueChanged.connect(self.schedule_view)
        self.horizontalScrollBar().valueChanged.connect(self.schedule_view)
        self.scene().selectionChanged.connect(self.selection_changed)

    @property
    def state(self):
        return self.project.pages[self.index] if self.project else None

    def show_page(self, project, index, fit=False):
        # One scene holds the entire document; raster tiles exist only near the viewport.
        signature = (id(project),tuple((p.id,p.size,p.rotation) for p in project.pages)) if project else None
        rebuild = signature != self.layout_signature or not self.roots
        center = self.mapToScene(self.viewport().rect().center())
        self.project,self.index = project,index
        if rebuild:
            self.finish_text_edit(commit=False)
            self.render_timer.stop()
            self.render_queue.clear()
            self.scene().clear()
            self.items_by_id = {}
            self.roots,self.backgrounds = [],{}
            self.mask_items = []
            self.selection_items,self.selected_words = [],[]
            self.gesture,self.preview,self.before = None,None,None
            if self.layout_signature is None or (signature and signature[0] != self.layout_signature[0]):
                self.tile_cache.clear()
                self.tile_bytes = 0
            self.layout_signature = signature
        if not project:
            self.layout_signature = None
            return
        if rebuild:
            widths = [p.size[1] if p.rotation%180 else p.size[0] for p in project.pages]
            max_width,y = max(widths),24
            for i,state in enumerate(project.pages):
                root = QGraphicsRectItem(QRectF(0,0,*state.size))
                root.setPen(QPen(QColor("#d1d9e6"),.6))
                root.setBrush(QColor("white"))
                root.setAcceptedMouseButtons(Qt.NoButton)
                self.scene().addItem(root)
                root.setTransformOriginPoint(state.size[0]/2,state.size[1]/2)
                root.setRotation(state.rotation)
                bounds = root.mapRectToScene(root.rect())
                root.setPos((max_width-bounds.width())/2-bounds.left()+24,y-bounds.top())
                self.roots.append(root)
                y += bounds.height()+28
            self.scene().setSceneRect(0,0,max_width+48,y)
        for mask in self.mask_items:
            self.scene().removeItem(mask)
        self.mask_items = []
        existing = set()
        for i,state in enumerate(project.pages):
            for z,obj in enumerate(state.objects):
                for r in obj.get("redactions",[]):
                    mask = QGraphicsRectItem(QRectF(r[0],r[1],r[2]-r[0],r[3]-r[1]),self.roots[i])
                    mask.setBrush(QColor("white"))
                    mask.setPen(QPen(Qt.NoPen))
                    mask.setZValue(2)
                    mask.setAcceptedMouseButtons(Qt.NoButton)
                    self.mask_items.append(mask)
                identifier = obj["id"]
                existing.add(identifier)
                item = self.items_by_id.get(identifier)
                if item is None:
                    item = ObjectItem(obj,self,self.roots[i],i)
                    self.items_by_id[identifier] = item
                else:
                    item.prepareGeometryChange()
                    item.obj = obj
                    item.page_index = i
                    item.setPos(obj["x"],obj["y"])
                    item.setTransformOriginPoint(obj["w"]/2,obj["h"]/2)
                    item.setRotation(obj["rotation"])
                    item.update()
                item.setZValue(10+z/1000)
        for identifier in set(self.items_by_id)-existing:
            item = self.items_by_id.pop(identifier)
            self.scene().removeItem(item)
        self.activate_page(index,emit=False)
        self.words = project.words(index)
        self.set_tool(self.tool)
        if fit:
            self.fit_page()
            self.scroll_to_page(index)
        elif rebuild:
            self.centerOn(center)
        self.schedule_view()

    def activate_page(self,index,emit=True):
        if not self.project or not 0<=index<len(self.roots):
            return
        changed = self.index != index
        if changed:
            self.clear_text_selection()
        self.index = index
        self.root = self.roots[index]
        if changed or not self.words:
            self.words = self.project.words(index)
        if changed and emit:
            self.page_changed.emit(index)

    def scroll_to_page(self,index):
        if not self.project:
            return
        self.finish_text_edit()
        self.activate_page(index)
        rect = self.roots[index].mapRectToScene(self.roots[index].rect())
        viewport_height = self.viewport().height()/self.transform().m11()
        self.centerOn(rect.center().x(),rect.top()+min(rect.height(),viewport_height)/2-8)
        self.schedule_view()

    def schedule_view(self,*args):
        self.view_timer.start()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.schedule_view()

    def update_visible_pages(self):
        if not self.project or not self.roots:
            return
        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        target = QPointF(visible.center().x(),visible.top()+min(visible.height()/3,160))
        index = min(range(len(self.roots)),key=lambda i:abs(self.roots[i].sceneBoundingRect().center().y()-target.y()) if not self.roots[i].sceneBoundingRect().contains(target) else -1)
        if self.editing is None and not self.gesture and self.before is None:
            self.activate_page(index)
        # Physical screen pixels, with modest oversampling and stable zoom buckets.
        resolution = math.ceil(self.transform().m11()*self.viewport().devicePixelRatioF()*1.15*4)/4
        resolution = max(.5,resolution)
        self.render_scale = resolution
        needed = set()
        queue = []
        for i,root in enumerate(self.roots):
            if not root.sceneBoundingRect().intersects(visible.adjusted(-80,-180,80,180)):
                continue
            state = self.project.pages[i]
            local = root.mapRectFromScene(visible.adjusted(-60,-120,60,120)).translated(-state.margins["left"],-state.margins["top"])
            local = local.intersected(QRectF(0,0,state.width,state.height))
            if local.isEmpty():
                continue
            tile_size = 512/resolution
            for ty in range(max(0,int(local.top()/tile_size)),int(math.ceil(local.bottom()/tile_size))):
                for tx in range(max(0,int(local.left()/tile_size)),int(math.ceil(local.right()/tile_size))):
                    key = (i,resolution,tx,ty)
                    needed.add(key)
                    if key not in self.backgrounds:
                        queue.append(key)
        # Keep older-resolution tiles until replacements arrive to avoid flashing.
        for key,item in list(self.backgrounds.items()):
            if key[1]==resolution and key not in needed or not self.roots[key[0]].sceneBoundingRect().intersects(visible.adjusted(-100,-250,100,250)):
                self.scene().removeItem(item)
                del self.backgrounds[key]
        self.needed_tiles = needed
        self.render_queue = queue
        if queue:
            self.render_timer.start()
        else:
            self.remove_old_tiles()

    def remove_old_tiles(self):
        for key,item in list(self.backgrounds.items()):
            if key not in self.needed_tiles:
                self.scene().removeItem(item)
                del self.backgrounds[key]

    def render_next_tile(self):
        if not self.render_queue or not self.project:
            self.render_timer.stop()
            if self.project:
                self.remove_old_tiles()
            return
        index,resolution,tx,ty = key = self.render_queue.pop(0)
        state = self.project.pages[index]
        cache_key = (state.source,resolution,tx,ty)
        tile = self.tile_cache.get(cache_key)
        if tile is None:
            size = 512/resolution
            clip = pymupdf.Rect(tx*size,ty*size,min(state.width,(tx+1)*size),min(state.height,(ty+1)*size))
            pix = self.project.doc[state.source].get_pixmap(matrix=pymupdf.Matrix(resolution,resolution),clip=clip,alpha=False,colorspace=pymupdf.csRGB)
            image = QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format_RGB888).copy()
            tile = (QPixmap.fromImage(image),pix.x/resolution,pix.y/resolution,pix.width*pix.height*4)
            self.tile_cache[cache_key] = tile
            self.tile_bytes += tile[3]
            while self.tile_bytes > 64*1024*1024 and len(self.tile_cache)>1:
                self.tile_bytes -= self.tile_cache.popitem(last=False)[1][3]
        else:
            self.tile_cache.move_to_end(cache_key)
        item = self.scene().addPixmap(tile[0])
        item.setParentItem(self.roots[index])
        item.setScale(1/resolution)
        item.setPos(tile[1]+state.margins["left"],tile[2]+state.margins["top"])
        item.setAcceptedMouseButtons(Qt.NoButton)
        item.setZValue(resolution/100)
        self.backgrounds[key] = item

    def fit_page(self):
        if self.project:
            rect = self.roots[self.index].sceneBoundingRect().adjusted(-24,-24,24,24)
            # Fit width for continuous reading; retain a useful text size.
            self.set_zoom(round(self.viewport().width()/rect.width()*100))
            self.scroll_to_page(self.index)
            self.zoom_changed.emit(round(self.transform().m11()*100))

    def set_zoom(self, percent):
        self.resetTransform()
        self.scale(percent/100,percent/100)
        self.zoom_changed.emit(percent)
        self.schedule_view()

    def set_tool(self, tool):
        self.tool = tool
        self.setDragMode(QGraphicsView.ScrollHandDrag if tool == "hand" else QGraphicsView.NoDrag)
        for item in self.items_by_id.values():
            enabled = (tool == "select" or tool=="select_text" and item.obj["kind"] in {"text","replacement"}) and not self.reading
            item.setAcceptedMouseButtons(Qt.LeftButton if enabled else Qt.NoButton)
            item.setFlag(QGraphicsItem.ItemIsSelectable,enabled)
            item.setFlag(QGraphicsItem.ItemIsMovable,enabled)
        cursor = Qt.ArrowCursor if tool == "select" else Qt.IBeamCursor if tool in {"select_text","text","highlight","underline","strike"} else Qt.CrossCursor
        if tool != "hand":
            self.viewport().setCursor(cursor)

    def start_text_edit(self,identifier,position=None):
        if self.reading or identifier not in self.items_by_id:
            return
        item = self.items_by_id[identifier]
        if self.editing is item:
            return
        self.finish_text_edit()
        self.activate_page(item.page_index)
        self.before = None
        self.text_before = self.project.snapshot()
        self.scene().clearSelection()
        item.setSelected(True)
        self.editing = item
        item.editor = InlineTextItem(item)
        cursor = item.editor.textCursor()
        cursor.setPosition(max(0,item.editor.document().documentLayout().hitTest(position,Qt.FuzzyHit)) if position is not None else max(0,item.editor.document().characterCount()-1))
        item.editor.setTextCursor(cursor)
        self.text_editing_changed.emit(True)
        item.editor.setFocus(Qt.MouseFocusReason)
        item.update()
        self.text_format_changed.emit()

    def finish_text_edit(self,commit=True):
        if self.editing is None:
            return
        item,self.editing = self.editing,None
        editor,item.editor = item.editor,None
        before,self.text_before = self.text_before,None
        editor.setTextInteractionFlags(Qt.NoTextInteraction)
        editor.setParentItem(None)
        self.scene().removeItem(editor)
        item.update()
        self.text_editing_changed.emit(False)
        self.setFocus()
        if commit and before is not None:
            after = self.project.snapshot()
            if before != after:
                self.committed.emit(before,after,"Wpisanie tekstu")

    def event(self,event):
        if event.type()==QEvent.ShortcutOverride and getattr(self,"editing",None):
            if not event.modifiers() & (Qt.ControlModifier|Qt.AltModifier) or event.key() in {Qt.Key_Z,Qt.Key_Y,Qt.Key_C,Qt.Key_X,Qt.Key_V,Qt.Key_A,Qt.Key_B,Qt.Key_I,Qt.Key_U,Qt.Key_Delete,Qt.Key_Backspace}:
                event.accept()
                return True
        return super().event(event)

    def begin_edit(self):
        if self.before is None:
            self.before = self.project.snapshot()

    def finish_edit(self,label):
        if self.before is not None:
            before,self.before = self.before,None
            after = self.project.snapshot()
            if before != after:
                self.committed.emit(before,after,label)

    def sync_items(self):
        for item in self.items_by_id.values():
            item.obj["x"],item.obj["y"] = item.pos().x(),item.pos().y()
            item.obj["rotation"] = item.rotation()

    def selected_objects(self):
        return [i.obj for i in self.scene().selectedItems() if isinstance(i,ObjectItem)]

    def select_ids(self, ids):
        for key,item in self.items_by_id.items():
            item.setSelected(key in ids)

    def clear_text_selection(self):
        for item in self.selection_items:
            self.scene().removeItem(item)
        self.selection_items = []
        self.selected_words = []

    def selection_rects(self, words=None):
        words = words if words is not None else self.selected_words
        # Merge neighboring words on the same line into continuous highlights.
        rects = []
        last_line = None
        for word in words:
            line = tuple(word[5:7])
            rect = list(word[:4])
            if rects and line == last_line and abs(rects[-1][1]-rect[1]) < 4:
                rects[-1] = [min(rects[-1][0],rect[0]),min(rects[-1][1],rect[1]),max(rects[-1][2],rect[2]),max(rects[-1][3],rect[3])]
            else:
                rects.append(rect)
            last_line = line
        return rects

    def mark_selection(self,kind):
        rects = self.selection_rects()
        if not rects:
            return
        x,y = min(r[0] for r in rects),min(r[1] for r in rects)
        w,h = max(r[2] for r in rects)-x,max(r[3] for r in rects)-y
        obj = make_object(kind,x,y,max(1,w),max(1,h),color=self.mark_color,
                          opacity=.32 if kind == "highlight" else 1,width=self.stroke_width,
                          rects=[[(a-x)/w,(b-y)/h,(c-x)/w,(d-y)/h] for a,b,c,d in rects])
        self.begin_edit()
        self.state.objects.append(obj)
        self.finish_edit("Zakreślenie" if kind == "highlight" else "Oznaczenie tekstu")

    def copy(self,cut=False):
        objects = self.selected_objects()
        if objects:
            mime = QMimeData()
            mime.setData(MIME,json.dumps(objects,ensure_ascii=False).encode("utf-8"))
            mime.setText("Obiekty Smart PDF")
            QGuiApplication.clipboard().setMimeData(mime)
            if cut:
                self.delete_selected()
        elif self.selected_words:
            QGuiApplication.clipboard().setText(" ".join(w[4] for w in self.selected_words))

    def paste(self):
        mime = QGuiApplication.clipboard().mimeData()
        if not self.project or self.reading or not mime.hasFormat(MIME):
            return
        try:
            objects = json.loads(bytes(mime.data(MIME)))
            if not isinstance(objects,list) or len(objects)>1000:
                return
            from smart_pdf.model import uid,KINDS
            self.begin_edit()
            ids = []
            for original in objects:
                obj = copy.deepcopy(original)
                if obj.get("kind") not in KINDS:
                    continue
                obj["id"] = uid()
                obj["x"] += 16
                obj["y"] += 16
                obj.pop("margin_side",None)
                # Duplicating a replacement creates ordinary text, not a second removal.
                if obj["kind"] == "replacement":
                    obj["kind"] = "text"
                    obj.pop("redactions",None)
                self.state.objects.append(obj)
                ids.append(obj["id"])
            self.next_selection = ids
            self.finish_edit("Wklejenie obiektów")
            self.select_ids(ids)
        except (ValueError,KeyError,TypeError):
            self.before = None

    def delete_selected(self):
        ids = {o["id"] for o in self.selected_objects()}
        if ids and not self.reading:
            self.begin_edit()
            for page in self.project.pages:
                page.objects = [o for o in page.objects if o["id"] not in ids]
            self.finish_edit("Usunięcie obiektów")

    def nearest_word(self,p):
        for i,word in enumerate(self.words):
            if QRectF(word[0]-3,word[1]-3,word[2]-word[0]+6,word[3]-word[1]+6).contains(p):
                return i
        if not self.words:
            return None
        distance = lambda w: abs((w[0]+w[2])/2-p.x()) + abs((w[1]+w[3])/2-p.y())
        i = min(range(len(self.words)),key=lambda i:distance(self.words[i]))
        return i if distance(self.words[i]) < 80 else None

    def draw_text_selection(self, start,end):
        self.clear_text_selection()
        self.selected_words = self.words[min(start,end):max(start,end)+1]
        for a,b,c,d in self.selection_rects():
            item = QGraphicsRectItem(QRectF(a,b,c-a,d-b),self.root)
            item.setPen(QPen(Qt.NoPen))
            item.setBrush(QColor(40,100,237,65))
            item.setZValue(50)
            item.setAcceptedMouseButtons(Qt.NoButton)
            self.selection_items.append(item)

    def mousePressEvent(self,event):
        if not self.project or event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        scene_pos = self.mapToScene(event.position().toPoint())
        hit = self.itemAt(event.position().toPoint())
        parent_hit = hit
        while parent_hit is not None and not isinstance(parent_hit,ObjectItem):
            parent_hit = parent_hit.parentItem()
        if self.editing is not None and parent_hit is not self.editing:
            self.finish_text_edit()
        if parent_hit is not None and self.tool in {"select","select_text"} and not self.reading:
            if self.tool=="select" or parent_hit.obj["kind"] in {"text","replacement"}:
                return super().mousePressEvent(event)
        index = next((i for i,root in enumerate(self.roots) if root.rect().contains(root.mapFromScene(scene_pos))),None)
        if index is None:
            return super().mousePressEvent(event)
        self.activate_page(index)
        p = self.root.mapFromScene(scene_pos)
        if self.tool in {"select_text","highlight","underline","strike"}:
            self.scene().clearSelection()
            start = self.nearest_word(p)
            if start is not None:
                self.gesture = ("words",start)
                self.draw_text_selection(start,start)
            return
        if self.reading:
            return super().mousePressEvent(event)
        if self.tool == "text":
            self.text_add_requested.emit(p.x(),p.y())
            return
        if self.tool in {"pen","line","ellipse","triangle","rect"}:
            self.begin_edit()
            self.gesture = ("draw",p,[p])
            self.preview = ObjectItem(make_object(self.tool,p.x(),p.y(),1,1,color=self.color,width=self.stroke_width,fill=self.fill,opacity=self.opacity),self,self.root)
            self.preview.setAcceptedMouseButtons(Qt.NoButton)
            self.preview.setZValue(100)
            return
        super().mousePressEvent(event)

    def contextMenuEvent(self,event):
        if not self.project or self.reading:
            return
        item = self.itemAt(event.pos())
        if isinstance(item,ObjectItem):
            if not item.isSelected():
                self.scene().clearSelection()
                item.setSelected(True)
            menu = QMenu(self)
            menu.addAction("Kopiuj obiekt",lambda:self.copy())
            menu.addAction("Wytnij obiekt",lambda:self.copy(True))
            menu.addAction("Usuń obiekt",self.delete_selected)
            if item.obj["kind"] in {"text","replacement"}:
                identifier = item.obj["id"]
                menu.addAction("Edytuj tekst…",lambda:self.edit_text_requested.emit(identifier))
            menu.exec(event.globalPos())
        elif self.selected_words:
            self.text_menu(event.globalPos())

    def update_preview(self,p,constrain=False):
        _,start,points = self.gesture
        if constrain and self.tool in {"ellipse","rect","triangle"}:
            size = max(abs(p.x()-start.x()),abs(p.y()-start.y()))
            p = QPointF(start.x()+math.copysign(size,p.x()-start.x()),start.y()+math.copysign(size,p.y()-start.y()))
        elif constrain and self.tool == "line":
            delta = p-start
            angle = round(math.atan2(delta.y(),delta.x())/(math.pi/4))*(math.pi/4)
            length = math.hypot(delta.x(),delta.y())
            p = QPointF(start.x()+length*math.cos(angle),start.y()+length*math.sin(angle))
        if self.tool == "pen":
            points.append(p)
        else:
            points[:] = [start,p]
        x,y = min(a.x() for a in points),min(a.y() for a in points)
        w,h = max(1,max(a.x() for a in points)-x),max(1,max(a.y() for a in points)-y)
        if self.tool in {"ellipse","triangle","rect"}:
            w,h = max(2,abs(p.x()-start.x())),max(2,abs(p.y()-start.y()))
        self.preview.prepareGeometryChange()
        self.preview.obj.update(x=x,y=y,w=w,h=h,points=[[(a.x()-x)/w,(a.y()-y)/h] for a in points])
        self.preview.setPos(x,y)
        self.preview.setTransformOriginPoint(w/2,h/2)
        self.preview.update()

    def mouseMoveEvent(self,event):
        if self.gesture:
            p = self.root.mapFromScene(self.mapToScene(event.position().toPoint()))
            if self.gesture[0] == "words":
                end = self.nearest_word(p)
                if end is not None:
                    self.draw_text_selection(self.gesture[1],end)
            else:
                self.update_preview(p,bool(event.modifiers() & Qt.ShiftModifier))
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if self.gesture:
            kind = self.gesture[0]
            if kind == "draw":
                self.state.objects.append(copy.deepcopy(self.preview.obj))
                self.scene().removeItem(self.preview)
                self.preview = None
                self.gesture = None
                self.finish_edit("Rysowanie")
            else:
                self.gesture = None
                if self.tool in {"highlight","underline","strike"} and not self.reading:
                    self.mark_selection(self.tool)
                elif self.selected_words:
                    self.text_menu(event.globalPosition().toPoint())
            return
        super().mouseReleaseEvent(event)

    def text_menu(self,position):
        menu = QMenu(self)
        menu.addAction("Kopiuj tekst",lambda:self.copy())
        if not self.reading:
            menu.addSeparator()
            menu.addAction("Zakreśl",lambda:self.mark_selection("highlight"))
            menu.addAction("Podkreśl",lambda:self.mark_selection("underline"))
            menu.addAction("Przekreśl",lambda:self.mark_selection("strike"))
        menu.exec(position)

    def wheelEvent(self,event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y()>0 else 1/1.15
            zoom = min(600,max(20,round(self.transform().m11()*100*factor)))
            self.set_zoom(zoom)
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self,event):
        if self.editing:
            return super().keyPressEvent(event)
        if event.key() == Qt.Key_Escape:
            if self.before is not None:
                self.project.restore(self.before)
                self.before = None
                self.show_page(self.project,self.index)
            self.clear_text_selection()
            self.scene().clearSelection()
            return
        super().keyPressEvent(event)

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self,event):
        event.acceptProposedAction()

    def dropEvent(self,event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith((".pdf",".smartpdf")):
                self.file_dropped.emit(path)
                break
        event.acceptProposedAction()
