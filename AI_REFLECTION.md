# AI Reflection & Multi-Agent Workflow

## Overview
This project utilized a collaborative multi-agent workflow to build a historically accurate Python CLI tool for the 1974/75 English First Division standings, strictly adhering to historical rules (2-point wins, Goal Average tie-breakers) and transparency guidelines.

## AI Tool Roles & Collaboration
1. **Amazon Q (`ai/`)**:
   - **Role**: Historical dataset research, fixture verification, and source cross-referencing.
   - **Outcome**: Compiled Week 1–10 match data by evaluating Wikipedia season pages and club-season fixture lists.
2. **Claude (`claude/`)**:
   - **Role**: Software engineering, architecture design, and test suite implementation.
   - **Outcome**: Implemented core dataclasses, historical point systems, Goal Average tie-breakers with `float("inf")` handling, CSV aliasing, and the 38-test `pytest` suite.

## Challenges, Failures & Maneuvers
- **Handling Staggered Midweek Fixtures**: 
  * *Failure/Challenge*: Naive calendar-date mapping for weeks 8–10 caused conflicts (e.g., 24 Sep and 28 Sep midweek games), because clubs played out-of-sequence rearranged matches and reached matchdays at different rates.
  * *Maneuver*: Rather than forcing a broken date-to-week mapping, we anchored the canonical round dates using matchday-numbered club sources (Stoke and Carlisle) and cross-validated rows against the season results matrix to ensure structural integrity.
- **Stubborn Wikipedia Table Layouts**:
  * *Failure/Challenge*: Several club pages (e.g., Burnley, Coventry, Ipswich, Newcastle) failed to parse through standard content APIs due to differing wikitable structures or missing standalone league tables.
  * *Maneuver*: Leveraged robust multi-format parsers (handling explicit home/away columns and relative venue tokens) and cross-checked every fixture against independent home/away partner pages and the season results matrix to guarantee zero data discrepancies.

## Reflection & Learnings
Balancing modern Python architecture with the messy, staggered realities of 1970s football data highlighted the importance of defensive parsing and rigorous test-driven verification. The multi-agent approach allowed for a clear separation between historical data curation and precise backend code implementation.
