STYLE = """
QMainWindow, QDialog { background: #f6f8fc; color: #25324a; }
QWidget { font-family: 'Segoe UI'; font-size: 10pt; }
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
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit { background: white; border: 1px solid #d4ddeb; border-radius: 5px; padding: 5px; selection-background-color: #2864ed; }
QDockWidget { background: #f8faff; }
QDockWidget::title { padding: 9px; background: #f3f6fc; font-weight: 600; }
QListWidget { background: #f8faff; border: none; padding: 5px; outline: none; }
QListWidget::item { padding: 9px; border: 1px solid transparent; border-radius: 6px; margin: 3px; }
QListWidget::item:selected { background: #e4edff; border-color: #afc8f9; color: #164abd; }
QStatusBar { background: white; border-top: 1px solid #dce2ed; padding: 4px; color: #64738c; }
QLabel#hero { font-size: 38pt; font-weight: 700; color: #1e3154; }
QLabel#subtitle { font-size: 13pt; color: #63738e; }
QScrollBar:vertical { background: #eef1f6; width: 11px; }
QScrollBar::handle:vertical { background: #bbc6d9; border-radius: 5px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
