import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.translations = []
        self.initUI()

    def initUI(self):
        # Set window flags for overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.Tool  # Prevents showing up in taskbar sometimes, though optional
        )
        # Make the background transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Determine the geometry of the entire screen
        screen = QApplication.primaryScreen()
        geometry = screen.geometry()
        self.setGeometry(geometry)
        
        self.show()

    def update_translations(self, translations):
        """
        Receives a list of dictionaries with format:
        {'rect': (x, y, w, h), 'translated_text': '...'}
        """
        self.translations = translations
        self.update()  # Request a repaint

    def clear_overlay(self):
        self.translations = []
        self.update()

    def paintEvent(self, event):
        if not self.translations:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for item in self.translations:
            x, y, w, h = item['rect']
            text = item.get('translated_text', '')

            if not text:
                continue

            # Draw a very light semi-transparent background for the text
            bg_rect = QRect(x, y, w, h)
            margin = 4
            expanded_rect = QRect(x - margin, y - margin, w + margin*2, h + margin*2)

            painter.setBrush(QBrush(QColor(0, 0, 0, 150))) # Softer black background
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(expanded_rect, 5, 5)

            # Auto-adjust font size roughly based on height of the selected region
            # We assume it might be a paragraph, so we adjust size reasonably
            font = QFont("Arial", 12, QFont.Weight.Bold)
            adjusted_size = max(12, int(h * 0.15)) 
            adjusted_size = min(adjusted_size, 24)
            font.setPointSize(adjusted_size)
            painter.setFont(font)
            
            # Fake text outline
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (0,-1), (0,1), (-1,0), (1,0)]:
                painter.drawText(bg_rect.translated(dx, dy), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)

            # Inner white text
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)

        painter.end()
