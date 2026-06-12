"""Gera o gráfico do benchmark Polars vs Pandas (PNG pronto pro LinkedIn)."""
import json
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

with open("resultados.json") as f:
    data = json.load(f)

info = data["info"]
res = data["resultados"]
n_threads = info.get("polars_threads", info.get("cpu_cores", 1))

ordem = ["leitura_csv", "leitura_parquet", "filtro", "groupby_agg",
         "join", "sort", "consulta_memoria", "pipeline_completo"]
rotulos = ["Leitura CSV", "Leitura Parquet", "Filtro", "GroupBy + agreg.",
           "Join", "Ordenação", "Consulta complexa\n(em memória)",
           "Pipeline completo\n(ler + processar)"]

pandas_t = [res[o]["pandas"] for o in ordem]
polars_t = [res[o]["polars"] for o in ordem]
speedup  = [p / q for p, q in zip(pandas_t, polars_t)]

# ----------------------------- Estilo -----------------------------
COR_PANDAS = "#8A94A6"   # cinza-ardósia
COR_POLARS = "#2D6FE0"   # azul vivo
COR_FUNDO  = "#FFFFFF"
COR_TXT    = "#1A2233"
COR_WIN    = "#1FB57A"   # verde p/ speedup quando Polars vence
COR_LOSE   = "#E0A33E"   # âmbar quando pandas vence

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#D8DEE9",
    "text.color": COR_TXT,
    "axes.labelcolor": COR_TXT,
    "xtick.color": COR_TXT,
    "ytick.color": COR_TXT,
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7.2), facecolor=COR_FUNDO)
fig.subplots_adjust(left=0.10, right=0.97, top=0.80, bottom=0.12, wspace=0.42)

y = np.arange(len(ordem))[::-1]   # de cima p/ baixo na ordem da lista
h = 0.38

# --- Painel 1: tempo absoluto (escala log p/ caber leitura e filtro juntos) ---
ax1.barh(y + h/2, pandas_t, height=h, color=COR_PANDAS, label="pandas", zorder=3)
ax1.barh(y - h/2, polars_t, height=h, color=COR_POLARS, label="Polars", zorder=3)
ax1.set_xscale("log")
ax1.set_yticks(y)
ax1.set_yticklabels(rotulos, fontsize=10.5)
ax1.set_xlabel("Tempo por operação — segundos (escala log)", fontsize=10.5)
ax1.set_title("Tempo de execução", fontsize=13, fontweight="bold", pad=10, loc="left")
ax1.grid(axis="x", color="#EAEEF4", zorder=0)
ax1.spines[["top", "right"]].set_visible(False)
for yi, v in zip(y + h/2, pandas_t):
    ax1.text(v * 1.12, yi, f"{v:.2f}s", va="center", fontsize=8.5, color=COR_PANDAS)
for yi, v in zip(y - h/2, polars_t):
    ax1.text(v * 1.12, yi, f"{v:.2f}s", va="center", fontsize=8.5,
             color=COR_POLARS, fontweight="bold")

# --- Painel 2: speedup (quantas vezes Polars é mais rápido) ---
cores = [COR_WIN if s >= 1 else COR_LOSE for s in speedup]
ax2.barh(y, speedup, height=0.6, color=cores, zorder=3)
ax2.axvline(1.0, color="#9AA4B2", linestyle="--", linewidth=1.2, zorder=2)
ax2.text(1.0, len(ordem) - 0.3, "empate (1x)", fontsize=8.5,
         color="#6B7686", ha="center")
ax2.set_yticks(y)
ax2.set_yticklabels([])
ax2.set_xlabel("Speedup — Polars vs pandas (maior = Polars mais rápido)", fontsize=10.5)
ax2.set_title("Quantas vezes mais rápido", fontsize=13, fontweight="bold", pad=10, loc="left")
ax2.grid(axis="x", color="#EAEEF4", zorder=0)
ax2.spines[["top", "right"]].set_visible(False)
ax2.set_xlim(0, max(speedup) * 1.25)
for yi, s in zip(y, speedup):
    ax2.text(s + max(speedup) * 0.02, yi, f"{s:.1f}x", va="center",
             fontsize=10, fontweight="bold",
             color=(COR_WIN if s >= 1 else COR_LOSE))

# --- Títulos gerais ---
fig.suptitle("Polars vs Pandas — Benchmark em 10 milhões de linhas",
             fontsize=19, fontweight="bold", x=0.10, ha="left", y=0.955)
subt = (f"{info['n_linhas']:,} linhas  ·  pandas {info['pandas']}  ·  "
        f"polars {info['polars']}  ·  Python {info['python']}  ·  "
        f"Polars com {n_threads} thread(s)  ·  mediana de {info['n_runs']} execuções")
fig.text(0.10, 0.875, subt, fontsize=10.5, color="#5B6675", ha="left")

# Chave de cores (no lugar da legenda interna)
fig.text(0.705, 0.875, "■", fontsize=13, color=COR_PANDAS, ha="left", va="center")
fig.text(0.720, 0.875, "pandas", fontsize=11, color="#5B6675", ha="left", va="center")
fig.text(0.795, 0.875, "■", fontsize=13, color=COR_POLARS, ha="left", va="center")
fig.text(0.810, 0.875, "Polars", fontsize=11, color="#5B6675", ha="left", va="center",
         fontweight="bold")

if n_threads <= 1:
    cap = ("⚠ Rodado com 1 thread: subestima o Polars, cujo maior trunfo é o "
           "paralelismo multi-core. Com vários núcleos, a vantagem em "
           "groupby/join/sort tende a crescer. Código aberto e reproduzível.")
else:
    cap = (f"Rodado com {n_threads} threads (multi-core). Os resultados variam "
           "conforme hardware, versões das libs e tipo de dado. "
           "Código aberto e reproduzível.")
fig.text(0.10, 0.025, cap, fontsize=8.5, color="#8A94A6", ha="left", style="italic")

plt.savefig("benchmark_polars_pandas.png", dpi=200,
            facecolor=COR_FUNDO, bbox_inches="tight")
print("Gráfico salvo: benchmark_polars_pandas.png")
print("\nSpeedups:", {r: round(s, 1) for r, s in zip(ordem, speedup)})


# ---------- Atualiza a tabela de resultados dentro do README.md ----------
def atualizar_readme():
    import re
    import os
    caminho = "README.md"
    if not os.path.exists(caminho):
        return
    cabecalho = (
        f"Rodado em **{info['cpu_cores']} núcleo(s) de CPU** "
        f"(Polars usando {n_threads} thread(s)) · pandas {info['pandas']} · "
        f"polars {info['polars']} · Python {info['python']} · "
        f"{info['n_linhas']:,} linhas · mediana de {info['n_runs']} execuções.\n\n"
        "| Operação | pandas (s) | Polars (s) | Speedup |\n"
        "|----------|-----------:|-----------:|--------:|\n"
    )
    linhas = []
    for o, r in zip(ordem, rotulos):
        p, q = res[o]["pandas"], res[o]["polars"]
        sp = p / q
        marca = f"**{sp:.1f}x**" if sp >= 1 else f"{sp:.1f}x"
        linhas.append(f"| {r.replace(chr(10), ' ')} | {p:.2f} | {q:.2f} | {marca} |")
    tabela = cabecalho + "\n".join(linhas)

    with open(caminho, encoding="utf-8") as f:
        conteudo = f.read()
    novo = re.sub(
        r"<!-- RESULTADOS_INICIO -->.*?<!-- RESULTADOS_FIM -->",
        f"<!-- RESULTADOS_INICIO -->\n{tabela}\n<!-- RESULTADOS_FIM -->",
        conteudo, flags=re.DOTALL,
    )
    if novo != conteudo:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(novo)
        print("README.md atualizado com os números desta execução.")


atualizar_readme()
