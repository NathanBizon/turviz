from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .model import TuringMachine, Transition


class StateGraphWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.machine: TuringMachine | None = None
        self.colors: dict[str, QColor] = {}
        self.active_state: str | None = None
        self.setMinimumHeight(220)
        self.setToolTip("Graphe des états et de leurs transitions")

    def set_machine(
        self,
        machine: TuringMachine | None,
        colors: dict[str, QColor] | None = None,
        active_state: str | None = None,
    ) -> None:
        self.machine = machine
        self.colors = colors or {}
        self.active_state = active_state
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f8fafc"))
        if self.machine is None or not self.machine.rules:
            painter.setPen(QColor("#64748b"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Aucun graphe à afficher")
            return

        node_radius = 30.0
        center = QPointF(self.width() / 2, self.height() / 2)
        orbit = max(70.0, min(self.width(), self.height()) * 0.32)
        positions: dict[str, QPointF] = {}
        count = len(self.machine.rules)
        for index, rule in enumerate(self.machine.rules):
            angle = -math.pi / 2 + 2 * math.pi * index / count
            positions[rule.name] = QPointF(
                center.x() + orbit * math.cos(angle),
                center.y() + orbit * math.sin(angle),
            )

        for rule in self.machine.rules:
            for symbol, transition in ((0, rule.on_zero), (1, rule.on_one)):
                self._draw_transition(
                    painter,
                    positions[rule.name],
                    node_radius,
                    transition,
                    str(symbol),
                    positions,
                )

        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        for rule in self.machine.rules:
            point = positions[rule.name]
            color = self.colors.get(rule.name, QColor("#64748b"))
            if rule.name == self.active_state:
                painter.setPen(QPen(QColor("#0f172a"), 4))
            else:
                painter.setPen(QPen(QColor("#334155"), 2))
            painter.setBrush(color)
            painter.drawEllipse(point, node_radius, node_radius)
            painter.setPen(QColor("#0f172a"))
            painter.drawText(
                QRectF(point.x() - node_radius, point.y() - 10, node_radius * 2, 20),
                Qt.AlignmentFlag.AlignCenter,
                rule.name,
            )

    def _draw_transition(
        self,
        painter: QPainter,
        source: QPointF,
        radius: float,
        transition: Transition | None,
        symbol: str,
        positions: dict[str, QPointF],
    ) -> None:
        if transition is None:
            return
        target = positions[transition.next_state]
        if target == source:
            path = QPainterPath(source + QPointF(radius * 0.7, -radius * 0.7))
            path.cubicTo(
                source + QPointF(radius * 2.2, -radius * 2.3),
                source + QPointF(radius * 2.3, radius * 0.8),
                source + QPointF(radius * 0.55, radius * 0.55),
            )
            painter.setPen(QPen(QColor("#64748b"), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            label_point = source + QPointF(radius * 1.7, -radius * 1.3)
            self._draw_label(painter, label_point, f"{symbol}: {transition.direction}")
            return

        vector = target - source
        length = math.hypot(vector.x(), vector.y())
        unit = QPointF(vector.x() / length, vector.y() / length)
        start = source + unit * radius
        end = target - unit * radius
        painter.setPen(QPen(QColor("#64748b"), 1.5))
        normal = QPointF(-unit.y(), unit.x())
        curve_offset = 18.0 if symbol == "0" else -18.0
        control = (start + end) * 0.5 + normal * curve_offset
        path = QPainterPath(start)
        path.quadTo(control, end)
        painter.drawPath(path)
        arrow_angle = math.atan2(unit.y(), unit.x())
        arrow_size = 7
        left = end - QPointF(
            arrow_size * math.cos(arrow_angle - math.pi / 6),
            arrow_size * math.sin(arrow_angle - math.pi / 6),
        )
        right = end - QPointF(
            arrow_size * math.cos(arrow_angle + math.pi / 6),
            arrow_size * math.sin(arrow_angle + math.pi / 6),
        )
        painter.setBrush(QColor("#64748b"))
        painter.drawPolygon((end, left, right))
        label_point = (
            start * 0.25 + end * 0.25 + control * 0.5
        )
        self._draw_label(painter, label_point, f"{symbol}: {transition.direction}")

    @staticmethod
    def _draw_label(painter: QPainter, point: QPointF, text: str) -> None:
        rect = QRectF(point.x() - 35, point.y() - 12, 70, 24)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#f8fafc"))
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(QColor("#334155"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
