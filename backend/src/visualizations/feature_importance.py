import plotly.graph_objects as go


def plot_feature_importance(importance_df, save_path = None):
    fig = go.Figure(data = go.Bar(
        y = importance_df["Feature"],
        x = importance_df["Importance"],
        orientation = "h",
        marker_color = "rgb(255, 75, 75)",
    ))

    fig.update_layout(
        title = "Random Forest — Feature Importance",
        xaxis_title = "Importance",
        yaxis = dict(autorange = "reversed"),
        width = 800, 
        height = 500,
        template = "plotly_dark",
    )

    if save_path:
        fig.write_html(save_path)
    fig.show()
    return fig