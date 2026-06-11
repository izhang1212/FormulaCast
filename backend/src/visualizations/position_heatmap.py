import numpy as np
import plotly.graph_objects as go


def plot_position_heatmap(position_probs, circuit_name = "", save_path = None):
    probs = position_probs.drop(columns=["P0"], errors="ignore")
    display_cols = [f"P{i}" for i in range(1, 21) if f"P{i}" in probs.columns]
    probs = probs[display_cols]

    fig = go.Figure(data=go.Heatmap(
        z = probs.values,
        x = [col.replace("P", "") for col in probs.columns],
        y = probs.index,
        colorscale = "YlOrRd",
        text = np.round(probs.values * 100, 1),
        texttemplate = "%{text}%",
        textfont = {"size": 9},
        colorbar = dict(title = "Probability"),
    ))

    fig.update_layout(
        title = f"Finishing Position Probabilities — {circuit_name}",
        xaxis_title = "Finishing Position",
        yaxis_title = "Driver",
        yaxis = dict(autorange = "reversed"),
        width = 1000, 
        height = 600,
        template = "plotly_dark",
    )

    if save_path:
        fig.write_html(save_path)
    fig.show()
    return fig