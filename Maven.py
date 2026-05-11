import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

from partywatch import (
    fetch_seekers,
    build_party_options,
    seeker_fits_role,
    ROLES,
)

st.set_page_config(
    page_title="Maven's Party Optimizer",
    layout="wide",
)

JOB_ICONS = {
    "WAR": "🪓", "MNK": "🥊", "WHM": "✨", "BLM": "🔥",
    "RDM": "🌹", "THF": "🗡️", "PLD": "🛡️", "DRK": "💀",
    "BST": "🐺", "BRD": "🎵", "RNG": "🏹", "SAM": "⚔️",
    "NIN": "🥷", "DRG": "🐉", "SMN": "🔮",
}

ARCHETYPE_ICONS = {
    "DRG Heal Burn": "🐉",
    "NIN/RDM Low Downtime Core": "🥷",
    "Light/Darkness Skillchain Party": "🌗",
    "Light Skillchain Party": "☀️",
    "Darkness Skillchain Party": "🌑",
    "Low Downtime Core": "💧",
    "BRD Pull Tempo": "🎵",
    "NIN/RDM Tank Core": "🥷",
    "Standard EXP": "⚔️",
}

ROLE_ICONS = {
    "👑 Healer": "👑",
    "👑 Support": "👑",
    "👑 Puller": "👑",
    "👑 Tank / DD": "👑",
    "👑 DD": "👑",
    "👑 Support / Puller": "👑",
    "Healer": "✨",
    "Support": "🎵",
    "Support / Puller": "🎵🏹",
    "Puller": "🏹",
    "Tank / DD": "🛡️",
    "DD": "⚔️",
}

ROLE_BADGE_COLORS = {
    "👑 Healer": "green",
    "👑 Support": "blue",
    "👑 Puller": "orange",
    "👑 Tank / DD": "red",
    "👑 DD": "gray",
    "👑 Support / Puller": "violet",
    "Healer": "green",
    "Support": "blue",
    "Support / Puller": "violet",
    "Puller": "orange",
    "Tank / DD": "red",
    "DD": "gray",
}


def job_icon(job):
    return JOB_ICONS.get(job, "◆")


def archetype_icon(archetype):
    return ARCHETYPE_ICONS.get(archetype, "◆")


def role_label(role):
    return {
        "healer": "Healer",
        "support": "Support",
        "support(puller)": "Support / Puller",
        "puller": "Puller",
        "dd(voke)": "Tank / DD",
        "dd": "DD",
    }.get(role, role.upper())


def score_percent(score, max_score):
    if max_score <= 0:
        return 0
    return max(0, min(100, int((score / max_score) * 100)))


def option_sync_level(option, your_level):
    return min([your_level] + [s["level"] for _, s in option["party"]])


st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(circle at top left, rgba(80,120,180,0.20), transparent 35%),
        linear-gradient(135deg, #070b10 0%, #111827 50%, #090b10 100%);
}
section[data-testid="stSidebar"] {
    background: rgba(7, 10, 16, 0.96);
}
.maven-logo {
    line-height: .9;
    margin-bottom: 8px;
}
.maven-logo-top {
    font-size: 44px;
    font-weight: 900;
    color: #f7e7bd;
    letter-spacing: 1px;
}
.maven-logo-bottom {
    font-size: 30px;
    font-weight: 800;
    color: #7cc7ff;
    letter-spacing: 2px;
}
.subtitle {
    color: #d4c2a1;
    margin-bottom: 20px;
}
div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(247,231,189,0.14);
    padding: 12px;
    border-radius: 16px;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,0.04);
    border-radius: 16px;
}
/* PARTY SYNC FILTER */
div[data-testid="stSelectbox"]:has(div[data-baseweb="select"]) {
    background: rgba(120, 25, 25, 0.22);
    border: 1px solid rgba(255, 80, 80, 0.30);
    border-radius: 14px;
    padding: 8px;
}

/* YOUR JOB INPUT */
div[data-testid="stTextInput"] {
    background: rgba(25, 90, 45, 0.22);
    border: 1px solid rgba(80, 255, 140, 0.28);
    border-radius: 14px;
    padding: 8px;
}

/* Make labels pop more */
label[data-testid="stWidgetLabel"] p {
    font-size: 15px !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="maven-logo">
    <div class="maven-logo-top">Maven's</div>
    <div class="maven-logo-bottom">Party Optimizer</div>
</div>
<div class="subtitle">
HorizonXI live seeker optimizer · skillchain-aware scoring · role compression
</div>
""", unsafe_allow_html=True)

refresh_minutes = st.sidebar.slider(
    "Refresh every X minutes",
    1,
    15,
    3,
)

st_autorefresh(
    interval=refresh_minutes * 60 * 1000,
    key="partywatch_refresh",
)

party_sync_filter_placeholder = st.sidebar.empty()

your_level = st.sidebar.number_input(
    "Your level",
    1,
    75,
    68,
)

default_min_level = max(1, your_level - 10)

min_level = st.sidebar.number_input(
    "Minimum party level accepted",
    1,
    75,
    default_min_level,
)

current_job = st.sidebar.text_input(
    "Your job",
    value="BRD",
).upper().strip()

max_level = min(75, your_level + 10)

st.sidebar.write(f"Search range: Lv{min_level}-{max_level}")

st.sidebar.divider()
st.sidebar.subheader("Job Filters")

selected_jobs_by_role = {}

for role, jobs in ROLES.items():
    filter_jobs = set(jobs)

    if role == "healer" and max_level < 60:
        filter_jobs.discard("DRG")

    with st.sidebar.expander(role.upper(), expanded=False):
        selected_jobs_by_role[role] = set()

        cols = st.columns(2)

        for idx, job in enumerate(sorted(filter_jobs)):
            with cols[idx % 2]:
                checked = st.checkbox(
                    f"{job_icon(job)} {job}",
                    value=True,
                    key=f"filter_{role}_{job}",
                )

            if checked:
                selected_jobs_by_role[role].add(job)


def seeker_allowed_for_any_role(seeker):
    for role, allowed_jobs in selected_jobs_by_role.items():
        if (
            seeker["main"] in allowed_jobs
            and seeker_fits_role(seeker, role, min_level)
        ):
            return True

    return False


with st.spinner("Fetching HorizonXI seekers..."):
    seekers = fetch_seekers()

seekers = [
    s for s in seekers
    if min_level <= s["level"] <= max_level
]

if min_level < 75:
    seekers = [s for s in seekers if s["level"] != 75]

seekers = [
    s for s in seekers
    if seeker_allowed_for_any_role(s)
]

try:
    all_options = build_party_options(
        seekers,
        current_job,
        your_level,
        min_level,
        selected_jobs_by_role,
    )
except Exception as e:
    st.error(f"Could not build parties: {e}")
    st.stop()

available_sync_levels = sorted(
    set(
        option_sync_level(option, your_level)
        for option in all_options
    ),
    reverse=True,
)

sync_filter_choices = ["All sync levels"] + [
    f"Lv{lvl}" for lvl in available_sync_levels
]

party_sync_filter = party_sync_filter_placeholder.selectbox(
    "Party sync level filter",
    sync_filter_choices,
)

if party_sync_filter != "All sync levels":
    selected_sync = int(party_sync_filter.replace("Lv", ""))

    options = [
        option for option in all_options
        if option_sync_level(option, your_level) == selected_sync
    ]
else:
    options = all_options

max_score = max(
    [o["score"] for o in options],
    default=1,
)

best_sync = "-"
best_score = "-"

if options:
    best_option = options[0]
    best_sync = option_sync_level(best_option, your_level)
    best_score = best_option["score"]

sync_levels_text = ", ".join(str(lvl) for lvl in available_sync_levels) or "-"

metric_cols = st.columns(4)

with metric_cols[0]:
    with st.container(border=True):
        st.caption("Sync Levels Available")
        st.markdown(f"### {sync_levels_text}")

metric_cols[1].metric("Party Options", len(options))
metric_cols[2].metric("Best Overall Sync", f"Lv{best_sync}" if best_sync != "-" else "-")
metric_cols[3].metric("Top Score", best_score)

st.subheader("Best Party Options")

if not options:
    st.warning("No full 6-person party found from current seekers.")
else:
    for i, option in enumerate(options, start=1):
        score = option["score"]
        archetype = option["archetype"]
        party = option["party"]
        reasons = option["reasons"]

        level_sync = option_sync_level(option, your_level)
        pct = score_percent(score, max_score)

        with st.container(border=True):
            top_cols = st.columns([1.2, 1.2, 2.8, 4])

            with top_cols[0]:
                if i == 1:
                    st.success("BEST OVERALL")
                else:
                    st.info(f"Option {i}")

            with top_cols[1]:
                st.info(f"Sync Lv{level_sync}")

            with top_cols[2]:
                st.markdown(f"**{archetype_icon(archetype)} {archetype}**")

            with top_cols[3]:
                st.progress(pct / 100)
                st.caption(f"Score {score}")

            your_main = current_job.split("/")[0]
            your_detected_role = option.get("your_role", "dd")

            role_map = {
                "healer": "👑 Healer",
                "support": "👑 Support",
                "puller": "👑 Puller",
                "dd(voke)": "👑 Tank / DD",
                "dd": "👑 DD",
            }

            if your_main == "BRD" and your_detected_role in {"support", "puller"}:
                your_role_display = "👑 Support / Puller"
            else:
                your_role_display = role_map.get(your_detected_role, "👑 YOU")

            party_members = [{
                "Role": your_role_display,
                "Name": "You",
                "Job/Sub": current_job,
                "Main": your_main,
                "Level": your_level,
            }]

            for role, seeker in party:
                party_members.append({
                    "Role": role_label(role),
                    "Name": seeker["name"],
                    "Job/Sub": seeker["job"],
                    "Main": seeker["main"],
                    "Level": seeker["level"],
                })

            member_cols = st.columns(6)

            for idx, member in enumerate(party_members):
                role_name = member["Role"]
                role_icon = ROLE_ICONS.get(role_name, "◆")
                badge_color = ROLE_BADGE_COLORS.get(role_name, "gray")

                with member_cols[idx]:
                    with st.container(border=True):
                        st.badge(
                            f"{role_icon} {role_name}",
                            color=badge_color,
                        )

                        st.markdown(
                            f"""
                            <div style="
                                font-size:20px;
                                font-weight:900;
                                margin-bottom:4px;
                                line-height:1.1;
                            ">
                                {member['Name']}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.markdown(
                            f"""
                            <div style="
                                font-size:14px;
                                font-weight:800;
                                line-height:1.2;
                            ">
                                {job_icon(member['Main'])} {member['Job/Sub']}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.caption(f"Lv{member['Level']}")

            if i == 1:
                with st.expander(
                    "Why the top party scored well",
                    expanded=False,
                ):
                    positives = [
                        r for r in reasons
                        if not r.startswith("-")
                    ]

                    warnings = [
                        r for r in reasons
                        if r.startswith("-")
                    ]

                    for r in positives[:14]:
                        st.write(r)

                    for w in warnings[:6]:
                        st.warning(w)

st.divider()

st.subheader("Available Seekers")

if seekers:
    seeker_rows = [
        {
            "Icon": job_icon(s["main"]),
            "Name": s["name"],
            "Job/Sub": s["job"],
            "Main": s["main"],
            "Sub": s["sub"],
            "Level": s["level"],
        }
        for s in seekers
    ]

    st.dataframe(
        pd.DataFrame(seeker_rows),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No seekers found in this level range.")

st.divider()

st.subheader("Role Match Table")

roles = [
    "healer",
    "support",
    "puller",
    "dd(voke)",
    "dd",
]

for role in roles:
    matches = [
        s for s in seekers
        if seeker_fits_role(s, role, min_level)
        and s["main"] in selected_jobs_by_role.get(role, set())
    ]

    with st.expander(
        f"{role.upper()} — {len(matches)} available",
        expanded=True,
    ):
        if matches:
            cols = st.columns(4)

            for idx, s in enumerate(matches):
                with cols[idx % 4]:
                    with st.container(border=True):
                        st.caption(role_label(role))

                        st.markdown(f"**{s['name']}**")

                        st.markdown(
                            f"{job_icon(s['main'])} "
                            f"`{s['job']}`"
                        )

                        st.caption(f"Lv{s['level']}")
        else:
            st.write("No matches.")