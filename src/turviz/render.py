from __future__ import annotations

from PySide6.QtGui import QColor, QImage, QPainter

from .engine import TapeSnapshot


def state_colors(state_names: tuple[str, ...]) -> dict[str, QColor]:
    """Assign evenly spaced, readable HSV hues to the machine states."""
    if not state_names:
        return {}
    return {
        name: QColor.fromHsv(int(index * 360 / len(state_names)) % 360, 190, 235)
        for index, name in enumerate(state_names)
    }


def render_trace(
    snapshots: tuple[TapeSnapshot, ...],
    *,
    cell_size: int = 24,
    margin: int = 8,
    show_head: bool = True,
    state_color_map: dict[str, QColor] | None = None,
    max_rows: int = 200,
    max_columns: int = 200,
) -> QImage:
    if max_rows < 1 or max_columns < 1:
        raise ValueError("Maximum dimensions must be positive")
    if not snapshots:
        snapshots = (TapeSnapshot({}, 0, ""),)
    snapshots = snapshots[-max_rows:]
    current = snapshots[-1]
    positions = {position for snapshot in snapshots for position in snapshot.cells}
    positions.update(snapshot.head for snapshot in snapshots)
    left, right = min(positions), max(positions)
    if right - left + 1 > max_columns:
        half = max_columns // 2
        left = current.head - half
        right = left + max_columns - 1
    width = (right - left + 1) * cell_size + margin * 2
    height = len(snapshots) * cell_size + margin * 2
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("#e9edf2"))
    painter = QPainter(image)
    painter.fillRect(
        margin,
        margin,
        (right - left + 1) * cell_size,
        len(snapshots) * cell_size,
        QColor("#111827"),
    )
    grid_color = QColor("#64748b")
    for row, snapshot in enumerate(snapshots):
        y = margin + row * cell_size
        for position, value in snapshot.cells.items():
            if not value:
                continue
            x = margin + (position - left) * cell_size
            painter.fillRect(x, y, cell_size, cell_size, QColor("#ffffff"))
        if show_head:
            head_x = margin + (snapshot.head - left) * cell_size
            head_color = QColor(
                (state_color_map or {}).get(snapshot.state, QColor("#9ca3af"))
            )
            head_color.setAlpha(128)
            painter.fillRect(
                head_x,
                y,
                cell_size,
                cell_size,
                head_color,
            )
    if cell_size >= 4:
        painter.setPen(grid_color)
        for row in range(len(snapshots) + 1):
            y = margin + row * cell_size
            painter.drawLine(margin, y, width - margin, y)
        for column in range(right - left + 2):
            x = margin + column * cell_size
            painter.drawLine(x, margin, x, height - margin)
    painter.end()
    return image
