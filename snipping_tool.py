from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor

class SnippingWidget(QWidget):
    on_selection_complete = pyqtSignal(QRect)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())

        self.begin = None
        self.end = None
        self.is_snipping = False

    def paintEvent(self, event):
        painter = QPainter(self)
        # Darken the whole screen
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        if self.is_snipping and self.begin and self.end:
            rect = QRect(self.begin, self.end).normalized()
            
            # Clear the selected region (make it fully transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            
            # Draw red border around selection
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawRect(rect)
            
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin = event.pos()
            self.end = self.begin
            self.is_snipping = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_snipping:
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_snipping = False
            rect = QRect(self.begin, self.end).normalized()
            self.hide()
            
            # If the user just clicked without dragging, ignore
            if rect.width() > 10 and rect.height() > 10:
                self.on_selection_complete.emit(rect)

            self.begin = None
            self.end = None

    def start_snipping(self):
        self.begin = None
        self.end = None
        self.is_snipping = False
        self.show()
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.activateWindow()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.begin = None
            self.end = None
            self.is_snipping = False
