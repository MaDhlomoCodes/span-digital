"""Tests for src.standings and src.main.

Run from the project root with:

    python -m pytest tests/test_standings.py

Using `python -m pytest` puts the project root on sys.path, so `src` imports resolve.
"""

from __future__ import annotations

import io
from typing import Iterable, Tuple

import pytest

from src.main import build_table, read_matches, write_table
from src.standings import LeagueTable, Team, league_table


def team_from_results(name: str, results: Iterable[Tuple[int, int]]) -> Team:
    """Build a Team by applying (scored, conceded) results in order."""
    team = Team(name)
    for scored, conceded in results:
        team.record_result(scored, conceded)
    return team


def goal_difference(team: Team) -> int:
    return team.goals_for - team.goals_against


# ---------------------------------------------------------------------------
# 1. Points allocation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "scored, conceded, expected_points",
    [
        (2, 0, 2),  # win
        (1, 0, 2),  # narrow win
        (1, 1, 1),  # draw
        (0, 0, 1),  # goalless draw
        (0, 1, 0),  # narrow loss
        (0, 3, 0),  # heavy loss
    ],
)
def test_single_result_awards_historical_points(scored, conceded, expected_points):
    team = team_from_results("Test FC", [(scored, conceded)])
    assert team.points == expected_points


def test_win_counts_as_two_points_not_three():
    team = team_from_results("Test FC", [(5, 0)])
    assert team.won == 1
    assert team.points == 2


def test_mixed_season_totals_points_correctly():
    # W (2) + D (1) + L (0) + W (2) = 5
    team = team_from_results(
        "Test FC",
        [(2, 1), (1, 1), (0, 2), (3, 0)],
    )
    assert (team.won, team.drawn, team.lost) == (2, 1, 1)
    assert team.points == 5


def test_points_via_league_table_match_recording():
    table = LeagueTable(["Home", "Away"])
    table.record_match("Home", "Away", 2, 0)  # Home wins
    assert table["Home"].points == 2
    assert table["Away"].points == 0

    table.record_match("Home", "Away", 1, 1)  # Draw
    assert table["Home"].points == 3
    assert table["Away"].points == 1


def test_record_match_rejects_team_playing_itself():
    table = LeagueTable(["Solo"])
    with pytest.raises(ValueError):
        table.record_match("Solo", "Solo", 1, 0)


def test_negative_goals_are_rejected():
    team = Team("Test FC")
    with pytest.raises(ValueError):
        team.record_result(-1, 0)
    with pytest.raises(ValueError):
        team.record_result(0, -1)


# ---------------------------------------------------------------------------
# 2. Goal average tie-breaker
# ---------------------------------------------------------------------------

def test_goal_average_ranks_ahead_of_higher_goal_difference():
    # Alpha: GF 10, GA 8 -> GD +2, GAv 1.250
    alpha = team_from_results("Alpha", [(6, 3), (4, 2), (0, 3)])
    # Beta:  GF 3, GA 2  -> GD +1, GAv 1.500
    beta = team_from_results("Beta", [(2, 0), (1, 0), (0, 2)])

    # Confirm the setup: equal points, Alpha has the better goal difference,
    # Beta has the better goal average.
    assert alpha.points == beta.points == 4
    assert goal_difference(alpha) > goal_difference(beta)
    assert beta.goal_average > alpha.goal_average

    # Goal average must decide the order, so Beta finishes above Alpha.
    assert [t.name for t in league_table([alpha, beta])] == ["Beta", "Alpha"]
    assert [t.name for t in league_table([beta, alpha])] == ["Beta", "Alpha"]


def test_goal_difference_is_not_used_when_goal_average_differs():
    # Same setup as above, confirming the sort does not fall back to GD.
    alpha = team_from_results("Alpha", [(6, 3), (4, 2), (0, 3)])
    beta = team_from_results("Beta", [(2, 0), (1, 0), (0, 2)])
    table = league_table([alpha, beta])
    assert table[0] is beta


def test_total_goals_for_breaks_ties_when_goal_average_is_equal():
    # Both teams have GAv 2.000 and 4 points.
    # Gamma: GF 4, GA 2
    gamma = team_from_results("Gamma", [(2, 1), (2, 0), (0, 1)])
    # Delta: GF 2, GA 1
    delta = team_from_results("Delta", [(1, 0), (1, 0), (0, 1)])

    assert gamma.goal_average == delta.goal_average == 2.0
    assert gamma.points == delta.points == 4

    assert [t.name for t in league_table([delta, gamma])] == ["Gamma", "Delta"]


def test_points_outrank_goal_average():
    # Winner has a poor goal average but more points.
    winner = team_from_results("Winner", [(1, 0), (1, 0), (0, 5)])  # 4 pts, GAv 0.4
    loser = team_from_results("Loser", [(9, 1), (0, 1)])            # 2 pts, GAv 9.0

    assert [t.name for t in league_table([loser, winner])] == ["Winner", "Loser"]


# ---------------------------------------------------------------------------
# 3. Edge cases: zero goals conceded
# ---------------------------------------------------------------------------

def test_goal_average_is_infinite_when_no_goals_conceded():
    team = team_from_results("Fortress", [(3, 0), (1, 0)])
    assert team.goal_average == float("inf")


def test_zero_zero_team_has_zero_goal_average_without_error():
    team = team_from_results("Stalemate", [(0, 0)])
    assert team.goal_average == 0.0
    assert team.points == 1


def test_unplayed_team_has_zero_goal_average_without_error():
    team = Team("Newcomer")
    assert team.goal_average == 0.0
    assert team.points == 0


def test_zero_conceded_team_ranks_above_finite_average_on_equal_points():
    # Both on 4 points. Clean sheets give infinite goal average.
    clean = team_from_results("Clean", [(1, 0), (1, 0)])
    leaky = team_from_results("Leaky", [(3, 1), (3, 1)])  # GAv 3.0

    assert clean.points == leaky.points == 4
    assert [t.name for t in league_table([leaky, clean])] == ["Clean", "Leaky"]


def test_two_infinite_goal_averages_fall_back_to_goals_for():
    # Both have conceded nothing, so both have infinite goal average.
    low_scoring = team_from_results("Low", [(1, 0), (1, 0)])    # GF 2
    high_scoring = team_from_results("High", [(3, 0), (1, 0)])  # GF 4

    assert low_scoring.goal_average == high_scoring.goal_average == float("inf")
    assert [t.name for t in league_table([low_scoring, high_scoring])] == [
        "High",
        "Low",
    ]


def test_sorting_does_not_raise_when_a_team_has_zero_goals_against():
    teams = [
        team_from_results("A", [(0, 0)]),
        team_from_results("B", [(2, 0)]),
        team_from_results("C", [(2, 2)]),
        team_from_results("D", []),
    ]
    # Should complete without ZeroDivisionError and place B first.
    table = league_table(teams)
    assert table[0].name == "B"


# ---------------------------------------------------------------------------
# 4. CSV parsing and header alias mapping (src.main.read_matches)
# ---------------------------------------------------------------------------

def parse(csv_text: str, max_week=None):
    return read_matches(io.StringIO(csv_text), max_week)


def test_standard_headers_are_parsed():
    csv_text = (
        "Week,Home Team,Away Team,Home Goals,Away Goals\n"
        "1,Arsenal,Liverpool,1,0\n"
    )
    assert parse(csv_text) == [
        {"home": "Arsenal", "away": "Liverpool", "home_goals": 1, "away_goals": 0}
    ]


@pytest.mark.parametrize(
    "header",
    [
        "HomeTeam,AwayTeam,FTHG,FTAG",
        "Home Team,Away Team,Home Goals,Away Goals",
        "home_team,away_team,home_goals,away_goals",
        "HOME TEAM,AWAY TEAM,HOME SCORE,AWAY SCORE",
        "home-club,away-club,hg,ag",
        "Home Club,Away Club,FTHG,FTAG",
    ],
)
def test_header_aliases_map_to_the_same_fields(header):
    csv_text = f"{header}\nArsenal,Liverpool,2,1\n"
    assert parse(csv_text) == [
        {"home": "Arsenal", "away": "Liverpool", "home_goals": 2, "away_goals": 1}
    ]


def test_column_order_does_not_matter():
    csv_text = "Away Goals,Home Goals,Away Team,Home Team\n0,3,Liverpool,Arsenal\n"
    assert parse(csv_text) == [
        {"home": "Arsenal", "away": "Liverpool", "home_goals": 3, "away_goals": 0}
    ]


def test_matchweek_alias_is_used_for_max_week_filter():
    csv_text = (
        "Matchweek,HomeTeam,AwayTeam,FTHG,FTAG\n"
        "1,A,B,1,0\n"
        "10,C,D,0,0\n"
        "11,E,F,2,2\n"
    )
    matches = parse(csv_text, max_week=10)
    assert [(m["home"], m["away"]) for m in matches] == [("A", "B"), ("C", "D")]


def test_max_week_is_ignored_when_no_week_column_exists():
    csv_text = "HomeTeam,AwayTeam,FTHG,FTAG\nA,B,1,0\nC,D,0,0\n"
    assert len(parse(csv_text, max_week=1)) == 2


def test_blank_rows_are_skipped():
    csv_text = (
        "HomeTeam,AwayTeam,FTHG,FTAG\n"
        "A,B,1,0\n"
        ",,,\n"
        "\n"
        "C,D,0,0\n"
    )
    assert len(parse(csv_text)) == 2


def test_whitespace_around_team_names_is_stripped():
    csv_text = "HomeTeam,AwayTeam,FTHG,FTAG\n  Arsenal ,  Liverpool ,1,0\n"
    match = parse(csv_text)[0]
    assert match["home"] == "Arsenal"
    assert match["away"] == "Liverpool"


def test_missing_required_column_raises_naming_the_column():
    csv_text = "HomeTeam,AwayTeam,FTHG\nA,B,1\n"
    with pytest.raises(ValueError, match="away_goals"):
        parse(csv_text)


def test_empty_file_raises():
    with pytest.raises(ValueError, match="no header"):
        parse("")


def test_non_integer_goals_raise_with_line_number():
    csv_text = "HomeTeam,AwayTeam,FTHG,FTAG\nA,B,1,0\nC,D,x,0\n"
    with pytest.raises(ValueError, match="line 3"):
        parse(csv_text)


def test_empty_team_name_raises():
    csv_text = "HomeTeam,AwayTeam,FTHG,FTAG\n,B,1,0\n"
    with pytest.raises(ValueError, match="empty"):
        parse(csv_text)


def test_end_to_end_csv_to_table_output():
    csv_text = (
        "Week,HomeTeam,AwayTeam,FTHG,FTAG\n"
        "1,Arsenal,Liverpool,1,0\n"
    )
    table = build_table(parse(csv_text))

    out = io.StringIO()
    write_table(table, out)

    assert out.getvalue().splitlines() == [
        "Pos,Team,Pld,W,D,L,GF,GA,GAv,Pts",
        "1,Arsenal,1,1,0,0,1,0,inf,2",
        "2,Liverpool,1,0,0,1,0,1,0.000,0",
    ]