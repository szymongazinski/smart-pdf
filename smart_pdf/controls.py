from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QSlider, QWidget, QStyledItemDelegate, QStyleOptionViewItem


class ValueSlider(QWidget):
    valueChanged = Signal(float)
    editingStarted = Signal()
    editingFinished = Signal()

    def __init__(self,minimum,maximum,value,suffix="",parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        row = QHBoxLayout(self)
        row.setContentsMargins(0,0,0,0)
        row.setSpacing(8)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(round(minimum*10),round(maximum*10))
        self.slider.setSingleStep(5)
        self.slider.setPageStep(50)
        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum,maximum)
        self.spin.setDecimals(1)
        self.spin.setSuffix(suffix)
        # Qt 6.12's styled NoButtons mode collapses the text editor to 1 px.
        # Keep the normal geometry; hide the arrow subcontrols in the theme.
        self.spin.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.spin.setFixedWidth(76)
        row.addWidget(self.slider,1)
        row.addWidget(self.spin)
        self.slider.valueChanged.connect(lambda n:self.change(n/10))
        self.spin.valueChanged.connect(self.change)
        self.slider.sliderPressed.connect(self.editingStarted)
        self.slider.sliderReleased.connect(self.editingFinished)
        self.setValue(value)

    def change(self,value):
        self.setValue(value)
        self.valueChanged.emit(value)

    def setValue(self,value):
        for widget in (self.slider,self.spin):
            widget.blockSignals(True)
        self.slider.setValue(round(value*10))
        self.spin.setValue(value)
        for widget in (self.slider,self.spin):
            widget.blockSignals(False)

    def value(self):
        return self.spin.value()


class DockTitle(QWidget):
    def __init__(self,dock,title):
        super().__init__(dock)
        self.setObjectName("dock-title")
        row = QHBoxLayout(self)
        row.setContentsMargins(14,8,8,8)
        label = QLabel(title)
        label.setStyleSheet("font-weight:600;")
        row.addWidget(label,1)
        close = QPushButton("×")
        close.setObjectName("dock-close")
        close.setFixedSize(26,26)
        close.setToolTip("Ukryj panel — możesz przywrócić go w menu Widok")
        close.clicked.connect(dock.hide)
        row.addWidget(close)


class PageDelegate(QStyledItemDelegate):
    def initStyleOption(self,option,index):
        super().initStyleOption(option,index)
        option.decorationPosition = QStyleOptionViewItem.Top
        option.decorationAlignment = Qt.AlignHCenter
        option.displayAlignment = Qt.AlignCenter
