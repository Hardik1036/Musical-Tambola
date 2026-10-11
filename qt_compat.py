"""
Musical Tambola - Qt Compatibility Layer
Provides a uniform abstraction across PyQt6, PySide6, and PyQt5.
Ensures zero DLL conflicts across Anaconda, standalone Python, and modern environments.
"""
import os
import sys

# Try QtPy first as it handles environment bindings cleanly
try:
    from qtpy import QtCore, QtGui, QtWidgets
    from qtpy.QtCore import Qt, QTimer, Signal as pyqtSignal
except ImportError:
    try:
        from PyQt6 import QtCore, QtGui, QtWidgets
        from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    except ImportError:
        try:
            from PySide6 import QtCore, QtGui, QtWidgets
            from PySide6.QtCore import Qt, QTimer, Signal as pyqtSignal
        except ImportError:
            from PyQt5 import QtCore, QtGui, QtWidgets
            from PyQt5.QtCore import Qt, QTimer, pyqtSignal

# Core Qt classes
QFont = QtGui.QFont
QColor = QtGui.QColor
QIcon = QtGui.QIcon
QPainter = QtGui.QPainter
QPen = QtGui.QPen
QBrush = QtGui.QBrush
QLinearGradient = QtGui.QLinearGradient
QPainterPath = QtGui.QPainterPath
QPixmap = QtGui.QPixmap
QRect = QtCore.QRect
QRectF = QtCore.QRectF

QApplication = QtWidgets.QApplication
QMainWindow = QtWidgets.QMainWindow
QWidget = QtWidgets.QWidget
QVBoxLayout = QtWidgets.QVBoxLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QGridLayout = QtWidgets.QGridLayout
QLabel = QtWidgets.QLabel
QPushButton = QtWidgets.QPushButton
QSlider = QtWidgets.QSlider
QProgressBar = QtWidgets.QProgressBar
QFrame = QtWidgets.QFrame
QMessageBox = QtWidgets.QMessageBox
QScrollArea = QtWidgets.QScrollArea
QCheckBox = QtWidgets.QCheckBox
QRadioButton = QtWidgets.QRadioButton
QButtonGroup = QtWidgets.QButtonGroup
QSizePolicy = QtWidgets.QSizePolicy
QSpinBox = QtWidgets.QSpinBox
QComboBox = QtWidgets.QComboBox
QLineEdit = QtWidgets.QLineEdit
QTableWidget = QtWidgets.QTableWidget
QTableWidgetItem = QtWidgets.QTableWidgetItem
QHeaderView = QtWidgets.QHeaderView
QFileDialog = QtWidgets.QFileDialog
QTabWidget = QtWidgets.QTabWidget
QStatusBar = QtWidgets.QStatusBar

# Normalize common Qt Enum differences between Qt5 and Qt6
if not hasattr(Qt, "Orientation"):
    Qt.Orientation = Qt
if not hasattr(Qt, "AlignmentFlag"):
    Qt.AlignmentFlag = Qt
if not hasattr(Qt, "CursorShape"):
    Qt.CursorShape = Qt

if not hasattr(QFont, "Weight"):
    class WeightCompat:
        Bold = getattr(QFont, "Bold", 75)
        Normal = getattr(QFont, "Normal", 50)
    QFont.Weight = WeightCompat

if not hasattr(QHeaderView, "ResizeMode"):
    QHeaderView.ResizeMode = QHeaderView
