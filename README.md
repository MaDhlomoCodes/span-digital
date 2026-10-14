# 1974/75 First Division League Standings CLI

A robust CLI utility built in Python to generate accurate historical standings for the 1974/75 Football League First Division.

## Features
- **Historical Domain Precision**: Enforces 2 points per win and Goal Average tie-breaking ($\text{GF} / \text{GA}$).
- **Flexible CSV Ingestion**: Handles non-standard column headers, whitespace, and column order variations cleanly using header normalization.
- **Matchweek Filtering**: Optional `--max-week N` parameter to view standings at any stage of the season.
- **Comprehensive Unit Testing**: Includes 38 unit tests covering edge cases like zero goals conceded, equal points/averages, and malformed CSV input.

## Project Structure

span-digital/
├── ai/                      # AI session artifacts
├── claude/                  # Claude session history export
├── scripts/                 # Execution wrapper scripts
│   └── standings.sh
├── src/                     # Core application source code
│   ├── __init__.py
│   ├── main.py
│   └── standings.py
├── tests/                   # Pytest test suite
│   └── test_standings.py
├── AI_REFLECTION.md         # Reflection on AI-assisted development
├── CLAUDE.md                # AI agent guidance & quick commands
├── output.csv               # Standings generated for Week 10
└── requirements.txt         # Dependencies (pytest)