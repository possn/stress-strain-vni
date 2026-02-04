import os
os.environ["MPLBACKEND"] = "Agg"

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
import matplotlib.image as mpimg

# =========================
# CONFIG
# =========================
OUT = "stress_strain_vni.mp4"
FPS = 20
DURATION_S = 60
W, H = 12.8, 7.2
DPI = 120

LUNG_IMG = "lung_realistic.png.PNG"

# Cenários didácticos
VT_L = 0.45           # 450 mL
CRF_OK_L = 2.5        # saudável
CRF_LOW_L = 1.0       # reduzida
SAFE_LIMIT = 0.25     # limite didáctico "seguro" p/ strain

def strain(vt, crf):
    return vt / crf

# timeline (60s)
# 0-20: pulmão saudável
# 20-40: CRF baixa (alto strain) + "ruptura"
# 40-60: VNI aumenta CRF efectiva -> strain baixa
def phase(t):
    if t < 20:
        return "ok"
    if t < 40:
        return "low"
    return "vni"

def smooth01(x):
    x = np.clip(x, 0, 1)
    return 0.5 - 0.5*np.cos(np.pi*x)

def load_lung():
    if not os.path.exists(LUNG_IMG):
        raise FileNotFoundError(f"Imagem não encontrada: {LUNG_IMG}")
    img = mpimg.imread(LUNG_IMG)
    # normaliza alpha se existir
    return img

lung_img = load_lung()

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
        crf_label = "CRF = 2,5 L"
        note = "Pulmão saudável: CRF alta → strain baixo (seguro)"
        rupture = 0.0
    elif ph == "low":
        crf = CRF_LOW_L
        crf_label = "CRF = 1,0 L"
        note = "CRF baixa → para o mesmo VT o strain sobe (lesão provável)"
        # ruptura visual cresce ao longo da fase 20-40
        rupture = smooth01((t-20)/20)
    else:
        # VNI: CRF efectiva aumenta gradualmente (ex: +0.8 L)
        crf = CRF_LOW_L + 0.8*smooth01((t-40)/20)
        crf_label = f"CRF efectiva ≈ {crf:.1f} L (com VNI)"
        note = "VNI ↑CRF efectiva (recrutamento/PEEP) → ↓strain → mais segurança"
        rupture = 0.0

    st = strain(VT_L, crf)

    # tidal "animado" (não é fisiologia exacta; é visual didáctico)
    tidal = 0.5 + 0.5*np.sin(2*np.pi*(t*0.22))
    vt_inst = VT_L*(0.35 + 0.65*tidal)  # varia entre ~35-100% do VT

    # escala visual do pulmão: depende do volume (CRF + VT_inst)
    # e normaliza por CRF saudável para dar sensação de "pulmão pequeno vs grande"
    base = (crf / CRF_OK_L)
    amp  = (vt_inst / CRF_OK_L)
    scale = 0.75 + 0.35*base + 0.45*amp

    # figura
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    ax = fig.add_axes([0,0,1,1])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # título
    ax.text(0.5, 0.93, "STRESS–STRAIN — CRF e papel da VNI",
            ha="center", va="center", fontsize=22, weight="bold", color="#111827")

    # fórmula
    ax.text(0.08, 0.83, "Definição:",
            fontsize=14, weight="bold", color="#111827")
    ax.text(0.08, 0.79, r"$\mathrm{strain}=\Delta V/V_0$",
            fontsize=18, color="#111827")

    # valores
    ax.text(0.08, 0.72, f"V0 (CRF) = {crf:.1f} L",
            fontsize=15, color="#111827")
    ax.text(0.08, 0.67, f"ΔV (VT) = {VT_L:.2f} L (450 mL)",
            fontsize=15, color="#111827")
    ax.text(0.08, 0.62, f"strain = {st:.2f}",
            fontsize=17, weight="bold",
            color=("#166534" if st <= SAFE_LIMIT else "#b91c1c"))

    # nota
    ax.text(0.08, 0.54, note,
            fontsize=13.5,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#f3f4f6", edgecolor="#e5e7eb"))

    # termómetro do strain (direita)
    x0, y0, w, h = 0.87, 0.20, 0.06, 0.62
    ax.add_patch(plt.Rectangle((x0,y0), w, h, fill=False, lw=2, ec="#111827"))
    # zonas
    ax.add_patch(plt.Rectangle((x0,y0), w, h*SAFE_LIMIT/0.6, fc="#dcfce7", ec="none"))
    ax.add_patch(plt.Rectangle((x0,y0+h*SAFE_LIMIT/0.6), w, h*(1-SAFE_LIMIT/0.6), fc="#fee2e2", ec="none"))
    ax.text(x0+w/2, y0+h+0.04, "STRAIN", ha="center", fontsize=12, weight="bold")
    # marcador
    st_clip = float(np.clip(st, 0, 0.60))
    ymark = y0 + h*(st_clip/0.60)
    ax.plot([x0-0.01, x0+w+0.01], [ymark, ymark], lw=3, color="#111827")
    ax.text(x0+w/2, y0-0.05, f"{st:.2f}", ha="center",
            fontsize=12, weight="bold",
            color=("#166534" if st <= SAFE_LIMIT else "#b91c1c"))

    # legenda CRF (baixo)
    ax.text(0.5, 0.12, crf_label,
            ha="center", fontsize=16, weight="bold",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#ecfeff", edgecolor="#a5f3fc"))

    # desenhar pulmão (imagem) com escala animada
    # posicionamento central
    cx, cy = 0.52, 0.46
    img = lung_img
    ih, iw = img.shape[0], img.shape[1]
    aspect = iw/ih

    # bbox em coordenadas do eixo
    target_h = 0.48 * scale
    target_w = target_h * aspect
    x1, x2 = cx - target_w/2, cx + target_w/2
    y1, y2 = cy - target_h/2, cy + target_h/2
    ax.imshow(img, extent=[x1, x2, y1, y2], zorder=2)

    # “ruptura” visual (fase low)
    if rupture > 0:
        # racha no pulmão + texto “ruptura”
        ax.plot([cx-0.08, cx+0.05], [cy+0.10, cy-0.05],
                color="#111827", lw=3, alpha=0.9, zorder=3)
        ax.plot([cx-0.02, cx+0.10], [cy+0.02, cy-0.12],
                color="#111827", lw=3, alpha=0.9, zorder=3)
        ax.text(0.52, 0.24, "strain excessivo → falha estrutural provável",
                ha="center", fontsize=14, weight="bold",
                color="#b91c1c",
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#fee2e2", edgecolor="#fecaca"),
                zorder=4)

    # frame -> vídeo
    fig.canvas.draw()
    frame = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
    writer.append_data(frame)
    plt.close(fig)

writer.close()
print("OK ->", OUT)
