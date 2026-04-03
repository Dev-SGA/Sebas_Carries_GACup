import streamlit as st
import matplotlib.pyplot as plt
from mplsoccer import Pitch
import pandas as pd
import numpy as np
from PIL import Image
from io import BytesIO
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
import math

# Coordenadas das carregadas
coords_by_match = {
    'Vs Los Angeles': [
        (75.96, 2.26), (111.03, 20.88),
        (53.02, 73.41), (99.90, 76.07)
    ],
    'Vs Slavia Praha': [
        (97.57, 3.93), (115.36, 19.22),
        (92.91, 10.41), (105.05, 22.88),
        (98.23, 26.37), (116.69, 24.54)
    ],
    'Vs Sockers': [
        (62.99, 70.42), (112.36, 69.09)
    ]
}

st.set_page_config(layout="wide", page_title="Carried Map Dashboard")
st.title("Progressive Carries Dashboard")

# ==========================
# Configuration
# ==========================
FINAL_THIRD_LINE_X = 80 

MATCHES = ["Vs Los Angeles", "Vs Slavia Praha", "Vs Sockers", "All Matches"]

st.sidebar.header("Seleção de Partida")
selected_match = st.sidebar.radio("Escolha o jogo", MATCHES, index=0)

def calculate_distance(x1, y1, x2, y2):
    # Cálculo da hipotenusa para saber a distância real da carregada
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def build_df(coords: list[tuple[float, float]]) -> pd.DataFrame:
    carregadas = []
    for i in range(0, len(coords), 2):
        start = coords[i]
        end = coords[i + 1]
        dist = calculate_distance(start[0], start[1], end[0], end[1])
        
        carregadas.append(
            {
                "numero": i // 2 + 1,
                "x_start": float(start[0]),
                "y_start": float(start[1]),
                "x_end": float(end[0]),
                "y_end": float(end[1]),
                "distancia": dist
            }
        )

    df = pd.DataFrame(carregadas)
    
    if not df.empty:
        df["in_final_third"] = df["x_end"] >= FINAL_THIRD_LINE_X
        df["to_box"] = df["x_end"] >= 100
    else:
        df = pd.DataFrame(columns=["numero", "x_start", "y_start", "x_end", "y_end", "distancia", "in_final_third", "to_box"])
        
    return df

def compute_stats(df: pd.DataFrame) -> dict:
    total_carregadas = len(df)
    distancia_total = df["distancia"].sum() if not df.empty else 0
    final_third_total = int(df["in_final_third"].sum()) if not df.empty else 0
    box_total = int(df["to_box"].sum()) if not df.empty else 0

    return {
        "total_carregadas": total_carregadas,
        "distancia_total": round(distancia_total, 1),
        "final_third_total": final_third_total,
        "box_total": box_total,
    }

def draw_carry_map(df: pd.DataFrame):
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#f5f5f5", line_color="#4a4a4a")
    fig, ax = pitch.draw(figsize=(6.4, 4.2))
    fig.set_dpi(100)

    ax.axvline(x=FINAL_THIRD_LINE_X, color="#FFD54F", linewidth=1.2, alpha=0.25)

    purple_color = (0.5, 0.0, 0.5, 0.75) 

    for _, row in df.iterrows():
        pitch.arrows(
            row["x_start"], row["y_start"],
            row["x_end"], row["y_end"],
            color=purple_color, width=1.55,
            headwidth=2.25, headlength=2.25, ax=ax,
        )

    ax.set_title(f"Mapa de Carregadas - {selected_match}", fontsize=12)

    legend_elements = [Line2D([0], [0], color=purple_color, lw=2.5, label="Carregadas (Progressive Carries)")]
    ax.legend(handles=legend_elements, loc="upper left", bbox_to_anchor=(0.01, 0.99), 
              frameon=True, facecolor="white", fontsize="x-small")

    arrow = FancyArrowPatch((0.45, 0.05), (0.55, 0.05), transform=fig.transFigure,
                             arrowstyle="-|>", mutation_scale=15, linewidth=2, color="#333333")
    fig.patches.append(arrow)
    fig.text(0.5, 0.02, "Direção do Ataque", ha="center", va="center", fontsize=9, color="#333333")

    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img = Image.open(buf)
    plt.close(fig)
    return img

# Lógica de seleção
if selected_match == "All Matches":
    all_coords = []
    for match in MATCHES[:-1]:
        all_coords.extend(coords_by_match[match])
    coords = all_coords
else:
    coords = coords_by_match[selected_match]

df = build_df(coords)
stats = compute_stats(df)

# ==========================
# Dashboard layout
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
    
    # Média por carregada
    if stats["total_carregadas"] > 0:
        media = round(stats["distancia_total"] / stats["total_carregadas"], 1)
        st.info(f"Média de {media} metros por carregada.")

with col_map:
    st.subheader("Visualização")
    img = draw_carry_map(df)
    st.image(img, width=620)
