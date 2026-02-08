# Rebalance Simulator (PySide6)

A draggable PySide6/Qt GUI that simulates portfolio growth with periodic rebalancing and visualizes total asset value over time.

![Screenshot](./screenshot.png)

## Features
- Multiple investment methods with individual annual returns and target weights
- Rebalance by month interval
- Time horizon by years
- Interactive chart with hover tooltip and point marker
- Draggable frameless window

## Requirements
- Python 3.9+
- PySide6
- matplotlib

## Install
Use the same Python you will run the app with.

```bash
python -m pip install PySide6 matplotlib
```

## Run
```bash
python main.py
```
Run the command from the project root.

## Usage
1. Enter `Initial Principal` (default: 5000).
2. Set `Years` and `Rebalance (months)`.
3. Add or remove investment methods.
4. Ensure `Target %` totals 100.
5. Click `Calculate` to update the chart.
6. Hover over the chart to see exact values.

## Notes
- Annual returns are fixed and compounded monthly.
- Rebalancing sets holdings back to target weights on the specified interval.

## Files
- `<your-path>/rebalance/main.py`
- `<your-path>/rebalance/README.md`
