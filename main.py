import sys
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from PySide6 import QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.offsetbox import AnnotationBbox, TextArea, VPacker


@dataclass
class InvestmentMethod:
    name: str
    annual_return: float  # percent
    target_weight: float  # percent


def simulate_growth(
    principal: float,
    years: int,
    rebalance_months: int,
    contribution_per_rebalance: float,
    methods: List[InvestmentMethod],
):
    if years <= 0:
        return [0], [principal], [principal]

    months = years * 12
    # Return empty values to signal invalid input.
    weight_sum = sum(m.target_weight for m in methods)
    if weight_sum <= 0:
        return None, None, None
    if abs(weight_sum - 100.0) > 0.01:
        return None, None, None
    if any(m.annual_return < -100.0 for m in methods):
        return None, None, None

    # Initialize holdings based on target weights
    holdings = [principal * (m.target_weight / 100.0) for m in methods]
    monthly_rates = [(1 + m.annual_return / 100.0) ** (1 / 12) - 1 for m in methods]

    timeline = [0]
    total_values = [principal]
    total_contributions = [principal]
    cumulative_contribution = principal

    for month in range(1, months + 1):
        # Grow each holding for the month
        for i in range(len(holdings)):
            holdings[i] *= (1 + monthly_rates[i])

        if rebalance_months > 0 and (month % rebalance_months == 0):
            added = max(0.0, contribution_per_rebalance)
            cumulative_contribution += added
            total = sum(holdings) + added
            for i, m in enumerate(methods):
                holdings[i] = total * (m.target_weight / 100.0)

        timeline.append(month)
        total_values.append(sum(holdings))
        total_contributions.append(cumulative_contribution)

    return timeline, total_values, total_contributions


class ChartWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self._xs = []
        self._ys = []
        self._ys_contrib = []
        self._ax = None
        self._info_box = None
        self._info_text_main = None
        self._info_text_total = None
        self._dot = None
        self._dot_contrib = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.canvas.mpl_connect("motion_notify_event", self.on_move)

    def plot(self, months, values, contributions):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(months, values, color="#1f77b4", linewidth=2)
        ax.plot(months, contributions, color="#2ecc71", linewidth=2, linestyle="--")
        ax.set_xlabel("Year")
        ax.set_ylabel("Total Asset")
        ax.grid(True, linestyle="--", alpha=0.4)
        self._dot = ax.plot([], [], "o", color="#1f77b4", markersize=5, zorder=5)[0]
        self._dot_contrib = ax.plot(
            [], [], "o", color="#2ecc71", markersize=5, zorder=5
        )[0]
        self._info_text_main = TextArea(
            "",
            textprops=dict(color="#f2f2f2"),
        )
        self._info_text_total = TextArea(
            "",
            textprops=dict(color="#e74c3c"),
        )
        packed = VPacker(
            children=[self._info_text_main, self._info_text_total],
            align="left",
            pad=0,
            sep=2,
        )
        self._info_box = AnnotationBbox(
            packed,
            (0, 0),
            xybox=(16, 16),
            xycoords="data",
            boxcoords="offset points",
            frameon=True,
            bboxprops=dict(boxstyle="round", fc="#1f2a35", ec="#4a4a4a", alpha=1.0),
        )
        self._info_box.set_zorder(10)
        self._info_box.set_visible(False)
        ax.add_artist(self._info_box)
        self.figure.tight_layout()
        self.canvas.draw()
        self._ax = ax
        self._xs = months
        self._ys = values
        self._ys_contrib = contributions

    def on_move(self, event):
        if self._ax is None or event.inaxes != self._ax or event.xdata is None:
            if self._info_box is not None:
                self._info_box.set_visible(False)
            if self._dot is not None:
                self._dot.set_data([], [])
            if self._dot_contrib is not None:
                self._dot_contrib.set_data([], [])
            self.canvas.draw_idle()
            return
        # Find nearest point for display
        x = event.xdata
        idx = min(range(len(self._xs)), key=lambda i: abs(self._xs[i] - x))
        if self._info_box is not None:
            if self._info_text_main is not None:
                self._info_text_main.set_text(
                    f"Year: {self._xs[idx]:.2f}\n"
                    f"Contrib: {self._ys_contrib[idx]:,.2f}"
                )
            if self._info_text_total is not None:
                self._info_text_total.set_text(f"Total: {self._ys[idx]:,.2f}")
            self._info_box.xy = (self._xs[idx], self._ys[idx])
            self._info_box.set_visible(True)
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
                    self._info_box.xybox = (ox, oy)
                    bbox = self._info_box.get_window_extent(renderer=renderer)
                    overflow_left = max(0, ax_bbox.x0 - bbox.x0)
                    overflow_right = max(0, bbox.x1 - ax_bbox.x1)
                    overflow_bottom = max(0, ax_bbox.y0 - bbox.y0)
                    overflow_top = max(0, bbox.y1 - ax_bbox.y1)
                    overflow_area = overflow_left + overflow_right + overflow_bottom + overflow_top
                    if best is None or overflow_area < best_overflow:
                        best = (ox, oy, ha)
                        best_overflow = overflow_area
                if best is not None:
                    ox, oy, _ha = best
                    self._info_box.xybox = (ox, oy)
            if self._dot is not None:
                self._dot.set_data([self._xs[idx]], [self._ys[idx]])
            if self._dot_contrib is not None:
                self._dot_contrib.set_data(
                    [self._xs[idx]], [self._ys_contrib[idx]]
                )
            self.canvas.draw_idle()


class RebalanceApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rebalance Simulator")
        self.resize(980, 620)

        self.settings_path = Path(__file__).with_name("rebalance_settings.json")
        self._settings_load_had_error = False

        form = QtWidgets.QGroupBox("Input")
        form_layout = QtWidgets.QGridLayout(form)

        self.input_principal = QtWidgets.QLineEdit("5000")
        self.input_years = QtWidgets.QSpinBox()
        self.input_years.setRange(1, 100)
        self.input_years.setValue(10)
        self.input_rebalance = QtWidgets.QSpinBox()
        self.input_rebalance.setRange(1, 120)
        self.input_rebalance.setValue(12)
        self.input_contribution = QtWidgets.QLineEdit("0")

        form_layout.addWidget(QtWidgets.QLabel("Initial Principal"), 0, 0)
        form_layout.addWidget(self.input_principal, 0, 1)
        form_layout.addWidget(QtWidgets.QLabel("Years"), 1, 0)
        form_layout.addWidget(self.input_years, 1, 1)
        form_layout.addWidget(QtWidgets.QLabel("Rebalance (months)"), 2, 0)
        form_layout.addWidget(self.input_rebalance, 2, 1)
        form_layout.addWidget(QtWidgets.QLabel("Contribution per Rebalance"), 3, 0)
        form_layout.addWidget(self.input_contribution, 3, 1)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Annual Return %", "Target %"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        btn_add = QtWidgets.QPushButton("Add Method")
        btn_remove = QtWidgets.QPushButton("Remove Selected")
        btn_calc = QtWidgets.QPushButton("Calculate")
        btn_save = QtWidgets.QPushButton("Save Settings")
        btn_add.clicked.connect(self.add_method)
        btn_remove.clicked.connect(self.remove_selected)
        btn_calc.clicked.connect(self.calculate)
        btn_save.clicked.connect(self.save_settings)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: #c0392b;")

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(form)
        left_layout.addWidget(self.table)
        left_layout.addWidget(btn_add)
        left_layout.addWidget(btn_remove)
        left_layout.addWidget(btn_calc)
        left_layout.addWidget(btn_save)
        left_layout.addWidget(self.status_label)
        left_layout.addStretch()

        self.chart = ChartWidget()

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        body = QtWidgets.QWidget()
        body_layout = QtWidgets.QHBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.addLayout(left_layout, 2)
        body_layout.addWidget(self.chart, 3)
        main_layout.addWidget(body)

        if not self.load_settings():
            self.add_default_rows()
        self.calculate(clear_status_on_success=not self._settings_load_had_error)

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
            if annual_return < -100.0:
                return None, "Annual return cannot be less than -100%."
            methods.append(InvestmentMethod(name, annual_return, target_weight))
        if not methods:
            return None, "Please add at least one investment method."
        return methods, ""

    def set_status(self, message, is_error=True):
        if message:
            color = "#c0392b" if is_error else "#2ecc71"
        else:
            color = "#c0392b"
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.setText(message)

    def get_current_settings(self):
        methods = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            ret_item = self.table.item(row, 1)
            weight_item = self.table.item(row, 2)
            name = name_item.text().strip() if name_item else ""
            annual_return = ret_item.text().strip() if ret_item else ""
            target_weight = weight_item.text().strip() if weight_item else ""
            if name or annual_return or target_weight:
                methods.append(
                    {
                        "name": name,
                        "annual_return": annual_return,
                        "target_weight": target_weight,
                    }
                )

        return {
            "principal": self.input_principal.text().strip(),
            "years": int(self.input_years.value()),
            "rebalance_months": int(self.input_rebalance.value()),
            "contribution_per_rebalance": self.input_contribution.text().strip(),
            "methods": methods,
        }

    def save_settings(self):
        settings = self.get_current_settings()
        try:
            with self.settings_path.open("w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            self.set_status(f"Failed to save settings: {exc}", is_error=True)
            return
        self.set_status(f"Settings saved: {self.settings_path.name}", is_error=False)

    def load_settings(self):
        self._settings_load_had_error = False
        if not self.settings_path.exists():
            return False
        try:
            with self.settings_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                self._settings_load_had_error = True
                self.set_status("Failed to load settings: invalid settings format.", is_error=True)
                return False

            principal = data.get("principal")
            if principal is not None:
                self.input_principal.setText(str(principal))

            years = data.get("years")
            if isinstance(years, int):
                self.input_years.setValue(
                    max(self.input_years.minimum(), min(years, self.input_years.maximum()))
                )

            rebalance_months = data.get("rebalance_months")
            if isinstance(rebalance_months, int):
                self.input_rebalance.setValue(
                    max(
                        self.input_rebalance.minimum(),
                        min(rebalance_months, self.input_rebalance.maximum()),
                    )
                )

            contribution = data.get("contribution_per_rebalance")
            if contribution is not None:
                self.input_contribution.setText(str(contribution))

            self.table.setRowCount(0)
            methods = data.get("methods", [])
            if isinstance(methods, list):
                for item in methods:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name", "")).strip()
                    annual_return = str(item.get("annual_return", "")).strip()
                    target_weight = str(item.get("target_weight", "")).strip()
                    if name or annual_return or target_weight:
                        self.add_row(name, annual_return, target_weight)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            self._settings_load_had_error = True
            self.set_status(f"Failed to load settings: {exc}", is_error=True)
            return False

        return self.table.rowCount() > 0

    def calculate(self, clear_status_on_success=True):
        try:
            principal = float(self.input_principal.text())
        except ValueError:
            self.set_status("Initial principal must be numeric.", is_error=True)
            return
        try:
            contribution = float(self.input_contribution.text())
        except ValueError:
            self.set_status("Contribution per rebalance must be numeric.", is_error=True)
            return
        years = int(self.input_years.value())
        rebalance_months = int(self.input_rebalance.value())

        methods, msg = self.parse_methods()
        if methods is None:
            self.set_status(msg, is_error=True)
            return

        months, values, contributions = simulate_growth(
            principal, years, rebalance_months, contribution, methods
        )
        if months is None:
            self.set_status(
                "Target weights must sum to 100%, and annual return must be >= -100%.",
                is_error=True,
            )
            return

        if clear_status_on_success:
            self.set_status("", is_error=False)
        years_axis = [m / 12.0 for m in months]
        self.chart.plot(years_axis, values, contributions)

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
