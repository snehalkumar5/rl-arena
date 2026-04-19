"""
Geo-Arena: Geopolitical Simulation Replay Viewer

A polished Streamlit dashboard for replaying and analyzing
multi-agent geopolitical simulations.

Run with: streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path
from typing import List

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
import pandas as pd

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Geo-Arena | Geopolitical Simulation",
    page_icon="globe",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Dark themed cards */
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
        color: #e0e0e0;
    }
    .metric-card h3 {
        color: #00d2ff;
        margin: 0 0 8px 0;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-card .value {
        font-size: 28px;
        font-weight: 700;
        color: #ffffff;
    }
    .metric-card .delta {
        font-size: 13px;
        margin-top: 4px;
    }
    .delta-positive { color: #00e676; }
    .delta-negative { color: #ff5252; }

    /* Actor cards */
    .actor-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-left: 4px solid;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
    .actor-state { border-left-color: #00d2ff; }
    .actor-nonstate { border-left-color: #ff6b35; }

    /* News ticker */
    .news-item {
        background: #1a1a2e;
        border-left: 3px solid #ffd700;
        padding: 10px 16px;
        margin: 6px 0;
        border-radius: 0 8px 8px 0;
        color: #e0e0e0;
        font-size: 14px;
    }

    /* Resolution log */
    .resolution {
        padding: 8px 14px;
        margin: 4px 0;
        border-radius: 6px;
        font-size: 13px;
        font-family: 'Consolas', monospace;
    }
    .res-treaty { background: #0d3320; border-left: 3px solid #00e676; color: #a5d6a7; }
    .res-sanction { background: #3e2723; border-left: 3px solid #ff5252; color: #ef9a9a; }
    .res-trade { background: #1a237e; border-left: 3px solid #448aff; color: #90caf9; }
    .res-military { background: #311b92; border-left: 3px solid #b388ff; color: #d1c4e9; }
    .res-covert { background: #263238; border-left: 3px solid #78909c; color: #b0bec5; }
    .res-default { background: #212121; border-left: 3px solid #616161; color: #bdbdbd; }

    /* Message styling */
    .msg-private {
        background: #1a1a2e;
        border-left: 3px solid #7c4dff;
        padding: 10px 14px;
        margin: 4px 0;
        border-radius: 0 8px 8px 0;
        font-size: 13px;
        color: #ce93d8;
    }
    .msg-public {
        background: #1a1a2e;
        border-left: 3px solid #00bcd4;
        padding: 10px 14px;
        margin: 4px 0;
        border-radius: 0 8px 8px 0;
        font-size: 13px;
        color: #80deea;
    }

    /* Section headers */
    .section-header {
        font-size: 18px;
        font-weight: 600;
        color: #00d2ff;
        padding: 8px 0;
        border-bottom: 2px solid #0f3460;
        margin-bottom: 12px;
    }

    /* Sidebar styling */
    .sidebar-info {
        background: #1a1a2e;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        font-size: 13px;
        color: #b0bec5;
    }

    /* Hide default streamlit elements for cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Action badge */
    .action-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-treaty { background: #1b5e20; color: #a5d6a7; }
    .badge-sanction { background: #b71c1c; color: #ef9a9a; }
    .badge-trade { background: #0d47a1; color: #90caf9; }
    .badge-mobilize { background: #4a148c; color: #ce93d8; }
    .badge-covert { background: #37474f; color: #90a4ae; }
    .badge-hold { background: #424242; color: #bdbdbd; }
    .badge-nonstate { background: #e65100; color: #ffcc80; }
</style>
""", unsafe_allow_html=True)


# ── Data Loading ────────────────────────────────────────────────────────────

@st.cache_data
def load_replay(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_replays() -> List[Path]:
    replay_dir = Path("logs/replays")
    if not replay_dir.exists():
        return []
    return sorted(replay_dir.glob("*_replay.json"), reverse=True)


# ── Color Schemes ───────────────────────────────────────────────────────────

ACTOR_COLORS = {
    0: "#00d2ff",  # Cyan
    1: "#ff6b35",  # Orange
    2: "#00e676",  # Green
    3: "#ffd740",  # Amber
    4: "#ff5252",  # Red
    5: "#b388ff",  # Purple
    6: "#ffa726",  # Deep Orange
    7: "#4db6ac",  # Teal
    8: "#e91e63",  # Pink
    9: "#8d6e63",  # Brown
}

ARCHETYPE_ICONS = {
    "maritime_trade_democracy": "anchor",
    "continental_revisionist_power": "shield",
    "energy_exporter": "zap",
    "trade_hub_mediator": "handshake",
    "insurgent_network": "target",
    "separatist_movement": "flag",
}

REGION_TYPES_COLORS = {
    "sea_lane": "#0077b6",
    "coastal": "#00b4d8",
    "interior": "#606c38",
    "border": "#bc6c25",
    "resource_zone": "#d4a373",
    "mountainous": "#6b705c",
}


# ── Helper Functions ────────────────────────────────────────────────────────

def get_actor_color(idx: int) -> str:
    return ACTOR_COLORS.get(idx, "#ffffff")


def get_resolution_class(res: str) -> str:
    res_lower = res.lower()
    if "treaty" in res_lower:
        return "res-treaty"
    if "sanction" in res_lower:
        return "res-sanction"
    if "trade" in res_lower or "aid" in res_lower:
        return "res-trade"
    if "mobilize" in res_lower or "military" in res_lower:
        return "res-military"
    if "covert" in res_lower or "cyber" in res_lower or "exposed" in res_lower:
        return "res-covert"
    return "res-default"


def get_action_badge_class(action_type: str) -> str:
    if action_type in ("treaty_proposal",):
        return "badge-treaty"
    if action_type in ("sanction",):
        return "badge-sanction"
    if action_type in ("trade_offer", "aid"):
        return "badge-trade"
    if action_type in ("mobilize",):
        return "badge-mobilize"
    if action_type in ("proxy_support", "cyber_operation", "intel_share"):
        return "badge-covert"
    if action_type in ("sabotage", "recruit", "raid", "seek_sponsor", "propaganda", "ceasefire_offer"):
        return "badge-nonstate"
    return "badge-hold"


# ── Visualization Functions ─────────────────────────────────────────────────

def create_world_map(world: dict, turn_data: dict = None) -> go.Figure:
    """Create a network graph visualization of the world regions."""
    G = nx.Graph()
    regions = world["regions"]
    actors = world["actors"]

    # Build actor lookup
    actor_lookup = {a["actor_id"]: a for a in actors}
    actor_ids = list(actor_lookup.keys())

    # Add region nodes
    for region in regions:
        G.add_node(region["region_id"], **region)

    # Add edges from adjacency
    for region in regions:
        for neighbor in region.get("neighbors", []):
            if G.has_node(neighbor):
                G.add_edge(region["region_id"], neighbor)

    # Use spring layout for positioning
    pos = nx.spring_layout(G, seed=42, k=2.5, iterations=80)

    # Get current control state from regions
    control = {}
    for region in regions:
        control[region["region_id"]] = region.get("controller")

    # Draw edges
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1.5, color="#2a3a5c"),
        hoverinfo="none",
        mode="lines",
    )

    # Draw nodes
    node_x, node_y, node_text, node_colors, node_sizes, hover_texts = [], [], [], [], [], []

    for region in regions:
        rid = region["region_id"]
        x, y = pos[rid]
        node_x.append(x)
        node_y.append(y)

        controller = control.get(rid)
        if controller and controller in actor_lookup:
            color_idx = actor_ids.index(controller)
            color = get_actor_color(color_idx)
            ctrl_name = actor_lookup[controller]["name"]
        else:
            color = "#555555"
            ctrl_name = "Contested"

        node_colors.append(color)
        node_sizes.append(35 if "chokepoint" in region.get("resource_tags", []) else 25)
        node_text.append(region["name"])

        stability = region.get("stability", 0.5)
        tags = ", ".join(region.get("resource_tags", []))
        hover_texts.append(
            f"<b>{region['name']}</b><br>"
            f"Type: {region['type']}<br>"
            f"Controller: {ctrl_name}<br>"
            f"Stability: {stability:.0%}<br>"
            f"Resources: {tags}"
        )

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        textfont=dict(size=11, color="#e0e0e0"),
        hovertext=hover_texts,
        hoverinfo="text",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color="#0f3460"),
            symbol="circle",
        ),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        plot_bgcolor="#0a0a1a",
        paper_bgcolor="#0a0a1a",
        margin=dict(l=20, r=20, t=40, b=20),
        height=420,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        title=dict(
            text="World Map - Region Control",
            font=dict(size=14, color="#00d2ff"),
            x=0.5,
        ),
    )

    return fig


def create_relations_graph(actors: list, turn_data: dict = None) -> go.Figure:
    """Create a force-directed graph showing actor relationships."""
    actor_lookup = {a["actor_id"]: a for a in actors}
    actor_ids = list(actor_lookup.keys())

    G = nx.Graph()
    for actor in actors:
        G.add_node(actor["actor_id"])

    # Get current relations
    relations = {}
    if turn_data and "state_snapshot" in turn_data:
        for aid, state in turn_data["state_snapshot"].items():
            relations[aid] = state.get("relations", {})
    else:
        for actor in actors:
            relations[actor["actor_id"]] = actor.get("relations", {})

    # Add edges with relation values
    seen = set()
    for aid, rels in relations.items():
        for other_id, value in rels.items():
            edge_key = tuple(sorted([aid, other_id]))
            if edge_key not in seen and other_id in actor_lookup:
                seen.add(edge_key)
                G.add_edge(aid, other_id, weight=value)

    pos = nx.spring_layout(G, seed=123, k=3.0, iterations=80)

    # Build all edge traces
    edge_traces = []
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        weight = edge[2].get("weight", 0)

        if weight > 0.3:
            color = f"rgba(0, 230, 118, {min(abs(weight), 1) * 0.7})"
            width = abs(weight) * 3
        elif weight < -0.3:
            color = f"rgba(255, 82, 82, {min(abs(weight), 1) * 0.7})"
            width = abs(weight) * 3
        else:
            color = "rgba(150, 150, 150, 0.2)"
            width = 0.5

        name0 = actor_lookup.get(edge[0], {}).get("name", edge[0])
        name1 = actor_lookup.get(edge[1], {}).get("name", edge[1])

        edge_traces.append(go.Scatter(
            x=[x0, x1], y=[y0, y1],
            mode="lines",
            line=dict(width=width, color=color),
            hoverinfo="text",
            hovertext=f"{name0} <-> {name1}: {weight:+.2f}",
            showlegend=False,
        ))

    # Draw nodes
    node_x, node_y, node_text, node_colors, hover_texts = [], [], [], [], []
    for i, actor in enumerate(actors):
        aid = actor["actor_id"]
        x, y = pos[aid]
        node_x.append(x)
        node_y.append(y)
        node_text.append(actor["name"].split()[0])  # Short name
        node_colors.append(get_actor_color(i))

        actor_type = "State" if actor["actor_type"] == "state" else "Non-State"
        hover_texts.append(
            f"<b>{actor['name']}</b><br>"
            f"Type: {actor_type}<br>"
            f"Archetype: {actor['archetype'].replace('_', ' ').title()}"
        )

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="bottom center",
        textfont=dict(size=11, color="#e0e0e0"),
        hovertext=hover_texts,
        hoverinfo="text",
        marker=dict(
            size=[40 if a["actor_type"] == "state" else 28 for a in actors],
            color=node_colors,
            line=dict(width=2, color="#0f3460"),
            symbol=["circle" if a["actor_type"] == "state" else "diamond" for a in actors],
        ),
        showlegend=False,
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        plot_bgcolor="#0a0a1a",
        paper_bgcolor="#0a0a1a",
        margin=dict(l=20, r=20, t=40, b=20),
        height=420,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        title=dict(
            text="Diplomacy Network (Green=Ally, Red=Hostile)",
            font=dict(size=14, color="#00d2ff"),
            x=0.5,
        ),
    )

    return fig


def create_score_chart(turns: list, actors: list) -> go.Figure:
    """Create a line chart showing score progression across turns."""
    actor_lookup = {a["actor_id"]: a for a in actors}
    actor_ids = list(actor_lookup.keys())

    fig = go.Figure()

    for i, actor in enumerate(actors):
        aid = actor["actor_id"]
        turn_nums = []
        scores = []

        for turn_data in turns:
            for score in turn_data.get("scores", []):
                if score["actor_id"] == aid:
                    turn_nums.append(turn_data["turn"])
                    scores.append(score["total"])

        fig.add_trace(go.Scatter(
            x=turn_nums,
            y=scores,
            mode="lines+markers",
            name=actor["name"],
            line=dict(color=get_actor_color(i), width=3),
            marker=dict(size=8, color=get_actor_color(i)),
        ))

    fig.update_layout(
        plot_bgcolor="#0a0a1a",
        paper_bgcolor="#0a0a1a",
        font=dict(color="#e0e0e0"),
        margin=dict(l=50, r=30, t=50, b=40),
        height=380,
        title=dict(
            text="Score Progression",
            font=dict(size=16, color="#00d2ff"),
            x=0.5,
        ),
        xaxis=dict(
            title="Turn",
            gridcolor="#1a2a44",
            dtick=1,
        ),
        yaxis=dict(
            title="Score",
            gridcolor="#1a2a44",
        ),
        legend=dict(
            bgcolor="rgba(10,10,26,0.8)",
            bordercolor="#0f3460",
            borderwidth=1,
            font=dict(size=11),
        ),
    )

    return fig


def create_resource_radar(actor_state: dict, actor_name: str, color: str) -> go.Figure:
    """Create a radar chart for an actor's resources."""
    categories = ["Treasury", "Stability", "Military", "Energy", "Food", "Influence", "Reputation"]
    values = [
        min(actor_state.get("treasury", 0) / 1.5, 100),
        actor_state.get("domestic_stability", 0),
        actor_state.get("military_readiness", 0),
        actor_state.get("energy", 0),
        actor_state.get("food", 0),
        actor_state.get("influence", 0),
        actor_state.get("reputation", 0),
    ]
    values.append(values[0])  # Close the radar
    categories.append(categories[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        fillcolor=f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.15)",
        line=dict(color=color, width=2),
        marker=dict(size=5, color=color),
        name=actor_name,
    ))

    fig.update_layout(
        polar=dict(
            bgcolor="#0a0a1a",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor="#1a2a44",
                tickfont=dict(size=9, color="#666"),
            ),
            angularaxis=dict(
                gridcolor="#1a2a44",
                tickfont=dict(size=10, color="#b0bec5"),
            ),
        ),
        plot_bgcolor="#0a0a1a",
        paper_bgcolor="#0a0a1a",
        margin=dict(l=60, r=60, t=30, b=30),
        height=280,
        showlegend=False,
    )

    return fig


def create_leaderboard_bar(final_scores: list, actors: list) -> go.Figure:
    """Create a horizontal bar chart for the final leaderboard."""
    actor_ids = [a["actor_id"] for a in actors]

    names = [s["name"] for s in final_scores]
    scores = [s["final_score"] for s in final_scores]
    colors = []
    for s in final_scores:
        idx = next((i for i, a in enumerate(actors) if a["actor_id"] == s["actor_id"]), 0)
        colors.append(get_actor_color(idx))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=names,
        x=scores,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(width=0),
        ),
        text=[f"{s:.1f}" for s in scores],
        textposition="outside",
        textfont=dict(color="#e0e0e0", size=13, family="Consolas"),
    ))

    fig.update_layout(
        plot_bgcolor="#0a0a1a",
        paper_bgcolor="#0a0a1a",
        font=dict(color="#e0e0e0"),
        margin=dict(l=150, r=60, t=40, b=30),
        height=280,
        title=dict(
            text="Final Leaderboard",
            font=dict(size=16, color="#00d2ff"),
            x=0.5,
        ),
        xaxis=dict(
            gridcolor="#1a2a44",
            title="Score",
        ),
        yaxis=dict(
            autorange="reversed",
        ),
    )

    return fig


def create_score_breakdown(turn_data: dict, actors: list) -> go.Figure:
    """Create stacked bar chart showing score components for each actor."""
    actor_lookup = {a["actor_id"]: a for a in actors}
    actor_ids = list(actor_lookup.keys())

    scores = turn_data.get("scores", [])
    if not scores:
        return go.Figure()

    names = []
    economy = []
    stability = []
    influence = []
    alliance = []
    objective = []

    for score in scores:
        names.append(actor_lookup.get(score["actor_id"], {}).get("name", score["actor_id"]))
        economy.append(score.get("economy_score", 0) * 0.20)
        stability.append(score.get("stability_score", 0) * 0.20)
        influence.append(score.get("influence_score", 0) * 0.20)
        alliance.append(score.get("alliance_score", 0) * 0.15)
        objective.append(score.get("objective_score", 0) * 0.20)

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Economy", x=names, y=economy, marker_color="#448aff"))
    fig.add_trace(go.Bar(name="Stability", x=names, y=stability, marker_color="#00e676"))
    fig.add_trace(go.Bar(name="Influence", x=names, y=influence, marker_color="#ffd740"))
    fig.add_trace(go.Bar(name="Alliance", x=names, y=alliance, marker_color="#b388ff"))
    fig.add_trace(go.Bar(name="Objective", x=names, y=objective, marker_color="#ff5252"))

    fig.update_layout(
        barmode="stack",
        plot_bgcolor="#0a0a1a",
        paper_bgcolor="#0a0a1a",
        font=dict(color="#e0e0e0", size=11),
        margin=dict(l=40, r=20, t=40, b=40),
        height=320,
        title=dict(
            text="Score Breakdown by Component",
            font=dict(size=14, color="#00d2ff"),
            x=0.5,
        ),
        xaxis=dict(gridcolor="#1a2a44", tickangle=-30),
        yaxis=dict(gridcolor="#1a2a44", title="Weighted Score"),
        legend=dict(
            bgcolor="rgba(10,10,26,0.8)",
            bordercolor="#0f3460",
            font=dict(size=10),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
    )

    return fig


# ── Main App ────────────────────────────────────────────────────────────────

def main():
    # ── Sidebar ─────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## GEO-ARENA")
        st.markdown("*Geopolitical Multi-Agent Simulation*")
        st.markdown("---")

        # Find and select replay
        replays = find_replays()

        if not replays:
            st.warning("No replay files found. Run a simulation first:")
            st.code("python -m app.main", language="bash")

            # Offer to run simulation
            if st.button("Run Simulation Now", type="primary"):
                with st.spinner("Running simulation..."):
                    from app.runner import run_simulation
                    run_simulation("scenarios/seed_worlds/saffron_sea_crisis.json")
                    st.rerun()
            return

        replay_names = [p.stem for p in replays]
        selected = st.selectbox("Select Replay", replay_names, index=0)
        replay_path = replays[replay_names.index(selected)]

        replay = load_replay(str(replay_path))
        world = replay["world"]
        turns = replay["turns"]
        final_scores = replay.get("final_scores", [])
        actors = world["actors"]

        st.markdown("---")

        # Turn selector
        max_turn = len(turns)
        current_turn = st.slider(
            "Turn",
            min_value=1,
            max_value=max_turn,
            value=max_turn,
            key="turn_slider",
        )
        turn_data = turns[current_turn - 1]

        st.markdown("---")

        # Actor list
        st.markdown("### Actors")
        for i, actor in enumerate(actors):
            icon = "circle" if actor["actor_type"] == "state" else "small_orange_diamond"
            color = get_actor_color(i)
            archetype = actor["archetype"].replace("_", " ").title()
            st.markdown(
                f'<div style="padding:6px 10px; margin:3px 0; border-left:3px solid {color}; '
                f'border-radius:0 4px 4px 0; background:#1a1a2e; font-size:13px;">'
                f'<b style="color:{color}">{actor["name"]}</b><br>'
                f'<span style="color:#78909c; font-size:11px;">{archetype}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown(
            '<div class="sidebar-info">'
            f'<b>Scenario:</b> {world["name"]}<br>'
            f'<b>Regions:</b> {len(world["regions"])}<br>'
            f'<b>Turn Limit:</b> {world["turn_limit"]}<br>'
            f'<b>Agent Type:</b> {replay.get("metadata", {}).get("agent_type", "unknown")}'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Main Content ────────────────────────────────────────────────────

    # Header
    st.markdown(
        f'<h1 style="text-align:center; color:#00d2ff; margin-bottom:0;">'
        f'{world["name"]}</h1>'
        f'<p style="text-align:center; color:#78909c; margin-top:4px; font-size:15px;">'
        f'Turn {current_turn} of {max_turn} | {len(actors)} Actors | {len(world["regions"])} Regions</p>',
        unsafe_allow_html=True,
    )

    # ── Top Row: Key Metrics ────────────────────────────────────────────
    st.markdown("---")

    # Compute metrics for current turn
    top_score = max(turn_data.get("scores", [{}]), key=lambda s: s.get("total", 0), default={})
    total_actions = len(turn_data.get("actions", []))
    total_messages = len(turn_data.get("messages", []))
    active_conflicts = sum(
        1 for r in turn_data.get("resolutions", [])
        if any(w in r.lower() for w in ["sabotage", "raid", "sanction", "cyber", "mobilize"])
    )

    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    with mcol1:
        leader_name = top_score.get("actor_id", "N/A")
        leader_actor = next((a for a in actors if a["actor_id"] == leader_name), None)
        leader_display = leader_actor["name"] if leader_actor else leader_name
        st.markdown(
            f'<div class="metric-card">'
            f'<h3>Current Leader</h3>'
            f'<div class="value">{leader_display}</div>'
            f'<div class="delta" style="color:#00e676;">Score: {top_score.get("total", 0):.1f}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with mcol2:
        st.markdown(
            f'<div class="metric-card">'
            f'<h3>Actions This Turn</h3>'
            f'<div class="value">{total_actions}</div>'
            f'<div class="delta" style="color:#448aff;">{total_messages} diplomatic messages</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with mcol3:
        st.markdown(
            f'<div class="metric-card">'
            f'<h3>Active Conflicts</h3>'
            f'<div class="value">{active_conflicts}</div>'
            f'<div class="delta" style="color:#ff5252;">hostile resolutions</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with mcol4:
        treaties_count = sum(
            1 for r in turn_data.get("resolutions", []) if "treaty" in r.lower() and "rejected" not in r.lower()
        )
        st.markdown(
            f'<div class="metric-card">'
            f'<h3>New Treaties</h3>'
            f'<div class="value">{treaties_count}</div>'
            f'<div class="delta" style="color:#00e676;">signed this turn</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── News Ticker ─────────────────────────────────────────────────────
    if turn_data.get("public_news"):
        st.markdown('<div class="section-header">PUBLIC BULLETIN</div>', unsafe_allow_html=True)
        for news in turn_data["public_news"]:
            st.markdown(f'<div class="news-item">{news}</div>', unsafe_allow_html=True)

    # ── Row 2: World Map + Relations ────────────────────────────────────
    map_col, rel_col = st.columns(2)

    with map_col:
        fig_map = create_world_map(world, turn_data)
        st.plotly_chart(fig_map, use_container_width=True)

    with rel_col:
        fig_rel = create_relations_graph(actors, turn_data)
        st.plotly_chart(fig_rel, use_container_width=True)

    # ── Row 3: Actions + Resolutions ────────────────────────────────────
    act_col, res_col = st.columns(2)

    with act_col:
        st.markdown('<div class="section-header">ACTIONS</div>', unsafe_allow_html=True)
        for action in turn_data.get("actions", []):
            badge_class = get_action_badge_class(action["action_type"])
            target_str = f" -> {action.get('target_name') or action.get('target', '')}" if action.get("target") else ""
            st.markdown(
                f'<div style="padding:8px 12px; margin:4px 0; background:#1a1a2e; border-radius:6px;">'
                f'<span class="action-badge {badge_class}">{action["action_type"].replace("_", " ")}</span> '
                f'<b style="color:#e0e0e0;">{action["actor_name"]}</b>'
                f'<span style="color:#78909c;">{target_str}</span><br>'
                f'<span style="color:#616161; font-size:12px; font-style:italic;">{action.get("rationale", "")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with res_col:
        st.markdown('<div class="section-header">RESOLUTIONS</div>', unsafe_allow_html=True)
        for res in turn_data.get("resolutions", []):
            res_class = get_resolution_class(res)
            st.markdown(f'<div class="resolution {res_class}">{res}</div>', unsafe_allow_html=True)

    # ── Row 4: Score Chart + Leaderboard ────────────────────────────────
    st.markdown("---")
    score_col, lb_col = st.columns([3, 2])

    with score_col:
        fig_scores = create_score_chart(turns[:current_turn], actors)
        st.plotly_chart(fig_scores, use_container_width=True)

    with lb_col:
        if final_scores:
            fig_lb = create_leaderboard_bar(final_scores, actors)
            st.plotly_chart(fig_lb, use_container_width=True)

    # ── Row 5: Score Breakdown + Messages ───────────────────────────────
    breakdown_col, msg_col = st.columns([3, 2])

    with breakdown_col:
        fig_breakdown = create_score_breakdown(turn_data, actors)
        st.plotly_chart(fig_breakdown, use_container_width=True)

    with msg_col:
        st.markdown('<div class="section-header">DIPLOMACY</div>', unsafe_allow_html=True)

        # Public statements
        for actor_id, statement in turn_data.get("public_statements", {}).items():
            actor_name = next((a["name"] for a in actors if a["actor_id"] == actor_id), actor_id)
            if statement:
                st.markdown(
                    f'<div class="msg-public"><b>{actor_name}:</b> {statement}</div>',
                    unsafe_allow_html=True,
                )

        # Private messages
        if turn_data.get("messages"):
            st.markdown(
                '<div style="margin-top:12px; font-size:12px; color:#7c4dff; font-weight:600;">'
                'PRIVATE CHANNELS (INTERCEPTED)</div>',
                unsafe_allow_html=True,
            )
            for msg in turn_data["messages"]:
                from_name = next((a["name"] for a in actors if a["actor_id"] == msg["from"]), msg["from"])
                to_name = next((a["name"] for a in actors if a["actor_id"] == msg["to"]), msg["to"])
                st.markdown(
                    f'<div class="msg-private"><b>{from_name}</b> -> <b>{to_name}</b>: {msg["text"]}</div>',
                    unsafe_allow_html=True,
                )

    # ── Row 6: Actor Details (expandable) ───────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-header">ACTOR DOSSIERS</div>', unsafe_allow_html=True)

    cols = st.columns(3)
    for i, actor in enumerate(actors):
        col_idx = i % 3
        color = get_actor_color(i)
        aid = actor["actor_id"]

        # Get current state
        actor_state = turn_data.get("state_snapshot", {}).get(aid, {})

        with cols[col_idx]:
            with st.expander(f"{actor['name']}", expanded=(i < 3)):
                # Radar chart
                if actor_state:
                    fig_radar = create_resource_radar(actor_state, actor["name"], color)
                    st.plotly_chart(fig_radar, use_container_width=True)

                # Key stats
                if actor_state:
                    st.markdown(
                        f'<div style="font-size:12px; color:#b0bec5; line-height:1.8;">'
                        f'Treasury: <b style="color:{color}">{actor_state.get("treasury", 0):.0f}</b> | '
                        f'Stability: <b style="color:{color}">{actor_state.get("domestic_stability", 0):.0f}</b> | '
                        f'Military: <b style="color:{color}">{actor_state.get("military_readiness", 0):.0f}</b><br>'
                        f'Influence: <b style="color:{color}">{actor_state.get("influence", 0):.0f}</b> | '
                        f'Reputation: <b style="color:{color}">{actor_state.get("reputation", 0):.0f}</b>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # Objectives
                st.markdown(
                    f'<div style="font-size:11px; color:#616161; margin-top:8px;">'
                    f'<b>Objectives:</b> {", ".join(actor.get("visible_objectives", []))}'
                    f'</div>',
                    unsafe_allow_html=True,
                )


def backtest_page():
    """Render the backtest comparison page for Hormuz scenario."""
    st.markdown(
        '<h1 style="text-align:center; color:#00d2ff; margin-bottom:0;">'
        'Hormuz Crisis - Backtest Analysis</h1>'
        '<p style="text-align:center; color:#78909c; margin-top:4px; font-size:13px;">'
        'DISCLAIMER: Simulation outputs are speculative. Not an intelligence product.</p>',
        unsafe_allow_html=True,
    )

    # Load backtest report
    report_path = Path("logs/metrics/backtest_report.json")
    variants_path = Path("logs/metrics/variant_comparison.json")

    if not report_path.exists():
        st.warning("No backtest report found. Run: `python -m app.backtest`")
        if st.button("Run Backtest Now", type="primary"):
            with st.spinner("Running Hormuz backtest..."):
                import subprocess
                subprocess.run([
                    "python", "-m", "app.backtest", "--agent", "mock",
                ], cwd=str(Path(__file__).parent))
                st.rerun()
        return

    with open(report_path) as f:
        report = json.load(f)

    # ── Overall Accuracy Gauge ──────────────────────────────────────────
    st.markdown("---")
    acc = report["overall_accuracy"]

    c1, c2, c3 = st.columns(3)
    with c1:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=acc * 100,
            title={"text": "Overall Accuracy", "font": {"color": "#00d2ff", "size": 16}},
            number={"suffix": "%", "font": {"color": "#e0e0e0"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#333"},
                "bar": {"color": "#00d2ff"},
                "bgcolor": "#1a1a2e",
                "bordercolor": "#0f3460",
                "steps": [
                    {"range": [0, 30], "color": "#3e1111"},
                    {"range": [30, 60], "color": "#3e3511"},
                    {"range": [60, 100], "color": "#113e1a"},
                ],
            },
        ))
        fig_gauge.update_layout(
            paper_bgcolor="#0a0a1a", font={"color": "#e0e0e0"},
            height=250, margin=dict(l=30, r=30, t=60, b=20),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with c2:
        correct = len(report.get("correct_predictions", []))
        diverge = len(report.get("divergences", []))
        total = correct + diverge
        st.markdown(
            f'<div class="metric-card">'
            f'<h3>Predictions</h3>'
            f'<div class="value">{correct} / {total}</div>'
            f'<div class="delta delta-positive">exact matches across all turns</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="metric-card">'
            f'<h3>Divergences</h3>'
            f'<div class="value">{diverge}</div>'
            f'<div class="delta delta-negative">missed predictions</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f'<div class="metric-card">'
            f'<h3>Baseline Date</h3>'
            f'<div class="value">{report.get("baseline_date", "N/A")}</div>'
            f'<div class="delta" style="color:#78909c;">Agent: {report.get("agent_type", "mock")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="metric-card">'
            f'<h3>Turns Simulated</h3>'
            f'<div class="value">{len(report.get("turn_comparisons", []))}</div>'
            f'<div class="delta" style="color:#78909c;">Apr 8 - Apr 19, 2026</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Per-Actor Accuracy Bar Chart ────────────────────────────────────
    st.markdown("---")
    actor_acc = report.get("actor_accuracy", {})
    if actor_acc:
        names = list(actor_acc.keys())
        accs = [actor_acc[n] * 100 for n in names]
        colors = ["#00e676" if a >= 40 else "#ffd740" if a >= 25 else "#ff5252" for a in accs]

        fig_bar = go.Figure(go.Bar(
            x=accs, y=names, orientation="h",
            marker=dict(color=colors),
            text=[f"{a:.0f}%" for a in accs],
            textposition="outside",
            textfont=dict(color="#e0e0e0", size=12),
        ))
        fig_bar.update_layout(
            title=dict(text="Per-Actor Prediction Accuracy", font=dict(color="#00d2ff", size=16), x=0.5),
            plot_bgcolor="#0a0a1a", paper_bgcolor="#0a0a1a",
            font=dict(color="#e0e0e0"),
            xaxis=dict(title="Accuracy %", gridcolor="#1a2a44", range=[0, 100]),
            yaxis=dict(autorange="reversed"),
            height=350, margin=dict(l=140, r=60, t=50, b=40),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── Turn-by-Turn Accuracy Line ──────────────────────────────────────
    comparisons = report.get("turn_comparisons", [])
    if comparisons:
        turn_labels = [c["label"] for c in comparisons]
        turn_accs = [c["turn_accuracy"] * 100 for c in comparisons]

        fig_line = go.Figure(go.Scatter(
            x=turn_labels, y=turn_accs,
            mode="lines+markers+text",
            text=[f"{a:.0f}%" for a in turn_accs],
            textposition="top center",
            textfont=dict(color="#e0e0e0", size=11),
            line=dict(color="#00d2ff", width=3),
            marker=dict(size=10, color="#00d2ff"),
        ))
        fig_line.update_layout(
            title=dict(text="Accuracy by Turn Phase", font=dict(color="#00d2ff", size=16), x=0.5),
            plot_bgcolor="#0a0a1a", paper_bgcolor="#0a0a1a",
            font=dict(color="#e0e0e0"),
            xaxis=dict(gridcolor="#1a2a44", tickangle=-15),
            yaxis=dict(title="Accuracy %", gridcolor="#1a2a44", range=[0, 100]),
            height=320, margin=dict(l=50, r=30, t=50, b=60),
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # ── Turn Detail Grid ────────────────────────────────────────────────
    st.markdown('<div class="section-header">TURN-BY-TURN ACTION COMPARISON</div>', unsafe_allow_html=True)

    for tc in comparisons:
        with st.expander(f"{tc['label']} -- Accuracy: {tc['turn_accuracy']:.0%}", expanded=False):
            for m in tc.get("actor_matches", []):
                icon_map = {"EXACT": "res-treaty", "PARTIAL": "res-trade", "MISS": "res-sanction"}
                label_map = {"EXACT": "MATCH", "PARTIAL": "PARTIAL", "MISS": "MISS"}
                css_class = icon_map.get(m["match"], "res-default")
                label = label_map.get(m["match"], "?")
                st.markdown(
                    f'<div class="resolution {css_class}">'
                    f'<b>[{label}]</b> <b>{m["actor_id"]}</b> -- '
                    f'Sim: <code>{m["sim_action"]}</code> | '
                    f'Real: <code>{m["real_action"]}</code> | '
                    f'Score: {m["score"]:.0%}'
                    f'<br><span style="color:#616161; font-size:11px;">'
                    f'Real: {m["real_description"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Variant Comparison ──────────────────────────────────────────────
    if variants_path.exists():
        st.markdown("---")
        st.markdown('<div class="section-header">BRANCHING SCENARIO VARIANTS</div>', unsafe_allow_html=True)

        with open(variants_path) as f:
            variants = json.load(f)

        if variants:
            vnames = [v["variant"] for v in variants]
            vaccs = [v["accuracy_vs_reality"] * 100 for v in variants]
            vcolors = ["#00d2ff" if v["variant"] == "baseline" else "#b388ff" for v in variants]

            fig_v = go.Figure(go.Bar(
                x=vnames, y=vaccs,
                marker=dict(color=vcolors),
                text=[f"{a:.1f}%" for a in vaccs],
                textposition="outside",
                textfont=dict(color="#e0e0e0", size=12),
            ))
            fig_v.update_layout(
                title=dict(text="Variant Accuracy vs Reality", font=dict(color="#00d2ff", size=16), x=0.5),
                plot_bgcolor="#0a0a1a", paper_bgcolor="#0a0a1a",
                font=dict(color="#e0e0e0"),
                xaxis=dict(gridcolor="#1a2a44", tickangle=-20),
                yaxis=dict(title="Accuracy %", gridcolor="#1a2a44", range=[0, 100]),
                height=350, margin=dict(l=50, r=30, t=50, b=80),
            )
            st.plotly_chart(fig_v, use_container_width=True)

            # Variant details table
            for v in variants:
                top = v["final_leaderboard"][0] if v["final_leaderboard"] else {}
                st.markdown(
                    f'<div style="padding:8px 12px; margin:4px 0; background:#1a1a2e; border-radius:6px;">'
                    f'<b style="color:#00d2ff;">{v["variant"]}</b> -- '
                    f'{v["description"]}<br>'
                    f'<span style="color:#78909c; font-size:12px;">'
                    f'Accuracy: {v["accuracy_vs_reality"]:.1%} | '
                    f'Winner: {top.get("name", "N/A")} ({top.get("final_score", 0):.1f})</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Platform Evaluation ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-header">PLATFORM EVALUATION</div>', unsafe_allow_html=True)

    eval_col1, eval_col2 = st.columns(2)
    with eval_col1:
        st.markdown(
            '<div class="actor-card actor-state" style="border-left-color:#00e676">'
            '<b style="color:#00e676;">STRENGTHS</b><br><br>'
            '<b>Multi-actor complexity:</b> Successfully modeled 8 actors (6 state + 2 non-state) '
            'with distinct doctrines, action spaces, and asymmetric information.<br><br>'
            '<b>Structured action resolution:</b> Deterministic engine produces legible, '
            'traceable outcomes with clear causal chains.<br><br>'
            '<b>Branching scenarios:</b> Doctrine override system enables rapid generation of '
            'counterfactual timelines with different escalation profiles.<br><br>'
            '<b>Backtesting framework:</b> Ground truth comparison with per-actor and per-turn '
            'accuracy scoring provides quantitative evaluation.<br><br>'
            '<b>Data ingestion:</b> World config schema handles the full complexity of the Hormuz '
            'crisis: 8 actors, 8 regions, 5 event-driven turns, asymmetric private briefs.'
            '</div>',
            unsafe_allow_html=True,
        )
    with eval_col2:
        st.markdown(
            '<div class="actor-card actor-nonstate" style="border-left-color:#ff5252">'
            '<b style="color:#ff5252;">GAPS & LIMITATIONS</b><br><br>'
            '<b>Mock agent fidelity (33.8%):</b> Rule-based agents lack the reasoning to '
            'predict context-dependent shifts (e.g. Iran opening then closing the strait).<br><br>'
            '<b>Single-action limitation:</b> Real actors take multiple simultaneous actions per period '
            '(US: blockade + negotiate + mine-clear). Platform allows only 1 per turn.<br><br>'
            '<b>No escalation dynamics:</b> Engine lacks compounding escalation mechanics -- '
            'actions don\'t raise global tension levels that affect future decision-making.<br><br>'
            '<b>Static non-state modeling:</b> Houthi/Shipping actors poorly predicted because '
            'their real behavior was "wait and hold" which mock agents with high escalation bias miss.<br><br>'
            '<b>No economic feedback:</b> Oil price shocks, inflation, trade dependency chains '
            'are not modeled. These drive real-world decision-making.'
            '</div>',
            unsafe_allow_html=True,
        )


# ── App Router ──────────────────────────────────────────────────────────────

def app():
    """Main app with page routing."""
    try:
        with st.sidebar:
            page = st.radio(
                "Navigation",
                ["Simulation Replay", "Hormuz Backtest"],
                index=0,
            )
            st.markdown("---")

        if page == "Simulation Replay":
            main()
        elif page == "Hormuz Backtest":
            backtest_page()
    except Exception as e:
        st.error(f"Application error: {type(e).__name__}: {e}")
        import traceback
        st.code(traceback.format_exc(), language="text")


if __name__ == "__main__":
    app()
