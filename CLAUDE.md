cat << 'EOF' > CLAUDE.md
# Project Instructions for Claude

## Project Overview
Backend coding test for Span Digital: A Python CLI application that calculates English First Division league standings for week 10 of the 1974/75 season.

## Tech Stack
- Language: Python 3.10+
- Testing: Pytest

## Key Rules & Logic
- Points: 2 for a win, 1 for a draw, 0 for a loss.
- Tie-breaker: Goal Average (Goals For / Goals Conceded) followed by Goals For.

## Development Commands
- Run tests: `pytest`
- Run application: `python -m src.main input.csv`
EOF

