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

# “Limites” visuais do termómetro (didáctico)
SAFE_LIMIT = 0.25
ST_MAX_BAR = 0.60  # topo do termómetro

def strain(vt, crf):
    return vt / crf

def phase(t):
    # 0-20: saudável
    # 20-40: CRF baixa (strain alto) + “ruptura”
    # 40-60: VNI aumenta CRF efectiva -> strain baixa
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

    # parâmetros por fase
    if ph == "ok":
        crf = CRF_OK_L
        banner = "Pulmão saudável: CRF alta → strain baixo (seguro)"
        rupture = 0.0
        vni_note = ""
    elif ph == "low":
        crf = CRF_LOW_L
        banner = "CRF baixa → para o mesmo VT o strain sobe (lesão provável)"
        rupture = smooth01((t - 20) / 20)  # cresce ao longo de 20s
        vni_note = ""
    else:
        crf = CRF_LOW_L + 0.8 * smooth01((t - 40) / 20)
        banner = "Com VNI: ↑CRF efectiva (recrutamento/PEEP) → ↓strain"
        rupture = 0.0
        vni_note = "VNI ↑V0 (CRF efectiva) → para o mesmo ΔV o strain desce"

    st = strain(VT_L, crf)

    # Tidal suave (visualmente claro)
    # 0.25 Hz ~ 15 ciclos/min (aprox) só para “vida” visual
    tidal = 0.5 + 0.5*np.sin(2*np.pi*(t*0.25))
    # VT instantâneo (varia entre 35% e 100% do VT)
    vt_inst = VT_L * (0.35 + 0.65*tidal)

    # Escala do pulmão: base depende de CRF (pulmão “maior” vs “menor”),
    # e variação (inflação) depende de VT_inst com amplitude VISÍVEL.
    base_scale = 0.78 + 0.18*(crf / CRF_OK_L)          # saudável maior
    inflate_amp = 0.14 * (vt_inst / VT_L)              # 0.05–0.14 aprox
    scale = base_scale + inflate_amp                   # variação evidente

    # figura
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Título
    ax.text(0.5, 0.93, "STRESS–STRAIN — CRF e papel da VNI",
            ha="center", va="center", fontsize=22, weight="bold", color="#111827")

    # BLOCO ESQUERDO (fixo) — nunca colide com o pulmão
    ax.text(0.08, 0.83, "Definição:", fontsize=14, weight="bold", color="#111827")
    ax.text(0.08, 0.79, r"$\mathrm{strain}=\Delta V/V_0$",
            fontsize=18, color="#111827")

    ax.text(0.08, 0.72, f"V0 (CRF) = {crf:.1f} L", fontsize=15, color="#111827")
    ax.text(0.08, 0.67, f"ΔV (VT) = {VT_L:.2f} L (450 mL)", fontsize=15, color="#111827")

    st_col = "#166534" if st <= SAFE_LIMIT else "#b91c1c"
    ax.text(0.08, 0.62, f"strain = {st:.2f}", fontsize=17, weight="bold", color=st_col)

    # Caixa explicativa (esquerda) — FORA da zona do pulmão
    ax.text(
        0.08, 0.53, banner,
        fontsize=13.2,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#f3f4f6", edgecolor="#e5e7eb"),
        color="#111827"
    )

    if vni_note:
        ax.text(
            0.08, 0.47, vni_note,
            fontsize=12.2,
            bbox=dict(boxstyle="round,pad=0.30", facecolor="#ecfeff", edgecolor="#a5f3fc"),
            color="#0f172a"
        )

    # TERMÓMETRO DO STRAIN (direita)
    x0, y0, wbar, hbar = 0.87, 0.20, 0.06, 0.62
    ax.add_patch(Rectangle((x0, y0), wbar, hbar, fill=False, lw=2, ec="#111827"))

    # zonas (verde até SAFE_LIMIT; vermelho acima)
    safe_frac = SAFE_LIMIT / ST_MAX_BAR
    safe_frac = float(np.clip(safe_frac, 0, 1))
    ax.add_patch(Rectangle((x0, y0), wbar, hbar*safe_frac, fc="#dcfce7", ec="none"))
    ax.add_patch(Rectangle((x0, y0+hbar*safe_frac), wbar, hbar*(1-safe_frac), fc="#fee2e2", ec="none"))

    ax.text(x0 + wbar/2, y0 + hbar + 0.04, "STRAIN", ha="center", fontsize=12, weight="bold")

    st_clip = float(np.clip(st, 0, ST_MAX_BAR))
    ymark = y0 + hbar*(st_clip / ST_MAX_BAR)
    ax.plot([x0-0.01, x0+wbar+0.01], [ymark, ymark], lw=3, color="#111827")
    ax.text(x0 + wbar/2, y0 - 0.05, f"{st:.2f}", ha="center", fontsize=12, weight="bold", color=st_col)

    # Badge CRF (baixo centro)
    ax.text(
        0.5, 0.12,
        f"CRF = {crf:.1f} L",
        ha="center", fontsize=16, weight="bold",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#ecfeff", edgecolor="#a5f3fc"),
        color="#0f172a"
    )

    # PULMÃO (centro) — área livre de texto
    cx, cy = 0.52, 0.47
    target_h = 0.44 * scale
    target_w = target_h * aspect
    x1, x2 = cx - target_w/2, cx + target_w/2
    y1, y2 = cy - target_h/2, cy + target_h/2

    ax.imshow(lung_img, extent=[x1, x2, y1, y2], zorder=3)

    # “ruptura” visual na fase low
    if rupture > 0:
        # rachas + texto (abaixo do pulmão, sem colisões)
        ax.plot([cx-0.07, cx+0.04], [cy+0.08, cy-0.02], color="#111827", lw=3, zorder=4)
        ax.plot([cx-0.01, cx+0.09], [cy+0.01, cy-0.10], color="#111827", lw=3, zorder=4)

        ax.text(
            0.52, 0.23,
            "strain excessivo → falha estrutural provável",
            ha="center", fontsize=14, weight="bold",
            color="#b91c1c",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#fee2e2", edgecolor="#fecaca"),
            zorder=5
        )

    # frame -> vídeo
    fig.canvas.draw()
    frame = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
    writer.append_data(frame)
    plt.close(fig)

writer.close()
print("OK ->", OUT)
