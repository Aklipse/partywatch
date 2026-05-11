import csv
import io
import itertools
import requests
from collections import defaultdict

URL = "https://api.horizonxi.com/api/v1/chars/lfp"

PARTY_TEMPLATE = ["healer", "support", "dd(voke)", "puller", "dd", "dd"]

ROLES = {
    "healer": {"WHM", "RDM", "SMN", "DRG"},
    "support": {"BRD", "RDM", "SMN"},
    "puller": {"BRD", "THF"},
    "dd(voke)": {"WAR", "NIN", "PLD"},
    "dd": {"WAR", "MNK", "DRK", "RNG", "SAM", "DRG", "BST"},
}


def fetch_seekers():
    response = requests.get(URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()

    try:
        data = response.json()
        if isinstance(data, dict):
            data = data.get("data", data.get("chars", data.get("results", [])))
        return [p for row in data if (p := normalize_player(row))]
    except Exception:
        reader = csv.DictReader(io.StringIO(response.text.strip()))
        return [p for row in reader if (p := normalize_player(row))]


def normalize_player(row):
    name = row.get("name") or row.get("charname") or row.get("character") or row.get("player")
    main_job = row.get("mjob")
    main_level = row.get("mlvl")
    sub_job = row.get("sjob")

    if not name or not main_job or not main_level:
        return None

    main_job = str(main_job).upper().strip()
    sub_job = str(sub_job).upper().strip() if sub_job else None

    try:
        main_level = int(main_level)
    except ValueError:
        return None

    job_display = main_job
    if sub_job and sub_job not in {"NONE", "NULL", ""}:
        job_display = f"{main_job}/{sub_job}"

    return {
        "name": str(name).strip(),
        "main": main_job,
        "sub": sub_job,
        "level": main_level,
        "job": job_display,
        "raw": row,
    }


def parse_current_job(current_job):
    parts = current_job.upper().strip().split("/")
    main = parts[0].strip()
    sub = parts[1].strip() if len(parts) > 1 else None
    return main, sub


def job_fits_role(main, role, party_sync=None):
    main = main.upper().strip()

    if role == "healer":
        if main in {"WHM", "RDM", "SMN"}:
            return True
        if main == "DRG" and party_sync is not None and party_sync >= 60:
            return True
        return False

    if role == "support":
        return main in {"BRD", "RDM", "SMN"}

    if role == "puller":
        return main in {"BRD", "THF"}

    if role == "dd(voke)":
        return main in {"WAR", "NIN", "PLD"}

    if role == "dd":
        return main in ROLES["dd"]

    return False


def seeker_fits_role(seeker, role, party_sync=None):
    return job_fits_role(seeker["main"], role, party_sync)


def current_job_fits_role(current_job, role, party_sync=None):
    main, _ = parse_current_job(current_job)
    return job_fits_role(main, role, party_sync)


def possible_your_roles(current_job, your_level):
    roles = []

    for role in PARTY_TEMPLATE:
        if current_job_fits_role(current_job, role, your_level):
            roles.append(role)

    return list(dict.fromkeys(roles))


def validate_current_job(current_job, your_level):
    return len(possible_your_roles(current_job, your_level)) > 0


def needed_roles_for_your_role(your_role, current_job=None):
    needed = PARTY_TEMPLATE.copy()
    needed.remove(your_role)

    if current_job:
        main, _ = parse_current_job(current_job)

        if main == "BRD":
            if your_role == "support" and "puller" in needed:
                needed.remove("puller")
                needed.append("dd")
            elif your_role == "puller" and "support" in needed:
                needed.remove("support")
                needed.append("dd")

    return needed


def role_allowed_by_filter(role, seeker, role_filters):
    if not role_filters:
        return True

    allowed = role_filters.get(role)

    if allowed is None:
        return True

    return seeker["main"] in allowed


def get_party_members(current_job, your_level, your_role, assignments):
    current_main, current_sub = parse_current_job(current_job)

    display_role_name = your_role
    if current_main == "BRD" and your_role in {"support", "puller"}:
        display_role_name = "support(puller)"

    members = [{
        "name": "You",
        "main": current_main,
        "sub": current_sub,
        "level": your_level,
        "job": current_job,
        "role": display_role_name,
        "is_you": True,
    }]

    for role, seeker in assignments:
        member = seeker.copy()
        member["role"] = role
        member["is_you"] = False
        members.append(member)

    return members


def party_has_job(members, job):
    return any(m["main"] == job for m in members)


def count_jobs(members, jobs):
    return sum(1 for m in members if m["main"] in jobs)


def has_brd_puller(members):
    return any(
        m["main"] == "BRD"
        and m["role"] in {"puller", "support(puller)"}
        for m in members
    )


def has_thf_puller(members):
    return any(m["role"] == "puller" and m["main"] == "THF" for m in members)


def has_drg_healer(members):
    return any(m["role"] == "healer" and m["main"] == "DRG" for m in members)


def has_rdm_support(members):
    return any(m["role"] == "support" and m["main"] == "RDM" for m in members)


def has_nin_rdm_tank(members):
    return any(
        m["role"] == "dd(voke)"
        and m["main"] == "NIN"
        and m.get("sub") == "RDM"
        for m in members
    )


def dd_members(members):
    return [m for m in members if m["role"] in {"dd", "dd(voke)", "puller"}]


def display_your_role(your_role, current_job):
    main, _ = parse_current_job(current_job)

    if main == "BRD" and your_role in {"support", "puller"}:
        return "YOU(SUPPORT-PULLER)"

    if your_role == "healer":
        return "YOU(HEALER)"
    if your_role == "support":
        return "YOU(SUPPORT)"
    if your_role == "dd(voke)":
        return "YOU(TANK/DD)"
    if your_role == "puller":
        if main == "THF":
            return "YOU(DD-PULLER)"
        return "YOU(PULLER)"
    if your_role == "dd":
        return "YOU(DD)"

    return "YOU"


def display_role(role, seeker=None):
    if role == "puller" and seeker:
        if seeker["main"] == "BRD":
            return "SUPPORT(PULLER)"
        if seeker["main"] == "THF":
            return "DD(PULLER)"
    if role == "dd(voke)":
        return "TANK/DD"
    return role.upper()


def dd_priority_value(job, sync_level):
    if sync_level > 62:
        values = {
            "RNG": 120,
            "DRG": 105,
            "MNK": 95,
            "WAR": 85,
            "SAM": 75,
            "DRK": 65,
            "BST": 45,
        }
    else:
        values = {
            "WAR": 120,
            "MNK": 105,
            "DRG": 95,
            "SAM": 85,
            "BST": 70,
            "DRK": 60,
            "RNG": 40,
        }

    return values.get(job, 0)


SC_PROPERTIES_BY_JOB = {
    "WAR": {"light": {"Fragmentation"}, "darkness": {"Gravitation"}},
    "MNK": {"light": {"Fusion", "Fragmentation"}, "darkness": set()},
    "DRK": {"light": {"Fragmentation"}, "darkness": {"Distortion", "Gravitation"}},
    "RNG": {"light": {"Fragmentation"}, "darkness": set()},
    "SAM": {"light": {"Fusion", "Fragmentation"}, "darkness": {"Gravitation", "Distortion"}},
    "DRG": {"light": {"Fusion"}, "darkness": set()},
    "NIN": {"light": {"Fragmentation"}, "darkness": set()},
    "PLD": {"light": {"Fragmentation"}, "darkness": set()},
    "BST": {"light": set(), "darkness": {"Distortion"}},
    "THF": {"light": {"Fragmentation"}, "darkness": {"Distortion"}},
}

LIGHT_PAIRINGS = {frozenset(("Fusion", "Fragmentation"))}
DARKNESS_PAIRINGS = {frozenset(("Gravitation", "Distortion"))}


def member_sc_properties(member, sync_level):
    if sync_level < 60:
        return {"light": set(), "darkness": set()}

    props = SC_PROPERTIES_BY_JOB.get(member["main"], {"light": set(), "darkness": set()})
    return {
        "light": set(props["light"]),
        "darkness": set(props["darkness"]),
    }


def can_make_level3_chain(members, sync_level, chain_type):
    dds = dd_members(members)

    for a, b in itertools.combinations(dds, 2):
        a_props = member_sc_properties(a, sync_level)[chain_type]
        b_props = member_sc_properties(b, sync_level)[chain_type]

        for pa in a_props:
            for pb in b_props:
                pair = frozenset((pa, pb))

                if chain_type == "light" and pair in LIGHT_PAIRINGS:
                    return True, a, b

                if chain_type == "darkness" and pair in DARKNESS_PAIRINGS:
                    return True, a, b

    return False, None, None


def skillchain_score(members, sync_level):
    score = 0
    reasons = []

    light, light_a, light_b = can_make_level3_chain(members, sync_level, "light")
    dark, dark_a, dark_b = can_make_level3_chain(members, sync_level, "darkness")

    if light:
        score += 120
        reasons.append(f"+120 Light skillchain potential: {light_a['main']} + {light_b['main']}")

    if dark:
        score += 120
        reasons.append(f"+120 Darkness skillchain potential: {dark_a['main']} + {dark_b['main']}")

    if light and dark:
        score += 100
        reasons.append("+100 Party can potentially make both Light and Darkness")

    if sync_level >= 65 and (light or dark):
        score += 50
        reasons.append("+50 Lv65+ skillchain window bonus")

    return score, reasons


def role_quality_score(members, sync_level):
    score = 0
    reasons = []

    healer = next((m for m in members if m["role"] == "healer"), None)
    support = next((m for m in members if m["role"] in {"support", "support(puller)"}), None)
    puller = next((m for m in members if m["role"] in {"puller", "support(puller)"}), None)
    tank = next((m for m in members if m["role"] == "dd(voke)"), None)

    if healer:
        if healer["main"] == "WHM":
            score += 90
            reasons.append("+90 WHM main healer")
        elif healer["main"] == "RDM":
            value = 110 if sync_level >= 60 else 85
            score += value
            reasons.append(f"+{value} RDM healer")
        elif healer["main"] == "SMN":
            score += 60
            reasons.append("+60 SMN healer")
        elif healer["main"] == "DRG":
            value = 80 if sync_level >= 60 else 40
            score += value
            reasons.append(f"+{value} DRG healer base")

    if support:
        if support["main"] == "BRD":
            score += 160
            reasons.append("+160 BRD support")
        elif support["main"] == "RDM":
            value = 140 if sync_level >= 60 else 100
            score += value
            reasons.append(f"+{value} RDM support")
        elif support["main"] == "SMN":
            score += 65
            reasons.append("+65 SMN support")

    if puller:
        if puller["main"] == "BRD":
            score += 180
            reasons.append("+180 BRD puller")
        elif puller["main"] == "THF":
            score += 55
            reasons.append("+55 THF DD(Puller)")

    if tank:
        if tank["main"] == "NIN":
            score += 140
            reasons.append("+140 NIN tank/DD")
            if tank.get("sub") == "RDM":
                score += 220
                reasons.append("+220 NIN/RDM tank bonus")
        elif tank["main"] == "WAR":
            score += 95
            reasons.append("+95 WAR tank/DD")
        elif tank["main"] == "PLD":
            score += 85
            reasons.append("+85 PLD tank")

    for m in members:
        if m["role"] == "dd":
            value = dd_priority_value(m["main"], sync_level)
            score += value
            reasons.append(f"+{value} {m['main']} DD priority value")

    return score, reasons


def synergy_score(members, sync_level):
    score = 0
    reasons = []

    brd = party_has_job(members, "BRD")
    rdm = party_has_job(members, "RDM")
    smn = party_has_job(members, "SMN")
    drg_healer = has_drg_healer(members)
    rdm_support = has_rdm_support(members)
    brd_puller = has_brd_puller(members)
    nin_rdm = has_nin_rdm_tank(members)

    if brd:
        score += 90
        reasons.append("+90 BRD party tempo")

    if rdm:
        value = 75 if sync_level >= 60 else 45
        score += value
        reasons.append(f"+{value} RDM sustain/enfeeble value")

    if brd and rdm:
        score += 120
        reasons.append("+120 BRD + RDM low-downtime core")

    if brd_puller:
        score += 100
        reasons.append("+100 BRD puller role compression")

    if smn and brd:
        score += 30
        reasons.append("+30 SMN benefits from BRD support")

    if nin_rdm and brd:
        score += 80
        reasons.append("+80 NIN/RDM tank with BRD support")

    if nin_rdm and rdm:
        score += 80
        reasons.append("+80 NIN/RDM tank with RDM support")

    if drg_healer and sync_level >= 60 and rdm_support:
        score += 300
        reasons.append("+300 DRG healer 60+ with RDM support")

    if drg_healer and sync_level >= 60 and brd_puller:
        score += 150
        reasons.append("+150 DRG healer with BRD puller")

    if drg_healer and sync_level >= 60 and rdm_support and brd_puller:
        score += 500
        reasons.append("+500 elite DRG healer + RDM support + BRD puller core")

    sc_score, sc_reasons = skillchain_score(members, sync_level)
    score += sc_score
    reasons.extend(sc_reasons)

    return score, reasons


def penalty_score(members, sync_level):
    score = 0
    reasons = []

    drg_healer = has_drg_healer(members)
    rdm_support = has_rdm_support(members)
    voke_jobs = count_jobs(members, {"WAR", "NIN", "PLD"})

    if drg_healer and not rdm_support:
        score -= 999
        reasons.append("-999 DRG healer without RDM support")

    if drg_healer and sync_level < 60:
        score -= 999
        reasons.append("-999 DRG healer below 60")

    if voke_jobs > 2:
        penalty = (voke_jobs - 2) * 45
        score -= penalty
        reasons.append(f"-{penalty} too many voke/tank jobs")

    support_count = count_jobs(members, {"BRD", "RDM", "SMN"})
    if support_count >= 4:
        score -= 80
        reasons.append("-80 too much support, likely low kill speed")

    dd_count = len(dd_members(members))
    if dd_count < 3:
        score -= 100
        reasons.append("-100 low damage count")

    return score, reasons


def determine_archetype(members, sync_level):
    if has_drg_healer(members) and has_rdm_support(members) and has_brd_puller(members):
        return "DRG Heal Burn"

    if has_nin_rdm_tank(members) and party_has_job(members, "BRD") and party_has_job(members, "RDM"):
        return "NIN/RDM Low Downtime Core"

    light, _, _ = can_make_level3_chain(members, sync_level, "light")
    dark, _, _ = can_make_level3_chain(members, sync_level, "darkness")

    if light and dark:
        return "Light/Darkness Skillchain Party"

    if light:
        return "Light Skillchain Party"

    if dark:
        return "Darkness Skillchain Party"

    if party_has_job(members, "BRD") and party_has_job(members, "RDM"):
        return "Low Downtime Core"

    if has_brd_puller(members):
        return "BRD Pull Tempo"

    if has_nin_rdm_tank(members):
        return "NIN/RDM Tank Core"

    return "Standard EXP"


def score_party(current_job, your_level, your_role, assignments):
    members = get_party_members(current_job, your_level, your_role, assignments)
    sync_level = min(m["level"] for m in members)

    total = 0
    reasons = []

    role_score, role_reasons = role_quality_score(members, sync_level)
    synergy, synergy_reasons = synergy_score(members, sync_level)
    penalties, penalty_reasons = penalty_score(members, sync_level)

    total += role_score
    total += synergy
    total += penalties

    reasons.extend(role_reasons)
    reasons.extend(synergy_reasons)
    reasons.extend(penalty_reasons)

    archetype = determine_archetype(members, sync_level)

    return total, archetype, reasons


def is_valid_final_party(current_job, your_level, your_role, assignments, minimum_party_level, role_filters=None):
    members = get_party_members(current_job, your_level, your_role, assignments)
    sync_level = min(m["level"] for m in members)
    max_level = max(m["level"] for m in members)

    if len(members) != 6:
        return False

    if sync_level < minimum_party_level:
        return False

    if max_level > sync_level + 10:
        return False

    if sync_level < 75:
        for m in members:
            if m["level"] == 75:
                return False

    if not current_job_fits_role(current_job, your_role, sync_level):
        return False

    for role, seeker in assignments:
        if not seeker_fits_role(seeker, role, sync_level):
            return False

        if not role_allowed_by_filter(role, seeker, role_filters):
            return False

    if has_drg_healer(members):
        if sync_level < 60:
            return False
        if not has_rdm_support(members):
            return False

    return True


def build_party_options(seekers, current_job, your_level, minimum_party_level, role_filters=None):
    all_options = []

    for your_role in possible_your_roles(current_job, your_level):
        roles_needed = needed_roles_for_your_role(your_role, current_job)

        def backtrack(index, used_names, assignments):
            if index >= len(roles_needed):
                if len(assignments) != 5:
                    return

                if not is_valid_final_party(
                    current_job,
                    your_level,
                    your_role,
                    assignments,
                    minimum_party_level,
                    role_filters,
                ):
                    return

                score, archetype, reasons = score_party(
                    current_job,
                    your_level,
                    your_role,
                    assignments,
                )

                all_options.append({
                    "score": score,
                    "your_role": your_role,
                    "party": assignments.copy(),
                    "archetype": archetype,
                    "reasons": reasons,
                })
                return

            role = roles_needed[index]

            for seeker in seekers:
                key = seeker["name"].lower()

                if key in used_names:
                    continue

                test_levels = [your_level] + [s["level"] for _, s in assignments] + [seeker["level"]]
                test_sync = min(test_levels)
                test_max = max(test_levels)

                if test_sync < minimum_party_level:
                    continue

                if test_max > test_sync + 10:
                    continue

                if test_sync < 75 and seeker["level"] == 75:
                    continue

                if not seeker_fits_role(seeker, role, test_sync):
                    continue

                if not role_allowed_by_filter(role, seeker, role_filters):
                    continue

                used_names.add(key)
                assignments.append((role, seeker))

                backtrack(index + 1, used_names, assignments)

                assignments.pop()
                used_names.remove(key)

        backtrack(0, set(), [])

    all_options.sort(key=lambda option: option["score"], reverse=True)

    clean = []
    seen = set()
    per_sync_count = defaultdict(int)

    for option in all_options:
        your_role = option["your_role"]
        party = option["party"]
        level_sync = min([your_level] + [s["level"] for _, s in party])

        party_key = (
            your_role,
            tuple(sorted(
                (
                    role,
                    seeker["name"].lower(),
                    seeker["main"],
                    seeker["sub"],
                    seeker["level"],
                )
                for role, seeker in party
            )),
        )

        if party_key in seen:
            continue

        if per_sync_count[level_sync] >= 2:
            continue

        seen.add(party_key)
        per_sync_count[level_sync] += 1
        clean.append(option)

    return clean