from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainterPath, QPen, QPolygonF, QTextDocument

# Scene coordinates and PDF coordinates are points (72 per inch). Explicit DPI
# prevents Windows screen DPI from silently enlarging 18-pt text to 24 pt.
_LAYOUT_DEVICE = QImage(1,1,QImage.Format_RGB32)
_LAYOUT_DEVICE.setDotsPerMeterX(round(72/0.0254))
_LAYOUT_DEVICE.setDotsPerMeterY(round(72/0.0254))


class SafeTextDocument(QTextDocument):
    def loadResource(self, kind, name):
        # Projects may contain rich text, but cannot load external images/files.
        return None


def rich_document(obj):
    document = SafeTextDocument()
    document.documentLayout().setPaintDevice(_LAYOUT_DEVICE)
    font = QFont("Arial")
    font.setPointSizeF(14)
    document.setDefaultFont(font)
    document.setDocumentMargin(5)
    document.setHtml(obj.get("html", ""))
    document.setTextWidth(obj["w"])
    return document


def paint_object(painter, obj):
    w, h = obj["w"], obj["h"]
    color = QColor(obj["color"])
    painter.setOpacity(obj.get("opacity", 1))
    pen = QPen(color, obj.get("width", 2), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QColor(obj["fill"]) if obj.get("fill") else Qt.NoBrush)
    kind = obj["kind"]
    if kind in {"text", "replacement"}:
        painter.setPen(Qt.NoPen)
        if kind == "replacement":
            painter.fillRect(QRectF(0,0,w,h), QColor("white"))
        rich_document(obj).drawContents(painter, QRectF(0,0,w,h))
    elif kind == "pen":
        points = obj["points"]
        if points:
            path = QPainterPath(QPointF(points[0][0]*w, points[0][1]*h))
            for x,y in points[1:]:
                path.lineTo(x*w,y*h)
            if len(points) == 1:
                painter.drawEllipse(QPointF(points[0][0]*w,points[0][1]*h), pen.widthF()/2,pen.widthF()/2)
            else:
                painter.drawPath(path)
    elif kind == "line":
        points = obj.get("points") or [[0,0],[1,1]]
        painter.drawLine(QPointF(points[0][0]*w,points[0][1]*h),QPointF(points[-1][0]*w,points[-1][1]*h))
    elif kind == "ellipse":
        painter.drawEllipse(QRectF(0,0,w,h))
    elif kind == "triangle":
        painter.drawPolygon(QPolygonF([QPointF(w/2,0),QPointF(w,h),QPointF(0,h)]))
    elif kind == "rect":
        painter.drawRect(QRectF(0,0,w,h))
    elif kind in {"highlight", "underline", "strike"}:
        for a,b,c,d in obj["rects"]:
            rect = QRectF(a*w,b*h,(c-a)*w,(d-b)*h)
            if kind == "highlight":
                painter.fillRect(rect, color)
            else:
                y = rect.bottom() if kind == "underline" else rect.center().y()
                painter.drawLine(QPointF(rect.left(),y),QPointF(rect.right(),y))
