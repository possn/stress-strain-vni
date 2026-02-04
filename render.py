# render_strain_crf_vni.py
# 16:9 | 60s | Stress–Strain — CRF e papel da VNI
# Coloca na raiz do repo: lung_realistic.png.PNG
# Saída: stress_strain_crf_vni.mp4

import os
os.environ["MPLBACKEND"] = "Agg"

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from PIL import Image


# =========================
# CONFIG
# =========================
OUT = "stress_strain_crf_vni.mp4"
IMG_LUNG = "lung_realistic.png.PNG"

FPS = 20
DURATION_S = 60
TOTAL_FRAMES = int(FPS * DURATION_S)

W, H = 12.8, 7.2       # 16:9
DPI = 120

VT_L = 0.45            # L (450 mL)
SAFE_LINE = 0.20       # linha didáctica "limite seguro" (ajusta se quiseres)

# Segmentos (s)
T1 = 20.0  # saudável
T2 = 20.0  # CRF baixa
T3 = 20.0  # VNI (CRF sobe progressivamente)
assert abs((T1 + T2 + T3) - DURATION_S) < 1e-6

# CRF por cenário
CRF_HEALTHY = 2.5
CRF_LOW = 1.0
CRF_VNI_START = 1.0
CRF_VNI_END = 1.8  # com VNI/PEEP, CRF sobe -> strain desce


# =========================
# HELPERS
# =========================
def smoothstep(x: float) -> float:
    x = np.clip(x, 0.0, 1.0)
    return 0.5 - 0.5*np.cos(np.pi*x)

def breathing_wave(phase01: float) -> float:
    # 0..1 -> seno 0..1 (insp) e 1..0 (exp) suave
    return 0.5 - 0.5*np.cos(2*np.pi*phase01)

def canvas_to_rgb(fig) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()

def fmt_L(x: float) -> str:
    # 2,5 L em PT
    return f"{x:.1f}".replace(".", ",") + " L"

def fmt_strain(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")

def clamp01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


# =========================
# LOAD IMAGE (PNG)
# =========================
if not os.path.exists(IMG_LUNG):
    raise FileNotFoundError(
        f"Não encontrei '{IMG_LUNG}' na raiz do repositório. "
        "Confirma o nome EXACTO (inclui .PNG)."
    )

lung_img = Image.open(IMG_LUNG).convert("RGBA")
lung_arr = np.asarray(lung_img)


# =========================
# FIGURE LAYOUT (3 COLUNAS FIXAS, SEM SOBREPOSIÇÃO)
# =========================
fig = plt.figure(figsize=(W, H), dpi=DPI)

# grelha: [texto | pulmão | barra]
gs = fig.add_gridspec(
    1, 3,
    left=0.05, right=0.97, top=0.90, bottom=0.10,
    wspace=0.12,
    width_ratios=[1.25, 1.45, 0.55]
)

ax_txt = fig.add_subplot(gs[0, 0])
ax_lung = fig.add_subplot(gs[0, 1])
ax_bar = fig.add_subplot(gs[0, 2])

# Fixar eixos como "canvas"
for ax in (ax_txt, ax_lung, ax_bar):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


# =========================
# DRAW: STRAIN BAR
# =========================
def draw_strain_bar(ax, strain_value: float):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Barra vertical (0..0.60 para visual)
    vmin, vmax = 0.00, 0.60
    frac = (strain_value - vmin) / (vmax - vmin)
    frac = clamp01(frac)

    # Geometria
    x0, y0 = 0.35, 0.15
    w, h = 0.30, 0.70

    # zonas (verde / vermelho)
    safe_frac = clamp01((SAFE_LINE - vmin) / (vmax - vmin))

    # fundo total
    ax.add_patch(plt.Rectangle((x0, y0), w, h, fill=False, lw=2.0, edgecolor="#111827"))

    # verde (seguro)
    ax.add_patch(plt.Rectangle((x0, y0), w, h*safe_frac, facecolor="#dcfce7", edgecolor="none", alpha=0.95))
    # vermelho (acima)
    ax.add_patch(plt.Rectangle((x0, y0 + h*safe_frac), w, h*(1-safe_frac), facecolor="#fee2e2", edgecolor="none", alpha=0.95))

    # marcador actual (linha grossa)
    y_mark = y0 + h*frac
    ax.plot([x0-0.08, x0+w+0.08], [y_mark, y_mark], color="#111827", lw=3.2, solid_capstyle="round")

    # título
    ax.text(0.50, 0.92, "STRAIN", ha="center", va="center", fontsize=11.5, weight="bold", color="#111827")

    # limite seguro
    y_safe = y0 + h*safe_frac
    ax.plot([x0-0.06, x0+w+0.06], [y_safe, y_safe], color="#6b7280", lw=2.0, ls="--")
    ax.text(0.50, y_safe + 0.035, "limite\nseguro", ha="center", va="bottom", fontsize=9.2, color="#6b7280")

    # valor numérico
    col = "#166534" if strain_value <= SAFE_LINE else "#b91c1c"
    ax.text(0.50, 0.08, fmt_strain(strain_value), ha="center", va="center", fontsize=12.5, weight="bold", color=col)


# =========================
# DRAW: TEXT PANEL (SEM CAIXAS A COLIDIR)
# =========================
def draw_text_panel(ax, title: str, crf: float, vt: float, strain: float, note_lines: list[str], badge_text: str, badge_color: str):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Título do vídeo (global) fica no suptitle
    ax.text(0.00, 0.92, title, fontsize=13.5, weight="bold", color="#111827", va="top")

    # Definição (sempre no mesmo sítio)
    ax.text(0.00, 0.80, "Definição:", fontsize=11.0, weight="bold", color="#111827")
    ax.text(0.00, 0.74, "strain = ΔV / V0", fontsize=13.5, color="#111827")

    # Substituição numérica (linhas fixas)
    ax.text(0.00, 0.62, f"V0 (≈ CRF) = {fmt_L(crf)}", fontsize=12.0, color="#111827")
    ax.text(0.00, 0.55, f"ΔV (VT)   = {fmt_L(vt)} (450 mL)", fontsize=12.0, color="#111827")

    col = "#166534" if strain <= SAFE_LINE else "#b91c1c"
    ax.text(0.00, 0.46, f"strain = {fmt_strain(strain)}", fontsize=14.5, weight="bold", color=col)

    # Nota didáctica (lista curta, sem caixas grandes)
    ax.text(0.00, 0.34, "Relação-chave (didáctica):", fontsize=11.0, weight="bold", color="#111827")
    y = 0.29
    for line in note_lines:
        ax.text(0.02, y, f"• {line}", fontsize=10.4, color="#111827", va="top")
        y -= 0.06

    # Badge final (uma única caixa, longe do resto)
    ax.text(
        0.00, 0.06, badge_text,
        fontsize=11.2, weight="bold", color="#111827",
        bbox=dict(boxstyle="round,pad=0.35", facecolor=badge_color, edgecolor="none", alpha=0.95),
        va="bottom"
    )


# =========================
# DRAW: LUNG (ANIMAÇÃO SEM SOBREPOSIÇÃO)
# =========================
def draw_lung(ax, strain_now: float, phase01: float, crack: bool = False):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # escala do pulmão: depende do "volume relativo" (tidal) e strain (para dramatizar)
    # respiração: 0..1 -> variação +/- pequena
    breath = breathing_wave(phase01)  # 0..1
    # base scale
    base = 0.72
    # amplitude do "pulsar"
    amp = 0.06 + 0.12*clamp01(strain_now/0.60)
    scale = base + amp*(breath - 0.5)

    # posição fixa (centro)
    cx, cy = 0.50, 0.54
    w = 0.72 * scale
    h = 0.80 * scale

    # desenhar imagem
    ax.imshow(
        lung_arr,
        extent=(cx - w/2, cx + w/2, cy - h/2, cy + h/2),
        interpolation="lanczos",
        zorder=2
    )

    # “fissura” didáctica (só quando crack=True)
    if crack:
        ax.plot([0.40, 0.62], [0.62, 0.40], color="#111827", lw=4.0, alpha=0.85, zorder=3)
        ax.plot([0.46, 0.58], [0.58, 0.46], color="#111827", lw=3.2, alpha=0.85, zorder=3)

    # legenda curta por baixo do pulmão (sem caixas)
    ax.text(0.50, 0.10, "Pulmão (ilustração) — deformação aumenta com strain",
            ha="center", va="center", fontsize=9.5, color="#6b7280")


# =========================
# MAIN RENDER
# =========================
writer = imageio.get_writer(
    OUT,
    fps=FPS,
    codec="libx264",
    macro_block_size=1,
    ffmpeg_params=["-preset", "ultrafast", "-crf", "22"]
)

for i in range(TOTAL_FRAMES):
    t = i / FPS

    # fase respiratória (0..1) contínua
    phase01 = (t % 4.0) / 4.0  # ciclo 4s

    # determinar segmento
    if t < T1:
        seg = 1
        crf = CRF_HEALTHY
        vt = VT_L
        strain = vt / crf
        crack = False
        title = "Pulmão saudável"
        notes = [
            "CRF alta → para o mesmo VT, strain baixo",
            "stress (tensão) sobe quando strain sobe",
            "risco mecânico aumenta quando CRF diminui"
        ]
        badge = "CRF alta → strain baixo (reversível/seguro)"
        badge_col = "#dcfce7"

    elif t < T1 + T2:
        seg = 2
        crf = CRF_LOW
        vt = VT_L
        strain = vt / crf
        crack = True if strain > 0.35 else False
        title = "Pulmão com CRF baixa"
        notes = [
            "CRF baixa → V0 pequeno → strain sobe",
            "mesmo VT → mais distensão relativa",
            "lesão mecânica provável se persistir"
        ]
        badge = "CRF baixa → strain excessivo (lesão provável)"
        badge_col = "#fee2e2"

    else:
        seg = 3
        # VNI: CRF sobe progressivamente (recrutamento/PEEP)
        x = (t - (T1 + T2)) / T3
        crf = CRF_VNI_START + (CRF_VNI_END - CRF_VNI_START) * smoothstep(x)
        vt = VT_L
        strain = vt / crf
        crack = False
        title = "VNI: porquê ajuda?"
        notes = [
            "VNI/PEEP ↑ → recruta alvéolos → CRF ↑",
            "V0 ↑ → strain ↓ para o mesmo VT",
            "↓ stress/strain → ↓ risco de VILI"
        ]
        badge = "VNI aumenta CRF → reduz strain para o mesmo VT"
        badge_col = "#dcfce7"

    # desenhar frame
    fig.clf()
    fig.set_size_inches(W, H)

    gs = fig.add_gridspec(
        1, 3,
        left=0.05, right=0.97, top=0.90, bottom=0.10,
        wspace=0.12,
        width_ratios=[1.25, 1.45, 0.55]
    )
    ax_txt = fig.add_subplot(gs[0, 0])
    ax_lung = fig.add_subplot(gs[0, 1])
    ax_bar = fig.add_subplot(gs[0, 2])

    for ax in (ax_txt, ax_lung, ax_bar):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

    fig.suptitle("STRESS–STRAIN — CRF e papel da VNI", fontsize=18, weight="bold", y=0.965)

    # Texto
    draw_text_panel(
        ax_txt,
        title=title,
        crf=crf,
        vt=vt,
        strain=strain,
        note_lines=notes,
        badge_text=badge,
        badge_color=badge_col
    )

    # Pulmão
    draw_lung(ax_lung, strain_now=strain, phase01=phase01, crack=crack)

    # Barra
    draw_strain_bar(ax_bar, strain_value=strain)

    writer.append_data(canvas_to_rgb(fig))

writer.close()
print("OK ->", OUT)
