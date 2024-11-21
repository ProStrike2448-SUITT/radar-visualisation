import asyncio
import json
import math
import sys
from typing import TypedDict

import websockets
from PySide6.QtCore import QObject, QPoint, QThread, Signal, Slot
from PySide6.QtGui import QBrush, QCloseEvent, QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget


class EchoResponse(TypedDict):
    time: float  # Час поширення імпульсу в секундах (двосторонній шлях)
    power: float  # Потужність відбитого сигналу (значення від 0 до 1)


class WebSocketResponse(TypedDict):
    scanAngle: int  # Кут зондування у градусах (від 0 до 360)
    pulseDuration: int  # Тривалість імпульсу в мікросекундах
    echoResponses: list[EchoResponse]


class WebSocketWorker(QObject):
    message_received = Signal(dict)
    connection_status = Signal(bool)

    def __init__(self):
        super().__init__()
        self.running = False

    @Slot()
    def start_websocket(self):
        self.running = True
        asyncio.run(self.websocket_client())

    async def websocket_client(self):
        while self.running:
            try:
                async with websockets.connect("ws://localhost:4000") as websocket:
                    self.connection_status.emit(True)
                    while self.running:
                        try:
                            message = await websocket.recv()
                            json_data = json.loads(message)
                            self.message_received.emit(json_data)
                        except websockets.exceptions.ConnectionClosed:
                            break
            except Exception as e:
                print(f"WebSocket connection error: {e}")
                self.connection_status.emit(False)
                await asyncio.sleep(5)

    def stop(self):
        self.running = False


class RadarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(300, 300)
        self.angle = 0
        self.dot_position = QPoint(150, 150)
        self.dot_visible = False

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        self.draw_radar(painter)

    def draw_radar(self, painter: QPainter):
        # Draw radar background
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(0, 255, 0))  # Green outline
        painter.setBrush(QBrush(QColor(0, 0, 0)))  # Black fill
        painter.drawEllipse(10, 10, 280, 280)

        # Draw concentric circles
        for i in range(1, 4):
            radius = i * 70
            painter.drawEllipse(150 - radius, 150 - radius, radius * 2, radius * 2)

        # Draw radar beam
        painter.save()
        painter.translate(150, 150)
        painter.rotate(self.angle)
        painter.setBrush(QBrush(QColor(0, 255, 0, 100)))
        painter.drawRect(-2, 0, 200, 4)
        painter.restore()

        # Draw dot if visible
        if self.dot_visible:
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.drawEllipse(self.dot_position.x() - 3, self.dot_position.y() - 3, 6, 6)

    def update_radar_data(self, angle: int, position: QPoint):
        self.angle = angle
        self.dot_position = position
        self.dot_visible = True
        self.update()


class RadarWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Radar Data Display")
        self.setGeometry(100, 100, 400, 400)

        # Create radar widget
        self.radar_widget = RadarWidget()
        self.setCentralWidget(self.radar_widget)

        # Setup WebSocket thread
        self.websocket_thread = QThread()
        self.websocket_worker = WebSocketWorker()

        # Move worker to thread
        self.websocket_worker.moveToThread(self.websocket_thread)

        # Connect signals
        self.websocket_worker.message_received.connect(self.process_message)
        self.websocket_worker.connection_status.connect(self.handle_connection)

        # Start thread
        self.websocket_thread.started.connect(self.websocket_worker.start_websocket)
        self.websocket_thread.start()

    def process_message(self, json_object: WebSocketResponse):
        try:
            if json_object.get("echoResponses"):
                angle = json_object["scanAngle"]
                relative_distance = ((json_object["echoResponses"][0]["time"] * 300_000) / 2) / 200

                x = relative_distance * 150 * math.cos(math.radians(angle)) + 150
                y = relative_distance * 150 * math.sin(math.radians(angle)) + 150

                # Update radar widget
                self.radar_widget.update_radar_data(angle, QPoint(int(x), int(y)))

        except Exception as e:
            print(f"Error processing message: {e}")

    def handle_connection(self, status):
        if status:
            print("WebSocket Connected")
        else:
            print("WebSocket Disconnected")

    def closeEvent(self, event: QCloseEvent):
        # Cleanup thread on window close
        self.websocket_worker.stop()
        self.websocket_thread.quit()
        self.websocket_thread.wait()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = RadarWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
