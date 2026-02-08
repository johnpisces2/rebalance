# Rebalance Simulator (PySide6)

A draggable PySide6/Qt GUI that simulates portfolio growth with periodic rebalancing and visualizes total asset value over time.

![Screenshot](/Users/ppppp/Desktop/python/rebalance/截圖 2026-02-08 晚上9.55.16.png)

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
/opt/homebrew/bin/python3 -m pip install PySide6 matplotlib
```

## Run
```bash
/opt/homebrew/bin/python3 /Users/ppppp/Desktop/python/rebalance/main.py
```

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
- `/Users/ppppp/Desktop/python/rebalance/main.py`
- `/Users/ppppp/Desktop/python/rebalance/README.md`
