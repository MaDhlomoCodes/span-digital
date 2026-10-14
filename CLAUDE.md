# 1974/75 English First Division Standings Generator

## Overview
A production-ready Python CLI application that processes match results from CSV input and outputs the 1974/75 English First Division league standings based on historical rules.

## Key Technical Rules (1974/75 Season)
- **Points**: 2 points for a Win, 1 point for a Draw, 0 points for a Loss.
- **Primary Tie-Breaker**: Goal Average ($\text{GA} = \frac{\text{Goals For}}{\text{Goals Conceded}}$). Higher goal average ranks higher.
- **Secondary Tie-Breaker**: Total Goals For ($\text{GF}$).
- **Fallback Tie-Breaker**: Alphabetical team name order.
- **Clean Sheets**: Zero goals conceded ($\text{GA} = 0$) results in an infinite goal average (`inf`), properly sorted above finite averages.

## Developer Commands

### Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt