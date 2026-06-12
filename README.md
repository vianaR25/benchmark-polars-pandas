# 🐻‍❄️ Polars vs 🐼 Pandas — Benchmark Honesto

Comparação de performance entre **Polars** e **Pandas** em operações comuns de um
pipeline de dados, com **10 milhões de linhas**, rodada em um **MacBook Air M2
(8 núcleos)**. O objetivo não é "provar" que uma biblioteca é melhor, e sim
**medir com método** e entender *por que* e *quando* cada uma vence.

> Projeto nasceu de uma conversa com o Eduardo, que me apresentou o Polars. 🙏

## 📊 Resultados (MacBook Air M2 · 8 threads)

<!-- RESULTADOS_INICIO -->
Rodado em **8 núcleo(s) de CPU** (Polars usando 8 thread(s)) · pandas 3.0.3 · polars 1.41.2 · Python 3.13.2 · 10,000,000 linhas · mediana de 7 execuções.

| Operação | pandas (s) | Polars (s) | Speedup |
|----------|-----------:|-----------:|--------:|
| Leitura CSV | 4.88 | 0.50 | **9.9x** |
| Leitura Parquet | 0.18 | 0.08 | **2.3x** |
| Filtro | 0.07 | 0.01 | **5.3x** |
| GroupBy + agreg. | 0.36 | 0.19 | **1.9x** |
| Join | 0.75 | 0.13 | **5.8x** |
| Ordenação | 3.33 | 0.51 | **6.5x** |
| Consulta complexa (em memória) | 0.96 | 0.11 | **9.0x** |
| Pipeline completo (ler + processar) | 6.35 | 1.01 | **6.3x** |
<!-- RESULTADOS_FIM -->

![Benchmark](benchmark_polars_pandas.png)

## 🔎 O que os números mostram

- **No M2 (8 núcleos), o Polars venceu todas as operações** — de **1.9x** (GroupBy)
  a **~10x** (leitura de CSV e consulta complexa em memória).
- **Os maiores ganhos foram em I/O e em operações pesadas:** leitura de CSV (9.9x),
  consulta complexa em memória (9.0x), ordenação (6.5x), pipeline completo (6.3x)
  e join (5.8x). São justamente as operações que mais se beneficiam de
  **paralelismo + formato colunar Apache Arrow + engine em Rust**.
- **O menor ganho foi o GroupBy (1.9x) — e isso é o detalhe mais revelador.**
  Rodando a *mesma máquina* em **1 thread**, o pandas 3.0 chega a *empatar* no
  GroupBy. Ou seja: boa parte da vantagem do Polars vem do **multi-core**, e o
  GroupBy do pandas 3.0 é eficiente o bastante pra quase neutralizar a diferença
  quando há só um núcleo.
- **O modo `lazy` é o trunfo do pipeline.** Com `scan_csv`, o otimizador faz
  *predicate/projection pushdown* (lê só as colunas e linhas necessárias). Por isso
  o "ler do disco + processar" rende 6.3x mesmo incluindo a leitura.
- **Cuidado com benchmark injusto:** comparar Polars lazy (que inclui a leitura)
  contra pandas operando sobre dados já em memória dá um resultado enganoso. Aqui
  separei "em memória" de "pipeline completo".

## ⚖️ Single-thread vs multi-core: a comparação honesta

A crítica nº 1 desse tipo de benchmark é *"Polars só ganha porque usa todos os
núcleos"*. Dá pra responder com dado, na **mesma máquina**, rodando duas vezes:

```bash
# 1 thread (neutraliza o paralelismo) — o GroupBy do pandas chega a empatar
POLARS_MAX_THREADS=1 python benchmark.py && python grafico.py
cp benchmark_polars_pandas.png bench_1thread.png

# todos os núcleos (8 no MacBook Air M2) — o Polars dispara
python benchmark.py && python grafico.py
cp benchmark_polars_pandas.png bench_multicore.png
```

> As duas execuções sobrescrevem `resultados.json` / `.png`. Renomeie entre elas
> para guardar os dois gráficos.

## ▶️ Como rodar (Mac — Apple Silicon)

```bash
# 1) entre na pasta do projeto
cd caminho/para/benchmark-polars-pandas

# 2) crie e ative um ambiente virtual (recomendado)
python3 -m venv .venv
source .venv/bin/activate

# 3) instale as dependências (todas têm wheels nativos arm64)
pip install -r requirements.txt

# 4) rode o benchmark (gera ~490 MB de dados na 1a vez) e o gráfico
python benchmark.py
python grafico.py
```

O `grafico.py` atualiza a tabela de resultados acima automaticamente com os
números da execução. Ajuste `N_ROWS` no topo de `benchmark.py` para testar outros
volumes.

## 🚀 Como publicar no GitHub

> Os comandos abaixo você roda na sua máquina (suas credenciais ficam com você).
> O `.gitignore` já exclui os ~490 MB de dados gerados, então o repo fica leve.

**Opção A — GitHub CLI (`gh`), mais rápida:**

```bash
# uma vez só: gh auth login
git init
git add .
git commit -m "Benchmark Polars vs Pandas em 10M de linhas (MacBook Air M2)"
gh repo create benchmark-polars-pandas --public --source=. --push
```

**Opção B — manual:**

```bash
# 1) crie um repositório VAZIO em https://github.com/new (sem README/licença)
# 2) na pasta do projeto:
git init
git add .
git commit -m "Benchmark Polars vs Pandas em 10M de linhas (MacBook Air M2)"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/benchmark-polars-pandas.git
git push -u origin main
```

## 🧪 Metodologia

- Mesmas operações, com **código idiomático** de cada biblioteca.
- **Warm-up** (2 execuções descartadas) + **mediana de 7 execuções** (robusta a outliers).
- Dados sintéticos com `seed` fixa (reprodutível).
- Comparação de leitura em **CSV e Parquet**, e de **eager vs lazy**.
- Ambiente: MacBook Air M2 (8 núcleos) · macOS · pandas 3.0.3 · polars 1.41.2 · Python 3.13.2.

## 📦 Estrutura

```
benchmark.py     # geração de dados + benchmark
grafico.py       # gera o gráfico e atualiza a tabela do README
resultados.json  # saída bruta da última execução
requirements.txt
.gitignore
```

---
Feito por um estudante de Ciência de Dados & IA aprendendo na prática.
Sugestões e críticas são MUITO bem-vindas. 🚀
