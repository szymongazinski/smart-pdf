from PySide6.QtWidgets import (QComboBox,QDialog,QDialogButtonBox,QFormLayout,
                              QLabel,QLineEdit,QRadioButton,QVBoxLayout)

from smart_pdf.page_ranges import parse_page_ranges,remaining_pages,format_page_ranges


class CutPagesDialog(QDialog):
    def __init__(self,count,parent=None):
        super().__init__(parent)
        self.count=count
        self.setWindowTitle('Wytnij strony')
        self.resize(560,360)
        layout=QVBoxLayout(self)
        heading=QLabel('Wybierz strony dokumentu')
        heading.setStyleSheet('font-size:18px;font-weight:600;padding-bottom:8px;')
        layout.addWidget(heading)
        self.keep=QRadioButton('Zostaw tylko wskazane strony')
        self.remove=QRadioButton('Usuń wskazane strony')
        self.keep.setChecked(True)
        layout.addWidget(self.keep)
        layout.addWidget(self.remove)
        layout.addSpacing(8)
        layout.addWidget(QLabel(f'Numery według kolejności w PDF: 1-{count}'))
        self.ranges=QLineEdit()
        self.ranges.setMaxLength(10000)
        self.ranges.setPlaceholderText('np. 11-19 i 20-35, 42')
        self.ranges.setAccessibleName('Zakres stron')
        layout.addWidget(self.ranges)
        help_text=QLabel('Myślnik łączy początek i koniec zakresu. Pozostały tekst jest ignorowany.\n'
                        'Strony zachowają kolejność z dokumentu; powtórzenia są pomijane.')
        help_text.setWordWrap(True)
        help_text.setStyleSheet('color:#74839a;font-size:9pt;')
        layout.addWidget(help_text)
        self.preview=QLabel()
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(58)
        layout.addWidget(self.preview)
        save_hint=QLabel('Zmianę możesz cofnąć przez Ctrl+Z. Oryginał zmieni się dopiero po eksporcie do tego samego pliku.')
        save_hint.setWordWrap(True)
        layout.addWidget(save_hint)
        layout.addStretch()
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.apply_button=buttons.button(QDialogButtonBox.Ok)
        self.apply_button.setText('Zastosuj')
        buttons.button(QDialogButtonBox.Cancel).setText('Anuluj')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.ranges.textChanged.connect(self.update_preview)
        self.keep.toggled.connect(self.update_preview)
        self.remove.toggled.connect(self.update_preview)
        self.update_preview()
        self.ranges.setFocus()

    def mode(self):
        return 'keep' if self.keep.isChecked() else 'remove'

    def indices(self):
        return remaining_pages(self.ranges.text(),self.count,self.mode())

    def update_preview(self):
        try:
            selected=parse_page_ranges(self.ranges.text(),self.count)
            remaining=self.indices()
            normalized=format_page_ranges(selected)
            if len(normalized)>220:
                normalized=normalized[:217]+'…'
            self.preview.setText(f'Rozpoznane strony: {normalized}\n'
                                 f'Pozostanie: {len(remaining)}  •  Usuniętych: {self.count-len(remaining)}')
            self.preview.setStyleSheet('color:#245ade;')
            self.apply_button.setEnabled(True)
        except ValueError as error:
            self.preview.setText(str(error))
            self.preview.setStyleSheet('color:#b04444;')
            self.apply_button.setEnabled(False)

    def accept(self):
        # Also validate Enter/default-button activation, independently of paint state.
        try:
            self.indices()
        except ValueError:
            self.update_preview()
            return
        super().accept()


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
