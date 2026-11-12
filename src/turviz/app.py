from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QFont, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
)

from .engine import run_machine, trace_metrics
from .graph import StateGraphWidget
from .parser import ParseError, parse_tm
from .render import render_trace, state_colors


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TurViz — Turing machine trace")
        self.resize(1_200, 760)
        self.current_path: Path | None = None
        self.image = None
        self.execution = None
        self.execution_colors = {}
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._advance_playback)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("State, write0, move0, next state0, write1, move1, next state1")
        self.editor.setFont(QFont("Cascadia Mono", 11))
        self.editor.textChanged.connect(self._handle_editor_changed)
        self.state_table = QTableWidget(0, 4)
        self.state_table.setHorizontalHeaderLabels(("State", "Color", "Symbol 0", "Symbol 1"))
        self.state_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.state_table.verticalHeader().setVisible(False)
        self.state_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.state_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.state_table.setToolTip("Colors match the HSV hues used for the head.")
        self.graph = StateGraphWidget()
        state_views = QTabWidget()
        state_views.addTab(self.state_table, "States")
        state_views.addTab(self.graph, "Graph")
        editor_panel = QSplitter(Qt.Orientation.Vertical)
        editor_panel.addWidget(self.editor)
        editor_panel.addWidget(state_views)
        editor_panel.setSizes([500, 220])
        self.preview = QLabel("The trace will appear here")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("background: #e9edf2; color: #475569;")
        self.insights = QLabel("Insights will appear after execution.")
        self.insights.setWordWrap(True)
        self.insights.setStyleSheet(
            "background: #f1f5f9; color: #334155; padding: 8px; "
            "border-top: 1px solid #cbd5e1;"
        )
        preview_panel = QSplitter(Qt.Orientation.Vertical)
        preview_panel.addWidget(self.preview)
        preview_panel.addWidget(self.insights)
        preview_panel.setSizes([600, 80])
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(preview_panel)
        splitter = QSplitter()
        splitter.addWidget(editor_panel)
        splitter.addWidget(scroll)
        splitter.setSizes([450, 750])
        self.setCentralWidget(splitter)
        self.setStatusBar(QStatusBar())
        self._build_toolbar()
        QShortcut("Ctrl+Enter", self, self.execute)
        QShortcut("Ctrl+S", self, self.save_file)
        self._load_example()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Actions")
        self.addToolBar(toolbar)
        for label, callback in (("New", self.new_file), ("Open", self.open_file), ("Save", self.save_file)):
            action = QAction(label, self)
            action.triggered.connect(callback)
            toolbar.addAction(action)
        add_state = QPushButton("Add state")
        add_state.clicked.connect(self.add_state)
        toolbar.addWidget(add_state)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Max steps: "))
        self.steps = QSpinBox()
        self.steps.setRange(0, 1_000_000)
        self.steps.setValue(1_000)
        toolbar.addWidget(self.steps)
        self.show_head = QCheckBox("Color head by state")
        self.show_head.setChecked(True)
        toolbar.addWidget(self.show_head)
        run_button = QPushButton("Run")
        run_button.clicked.connect(self.execute)
        toolbar.addWidget(run_button)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Step: "))
        self.step_slider = QSlider(Qt.Orientation.Horizontal)
        self.step_slider.setRange(0, 0)
        self.step_slider.setFixedWidth(150)
        self.step_slider.valueChanged.connect(self._show_step)
        toolbar.addWidget(self.step_slider)
        self.previous_step = QPushButton("◀")
        self.previous_step.setToolTip("Previous step")
        self.previous_step.clicked.connect(lambda: self.step_slider.setValue(self.step_slider.value() - 1))
        toolbar.addWidget(self.previous_step)
        self.next_step = QPushButton("▶")
        self.next_step.setToolTip("Next step")
        self.next_step.clicked.connect(lambda: self.step_slider.setValue(self.step_slider.value() + 1))
        toolbar.addWidget(self.next_step)
        self.play_button = QPushButton("Play")
        self.play_button.setToolTip("Play the trace automatically")
        self.play_button.clicked.connect(self._toggle_playback)
        toolbar.addWidget(self.play_button)
        toolbar.addWidget(QLabel("ms: "))
        self.playback_speed = QSpinBox()
        self.playback_speed.setRange(50, 2_000)
        self.playback_speed.setSingleStep(50)
        self.playback_speed.setValue(350)
        self.playback_speed.valueChanged.connect(self.playback_timer.setInterval)
        toolbar.addWidget(self.playback_speed)
        export_button = QPushButton("Export PNG")
        export_button.clicked.connect(self.export_image)
        toolbar.addWidget(export_button)

    def _load_example(self) -> None:
        self.editor.setPlainText("A,1,R,B,0,L,B\nB,HALT,1,R,A\n")
        self._refresh_state_table()

    def _handle_editor_changed(self) -> None:
        self._stop_playback()
        self._clear_execution()
        self._refresh_state_table()

    def new_file(self) -> None:
        self.current_path = None
        self.editor.clear()
        self.state_table.setRowCount(0)
        self.graph.set_machine(None)
        self._clear_execution()
        self.statusBar().showMessage("New file")

    def open_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Open a TM file", "", "Turing machines (*.tm);;All files (*)")
        if filename:
            path = Path(filename)
            self.current_path = path
            self.editor.setPlainText(path.read_text(encoding="utf-8"))
            self._refresh_state_table()
            self.statusBar().showMessage(f"Opened: {path.name}")

    def save_file(self) -> None:
        path = self.current_path
        if path is None:
            filename, _ = QFileDialog.getSaveFileName(self, "Save the machine", "", "Turing machines (*.tm)")
            if not filename:
                return
            path = Path(filename)
            if path.suffix.lower() != ".tm":
                path = path.with_suffix(".tm")
            self.current_path = path
        path.write_text(self.editor.toPlainText(), encoding="utf-8")
        self.statusBar().showMessage(f"Saved: {path.name}")

    def add_state(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Add a state")
        form = QFormLayout(dialog)
        state = QLineEdit()
        state.setPlaceholderText("Ex. SCAN")
        form.addRow("Name:", state)
        zero_write = QComboBox()
        zero_write.addItems(["HALT", "0", "1"])
        zero_direction = QComboBox()
        zero_direction.addItems(["R", "L"])
        zero_target = QLineEdit()
        zero_target.setPlaceholderText("Target state")
        form.addRow("Symbol 0:", zero_write)
        form.addRow("Move 0:", zero_direction)
        form.addRow("Next state 0:", zero_target)
        one_write = QComboBox()
        one_write.addItems(["HALT", "0", "1"])
        one_direction = QComboBox()
        one_direction.addItems(["R", "L"])
        one_target = QLineEdit()
        one_target.setPlaceholderText("Target state")
        form.addRow("Symbol 1:", one_write)
        form.addRow("Move 1:", one_direction)
        form.addRow("Next state 1:", one_target)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name = state.text().strip()
        if not name:
            QMessageBox.warning(self, "Incomplete state", "Enter a state name.")
            return
        try:
            existing_machine = parse_tm(self.editor.toPlainText())
            if any(rule.name == name for rule in existing_machine.rules):
                raise ValueError(f"State {name} already exists.")
        except ParseError:
            pass
        except ValueError as error:
            QMessageBox.warning(self, "Duplicate state", str(error))
            return

        def branch(write: QComboBox, direction: QComboBox, target: QLineEdit) -> str:
            if write.currentText() == "HALT":
                return "HALT"
            destination = target.text().strip()
            if not destination:
                raise ValueError("Each normal branch needs a target state.")
            return f"{write.currentText()},{direction.currentText()},{destination}"

        try:
            line = f"{name},{branch(zero_write, zero_direction, zero_target)},{branch(one_write, one_direction, one_target)}"
        except ValueError as error:
            QMessageBox.warning(self, "Incomplete transition", str(error))
            return
        text = self.editor.toPlainText().rstrip()
        self.editor.setPlainText(f"{text}\n{line}\n" if text else f"{line}\n")
        self.statusBar().showMessage(f"State {name} added")

    def execute(self) -> None:
        self._stop_playback()
        try:
            machine = parse_tm(self.editor.toPlainText())
            result = run_machine(machine, self.steps.value())
        except (ParseError, ValueError) as error:
            QMessageBox.critical(self, "Invalid machine", str(error))
            return
        colors = state_colors(tuple(rule.name for rule in machine.rules))
        self.execution = result
        self.execution_colors = colors
        self.step_slider.blockSignals(True)
        self.step_slider.setRange(0, len(result.snapshots) - 1)
        self.step_slider.setValue(len(result.snapshots) - 1)
        self.step_slider.blockSignals(False)
        self._show_step(self.step_slider.value())
        suffix = ""
        if result.cycle_length is not None:
            suffix = f" — period {result.cycle_length}"
        self.statusBar().showMessage(f"{result.reason} — {len(result.snapshots) - 1} steps{suffix}")

    def _show_step(self, step: int) -> None:
        if self.execution is None:
            return
        snapshots = self.execution.snapshots[: step + 1]
        current = snapshots[-1]
        try:
            machine = parse_tm(self.editor.toPlainText())
        except ParseError:
            return
        self._refresh_state_table(machine, self.execution_colors, current.state)
        metrics = trace_metrics(snapshots)
        self.insights.setText(
            f"<b>Insights through step {step}</b> · "
            f"{metrics.visited_positions} position(s) visited · "
            f"max width {metrics.max_width} · "
            f"maximum {metrics.max_ones} cell(s) set to 1 · "
            f"final {metrics.final_ones} cell(s) set to 1"
        )
        self.image = render_trace(
            snapshots,
            show_head=self.show_head.isChecked(),
            state_color_map=self.execution_colors,
        )
        self.preview.setPixmap(QPixmap.fromImage(self.image))
        self.previous_step.setEnabled(step > 0)
        self.next_step.setEnabled(step < len(self.execution.snapshots) - 1)
        self.statusBar().showMessage(
            f"Step {step}/{len(self.execution.snapshots) - 1} — "
            f"state {current.state}, head {current.head}, "
            f"{sum(current.cells.values())} cell(s) set to 1"
        )

    def _toggle_playback(self) -> None:
        if self.execution is None or self.step_slider.maximum() == 0:
            return
        if self.playback_timer.isActive():
            self._stop_playback()
            return
        if self.step_slider.value() >= self.step_slider.maximum():
            self.step_slider.setValue(0)
        self.playback_timer.start(self.playback_speed.value())
        self.play_button.setText("Pause")

    def _advance_playback(self) -> None:
        next_step = self.step_slider.value() + 1
        if next_step >= self.step_slider.maximum():
            self.step_slider.setValue(self.step_slider.maximum())
            self._stop_playback()
        else:
            self.step_slider.setValue(next_step)

    def _stop_playback(self) -> None:
        self.playback_timer.stop()
        if hasattr(self, "play_button"):
            self.play_button.setText("Play")

    def _clear_execution(self) -> None:
        self._stop_playback()
        self.execution = None
        self.image = None
        self.insights.setText("Insights will appear after execution.")
        self.step_slider.setRange(0, 0)
        self.previous_step.setEnabled(False)
        self.next_step.setEnabled(False)

    def _refresh_state_table(self, machine=None, colors=None, active_state: str | None = None) -> None:
        if machine is None:
            try:
                machine = parse_tm(self.editor.toPlainText())
            except ParseError:
                self.state_table.setRowCount(0)
                self.graph.set_machine(None)
                return
        if colors is None:
            colors = state_colors(tuple(rule.name for rule in machine.rules))
        self.graph.set_machine(machine, colors, active_state)
        self.state_table.setRowCount(len(machine.rules))
        for row, rule in enumerate(machine.rules):
            state_item = QTableWidgetItem(rule.name)
            if rule.name == active_state:
                state_item.setText(f"{rule.name} (actif)")
                self.state_table.selectRow(row)
            self.state_table.setItem(row, 0, state_item)
            color_item = QTableWidgetItem()
            color = colors[rule.name]
            color_item.setBackground(color)
            color_item.setToolTip(f"HSV : {color.hue()}, {color.saturation()}, {color.value()}")
            self.state_table.setItem(row, 1, color_item)
            self.state_table.setItem(row, 2, QTableWidgetItem(self._transition_text(rule.on_zero)))
            self.state_table.setItem(row, 3, QTableWidgetItem(self._transition_text(rule.on_one)))

    @staticmethod
    def _transition_text(transition) -> str:
        if transition is None:
            return "HALT"
        return f"writes {transition.write}, {transition.direction} → {transition.next_state}"

    def export_image(self) -> None:
        if self.image is None:
            self.execute()
        if self.image is None:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Export the trace", "", "PNG image (*.png)")
        if filename:
            self.image.save(filename, "PNG")
            self.statusBar().showMessage(f"Image exported: {Path(filename).name}")


def run() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
