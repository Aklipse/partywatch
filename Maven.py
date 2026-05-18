import streamlit as st
import streamlit.components.v1 as components
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


def count_level_75_jobs(seeker):
    jobs = seeker.get("raw", {}).get("jobs", {})
    count_75 = 0

    if isinstance(jobs, dict):
        for _, job_level in jobs.items():
            try:
                if int(job_level) == 75:
                    count_75 += 1
            except (TypeError, ValueError):
                pass

    if count_75 == 0 and seeker.get("level") == 75:
        count_75 = 1

    return count_75


def best_party_signature(option, your_level):
    if not option:
        return None

    members = [
        f"{role}:{s['name']}:{s['job']}:{s['level']}"
        for role, s in option["party"]
    ]

    return "|".join([
        option.get("archetype", ""),
        str(option.get("score", "")),
        str(option_sync_level(option, your_level)),
        *sorted(members),
    ])


def unlock_audio_button():
    components.html(
        """
        <button
            id="enableSoundButton"
            onclick="
                try {
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    const ctx = new AudioContext();
                    ctx.resume();

                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();

                    osc.type = 'sine';
                    osc.frequency.value = 880;
                    gain.gain.value = 0.001;

                    osc.connect(gain);
                    gain.connect(ctx.destination);

                    osc.start();
                    osc.stop(ctx.currentTime + 0.05);

                    this.innerText = 'Sound Enabled';
                    this.style.background = '#1f7a3f';
                    this.style.border = '1px solid #77ff99';
                } catch (e) {
                    console.log('Audio unlock failed:', e);
                    this.innerText = 'Sound Blocked';
                }
            "
            style="
                width: 100%;
                background: rgba(124,199,255,0.18);
                color: #f7e7bd;
                border: 1px solid rgba(124,199,255,0.55);
                border-radius: 10px;
                padding: 8px 10px;
                font-weight: 800;
                cursor: pointer;
            "
        >
            Enable Sound
        </button>
        """,
        height=45,
    )


def play_wind_chime_sound():
    components.html(
        """
        <script>
        async function playChime() {
            try {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                const ctx = new AudioContext();

                if (ctx.state === "suspended") {
                    await ctx.resume();
                }

                const now = ctx.currentTime;

                function chime(freq, delay, gainValue) {
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();

                    osc.type = "sine";
                    osc.frequency.value = freq;

                    gain.gain.setValueAtTime(0.0001, now + delay);
                    gain.gain.linearRampToValueAtTime(gainValue, now + delay + 0.03);
                    gain.gain.exponentialRampToValueAtTime(0.0001, now + delay + 2.5);

                    osc.connect(gain);
                    gain.connect(ctx.destination);

                    osc.start(now + delay);
                    osc.stop(now + delay + 2.5);
                }

                chime(880, 0.00, 0.08);
                chime(1174, 0.18, 0.06);
                chime(1567, 0.36, 0.045);
            } catch (e) {
                console.log("Chime failed:", e);
            }
        }

        playChime();
        </script>
        """,
        height=1,
        width=1,
    )


st.markdown("""
<style>
.stApp {
    background: unset;
    color-scheme: light;
}

section[data-testid="stSidebar"] {
    background: rgba(7, 10, 16, 0.96);
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
}

section[data-testid="stSidebar"] hr {
    margin-top: 0.35rem !important;
    margin-bottom: 0.35rem !important;
}

section[data-testid="stSidebar"] .stNumberInput,
section[data-testid="stSidebar"] .stTextInput,
section[data-testid="stSidebar"] .stSelectbox {
    margin-bottom: 0.15rem !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] {
    margin-top: 0.15rem !important;
    margin-bottom: 0.15rem !important;
}

section[data-testid="stSidebar"] h3 {
    margin-top: 0.35rem !important;
    margin-bottom: 0.35rem !important;
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

div[data-testid="stSelectbox"]:has(div[data-baseweb="select"]) {
    background: rgba(120, 25, 25, 0.22);
    border: 1px solid rgba(255, 80, 80, 0.30);
    border-radius: 14px;
    padding: 8px;
}

/* DEFAULT SIDEBAR TEXT INPUTS = GREEN */
section[data-testid="stSidebar"] div[data-testid="stTextInput"] {
    background: rgba(25, 90, 45, 0.22);
    border: 1px solid rgba(80, 255, 140, 0.28);
    border-radius: 14px;
    padding: 8px;
}

/* ONLY YOUR NAME FIELD = GOLD */
section[data-testid="stSidebar"] div[data-testid="stTextInput"]:has(input[aria-label="Your Name"]) {
    background: rgba(247, 201, 88, 0.18) !important;
    border: 1px solid rgba(247, 201, 88, 0.60) !important;
    box-shadow: 0 0 10px rgba(247, 201, 88, 0.18) !important;
}

/* CLEAN INPUT BACKGROUND */
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
    background: transparent !important;
}

label[data-testid="stWidgetLabel"] p {
    font-size: 15px !important;
    font-weight: 700 !important;
}

.player-hover-name {
    font-size:20px;
    font-weight:900;
    margin-bottom:4px;
    line-height:1.1;
}

.level75-count {
    font-size:14px;
    color:#f7e7bd;
    font-weight:800;
    opacity:0.9;
}
</style>
""", unsafe_allow_html=True)


top_cols = st.columns([1.5, 1.5, 5])

with top_cols[0]:
    st.markdown("**Enable Sound Alerts**")
    alert_sound_enabled = st.toggle(
        "Wind chime",
        value=True,
        key="alert_sound_enabled",
    )

with top_cols[1]:
    st.markdown("**Refresh Every X Minutes**")
    refresh_minutes = st.slider(
        "Refresh every X minutes",
        1,
        15,
        3,
        key="refresh_minutes_top",
        label_visibility="collapsed",
    )

with top_cols[2]:
    st.markdown("")

st_autorefresh(
    interval=refresh_minutes * 60 * 1000,
    key="partywatch_refresh",
)

# Purple-styled Your Name input above job
st.sidebar.image("assets/ffxiparty_logo.png", width=240)

st.sidebar.markdown("""
<style>
section[data-testid="stSidebar"] img {
    display: block;
    margin: 0 auto 18px auto;
}

</style>
""", unsafe_allow_html=True)

your_name = st.sidebar.text_input(
    "Your Name",
    value="",
).strip()

current_job = st.sidebar.text_input(
    "Your job",
    value="",
).upper().strip()

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

max_level = min(75, your_level + 10)

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
    all_seekers_raw = fetch_seekers()

level_75_count_by_name = {
    s["name"].lower(): count_level_75_jobs(s)
    for s in all_seekers_raw
}

seekers = [
    s for s in all_seekers_raw
    if min_level <= s["level"] <= max_level
]

if min_level < 75:
    seekers = [s for s in seekers if s["level"] != 75]

seekers = [
    s for s in seekers
    if seeker_allowed_for_any_role(s)
]

st.sidebar.subheader("Available Seekers")

included_seekers = []
forced_seekers = []

with st.sidebar.expander("Include / Force Seekers", expanded=False):
    if seekers:
        for s in sorted(seekers, key=lambda x: x["name"].lower()):
            base_key = f"{s['name'].lower()}_{s['main']}_{s['level']}"

            st.caption(f"{job_icon(s['main'])} {s['name']} — {s['job']} Lv{s['level']}")

            cols = st.columns([1, 1])

            with cols[0]:
                included = st.checkbox(
                    "Include",
                    value=True,
                    key=f"include_seeker_{base_key}",
                )

            with cols[1]:
                forced = st.checkbox(
                    "Force",
                    value=False,
                    key=f"force_seeker_{base_key}",
                )

            if forced:
                included = True
                forced_seekers.append(s)

            if included:
                included_seekers.append(s)

            st.divider()
    else:
        st.caption("No seekers available with current filters.")

seekers = included_seekers

if len(forced_seekers) > 5:
    st.sidebar.error("You can only force up to 5 seekers because you are the 6th party member.")

try:
    all_options = build_party_options(
        seekers,
        current_job,
        your_level,
        min_level,
        selected_jobs_by_role,
        forced_seekers,
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

if (
    "party_sync_filter" in st.session_state
    and st.session_state.party_sync_filter not in sync_filter_choices
):
    st.session_state.party_sync_filter = "All sync levels"

default_index = sync_filter_choices.index(
    st.session_state.get("party_sync_filter", "All sync levels")
)

party_sync_filter = party_sync_filter_placeholder.selectbox(
    "Party sync level filter",
    sync_filter_choices,
    index=default_index,
    key="party_sync_filter",
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

    current_best_signature = best_party_signature(best_option, your_level)
    previous_best_signature = st.session_state.get("previous_best_signature")

    new_best_available = (
        previous_best_signature is not None
        and current_best_signature != previous_best_signature
    )

    st.session_state["previous_best_signature"] = current_best_signature

    if new_best_available:
        st.toast("🔔 New best party option available!", icon="🎵")

        if alert_sound_enabled:
            play_wind_chime_sound()
else:
    st.session_state["previous_best_signature"] = None

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

                        level_75_count = level_75_count_by_name.get(
                            member["Name"].lower(),
                            0,
                        )

                        level_75_text = (
                            ""
                            if member["Name"] == "You"
                            else f" <span class='level75-count'>(75: {level_75_count})</span>"
                        )

                        st.markdown(
                            f"""
                            <div class="player-hover-name">
                                {member['Name']}{level_75_text}
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
    forced_names = {fs["name"].lower() for fs in forced_seekers}

    seeker_rows = [
        {
            "Icon": job_icon(s["main"]),
            "Name": s["name"],
            "Job/Sub": s["job"],
            "Main": s["main"],
            "Sub": s["sub"],
            "Level": s["level"],
            "75 Jobs Seeking": level_75_count_by_name.get(s["name"].lower(), 0),
            "Forced": "Yes" if s["name"].lower() in forced_names else "",
        }
        for s in sorted(seekers, key=lambda x: x["name"].lower())
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

    if not matches:
        continue

    st.markdown(f"### {role.upper()}")

    rows = [
        {
            "Name": s["name"],
            "Job": s["job"],
            "Main": s["main"],
            "Level": s["level"],
        }
        for s in sorted(matches, key=lambda x: x["name"].lower())
    ]

    st.dataframe(pd.DataFrame(rows), hide_index=True)
