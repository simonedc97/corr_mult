
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative
from io import BytesIO

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(layout="wide")

# --------------------------------------------------
# Load Correlation Data - E7X only
# --------------------------------------------------
@st.cache_data
def load_corr_data(path):
    df = pd.read_excel(path, sheet_name="Correlation Clean")
    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
    df = df.set_index(df.columns[0]).sort_index()
    return df


corrE7X = load_corr_data("corrE7X.xlsx")


# --------------------------------------------------
# Load E7X Legend
# --------------------------------------------------
@st.cache_data
def load_legenda_sheet():
    return pd.read_excel(
        "Legenda.xlsx",
        sheet_name="E7X",
        usecols="A:C"
    )


legenda_main = load_legenda_sheet()


# ==================================================
# CORRELATION - E7X
# ==================================================

df = corrE7X.copy()

chart_title = "E7X Dynamic Asset Allocation vs Funds"

# --------------------------------------------------
# Date range selector
# --------------------------------------------------
st.sidebar.title("Controls")

st.sidebar.subheader("Date range")

start_date, end_date = st.sidebar.date_input(
    "Select start and end date",
    value=(df.index.min().date(), df.index.max().date()),
    min_value=df.index.min().date(),
    max_value=df.index.max().date()
)

df = df.loc[
    pd.to_datetime(start_date):pd.to_datetime(end_date)
]


# --------------------------------------------------
# Series selector
# --------------------------------------------------
st.sidebar.subheader("Series")

selected_series = st.sidebar.multiselect(
    "Select series",
    options=df.columns.tolist(),
    default=df.columns.tolist()
)

if not selected_series:
    st.warning("Please select at least one series.")
    st.stop()


# --------------------------------------------------
# Color map
# --------------------------------------------------
palette = qualitative.Plotly

color_map = {
    s: palette[i % len(palette)]
    for i, s in enumerate(selected_series)
}


# --------------------------------------------------
# Title
# --------------------------------------------------
st.title(chart_title)


# ==================================================
# 1. CORRELATION TIME SERIES
# ==================================================

st.subheader("Correlation Time Series")

fig_ts = go.Figure()

for col in selected_series:
    fig_ts.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col] * 100,
            mode="lines",
            name=col,
            line=dict(color=color_map[col]),
            hovertemplate="%{y:.2f}%<extra></extra>"
        )
    )

fig_ts.update_layout(
    height=600,
    hovermode="x unified",
    template="plotly_white",
    yaxis=dict(ticksuffix="%"),
    xaxis_title="Date",
    yaxis_title="Correlation"
)

st.plotly_chart(fig_ts, use_container_width=True)


# --------------------------------------------------
# Download Time Series Data
# --------------------------------------------------
df_download = df[selected_series] * 100

output = BytesIO()

with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_download.to_excel(
        writer,
        sheet_name="Time Series Data"
    )

st.download_button(
    label="📥 Download time series data as Excel",
    data=output.getvalue(),
    file_name="time_series_data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="download_time_series"
)


# ==================================================
# 2. CORRELATION RADAR
# ==================================================

st.subheader("Correlation Radar")

snapshot_date = df.index.max()

snapshot = df.loc[snapshot_date, selected_series]

mean_corr = df[selected_series].mean()

fig_radar = go.Figure()

# End date
fig_radar.add_trace(
    go.Scatterpolar(
        r=snapshot.values * 100,
        theta=snapshot.index,
        name=f"End date ({snapshot_date.date()})",
        line=dict(width=3)
    )
)

# Period mean
fig_radar.add_trace(
    go.Scatterpolar(
        r=mean_corr.values * 100,
        theta=mean_corr.index,
        name="Period mean",
        line=dict(dash="dot")
    )
)

fig_radar.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[-100, 100],
            ticksuffix="%"
        )
    ),
    template="plotly_white",
    height=650
)

st.plotly_chart(fig_radar, use_container_width=True)


# ==================================================
# 3. SUMMARY STATISTICS
# ==================================================

# Ticker -> Name mapping
ticker_to_name = dict(
    zip(
        legenda_main["Ticker"],
        legenda_main["Name"]
    )
)

st.subheader("Summary statistics")

stats_df = pd.DataFrame(index=selected_series)

# Name
stats_df.insert(
    0,
    "Name",
    [ticker_to_name.get(t, "") for t in selected_series]
)

# Statistics
stats_df["Mean (%)"] = df[selected_series].mean() * 100

stats_df["Min (%)"] = df[selected_series].min() * 100

stats_df["Min Date"] = [
    df[col][df[col] == df[col].min()].index.max()
    for col in selected_series
]

stats_df["Max (%)"] = df[selected_series].max() * 100

stats_df["Max Date"] = [
    df[col][df[col] == df[col].max()].index.max()
    for col in selected_series
]


# --------------------------------------------------
# Date formatting
# --------------------------------------------------
stats_df["Min Date"] = pd.to_datetime(
    stats_df["Min Date"]
).dt.strftime("%d/%m/%Y")

stats_df["Max Date"] = pd.to_datetime(
    stats_df["Max Date"]
).dt.strftime("%d/%m/%Y")


# --------------------------------------------------
# Display statistics
# --------------------------------------------------
st.dataframe(
    stats_df.style.format({
        "Mean (%)": "{:.2f}%",
        "Min (%)": "{:.2f}%",
        "Max (%)": "{:.2f}%"
    }),
    use_container_width=True
)


# --------------------------------------------------
# Download Summary Statistics
# --------------------------------------------------
output = BytesIO()

with pd.ExcelWriter(output, engine="openpyxl") as writer:
    stats_df.to_excel(
        writer,
        sheet_name="Summary Stats"
    )

st.download_button(
    label="📥 Download summary statistics as Excel",
    data=output.getvalue(),
    file_name="summary_statistics.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="download_summary_stats"
)
