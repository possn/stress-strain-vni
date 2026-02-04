# render_strain_crf_vni.py
# 16:9 | 60s | Stress–Strain — CRF e papel da VNI
# Requisitos na raiz do repo:
#   - lung_realistic.png.PNG
# Saída:
#   - stress_strain_crf_vni.mp4

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
SAFE_LINE = 0.25       # limite didático “seguro” para strain

# Segmentos (s)
T1 = 20.0  # saudável
T2 = 20.0  # CRF baixa
T3 = 20.0  # VNI (CRF sobe progressivamente)
assert abs((T1 + T2 + T3) - DURATION_S) < 1e-6

# CRF por cenário
CRF_HEALTHY = 2.5
CRF_LOW = 1.0
CRF_VNI_START = 1.0
CRF_VNI_END = 1.8


# =========================
# HELPERS
# =========================
def smoothstep(x: float) -> float:
    x = np.clip(x, 0.0, 1.0)
    return 0.5 - 0.5*np.cos(np.pi*x)

def breathing_wave(phase01: float) -> float:
    """0..1 -> 0..1..0 (inspira e expira suave)"""
    return 0.5 - 0.5*np.cos(2*np.pi*phase01)

def canvas_to_rgb(fig) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()

def fmt_L(x: float) -> str:
    return f"{x:.1f}".replace(".", ",") + " L"

def fmt_strain(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")

def clamp01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


# =========================
# LOAD IMAGE
# =========================
if not os.path.exists(IMG_LUNG):
    raise FileNotFoundError(
        f"Não encontrei '{IMG_LUNG}' na raiz do repositório. "
        "Confirma o nome EXACTO (inclui .PNG)."
    )

lung_img = Image.open(IMG_LUNG).convert("RGBA")
lung_arr = np.asarray(lung_img)


# =========================
# DRAW: STRAIN BAR (ANIMADA)
# =========================
def draw_strain_bar(ax, strain_now: float, strain_peak: float):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Escala visual da barra
    vmin, vmax = 0.00, 0.60
    frac_now = clamp01((strain_now - vmin) / (vmax - vmin))
    frac_peak = clamp01((strain_peak - vmin) / (vmax - vmin))

    # Geometria
    x0, y0 = 0.35, 0.15
    w, h = 0.30, 0.70

    safe_frac = clamp01((SAFE_LINE - vmin) / (vmax - vmin))
    y_safe = y0 + h*safe_frac

    # moldura
    ax.add_patch(plt.Rectangle((x0, y0), w, h, fill=False, lw=2.0, edgecolor="#111827"))

    # zonas (seguro/excesso)
    ax.add_patch(plt.Rectangle((x0, y0), w, h*safe_frac, facecolor="#dcfce7", edgecolor="none", alpha=0.95))
    ax.add_patch(plt.Rectangle((x0, y0 + h*safe_frac), w, h*(1-safe_frac), facecolor="#fee2e2", edgecolor="none", alpha=0.95))

    # etiquetas
    ax.text(0.50, y0 + h*0.20, "seguro", ha="center", va="center", fontsize=9.5, color="#166534", weight="bold")
    ax.text(0.50, y0 + h*0.85, "excesso", ha="center", va="center", fontsize=9.5, color="#b91c1c", weight="bold")

    # limite seguro
    ax.plot([x0-0.06, x0+w+0.06], [y_safe, y_safe], color="#6b7280", lw=2.0, ls="--")
    ax.text(0.50, y_safe + 0.035, "limite\nseguro", ha="center", va="bottom", fontsize=9.0, color="#6b7280")

    # preenchimento suave até strain_now
    fill_color = "#16a34a" if strain_now <= SAFE_LINE else "#dc2626"
    ax.add_patch(plt.Rectangle((x0, y0), w, h*frac_now, facecolor=fill_color, edgecolor="none", alpha=0.18))

    # marcador actual (sobe/desce)
    y_now = y0 + h*frac_now
    ax.plot([x0-0.08, x0+w+0.08], [y_now, y_now], color="#111827", lw=3.2, solid_capstyle="round")

    # marcador do pico (VT/CRF)
    y_pk = y0 + h*frac_peak
    ax.plot([x0-0.07, x0+w+0.07], [y_pk, y_pk], color="#111827", lw=2.0, ls=":", alpha=0.9)
    ax.text(0.50, y_pk + 0.02, "pico", ha="center", va="bottom", fontsize=9.0, color="#111827")

    # título e valor
    ax.text(0.50, 0.92, "STRAIN", ha="center", va="center", fontsize=11.5, weight="bold", color="#111827")

    col = "#166534" if strain_now <= SAFE_LINE else "#b91c1c"
    ax.text(0.50, 0.08, fmt_strain(strain_now), ha="center", va="center", fontsize=12.5, weight="bold", color=col)


# =========================
# DRAW: TEXT PANEL (SEM SOBREPOSIÇÕES)
# =========================
def draw_text_panel(ax, title: str, crf: float, vt: float, dv_now: float,
                    strain_now: float, strain_peak: float,
                    note_lines: list[str], badge_text: str, badge_color: str):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.00, 0.92, title, fontsize=13.5, weight="bold", color="#111827", va="top")

    ax.text(0.00, 0.80, "Definição:", fontsize=11.0, weight="bold", color="#111827")
    ax.text(0.00, 0.74, "strain = ΔV / V0", fontsize=13.5, color="#111827")
    ax.text(0.00, 0.69, "(onde V0 ≈ CRF)", fontsize=10.5, color="#6b7280")

    ax.text(0.00, 0.60, f"V0 (≈ CRF) = {fmt_L(crf)}", fontsize=12.0, color="#111827")
    ax.text(0.00, 0.54, f"VT (pico)  = {fmt_L(vt)} (450 mL)", fontsize=12.0, color="#111827")

    ax.text(0.00, 0.47, f"ΔV (agora) = {fmt_L(dv_now)}", fontsize=12.0, color="#111827")

    col_now = "#166534" if strain_now <= SAFE_LINE else "#b91c1c"
    ax.text(0.00, 0.40, f"strain (agora) = {fmt_strain(strain_now)}", fontsize=14.0, weight="bold", color=col_now)

    col_pk = "#166534" if strain_peak <= SAFE_LINE else "#b91c1c"
    ax.text(0.00, 0.34, f"strain (pico)  = {fmt_strain(strain_peak)}", fontsize=12.5, weight="bold", color=col_pk)

    ax.text(0.00, 0.26, "Relação-chave (didáctica):", fontsize=11.0, weight="bold", color="#111827")
    y = 0.21
    for line in note_lines:
        ax.text(0.02, y, f"• {line}", fontsize=10.4, color="#111827", va="top")
        y -= 0.06

    ax.text(
        0.00, 0.06, badge_text,
        fontsize=11.2, weight="bold", color="#111827",
        bbox=dict(boxstyle="round,pad=0.35", facecolor=badge_color, edgecolor="none", alpha=0.95),
        va="bottom"
    )


# =========================
# DRAW: LUNG (ANIMAÇÃO)
# =========================
def draw_lung(ax, strain_now: float, phase01: float, crack: bool = False):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    breath = breathing_wave(phase01)  # 0..1..0
    base = 0.72
    amp = 0.06 + 0.12*clamp01(strain_now/0.60)
    scale = base + amp*(breath - 0.5)

    cx, cy = 0.50, 0.54
    w = 0.72 * scale
    h = 0.80 * scale

    ax.imshow(
        lung_arr,
        extent=(cx - w/2, cx + w/2, cy - h/2, cy + h/2),
        interpolation="lanczos",
        zorder=2
    )

    if crack:
        ax.plot([0.40, 0.62], [0.62, 0.40], color="#111827", lw=4.0, alpha=0.85, zorder=3)
        ax.plot([0.46, 0.58], [0.58, 0.46], color="#111827", lw=3.2, alpha=0.85, zorder=3)

    ax.text(0.50, 0.10, "Pulmão — deformação aumenta quando a CRF cai",
            ha="center", va="center", fontsize=9.5, color="#6b7280")


# =========================
# MAIN RENDER
# =========================
fig = plt.figure(figsize=(W, H), dpi=DPI)

writer = imageio.get_writer(
    OUT,
    fps=FPS,
    codec="libx264",
    macro_block_size=1,
    ffmpeg_params=["-preset", "ultrafast", "-crf", "22"]
)

for i in range(TOTAL_FRAMES):
    t = i / FPS

    # ciclo respiratório (4s): ΔV(t)=VT*breath
    phase01 = (t % 4.0) / 4.0
    breath = breathing_wave(phase01)
    dv_now = VT_L * breath

    # cenário
    if t < T1:
        crf = CRF_HEALTHY
        title = "Pulmão saudável"
        notes = [
            "CRF alta → para o mesmo VT, strain baixo",
            "stress (tensão) ↑ quando strain ↑",
            "se CRF ↓, o mesmo VT torna-se “grande demais”"
        ]
        badge = "CRF alta → strain baixo (reversível/seguro)"
        badge_col = "#dcfce7"

    elif t < T1 + T2:
        crf = CRF_LOW
        title = "Pulmão com CRF baixa"
        notes = [
            "CRF baixa → V0 pequeno → strain sobe",
            "mesmo VT → mais distensão relativa",
            "risco mecânico aumenta"
        ]
        badge = "CRF baixa → strain excessivo (lesão provável)"
        badge_col = "#fee2e2"

    else:
        x = (t - (T1 + T2)) / T3
        crf = CRF_VNI_START + (CRF_VNI_END - CRF_VNI_START) * smoothstep(x)
        title = "VNI: porquê ajuda?"
        notes = [
            "VNI/PEEP ↑ → recrutamento → CRF ↑",
            "V0 ↑ → strain ↓ para o mesmo VT",
            "↓ stress/strain → ↓ risco de VILI"
        ]
        badge = "VNI aumenta CRF → reduz strain para o mesmo VT"
        badge_col = "#dcfce7"

    strain_now = dv_now / crf
    strain_peak = VT_L / crf

    crack = True if (t >= T1 and t < T1 + T2 and strain_peak > 0.35) else False

    fig.clf()
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

    draw_text_panel(
        ax_txt,
        title=title,
        crf=crf,
        vt=VT_L,
        dv_now=dv_now,
        strain_now=strain_now,
        strain_peak=strain_peak,
        note_lines=notes,
        badge_text=badge,
        badge_color=badge_col
    )

    draw_lung(ax_lung, strain_now=strain_now, phase01=phase01, crack=crack)

    draw_strain_bar(ax_bar, strain_now=strain_now, strain_peak=strain_peak)

    writer.append_data(canvas_to_rgb(fig))

writer.close()
print("OK ->", OUT)
