OVERWATCH_ROLE_TARGET = {
    "돌격": 1,
    "딜러": 2,
    "지원": 2,
}


def calc_elo_delta(avg_a: int, avg_b: int, winner_team: str):
    expected_a = 1 / (1 + 10 ** ((avg_b - avg_a) / 400))
    expected_b = 1 / (1 + 10 ** ((avg_a - avg_b) / 400))

    k = 24
    actual_a = 1 if winner_team == "A" else 0
    actual_b = 1 if winner_team == "B" else 0

    delta_a = round(k * (actual_a - expected_a))
    delta_b = round(k * (actual_b - expected_b))
    return delta_a, delta_b


def split_by_mmr(players: list[dict], team_size: int):
    sorted_players = sorted(players, key=lambda x: x["mmr"], reverse=True)

    team_a = []
    team_b = []
    score_a = 0
    score_b = 0

    for player in sorted_players:
        if len(team_a) >= team_size:
            team_b.append(player)
            score_b += player["mmr"]
            continue
        if len(team_b) >= team_size:
            team_a.append(player)
            score_a += player["mmr"]
            continue

        if score_a <= score_b:
            team_a.append(player)
            score_a += player["mmr"]
        else:
            team_b.append(player)
            score_b += player["mmr"]

    return team_a, team_b


def count_overwatch_roles(team: list[dict]):
    counts = {"돌격": 0, "딜러": 0, "지원": 0, "상관없음": 0}
    for player in team:
        pos = player["position"]
        if pos in counts:
            counts[pos] += 1
        else:
            counts["상관없음"] += 1
    return counts


def overwatch_role_need_score(team: list[dict], player: dict):
    counts = count_overwatch_roles(team)
    pos = player["position"]

    if pos == "상관없음":
        missing = 0
        for role, need in OVERWATCH_ROLE_TARGET.items():
            if counts[role] < need:
                missing += (need - counts[role])
        return missing * 2

    if pos not in OVERWATCH_ROLE_TARGET:
        return 0

    need = OVERWATCH_ROLE_TARGET[pos]
    current = counts[pos]

    if current < need:
        return 10 + (need - current) * 3

    return 1


def make_overwatch_balanced_teams(players: list[dict], team_size: int):
    sorted_players = sorted(players, key=lambda x: x["mmr"], reverse=True)

    team_a = []
    team_b = []

    def team_score(team):
        return sum(p["mmr"] for p in team)

    for player in sorted_players:
        if len(team_a) >= team_size:
            team_b.append(player)
            continue
        if len(team_b) >= team_size:
            team_a.append(player)
            continue

        need_a = overwatch_role_need_score(team_a, player)
        need_b = overwatch_role_need_score(team_b, player)

        if need_a > need_b:
            team_a.append(player)
            continue
        if need_b > need_a:
            team_b.append(player)
            continue

        if team_score(team_a) <= team_score(team_b):
            team_a.append(player)
        else:
            team_b.append(player)

    return team_a, team_b


def auto_balance_players(game_key: str, players: list[dict], team_size: int):
    if game_key == "overwatch" and team_size == 5:
        return make_overwatch_balanced_teams(players, team_size), "오버워치 역할 균형 + MMR 분배"

    return split_by_mmr(players, team_size), "기본 MMR 분배"