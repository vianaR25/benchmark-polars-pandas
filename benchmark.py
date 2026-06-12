"""
Benchmark Polars vs Pandas — comparação honesta e reproduzível.

Regras do jogo (pra ser defensável):
- Mesmas operações nos dois lados, com código IDIOMÁTICO de cada biblioteca.
- Vários runs + warm-up; reportamos a MEDIANA (mais robusta a outliers).
- Imprime versões, nº de cores e tamanho dos dados pra qualquer um reproduzir.
- Inclui Polars em modo LAZY (com query optimizer) na consulta complexa.
"""

import os
import time
import json
import platform
import statistics
import numpy as np
import pandas as pd
import polars as pl

# ----------------------------- Config -----------------------------
N_ROWS  = 10_000_000     # tabela de fatos (transações)
N_USERS = 500_000        # tabela de dimensão (usuários) p/ o join
N_RUNS  = 7              # execuções cronometradas por operação
WARMUP  = 2              # execuções de aquecimento (descartadas)
SEED    = 42

CSV_PATH = "fact.csv"
PARQUET_PATH = "fact.parquet"

rng = np.random.default_rng(SEED)


# ------------------------- Geração de dados -------------------------
def gerar_dados():
    categorias = ["eletronicos", "moda", "casa", "esporte", "livros",
                  "beleza", "games", "mercado", "pet", "auto"]
    regioes = ["sudeste", "sul", "nordeste", "norte", "centro-oeste"]

    print(f"Gerando {N_ROWS:,} linhas...")
    fato = pd.DataFrame({
        "transacao_id": np.arange(N_ROWS, dtype=np.int64),
        "user_id":      rng.integers(0, N_USERS, size=N_ROWS, dtype=np.int64),
        "categoria":    rng.choice(categorias, size=N_ROWS),
        "regiao":       rng.choice(regioes, size=N_ROWS),
        "valor":        np.round(rng.gamma(2.0, 120.0, size=N_ROWS), 2),
        "quantidade":   rng.integers(1, 11, size=N_ROWS, dtype=np.int64),
    })

    usuarios = pd.DataFrame({
        "user_id": np.arange(N_USERS, dtype=np.int64),
        "tier":    rng.choice(["bronze", "prata", "ouro", "diamante"], size=N_USERS),
        "score":   np.round(rng.uniform(0, 100, size=N_USERS), 1),
    })

    if os.path.exists(CSV_PATH) and os.path.exists(PARQUET_PATH):
        print("Arquivos já existem, pulando regeração da tabela de fatos.")
    else:
        print("Salvando CSV e Parquet em disco...")
        fato.to_csv(CSV_PATH, index=False)
        fato.to_parquet(PARQUET_PATH, index=False)
    return usuarios


# --------------------------- Cronômetro ---------------------------
def bench(func, n_runs=N_RUNS, warmup=WARMUP):
    for _ in range(warmup):
        func()
    tempos = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        func()
        tempos.append(time.perf_counter() - t0)
    return statistics.median(tempos)


def main():
    usuarios_pd = gerar_dados()

    # Carrega uma vez em memória (operações in-memory reusam estes frames)
    df_pd = pd.read_csv(CSV_PATH)
    df_pl = pl.read_csv(CSV_PATH)
    usuarios_pl = pl.from_pandas(usuarios_pd)

    resultados = {}

    # 1) Leitura de CSV
    resultados["leitura_csv"] = {
        "pandas": bench(lambda: pd.read_csv(CSV_PATH)),
        "polars": bench(lambda: pl.read_csv(CSV_PATH)),
    }

    # 2) Leitura de Parquet
    resultados["leitura_parquet"] = {
        "pandas": bench(lambda: pd.read_parquet(PARQUET_PATH)),
        "polars": bench(lambda: pl.read_parquet(PARQUET_PATH)),
    }

    # 3) Filtro (valor > 500)
    resultados["filtro"] = {
        "pandas": bench(lambda: df_pd[df_pd["valor"] > 500]),
        "polars": bench(lambda: df_pl.filter(pl.col("valor") > 500)),
    }

    # 4) GroupBy + agregação por categoria
    resultados["groupby_agg"] = {
        "pandas": bench(lambda: df_pd.groupby("categoria")["valor"]
                                     .agg(["sum", "mean", "count"])),
        "polars": bench(lambda: df_pl.group_by("categoria").agg([
            pl.col("valor").sum().alias("soma"),
            pl.col("valor").mean().alias("media"),
            pl.col("valor").count().alias("contagem"),
        ])),
    }

    # 5) Join com a tabela de usuários
    resultados["join"] = {
        "pandas": bench(lambda: df_pd.merge(usuarios_pd, on="user_id", how="left")),
        "polars": bench(lambda: df_pl.join(usuarios_pl, on="user_id", how="left")),
    }

    # 6) Sort por valor (desc)
    resultados["sort"] = {
        "pandas": bench(lambda: df_pd.sort_values("valor", ascending=False)),
        "polars": bench(lambda: df_pl.sort("valor", descending=True)),
    }

    # 7) Consulta complexa EM MEMÓRIA (dados já carregados): filtro->groupby->sort
    def pandas_complexo():
        return (df_pd[df_pd["valor"] > 100]
                .groupby(["categoria", "regiao"])
                .agg(total=("valor", "sum"), media_qtd=("quantidade", "mean"))
                .reset_index()
                .sort_values("total", ascending=False))

    def polars_complexo():
        return (df_pl.filter(pl.col("valor") > 100)
                     .group_by(["categoria", "regiao"])
                     .agg([pl.col("valor").sum().alias("total"),
                           pl.col("quantidade").mean().alias("media_qtd")])
                     .sort("total", descending=True))

    resultados["consulta_memoria"] = {
        "pandas": bench(pandas_complexo),
        "polars": bench(polars_complexo),
    }

    # 8) PIPELINE COMPLETO: ler do disco + filtro + groupby + sort.
    #    Aqui o LAZY do Polars brilha: scan_csv + optimizer faz projection/
    #    predicate pushdown — só lê as colunas/linhas necessárias.
    def pandas_pipeline():
        df = pd.read_csv(CSV_PATH)
        return (df[df["valor"] > 100]
                .groupby(["categoria", "regiao"])
                .agg(total=("valor", "sum"), media_qtd=("quantidade", "mean"))
                .reset_index()
                .sort_values("total", ascending=False))

    def polars_lazy_pipeline():
        return (pl.scan_csv(CSV_PATH)
                  .filter(pl.col("valor") > 100)
                  .group_by(["categoria", "regiao"])
                  .agg([pl.col("valor").sum().alias("total"),
                        pl.col("quantidade").mean().alias("media_qtd")])
                  .sort("total", descending=True)
                  .collect())

    resultados["pipeline_completo"] = {
        "pandas": bench(pandas_pipeline),
        "polars": bench(polars_lazy_pipeline),
    }

    # --------------------------- Relatório ---------------------------
    info = {
        "n_linhas": N_ROWS,
        "n_usuarios": N_USERS,
        "n_runs": N_RUNS,
        "cpu_cores": os.cpu_count(),
        "polars_threads": pl.thread_pool_size(),
        "polars": pl.__version__,
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "python": platform.python_version(),
        "maquina": platform.platform(),
    }

    print("\n" + "=" * 64)
    print(f"  Ambiente: {info['cpu_cores']} core(s) de CPU | "
          f"Polars usando {info['polars_threads']} thread(s)")
    print(f"  polars {info['polars']} | pandas {info['pandas']} | "
          f"{info['n_linhas']:,} linhas | mediana de {info['n_runs']} execuções")
    print("=" * 64)
    print(f"{'Operação':<22}{'pandas (s)':>12}{'polars (s)':>12}{'speedup':>10}")
    print("-" * 64)
    for op, t in resultados.items():
        sp = t["pandas"] / t["polars"]
        print(f"{op:<22}{t['pandas']:>12.4f}{t['polars']:>12.4f}{sp:>9.1f}x")
    print("=" * 64)

    with open("resultados.json", "w") as f:
        json.dump({"info": info, "resultados": resultados}, f, indent=2)
    print("\nSalvo em resultados.json")


if __name__ == "__main__":
    main()
