---
phase: 01-funda-o-firewall-gravador-e-spike-de-campo
workstream: mercado
fixed_at: 2026-08-28
review_path: .planning/workstreams/mercado/phases/01-funda-o-firewall-gravador-e-spike-de-campo/01-REVIEW.md
iteration: 1
findings_in_scope: 18
fixed: 18
skipped: 0
status: all_fixed
suite_before: "1457 passed, 2 skipped"
suite_after: "1558 passed, 2 skipped"
---

# Phase 01: Code Review Fix Report

**Escopo:** Critical + Warning. Os 6 INFO ficaram fora, por decisao do pedido.
**Suite:** `python -m pytest tests/ -q` — de **1457 passed, 2 skipped** para
**1558 passed, 2 skipped**. Zero regressoes; 101 testes novos, todos verificados
falhando ANTES do fix correspondente.

**Onde os portoes rodaram:** no **checkout principal**
(`C:\Users\refun\Desktop\Lineage2-warnings`), depois do fast-forward. O trabalho
foi feito num worktree isolado (`.claude/worktrees/rf-01-*`), onde a suite dava
`1552 passed, 8 skipped` — os 6 skips a mais sao os testes que exigem
`recordings/`, que e gitignored e nao se materializa num worktree. Os numeros
acima, e a medicao de janela do CR-01, sao do checkout principal e sao
reproduziveis la.

## Resumo

- Achados no escopo: 18 (5 BLOCKER + 13 WARNING)
- Corrigidos: 18
- Rejeitados: 0
- Corrigidos com a alternativa mais barata, e a cara documentada: 1 (WR-08)

## BLOCKERs

### CR-01: `WINDOW_NORMAL` encolhia a area de desenho

**Arquivos:** `l2scanner/calibrar.py`, `l2scanner/calibrar_mercado.py`,
`tests/test_janela_de_selecao.py` (novo)
**Commit:** `b664522`

`cv2.WINDOW_AUTOSIZE` no lugar de `WINDOW_NORMAL`, nos dois sites. O
`moveWindow(40, 40)` FICOU — ele resolvia um problema real (janela nascendo onde
o usuario nao a achava, numa maquina de dois monitores) e posiciona igual sobre
AUTOSIZE. So o flag estava errado.

**Medicao, no caminho real de `_selecionar_regiao`** (`getWindowImageRect` lido
de dentro da funcao, com o `selectROI` dublado), cv2 4.14.0:

| visao | WINDOW_NORMAL | WINDOW_AUTOSIZE |
|---|---|---|
| 1600x1295 | **120x1440** | 1600x1295 |
| 1720x1392 | **120x1440** | 1720x1392 |
| 3440x1440 -> visao 1600x670 | **120x1440** | 1600x670 |
| 800x600 | **120x1440** | 800x600 |

O numero do NORMAL nem e estavel entre execucoes — a revisao mediu 304x281, eu
medi 120x1440 — justamente porque nao vem da imagem, e sim do Win32. Essa
instabilidade e o argumento.

**Party 1:1 confirmado:** frame 1440x900 (abaixo do limite de reescala de 1600)
-> janela 1440x900, e a caixa desenhada volta identica: `(10,20,100,50)` entra,
`(10,20,100,50)` sai.

Junto veio o IN-02 de graca: os dois blocos de comentario fundidos (o do
posicionamento e o do dreno de teclas) foram separados e colados cada um no seu
codigo.

### CR-02: a promessa de uma imagem de conferencia que pode nao existir

**Arquivos:** `l2scanner/calibrar_mercado.py`, `calibrar-mercado.bat`,
`tests/test_calibrar_mercado.py`, `tests/test_calibrar_mercado_bat.py`
**Commit:** `32facaa`

`_texto_final_da_conferencia(caminho, arquivo)`, no molde do
`calibrar._texto_final_do_solo`. Com imagem, manda abrir **o caminho que foi
gravado** (inclusive o alternativo com horario). Sem imagem, diz que a
conferencia nao aconteceu, **diz que os retangulos JA ESTAO no
calibration.json** — o `cal.salvar` roda antes — e nao cita nome de PNG nenhum,
pela mesma regra de `_gravar_conferencia`.

O `.bat` parou de citar `calibracao-conferencia.png`: ele nao sabe qual foi. Ha
um teste que proibe qualquer `echo` do .bat de nomear a imagem.

### CR-03: matriz "APROVADA" sobre zero comparacoes, e limiar 0.5 gravado

**Arquivos:** `l2scanner/calibrar_mercado.py`, `tests/test_calibrar_mercado.py`
**Commit:** `e671329`

`pior_score` e `limiar_sugerido` viraram `float | None`, `None` quando nao houve
par. A propriedade `rodou` diz isso explicitamente e `explicar()` imprime
"Matriz de confusao NAO RODOU: 0 pares para comparar". A gravacao do limiar
ficou condicional — o que ja estava no arquivo fica como esta.

### CR-04: rodar sem watchlist apagava os moldes de nome

**Arquivos:** `l2scanner/calibrar_mercado.py`, `tests/test_calibrar_mercado.py`
**Commit:** `4da91f1`

So escreve `mercado_templates_de_nome` quando ha molde cortado; senao preserva e
avisa quantos manteve. A mensagem de "sem watchlist" passou a dizer a verdade
sobre a preservacao. Recortar de novo continua substituindo — e assim que o
usuario conserta um molde ruim.

Os testes rodam `calibrar()` **de ponta a ponta pela primeira vez no projeto**,
com dubles so em `_selecionar_regiao` (exige mao humana) e `_gravar_conferencia`
(escreveria na raiz do repo).

### CR-05: o portao do spike contava `NAO VERIFICADO` como `VERIFICADO`

**Arquivos:** `tools/conferir_spike_respostas.py`,
`tests/test_conferir_spike_respostas.py` (novo — WR-11)
**Commit:** `7da9b26`

`NEGACAO_DE_SELO` rebaixa toda negacao explicita (`NAO VERIFICADO`, `NAO
PARCIAL`, com ou sem til) para `NAO RESPONDIDO` ANTES da contagem, e a ordem de
busca ficou explicita em `ORDEM_DE_BUSCA`.

Rodado contra o `SPIKE-RESPOSTAS.md` real: **APROVADO, 9 secoes, 43 caminhos
resolvidos, mesma tabela de antes** — nenhuma resposta do usuario foi rebaixada
por engano.

## WARNINGs

| ID | O que mudou | Commit |
|---|---|---|
| WR-01 | `ancoras_para_calibracao` grava `altura`/`largura` ao lado do molde; `ancoras_de_calibracao` passa `forma_esperada`. Molde transposto agora e recusado no caminho de PRODUCAO. Compat: arquivo antigo carrega sem a conferencia. | `679ef56` |
| WR-02 | `evidencia_resolvida()`: recusa `..` nas partes do caminho e exige `is_file()`. `recordings/../l2scanner/visao.py` resolvia `True`. | `e9ecfde` |
| WR-03 | `waitKeyEx` antes de mascarar; codigos GTK 81-84 removidos (`S` maiusculo andava para FRENTE). Setas MEDIDAS por injecao de VK_*. | `d7df1b7` |
| WR-04 | `waitKeyEx(50)` + `WND_PROP_VISIBLE`; fechar no X levanta em vez de travar para sempre. Aviso "NAO feche no X" na ajuda. | `d7df1b7` |
| WR-05 | `esvaziar_a_fila_de_teclas(0.15)`: dreno POR TEMPO, nao ate o primeiro `-1`. | `f5a2df2` |
| WR-06 | TOML invalido, `watchlist` do tipo errado e falha de `cal.salvar` viram `MercadoNaoCalibravel`. Watchlist lida ANTES da primeira janela. | `2c2fca8` |
| WR-07 | Aviso de DPI em `main()`, dizendo o que torna esta instancia pior: aqui as coordenadas erradas vao para o disco. | `2c2fca8` |
| WR-08 | Molde da ancora indexado por NOME; comentario de `ANCORAS_SUGERIDAS` corrigido. | `ee9e9bf` |
| WR-09 | Grade degenerada recusada; divergir de `LINHAS_ESPERADAS` (10/10/9, medido em campo) avisa alto. | `d89436d` |
| WR-10 | Falha da leitura do mercado: um `WARNING` com `exc_info`, depois `DEBUG` — mesmo trilho do vizinho. | `c230d0d` |
| WR-11 | `tests/test_conferir_spike_respostas.py`, 25 testes. | `7da9b26` + `e9ecfde` |
| WR-12 | `Calibracao.salvar` escreve `.json.tmp` ao lado e faz `os.replace`. Atomico, e todos os escritores herdam. | `dc3ef6c` |
| WR-13 | Codigos de saida 10/11/12; qualquer outro vira `CRASH (codigo N)` e "CONCLUSAO: NENHUMA". | `b37faeb` |

## A metade cara do WR-08, que NAO foi paga

A revisao ofereceu duas saidas: **desenhar** o retangulo sugerido sobre o frame
antes do arrasto (cumprindo a docstring, e uma defesa real contra o CR-01), ou
**corrigir a docstring**. Escolhi a segunda.

Motivo: pre-desenhar exigiria mudar a assinatura de
`calibrar._selecionar_regiao`, que e COMPARTILHADA com a calibracao de party e
funciona hoje — a restricao mais cara desta fase. O comentario agora diz o que a
ferramenta faz E por que a alternativa nao foi paga, para o proximo nao achar
que foi esquecimento.

## O que precisa da sua mao

### 1. O `calibration.json` de hoje JA carrega o dano do CR-03 e do CR-04

Os fixes impedem que aconteca de novo; eles nao desfazem o que ja esta gravado.
Lido agora do seu arquivo:

```
mercado_templates_de_nome : []        <- CR-04 ja apagou (ou nunca cortou)
mercado_limiar_de_template: 0.5       <- CR-03: o numero inventado, no disco
mercado_ancoras           : sem altura/largura (formato antigo, WR-01)
```

`0.5` para casamento de nome casa quase tudo — o pior inter-classe que o proprio
modulo tolera e 0.85. **Nao editei o arquivo**: ele e estado de maquina, e a
regra do ROADMAP e "sem editar JSON a mao". Para consertar, escreva a watchlist
no `config.toml` e rode `calibrar-mercado.bat` de novo — a rodada nova mede o
limiar de verdade e grava `altura`/`largura` nas ancoras, ligando a conferencia
de forma do WR-01.

### 2. O CR-01 continua exigindo um arrasto seu

Eu medi que a JANELA voltou a ter o tamanho da imagem, com o `selectROI`
dublado. O que nenhum agente consegue medir e se o retangulo que a SUA mao
desenha cai onde voce quer — isso e mouse humano, e a restricao ja estava
registrada em `.planning/debug/resolved/selectroi-devolve-caixa-vazia.md`.

Rode `calibrar.bat` e confira que a janela abre no tamanho do frame.

### 3. As setas do navegador de frames

Medi os codigos por injecao (`PostMessageW` com VK_LEFT/RIGHT/UP/DOWN):
`waitKey` devolve 0 para as quatro, `waitKeyEx` devolve 2555904/2424832/2490368/
2621440. O codigo agora le `waitKeyEx`. **Teclado fisico eu nao consigo
testar** — vale um toque nas setas na proxima vez que abrir o navegador.

## Um defeito PRE-EXISTENTE que apareceu no caminho (fora do escopo)

`tests/test_agenda.py` tem um flake: **5 falhas em 60 rodadas** do arquivo
sozinho, **no commit base `1890ff2`, no checkout principal, sem nenhuma
mudanca minha**. O sintoma e um `KeyboardInterrupt` que escapa e aborta a
sessao inteira do pytest, atribuido a `test_agenda.py:1141` — o
`raise KeyboardInterrupt` do duble de `time.sleep`.

Mecanismo provavel: `monkeypatch.setattr(principal.time, "sleep", ...)` troca o
`time.sleep` GLOBAL, e o `laco_da_agenda` deixa alguma coisa viva que ainda o
chama; o plugin `threadexception` do pytest ressuscita a excecao contra o teste
que estiver rodando naquele instante. Nao esta no `01-REVIEW.md` e nao toquei
nele.

**Consequencia pratica:** uma rodada de `pytest` pode abortar por volta de 88
testes sem nenhuma falha real. Rodar de novo resolve. Ate ser consertado, um
verde vale; um "KeyboardInterrupt" nao e uma reprovacao.

---

_Fixed: 2026-08-28_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
