---
phase: 01-dashboard-do-cambio-ao-vivo
workstream: dashboard
verified: 2026-09-02T10:11:38Z
status: human_needed
score: 6/9 criterios de sucesso verificados
behavior_unverified: 3
overrides_applied: 0
re_verification: null
gaps: []
deferred: []
behavior_unverified_items:
  - truth: "Uma pagina nova lida pelo scanner aparece na tela sem recarregar a mao (criterio 1)"
    test: "Com o `--mercado` coletando e o dashboard aberto, abrir a aba Adena e esperar o scanner gravar uma linha nova. Nao tocar no navegador."
    expected: "Em ate ~2 s o numero em destaque e o grafico mudam sozinhos, sem F5, e sem a tela voltar para `Lendo o arquivo...` no meio."
    why_human: "A metade do servidor esta provada (endpoint devolve 11,50 XM sobre o CSV real; `TestOCacheDaLeitura::test_TOCAR_o_arquivo_faz_a_leitura_acontecer_DE_NOVO` prende a releitura por mtime). O que nenhum teste exercita e a REPINTURA do DOM: `darUmaVolta` -> `buscarOsDados` -> `pintar` so roda em navegador, e a casa recusou Playwright por instalador pesado (01-CONTEXT)."
  - truth: "O grafico mostra duas linhas com zoom de horas do dia ate dias atras (criterio 5, metade do desenho)"
    test: "Com serie da Adena na tela, girar a roda sobre o grafico; arrastar com Shift ou botao do meio; arrastar simples para selecionar; clicar em `Ver todo o periodo`."
    expected: "A roda aproxima/afasta em torno do cursor e a pagina NAO rola junto; Shift+arrasto desloca a janela; arrasto simples continua sendo o zoom por selecao nativo; o botao devolve o periodo inteiro. As duas linhas se distinguem por cor E por traco, e onde falta mediana ha VAO, nunca zero."
    why_human: "`ligarOZoomEODeslocamento` foi escrita a mao (uPlot registra zero listeners de `wheel`, medido no 01-RESEARCH). Os testes de fonte (`TestOZoomEDeNosEDizPorQue`, 6 testes) pegam implementacao vazia, evento errado e API errada — mas NAO distinguem um zoom que funciona de um registrador que faz a coisa errada. Esta reserva esta escrita por extenso no proprio 01-07-SUMMARY."
  - truth: "`dashboard.bat` sobe a interface em dois cliques (criterio 9, metade do lancador)"
    test: "Duplo clique no `dashboard.bat` pelo Explorer, com o `.venv` do usuario montado. Repetir com o dashboard ja aberto (porta ocupada). Repetir numa arvore SEM `.venv` (primeira execucao)."
    expected: "Abre o navegador na pagina depois do bind; com a porta ocupada, a janela preta explica e a coleta segue; sem `.venv`, o bloco de primeira execucao monta o ambiente."
    why_human: "O `main()` esta provado (`TestOMainSobeECaiEmVozAlta`, 3 testes; e eu subi o servidor de verdade: bind 127.0.0.1, segundo bind recusado com errno 10048). O `.bat` em si nunca foi executado — os testes dele julgam TEXTO (ASCII, ordem dos blocos, sonda medida e nao copiada). O proprio 01-08-SUMMARY declara isso como verificacao humana."
coincidental_reliance_items: []
human_verification:
  - test: "Ver os itens de `behavior_unverified_items` acima (repintura sem F5, zoom/duas linhas, duplo clique no .bat)"
    expected: "Conforme cada item"
    why_human: "Conforme cada item"
  - test: "UI-SPEC `zero-one-many` (backstop): pedir ao servidor uma segunda serie e instancia-la na tela ao lado da Adena"
    expected: "As duas linhas se distinguem, a legenda cabe, as cores nao brigam, e o titulo longo do OCR corta com reticencia sem invadir a area do numero."
    why_human: "A prova sem navegador (`tests/test_dashboard_serie_generica.py`, 5 elos + controle negativo) cobre dado, contrato, conta, endpoint e as propriedades que o JS consome. O que ela declaradamente NAO cobre e a legibilidade de DUAS series desenhadas ao mesmo tempo — e a reserva esta presa por `TestAFronteiraDestaProvaEstaDECLARADA`."
  - test: "UI-SPEC `stale` (backstop): deixar o dashboard aberto e MATAR o `vigiar-mercado.bat`; esperar passar de uma hora"
    expected: "O valor permanece na tela, a recencia vira `--cor-frio`, a frase de dado velho aparece e a tela nunca afirma `agora`."
    why_human: "A regra de precedencia esta provada no endpoint (medido por mim sobre o CSV real: `Sem leitura nova: ha 9 h (01/09 21:41)`, e `TestOCacheDaLeitura::test_o_aviso_de_DADO_VELHO_aparece_mesmo_com_o_arquivo_PARADO`). O DESENHO do estado velho e verificacao humana declarada."
  - test: "UI-SPEC `long-text` em `#procedencia` (backstop): forcar as frases mais longas do Python no rodape (piso de evidencia + recencia + nota de linha parcial + aviso de cambio)"
    expected: "As frases envolvem em varias linhas sem empurrar o formulario para fora do painel, e nenhuma delas foi reacentuada ou reescrita pelo JS."
    why_human: "Nao ha teste de layout de navegador nesta arvore. A metade afirmavel — que o JS nao e um segundo formatador — esta provada com controle negativo (`TestOJSNaoEUmSegundoFormatador`)."
---

# Fase 1 (workstream `dashboard`): Dashboard do cambio ao vivo — Relatorio de Verificacao

**Goal da fase:** "uma pagina no navegador local responde 'quanto vale 1 milhao de adena agora,
em XM e em R$' e mostra a historia dessa taxa com zoom — lendo o `.mercado/observacoes.csv` que o
`--mercado` ja grava, sem tocar na coleta."

**Verificado:** 2026-09-02T10:11:38Z
**Status:** `human_needed`
**Re-verificacao:** Nao — verificacao inicial.

**A razao do status, em uma frase:** nenhum criterio falhou e nenhum artefato e stub — o que
sobra sao **tres metades de navegador** (repintura sem F5, o zoom/as duas linhas, o duplo clique
no `.bat`) e as **tres linhas `backstop`** do UI-SPEC, todas declaradas como verificacao humana
antes de a fase comecar, todas com um piso automatizado por baixo, e nenhuma escondida atras de
um teste verde.

---

## O que eu confirmei do que o orquestrador ja sabia

Reafirmado aqui para nao ser lido como achado meu — mas conferido, e nao aceito de palavra:

1. **A suite passa.** Rodei os doze arquivos desta fase: **478 passed, 0 failed, 0 skipped** em
   11 s. O teste temporal de `tests/test_janela_de_selecao.py` e de outro workstream e esta fase
   nao o toca — confirmei por `git log` que nenhum commit `01-0N` encosta nele.
2. **A promessa do DASH-06 esta meio cumprida, e isso esta escrito.** Confirmei a refutacao em
   `l2scanner/raiz.py` (docstring, secao "O QUE ESTE CORTE **NAO** COMPRA"), em
   `tests/test_mercado_registro.py` (docstring do teste virado) e em
   `tests/test_mercado_firewall_de_fase.py` (paragrafo (2) do cabecalho reescrito, com as duas
   ressalvas). O `dashboard.bat` tambem sonda `cv2` e `numpy` com a medicao ao lado, em vez de
   prometer o contrario. **A documentacao e honesta**, e a promessa que sobrevive foi verificada
   por mim de forma independente (abaixo, criterio 9).
3. **Duas fronteiras sao verificacao humana declarada**, e nao automacao esquecida. Confirmei
   que ambas tem piso automatizado (`TestOZoomEDeNosEDizPorQue`, 6 testes de fonte;
   `tests/test_dashboard_serie_generica.py`, 5 elos com controle negativo) e que as reservas
   estao presas NO FONTE, nao so no SUMMARY.
4. **As duas edicoes pos-merge do orquestrador conferem.** O UI-SPEC agora rotula `6,12:1` e
   `5,25:1` como `AA (corpo) · AAA (texto grande)` com a nota da correcao (`ba03931`), e o
   `index.html` carrega `vendor/uPlot.iife.min.js` com `defer` antes do `dashboard.js`
   (`1805168`). **Uma ressalva minha sobre esse segundo conserto esta na secao de Anti-Patterns.**

---

## Alcance do Goal

### Verdades Observaveis — os 9 criterios de sucesso do ROADMAP

| # | Criterio | Status | Evidencia |
|---|---|---|---|
| 1 | Dashboard aberto mostra o valor de agora, e pagina nova aparece **sem recarregar a mao** — DASH-01, DASH-04 | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | **Metade do servidor VERIFICADA por mim ao vivo:** subi `montar_servidor`, `GET /dados` -> 200, `estado: serie_presente`, `destaque.xm.texto: "11,50 XM por milhao de adena (derivado)"`, `intervalo_de_polling_ms: 2000`. A releitura por mtime esta presa (`TestOCacheDaLeitura::test_TOCAR_o_arquivo_faz_a_leitura_acontecer_DE_NOVO`). O laco existe e esta ligado (`DOMContentLoaded` -> `comecar` -> `carregarABiblioteca(darUmaVolta)` -> `buscarOsDados`/`pintar`/`agendarAProximaBusca`, `dashboard.js:1153-1171`). **Nenhum teste exercita a repintura do DOM** — ver item humano. |
| 2 | Matar o dashboard nao interrompe a coleta; matar o scanner deixa o dashboard vivo com a **recencia na cara** — DASH-06, DASH-04 | ✓ VERIFICADO | Processos separados por construcao: `dashboard.bat` chama `-m l2scanner.dashboard` direto e **`l2scanner/__main__.py` nao mudou uma linha por causa desta fase** (ultimo toque e do workstream `x9e`). Nenhum modulo do `--mercado` importa `dashboard*`. A recencia foi medida por mim sobre o CSV real: primeiro aviso do payload = `"Sem leitura nova: ha 9 h (01/09 21:41). O valor abaixo e dessa leitura, nao de agora."`, com `velho: true` viajando dentro de cada numero. O DESENHO desse estado e a linha `stale` do UI-SPEC → humano. |
| 3 | Digitar `0,50` faz o R$ aparecer; reabrir **mantem o valor**; a tela diz que foi informado por voce e quando — DASH-02 | ✓ VERIFICADO | Medido por mim: `gravar_o_cambio(tmp, "0,50")` -> `ler_o_cambio` devolve `Decimal('0.50')` com carimbo; o payload seguinte traz `"R$ 5,75 por milhao de adena (derivado do cambio informado por voce em 02/09 07:06)"` com `derivado: true` e `informado_em`. Persistencia em `.mercado/cambio.json` como **historico carimbado**, ultima entrada vigente (conferi o JSON com duas entradas). |
| 4 | **Sem taxa informada**, XM aparece e o R$ e dito indisponivel; **nenhum default e chutado** — DASH-02 | ✓ VERIFICADO | Medido: sem `cambio.json`, `destaque.reais` e literalmente `None` (o sub-objeto **some**, nao vem zerado nem cinza), e o aviso `"R$ indisponivel — nenhum cambio informado."` entra na lista. No CSS, `body[data-cambio="ausente"] #cartao-reais { display: none }`. Portao de duas camadas com controle negativo: recusei `''`, `abc`, `0`, `-1`, `0,,5`, `1,2,3` e o cinco arabe-indico — todos `CambioInvalido`, e **o cambio anterior continuou valendo** (`0.50`) apos a recusa. |
| 5 | Grafico com **duas linhas** e zoom, e **os numeros batem com o console** — DASH-03 | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | **A metade "batem com o console" esta VERIFICADA:** `test_o_texto_do_destaque_e_IDENTICO_ao_que_o_console_imprime` compara byte a byte com `mercado_console.formatar_taxa_derivada`, e as frases de piso sao provadas SUBSTRING de `mercado_console._linha_do_menor` / `_linha_da_mediana`. **Sem segundo parser** — `ArquivoRecortado` reusa `mercado_registro.observacoes_do_arquivo`, com as tres rotas alternativas recusadas por escrito. **Sem segundo formatador** — `TestOJSNaoEUmSegundoFormatador` com controle negativo. A metade do DESENHO (duas linhas + zoom) → humano. |
| 6 | CSV aberto **somente para leitura**, provado por medicao | ✓ VERIFICADO | Medido por mim, com impressao de tres componentes `(st_size, st_mtime_ns, sha256)`: inalterada apos `payload()` sobre o `.mercado/` real, e inalterada apos gravar cambio duas vezes numa copia. Na suite: `TestOServidorNaoEscreveNoCSV::test_cinquenta_pedidos_e_um_POST_nao_mudam_um_BYTE_do_CSV`, mais o tripwire de fonte que proibe `"w"`, `"a"` e `mkdir` dentro de `Manipulador`. `dashboard_dados.observacoes_ao_vivo` abre com `"r"`. Unica escrita: `.mercado/cambio.json` (e o teste afirma que nenhum temporario fica para tras). |
| 7 | Com o scanner apendando, **nao exibe linha parcial e nao some com a serie** | ✓ VERIFICADO | Medido por mim cortando o CSV real 40 bytes no meio de uma linha: `estado: serie_presente`, `cauda_incompleta: true`, `linhas_completas: 142` (era 143), **39 series sobreviveram**, destaque intacto em `11,50 XM`, e o PRIMEIRO aviso e `"Ultima linha ignorada: incompleta (o scanner estava escrevendo)."` A divergencia da regra do terminador da Fase 3 esta escrita no fonte (`observacoes_ao_vivo`, docstring inteira), com a frequencia real MEDIDA (0 de 22.970) e o controle positivo que acusou 3.252 de 4.079 — o zero e resultado, nao cegueira da sonda. |
| 8 | Componente de serie instanciavel para uma segunda serie **sem codigo de grafico novo**, provado em teste — DASH-05 | ✓ VERIFICADO | O criterio pede uma prova em teste, e ela existe em cinco elos: dado (dois elementos), contrato (conjuntos de chaves IDENTICOS), conta (formatador do ponto de decisao unico, textos diferindo em FORMA), servidor (os dois atravessam o endpoint) e navegador por leitura de fonte (toda propriedade que `desenharUmaSerie` consome existe nos DOIS) — **com controle negativo no extrator**, sem o qual o elo 5 passaria por vacuidade. Confirmei ao vivo: o payload sobre o CSV real traz **39 series**, todas com as mesmas 7 chaves, e `series` e lista mesmo com um elemento so. |
| 9 | `dashboard.bat` sobe em dois cliques, e o caminho do `--mercado` fica intocado — DASH-06 | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | **A metade "o `--mercado` nao muda" esta VERIFICADA por atribuicao commit a commit** (ver Cerca de Escopo). **A metade do duplo clique nao foi executada** — ver item humano. Nota de contrato: a letra "byte-identico" deste criterio foi formalmente substituida por "comportamento identico" no DASH-06, com aprovacao do usuario em 2026-09-01 e o preco da alternativa medido dentro do proprio requisito; verifico contra a redacao vigente, nao contra a revogada. |

**Score:** **6/9 verificados** (3 presentes e ligados, com o comportamento de navegador nao
exercitado). Nenhum criterio FALHOU.

### Cerca de Escopo (DASH-06) — atribuicao por commit, e nao por `git diff`

O branch e compartilhado com `renda`, `x9e` e `260901-p2r`, entao um diff contra a base da fase
nao mede esta fase. Atribui **cada arquivo preexistente ao commit que o tocou**:

| Arquivo preexistente | Commit desta fase | Autorizado? |
|---|---|---|
| `l2scanner/config.py` | `5ac2219` (01-01) | **Sim** — 1 linha removida (a definicao antiga de `RAIZ`), substituida por re-exportacao. Conferi o diff: `ARQUIVO_ENV`, `ARQUIVO_CONFIG` e `ARQUIVO_CONFIG_LOCAL` intocados. |
| `l2scanner/mercado_catalogo.py` | `5ac2219` (01-01) | **Sim** — a unica linha do `mercado`, nomeada por CTX-2. |
| `tests/test_mercado_firewall_de_fase.py` | `5ac2219`, `435083d` | **Sim** — nomeado. |
| `tests/test_mercado_registro.py` | `5ac2219` | **Sim, pela excecao documentada** — o tripwire foi VIRADO (`"True True"` -> `"False False"`) na instrucao escrita da propria docstring dele, e nao apagado. |

**Nenhum quinto arquivo.** Conferi o ultimo toque de `__main__.py`, `mercado_modo.py`,
`mercado_console.py`, `mercado_registro.py`, `mercado_analise.py`, `rastreador.py`, `visao.py`,
`vigiar-mercado.bat` e `requirements.txt` — **nenhum deles foi tocado por um commit desta fase**.
`requirements.txt` nao ganhou uma linha (zero dependencia Python nova; o uPlot e ativo estatico
vendorizado, e a distincao esta escrita).

### A decisao literal do usuario sobre o grafico (CTX-1) — conferida no dado real

O ponto travado era: **um ponto = um instante de leitura**, mediana ausente na maior parte, e
**frase de piso em vez de numero** onde ela falta — sem cumulativo. Medido por mim agora, sobre
as 143 linhas reais:

```
pontos: 3            (de 143 linhas — a agregacao por instante, literal)
  21:28:37  menor 12,00 XM  | tipica 18,00 XM              (esse instante alcancou n>=5)
  21:41:15  menor 18,00 XM  | tipica "sem evidencia - 1 de 5 ofertas distintas, faltam 4"
  21:41:28  menor 11,50 XM  | tipica "sem evidencia - 2 de 5 ofertas distintas, faltam 3"
```

A frase de piso aparece, o numero nunca e chutado, e a agregacao larga usa
`statistics.median_low` (D-02: um numero exibido tem de ter existido) com `median`, `mean` e
`median_high` refutadas por escrito no fonte. **Nenhum cumulativo foi contrabandeado de volta** —
nem no Python nem no JS, onde `TestOEstadoEhLIDOeNaoRECALCULADO` prende que os pisos nao viram
comparacao no navegador.

### Artefatos Exigidos

| Artefato | Esperado | Status | Detalhes |
|---|---|---|---|
| `l2scanner/raiz.py` | Modulo folha com a medicao e a refutacao | ✓ VERIFICADO | 88 linhas; **zero import relativo**; docstring com as 4 metricas nas duas arvores e a secao do que o corte NAO compra. |
| `l2scanner/dashboard_dados.py` | Leitura ao vivo, agregacao, payload | ✓ VERIFICADO | 1062 linhas; executado por mim contra o CSV real, sem stub. |
| `l2scanner/dashboard_cambio.py` | Portao de 2 camadas, escrita atomica, historico | ✓ VERIFICADO | 424 linhas; escrita atomica com sufixo temporario limpo; 7 formas invalidas recusadas na bancada. |
| `l2scanner/dashboard.py` | Servidor stdlib endurecido | ✓ VERIFICADO | 838 linhas; subi ao vivo — bind `127.0.0.1`, `allow_reuse_address=False` (segundo bind -> errno 10048), listagem 404, travessia `/../` 404, CSP/nosniff/no-referrer, portao de origem no POST. |
| `.../recursos/dashboard/index.html` | Tres regioes, form real, nada embutido | ✓ VERIFICADO | 261 linhas; 6 estados por atributo no `<body>`; `maxlength=12`, `placeholder="0,50"`, `value=""`; carrega uPlot e o `dashboard.js` com `defer` na ordem certa. |
| `.../recursos/dashboard/dashboard.css` | Tema L2 com contraste recalculado | ✓ VERIFICADO | 848 linhas; `clamp(32px,6vw,48px)`, `tabular-nums`, `text-overflow: ellipsis`, grade desenhada no estado vazio. |
| `.../recursos/dashboard/dashboard.js` | Polling, estados, serie generica, zoom | ✓ VERIFICADO | 1171 linhas; **`node --check` passa** (rodei; o `node` existe nesta maquina, entao o teste da suite tambem rodou de verdade). |
| `.../vendor/uPlot.*` | Biblioteca com proveniencia conferivel | ✓ VERIFICADO | uPlot 1.6.32, `uPlot.LICENSE` (MIT), `README.md` de 13 KB com a contagem POR primitiva, `.gitattributes`. Servido ao vivo: 51.081 bytes, 200. |
| `dashboard.bat` | Lancador irmao, erros ANTES da execucao | ✓ VERIFICADO | 168 linhas; blocos de erro acima com `goto executar` por cima; sonda de dependencia MEDIDA para este processo (nao copiada do irmao); recusa instalar com a coleta rodando. |

### Verificacao dos Elos (wiring)

| De | Para | Via | Status |
|---|---|---|---|
| `dashboard_dados` | `mercado_registro` | `observacoes_do_arquivo(ArquivoRecortado)` — **um parser so** | ✓ WIRED |
| `dashboard_dados` | `mercado_analise` | `menor_pedido_visivel` / `mediana_dos_unitarios` / `recencia_do_preco` | ✓ WIRED |
| `dashboard_dados` | `mercado_console` | `formatador_do_unitario` — **um ponto de decisao so** | ✓ WIRED |
| `dashboard.py` | `dashboard_dados.payload` | `CacheDaLeitura.pronto` com chave composta (arquivo + minuto + cambio) | ✓ WIRED (medido ao vivo) |
| `dashboard.py` | `dashboard_cambio.gravar_o_cambio` | unica escrita, delegada e nominal | ✓ WIRED |
| `index.html` | `vendor/uPlot.iife.min.js` | `<script src defer>` antes do `dashboard.js` | ✓ WIRED (200 no HTTP) — **mas sem guarda de teste, ver Anti-Patterns** |
| `dashboard.js` | `GET /dados` | `fetch(CAMINHO_DOS_DADOS)` no laco | ✓ WIRED |
| `dashboard.js` | `POST /cambio` | `enviarOCambio` com `preventDefault` | ✓ WIRED |
| `mercado_catalogo` | `raiz` | `from .raiz import RAIZ` (aresta do `cv2` cortada) | ✓ WIRED |

### Traco de Fluxo de Dado (Nivel 4)

| Artefato | Valor exibido | Fonte | Dado real? | Status |
|---|---|---|---|---|
| `#xm-texto` | `11,50 XM por milhao de adena (derivado)` | CSV real -> `menor_pedido_visivel` -> `formatador_do_unitario` | Sim | ✓ FLOWING |
| `#reais-texto` | `R$ 5,75 por milhao...` | XM x `cambio.json` (0,50) | Sim | ✓ FLOWING |
| `#serie-grafico` | 3 pontos / 3 baldes | `pontos_por_instante` + `baldes` | Sim | ✓ FLOWING |
| `#serie-vazio-prova` | `N linhas, M da serie` | `linhas_completas` + `evidencia.n` | Sim | ✓ FLOWING |
| `#nota-linha-parcial` | nota de cauda | `LeituraAoVivo.cauda_incompleta` | Sim (medido com o CSV cortado) | ✓ FLOWING |
| `#fonte-arquivo` | caminho | `_fonte()` | Sim | ✓ FLOWING |

**Nenhum valor termina em literal, retorno estatico ou mock.**

### Spot-checks comportamentais (executados por mim, nesta arvore)

| Comportamento | Comando | Resultado | Status |
|---|---|---|---|
| Suite da fase | `pytest` nos 12 arquivos | 478 passed, 0 failed, 0 skipped, 11 s | ✓ PASS |
| Payload sobre CSV real | `dashboard_dados.payload(Path(".mercado"), now())` | `serie_presente`, `11,50 XM`, 39 series, `somente_leitura: true` | ✓ PASS |
| Somente-leitura | `(size, mtime_ns, sha256)` antes/depois | identico | ✓ PASS |
| Cauda cortada 40 B | payload sobre copia truncada | `cauda_incompleta: true`, 142 linhas, 39 series vivas, aviso primeiro | ✓ PASS |
| Cabecalho trocado | payload | `erro_de_contrato`, mensagem nomeia o arquivo REAL | ✓ PASS |
| Arquivo ausente | payload | `arquivo_ausente` com a frase propria | ✓ PASS |
| Cambio valido | `gravar` + `ler` + payload | `0.50` -> `R$ 5,75` com carimbo e `derivado: true` | ✓ PASS |
| Cambio invalido (7 formas) | `interpretar_o_cambio` | 7/7 `CambioInvalido`; anterior segue valendo | ✓ PASS |
| Historico carimbado | 2 gravacoes | JSON com 2 entradas, ultima vigente | ✓ PASS |
| Servidor ao vivo | `montar_servidor(0, ...)` | `127.0.0.1`; `/dados` 200; `/` 200; `/vendor/` 404; `/../config.py` 404; uPlot 200 (51.081 B) | ✓ PASS |
| Portao de origem | POST com `Origin` forasteira / ausente | 403 nos dois, frase travada, nada gravado | ✓ PASS |
| Bind exclusivo | segundo `montar_servidor` na mesma porta | `OSError errno=10048` | ✓ PASS |
| Sintaxe do JS | `node --check dashboard.js` | exit 0 | ✓ PASS |

### Execucao de Probes

Nao ha `scripts/*/tests/probe-*.sh` nesta arvore e nenhum PLAN/SUMMARY desta fase declara
probe — a doutrina de prova daqui e pytest. **Step 7c: N/A.** Os spot-checks acima cobrem o
papel (executados no meu processo, com a saida registrada, e nao aceitos do SUMMARY).

### Cobertura de Requisitos

| Requisito | Descricao (resumo) | Status | Evidencia |
|---|---|---|---|
| DASH-01 | Somente-leitura, degrada para a ultima linha completa, divergencia no fonte | ✓ SATISFEITO | Impressao de 3 componentes inalterada (medida); corte de 40 B preservou a serie; docstring de `observacoes_ao_vivo` com a divergencia e a medicao (0/22.970) |
| DASH-02 | XM->BRL manual, persistido, declarado como informado, sem default | ✓ SATISFEITO | `.mercado/cambio.json` carimbado; `derivado: true`; sem cambio o cartao SOME; 7 recusas na bancada |
| DASH-03 | Zoom, duas linhas, bate com o console, sem segundo parser | ⚠️ PARCIAL | Parser unico, formatador unico e paridade com o console VERIFICADOS; o desenho das duas linhas e o zoom sao humanos (criterio 5) |
| DASH-04 | Valor de agora com `n` e recencia; nunca afirma "agora" sobre dado velho | ✓ SATISFEITO | `n`, `recencia` e `velho` viajam dentro de cada numero; aviso de dado velho medido |
| DASH-05 | Componente generico, Adena e a primeira instancia, provado em teste | ✓ SATISFEITO | 5 elos + controle negativo; 39 series com chaves identicas no payload real |
| DASH-06 | Lancador proprio, processo separado, comportamento do `--mercado` identico | ✓ SATISFEITO (com a refutacao escrita) | Cerca de escopo atribuida commit a commit; `config` re-exporta `RAIZ` (mesmo objeto); a segunda aresta do `cv2` esta declarada em 3 lugares |

**Nenhum requisito orfao.** DASH-01..06 mapeados na fase e todos reclamados por algum plano.

### Cobertura de Decisoes (CONTEXT)

O gate automatico (`check.decision-coverage-verify`) devolveu `could-not-parse` — o bloco
`<decisions>` e prosa em portugues e o motor busca pistas em ingles. **Nao bloqueante**, e
conferi a mao: layout de tres regioes, dois numeros lado a lado, tema L2, estado vazio como
conteudo, polling ~2 s (2000 ms servido pelo servidor), arquivo inteiro carregado, um ponto = um
instante, `median_low` no zoom largo, `.mercado/cambio.json`, entrada em reais por 1 XM, carimbo
por alteracao, cambio de hoje aplicado a serie **com o aviso na tela**, `http.server` da stdlib,
biblioteca vendorizada, bind so em `127.0.0.1`, unica escrita e o `cambio.json`, prova sem
navegador — **todas honradas**. Nenhuma decisao abandonada em silencio.

### Auditoria de Qualidade dos Testes

| Aspecto | Resultado |
|---|---|
| Testes desabilitados sobre requisito | **0.** Os dois `pytest.skip` sao condicionais de ambiente (`node` ausente, `.env` ausente), ambos com a razao dita e ambos **nao acionados** nesta maquina (0 skipped na rodada). |
| Padroes circulares | **0.** Os valores esperados vem de fontes independentes: `mercado_console` (sistema preexistente, de outro workstream), a formula da WCAG conferida contra os dois extremos (`#FFF/#000 = 21,00`, `#E0B450/#E0B450 = 1,00`), e fixtures escritas a mao. |
| Forca das assercoes | **Valor e comportamental.** Comparacao byte a byte com o console; impressao de 3 componentes; HTTP real contra servidor real. |
| Controles negativos | **Presentes e discriminantes** — conferi 4 deles: o detector de primitivas de rede acusa `fetch(`/`XMLHttpRequest`/`sendBeacon`/`new Function`/`WebSocket` e **nao** acusa uso legitimo de uPlot; o guarda de `requirements.txt` reprova sobre um texto adulterado com `plotly>=6.0`; o extrator de propriedades do JS acusa nos dois sentidos; o tripwire de import foi provado capaz de **distinguir as duas arvores** (1 failed com a linha revertida, 18 passed com ela). |
| Guardas que nao podem falhar | **Um encontrado** — ver Anti-Patterns. |

### Anti-Patterns Encontrados

| Arquivo | Linha | Padrao | Severidade | Impacto |
|---|---|---|---|---|
| `l2scanner/dashboard_dados.py` | 1046 | `TODO` | ℹ️ Info — **falso positivo** | E a palavra portuguesa em `"# TODO NUMERO VIAJA COM n E RECENCIA"`. Nao e marcador de divida. |
| `tests/test_dashboard_servidor.py` | 968 | `TODO` | ℹ️ Info — **falso positivo** | Idem: `"O conteudo de TODO arquivo servivel"`. |
| `tests/test_dashboard_pagina.py` | 199-209 | Guarda fraca | ⚠️ **WARNING** | `test_todo_script_carrega_por_ARQUIVO` afirma que existe **algum** `<script>` e que todos tem `src` — **nao** afirma que `vendor/uPlot.iife.min.js` esta entre eles, nem a ordem. Ha teste de ORDEM para o CSS do vendor (`FOLHA_DA_BIBLIOTECA` antes do nosso) e **nenhum** simetrico para o script. |

**Zero `TBD` / `FIXME` / `XXX` / `HACK` / `PLACEHOLDER` reais** nos oito arquivos de producao da
fase. Nenhum stub, nenhum `return null` de conveniencia, nenhum dado embutido.

#### Sobre o WARNING, e por que ele nao e bloqueador

O conserto do orquestrador (`1805168`, a linha `<script src="vendor/uPlot.iife.min.js" defer>`)
**entrou sem guarda**. Somando: nem a linha do `index.html`, nem o carregador de reserva
`carregarABiblioteca` (`dashboard.js:1131-1151`) sao mencionados por **nenhum** teste desta arvore
— conferi por grep nos dois arquivos de teste candidatos. Apagar as duas rotas deixaria a suite
inteira verde e o grafico jamais apareceria (o codigo cai em `console.error` e segue).

Nao e bloqueador porque **as duas rotas existem e funcionam hoje** (servi o arquivo por HTTP: 200,
51.081 bytes) e sao redundantes de proposito. Mas e exatamente a assimetria que a doutrina desta
fase persegue: o CSS do vendor tem guarda de ordem, o JS do vendor nao tem guarda nenhuma. **Vale
uma linha de teste** — que `vendor/uPlot.iife.min.js` esta entre os `src` e vem antes de
`dashboard.js` — e ela fecharia o unico ponto da fase em que uma regressao passaria calada.

### Verificacao Humana Necessaria

#### 1. A tela se atualiza sozinha (criterio 1)
**Teste:** com o `--mercado` coletando e o dashboard aberto, abrir a aba Adena e esperar o
scanner gravar. **Nao tocar no navegador.**
**Esperado:** em ~2 s o numero e o grafico mudam sozinhos, sem F5, e sem voltar para
`Lendo o arquivo...`.
**Por que humano:** a metade do servidor esta provada (endpoint + releitura por mtime); a
repintura do DOM so roda em navegador, e Playwright foi recusado por doutrina.

#### 2. O zoom e as duas linhas (criterio 5 — onde o ROADMAP repousa)
**Teste:** roda sobre o grafico; `Shift`+arrasto e botao do meio; arrasto simples; botao
`Ver todo o periodo`.
**Esperado:** zoom em torno do cursor **sem a pagina rolar junto**; deslocamento; selecao nativa
preservada; periodo inteiro restaurado. Duas linhas distintas por **cor E traco**, e **vao** onde
falta mediana — nunca zero.
**Por que humano:** o zoom foi escrito a mao porque uPlot registra zero listeners de `wheel`
(medido). Assercao de fonte pega implementacao vazia; nao pega um registrador que faz a coisa
errada.

#### 3. O duplo clique no `dashboard.bat` (criterio 9)
**Teste:** duplo clique pelo Explorer. Repetir com o dashboard ja aberto. Repetir sem `.venv`.
**Esperado:** navegador abre **depois** do bind; porta ocupada explica na janela preta e a coleta
segue; primeira execucao monta o ambiente.
**Por que humano:** `main()` esta provado e eu subi o servidor de verdade; o `.bat` em si nunca
foi executado — os testes dele julgam texto.

#### 4. UI-SPEC `zero-one-many` (backstop)
**Teste:** instanciar uma segunda serie ao lado da Adena na tela.
**Esperado:** as duas linhas se distinguem, a legenda cabe, o titulo longo do OCR corta com
reticencia sem invadir o numero.
**Por que humano:** a prova sem navegador cobre 5 elos e **declara** que nao cobre a legibilidade
de duas series desenhadas juntas.

#### 5. UI-SPEC `stale` (backstop)
**Teste:** dashboard aberto, matar o `vigiar-mercado.bat`, esperar passar de uma hora.
**Esperado:** o valor permanece, a recencia vira `--cor-frio`, a frase de dado velho aparece, a
tela nunca afirma `agora`.
**Por que humano:** a precedencia esta provada no endpoint (e medida por mim); o desenho nao.

#### 6. UI-SPEC `long-text` em `#procedencia` (backstop)
**Teste:** forcar as frases mais longas do Python no rodape ao mesmo tempo.
**Esperado:** envolvem em varias linhas sem empurrar o formulario para fora do painel, e nenhuma
foi reacentuada pelo JS.
**Por que humano:** nao ha teste de layout de navegador; a metade afirmavel (nao ser um segundo
formatador) esta provada com controle negativo.

### Resumo — o que falta, e o que nao falta

**Nao falta nada de codigo.** Os nove criterios estao implementados, ligados e com dado real
fluindo ponta a ponta; os seis requisitos estao cobertos em substancia; as 13 linhas `✅ covered`
das `## UI Considerations` tem artefato real no `index.html`/`dashboard.css`; as 3 linhas
`🧪 backstop` **rotearam para verificacao humana em vez de passar caladas**, que era exatamente o
que o UI-SPEC pediu delas. A cerca de escopo do DASH-06 nao foi rompida — quatro arquivos
preexistentes, todos autorizados, o quarto pela excecao que a docstring dele mesmo mandava. E a
promessa que o DASH-06 quebrou (o `cv2` no processo do dashboard) esta escrita em quatro lugares
do fonte com a medicao ao lado, o que e a forma da casa de dizer que um numero caiu.

**Falta o navegador.** Tres metades desta fase (repintura, zoom/duas linhas, duplo clique) e as
tres linhas `backstop` so podem ser afirmadas por um humano com o jogo ao lado — e isso foi
decidido antes de a fase comecar, com o Playwright recusado por instalador pesado, e esta
declarado no fonte e nao so nos SUMMARY. **Por isso o status e `human_needed` e nao `passed`:
`passed` exigiria a secao de verificacao humana vazia, e ela nao esta.**

**E falta uma linha de teste** (o WARNING acima): o `<script>` do uPlot e o carregador de reserva
nao tem guarda nenhuma, num arquivo cujo irmao de CSS tem. Nao bloqueia o goal — bloqueia o
sono de quem vier depois.

---

*Verificado: 2026-09-02T10:11:38Z*
*Verificador: Claude (gsd-verifier)*
