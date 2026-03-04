# Rugby Video Review Tagger

A lightweight **Python GUI tool for rugby match video review** that
allows analysts and coaches to quickly tag events during video playback
and automatically generate visual match reports.

The tool is designed to be **fast to use during review sessions** and
produce **clear post-match statistics**.

------------------------------------------------------------------------

## Features

### Match Tagging GUI

Track key rugby events during video review with a simple click
interface.

The interface contains:

### Team Aggregates

Special rows for:

**Rucks** - Attacking players committed: 1 / 2 / 3+ - Defensive contest
on opposition rucks: 0 / 1 / 2 - Own ruck lost - Turnovers won

**Lineouts** - Own won - Own lost - Opponent won - Opponent lost

**Scrums** - Own won - Own lost - Opponent won - Opponent lost

**Penalties** - At ruck - High tackle - At scrum - Not releasing - Not
rolling away - Other

------------------------------------------------------------------------

### Player Statistics (23 Players)

Each player tracks:

**Carries** - Positive carry - Negative carry

**Passing** - Pass - Ground pass - Offload

**Tackling** - Tackle made - Tackle missed - Assisted tackle

**Handling** - Handling error - Dropped pass

------------------------------------------------------------------------

## Save / Resume Analysis

Match sessions can be saved as JSON files.

This allows you to:

-   Pause video review
-   Resume later
-   Share analysis with other staff

------------------------------------------------------------------------

## Report Generation

When the **Generate Report** button is pressed, the tool creates a
report folder containing:

    match_report/
    │
    ├── team_recap.png
    ├── stats.csv
    ├── summary.txt
    │
    └── players/
        ├── Player1.png
        ├── Player2.png
        ├── ...

------------------------------------------------------------------------

## Team Recap

The team report contains donut charts summarizing:

-   Total carries (positive / negative)
-   Tackles (made / missed)
-   Errors (handling / dropped passes)
-   Own scrums (won / lost)
-   Opponent scrums (won / lost)
-   Own lineouts (won / lost)
-   Opponent lineouts (won / lost)
-   Attacking rucks (players committed)
-   Defensive rucks (contest numbers)

------------------------------------------------------------------------

## Player Reports

Each player receives a **single bar chart** summarizing their individual
performance.

Example stats per player:

-   Carries +
-   Carries -
-   Pass
-   Ground pass
-   Offload
-   Tackles made
-   Tackles missed
-   Assisted tackles
-   Handling errors
-   Dropped passes

------------------------------------------------------------------------

## Installation

Requires **Python 3.9+**

Install dependencies:

``` bash
pip install matplotlib
```

The GUI uses only the Python standard library (`tkinter`).


## Future Improvements

Potential additions:

### Analysis Improvements

-   Possession statistics
-   Phase counts
-   Territory metrics
-   Time‑stamped tagging
-   Video integration

### GUI Improvements

-   Keyboard shortcuts for faster tagging
-   Selected-player quick tag panel
-   Live stat summaries during review

### Reporting Improvements

-   HTML report dashboard
-   Interactive charts
-   Comparison between matches
-   Season aggregation

------------------------------------------------------------------------

### License

MIT License
