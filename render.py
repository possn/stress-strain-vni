import os
os.environ["MPLBACKEND"] = "Agg"

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
import matplotlib.image as mpimg
from matplotlib.patches import Rectangle

# =========================
# CONFIG
# =========================
OUT = "stress_strain_vni.mp4"
FPS = 20
DURATION_S = 60
W, H = 12.8, 7.2
DPI = 120

LUNG_IMG = "lung_realistic.png.PNG"

# Didáctico
VT_L = 0.45
CRF_OK_L = 2.5
CRF_LOW_L = 1.0

# Barra strain (didáctico)
SAFE_LIMIT = 0.25
ST_MAX_BAR = 0.60  # topo da barra

def strain(vt, crf):
    return vt / crf

def phase(t):
    # 0-20: saudável
    # 20-40: CRF baixa (lesão)
    # 40-60: VNI aumenta CRF efectiva (recrutamento)
    if t < 20:
        return "ok"
    if t < 40:
        return "low"
    return "vni"

def smooth01(x):
    x = np.clip(x, 0.0, 1.0)
    return 0.5 - 0.5*np.cos(np.pi*x)

def load_lung():
    if not os.path.exists(LUNG_IMG):
        raise FileNotFoundError(f"Imagem não encontrada: {LUNG_IMG}")
    return mpimg.imread(LUNG_IMG)

lung_img = load_lung()
ih, iw = lung_img.shape[0], lung_img.shape[1]
aspect = iw / ih

writer = imageio.get_writer(
    OUT, fps=FPS, codec="libx264", macro_block_size=1,
    ffmpeg_params=["-preset", "veryfast", "-crf", "22"]
)

total_frames = int(DURATION_S * FPS)

for i in range(total_frames):
    t = i / FPS
    ph = phase(t)

    # -------------------------
    # Parâmetros por fase
    # -------------------------
    if ph == "ok":
        crf = CRF_OK_L
        banner = "Pulmão saudável:\nCRF alta → strain baixo (seguro)"
        rupture = 0.0
        vni_note = ""
    elif ph == "low":
        crf = CRF_LOW_L
        banner = "CRF baixa:\nmesmo VT → strain sobe (lesão provável)"
        rupture = smooth01((t - 20) / 20)
        vni_note = ""
    else:
        crf = CRF_LOW_L + 0.8 * smooth01((t - 40) / 20)
        banner = "Com VNI:\n↑CRF efectiva → ↓strain (mesmo VT)"
        rupture = 0.0
        vni_note = "VNI (PEEP/recrutamento) ↑V0 → strain = ΔV/V0 desce"

    # strain "médio" do slide (VT fixo / CRF)
    st_mean = strain(VT_L, crf)

    # -------------------------
    # Tidal (VT instantâneo) -> isto faz a barra mexer
    # -------------------------
    # 0.25 Hz (~15/min) só para vida visual
    tidal = 0.5 + 0.5*np.sin(2*np.pi*(t*0.25))
    # VT(t) oscila entre 35% e 100% do VT
    vt_inst = VT_L * (0.35 + 0.65*tidal)
    st_inst = strain(vt_inst, crf)  # <-- ESTE é o que move a barra

    # Escala do pulmão (visível)
    base_scale = 0.78 + 0.18*(crf / CRF_OK_L)
    inflate_amp = 0.14 * (vt_inst / VT_L)
    scale = base_scale + inflate_amp

    # -------------------------
    # FIG
    # -------------------------
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Título
    ax.text(0.5, 0.93, "STRESS–STRAIN — CRF e papel da VNI",
            ha="center", va="center", fontsize=22, weight="bold", color="#111827")

    # -------------------------
    # BLOCO ESQUERDO (fixo e estreito -> não invade pulmão)
    # -------------------------
    ax.text(0.08, 0.83, "Definição:", fontsize=14, weight="bold", color="#111827")
    ax.text(0.08, 0.79, r"$\mathrm{strain}=\Delta V/V_0$",
            fontsize=18, color="#111827")

    ax.text(0.08, 0.72, f"V0 (CRF) = {crf:.1f} L", fontsize=15, color="#111827")
    ax.text(0.08, 0.67, f"ΔV (VT) = {VT_L:.2f} L (450 mL)", fontsize=15, color="#111827")

    st_col_mean = "#166534" if st_mean <= SAFE_LIMIT else "#b91c1c"
    st_col_inst = "#166534" if st_inst <= SAFE_LIMIT else "#b91c1c"

    ax.text(0.08, 0.62, f"strain (médio) = {st_mean:.2f}",
            fontsize=16.5, weight="bold", color=st_col_mean)

    ax.text(0.08, 0.58, f"strain (inst.) = {st_inst:.2f}",
            fontsize=12.5, weight="bold", color=st_col_inst)

    # Caixa cinzenta (curta, 2 linhas, e com WRAP)
    ax.text(
        0.08, 0.50, banner,
        fontsize=12.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#f3f4f6", edgecolor="#e5e7eb"),
        color="#111827",
        ha="left", va="center",
        wrap=True
    )

    if vni_note:
        ax.text(
            0.08, 0.43, vni_note,
            fontsize=12.0,
            bbox=dict(boxstyle="round,pad=0.30", facecolor="#ecfeff", edgecolor="#a5f3fc"),
            color="#0f172a",
            ha="left", va="center",
            wrap=True
        )

    # -------------------------
    # BARRA DO STRAIN (direita) - agora mexe com st_inst
    # -------------------------
    x0, y0, wbar, hbar = 0.87, 0.20, 0.06, 0.62
    ax.add_patch(Rectangle((x0, y0), wbar, hbar, fill=False, lw=2, ec="#111827"))

    safe_frac = float(np.clip(SAFE_LIMIT / ST_MAX_BAR, 0, 1))
    ax.add_patch(Rectangle((x0, y0), wbar, hbar*safe_frac, fc="#dcfce7", ec="none"))
    ax.add_patch(Rectangle((x0, y0+hbar*safe_frac), wbar, hbar*(1-safe_frac), fc="#fee2e2", ec="none"))

    ax.text(x0 + wbar/2, y0 + hbar + 0.04, "STRAIN", ha="center", fontsize=12, weight="bold")

    # marcador usa strain instantâneo
    st_clip = float(np.clip(st_inst, 0, ST_MAX_BAR))
    ymark = y0 + hbar*(st_clip / ST_MAX_BAR)
    ax.plot([x0-0.01, x0+wbar+0.01], [ymark, ymark], lw=3, color="#111827")

    ax.text(x0 + wbar/2, y0 - 0.05, f"{st_mean:.2f}", ha="center",
            fontsize=12, weight="bold", color=st_col_mean)

    # -------------------------
    # Badge CRF
    # -------------------------
    ax.text(
        0.54, 0.12,
        f"CRF = {crf:.1f} L",
        ha="center", fontsize=16, weight="bold",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#ecfeff", edgecolor="#a5f3fc"),
        color="#0f172a"
    )

    # -------------------------
    # PULMÃO (centro) — ligeiramente mais à direita para ficar “limpo”
    # -------------------------
    cx, cy = 0.58, 0.47
    target_h = 0.44 * scale
    target_w = target_h * aspect
    x1, x2 = cx - target_w/2, cx + target_w/2
    y1, y2 = cy - target_h/2, cy + target_h/2

    ax.imshow(lung_img, extent=[x1, x2, y1, y2], zorder=3)

    # Ruptura visual (fase low)
    if rupture > 0:
        ax.plot([cx-0.07, cx+0.04], [cy+0.08, cy-0.02], color="#111827", lw=3, zorder=4)
        ax.plot([cx-0.01, cx+0.09], [cy+0.01, cy-0.10], color="#111827", lw=3, zorder=4)

        ax.text(
            0.55, 0.23,
            "strain excessivo → falha estrutural provável",
            ha="center", fontsize=14, weight="bold",
            color="#b91c1c",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#fee2e2", edgecolor="#fecaca"),
            zorder=5
        )

    # -------------------------
    # Frame -> vídeo
    # -------------------------
    fig.canvas.draw()
    frame = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
    writer.append_data(frame)
    plt.close(fig)

writer.close()
print("OK ->", OUT)
