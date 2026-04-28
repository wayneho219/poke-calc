from __future__ import annotations
import plotly.graph_objects as go
from domain.models.stats import StatSet

_FILL_COLOR   = "rgba(99, 144, 240, 0.30)"
_LINE_COLOR   = "#6390F0"
_MEGA_FILL    = "rgba(238, 129, 48, 0.25)"
_MEGA_LINE    = "#EE8130"
_MAX_STAT     = 255


def _stat_values(stats: StatSet) -> list[int]:
    return [stats.hp, stats.attack, stats.defense, stats.sp_attack, stats.sp_defense, stats.speed]


def stat_radar_chart(
    base_stats: StatSet,
    stat_labels: list[str],
    mega_stats: StatSet | None = None,
    mega_label: str = "Mega",
    base_label: str = "",
) -> go.Figure:
    """
    Build a Plotly Scatterpolar radar chart for base stats.
    If mega_stats is provided, overlays the Mega form as a second trace.
    """
    labels_closed = stat_labels + [stat_labels[0]]

    base_vals = _stat_values(base_stats)
    base_vals_closed = base_vals + [base_vals[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=base_vals_closed,
        theta=labels_closed,
        fill="toself",
        name=base_label or "Base",
        line=dict(color=_LINE_COLOR, width=2),
        fillcolor=_FILL_COLOR,
        mode="lines+markers+text",
        text=[str(v) for v in base_vals] + [""],
        textposition="top center",
        textfont=dict(size=11, color=_LINE_COLOR),
    ))

    if mega_stats is not None:
        mega_vals = _stat_values(mega_stats)
        mega_vals_closed = mega_vals + [mega_vals[0]]
        fig.add_trace(go.Scatterpolar(
            r=mega_vals_closed,
            theta=labels_closed,
            fill="toself",
            name=mega_label,
            line=dict(color=_MEGA_LINE, width=2, dash="dot"),
            fillcolor=_MEGA_FILL,
            mode="lines+markers+text",
            text=[str(v) for v in mega_vals] + [""],
            textposition="top center",
            textfont=dict(size=11, color=_MEGA_LINE),
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, _MAX_STAT],
                tickfont=dict(size=8),
                gridcolor="rgba(200,200,200,0.2)",
                linecolor="rgba(200,200,200,0.3)",
            ),
            angularaxis=dict(
                tickfont=dict(size=11),
                gridcolor="rgba(200,200,200,0.2)",
                linecolor="rgba(200,200,200,0.3)",
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=(mega_stats is not None),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        margin=dict(l=50, r=50, t=30, b=30),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
