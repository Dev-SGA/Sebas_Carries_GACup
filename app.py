import streamlit as st
import matplotlib.pyplot as plt
from mplsoccer import Pitch
import pandas as pd
import numpy as np
from PIL import Image
from io import BytesIO
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
from streamlit_image_coordinates import streamlit_image_coordinates
import math
import socceraction.xthreat as xthreat

st.set_page_config(layout="wide", page_title="Carry Map Dashboard")
st.title("Progressive Carries Dashboard")
st.caption("Click on the dot at the start of the carry to view the video (if available).")

# ==========================
# Configuration
# ==========================
FINAL_THIRD_LINE_X = 80

# StatsBomb pitch box approximation
BOX_X_MIN = 102
BOX_Y_MIN = 18
BOX_Y_MAX = 62

PITCH_LENGTH = 120
PITCH_WIDTH = 80

XT_MODEL_URL = "https://karun.in/blog/data/open_xt_12x8_v1.json"

# ==========================
# DATA
# Each item:
# (x_start, y_start, x_end, y_end, video)
# ==========================
carries_by_match = {
    "Vs Los Angeles": [
        (75.96, 2.26, 111.03, 20.88, "videos/2 - LA.mp4"),
        (53.02, 73.41, 99.90, 76.07, "videos/1 - LA.mp4"),
    ],
    "Vs Slavia Praha": [
        (97.57, 3.93, 115.36, 19.22, "videos/1 - SP.mp4"),
        (92.91, 10.41, 105.05, 22.88, "videos/3 - SP.mp4"),
        (98.23, 26.37, 116.69, 24.54, "videos/2 - SP.mp4"),
    ],
    "Vs Sockers": [
        (62.99, 70.42, 112.36, 69.09, "videos/1 - SK.mp4"),
    ],
}

MATCHES = ["Vs Los Angeles", "Vs Slavia Praha", "Vs Sockers", "All Matches"]

# ==========================
# Load xT model
# ==========================
@st.cache_resource
def load_xt_model():
    return xthreat.load_model(XT_MODEL_URL)

xt_model = load_xt_model()
xt_grid = xt_model.xT

# ==========================
# Helpers
# ==========================
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def has_video_value(v) -> bool:
    return pd.notna(v) and str(v).strip() != ""

def is_in_box(x, y) -> bool:
    return x >= BOX_X_MIN and BOX_Y_MIN <= y <= BOX_Y_MAX

def get_xt_value(x: float, y: float, grid: np.ndarray) -> float:
    rows, cols = grid.shape

    x = min(max(float(x), 0), PITCH_LENGTH - 1e-6)
    y = min(max(float(y), 0), PITCH_WIDTH - 1e-6)

    col = min(int((x / PITCH_LENGTH) * cols), cols - 1)
    row = min(int((y / PITCH_WIDTH) * rows), rows - 1)

    return float(grid[row, col])

def compute_carry_xt(x_start: float, y_start: float, x_end: float, y_end: float, grid: np.ndarray) -> float:
    xt_start = get_xt_value(x_start, y_start, grid)
    xt_end = get_xt_value(x_end, y_end, grid)
    return xt_end - xt_start

def build_df(events: list[tuple]) -> pd.DataFrame:
    carries = []

    for i, event in enumerate(events, start=1):
        x_start, y_start, x_end, y_end, video = event
        dist = calculate_distance(x_start, y_start, x_end, y_end)
        xt_value = compute_carry_xt(x_start, y_start, x_end, y_end, xt_grid)

        carries.append(
            {
                "number": i,
                "x_start": float(x_start),
                "y_start": float(y_start),
                "x_end": float(x_end),
                "y_end": float(y_end),
                "distance": dist,
                "video": video,
                "xT": xt_value,
            }
        )

    df = pd.DataFrame(carries)

    if not df.empty:
        df["to_final_third"] = (
            (df["x_start"] < FINAL_THIRD_LINE_X) &
            (df["x_end"] >= FINAL_THIRD_LINE_X)
        )

        df["into_box"] = df.apply(
            lambda row: (not is_in_box(row["x_start"], row["y_start"])) and is_in_box(row["x_end"], row["y_end"]),
            axis=1
        )
    else:
        df = pd.DataFrame(
            columns=[
                "number", "x_start", "y_start", "x_end", "y_end",
                "distance", "video", "xT", "to_final_third", "into_box"
            ]
        )

    return df

def compute_stats(df: pd.DataFrame) -> dict:
    total_carries = len(df)
    total_distance = df["distance"].sum() if not df.empty else 0
    total_xt = df["xT"].sum() if not df.empty else 0
    to_final_third = int(df["to_final_third"].sum()) if not df.empty else 0
    into_box = int(df["into_box"].sum()) if not df.empty else 0
    avg_distance = (total_distance / total_carries) if total_carries > 0 else 0
    avg_xt = (total_xt / total_carries) if total_carries > 0 else 0

    return {
        "total_carries": total_carries,
        "total_distance": round(total_distance, 1),
        "total_xt": round(total_xt, 3),
        "to_final_third": to_final_third,
        "into_box": into_box,
        "avg_distance": round(avg_distance, 1),
        "avg_xt": round(avg_xt, 3),
    }

def draw_carry_map(df: pd.DataFrame, title: str):
    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color="#f5f5f5",
        line_color="#4a4a4a"
    )
    fig, ax = pitch.draw(figsize=(7.9, 5.3))
    fig.set_dpi(110)

    ax.axvline(x=FINAL_THIRD_LINE_X, color="#FFD54F", linewidth=1.2, alpha=0.25)

    carry_color = (0.5, 0.0, 0.5, 0.75)
    START_DOT_SIZE = 45

    for _, row in df.iterrows():
        has_vid = has_video_value(row["video"])

        pitch.arrows(
            row["x_start"], row["y_start"],
            row["x_end"], row["y_end"],
            color=carry_color,
            width=1.55,
            headwidth=2.25,
            headlength=2.25,
            ax=ax,
            zorder=3,
        )

        if has_vid:
            pitch.scatter(
                row["x_start"], row["y_start"],
                s=95,
                marker="o",
                facecolors="none",
                edgecolors="#FFD54F",
                linewidths=2.0,
                ax=ax,
                zorder=4,
            )

        pitch.scatter(
            row["x_start"], row["y_start"],
            s=START_DOT_SIZE,
            marker="o",
            color=carry_color,
            edgecolors="white",
            linewidths=0.8,
            ax=ax,
            zorder=5,
        )

    ax.set_title(title, fontsize=12)

    legend_elements = [
        Line2D([0], [0], color=carry_color, lw=2.5, label="Carries"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor="gray", markeredgecolor="white",
               markersize=6, label="Start point (click)"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor="gray", markeredgecolor="#FFD54F",
               markeredgewidth=2, markersize=7, label="Has video"),
    ]

    legend = ax.legend(
        handles=legend_elements,
        loc="upper left",
        bbox_to_anchor=(0.01, 0.99),
        frameon=True,
        facecolor="white",
        edgecolor="#cccccc",
        shadow=False,
        fontsize="x-small",
        labelspacing=0.5,
        borderpad=0.5,
    )
    legend.get_frame().set_alpha(1.0)

    arrow = FancyArrowPatch(
        (0.45, 0.05), (0.55, 0.05),
        transform=fig.transFigure,
        arrowstyle="-|>",
        mutation_scale=15,
        linewidth=2,
        color="#333333",
    )
    fig.patches.append(arrow)
    fig.text(
        0.5, 0.02, "Attack Direction",
        ha="center", va="center",
        fontsize=9, color="#333333"
    )

    fig.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    buf.seek(0)
    img_obj = Image.open(buf)
    return img_obj, ax, fig

# ==========================
# Sidebar
# ==========================
st.sidebar.header("Match Selection")
selected_match = st.sidebar.radio("Choose the match", MATCHES, index=0)

# ==========================
# Data selection
# ==========================
if selected_match == "All Matches":
    all_events = []
    for match in MATCHES[:-1]:
        all_events.extend(carries_by_match[match])
    selected_events = all_events
else:
    selected_events = carries_by_match[selected_match]

df = build_df(selected_events)
stats = compute_stats(df)

# ==========================
# Layout
# ==========================
col_stats, col_map = st.columns([1, 2], gap="large")

with col_stats:
    st.subheader("Statistics")

    c1, c2 = st.columns(2)
    c1.metric("Total Carries", stats["total_carries"])
    c2.metric("Total Distance", f"{stats['total_distance']} m")

    st.divider()

    c3, c4 = st.columns(2)
    c3.metric("Total xT", f"{stats['total_xt']:.3f}")
    c4.metric("Avg xT / Carry", f"{stats['avg_xt']:.3f}")

    st.divider()

    st.subheader("Progression")
    c5, c6, c7 = st.columns(3)
    c5.metric("To Final Third", stats["to_final_third"])
    c6.metric("Into the Box", stats["into_box"])
    c7.metric("Avg Carry Distance", f"{stats['avg_distance']} m")

with col_map:
    st.subheader("Carry Map")

    img_obj, ax, fig = draw_carry_map(df, title=f"Carry Map - {selected_match}")
    click = streamlit_image_coordinates(img_obj, width=780)

    selected_carry = None

    if click is not None:
        real_w, real_h = img_obj.size
        disp_w, disp_h = click["width"], click["height"]

        pixel_x = click["x"] * (real_w / disp_w)
        pixel_y = click["y"] * (real_h / disp_h)

        mpl_pixel_y = real_h - pixel_y
        coords_clicked = ax.transData.inverted().transform((pixel_x, mpl_pixel_y))
        field_x, field_y = coords_clicked[0], coords_clicked[1]

        df_sel = df.copy()
        df_sel["dist"] = np.sqrt(
            (df_sel["x_start"] - field_x) ** 2 +
            (df_sel["y_start"] - field_y) ** 2
        )

        RADIUS = 7.0
        candidates = df_sel[df_sel["dist"] < RADIUS]

        if not candidates.empty:
            selected_carry = candidates.loc[candidates["dist"].idxmin()]

    plt.close(fig)

    st.divider()
    st.subheader("Video")

    if selected_carry is None:
        st.info("Click on the dot at the start of the carry to view the video (if available).")
    else:
        st.success(f"Selected carry: #{int(selected_carry['number'])}")
        st.write(
            f"Start: ({selected_carry['x_start']:.2f}, {selected_carry['y_start']:.2f})  \n"
            f"End: ({selected_carry['x_end']:.2f}, {selected_carry['y_end']:.2f})  \n"
            f"Distance: {selected_carry['distance']:.2f} m  \n"
            f"xT: {selected_carry['xT']:.3f}"
        )

        if has_video_value(selected_carry["video"]):
            try:
                st.video(selected_carry["video"])
            except Exception:
                st.error(f"Video file not found: {selected_carry['video']}")
        else:
            st.warning("No video available for this carry.")

# ==========================
# Optional table
# ==========================
with st.expander("Show carry data"):
    st.dataframe(
        df[["number", "x_start", "y_start", "x_end", "y_end", "distance", "xT", "to_final_third", "into_box"]],
        use_container_width=True
    )
