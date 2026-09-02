# Fase 1: Dashboard do cambio ao vivo — Pesquisa

**Pesquisado:** 2026-09-01
**Workstream:** dashboard
**Dominio:** servidor local da stdlib + leitura concorrente de CSV no Windows + grafico vendorizado
**Confianca geral:** ALTA — quase tudo aqui foi **medido nesta maquina**, com o comando e a saida ao lado

> **Como ler este documento.** A casa escreve "medido, nao suposto". Cada afirmacao carrega uma
> etiqueta: `[VERIFICADO: <comando/arquivo:linha>]` quando eu rodei e vi, `[CITADO: <url>]` quando
> veio de fonte oficial, `[SUPOSTO]` quando e memoria de treino. **Tres suposicoes do CONTEXT.md e
> do UI-SPEC.md foram REFUTADAS por medicao** — elas estao marcadas com 🔴 e a medicao esta junto.

---

<user_constraints>
## User Constraints (do 01-CONTEXT.md)

### Locked Decisions — pesquisar ESTAS, nao alternativas

**A superficie — o que aparece na tela**

- **Layout:** numero grande no topo (o valor de agora), grafico abaixo, rodape com a
  procedencia (`n`, recencia, cambio informado e quando). A pergunta do usuario e uma so,
  entao uma coisa domina a tela.
- **Dois numeros no destaque, lado a lado:** **XM por milhao** (a unidade que ele fala em voz
  alta, ja implementada em `mercado_console.formatar_taxa_derivada`) **e R$ por milhao**. Os
  dois carregam `n` e recencia, como toda a disciplina do console de mercado exige.
- **Tema escuro E TEMATICO DE LINEAGE 2.** Nao e um dashboard generico de analytics: e um painel
  do jogo. **O tema nunca custa legibilidade do numero**: se um ornamento disputar com o valor em
  destaque, o ornamento sai.
- **Estado vazio e conteudo, nao ausencia.** Hoje o CSV tem 93 linhas e **zero** com a sentinela
  `adena#`. Sem leitura da Adena, a pagina diz isso com todas as letras e explica como coletar.
  **Grafico vazio mudo esta proibido.**

**O dado e a atualizacao**

- **Atualizacao por polling:** o navegador consulta um endpoint JSON local a cada ~2s; o servidor
  rele o CSV quando `mtime`/tamanho mudam. Sem WebSocket, sem SSE.
- **O arquivo inteiro e carregado.** 93 linhas hoje, crescendo devagar. Filtrar o zoom no navegador
  e mais simples e mais correto que paginar no servidor.
- **Um ponto do grafico e um instante de leitura** (`primeira_vez`), com o menor pedido visivel e a
  mediana daquele instante — exatamente a conta que o console ja faz via `mercado_analise`.
- **Zoom largo agrega com `median_low`**, nunca media. E o D-02 do projeto.

**O cambio XM → BRL**

- **Persiste em `.mercado/cambio.json`**, escrito pelo dashboard. Fora do `calibration.json` e fora
  do `config.toml` (o `tomllib` da stdlib e read-only). `localStorage` foi recusado.
- **A entrada e em reais por 1 XM** (`0,50`).
- **Cada alteracao e guardada com carimbo**, e a ultima e a vigente.
- **Os pontos historicos em R$ usam o cambio de hoje**, com o aviso na tela.

**O processo, o servidor e a prova**

- **`http.server` da stdlib — zero dependencia Python nova.** Nada entra no `requirements.txt`.
- **A biblioteca de grafico JS e vendorizada na arvore** (arquivo unico, sem CDN, sem rede), com
  proveniencia escrita (nome, versao, licenca, de onde veio).
- **Bind em `127.0.0.1` apenas, nunca `0.0.0.0`**, em porta fixa. O `.bat` abre o navegador sozinho.
- **A unica escrita do servidor e o `.mercado/cambio.json`.** O `observacoes.csv` e aberto em modo
  leitura, e ha teste provando que tamanho e mtime nao mudam depois de uma sessao.
- **A prova sem navegador** e por testes sobre o endpoint JSON e sobre as funcoes de agregacao
  (puras). O desenho na tela fica como **verificacao humana declarada**. Playwright foi recusado.

### Claude's Discretion — pesquisar opcoes e recomendar

- Nome do modulo, nome do endpoint, porta escolhida, e qual biblioteca de grafico exatamente
  (o criterio e: arquivo unico, licenca permissiva, zoom/pan nativo, sem dependencia de rede).
- A forma interna do JSON servido e a estrutura do `cambio.json`.
- Como o componente de serie e generalizado (DASH-05) — so o resultado esta travado.

### Deferred Ideas (FORA DE ESCOPO — ignorar completamente)

- Coleta automatica do cambio XM→BRL pelo listener dos grupos de venda do WhatsApp.
- A aba de negociacao na tela.
- Acesso pelo celular / pela rede.
- Cambio de epoca aplicado a cada ponto historico.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Descricao (de REQUIREMENTS.md) | O que desta pesquisa sustenta a implementacao |
|----|-------------|------------------|
| **DASH-01** | Superficie somente-leitura sobre o CSV; le ate a ultima linha completa; nao exibe linha parcial; divergencia escrita no fonte | §2 inteira. A prova de somente-leitura esta medida (0 mudanca de `size/mtime_ns/sha256` em 300 leituras); a degradacao correta e o corte em `rfind("\n")` **antes** do portao do terminador; e 🔴 **a premissa da frequencia esta refutada** — o escritor abre/escreve/fecha por linha e nenhuma leitura parcial foi observada em 22.970 tentativas |
| **DASH-02** | Taxa XM→BRL manual, editavel, persistida; todo R$ declarado como informado; sem taxa, R$ indisponivel | §7 (POST + `os.replace` atomico medido em 9,18 ms) e o **Pitfall 5**, que mede que `Decimal` sozinho aceita `1e3` → 1000 e `1_0` → 10 |
| **DASH-03** | Linha do tempo com zoom, duas linhas, numeros batendo com o console, sem segundo parser | §1 (reuso de `mercado_analise`/`mercado_console` sem arrastar captura), §6 (agregacao `median_low` sobre `Fraction`, bucketizacao sem float) e §4 (a biblioteca). ⚠ **Ha uma divergencia semantica entre "o numero do console" e "o ponto do grafico" que o plano precisa resolver** — ver Open Question 1 |
| **DASH-04** | Valor de agora em destaque com `n` e recencia; nunca afirma "agora" sobre numero velho | §1: `menor_pedido_visivel`, `mediana_dos_unitarios`, `recencia_do_preco`, `Evidencia` e `_recencia_em_duas_formas` sao reutilizaveis; a string vem pronta do Python |
| **DASH-05** | Componente de serie generico; segunda instancia sem codigo de grafico novo; provado em teste | §4 (a config das tres candidatas e por-serie, entao a generalidade e estrutural) e §8 (o teste que instancia a segunda serie roda sobre o **JSON servido**, sem navegador) |
| **DASH-06** | Lancador proprio, processo separado, caminho do `--mercado` byte-identico | §1 (o corte de `RAIZ` e a unica mudanca proposta em arquivo do mercado — **e ela toca `mercado_catalogo.py`**, o que exige decisao explicita do planejador: ver Open Question 2) e §3/§9 (o molde do `.bat`) |
</phase_requirements>

---

## Summary

Esta fase tem **zero dependencia Python nova** e **um** artefato de terceiro (um `.js`
vendorizado). O risco tecnico nao esta onde o CONTEXT supos que estivesse.

**O que eu media achando que era o problema, e nao era.** A leitura concorrente do CSV enquanto o
scanner apenda parecia o ponto quente: o ROADMAP diz que "o dashboard cairia em cegueira toda vez
que pegasse o arquivo no meio de uma escrita". **Medido: nao cai.** O escritor
(`mercado_registro.registrar`) abre, escreve UMA linha, da `flush` e **fecha** — por linha. Em
22.970 leituras de cauda durante 200.000 appends concorrentes, **zero** leituras sem terminador e
**zero** erros de abertura. Uma sonda de controle com escrita deliberadamente rasgada acusou 3.252
de 4.079, entao a sonda funciona e o zero e resultado, nao cegueira. A regra "leio ate a ultima
linha completa" continua **certa** — ela cobre edicao a mao no Sheets e queda de energia — mas ela e
**rede de seguranca**, nao o caminho normal, e o fonte tem de dizer isso.

**O que realmente e o problema, medido.** Tres coisas:

1. **A cadeia de import.** `import l2scanner.mercado_registro` traz **280 modulos novos, incluindo
   `cv2` e `numpy`**, e custa 175–371 ms e ~44 MB de working set. A cadeia e
   `mercado_catalogo` → `config` (so por `RAIZ`) → `notificador` → `rastreador` → `visao` → `cv2`.
   Uma mudanca de **duas linhas** (um modulo-folha `raiz.py` + trocar `from .config import RAIZ`
   por `from .raiz import RAIZ` em `mercado_catalogo.py:95`) derruba para **52 modulos, zero
   pesados, 40 ms, 17,3 MB** — medido nas duas arvores.
2. **`http.server.HTTPServer.allow_reuse_address` vale `1` por padrao**, e no Windows
   `SO_REUSEADDR` significa *roubar a porta*: dois `dashboard.bat` abertos **bindam a mesma porta
   sem erro nenhum** e o navegador fala com quem ganhar a corrida. Medido. Com
   `allow_reuse_address = False` o segundo bind levanta `OSError` `errno 10048`, que e o que da
   para mostrar ao usuario.
3. **Nenhuma das duas bibliotecas de grafico da classe uPlot tem zoom por roda do mouse nativo.**
   O UI-SPEC afirma "Roda do mouse e arrasto, pela biblioteca. Toda biblioteca dessa classe faz
   isso com config" — 🔴 **falso**. Medido sobre os `.min.js` baixados: `uPlot.iife.min.js` registra
   `click/dblclick/mousedown/mouseenter/mouseleave/mousemove/mouseup/resize/scroll` e **nenhum**
   `wheel`; `dygraph.min.js` idem. So `lightweight-charts` tem `wheel`. E a documentacao oficial do
   uPlot confirma: "No built-in drag scrolling/panning"; wheel zoom "can be added externally via
   the plugin/hooks API".

**Recomendacao primaria:** cortar a cadeia de `RAIZ` como primeira tarefa da fase (ela desbloqueia
tudo e e barata), montar o servidor sobre `ThreadingHTTPServer` com `allow_reuse_address = False`
e um `SimpleHTTPRequestHandler(directory=...)` com listagem desligada, e escolher a biblioteca de
grafico **sabendo que uPlot custa ~25 linhas de wheel-zoom nossas** — o que ainda pode ser a
escolha certa, porque em compensacao ele e o unico dos tres com **zero** primitivas de rede no
fonte (VEND-2 passa limpo, medido).

---

## Architectural Responsibility Map

| Capacidade | Camada primaria | Camada secundaria | Por que essa camada e a dona |
|------------|-------------|----------------|-----------|
| Ler e tipar o CSV | Processo Python do dashboard | — | `mercado_registro.observacoes_do_arquivo` e o **unico** parser e tem que continuar sendo (DASH-03). Nada disso pode migrar para o JS. |
| Menor / mediana / recencia / `n` | Processo Python do dashboard | — | `mercado_analise`, puro, em `Fraction`. Refazer no JS seria float e um segundo formatador. |
| Formatar o numero exibido | Processo Python do dashboard | — | `formatar_taxa_derivada`, `formatar_centesimos`, `_recencia_em_duas_formas`. **O JS exibe como recebeu** (regra dura do UI-SPEC). |
| Agregar por balde de tempo (zoom) | Processo Python do dashboard | — | `median_low` sobre `Fraction` so existe no Python. Ver Open Question 3 sobre onde o corte fica. |
| Escolher a janela de zoom | Navegador (JS) | — | Decisao locked: "o arquivo inteiro e carregado; filtrar o zoom no navegador". |
| Desenhar eixos, grade, linhas, pan/zoom | Navegador (JS, biblioteca vendorizada) | — | Canvas. Nada disso da para afirmar sem navegador — e o que vira verificacao humana declarada. |
| Persistir o cambio | Processo Python do dashboard | — | `os.replace` atomico sobre `.mercado/cambio.json`. `localStorage` foi recusado no CONTEXT. |
| Validar o cambio digitado | Processo Python do dashboard | Navegador (so conveniencia) | **Falha fechada mora no servidor.** Validacao no JS e enfeite; um POST direto tem de ser recusado igual. |
| Servir os estaticos | Processo Python do dashboard | — | `file://` foi recusado na exploracao (nao consegue `fetch` do CSV). |
| Capturar tela | **NENHUMA** | — | O dashboard nao captura. Nem `mss`, nem `windows_capture`, nem `dxcam` entram neste processo. |

---

## Standard Stack

### Core — tudo stdlib, nada novo no `requirements.txt`

| Modulo | Versao | Proposito | Por que e o padrao aqui |
|---------|---------|---------|--------------|
| `http.server` (`ThreadingHTTPServer`, `SimpleHTTPRequestHandler`) | stdlib CPython **3.12.13** (.venv) / **3.12.10** (global) | Servidor local, estaticos e endpoint JSON | Decisao travada no CONTEXT. `ThreadingHTTPServer` e nao `HTTPServer`: com `HTTPServer` (serial) uma aba pendurada num `fetch` bloqueia o `GET` do proximo estatico. `[VERIFICADO: .venv/Scripts/python.exe --version → Python 3.12.13; python --version → Python 3.12.10]` |
| `json` | stdlib | Endpoint e `cambio.json` | O calibrador do mercado ja usa o mesmo par (`tomllib` le, `json` escreve). |
| `csv` + `io` | stdlib | Ja usados por `mercado_registro` — **nao reimplementar** | `observacoes_do_arquivo` e o unico parser (DASH-03). |
| `fractions.Fraction` | stdlib | Toda comparacao de preco | Regra da casa. `float` so aparece na fronteira do JSON, e isso e declarado (§6). |
| `statistics.median_low` | stdlib | Agregacao do zoom | `[VERIFICADO: medido]` sobre `Fraction`: devolve `Fraction` que **esta na lista** (n par e impar). `statistics.median` sobre os mesmos 4 valores devolveu `13/42`, que **nao esta na lista** — o D-02 violado, medido. |
| `decimal.Decimal` + `re` | stdlib | Ler o cambio digitado | `Decimal` **sozinho nao basta** — ver Pitfall 5. |
| `pathlib`, `os.replace`, `hashlib`, `threading`, `webbrowser`, `socket` | stdlib | Caminhos, escrita atomica, impressao digital, laco do servidor, abrir o navegador, sondar a porta | — |

### Suporte — o unico artefato de terceiro

| Artefato | Versao | Proposito | Quando usar |
|---------|---------|---------|-------------|
| Uma biblioteca de grafico JS **vendorizada** | ver §4 | Duas linhas, eixo temporal, zoom/pan | Sempre. A comparacao com numeros esta na §4; **a escolha e do planejador** (Claude's Discretion). |

### Alternativas consideradas

| Em vez de | Poderia usar | Tradeoff |
|------------|-----------|----------|
| `ThreadingHTTPServer` | `HTTPServer` (serial) | Mais simples, mas uma requisicao lenta trava a proxima. Custa uma palavra usar o threading. |
| `SimpleHTTPRequestHandler(directory=...)` | Servir os 4 arquivos com um `dict` na memoria | Mais controle e imune por construcao a travessia, mas perde `Last-Modified`/`If-Modified-Since` e reimplementa MIME. **Ambos aceitaveis**; o `directory=` foi medido seguro (§3). |
| Polling a 2 s | SSE (`text/event-stream`) | Recusado no CONTEXT. A medicao apoia: uma leitura completa do arquivo real custa **0,519 ms** — polling e ruido. |
| Cache por `mtime`/tamanho | Reler sempre | Hoje reler sempre e gratis (0,519 ms). **A 60.000 linhas custa 366 ms de parse + 174 ms de analise**, medido — a 2 s isso e ~27% de um nucleo. O cache e barato e evita a divida. |
| `os.replace` atomico no `cambio.json` | `open("w")` direto | O direto perde o arquivo inteiro se o processo morrer no meio. `os.replace` medido em **9,18 ms** com `fsync` — irrelevante para uma escrita por clique. |

**Instalacao:** nenhuma. `pip install` **nao acontece nesta fase**.

**Verificacao de versao:**

```bash
.venv/Scripts/python.exe --version   # medido: Python 3.12.13
python --version                     # medido: Python 3.12.10  (o que roda a suite)
```

> 🔴 **Refutacao de doutrina, registrada.** O `.claude/CLAUDE.md` prescreve **Python 3.13.x**. Esta
> maquina roda **3.12.13** no `.venv` e **3.12.10** no global. `[VERIFICADO: comandos acima]`.
> Nada nesta fase precisa de 3.13; tudo que ela usa existe desde 3.7 (`directory=` do
> `SimpleHTTPRequestHandler`) ou 3.11 (`allow_reuse_port`). Registrado para o documento nao
> envelhecer mentindo.

---

## Package Legitimacy Audit

**Pacotes Python instalados nesta fase: nenhum.** O `requirements.txt` nao muda. O `FIRE-01`
continua trivialmente satisfeito porque nada entra.

O portao se aplica ao **artefato JS vendorizado**. Rodado no ecossistema de origem (`npm`), com o
seam, sobre as tres candidatas:

```bash
node ~/.claude/gsd-core/bin/gsd-tools.cjs query package-legitimacy check \
  --ecosystem npm uplot dygraphs lightweight-charts
```

| Pacote | Registro | Publicado | Downloads/sem | Repositorio | `postinstall` | Veredito | Disposicao |
|---------|----------|-----|-----------|-------------|---|---------|-------------|
| `uplot` 1.6.32 | npm | 2025-03-14 | 560.268 | github.com/leeoniya/uPlot | `null` | **OK** | Aprovado |
| `dygraphs` 2.2.2 | npm | 2026-07-27 | 16.095 | github.com/danvk/dygraphs | `null` | **OK** | Aprovado, **mas reprova VEND-2** (ver §4) |
| `lightweight-charts` 5.2.1 | npm | 2026-08-12 | 939.089 | github.com/tradingview/lightweight-charts | `null` | **SUS** | `too-new` (3 semanas). Se escolhida, o planejador **precisa** de um `checkpoint:human-verify` antes, ou fixar uma versao mais antiga |

`[VERIFICADO: saida do seam, colada acima]`

**Removidos por veredito [SLOP]:** nenhum.
**Marcados [SUS]:** `lightweight-charts` 5.2.1 — `too-new`.

### VEND-1 — proveniencia ja medida, para o planejador nao ter que baixar de novo

| Arquivo | Bytes | SHA-256 | Licenca | Origem |
|---|---|---|---|---|
| `uPlot.iife.min.js` (v1.6.32) | **51.081** | `19c8d4c6ad88929a79f4ae49d6f7161566dfd0ba3d15cc495e974f787eb78f1f` | MIT | `https://cdn.jsdelivr.net/npm/uplot@1.6.32/dist/uPlot.iife.min.js` |
| `uPlot.min.css` (v1.6.32) | **1.857** | (nao baixado) | MIT | `https://cdn.jsdelivr.net/npm/uplot@1.6.32/dist/uPlot.min.css` |
| `dygraph.min.js` (v2.2.2) | **130.226** | `8492cbf8c87f99c2e30a9e7577b344370355974f9e47969f265623368d656242` | MIT | `https://cdn.jsdelivr.net/npm/dygraphs@2.2.2/dist/dygraph.min.js` |
| `lightweight-charts.standalone.production.js` (v5.2.1) | **197.922** | `e21cc5caa0226ef30bd8549c50b9ef926615f2a4ee6b4e486353477a55f598cf` | Apache-2.0 | `https://cdn.jsdelivr.net/npm/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js` |

`[VERIFICADO: curl -sIL <url> | grep content-length; sha256sum sobre os arquivos baixados]`

**Aviso para o VEND-1:** o SHA-256 registrado tem de ser recalculado **sobre o arquivo em disco na
arvore**, nao copiado daqui — se o planejador escolher outra versao ou outro `dist/`, os hashes
acima nao valem. E os hashes acima sao do arquivo do jsDelivr; se o download vier do GitHub
Releases o byte pode diferir (line endings), e ai o hash muda legitimamente.

### VEND-2 — varredura de primitivas, ja executada

```bash
for f in *.js; do for p in "fetch(" "XMLHttpRequest" "sendBeacon" "eval(" "new Function" \
  "import(" "createElement('script'" "WebSocket"; do grep -o -F "$p" "$f" | wc -l; done; done
```

| Arquivo | `fetch(` | `XMLHttpRequest` | `sendBeacon` | `eval(` | `new Function` | `WebSocket` | Veredito VEND-2 |
|---|---|---|---|---|---|---|---|
| `uPlot.iife.min.js` | 0 | 0 | 0 | 0 | 0 | 0 | ✅ **limpo** |
| `dygraph.min.js` | 0 | **2** | 0 | 0 | 0 | 0 | ⛔ **reprova** |
| `lightweight-charts.standalone.production.js` | 0 | 0 | 0 | 0 | 0 | 0 | ✅ limpo (mas 5× `navigator.userAgent`) |

`[VERIFICADO: grep sobre os arquivos baixados no scratchpad]`

O contexto exato do XHR do dygraphs, extraido do minificado:

```
"string"==i?M.detectLineDelimiter(a)?this.loadedEvent_(a):(t=window.XMLHttpRequest?
new XMLHttpRequest:new ActiveXObject("Microsoft.XMLHTTP"),...
```

Ou seja: dygraphs aceita **uma URL como fonte de dados** e a busca sozinho. Nao e telemetria — e
uma feature. Mas o VEND-2 do UI-SPEC diz "Qualquer ocorrencia → **revisao humana explicita e
registrada** antes de seguir; uma biblioteca de grafico nao precisa de nenhuma dessas primitivas".
Escolher dygraphs **obriga** essa revisao a acontecer e a ser escrita. A CSP (`connect-src 'self'`)
conteria o estrago, mas o portao e sobre o fonte, nao sobre a contencao.

---

## Architecture Patterns

### Diagrama do sistema — o fluxo do dado, nao a lista de arquivos

```
  [ processo do --mercado, INTOCADO ]              [ o usuario, no navegador ]
              |                                                |
       append linha a linha                          GET /  (2 s de polling)
       (open "a" -> writerow -> flush -> close)       POST /cambio (ao clicar)
              |                                                |
              v                                                v
   .mercado/observacoes.csv  <--- SOMENTE LEITURA ---  [ processo do dashboard ]
              ^                                          |    ^          |
              |                                          |    |          |
              +-- nunca escrito, provado por             |    |          |
                  (size, mtime_ns, sha256)               |    |          |
                                                          |    |          |
        .mercado/cambio.json  <--- os.replace atomico ----+    |          |
                                                               |          |
    ==============  DENTRO DO PROCESSO DO DASHBOARD  ==========|==========|====
                                                               |          |
  (1) le bytes  ->  (2) corta em rfind("\n")  ->  (3) conferir_o_cabecalho
       |                    |                              |
       |          [DASH-01] a divergencia                  v
       |          deliberada: NAO chamamos          (4) csv.reader + ObservacaoLida
       |          conferir_o_terminador sobre           (mercado_registro, UNICO parser)
       |          o bruto; cortamos ANTES,                  |
       |          e o corte torna o portao                  v
       |          verdadeiro por construcao          (5) agrupar por chave_da_serie
       |                                                    | (ModeloDeMercado)
       v                                                    v
  cache por (size, mtime_ns)                         (6) mercado_analise:
                                                        menor_pedido_visivel
                                                        mediana_dos_unitarios
                                                        recencia_do_preco  + Evidencia
                                                            |
                                          +-----------------+------------------+
                                          v                                    v
                            (7a) DESTAQUE de agora                (7b) SERIE por instante
                            formatar_taxa_derivada ->              agrupar por primeira_vez
                            string PRONTA, ASCII                   -> median_low por balde
                                          |                                    |
                                          +----------------+-------------------+
                                                           v
                                              (8) JSON: strings prontas
                                                  + numeros so para PIXEL
                                                           |
                                    CSP: default-src 'none'; connect-src 'self'
                                                           v
                                              (9) dashboard.js: exibe a string
                                                  como recebeu; passa os numeros
                                                  para a biblioteca de grafico
```

### Estrutura de projeto recomendada

```
l2scanner/
├── raiz.py               # NOVO, folha: so RAIZ. Corta a cadeia (§1)
├── dashboard.py          # NOVO: o servidor, o endpoint, a agregacao. Nada de tela.
├── mercado_registro.py   # ALTERADO? so se o planejador escolher a rota (b) da §2
└── mercado_catalogo.py   # ALTERADO: 1 linha (from .raiz import RAIZ)

l2scanner/recursos/dashboard/       # os estaticos, servidos com directory=
├── index.html
├── dashboard.css
├── dashboard.js
└── vendor/
    ├── <lib>.min.js
    ├── <lib>.LICENSE
    └── README.md         # VEND-1: nome, versao, licenca, URL, data, SHA-256, nota do VEND-2

tests/
├── test_dashboard.py             # endpoint, precedencia de estados, cambio
├── test_dashboard_somente_leitura.py   # a impressao digital (DASH-01)
└── test_firewall_dashboard.py    # VEND-3, no molde do FIRE-01

dashboard.bat             # NOVO, irmao do vigiar-mercado.bat
```

`l2scanner/recursos/` **ja existe** `[VERIFICADO: ls l2scanner/ → recursos]`, entao os estaticos tem
casa sem inventar convencao.

### Padrao 1: o corte da cadeia de import (§1) — a primeira tarefa da fase

**O que:** um modulo-folha com `RAIZ`, e `config.py` re-exportando.
**Quando usar:** antes de qualquer outra coisa. Ele desbloqueia o resto e e barato.
**Medicao (as duas arvores, processo limpo):**

```bash
# ANTES — arvore atual
$ PYTHONPATH=. .venv/Scripts/python.exe -c \
   "import sys, l2scanner.mercado_catalogo; \
    print('config:', 'l2scanner.config' in sys.modules, \
          '| rastreador:', 'l2scanner.rastreador' in sys.modules, \
          '| cv2:', 'cv2' in sys.modules)"
config: True | rastreador: True | cv2: True

# DEPOIS — mesma medicao, arvore com o corte
config: False | rastreador: False | cv2: False
```

`[VERIFICADO: medido nas duas arvores, 2026-09-01]`

**A mudanca, por extenso — duas linhas de codigo:**

```python
# l2scanner/raiz.py  (NOVO — folha, sem NADA em volta)
"""A raiz do projeto, sozinha.

ELE EXISTE PARA CORTAR UMA CADEIA, e a cadeia esta medida. `mercado_catalogo`
precisava de UMA constante de `config.py` (`RAIZ`), e `config` importa
`agenda`/`bosses`/`comandos`/`loot`/`notificador`/`respawn` — e `notificador`
importa `rastreador`, que importa `visao`, que importa `cv2` e `numpy`. Uma
`Path` de uma linha arrastava 280 modulos e 27 MB.
"""
from __future__ import annotations
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
```

```python
# l2scanner/config.py:48  — passa a IMPORTAR (re-export: quem faz
# `from .config import RAIZ` continua funcionando identico)
from .raiz import RAIZ  # re-exportado

# l2scanner/mercado_catalogo.py:95
-from .config import RAIZ
+from .raiz import RAIZ
```

**O valor nao muda:** `[VERIFICADO]` na arvore cortada, `RAIZ == l2scanner.raiz.RAIZ` → `True`, e
`PASTA_DO_MERCADO` continua resolvendo para `<raiz>/.mercado`.

**O que isso compra, medido:**

| | Arvore atual | Com o corte |
|---|---|---|
| `import l2scanner.mercado_registro` — modulos novos | **280** | **52** |
| ... pesados (`cv2`, `numpy`) | **cv2, numpy** | **nenhum** |
| ... tempo de import | 175–371 ms | **40–65 ms** |
| ... `sys.modules` total | 339–342 | **111** |
| ... working set | **44,3 MB** | **17,3 MB** |

`[VERIFICADO: probe_import.py, tempo.py, mem3.py — cada um rodado nas duas arvores]`

**O que o corte NAO resolve:** `import l2scanner.mercado_console` **continua** trazendo `cv2`,
porque `mercado_console.py:42` faz `from . import console`, e `console.py:16` faz
`from .rastreador import TipoDeEvento` → `visao` → `cv2`. Medido: 228 modulos, ainda com
`cv2`+`numpy`. Cortar essa segunda aresta exigiria mexer em `console.py` **ou** em `rastreador.py`
— e `rastreador.py` e intocavel por decisao do 04-CONTEXT do mercado. Ver Open Question 2.

### Padrao 2: a leitura ao vivo (DASH-01) — cortar ANTES do portao, nunca depois

```python
def observacoes_ao_vivo(arquivo: Path) -> tuple[list[ObservacaoLida], bool]:
    """As observacoes ate a ULTIMA LINHA COMPLETA. DIVERGENCIA DELIBERADA (DASH-01).

    A FASE 3 DO MERCADO DECIDIU O CONTRARIO, E ESTAVA CERTA PARA ELA.
    `conferir_o_terminador` (mercado_registro.py:412) recusa o arquivo INTEIRO
    quando ele nao termina em quebra de linha, porque la o leitor e o ARRANQUE
    DO ESCRITOR: um append desalinhado grava preco errado para sempre. Aqui o
    leitor NAO escreve nada, entao o custo de recusar e cegueira e o custo de
    degradar e zero.

    A DIVERGENCIA E DE FORMA, NAO DE PARSER. O corte acontece ANTES do portao,
    e por isso o portao continua sendo chamado e continua verdadeiro: um texto
    cortado em `rfind("\\n")+1` TERMINA em quebra de linha por construcao. Nao
    ha um segundo `csv.reader` nesta funcao — se houvesse, seria a segunda
    chance de alguem esquecer o portao, que e exatamente o que a Fase 3 gastou
    um plano inteiro para nao ter.

    A FREQUENCIA DO CASO ESTA MEDIDA, E O ROADMAP A SUPERESTIMOU. O escritor
    (`mercado_registro.registrar`, l.836) abre/escreve/flush/FECHA por linha, e
    `writerow`+`flush` e UMA chamada de escrita. Em 22.970 leituras de cauda
    durante 200.000 appends concorrentes nesta maquina: ZERO linhas parciais
    observadas. Com uma linha de 256 KB: ZERO tambem. Uma sonda de controle,
    escrevendo a linha em DUAS chamadas com pausa no meio, acusou 3.252 de
    4.079 — entao a sonda funciona e o zero e resultado.

    ISTO NAO TORNA A REDE INUTIL: ela cobre o arquivo EDITADO A MAO no Sheets e
    salvo sem quebra final, e a queda de energia. Ela e rede, nao caminho.
    """
    try:
        bruto = arquivo.read_text(encoding="utf-8", newline="")
    except FileNotFoundError:
        return [], False
    if not bruto:
        return [], False

    corte = bruto.rfind("\n")
    if corte < 0:
        # Nem uma linha completa. Nao ha nem cabecalho — nada a afirmar.
        return [], True
    completo, cauda = bruto[: corte + 1], bruto[corte + 1 :]

    # ... daqui para baixo, o MESMO caminho de `observacoes_do_arquivo`:
    #     conferir_o_terminador(completo, arquivo)   # verdadeiro por construcao
    #     conferir_o_cabecalho(...)                  # CONTRATO: continua desligando alto
    return _pelo_portao_unico(completo, arquivo), bool(cauda.strip())
```

**Nota de forma que o planejador tem de decidir (§2):** `observacoes_do_arquivo` recebe um `Path` e
le o arquivo ela mesma (`mercado_registro.py:552-556`). Para reusar o corpo dela sobre um **texto**
ja cortado, uma das tres rotas da §2 tem de ser escolhida.

### Padrao 3: o servidor — a forma medida inteira

```python
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; "
       "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'")

class Manipulador(http.server.SimpleHTTPRequestHandler):
    server_version = "L2Dashboard"      # nao entregar a versao do Python
    sys_version = ""

    def end_headers(self):
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def list_directory(self, path):     # LISTAGEM DESLIGADA, sempre
        self.send_error(404, "File not found")
        return None

class Servidor(http.server.ThreadingHTTPServer):
    # NAO E ESTILO. Medido: com o padrao (=1), no Windows SO_REUSEADDR deixa um
    # SEGUNDO processo bindar a MESMA porta sem erro nenhum, e o navegador fala
    # com quem ganhar a corrida do accept. Com False, o segundo bind levanta
    # OSError errno 10048 (WSAEADDRINUSE), que e o que da para MOSTRAR.
    allow_reuse_address = False
    daemon_threads = True

srv = Servidor(("127.0.0.1", PORTA),
               functools.partial(Manipulador, directory=str(PASTA_DOS_ESTATICOS)))
```

Resultado medido com essa forma exata:

```
GET /index.html      -> 200 | CSP presente | Server: L2Dashboard
GET /dados           -> 200 b'{"ok": true}' | CSP presente
POST /cambio         -> 200 b'{"recebido": {"reais_por_xm": "0,50"}}'
GET /                -> 200   (serve o index; a listagem nunca aparece)
GET /../SEGREDO.env  -> 404 | vazou: False
shutdown+server_close+join: 500,1 ms | thread viva: False
```

`[VERIFICADO: prova_servidor.py, saida colada]`

### Anti-padroes a evitar

- **`SimpleHTTPRequestHandler` sem `directory=`** — serviria o diretorio de trabalho, que e a raiz
  do repo, que contem `.env` com o token do Chatwoot. O UI-SPEC ja proibe; a medicao confirma que
  com `directory=` a travessia nao passa (§3).
- **Deixar `allow_reuse_address` no padrao.** Medido: dois binds na mesma porta, sem erro.
- **Reimplementar o parser do CSV no dashboard** — DASH-03 proibe, e a Fase 3 mediu por que.
- **Reacentuar ou reformatar no JS as strings vindas do Python** — o UI-SPEC chama isso de "o
  segundo formatador" e proibe. A divergencia de acentuacao e intencional.
- **`statistics.median`** — medido, inventa valor (`13/42` sobre uma lista que nao o contem).
- **`total_seconds()` para bucketizar** — devolve `float` (medido: `69713.696`). Use
  `(t - epoca) // largura`, que devolve `int` exato (medido: `69713`).
- **`Decimal(texto)` sozinho para validar o cambio** — aceita `1e3` e `1_0` (Pitfall 5).
- **Porta fixa dentro de uma faixa reservada do Windows** — ver Pitfall 4.
- **Abrir o CSV em modo `"r+"`, `"a"` ou `"w"` por descuido** — DASH-01 exige `"r"`. O teste da
  impressao digital pega, mas o modo tem que estar certo por escrito.

---

## Don't Hand-Roll

| Problema | Nao construir | Usar | Por que |
|---------|-------------|-------------|-----|
| Ler e tipar o CSV | um `csv.reader` "simples" no dashboard | `mercado_registro.observacoes_do_arquivo` (o corpo dela) | Das 5 truncagens medidas na Fase 3, **2 produzem 6 campos todos parseaveis** (`80`→`8`). Contagem de campos nao pega; tipo nao pega; so o terminador pega. Duas implementacoes = duas chances de esquecer o portao. `[VERIFICADO: mercado_registro.py:412-460, docstring]` |
| Menor / mediana / recencia | `min()` e `statistics.median` a mao | `mercado_analise.menor_pedido_visivel`, `mediana_dos_unitarios`, `recencia_do_preco` | Elas ja carregam `Evidencia` (`n` + `piso` + `faltam`), ja desempatam pelo carimbo mais antigo, ja descartam quantidade nao-positiva, e ja usam `median_low`. Refazer perderia os quatro. |
| Formatar o numero | `f"{x:.2f}"` no Python ou `toFixed(2)` no JS | `formatar_taxa_derivada` / `formatar_unitario_derivado`, escolhidos por `formatador_do_unitario(chave)` | `round(Fraction(11600, 10_000_000))` vale **zero** — chamar o formatador errado imprime `0,00` com toda a confianca do mundo. `[VERIFICADO: mercado_console.py:268-303, docstring]` |
| Recencia em texto | `"ha " + str(delta)` | `_recencia_em_duas_formas` | Ela ja da as duas formas juntas (`ha 8 h (31/08 10:00)`) e ja trata carimbo no futuro como `agora mesmo`. |
| Zoom e pan no canvas | `mousedown`/`mousemove` + `requestAnimationFrame` a mao | a biblioteca vendorizada | Escala de eixo temporal, rescale automatico, hit-testing do cursor e limite de arrasto sao onde codigo a mao apodrece. **Com uma excecao medida**: o wheel-zoom do uPlot **e** codigo nosso (§4). |
| Escrita atomica do JSON | `open("w")` + `json.dump` | tmp + `fsync` + `os.replace` | Medido funcionando sobre alvo existente no Windows, 9,18 ms, zero `.tmp` orfaos em 200 gravacoes. |
| Validar o numero digitado | `float(texto)` ou `Decimal(texto)` | regex ASCII explicita **e depois** `Decimal` | Medido: `Decimal("1e3")` → 1000 e `Decimal("1_0")` → 10. |

**Insight central:** neste projeto o codigo a mao nao apodrece por ser feio — apodrece por **divergir
em silencio** do outro que faz a mesma coisa. Toda linha desta tabela e um caso de "duas verdades
sobre um fato so", que e o defeito que a Fase 3 e a Fase 4 do mercado ja pagaram para nao ter.

---

## Runtime State Inventory

> Esta fase e majoritariamente greenfield, mas ela **contem um refactor** (o corte de `RAIZ`) e
> **cria um arquivo novo**. Preenchida por isso.

| Categoria | Encontrado | Acao necessaria |
|----------|-------------|------------------|
| Dado armazenado | `.mercado/observacoes.csv` — 8.536 bytes, 93 linhas, **0 com `adena#`**, 13 instantes distintos de `primeira_vez` `[VERIFICADO: wc -l, grep -c, cut+uniq]`. **Nenhuma migracao**: o dashboard so le. | Nenhuma |
| Config de servico vivo | Nenhuma. O dashboard nao fala com Chatwoot, n8n, Discord nem Datadog. Verificado por ausencia de qualquer import de `notificador`/`ponte_*` no desenho proposto. | Nenhuma |
| Estado registrado no SO | Nenhum. Nao ha Task Scheduler, nem pm2, nem servico. O `dashboard.bat` e lancado a mao. **A porta TCP e o unico recurso do SO tomado** — e por isso o Pitfall 4 existe. | Nenhuma |
| Segredos / variaveis de ambiente | Nenhum novo. O `.env` com `CHATWOOT_API_TOKEN` existe na raiz `[VERIFICADO: ls -la → .env, 1055 bytes]` e **e exatamente o que a CSP e o `directory=` existem para nao vazar**. | Nenhuma — mas o teste de travessia e obrigatorio |
| Artefato de build / pacote instalado | Nenhum `pip install`. **`__pycache__` de `l2scanner/` fica obsoleto** apos o corte de `RAIZ` — o Python revalida por mtime sozinho, entao nao ha acao. | Nenhuma |
| **Teste que muda de significado** | `tests/test_mercado_firewall_de_fase.py:315` — `test_o_rastreador_chega_por_uma_CADEIA_PREEXISTENTE_do_config`, cuja docstring **descreve a cadeia que esta fase corta**. | **Atualizar a docstring e a assercao.** Ver Pitfall 1 — o teste tem um buraco medido. |

---

## Common Pitfalls

### Pitfall 1: o tripwire da cadeia de import passa mesmo depois de a cadeia ser cortada

**O que da errado:** `tests/test_mercado_firewall_de_fase.py:315` existe justamente para "se a
cadeia for cortada um dia, ele cai e obriga quem cortou a atualizar a historia". **Ele nao cai.**

**Por que acontece:** o corpo do teste e

```python
codigo = (
    "import sys\n"
    "import l2scanner.config\n"
    "assert 'l2scanner.rastreador' in sys.modules\n"
    "import l2scanner.mercado_catalogo\n"
    "assert 'l2scanner.config' in sys.modules\n"
)
```

A segunda assercao e **tautologica**: `l2scanner.config` ja esta em `sys.modules` porque a linha 2
o importou. A aresta `mercado_catalogo → config` nunca foi realmente presa.

**Medido:**

```bash
# o codigo EXATO do teste, nas duas arvores
arvore ATUAL      : as duas assercoes do teste passaram
arvore COM O CORTE: as duas assercoes do teste passaram     <-- deveria ter caido

# a medicao HONESTA, em processo limpo, importando SO o catalogo
arvore ATUAL      : config: True  | rastreador: True  | cv2: True
arvore COM O CORTE: config: False | rastreador: False | cv2: False
```

`[VERIFICADO: os dois comandos rodados nas duas arvores, 2026-09-01]`

**Como evitar:** a tarefa do corte tem de **consertar o teste tambem**, trocando a assercao B por
um subprocesso que importa **apenas** `l2scanner.mercado_catalogo`. E a docstring dele tem de virar
a historia nova — "refutacao mora no fonte" vale tambem para uma refutacao que o proprio projeto
escreveu e que deixou de ser verdade.

**Sinal de alerta:** o teste ficar verde depois do corte. Isso e o sintoma, nao o alivio.

### Pitfall 2: `allow_reuse_address` deixa dois dashboards na mesma porta, calados

**O que da errado:** o usuario da dois cliques no `dashboard.bat` duas vezes. Nenhum erro aparece.
O navegador abre e mostra dados; qual dos dois processos respondeu e sorte.

**Medido:**

```
allow_reuse_address padrao de HTTPServer: 1
primeiro bind OK em ('127.0.0.1', 8791)
!!! SEGUNDO BIND TAMBEM PASSOU ('127.0.0.1', 8791)
com allow_reuse_address=False: OSError errno=10048 winerror=10048 | EADDRINUSE=10048
```

`[VERIFICADO: porta.py, saida colada]`

**Como evitar:** `allow_reuse_address = False` na subclasse, e o `errno 10048` traduzido para o
usuario: *"O dashboard ja esta aberto nesta maquina (porta 8791 ocupada). Feche a janela preta
anterior, ou so use a aba que ja esta aberta."* — e **nao** um traceback.

**Sinal de alerta:** dois `python.exe` no gerenciador de tarefas e um numero que "as vezes atrasa".

### Pitfall 3: `median` inventa um valor; `total_seconds()` traz float pela porta dos fundos

**Medido:**

```
median_low par  : 2/7   | tipo: Fraction | esta na lista: True
median (proibida): 13/42 |                 esta na lista: False    <-- D-02 violado
median_low impar: 1/3   |                 esta na lista: True

total_seconds(): 69713.696 float
//timedelta    : 69713    int
```

`[VERIFICADO: agregacao.py]`

**Como evitar:** `statistics.median_low` sempre, e `(t - epoca) // largura` para o indice do balde.
E ha um terceiro: **o balde de um dia ancorado num instante arbitrario nao comeca a meia-noite**.
Medido — com `epoca = 2026-08-31 15:00`, os baldes de `timedelta(days=1)` comecam as **15:00**, nao
as 00:00. Para o zoom "dias atras" fazer sentido para um humano, a ancora tem que ser a meia-noite
local, nao a primeira observacao.

### Pitfall 4: uma porta fixa pode cair numa faixa que o Windows reservou

**O que da errado:** o `.bat` sobe, o bind falha com um erro obscuro, e o usuario nao tem nada a
fazer — porque a porta nao esta em uso por ninguem: ela esta **excluida**.

**Medido nesta maquina:**

```
$ netsh interface ipv4 show excludedportrange protocol=tcp
      5357  5357
     49152  49251
     50000  50059  *
     53409  53508
     53609  53708
     53709  53808
     53918  54017
     54543  54642
     64051  64150
```

`[VERIFICADO: netsh, saida colada]` — essas faixas sao do WinNAT/Hyper-V e **mudam a cada boot**.

**Como evitar:** escolher a porta fixa **abaixo de 49152** (fora do intervalo dinamico), e sondar
antes de subir. Livres nesta maquina agora: `8080, 8000, 5000, 3000, 8765, 8787, 9009, 27015,
47821` `[VERIFICADO: portas.py]`. Ocupadas: `9010` e `9180`, entre outras. Portas de dev famosas
(`3000`, `8000`, `8080`, `5000`) estao livres mas sao as mais disputadas por qualquer outra
ferramenta que o usuario abrir — uma porta "sem vizinhos" na faixa 8700–8800 e a aposta mais quieta.

### Pitfall 5: `Decimal` sozinho aceita `1e3` e `1_0` — e isso e dinheiro real

**O que da errado:** o usuario digita `1_0` querendo `1,0`. `Decimal` le `10`. O R$ na tela fica
**20× errado**, sem nenhum aviso, e a decisao de compra sai desse numero.

**Medido:**

| Entrada | `Decimal` sozinho (`>0` e `is_finite`) | Valor | Regex ASCII explicita |
|---|---|---|---|
| `'0,50'` | aceito | `0.50` | aceito |
| `'0'` / `'-1'` / `''` / `'abc'` / `'0,5,0'` | recusado | — | recusado |
| **`'1e3'`** | **aceito** | **`1E+3`** | **recusado** |
| **`'+0.5'`** | **aceito** | `0.5` | **recusado** |
| **`'1_0'`** | **aceito** | **`10`** | **recusado** |
| **`'1234567890123,5'`** | **aceito** | `1234567890123.5` | **recusado** |
| `'Infinity'` / `'NaN'` | recusado (por `is_finite`) | — | recusado |
| `'٠٫٥'` / `'０．５'` (digitos Unicode) | recusado | — | recusado |

`[VERIFICADO: cambio2.py, tabela e a saida do script]`

**Como evitar:** portao em duas camadas, **no servidor** (o JS e conveniencia):

```python
MOLDE_DO_CAMBIO = re.compile(r"^\d{1,7}([.,]\d{1,4})?$")   # ASCII, sem expoente, sem "_", sem sinal
```

e so depois `Decimal(texto.replace(",", ".")) > 0`. A frase de recusa ja esta travada no UI-SPEC:
`Cambio nao salvo: informe um numero maior que zero, como 0,50.`

**Sinal de alerta:** um R$ que muda de ordem de grandeza depois de o usuario "so corrigir um
digito".

### Pitfall 6: `form-action 'none'` e um `<form>` de verdade colidem

**O que da errado:** o UI-SPEC trava **duas** coisas: a CSP com `form-action 'none'` (Registry
Safety, VEND-4) e "`<form>` de verdade, `Enter` submete" (Interacao). Se o `dashboard.js` nao
interceptar com `preventDefault()`, o `Enter` dispara um submit nativo que a CSP **bloqueia** — e
o navegador nao mostra nada alem de um erro no console.

**Confianca:** `[CITADO: https://www.w3.org/TR/CSP3/#directive-form-action]` — `form-action`
restringe os destinos aos quais um formulario pode ser submetido; `'none'` nao permite nenhum.
**Nao medido** (exige navegador).

**Como evitar:** e na verdade a **falha fechada certa** — se o JS morrer, o formulario nao envia em
vez de recarregar a pagina para lugar nenhum. Mas isso tem que estar **escrito**, e o `submit`
handler com `preventDefault()` + `fetch()` e obrigatorio, nao opcional. Fica como item de
verificacao humana declarada.

### Pitfall 7: o custo de reler o arquivo inteiro nao e zero para sempre

**Medido hoje:** 92 observacoes → `observacoes_do_arquivo` em **0,519 ms** (media de 300 leituras).
**Medido a 60.000 linhas (2,9 MB):** parse **366 ms** + `menor+mediana+recencia` **174 ms** = 540 ms.
A 2 s de polling isso e ~27% de um nucleo, na mesma maquina que roda o jogo.
`[VERIFICADO: somente_leitura.py e escala.py]`

**Como evitar:** o cache por `(st_size, st_mtime_ns)` que o CONTEXT ja trava ("o servidor rele o CSV
quando `mtime`/tamanho mudam"). Ele e desnecessario hoje e obrigatorio depois; implementar agora
custa 5 linhas.

---

## Code Examples

### A prova de somente-leitura (DASH-01, criterio 6) — no molde que a casa ja usa

O helper existe e e reutilizavel: `tests/test_mercado_firewall_de_fase.py:481` —
`_impressao_do_arquivo(caminho) -> (st_size, st_mtime_ns, sha256)`, com a razao dos **tres juntos**
escrita na docstring dele. Medido sobre uma copia do arquivo real:

```
300 leituras do arquivo real de 92 linhas: 0.519 ms por leitura
observacoes por leitura: 92
impressao IGUAL (tamanho, mtime_ns, sha256): True
  antes : 8536 1788268914023244000 21dc10f297c079d5
  depois: 8536 1788268914023244000 21dc10f297c079d5
```

`[VERIFICADO: somente_leitura.py]`

### A prova de que a linha parcial nao aparece — e a sonda que prova que a sonda funciona

```python
# O leitor AGRESSIVO: le so a cauda (os.read cru), em laco apertado.
while time.perf_counter() < fim:
    fd = os.open(alvo, os.O_RDONLY | os.O_BINARY)
    tam = os.fstat(fd).st_size
    os.lseek(fd, max(0, tam - 4096), 0)
    cauda = os.read(fd, 4096)
    os.close(fd)
    if cauda and not cauda.endswith(b"\n"):
        sem_terminador += 1
```

| Escritor | Appends | Leituras de cauda | Sem terminador | Erros de abertura |
|---|---|---|---|---|
| o padrao real (`open "a"` → `writerow` → `flush` → `close`) | 200.000 | 22.970 | **0** | **0** |
| idem, com linha de **256 KB** | 3.000 | 19.898 | **0** | **0** |
| leitura do arquivo INTEIRO durante appends | 60.000 | 510 | **0** | **0** |
| **controle positivo** (`os.write` da linha, pausa, `os.write` do `\r\n`) | 4.000 | 4.079 | **3.252** | 0 |

`[VERIFICADO: escritor.py + leitor.py + leitor_cauda.py + escritor_grande.py + escritor_rasgado.py]`

A ultima linha e o que torna as tres primeiras uma medicao e nao um silencio.

### O teste do endpoint sem navegador (o molde para `tests/test_dashboard.py`)

```python
@pytest.fixture
def servidor(tmp_path):
    """Porta EFEMERA (0), nunca a fixa: a suite nao pode brigar com o dashboard
    que o usuario deixou aberto, e duas rodadas em paralelo nao podem colidir.

    `poll_interval` MEDIDO: com o padrao (0,5 s) cada `shutdown()` custa 449 ms.
    Com 0,01 s custa 9,7 ms. Numa suite de ~4.100 testes, 0,5 s por servidor e
    meio segundo por teste que ninguem vai perdoar.
    """
    srv = montar_servidor(porta=0, pasta_do_mercado=tmp_path)
    t = threading.Thread(target=srv.serve_forever,
                         kwargs={"poll_interval": 0.01}, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); t.join(timeout=5)
        assert not t.is_alive()
```

Medido: `poll_interval=0.5 → 449,5 ms` · `0.05 → 45,1 ms` · `0.01 → 9,7 ms`
`[VERIFICADO: desligar.py]`

Para o cliente, `http.client.HTTPConnection` em vez de `urllib.request`: ele deixa mandar caminhos
crus (`putrequest(..., skip_accept_encoding=True)`), que e como a travessia de caminho foi testada
— `urllib` normaliza a URL antes de enviar e **esconderia** metade dos casos.

### O bucketizador sem float (DASH-03 + D-02)

```python
def baldes(observacoes, largura: timedelta, ancora: datetime):
    """Um ponto por balde, e o valor do ponto EXISTIU.

    O INDICE E INTEIRO EXATO: `(t - ancora) // largura` opera sobre microssegundos
    inteiros do timedelta. `total_seconds()` devolveria float — medido, 69713.696
    contra 69713 — e float e como um centavo aparece do nada.

    A ANCORA E A MEIA-NOITE LOCAL, E NAO A PRIMEIRA OBSERVACAO. Medido: com a
    ancora em 15:00, os baldes de um dia comecam as 15:00, e "dias atras" deixa
    de querer dizer o que um humano acha que quer dizer.

    O VALOR DO BALDE E `median_low` DOS VALORES DOS INSTANTES DELE, e por isso
    ele continua sendo um valor OBSERVADO: `median_low` devolve um ELEMENTO da
    lista (medido), e cada elemento ja e um unitario que esteve na tela. A
    composicao preserva o D-02; `statistics.median` a quebraria na primeira
    contagem par.
    """
    por_balde: dict[int, list[Fraction]] = {}
    for instante, valor in observacoes:
        por_balde.setdefault((instante - ancora) // largura, []).append(valor)
    return sorted(
        (ancora + i * largura, statistics.median_low(vs))
        for i, vs in por_balde.items()
    )
```

### A fronteira do `float` — dita em voz alta, porque ela existe

O canvas so aceita numero de JS. Medido, sobre a taxa da Adena em centesimos por milhao:

| Fracao exata | `float()` | Erro absoluto |
|---|---|---|
| `Fraction(11600, 10_000_000) × 10⁶` = **1160** | `1160.0` | **0** |
| `Fraction(30000, 15_000_000) × 10⁶` = **2000** | `2000.0` | **0** |
| `Fraction(1, 3) × 10⁶` | `333333.3333333333` | `1,9e-11` |
| `Fraction(99991, 7_000_003) × 10⁶` | `14284.422449533236` | `5,2e-13` |

`[VERIFICADO: float_do_grafico.py]` — pior erro medido: **1,9e-11 centesimos por milhao**.

A regra que sai disso: **o `float` no JSON e o pixel; a `string` no JSON e a verdade.** O JSON de
cada ponto carrega os dois, e o texto do *tooltip* e da legenda vem da string do Python, nunca de
`toFixed()`. Isso e o mesmo argumento do D-02, aplicado a fronteira HTTP.

---

## State of the Art

| Abordagem antiga | Abordagem atual | Quando mudou | Impacto |
|--------------|------------------|--------------|--------|
| `SimpleHTTPRequestHandler` servindo `os.getcwd()` | parametro `directory=` no construtor | Python **3.7** | O `functools.partial(Handler, directory=...)` e o jeito suportado; sem ele o repo inteiro fica exposto |
| `SocketServer.ThreadingMixIn` + `HTTPServer` a mao | `http.server.ThreadingHTTPServer` pronto | Python **3.7** | Uma classe em vez de duas |
| `SO_REUSEADDR` como "boa pratica" | no Windows ele significa **roubar a porta** | sempre foi; e folclore que nao | `allow_reuse_address = False` e o correto para um servidor de porta fixa em `127.0.0.1` |
| `allow_reuse_port` inexistente | `socketserver.TCPServer.allow_reuse_port` (padrao `False`) | Python **3.11** | `[VERIFICADO: hasattr → True, valor → False]`. Nao mexer: `SO_REUSEPORT` nem existe no Windows |

**Depreciado / superado:**

- `cgi`/`cgitb` — removidos no 3.13. Nao usar nem como exemplo.
- `urllib.request` para testar travessia de caminho — ele normaliza a URL antes de enviar; use
  `http.client.HTTPConnection.putrequest`.

---

## Assumptions Log

| # | Afirmacao | Secao | Risco se estiver errada |
|---|-------|---------|---------------|
| A1 | Uma porta na faixa 8700–8800 tem menos vizinhos que 3000/8000/8080 | Pitfall 4 | Baixo — o `.bat` sonda antes e a mensagem de porta ocupada e clara. Nao medi "quais portas outras ferramentas do usuario usam", so quais estao livres AGORA. |
| A2 | `form-action 'none'` bloqueia o submit nativo de um `<form>` | Pitfall 6 | Medio — se eu estiver errado, o `Enter` recarrega a pagina em vez de nao fazer nada. **Nao medivel sem navegador**; e verificacao humana declarada. |
| A3 | `dygraphs` 2.2.2 nao tem wheel-zoom no `dist` minificado | §4 | Medio — medi a **ausencia de qualquer string de evento de roda** no minificado (`wheel`, `mousewheel`, `wheelDelta`, `DOMMouse`, `Scroll` → todas 0), e a doc oficial nao lista a opcao. Mas o `interactionModel` do dygraphs esta documentado como "TODO(konigsberg): document this", entao nao posso afirmar categoricamente. |
| A4 | `lightweight-charts` desenha bem uma serie **esparsa e irregular** (13 pontos em 2 dias) | §4 | **Alto** — ela e feita para candles em grade temporal regular. Uma serie de 13 pontos irregulares e o caso que ela menos serve, e eu nao testei. Isso derruba a candidata na pratica, mas por raciocinio, nao por medicao. |
| A5 | O usuario aceita que a segunda tarefa da fase mexa em `mercado_catalogo.py` | Open Question 2 | **Alto** — DASH-06 diz "byte-identico". A decisao e do planejador/usuario, nao minha. |

---

## Open Questions (RESOLVED)

> **AS TRES FORAM RESOLVIDAS EM 2026-09-01, DEPOIS DE ESTA PESQUISA SER ESCRITA.** Este bloco
> ficou no lugar porque a medicao que sustenta cada pergunta continua valendo e continua util —
> mas **as recomendacoes abaixo NAO sao mais o caminho a seguir**, e duas delas foram
> explicitamente RECUSADAS. Cada pergunta traz agora o desfecho no proprio titulo e um bloco
> `RESOLVIDO` no fim. Quem chegar aqui pelo `<read_first>` de um plano: leia a medicao, e ignore
> a recomendacao. O que vale e o `01-CONTEXT.md` e os planos `01-01`/`01-02`.

### 1. "Um ponto do grafico e um instante de leitura" nao e a mesma conta que o console faz — RESOLVIDO: CTX-1 (a recomendacao abaixo foi RECUSADA)

**O que sabemos, medido.** O CONTEXT trava: *"Um ponto do grafico e um instante de leitura
(`primeira_vez`), com o menor pedido visivel e a mediana daquele instante — exatamente a conta que o
console ja faz via `mercado_analise`"*. E o DASH-03 exige: *"Os numeros batem com os do console
`--mercado` para o mesmo instante"*.

Mas `mercado_analise.menor_pedido_visivel(observacoes)` opera sobre a **serie inteira**, e o console
a chama com `modelo.observacoes_de(chave)` — **toda a historia da serie**, nao um instante.
`[VERIFICADO: mercado_analise.py:286-325 e :561-604; mercado_console.py:522-560]`

Pior, a docstring de `mercado_analise` diz por extenso:

> *"Nao existe serie temporal de preco neste CSV — existe uma sequencia de anuncios diferentes, e o
> `n` conta anuncios, nao instantes."* `[VERIFICADO: mercado_analise.py:411-420]`

E `tests/test_mercado_analise.py:8-16` repete: a chave de dedup e `(chave, total, quantidade)` **sem
tempo**, entao **um painel relido sem ofertas novas nao produz linha nenhuma** — e portanto nenhum
ponto novo no grafico.

**O que a medicao mostra sobre o dado real:** 92 observacoes, **13** valores distintos de
`primeira_vez`; a maior serie (`protecting-scroll`) tem 15 observacoes em **2** instantes (10 e 5).
`[VERIFICADO: cut -d';' -f3 | sort | uniq -c]` Ou seja: agrupar por instante da poucos pontos, e
cada ponto e um `menor`/`mediana` sobre um `n` pequeno — muitas vezes **abaixo do piso**
(`N_MINIMO_PARA_MEDIANA = 5`).

**O que nao esta claro:** o grafico mostra (a) o valor **daquele instante** (subconjunto — quase
sempre sem mediana, por piso), ou (b) o valor **acumulado ate aquele instante** (que bate com o
console e sempre tem mediana quando o piso deixa)?

**Recomendacao:** **(b), acumulado ate o instante.** E o unico que satisfaz DASH-03 literalmente
("batem com os do console para o mesmo instante"), e o unico em que a linha da mediana existe com o
dado que o CSV tem. E ele preserva o D-02: cada ponto e um `median_low` sobre unitarios observados.
O custo e O(n²) ingenuo, mas com 13 instantes e irrelevante — e um acumulador incremental resolve.
**Isto precisa de confirmacao do usuario**, porque contradiz a leitura literal do CONTEXT.

> **RESOLVIDO: CTX-1 — a recomendacao (b) foi RECUSADA pelo usuario em 2026-09-01.** Ele foi
> confrontado com esta medicao exata (92 observacoes, 13 instantes distintos, a maior serie com
> 2 instantes, `N_MINIMO_PARA_MEDIANA = 5`) e **manteve a leitura literal (a)**: um ponto do
> grafico e UM INSTANTE DE LEITURA. A consequencia foi aceita de olhos abertos e e o caso
> NORMAL da tela — a linha da mediana fica ausente na maior parte do grafico, e onde ela falta
> aparece a frase de piso vinda do Python, nunca um numero. Implementado em `01-02` Tarefa 2,
> com esta refutacao escrita na docstring de `pontos_por_instante`. **Nao reintroduzir (b).**

### 2. O corte de `RAIZ` toca `mercado_catalogo.py`, e DASH-06 diz "byte-identico" — RESOLVIDO: CTX-2 (saida A, o corte foi AUTORIZADO)

**O que sabemos.** DASH-06 e o criterio 9 do ROADMAP exigem: *"o caminho do `--mercado` fica
**byte-identico** — nenhuma linha do modo mercado muda por causa desta fase"*. O corte de `RAIZ`
muda **uma linha** de `mercado_catalogo.py` e **uma linha** de `config.py`.

**O que a medicao diz sobre o comportamento:** `RAIZ` e `PASTA_DO_MERCADO` continuam com o **mesmo
valor** (`RAIZ == l2scanner.raiz.RAIZ` → `True`), e `mercado_catalogo` continua exportando o mesmo
`SEPARADOR`, `PASTA_DO_MERCADO` e `CHAVE_DA_SERIE_DA_ADENA`. **Comportamentalmente identico;
textualmente nao.** `[VERIFICADO]`

**O que nao esta claro:** "byte-identico" e sobre o **texto do fonte** ou sobre o **comportamento do
caminho**?

**Recomendacao:** apresentar ao usuario como decisao explicita, com as tres saidas medidas:

> **RESOLVIDO: CTX-2 — o usuario escolheu a saida (A), fazer o corte, em 2026-09-01.** Nasce
> `l2scanner/raiz.py` (folha) e `mercado_catalogo.py` passa a importar dali; DASH-06 foi
> reescrito de "byte-identico" para "comportamento identico". **`mercado_catalogo.py` e o UNICO
> arquivo do workstream `mercado` que esta fase pode tocar** — o que, no planejamento, tambem
> eliminou a rota (a) da §2 (ela tocaria `mercado_registro.py`) e a rota (iii) da §1 (ela
> tocaria `console.py`). Implementado em `01-01` Tarefas 2 e 3.

| Saida | Custo | O que quebra |
|---|---|---|
| **(A) Fazer o corte** | 2 linhas + consertar o tripwire (Pitfall 1) | A letra do DASH-06. Ganha: 280→52 modulos, 44,3→17,3 MB, sem `cv2` no processo do dashboard |
| **(B) Nao cortar** | zero | Nada. Mas o dashboard importa `cv2`+`numpy`, **exige o `.venv`**, e a promessa "o dashboard nunca toca em captura" fica sendo sobre comportamento, nao sobre estrutura |
| **(C) Cortar numa fase propria do workstream `mercado`** | uma fase a mais, e coordenacao entre workstreams — que e exatamente o que o ROADMAP do dashboard existiu para evitar | Nada, mas atrasa |

**Nota importante para (B):** importar `cv2` **nao e capturar tela**. Nenhuma sessao WGC, nenhuma
camera DXGI, nenhum `mss.grab` acontece por import — medido, `mss` e `windows_capture` **nao**
aparecem em `sys.modules` em nenhuma das medicoes. A objecao a (B) e de doutrina e de peso, nao de
seguranca.

### 3. Onde fica o corte da agregacao: servidor ou navegador? — RESOLVIDO pelo planejamento (a recomendacao abaixo foi ADOTADA)

**O que sabemos.** O CONTEXT trava duas coisas que puxam para lados diferentes: *"o arquivo inteiro
e carregado; filtrar o zoom no navegador e mais simples e mais correto que paginar no servidor"* e
*"Zoom largo agrega com `median_low`, nunca media"`. Mas `median_low` sobre `Fraction` so existe no
Python — no JS seria `float` e ordenacao de numeros de ponto flutuante.

**O que nao esta claro:** o servidor manda **todos os instantes** e o JS agrega ao dar zoom
(precisaria de `median_low` em JS), ou o servidor manda **os baldes ja prontos por nivel de zoom** e
o JS so troca de conjunto?

**Recomendacao:** **o servidor manda os baldes prontos, um conjunto por nivel de zoom** (por
exemplo 5 min / 1 h / 1 dia), mais a serie crua. `median_low` de uma lista de `Fraction` fica no
Python; o JS escolhe qual conjunto desenhar conforme o alcance. Isso respeita "filtrar no navegador"
(o filtro e a janela, e ela continua no JS) sem exportar a **conta** para o float. Com 13 instantes
o JSON inteiro cabe em poucos KB.

> **RESOLVIDO — recomendacao ADOTADA no planejamento de 2026-09-01.** O servidor manda os baldes
> prontos por nivel de zoom mais a serie crua (`01-02` Tarefa 2, `LARGURAS_DE_BALDE`), e o
> navegador so escolhe qual conjunto desenhar conforme o alcance visivel (`01-07` Tarefa 2). A
> conta fica no Python, em `Fraction`; a janela continua sendo decisao do navegador.
>
> *(Nao confundir com CTX-3, que e outra decisao do mesmo dia: a biblioteca de grafico e uPlot,
> com o zoom por roda escrito por nos pela API de hooks.)*

---

## Environment Availability

| Dependencia | Exigida por | Disponivel | Versao | Alternativa |
|------------|------------|-----------|---------|----------|
| CPython 64-bit | tudo | ✓ | **3.12.13** (`.venv`) / **3.12.10** (global) | — |
| `http.server`, `json`, `csv`, `statistics`, `decimal`, `fractions` | tudo | ✓ | stdlib | — |
| pytest | a prova | ✓ | **9.1.1** (no Python **global**, nao no `.venv`) | — |
| `.mercado/observacoes.csv` | o dado | ✓ | 8.536 B, 93 linhas, **0 da Adena** | O estado vazio ja e a primeira tela |
| `.mercado/cambio.json` | DASH-02 | ✗ (nasce nesta fase) | — | Sem ele, `R$ indisponivel` — ja especificado |
| `curl` (so para vendorizar a lib, uma vez) | VEND-1 | ✓ | — | Download manual pelo navegador |
| Um navegador | a verificacao humana | ✓ (Windows 11) | — | — |
| `cv2`, `numpy` | **nada nesta fase** | ✓ (4.14.0 / 2.5.2, nos dois Pythons) | — | Se o corte de `RAIZ` acontecer, o dashboard **nao precisa deles** e pode rodar no Python global |

**Faltando sem alternativa:** nenhum.

> **Consequencia pratica do corte de `RAIZ` para o `dashboard.bat`:** com o corte, o dashboard nao
> precisa de **nenhum** pacote de terceiro. O `.bat` pode dispensar o bloco de `venv` e a sonda de
> `import mss,cv2,numpy,windows_capture,winrt...` que o `vigiar-mercado.bat` tem
> `[VERIFICADO: vigiar-mercado.bat, a linha da sonda]`, e rodar direto no Python que o `where py`
> achar. Isso e **DASH-06 virando estrutura**: derrubar o `.venv` nao derruba o dashboard, e vice-versa.

---

## Security Domain

### Categorias ASVS aplicaveis

| Categoria ASVS | Aplica | Controle padrao |
|---------------|---------|-----------------|
| V2 Autenticacao | **nao** | Bind em `127.0.0.1` apenas. Sem rede, sem usuario, sem sessao — travado no CONTEXT |
| V3 Sessao | **nao** | Nao ha sessao nem cookie |
| V4 Controle de acesso | **parcial** | O unico "acesso" e o do proprio usuario da maquina. `127.0.0.1` e o controle |
| V5 Validacao de entrada | **sim** | Regex ASCII + `Decimal` no **servidor** para o cambio (Pitfall 5); `directory=` + listagem desligada para o caminho (§3) |
| V6 Criptografia | **nao** | Nenhum segredo e manuseado. O `.env` **existe na arvore** — e a razao de V5 e a CSP importarem |
| V12 Arquivos e recursos | **sim** | Travessia de caminho medida (10 sondas, 0 vazamentos); escrita restrita a **um** arquivo, atomica |
| V14 Configuracao | **sim** | CSP em toda resposta; `Server:` sem versao do Python; `X-Content-Type-Options: nosniff` |

### Padroes de ameaca para esta pilha

| Padrao | STRIDE | Mitigacao, medida |
|---------|--------|---------------------|
| Travessia de caminho lendo `.env` | Divulgacao | `SimpleHTTPRequestHandler(directory=...)`. **10 sondas** (`../`, `..%2f`, `%2e%2e/`, `....//`, `..\`, `..%5c`, `C:/Windows/win.ini`, `//`, `publico/../`) → **0 vazamentos**. `[VERIFICADO: travessia.py]`. As duas variantes de contrabarra devolvem **301** para o proprio diretorio, nao o arquivo — o `translate_path` descarta o componente por conter separador |
| Listagem de diretorio expondo a arvore | Divulgacao | `list_directory` sobrescrito para `404`. Sem isso, o `GET /` de um diretorio sem `index.html` lista os arquivos |
| Um site qualquer no navegador falando com `127.0.0.1` | Elevacao / Adulteracao | O `POST /cambio` **precisa** conferir `Origin`/`Sec-Fetch-Site` — um `<form>` em qualquer aba pode fazer POST cross-origin para `localhost`. Recusar `Origin` ausente ou diferente de `http://127.0.0.1:<porta>`. **Nao medido** (exige navegador) — e a mitigacao mais importante que a CSP **nao** cobre, porque a CSP protege *a nossa* pagina, nao *a nossa* API |
| A biblioteca vendorizada telefonando para casa | Divulgacao | **Tres camadas:** VEND-2 (grep no fonte — uPlot passou com **0**), VEND-3 (teste que quebra) e VEND-4 (`connect-src 'self'` no cabecalho, afirmavel sem navegador). A CSP torna estrutural o que o grep so torna verificado uma vez |
| Dois dashboards na mesma porta | Adulteracao | `allow_reuse_address = False` (Pitfall 2) |
| DoS por polling num arquivo grande | DoS | Cache por `(size, mtime_ns)`. Sem ele, 540 ms a cada 2 s com 60.000 linhas (Pitfall 7) |

> **Achado de seguranca que nenhum documento anterior levantou:** a defesa contra CSRF do
> `POST /cambio`. A CSP protege a nossa pagina de carregar coisa de fora; ela **nao** impede uma
> pagina de fora de mandar um POST para a nossa. Numa maquina onde o `.env` do Chatwoot mora ao
> lado, uma API local que escreve arquivo sem checar `Origin` e uma superficie de verdade. A
> conferencia e barata e afirmavel em teste (basta mandar um `Origin:` errado e exigir 403).

---

## Project Constraints (do `.claude/CLAUDE.md`)

| Diretiva | Como esta fase cumpre |
|---|---|
| **Deteccao passiva; nunca injetar, ler memoria ou enviar input** | O dashboard **nao captura nada**. Com o corte de `RAIZ`, nem `cv2` entra no processo — medido |
| **FIRE-01: nenhuma biblioteca de sintese de input** | `requirements.txt` **nao muda**. `tests/test_firewall_escopo.py` continua verde sem alteracao |
| **Doutrina de zero-install: dependencia nova e decisao de pesquisa** | **Zero dependencias Python novas.** O unico artefato de terceiro e um `.js` vendorizado, com os quatro portoes VEND-1..4 |
| **`config.toml` humano (`tomllib`, read-only) · `calibration.json` de maquina (`json`)** | O `cambio.json` segue a **mesma logica**: maquina escreve → `json`. E ele nao encosta no `calibration.json`, que o mercado so le |
| **Nunca hardcodar constante magica** | A porta, o intervalo de polling, os pisos e as larguras de balde saem de constantes nomeadas com a razao escrita ao lado |
| **`Fraction`, nunca `float`, para preco** | Respeitado ate a fronteira do JSON, onde o `float` e **declarado como pixel** e o erro esta medido (pior caso 1,9e-11) |
| **Todo numero exibido carrega `n` e recencia; derivado diz que e derivado** | `Evidencia` viaja dentro de cada resultado e a string do Python ja traz `(derivado)` |
| **Refutacao mora no fonte** | Tres refutacoes desta pesquisa (frequencia da linha parcial, wheel-zoom "nativo", buraco do tripwire) tem de virar comentario no fonte, nao so linha aqui |
| **Nada de `rich`** | Nao aplicavel — nao ha console novo |

---

## Sources

### Primaria (confianca ALTA — medido nesta maquina, 2026-09-01)

- `probe_import.py` / `tempo.py` / `mem3.py` — cadeia de import, tempo e working set, nas **duas** arvores
- `escritor.py` + `leitor.py` + `leitor_cauda.py` + `escritor_grande.py` + **`escritor_rasgado.py`** (controle positivo) — leitura concorrente
- `porta.py` — `allow_reuse_address`, `allow_reuse_port`, `errno 10048`
- `travessia.py` / `travessia2.py` — 10 sondas de travessia
- `prova_servidor.py` — CSP, JSON, POST, listagem, `shutdown`
- `desligar.py` — `poll_interval` × latencia de `shutdown`
- `agregacao.py` / `float_do_grafico.py` — `median_low`, bucketizacao inteira, erro do `float`
- `cambio.py` / `cambio2.py` — `os.replace` atomico e a permissividade do `Decimal`
- `somente_leitura.py` / `escala.py` — impressao digital e custo em escala
- `netsh interface ipv4 show excludedportrange protocol=tcp`; `netstat -ano -p tcp`
- `curl -sIL <cdn>` + `sha256sum` + `grep -o -F` sobre os tres `.min.js`
- **Fonte deste repo, lido nesta sessao:** `l2scanner/mercado_registro.py` (:1-60, :125-140, :255-300, :412-610, :799-880), `l2scanner/mercado_analise.py` (:152-180, :227-262, :286-410, :536-720), `l2scanner/mercado_console.py` (:219-345, :500-600), `l2scanner/mercado_catalogo.py` (:95, :120, :145, :670), `l2scanner/config.py` (:9-48), `l2scanner/console.py` (:11-16, :85-93), `l2scanner/visao.py` (:25-36), `tests/conftest.py`, `tests/test_firewall_escopo.py`, `tests/test_mercado_firewall_de_fase.py` (:1-60, :310-360, :470-530), `tests/test_mercado_analise.py` (:1-45), `vigiar-mercado.bat`, `.gitignore`

### Secundaria (confianca MEDIA — fonte oficial, nao medida aqui)

- `https://github.com/leeoniya/uPlot` — MIT; "~50 KB min"; "No built-in drag scrolling/panning";
  wheel zoom "can be added externally via the plugin/hooks API"; demos `zoom-wheel.html`, `zoom-touch.html`
- `https://registry.npmjs.org/{uplot,dygraphs,lightweight-charts,chart.js,chartjs-plugin-zoom}` — versao, data, licenca, dependencias
- `https://dygraphs.com/options.html` — `animatedZooms`, `panEdgeFraction`, `zoomCallback`; `interactionModel` documentado como "TODO(konigsberg): document this"
- `https://www.w3.org/TR/CSP3/#directive-form-action` — `form-action` restringe destinos de submit
- seam `gsd-tools query package-legitimacy check --ecosystem npm ...`

### Terciaria (confianca BAIXA — raciocinio, marcado para validacao)

- A adequacao do `lightweight-charts` a uma serie esparsa e irregular (A4) — nao testada
- A escolha de faixa de porta (A1) — livre agora, mas nao ha medicao de "quem mais usa"

---

## §1 — A cadeia de import, por extenso

A aresta, com arquivo e linha:

```
l2scanner.mercado_registro   :70  from .mercado_catalogo import PASTA_DO_MERCADO, SEPARADOR
l2scanner.mercado_catalogo   :95  from .config import RAIZ            <-- A ARESTA CARA
l2scanner.config             :37  from .notificador import ConfigChatwoot
l2scanner.notificador        :36  from .rastreador import Evento, TipoDeEvento
l2scanner.rastreador         :56  from .visao import EstadoDaLinha, LeituraDeLinha, Observacao
l2scanner.visao              :30  import cv2
l2scanner.visao              :31  import numpy as np
```

E a segunda aresta, que o corte de `RAIZ` **nao** resolve:

```
l2scanner.mercado_console    :42  from . import console
l2scanner.console            :16  from .rastreador import TipoDeEvento   <-- A SEGUNDA ARESTA
```

`mercado_console` usa de `console` **apenas** `moldurar` — uma funcao de texto puro
`[VERIFICADO: grep "console\." l2scanner/mercado_console.py → so `console.moldurar`]`. `console.py`
usa `TipoDeEvento` so como **chave de dicionario** em `_ESTILO` (`console.py:85-93`) e como
anotacao em `destacar`. Entao a segunda aresta e cortavel de tres formas, todas fora do escopo desta
fase por decisao travada:

- (i) mover `TipoDeEvento` para um modulo-folha — **toca `rastreador.py`, intocavel**;
- (ii) `console.py` importar `TipoDeEvento` sob `TYPE_CHECKING` + lazy dentro de `destacar` — toca
  `console.py`, que e do caminho da party;
- (iii) extrair `moldurar` para um modulo-folha e `console.py` re-exportar — toca `console.py` **e**
  `mercado_console.py`.

**Recomendacao:** **nao cortar a segunda aresta nesta fase.** Cortar so a de `RAIZ` ja tira
`mercado_registro`/`mercado_catalogo` de `cv2`. Para o formatador, a saida barata e importar as
**funcoes puras** de `mercado_console` — mas `import l2scanner.mercado_console` executa o modulo
inteiro e a aresta dispara mesmo assim. Duas saidas honestas:

| Saida | Custo | Consequencia |
|---|---|---|
| **Aceitar `cv2` no processo** so por causa do formatador | +27 MB, +130 ms no arranque, exige o `.venv` | O dashboard continua sem capturar nada; a promessa vira comportamental |
| Extrair `moldurar` (rota iii) | toca 2 arquivos do caminho da party/mercado | Processo do dashboard 100% limpo, roda no Python global |

A decisao e do planejador, e ela **deve** aparecer no plano como tarefa nomeada, nao como efeito
colateral.

---

## §2 — As tres rotas para "ler ate a ultima linha completa" sem um segundo parser

`observacoes_do_arquivo(arquivo: Path)` le o arquivo ela mesma
(`mercado_registro.py:552-556`) e so depois chama `conferir_o_terminador(bruto, arquivo)`. Para
alimentar a ela um **texto ja cortado**, uma das tres:

| Rota | Como | Custo | Risco |
|---|---|---|---|
| **(a) Extrair `observacoes_do_texto(bruto, arquivo)`** e fazer `observacoes_do_arquivo` virar um invólucro de 4 linhas | uma refatoracao de **`mercado_registro.py`**, sem mudar comportamento nenhum | ~15 linhas movidas | **Toca o caminho do `--mercado`** (mesma tensao da Open Question 2). Mas e a unica que mantem literalmente **um** parser e mensagens de erro nomeando o arquivo certo |
| **(b) Escrever o texto cortado num temporario e chamar `observacoes_do_arquivo(temp)`** | zero mudanca no mercado | uma escrita de ate 3 MB por polling; e as mensagens de `ContratoDoArquivoQuebrado` passariam a **nomear o temporario**, nao o `.mercado/observacoes.csv` | O erro que o usuario le aponta para um caminho que nao existe mais. **Recusar** |
| **(c) Chamar as funcoes de portao publicas uma a uma** (`conferir_o_cabecalho`, `chave_dos_campos`, `residuo_dos_campos`) e remontar o laco de `ObservacaoLida` no dashboard | zero mudanca no mercado | ~25 linhas de laco duplicado | E **exatamente** "o segundo parser" que a docstring de `observacoes_do_arquivo` diz existir para nao ter. **Recusar** |

**Recomendacao: (a).** As funcoes de portao ja foram extraidas para modulo na Fase 4 justamente para
isto (`conferir_o_terminador`, `conferir_o_cabecalho`, `chave_dos_campos`, `residuo_dos_campos` sao
todas de modulo, nao metodos) — extrair mais uma e continuar o mesmo movimento, e nao inventar um
novo. E se a Open Question 2 for resolvida como "(A) fazer o corte", entao `mercado_registro.py` ja
esta na lista de arquivos tocados e (a) nao acrescenta tensao nova.

---

## §4 — A comparacao das bibliotecas de grafico, com numeros

**A escolha e do planejador (Claude's Discretion). Isto e a comparacao, nao a escolha.**

| Criterio | **uPlot 1.6.32** | **dygraphs 2.2.2** | **lightweight-charts 5.2.1** |
|---|---|---|---|
| Publicado | 2025-03-14 | 2026-07-27 | 2026-08-12 |
| Downloads/semana | 560.268 | 16.095 | 939.089 |
| Veredito do seam | **OK** | **OK** | **SUS** (`too-new`) |
| Licenca | **MIT** | **MIT** | **Apache-2.0** |
| Arquivo unico? | **nao** — `.js` **+** `.css` | **nao** — `.js` **+** `.css` | **sim** — so o `.js` |
| Bytes do `.js` | **51.081** | 130.226 | 197.922 |
| Bytes do `.css` | 1.857 | 1.255 | 0 |
| **Total vendorizado** | **52.938** | 131.481 | **197.922** |
| VEND-2 (primitivas de rede) | ✅ **zero** | ⛔ **2× `XMLHttpRequest`** | ✅ zero (5× `navigator.userAgent`) |
| Zoom por **arrasto** (box select) | ✅ nativo | ✅ nativo | ✅ nativo |
| **Zoom por roda do mouse** | ❌ **nao** (0 listeners de `wheel`) | ❌ **nao** (0 listeners de `wheel`) | ✅ **sim** (2× `wheel`, 2× `deltaY`) |
| Pan por arrasto | ❌ "No built-in drag scrolling/panning" `[CITADO: repo oficial]` | ⚠ `panEdgeFraction` existe; `interactionModel` sem doc | ✅ nativo |
| Duas series, solido + tracejado | ✅ config por serie | ✅ config por serie | ✅ config por serie |
| Cor de eixo/grade por config | ✅ | ✅ | ✅ |
| Eixo temporal com serie **esparsa e irregular** | ✅ (`x` e um array de timestamps quaisquer) | ✅ | ⚠ **feita para grade temporal regular** (candles). Nao testado — A4 |
| Genericidade (DASH-05) | ✅ a config e por serie | ✅ | ✅ |

`[VERIFICADO: npm registry JSON; curl -sIL content-length; grep -o -F sobre os .min.js baixados]`
`[CITADO: https://github.com/leeoniya/uPlot para "no built-in drag scrolling/panning" e para o wheel via hooks]`

### 🔴 A refutacao que o planejador precisa ver antes de escolher

O UI-SPEC afirma:

> *"Zoom do grafico: Roda do mouse e arrasto, pela biblioteca."* e *"O planejador nao pode exigir da
> biblioteca nada alem de: duas series, traco solido e tracejado, cor de eixo/grade, fonte dos
> rotulos, zoom e pan. **Toda biblioteca dessa classe faz isso com config.**"*

**Medido: falso para duas das tres candidatas.** Nem uPlot nem dygraphs registram um unico listener
de `wheel`:

```
=== uPlot: eventos citados ===
  2 "click"   1 "dblclick"  1 "mousedown"  1 "mouseenter"  1 "mouseleave"
  1 "mousemove"  1 "mouseup"  1 "resize"  1 "scroll"        <-- nenhum "wheel"

=== dygraphs: todos os nomes de evento entre aspas ===
  2 "click"  2 "dblclick"  4 "mousedown"  9 "mousemove"  3 "mouseout"
  1 "mouseover"  7 "mouseup"  2 "resize"  4 "touchstart" ...  <-- nenhum "wheel"

=== lightweight-charts ===
  ... 2 "wheel"                                              <-- o unico
```

E a documentacao oficial do uPlot confirma o mecanismo: zoom com rescale **e** nativo (o arrasto de
selecao), pan **nao** e, e wheel zoom "can be added externally via the plugin/hooks API", com dois
demos oficiais (`zoom-wheel.html`, `zoom-touch.html`).

**Consequencia para o plano, seja qual for a escolha:**

- Se **uPlot** ou **dygraphs**: o wheel-zoom e **codigo nosso** (~25 linhas de
  `over.addEventListener("wheel", ...)` que recalculam a escala e chamam `setScale`). Isso e uma
  **tarefa de plano**, e o UI-SPEC precisa de uma nota de refutacao. Nao e um impedimento — o botao
  `Ver todo o periodo` ja esta especificado e o arrasto-para-zoom nativo cobre o caso principal.
- Se **lightweight-charts**: o wheel vem de graca, mas entram tres custos: veredito **SUS**
  (`too-new`, exige `checkpoint:human-verify`), **Apache-2.0** (permissiva, mas exige preservar o
  `NOTICE`/atribuicao, diferente do MIT) e **197 KB** — quase 4× o uPlot; e o risco A4 (serie
  esparsa numa biblioteca de candles) e o maior dos tres e nao foi medido.

### O que teria de ser escrito a mao se nenhuma qualificasse

Eixo temporal com ticks legiveis (a parte cara: escolher passos de 5 min/1 h/1 dia que caiam em
fronteiras redondas), rescale automatico do eixo Y, hit-testing do cursor para o tooltip, e o
box-select de zoom. Estimativa: **300–500 linhas de canvas**, e e precisamente a categoria que o
CONTEXT chamou de "onde codigo a mao apodrece". **Nenhuma das tres cai nesse caso** — as tres
qualificam; o que muda e o preco do wheel e o preco do VEND-2.

---

## Metadata

**Confianca por area:**

| Area | Nivel | Razao |
|------|-------|-------|
| Cadeia de import (§1) | **ALTA** | Medido nas duas arvores, processo limpo, quatro metricas |
| Leitura concorrente (§2) | **ALTA** | 4 experimentos + **um controle positivo** que provou a sonda |
| Servidor stdlib (§3) | **ALTA** | Bind, CSP, POST, travessia e shutdown medidos com saida colada |
| Biblioteca de grafico (§4) | **MEDIA-ALTA** | Bytes, hashes, licencas e listeners **medidos**; a adequacao visual (A4) e raciocinio |
| Teste sem navegador (§5) | **ALTA** | `poll_interval` medido; idioma da casa lido no fonte |
| Agregacao (§6) | **ALTA** | `median_low`, bucketizacao inteira e erro de `float` medidos |
| Semantica do ponto do grafico | **BAIXA** | **Aberta.** Ver Open Question 1 — precisa do usuario |

**Data da pesquisa:** 2026-09-01
**Valido ate:** 2026-10-01 para a pilha (stdlib, estavel). **7 dias** para os hashes e versoes das
bibliotecas JS — recalcular o SHA-256 no momento de vendorizar, sempre.
