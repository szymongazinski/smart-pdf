from __future__ import annotations

import copy
import json
import math

from PySide6.QtCore import QMimeData, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsObject, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QMenu,
)

from smart_pdf.model import make_object
from smart_pdf.painting import paint_object

MIME = "application/x-smartpdf-objects"


class ObjectItem(QGraphicsObject):
    def __init__(self, obj, canvas, parent):
        super().__init__(parent)
        self.obj, self.canvas = obj, canvas
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
        paint_object(painter,self.obj)
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
                self.setCursor(Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
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
            self.canvas.edit_text_requested.emit(self.obj["id"])
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class Canvas(QGraphicsView):
    committed = Signal(object,object,str)
    text_add_requested = Signal(float,float)
    edit_text_requested = Signal(str)
    replacement_requested = Signal(object)
    selection_changed = Signal()
    file_dropped = Signal(str)
    zoom_changed = Signal(int)

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
        self.tool = "select"
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
        self.scene().selectionChanged.connect(self.selection_changed)

    @property
    def state(self):
        return self.project.pages[self.index] if self.project else None

    def show_page(self, project, index, fit=False):
        self.project,self.index = project,index
        self.scene().clear()
        self.items_by_id = {}
        self.selection_items = []
        self.selected_words = []
        self.gesture,self.preview,self.before = None,None,None
        if not project:
            return
        state = self.state
        self.root = QGraphicsRectItem(QRectF(0,0,*state.size))
        self.root.setPen(QPen(Qt.NoPen))
        self.root.setBrush(QColor("white"))
        self.scene().addItem(self.root)
        self.root.setTransformOriginPoint(state.size[0]/2,state.size[1]/2)
        self.root.setRotation(state.rotation)
        # Render only the visible page. A 140-DPI preview is bounded for huge pages.
        scale = min(1.95, (16_000_000/(state.width*state.height))**.5)
        page = project.doc[state.source]
        import pymupdf
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False,colorspace=pymupdf.csRGB)
        image = QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format_RGB888).copy()
        background = self.scene().addPixmap(QPixmap.fromImage(image))
        background.setParentItem(self.root)
        background.setScale(1/scale)
        background.setPos(state.margins["left"],state.margins["top"])
        background.setAcceptedMouseButtons(Qt.NoButton)
        background.setZValue(0)
        # Show fixed masks when a replacement object has been moved elsewhere.
        for obj in state.objects:
            for r in obj.get("redactions",[]):
                mask = QGraphicsRectItem(QRectF(r[0],r[1],r[2]-r[0],r[3]-r[1]),self.root)
                mask.setBrush(QColor("white"))
                mask.setPen(QPen(Qt.NoPen))
                mask.setZValue(2)
                mask.setAcceptedMouseButtons(Qt.NoButton)
        for z,obj in enumerate(state.objects):
            item = ObjectItem(obj,self,self.root)
            item.setZValue(10+z/1000)
            self.items_by_id[obj["id"]] = item
        self.words = project.words(index)
        self.scene().setSceneRect(self.root.mapRectToScene(self.root.rect()).adjusted(-42,-42,42,42))
        self.set_tool(self.tool)
        if fit:
            self.fit_page()

    def fit_page(self):
        if self.project:
            self.fitInView(self.scene().sceneRect(),Qt.KeepAspectRatio)
            self.zoom_changed.emit(round(self.transform().m11()*100))

    def set_zoom(self, percent):
        self.resetTransform()
        self.scale(percent/100,percent/100)
        self.zoom_changed.emit(percent)

    def set_tool(self, tool):
        self.tool = tool
        self.setDragMode(QGraphicsView.ScrollHandDrag if tool == "hand" else QGraphicsView.NoDrag)
        for item in self.items_by_id.values():
            enabled = tool == "select" and not self.reading
            item.setAcceptedMouseButtons(Qt.LeftButton if enabled else Qt.NoButton)
            item.setFlag(QGraphicsItem.ItemIsSelectable,enabled)
            item.setFlag(QGraphicsItem.ItemIsMovable,enabled)
        cursor = Qt.ArrowCursor if tool == "select" else Qt.IBeamCursor if tool in {"select_text","text","highlight","underline","strike"} else Qt.CrossCursor
        if tool != "hand":
            self.viewport().setCursor(cursor)

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
                # Duplicating a replacement creates ordinary text, not a second removal.
                if obj["kind"] == "replacement":
                    obj["kind"] = "text"
                    obj.pop("redactions",None)
                self.state.objects.append(obj)
                ids.append(obj["id"])
            self.finish_edit("Wklejenie obiektów")
            self.next_selection = ids
            self.select_ids(ids)
        except (ValueError,KeyError,TypeError):
            self.before = None

    def delete_selected(self):
        ids = {o["id"] for o in self.selected_objects()}
        if ids and not self.reading:
            self.begin_edit()
            self.state.objects = [o for o in self.state.objects if o["id"] not in ids]
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
        p = self.root.mapFromScene(self.mapToScene(event.position().toPoint()))
        if not self.root.rect().contains(p):
            return super().mousePressEvent(event)
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
            menu.addAction("Zmień tekst…",lambda:self.replacement_requested.emit(list(self.selected_words)))
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
