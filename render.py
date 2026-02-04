# render_strain_crf_vni.py
# Vídeo 16:9 (60s) — stress/strain, CRF e papel da VNI
# FIX pedido: o TEXTO (painel esquerdo) está todo “em bloco” e pode ser deslocado mudando só X_PANEL.
# Requisitos: pip install matplotlib imageio

import os
os.environ["MPLBACKEND"] = "Agg"

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from matplotlib.patches import Rectangle, FancyBboxPatch

# =========================
# OUTPUT / VIDEO
# =========================
OUT = "stress_strain_vni.mp4"
FPS = 20
DURATION_S = 60

W, H = 12.8, 7.2
DPI = 120

# =========================
# ASSET
# =========================
LUNG_IMG = "lung_realistic.png.PNG"  # usa exactamente este nome (como tens no GitHub)

# =========================
# LAYOUT — MUDA SÓ ISTO
# =========================
# Painel de texto "em bloco" (esquerda). Se houver sobreposição, mexe só aqui.
X_PANEL = 0.08     # <- desloca tudo para a direita/esquerda
Y_TOP   = 0.80

# Zonas reservadas:
# - Texto: x in [X_PANEL .. X_PANEL+PANEL_W]
# - Pulmão: centro
# - Barra strain: direita
PANEL_W = 0.40
BAR_X0  = 0.86  # barra strain (direita)
BAR_W   = 0.06
BAR_Y0  = 0.22
BAR_H   = 0.58

# =========================
# DIDÁTICA (valores)
# =========================
VT_L = 0.45                 # 450 mL
CRF_HEALTHY = 2.5           # L
CRF_LOW = 1.0               # L
CRF_VNI_TARGET = 1.8        # L (exemplo: VNI/PEEP sobe CRF/recruta)

SAFE_STRAIN = 0.25          # limite didático (não é "lei"; serve para semáforo)

# =========================
# TIMELINE (60s)
# =========================
# 0–20s: saudável
# 20–40s: CRF baixa + “falha provável”
# 40–60s: VNI ↑CRF → strain baixa
T1, T2, T3 = 20.0, 40.0, 60.0

# =========================
# Helpers
# =========================
def clamp(x, a, b):
    return max(a, min(b, x))

def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return 0.5 - 0.5*np.cos(np.pi*x)

def lerp(a, b, t):
    return a + (b - a)*t

def strain(vt, v0):
    return vt / max(v0, 1e-9)

def canvas_to_rgb(fig):
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()

def load_lung(path):
    if os.path.exists(path):
        return plt.imread(path)
    return None

LUNG = load_lung(LUNG_IMG)

def draw_strain_bar(ax, s, x0=BAR_X0, y0=BAR_Y0, w=BAR_W, h=BAR_H, safe=SAFE_STRAIN):
    # fundo
    ax.add_patch(Rectangle((x0, y0), w, h, fill=False, lw=2.0, edgecolor="#111827"))

    # zonas (verde seguro / vermelho acima)
    safe_frac = clamp(safe / 0.60, 0.0, 1.0)  # escala até 0.60 (didático)
    y_safe = y0 + h*safe_frac

    ax.add_patch(Rectangle((x0, y0), w, y_safe - y0, facecolor="#dcfce7", edgecolor="none", alpha=0.95))
    ax.add_patch(Rectangle((x0, y_safe), w, y0 + h - y_safe, facecolor="#fee2e2", edgecolor="none", alpha=0.95))

    # marcador strain (escala 0..0.60)
    frac = clamp(s / 0.60, 0.0, 1.0)
    ym = y0 + h*frac
    ax.plot([x0-0.01, x0+w+0.01], [ym, ym], lw=3.0, color="#111827")

    # texto
    ax.text(x0 + w/2, y0 + h + 0.03, "STRAIN", ha="center", va="bottom", fontsize=11, weight="bold")
    ax.text(x0 + w/2, y0 - 0.04, f"{s:.2f}", ha="center", va="top",
            fontsize=11, weight="bold", color="#166534" if s <= safe else "#991b1b")
    ax.text(x0 - 0.01, y_safe, "limite\nseguro", ha="right", va="center", fontsize=9, color="#374151")

def panel_box(ax, x, y, text, fontsize=12, fc="#ffffff", ec="#e5e7eb",
              weight="normal", color="#111827", pad=0.35, alpha=0.95, va="top"):
    ax.text(
        x, y, text, transform=ax.transAxes,
        ha="left", va=va, fontsize=fontsize, weight=weight, color=color,
        bbox=dict(boxstyle=f"round,pad={pad}", facecolor=fc, edgecolor=ec, alpha=alpha)
    )

def draw_lung(ax, center=(0.58, 0.45), scale=1.0, pulse=0.0, crack=False):
    cx, cy = center
    # “pulso” suave (insp/exp)
    s = scale * (1.0 + 0.06*pulse)

    if LUNG is not None:
        # desenhar imagem com extent controlado
        w = 0.34*s
        h = 0.44*s
        ax.imshow(LUNG, extent=(cx-w/2, cx+w/2, cy-h/2, cy+h/2), zorder=2)
    else:
        # fallback simples (nunca devia acontecer se o ficheiro existir)
        ax.add_patch(plt.Circle((cx-0.06*s, cy), 0.10*s, color="#f4a7b9", ec="#7f1d1d", lw=2))
        ax.add_patch(plt.Circle((cx+0.06*s, cy), 0.10*s, color="#f4a7b9", ec="#7f1d1d", lw=2))

    # “fissura” didática quando crack=True
    if crack:
        ax.plot([cx-0.07, cx+0.08], [cy+0.04, cy-0.10], color="#111827", lw=3.0, zorder=5)
        ax.plot([cx-0.02, cx+0.10], [cy+0.02, cy-0.06], color="#111827", lw=2.0, zorder=5)

# =========================
# RENDER
# =========================
fig = plt.figure(figsize=(W, H), dpi=DPI)
writer = imageio.get_writer(
    OUT,
    fps=FPS,
    codec="libx264",
    macro_block_size=1,
    ffmpeg_params=["-preset", "ultrafast", "-crf", "24"]
)

total_frames = int(DURATION_S * FPS)

for i in range(total_frames):
    t = i / FPS

    # ciclo respiratório (pulso visual)
    resp_phase = (t % 4.0) / 4.0
    pulse = np.sin(2*np.pi*resp_phase) * 0.5 + 0.5  # 0..1

    # escolher cenário por tempo
    if t < T1:
        # saudável
        v0 = CRF_HEALTHY
        s = strain(VT_L, v0)
        crack = False
        headline = "Pulmão saudável"
        msg = "CRF alta → para o mesmo VT → strain baixo (seguro)"
        msg_fc = "#dcfce7"
        msg_col = "#166534"
    elif t < T2:
        # CRF baixa (lesão provável)
        v0 = CRF_LOW
        s = strain(VT_L, v0)
        crack = (t > (T1 + 7.0))  # começa a “fissura” após alguns segundos
        headline = "Pulmão com CRF baixa"
        msg = "CRF baixa → para o mesmo VT → strain sobe (lesão provável)"
        msg_fc = "#fee2e2"
        msg_col = "#991b1b"
    else:
        # VNI melhora CRF (transição suave até target)
        k = smoothstep((t - T2) / (T3 - T2))
        v0 = lerp(CRF_LOW, CRF_VNI_TARGET, k)
        s = strain(VT_L, v0)
        crack = False
        headline = "VNI: recruta + aumenta CRF"
        msg = "Ao subir CRF (V0), o mesmo VT gera menos strain → menor risco mecânico"
        msg_fc = "#dcfce7"
        msg_col = "#166534"

    # stress (muito simplificado) só para ligação conceptual
    # (didático): stress ∝ strain
    stress_rel = 1.0 * s

    fig.clf()
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Título
    ax.text(0.06, 0.93, "STRESS–STRAIN — CRF e o papel da VNI",
            fontsize=18, weight="bold", ha="left", va="center", color="#111827")

    # =========================
    # PAINEL ESQUERDO (BLOCO) — TUDO preso ao X_PANEL
    # =========================
    y = Y_TOP
    panel_box(ax, X_PANEL, y, f"{headline}", fontsize=14, weight="bold", fc="#ffffff", ec="#e5e7eb", pad=0.40); y -= 0.10

    # Definição curta e explícita (sem confusão)
    # V0 aqui é CRF (proxy didático)
    def_text = (
        "Definição:\n"
        "strain = ΔV / V0\n"
        f"V0 (≈ CRF) = {v0:.1f} L\n"
        f"ΔV (VT)    = {VT_L:.2f} L (450 mL)\n"
        f"⇒ strain   = {s:.2f}"
    )
    panel_box(ax, X_PANEL, y, def_text, fontsize=12.5, fc="#ffffff", ec="#e5e7eb", pad=0.45); y -= 0.26

    # Ligação stress–strain (simples, sem equações extra)
    link_text = (
        "Relação chave (didática):\n"
        "• CRF (V0) ↓  → strain ↑ (para o mesmo VT)\n"
        "• stress ↑ quando strain ↑ (maior distensão → maior tensão)\n"
        "• risco mecânico sobe quando CRF está reduzida"
    )
    panel_box(ax, X_PANEL, y, link_text, fontsize=11.2, fc="#f8fafc", ec="#e5e7eb", pad=0.40); y -= 0.23

    # Mensagem (sem sobreposição) — caixa própria
    panel_box(ax, X_PANEL, y, msg, fontsize=12.2, fc=msg_fc, ec=msg_fc, pad=0.45, weight="bold", color=msg_col); y -= 0.10

    # Rodapé curto só no bloco esquerdo
    if t >= T2:
        vni_text = "VNI ↑CRF (recrutamento/PEEP) → V0 ↑ → strain ↓ → menor stress"
        panel_box(ax, X_PANEL, y, vni_text, fontsize=11.0, fc="#eef2ff", ec="#c7d2fe", pad=0.40, color="#1e3a8a"); y -= 0.10

    # =========================
    # Pulmão (centro)
    # =========================
    # Escala e pulso: mais “dramático” quando CRF baixa
    base_scale = 1.0 if t < T1 else (0.92 if t < T2 else 0.98)
    # pulso relativo ao strain (para “ver” mais deformação quando strain alto)
    pulse_gain = clamp(s / 0.45, 0.4, 1.2)
    draw_lung(ax, center=(0.60, 0.48), scale=base_scale, pulse=pulse * pulse_gain, crack=crack)

    # Etiqueta CRF (no centro inferior, não colide)
    ax.text(0.60, 0.18, f"CRF = {v0:.1f} L",
            ha="center", va="center", fontsize=13, weight="bold",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#e0f2fe", edgecolor="#bae6fd", alpha=0.98),
            color="#111827")

    # =========================
    # Barra STRAIN (direita) — agora move sempre
    # =========================
    draw_strain_bar(ax, s, x0=BAR_X0, y0=BAR_Y0, w=BAR_W, h=BAR_H, safe=SAFE_STRAIN)

    # “Semáforo” rápido em baixo (curto, sem caixas a colidir)
    if s <= SAFE_STRAIN:
        sem_text = "strain dentro do limite (reversível)"
        sem_fc, sem_ec, sem_col = "#dcfce7", "#bbf7d0", "#166534"
    else:
        sem_text = "strain excessivo (lesão provável)"
        sem_fc, sem_ec, sem_col = "#fee2e2", "#fecaca", "#991b1b"

    ax.text(0.86, 0.14, sem_text, ha="center", va="center",
            fontsize=11, weight="bold",
            bbox=dict(boxstyle="round,pad=0.35", facecolor=sem_fc, edgecolor=sem_ec, alpha=0.98),
            color=sem_col)

    fig.tight_layout()
    writer.append_data(canvas_to_rgb(fig))

writer.close()
print("OK ->", OUT)
