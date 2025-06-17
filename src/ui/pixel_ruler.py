from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QFontMetrics
from PySide6.QtCore import Qt, QPoint

class PixelRulerOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.initial_pos = QPoint(-1, -1)
        self.current_pos = QPoint(-1, -1)
        self.is_measuring = False

        # Set mouse tracking to true to get mouseMoveEvents even when no button is pressed
        self.setMouseTracking(True)

    def start_measurement(self, pos):
        print(f"[DEBUG] Ruler: start_measurement (called internally) at {pos}")
        self.initial_pos = pos
        self.current_pos = pos
        self.is_measuring = True
        self.update() # Redraw the ruler

    def update_measurement(self, pos):
        if self.is_measuring:
            self.current_pos = pos
            self.update()

    def stop_measurement(self):
        print("[DEBUG] Ruler: stop_measurement (called internally)")
        if self.is_measuring:
            self.is_measuring = False
            self.initial_pos = QPoint(-1, -1)
            self.current_pos = QPoint(-1, -1)
            self.update()

    def mousePressEvent(self, event):
        print(f"[DEBUG] Ruler: mousePressEvent at {event.globalPosition().toPoint()}")
        if event.button() == Qt.MouseButton.LeftButton:
            self.grabMouse() # Nắm bắt chuột khi bắt đầu đo
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False) # Cho phép nhận sự kiện chuột
            self.start_measurement(event.globalPosition().toPoint()) # Gọi start_measurement sau khi grab chuột
        elif event.button() == Qt.MouseButton.RightButton:
            self.stop_measurement_and_release_mouse() # Phương thức mới để dừng và nhả chuột

    def mouseMoveEvent(self, event):
        if self.is_measuring:
            self.current_pos = event.globalPosition().toPoint()
            self.update()
        
    def mouseReleaseEvent(self, event):
        print(f"[DEBUG] Ruler: mouseReleaseEvent at {event.globalPosition().toPoint()}")
        if event.button() == Qt.MouseButton.LeftButton:
            self.stop_measurement_and_release_mouse() # Phương thức mới để dừng và nhả chuột

    def stop_measurement_and_release_mouse(self):
        print("[DEBUG] Ruler: stop_measurement_and_release_mouse")
        if self.is_measuring:
            self.is_measuring = False
            self.initial_pos = QPoint(-1, -1)
            self.current_pos = QPoint(-1, -1)
            self.releaseMouse() # Nhả chuột
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True) # Trở lại trong suốt với sự kiện chuột
            self.update()

    def paintEvent(self, event):
        if not self.is_measuring or self.initial_pos.x() == -1:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Map global positions to widget local positions
        local_initial_pos = self.mapFromGlobal(self.initial_pos)
        local_current_pos = self.mapFromGlobal(self.current_pos)

        # Draw measuring lines (solid red)
        pen = QPen(QColor(255, 0, 0), 1, Qt.PenStyle.SolidLine) # Solid red line
        painter.setPen(pen)

        # Draw bounding box (dashed for clarity)
        dashed_pen = QPen(QColor(255, 0, 0, 150), 1, Qt.PenStyle.DashLine)
        painter.setPen(dashed_pen)
        painter.drawRect(local_initial_pos.x(), local_initial_pos.y(), 
                         local_current_pos.x() - local_initial_pos.x(), 
                         local_current_pos.y() - local_initial_pos.y())

        # Draw coordinates and dimensions
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0)) # Black text

        x_diff = abs(self.current_pos.x() - self.initial_pos.x())
        y_diff = abs(self.current_pos.y() - self.initial_pos.y())

        # Text for current position, ensure it's visible
        pos_text = f"X: {self.current_pos.x()}, Y: {self.current_pos.y()}"
        painter.drawText(local_current_pos.x() + 10, local_current_pos.y() + 10, pos_text)

        # Text for dimensions (width x height), ensure it's visible
        dim_text = f"Width: {x_diff}px, Height: {y_diff}px"
        painter.drawText(local_current_pos.x() + 10, local_current_pos.y() + 30, dim_text)

        # Text for distance, ensure it's visible
        dist_text = f"Dist: {int((x_diff**2 + y_diff**2)**0.5)}px"
        painter.drawText(local_current_pos.x() + 10, local_current_pos.y() + 50, dist_text)

        # Draw text showing the dimensions near the lines
        font_metrics = QFontMetrics(font)
        
        # Draw width text
        if x_diff > 0:
            width_text = f"{x_diff}px"
            text_width = font_metrics.width(width_text)
            x_center = (local_initial_pos.x() + local_current_pos.x()) / 2
            # Adjust y_pos for better visibility
            y_pos_width = min(local_initial_pos.y(), local_current_pos.y()) - 5 
            painter.drawText(x_center - text_width / 2, y_pos_width, width_text)
        
        # Draw height text
        if y_diff > 0:
            height_text = f"{y_diff}px"
            text_height = font_metrics.height()
            # Adjust x_pos for better visibility
            x_pos_height = min(local_initial_pos.x(), local_current_pos.x()) - text_height - 5 
            y_center = (local_initial_pos.y() + local_current_pos.y()) / 2
            painter.drawText(x_pos_height, y_center + text_height / 2, height_text) 