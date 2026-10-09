STYLE = """
QMainWindow, QDialog { background: #f6f8fc; color: #25324a; }
QWidget { font-family: 'Segoe UI'; font-size: 10pt; color: #25324a; }
QWidget:disabled { color: #8a97ac; }
QMenuBar { background: #ffffff; padding: 3px; }
QMenuBar::item:selected, QMenu::item:selected { background: #e4edff; color: #164abd; }
QMenu { background: white; border: 1px solid #dce2ed; padding: 5px; }
QMenu::item { padding: 7px 24px; }
QToolBar { background: white; border: none; border-bottom: 1px solid #dce2ed; spacing: 5px; padding: 7px; }
QToolBar::separator { background: #dce2ed; width: 1px; margin: 5px; }
QToolButton { padding: 7px 10px; border: 1px solid transparent; border-radius: 6px; color: #34435b; }
QToolButton:hover { background: #f0f4fb; }
QToolButton:checked { background: #e4edff; color: #1855d1; border-color: #c4d6fb; }
QPushButton { background: white; border: 1px solid #d4ddeb; border-radius: 6px; padding: 7px 12px; }
QPushButton:hover { background: #edf3ff; border-color: #9ebcf6; }
QPushButton:checked { background: #e4edff; color: #1855d1; }
QPushButton#primary { background: #2864ed; color: white; border: none; font-weight: 600; padding: 12px 26px; }
QPushButton#primary:hover { background: #174ed0; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit { background: white; border: 1px solid #d4ddeb; border-radius: 5px; padding: 5px; selection-background-color: #2864ed; color: #25324a; }
QLineEdit { placeholder-text-color: #8290a5; }
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0; height: 0; border: none; }
QSpinBox QLineEdit, QDoubleSpinBox QLineEdit { border: none; padding: 0; background: transparent; }
QComboBox::drop-down { border: none; width: 20px; }
QToolButton::menu-button { width: 16px; border: none; border-left: 1px solid #e2e8f1; background: #f6f8fc; border-top-right-radius: 5px; border-bottom-right-radius: 5px; }
QDockWidget { background: #f8faff; }
QDockWidget::title { padding: 9px; background: #f3f6fc; font-weight: 600; }
QListWidget { background: #f8faff; border: none; padding: 5px; outline: none; }
QListWidget::item { padding: 9px; border: 1px solid transparent; border-radius: 6px; margin: 3px; }
QListWidget::item:selected { background: #e4edff; border-color: #afc8f9; color: #164abd; }
QListWidget::item:hover { background: #edf3ff; border-color: #96b8f7; }
QListWidget::item:selected:hover { background: #dce8ff; border-color: #6699f3; }
QWidget#dock-title { background: #f6f8fc; border-bottom: 1px solid #e2e8f1; }
QPushButton#dock-close { padding: 0; border: none; background: transparent; color: #71839d; font-size: 16pt; }
QPushButton#dock-close:hover { background: #e4edff; color: #245ade; }
QSlider::groove:horizontal { height: 4px; background: #dce4f0; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #2864ed; border-radius: 2px; }
QSlider::handle:horizontal { background: #ffffff; border: 2px solid #2864ed; width: 12px; height: 12px; margin: -5px 0; border-radius: 7px; }
QSlider::handle:horizontal:hover { background: #dce9ff; }
QStatusBar { background: white; border-top: 1px solid #dce2ed; padding: 4px; color: #64738c; }
QLabel#hero { font-size: 38pt; font-weight: 700; color: #1e3154; }
QLabel#subtitle { font-size: 13pt; color: #63738e; }
QScrollBar:vertical { background: #eef1f6; width: 11px; }
QScrollBar::handle:vertical { background: #bbc6d9; border-radius: 5px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: #eef1f6; height: 11px; }
QScrollBar::handle:horizontal { background: #bbc6d9; border-radius: 5px; min-width: 24px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
"""
