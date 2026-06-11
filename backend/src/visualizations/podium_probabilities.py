import plotly.graph_objects as go
import plotly.express as px


def plot_podium_probabilities(summary, circuit_name = "", save_path = None):
    
    top = summary.nlargest(10, "PodiumProb")

    fig = go.Figure(data = go.Bar(
        y = top["Driver"],
        x = top["PodiumProb"],
        orientation = "h",
        text = [f"{v:.1f}%" for v in top["PodiumProb"]],
        textposition = "outside",
        marker_color = px.colors.sequential.Reds_r[:len(top)],
    ))

    fig.update_layout(
        title = f"Podium Probability — {circuit_name}",
        xaxis_title = "Probability (%)",
        yaxis = dict(autorange="reversed"),
        width = 800, 
        height = 500,
        template = "plotly_dark",
    )

    if save_path:
        fig.write_html(save_path)
    fig.show()
    return fig