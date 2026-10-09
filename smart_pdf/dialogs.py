from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFontComboBox, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QTextEdit, QVBoxLayout,
)

from smart_pdf.painting import SafeTextDocument


class TextDialog(QDialog):
    def __init__(self, html="",parent=None):
        super().__init__(parent)
        self.setWindowTitle("Smart PDF • tekst i formatowanie")
        self.resize(680,420)
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.fonts = QFontComboBox()
        self.fonts.setCurrentFont(QFont("Arial"))
        bar.addWidget(self.fonts,1)
        size = QSpinBox()
        size.setRange(6,144)
        size.setValue(14)
        size.setSuffix(" pt")
        bar.addWidget(size)
        self.bold = QPushButton("B")
        self.bold.setCheckable(True)
        self.bold.setFont(QFont("Arial",11,QFont.Bold))
        self.italic = QPushButton("I")
        self.italic.setCheckable(True)
        self.italic.setFont(QFont("Arial",11,-1,True))
        self.underline = QPushButton("U")
        self.underline.setCheckable(True)
        for button in (self.bold,self.italic,self.underline):
            button.setMaximumWidth(38)
            bar.addWidget(button)
        color = QPushButton("Kolor")
        bar.addWidget(color)
        align = QComboBox()
        align.addItems(["Do lewej","Na środku","Do prawej"])
        bar.addWidget(align)
        layout.addLayout(bar)
        self.editor = QTextEdit()
        self.editor.setDocument(SafeTextDocument(self.editor))
        self.editor.document().setDefaultFont(QFont("Arial",14))
        self.editor.setHtml(html)
        layout.addWidget(self.editor,1)
        layout.addWidget(QLabel("Zaznacz fragment, aby sformatować tylko ten fragment. Po zatwierdzeniu pole można przesuwać i obracać."))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Zastosuj")
        buttons.button(QDialogButtonBox.Cancel).setText("Anuluj")
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.fonts.currentFontChanged.connect(lambda f:self.format(font=f.family()))
        size.valueChanged.connect(lambda n:self.format(size=n))
        self.bold.clicked.connect(lambda checked:self.format(bold=checked))
        self.italic.clicked.connect(lambda checked:self.format(italic=checked))
        self.underline.clicked.connect(lambda checked:self.format(underline=checked))
        color.clicked.connect(self.choose_color)
        align.currentIndexChanged.connect(lambda i:self.editor.setAlignment([Qt.AlignLeft,Qt.AlignHCenter,Qt.AlignRight][i]))
        self.editor.cursorPositionChanged.connect(lambda:self.sync_format(size))
        self.sync_format(size)
        self.editor.setFocus()

    def format(self,**options):
        fmt = QTextCharFormat()
        if "font" in options:
            fmt.setFontFamilies([options["font"]])
        if "size" in options:
            fmt.setFontPointSize(options["size"])
        if "bold" in options:
            fmt.setFontWeight(QFont.Bold if options["bold"] else QFont.Normal)
        if "italic" in options:
            fmt.setFontItalic(options["italic"])
        if "underline" in options:
            fmt.setFontUnderline(options["underline"])
        if "color" in options:
            fmt.setForeground(QColor(options["color"]))
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def sync_format(self,size):
        fmt = self.editor.currentCharFormat()
        for widget in (self.bold,self.italic,self.underline,size,self.fonts):
            widget.blockSignals(True)
        self.bold.setChecked(fmt.fontWeight()>=QFont.Bold)
        self.italic.setChecked(fmt.fontItalic())
        self.underline.setChecked(fmt.fontUnderline())
        size.setValue(round(fmt.fontPointSize() or 14))
        self.fonts.setCurrentFont(fmt.font())
        for widget in (self.bold,self.italic,self.underline,size,self.fonts):
            widget.blockSignals(False)

    def choose_color(self):
        color = QColorDialog.getColor(self.editor.textColor(),self,"Kolor tekstu")
        if color.isValid():
            self.format(color=color.name())

    def html(self):
        return self.editor.toHtml()


class ScopeDialog(QDialog):
    def __init__(self,title,current,selected,count,margin=False,parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(390,220)
        self.current,self.selected,self.count = current,selected,count
        layout = QFormLayout(self)
        self.scope = QComboBox()
        self.scope.addItems(["Bieżąca strona",f"Zaznaczone strony ({len(selected)})","Wszystkie strony"])
        layout.addRow("Zakres",self.scope)
        if margin:
            self.side = QComboBox()
            self.side.addItems(["Prawy","Lewy","Górny","Dolny"])
            layout.addRow("Strona marginesu",self.side)
            self.width = QDoubleSpinBox()
            self.width.setRange(10,500)
            self.width.setValue(55)
            self.width.setSuffix(" mm")
            layout.addRow("Szerokość",self.width)
            self.text = QCheckBox("Dodaj pole tekstowe na marginesie")
            self.text.setChecked(True)
            layout.addRow(self.text)
        else:
            self.angle = QComboBox()
            self.angle.addItems(["90° w prawo","90° w lewo","180°"])
            layout.addRow("Obrót",self.angle)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Zastosuj")
        buttons.button(QDialogButtonBox.Cancel).setText("Anuluj")
        layout.addRow(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def indices(self):
        return [self.current] if self.scope.currentIndex()==0 else self.selected if self.scope.currentIndex()==1 else list(range(self.count))
