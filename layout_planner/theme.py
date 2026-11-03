# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Muhammad Naeem

STYLE = """
QDialog#LayoutPlannerDialog { background: #f3f6f7; color: #1d3338; }
QDialog#LayoutPlannerDialog QWidget { font-family: 'Segoe UI', 'Noto Sans', sans-serif; font-size: 12px; color: #263e43; }
QFrame#Header { background: #112d32; border: none; }
QFrame#Header QLabel { color: #ffffff; background: transparent; }
QFrame#Header QLabel[role="subtitle"] { color: #9fbec2; font-size: 10px; letter-spacing: 1px; }
QLabel[role="title"] { font-size: 20px; font-weight: 600; }
QLabel[role="section"] { font-size: 11px; font-weight: 600; color: #6a8087; }
QLabel[role="muted"] { color: #738a91; font-size: 11px; }
QLabel[role="hint"] { color: #728b88; font-size: 11px; padding: 12px; background: #eff8f3; border: 1px solid #d9eade; border-radius: 7px; }
QFrame#Sidebar, QFrame#Inspector { background: #ffffff; }
QScrollArea { background: #ffffff; border: none; }
QScrollArea > QWidget > QWidget { background: #ffffff; }
QSplitter::handle { background: #dfe7e9; width: 1px; }
QPushButton, QToolButton { background: #ffffff; border: 1px solid #d4e0e3; border-radius: 6px; padding: 8px 11px; color: #344e56; font-weight: 500; }
QPushButton:hover, QToolButton:hover { border-color: #6dafa0; background: #eff9f5; }
QPushButton:pressed, QToolButton:checked { background: #d9f3e8; color: #096d51; border-color: #60ba9d; }
QPushButton#Primary { background: #65dfb3; border: 1px solid #65dfb3; color: #103c31; font-weight: 600; padding: 9px 18px; }
QPushButton#Primary:hover { background: #8debc9; }
QPushButton#HeaderSecondary { background: #1c3a3f; border-color: #3b565b; color: #e0f0ed; }
QPushButton#Link { border: none; background: transparent; color: #16866b; padding: 6px 2px; text-align: left; }
QPushButton:disabled, QToolButton:disabled { color: #99aaa9; background: #eef2f1; border-color: #e3e8e6; }
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox { background: #f9fbfc; border: 1px solid #dce5e8; border-radius: 5px; padding: 7px; min-height: 18px; selection-background-color: #b9e6d5; color: #2a454d; }
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus { border: 1px solid #26aa85; background: #ffffff; }
QComboBox { padding-right: 22px; }
QComboBox QAbstractItemView { background: #ffffff; selection-background-color: #dff3e9; selection-color: #1e5341; }
QListWidget { background: #ffffff; border: none; outline: none; }
QListWidget::item { padding: 10px 9px; margin: 3px 0; border: 1px solid #e2e9e9; border-radius: 6px; }
QListWidget::item:selected { background: #e6f6ee; color: #12694d; border: 1px solid #89c9af; }
QListWidget::item:hover { background: #f1f8f5; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #a7bfc0; border-radius: 3px; background: #ffffff; }
QCheckBox::indicator:checked { background: #139f78; border-color: #139f78; }
QFrame#CanvasBar { background: #ffffff; border-bottom: 1px solid #dfe7e9; }
QFrame#StatusBar { background: #ffffff; border-top: 1px solid #dfe7e9; }
QLabel#Status { color: #22856a; font-size: 11px; }
QLabel#Status[warning="true"] { color: #b27327; }
QFrame[role="separator"] { background: #e7edef; max-height: 1px; }
QScrollBar:vertical { background: #f4f7f7; width: 7px; margin: 0; }
QScrollBar::handle:vertical { background: #c4d3d5; min-height: 25px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QPlainTextEdit { border: 1px solid #dbe6e6; background: #f9fbfc; border-radius: 7px; padding: 10px; }
"""
