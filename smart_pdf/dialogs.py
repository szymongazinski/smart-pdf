from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout


class ScopeDialog(QDialog):
    def __init__(self,title,current,selected,count,parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(390,180)
        self.current,self.selected,self.count = current,selected,count
        layout = QFormLayout(self)
        self.scope = QComboBox()
        self.scope.addItems(["Bieżąca strona",f"Zaznaczone strony ({len(selected)})","Wszystkie strony"])
        layout.addRow("Zakres",self.scope)
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
