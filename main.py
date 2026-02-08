import sys
from dataclasses import dataclass
from typing import List

from PySide6 import QtCore, QtGui, QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


@dataclass
class InvestmentMethod:
    name: str
    annual_return: float  # percent
    target_weight: float  # percent


def simulate_growth(
    principal: float,
    years: int,
    rebalance_months: int,
    methods: List[InvestmentMethod],
):
    if years <= 0:
        return [0], [principal]

    months = years * 12
    # Normalize weights if they sum to 100, otherwise return empty to signal invalid input
    weight_sum = sum(m.target_weight for m in methods)
    if weight_sum <= 0:
        return None, None
    if abs(weight_sum - 100.0) > 0.01:
        return None, None

    # Initialize holdings based on target weights
    holdings = [principal * (m.target_weight / 100.0) for m in methods]
    monthly_rates = [(1 + m.annual_return / 100.0) ** (1 / 12) - 1 for m in methods]

    timeline = [0]
    total_values = [principal]

    for month in range(1, months + 1):
        # Grow each holding for the month
        for i in range(len(holdings)):
            holdings[i] *= (1 + monthly_rates[i])

        if rebalance_months > 0 and (month % rebalance_months == 0):
            total = sum(holdings)
            for i, m in enumerate(methods):
                holdings[i] = total * (m.target_weight / 100.0)

        timeline.append(month)
        total_values.append(sum(holdings))

    return timeline, total_values


class ChartWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self._xs = []
        self._ys = []
        self._ax = None
        self._annot = None
        self._dot = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.canvas.mpl_connect("motion_notify_event", self.on_move)

    def plot(self, months, values):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(months, values, color="#1f77b4", linewidth=2)
        ax.set_xlabel("Year")
        ax.set_ylabel("Total Asset")
        ax.grid(True, linestyle="--", alpha=0.4)
        self._dot = ax.plot([], [], "o", color="#1f77b4", markersize=5, zorder=5)[0]
        self._annot = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 12),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="#1f2a35", ec="#4a4a4a", alpha=0.9),
            color="#f2f2f2",
        )
        self._annot.set_visible(False)
        self.figure.tight_layout()
        self.canvas.draw()
        self._ax = ax
        self._xs = months
        self._ys = values

    def on_move(self, event):
        if self._ax is None or event.inaxes != self._ax or event.xdata is None:
            if self._annot is not None:
                self._annot.set_visible(False)
            if self._dot is not None:
                self._dot.set_data([], [])
                self.canvas.draw_idle()
            return
        # Find nearest point for display
        x = event.xdata
        idx = min(range(len(self._xs)), key=lambda i: abs(self._xs[i] - x))
        if self._annot is not None:
            self._annot.xy = (self._xs[idx], self._ys[idx])
            self._annot.set_text(
                f"Year: {self._xs[idx]:.2f}\nTotal: {self._ys[idx]:.2f}"
            )
            self._annot.set_visible(True)
            # Choose the quadrant with the least overflow (closest to the point)
            renderer = self.canvas.get_renderer()
            if renderer is not None:
                ax_bbox = self._ax.get_window_extent(renderer=renderer)
                pad = 10
                candidates = [
                    (pad, pad, "left"),   # Q1: right-up
                    (-pad, pad, "right"), # Q2: left-up
                    (pad, -pad, "left"),  # Q4: right-down
                    (-pad, -pad, "right"),# Q3: left-down
                ]
                best = None
                best_overflow = None
                for ox, oy, ha in candidates:
                    self._annot.set_position((ox, oy))
                    self._annot.set_ha(ha)
                    bbox = self._annot.get_window_extent(renderer=renderer)
                    overflow_left = max(0, ax_bbox.x0 - bbox.x0)
                    overflow_right = max(0, bbox.x1 - ax_bbox.x1)
                    overflow_bottom = max(0, ax_bbox.y0 - bbox.y0)
                    overflow_top = max(0, bbox.y1 - ax_bbox.y1)
                    overflow_area = overflow_left + overflow_right + overflow_bottom + overflow_top
                    if best is None or overflow_area < best_overflow:
                        best = (ox, oy, ha)
                        best_overflow = overflow_area
                if best is not None:
                    ox, oy, ha = best
                    self._annot.set_position((ox, oy))
                    self._annot.set_ha(ha)
            if self._dot is not None:
                self._dot.set_data([self._xs[idx]], [self._ys[idx]])
            self.canvas.draw_idle()


class RebalanceApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rebalance Simulator")
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.resize(980, 620)

        self._drag_pos = None

        self.title_bar = QtWidgets.QWidget()
        self.title_bar.setFixedHeight(36)
        self.title_bar.setStyleSheet("background-color: #1f2a35;")
        title_layout = QtWidgets.QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(12, 0, 8, 0)
        title = QtWidgets.QLabel("Rebalance Simulator")
        title.setStyleSheet("color: #f2f2f2; font-weight: 600;")
        btn_close = QtWidgets.QPushButton("X")
        btn_close.setFixedSize(28, 24)
        btn_close.setStyleSheet(
            "QPushButton { color: #f2f2f2; background: #c0392b; border: none; border-radius: 4px; }"
            "QPushButton:hover { background: #e74c3c; }"
        )
        btn_close.clicked.connect(self.close)
        title_layout.addWidget(title)
        title_layout.addStretch()
        title_layout.addWidget(btn_close)

        form = QtWidgets.QGroupBox("Input")
        form_layout = QtWidgets.QGridLayout(form)

        self.input_principal = QtWidgets.QLineEdit("5000")
        self.input_years = QtWidgets.QSpinBox()
        self.input_years.setRange(1, 100)
        self.input_years.setValue(10)
        self.input_rebalance = QtWidgets.QSpinBox()
        self.input_rebalance.setRange(1, 120)
        self.input_rebalance.setValue(12)

        form_layout.addWidget(QtWidgets.QLabel("Initial Principal"), 0, 0)
        form_layout.addWidget(self.input_principal, 0, 1)
        form_layout.addWidget(QtWidgets.QLabel("Years"), 1, 0)
        form_layout.addWidget(self.input_years, 1, 1)
        form_layout.addWidget(QtWidgets.QLabel("Rebalance (months)"), 2, 0)
        form_layout.addWidget(self.input_rebalance, 2, 1)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Annual Return %", "Target %"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        btn_add = QtWidgets.QPushButton("Add Method")
        btn_remove = QtWidgets.QPushButton("Remove Selected")
        btn_calc = QtWidgets.QPushButton("Calculate")
        btn_add.clicked.connect(self.add_method)
        btn_remove.clicked.connect(self.remove_selected)
        btn_calc.clicked.connect(self.calculate)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: #c0392b;")

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(form)
        left_layout.addWidget(self.table)
        left_layout.addWidget(btn_add)
        left_layout.addWidget(btn_remove)
        left_layout.addWidget(btn_calc)
        left_layout.addWidget(self.status_label)
        left_layout.addStretch()

        self.chart = ChartWidget()

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.title_bar)

        body = QtWidgets.QWidget()
        body_layout = QtWidgets.QHBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.addLayout(left_layout, 2)
        body_layout.addWidget(self.chart, 3)
        main_layout.addWidget(body)

        self.add_default_rows()
        self.calculate()

    def add_default_rows(self):
        self.table.setRowCount(0)
        defaults = [
            ("Stock", "7", "60"),
            ("Bond", "3", "40"),
        ]
        for name, ret, weight in defaults:
            self.add_row(name, ret, weight)

    def add_row(self, name="", ret="", weight=""):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
        self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(ret))
        self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(weight))

    def add_method(self):
        self.add_row("New", "5", "0")

    def remove_selected(self):
        selected = self.table.selectionModel().selectedRows()
        for index in sorted(selected, key=lambda x: x.row(), reverse=True):
            self.table.removeRow(index.row())

    def parse_methods(self):
        methods = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            ret_item = self.table.item(row, 1)
            weight_item = self.table.item(row, 2)
            if not name_item or not ret_item or not weight_item:
                continue
            name = name_item.text().strip() or f"Method {row + 1}"
            try:
                annual_return = float(ret_item.text())
                target_weight = float(weight_item.text())
            except ValueError:
                return None, "Please enter numeric values for returns and weights."
            methods.append(InvestmentMethod(name, annual_return, target_weight))
        if not methods:
            return None, "Please add at least one investment method."
        return methods, ""

    def calculate(self):
        try:
            principal = float(self.input_principal.text())
        except ValueError:
            self.status_label.setText("Initial principal must be numeric.")
            return
        years = int(self.input_years.value())
        rebalance_months = int(self.input_rebalance.value())

        methods, msg = self.parse_methods()
        if methods is None:
            self.status_label.setText(msg)
            return

        months, values = simulate_growth(principal, years, rebalance_months, methods)
        if months is None:
            self.status_label.setText("Target weights must sum to 100%.")
            return

        self.status_label.setText("")
        years_axis = [m / 12.0 for m in months]
        self.chart.plot(years_axis, values)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(
        "QWidget { font-family: 'Segoe UI'; font-size: 12px; color: #f2f2f2; }"
        "QGroupBox { font-weight: 600; }"
        "QLineEdit, QSpinBox, QDoubleSpinBox { background: #2b2b2b; color: #f2f2f2; border: 1px solid #4a4a4a; padding: 4px; }"
        "QTableWidget { background: #2b2b2b; color: #f2f2f2; gridline-color: #4a4a4a; }"
        "QHeaderView::section { background: #3a3a3a; color: #f2f2f2; padding: 6px; border: 1px solid #4a4a4a; }"
        "QTableWidget::item:selected { background: #4a6fa5; color: #ffffff; }"
        "QPushButton { background: #5a5a5a; color: #f2f2f2; border-radius: 6px; padding: 6px; }"
        "QPushButton:hover { background: #6a6a6a; }"
    )
    window = RebalanceApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
