# Building Energy Analyzer

**Student name:** [Write your name here]

## Project description
A Python application that calculates and analyzes building energy consumption. It has two connected
modules, joined by a menu in `main.py`:

1. **Module 1 - Energy Consumption Calculator** (`module1_energy_calculator.py`)
   A `Room` class (name, building, area, lighting / AC / equipment power in kW, daily operating hours) and a
   `RoomManager` to add, list, search and update rooms. It calculates daily energy per room
   (`total kW x hours`), total consumption, and consumption per m2, and saves rooms to CSV.
   Inputs are validated: area > 0, power >= 0, hours between 0 and 24.

2. **Module 2 - Consumption and Cost Analysis** (`module2_analysis.py`)
   Uses pandas to read, clean (duplicates, missing values) and merge the daily readings with the room data;
   calculates consumption and cost per room, building and month from a price per kWh entered by the user;
   uses NumPy to compare estimated consumption before and after reducing AC power by a chosen percentage;
   creates four Matplotlib charts (line, bar, scatter, histogram) and exports reports (CSV) and charts (PNG).

## Sample data
- `data/rooms.csv` - 8 rooms in 2 buildings (Admin Block, Academic Block)
- `data/readings.csv` - daily readings for every room, 1 Aug - 30 Sep 2026 (about 61 days x 8 rooms).
  It contains 2 duplicate rows and 3 missing values on purpose, to demonstrate the cleaning step.

## Required libraries
Python 3.9+ and: `pandas`, `numpy`, `matplotlib`

```
pip install -r requirements.txt
```

## How to run
Run all commands from the project folder (the one that contains `main.py`).

```
python main.py          # interactive menu
python tests.py         # 3 valid + 3 invalid test cases -> test_results.csv
```

Suggested order in the menu: `2` list rooms -> `5` consumption -> `7` load/clean/merge ->
`8` cost reports (enter a price per kWh) -> `9` AC scenario (enter a percentage) ->
`10` charts -> `11` export reports.

## Project structure
```
main.py                       menu that connects both modules
module1_energy_calculator.py  Room class, RoomManager, validation, CSV save/load
module2_analysis.py           pandas cleaning/merging/grouping, NumPy scenario, charts, exports
tests.py                      valid / invalid test cases
test_results.csv              expected vs actual results of the tests
analysis_notebook.ipynb       short notebook explaining the analysis
data/                         rooms.csv, readings.csv
reports/                      exported CSV reports
charts/                       exported PNG charts
```

## Test results
See `test_results.csv` (6 of 6 pass): 3 valid cases (daily energy, per-m2 energy, AC-reduction scenario)
and 3 invalid cases (area = 0, negative AC power, 25 operating hours).
