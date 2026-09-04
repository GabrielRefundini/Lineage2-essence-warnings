# Itens adiados — Fase 02 (dashboard / calculadora de rotas)

## 16 falhas PRE-EXISTENTES no subsistema de party/bosses/agenda

**Descoberto durante:** a rodada unica de `python -m pytest -q --ignore=tests/test_agenda.py`
ao fim do plano 02-01, em 2026-09-03.

**Fora do alcance deste plano** (regra de SCOPE BOUNDARY): nenhum dos arquivos
envolvidos esta em `files_modified`, e nenhum deles e do workstream `dashboard`.

### As falhas

| Arquivo | Testes |
|---|---|
| `tests/test_janela_de_selecao.py` | `TestODrenoDaFilaDeTeclas::test_dreno_por_tempo_e_nao_por_numero_de_sondagens` |
| `tests/test_janela_no_relogio.py` | 7 testes (`TestAJanelaComOJogoFechado` x4, `TestOShellDoSoAgenda` x2, `TestAPrevisaoNoArranque` x1) |
| `tests/test_respawn.py` | `TestOMarcarEADecisaoDeDespachar` x2 |
| `tests/test_sessao.py` | `TestAFatiaInteiraDaJanelaDeRespawn` x3, `TestUmNascimentoUmaMensagem` x3 |

### A CAUSALIDADE FOI MEDIDA, E NAO SUPOSTA

Esta fase mexeu em `l2scanner/config.py`, que os testes de `sessao` e de
`janela_no_relogio` CARREGAM — entao "eles nao importam o que eu mudei" nao
bastava como argumento, e foi conferido em vez de afirmado.

**A medicao:** a versao de `l2scanner/config.py` ANTERIOR a esta fase
(`git show bfbb5ab:l2scanner/config.py`) foi colocada no lugar e os quatro
arquivos rodaram de novo. Resultado **identico**: `15 failed, 264 passed` nos
dois casos, o mesmo conjunto de testes. A mudanca desta fase nao e a causa.

### O que parece ser

As falhas tem cara de **dependencia de data**. O material fixo desses testes
esta cravado em 2026-08-30/31 (`NASCIMENTO = datetime(2026, 8, 30, 14, 30)` em
`tests/test_respawn.py:51`), e hoje sao **2026-09-03** — quatro dias depois. Os
sintomas sao todos de aviso que deixou de sair (`assert (0 + 0) == 1`, "o mesmo
aviso saiu em dobro, ou nao saiu de ninguem"), que e o que uma janela de
respawn ja vencida produziria.

**ISTO E UMA HIPOTESE, E NAO UMA MEDICAO.** Ninguem congelou o relogio para
confirmar. Quem for consertar comeca por ai, e nao por este paragrafo.

### O que NAO fazer

Nao consertar dentro de um plano do workstream `dashboard`. Sao dois
subsistemas diferentes, e um conserto de relogio no caminho de party/bosses
merece o proprio plano — com a medicao que falta acima.
