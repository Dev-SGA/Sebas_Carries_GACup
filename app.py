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

st.set_page_config(layout="wide", page_title="Carried Map Dashboard")
st.title("Progressive Carries Dashboard")
st.caption("Clique na bolinha no início da carregada para ver o vídeo (se houver).")

# ==========================
# Configuration
# ==========================
FINAL_THIRD_LINE_X = 80

# ==========================
# DATA
# Cada item:
# (x_start, y_start, x_end, y_end, video)
# ==========================
carries_by_match = {
    "Vs Los Angeles": [
        (75.96, 2.26, 111.03, 20.88, "videos/carry_la_1.mp4"),
        (53.02, 73.41, 99.90, 76.07, None),
    ],
    "Vs Slavia Praha": [
        (97.57, 3.93, 115.36, 19.22, None),
        (92.91, 10.41, 105.05, 22.88, "videos/carry_slavia_2.mp4"),
        (98.23, 26.37, 116.69, 24.54, None),
    ],
    "Vs Sockers": [
        (62.99, 70.42, 112.36, 69.09, "videos/carry_sockers_1.mp4"),
    ],
}

MATCHES = ["Vs Los Angeles", "Vs Slavia Praha", "Vs Sockers", "All Matches"]

# ==========================
# Helpers
# ==========================
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def has_video_value(v) -> bool:
    return pd.notna(v) and str(v).strip() != ""

def build_df(events: list[tuple]) -> pd.DataFrame:
    carregadas = []

    for i, event in enumerate(events, start=1):
        x_start, y_start, x_end, y_end, video = event
        dist = calculate_distance(x_start, y_start, x_end, y_end)

        carregadas.append(
            {
                "numero": i,
                "x_start": float(x_start),
                "y_start": float(y_start),
                "x_end": float(x_end),
                "y_end": float(y_end),
                "distancia": dist,
                "video": video,
            }
        )

    df = pd.DataFrame(carregadas)

    if not df.empty:
        df["in_final_third"] = df["x_end"] >= FINAL_THIRD_LINE_X
        df["to_box"] = df["x_end"] >= 100
    else:
        df = pd.DataFrame(
            columns=[
                "numero", "x_start", "y_start", "x_end", "y_end",
                "distancia", "video", "in_final_third", "to_box"
            ]
        )

    return df

def compute_stats(df: pd.DataFrame) -> dict:
    total_carregadas = len(df)
    distancia_total = df["distancia"].sum() if not df.empty else 0
    final_third_total = int(df["in_final_third"].sum()) if not df.empty else 0
    box_total = int(df["to_box"].sum()) if not df.empty else 0
    com_video = int(df["video"].apply(has_video_value).sum()) if not df.empty else 0

    return {
        "total_carregadas": total_carregadas,
        "distancia_total": round(distancia_total, 1),
        "final_third_total": final_third_total,
        "box_total": box_total,
        "com_video": com_video,
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

        # Anel dourado se houver vídeo
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

        # Bolinha principal clicável
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
        Line2D([0], [0], color=carry_color, lw=2.5, label="Carregadas"),
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
        0.5, 0.02, "Direção do Ataque",
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
st.sidebar.header("Seleção de Partida")
selected_match = st.sidebar.radio("Escolha o jogo", MATCHES, index=0)

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
    st.subheader("Estatísticas")

    c1, c2 = st.columns(2)
    c1.metric("Total Carregadas", stats["total_carregadas"])
    c2.metric("Distância Total", f"{stats['distancia_total']}m")

    st.divider()

    st.subheader("Avanço")
    c3, c4 = st.columns(2)
    c3.metric("No Terço Final", stats["final_third_total"])
    c4.metric("Até a Área", stats["box_total"])

    st.metric("Com Vídeo", stats["com_video"])

    if stats["total_carregadas"] > 0:
        media = round(stats["distancia_total"] / stats["total_carregadas"], 1)
        st.info(f"Média de {media} metros por carregada.")

with col_map:
    st.subheader("Visualização")

    img_obj, ax, fig = draw_carry_map(df, title=f"Mapa de Carregadas - {selected_match}")
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
    st.subheader("Vídeo")

    if selected_carry is None:
        st.info("Clique na bolinha no início da carregada para ver o vídeo (se houver).")
    else:
        st.success(f"Carregada selecionada: #{int(selected_carry['numero'])}")
        st.write(
            f"Início: ({selected_carry['x_start']:.2f}, {selected_carry['y_start']:.2f})  \n"
            f"Fim: ({selected_carry['x_end']:.2f}, {selected_carry['y_end']:.2f})  \n"
            f"Distância: {selected_carry['distancia']:.2f} m"
        )

        if has_video_value(selected_carry["video"]):
            try:
                st.video(selected_carry["video"])
            except Exception:
                st.error(f"Arquivo de vídeo não encontrado: {selected_carry['video']}")
        else:
            st.warning("Não há vídeo carregado para esta carregada.")
