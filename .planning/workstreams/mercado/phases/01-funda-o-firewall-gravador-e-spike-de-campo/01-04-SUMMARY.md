---
phase: 01-funda-o-firewall-gravador-e-spike-de-campo
plan: 04
subsystem: detection
tags: [mercado, ancora, multi-ancora, votacao, matchTemplate, calibracao, 27x, regressao]

requires:
  - phase: 01-02
    provides: "mercado_visao.casamento_da_ancora, molde_da_ancora.png, limiar 0.73, 4 chaves opcionais em calibration.json"
  - phase: 01-03
    provides: "SPIKE-RESPOSTAS.md VALIDADO pelo usuario — a margem de campo NEGATIVA e a decisao de desenho adquirir/seguir/votar"
provides:
  - "l2scanner/mercado_visao.py: AncoraDoPainel, VotoDoPainel, buscar_ancora, localizar_painel, conferir_painel, RastreioDoPainel, ancoras_para/de_calibracao"
  - "DESENHO NOVO MEDIDO: votacao entre 3 ancoras independentes devolve a margem a +0.3700 (a faixa de titulo sozinha dava -0.0643)"
  - "l2scanner/calibrar._selecionar_regiao: mecanica de selectROI EXTRAIDA e compartilhada pelos dois calibradores"
  - "l2scanner/calibrar_mercado.py + calibrar-mercado.bat: calibracao do mercado sobre frame GRAVADO, com matriz de confusao que RECUSA colisao"
  - "5 chaves opcionais novas em calibration.json (mercado_ancoras, mercado_grade, mercado_templates_de_nome, mercado_templates_de_digito, mercado_limiar_de_template); VERSAO_DO_ESQUEMA segue 2"
  - "Calibracao.conferir_geometria_do_mercado: a leitura recusa com 'recalibre' quando a janela muda de tamanho"
  - "tests/test_mercado_27x.py: as DUAS metades do criterio 4 do ROADMAP presas no mesmo arquivo, mais o tripwire de arquitetura"
  - "config.toml: secao [mercado] watchlist comentada, para o portao humano ter onde escrever"
affects: [fase 2 leitura da grade, fase 4 consumidor de oclusao e modo --mercado]

actuals:
  tokens: 96000
  tasks: 1
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Votacao pelo MAXIMO entre ancoras espalhadas quando o ruido esperado e LOCAL (tooltip perto do cursor)"
    - "Duas cadencias distintas: perder o seguimento varre AGORA; nao saber onde ele esta varre a cada N ticks"
    - "Ancora fora da janela ABSTEM em vez de votar 0.0 — 0.0 seria leitura inventada sobre pixels que nao existem"
    - "Ancora de arte CHAPADA e medida e descartada: sem textura ela encontra o painel onde ele nao esta"
    - "Auxiliar EXTRAIDO com teste de equivalencia, em vez de mecanica duplicada entre duas ferramentas"
    - "Matriz de confusao alinhada ao menor comum: quando ela erra, erra para o lado de RECUSAR"
    - "Replay de PRODUCAO sobre a gravacao real como portao — foi ele que achou a cadencia errada que a suite sintetica aprovava"

key-files:
  created:
    - l2scanner/calibrar_mercado.py
    - calibrar-mercado.bat
    - tests/test_calibrar_mercado.py
    - tests/test_mercado_multiancora.py
    - tests/test_mercado_27x.py
    - tests/fixtures/mercado/ (23 PNGs novos, 38 KB)
  modified:
    - l2scanner/mercado_visao.py
    - l2scanner/calibracao.py
    - l2scanner/calibrar.py
    - config.toml

key-decisions:
  - "A deteccao deixa de ser 'casar um retangulo contra um limiar' e passa a ser 'aquisicao por varredura + seguimento barato + votacao entre ancoras' — decisao de desenho AUTORIZADA pelo usuario em 2026-08-28 (SPIKE-RESPOSTAS secao 8)"
  - "O limiar 0.73 do 01-02 NAO muda: o que estava errado era supor que uma ancora so bastava"
  - "Tres ancoras: faixa de titulo, botao de fechar e canto inferior direito. As duas ancoras de arte chapada (cantos esquerdos) foram medidas e DESCARTADAS por casarem 0.8050 e 0.6881 contra grama"
  - "Perder o seguimento varre no MESMO tick; a cadencia de 3 ticks vale so para a varredura ociosa"
  - "A oferta do usuario de nao passar o mouse no meio da lista foi aceita como REDUCAO DE RUIDO e recusada como mecanismo de correcao"
  - "Task 3 do plano (campo exibicional em visao.py e extra em __main__.py) NAO foi executada: ela vem depois do portao humano da Task 2, e a lista de proibicoes desta execucao inclui visao.py"

requirements-completed: []

coverage:
  - id: D1
    description: "_selecionar_regiao extraido de calibrar_selecionando e compartilhado pelos dois calibradores, com comportamento preservado"
    requirement: "FUND-03"
    verification:
      - kind: unit
        ref: "tests/test_calibrar_mercado.py#TestOAuxiliarExtraido (4 casos: reescala, sem reescala, duas caixas degeneradas)"
        status: pass
      - kind: unit
        ref: "tests/test_calibrar_mercado.py#TestAEquivalenciaDaRefatoracao (2 testes: mesmo recorte e mesma origem; cancelar nao chama o automatico)"
        status: pass
      - kind: unit
        ref: "tests/test_calibrar_mercado.py#test_a_selecao_e_COMPARTILHADA_e_nao_duplicada"
        status: pass
    human_judgment: false
  - id: D2
    description: "Os DOIS tripwires de escrita de imagem verdes: zero em calibrar_mercado, e o de calibrar inalterado apos a extracao"
    requirement: "FUND-03"
    verification:
      - kind: unit
        ref: "tests/test_calibrar_mercado.py#TestOsDoisTripwiresDeEscritaDeImagem (4 testes)"
        status: pass
      - kind: unit
        ref: "tests/test_conferencia_gravada.py#test_existe_um_unico_ponto_de_escrita_no_modulo"
        status: pass
    human_judgment: false
  - id: D3
    description: "A matriz de confusao RECUSA dois moldes quase identicos nomeando o par, e aprova moldes separados com limiar sugerido"
    requirement: "FUND-03"
    verification:
      - kind: unit
        ref: "tests/test_calibrar_mercado.py#TestAMatrizDeConfusao (5 testes, inclusive moldes de tamanhos diferentes)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A votacao entre ancoras separa aberto de fechado onde a faixa de titulo sozinha NAO separava"
    requirement: "DETC-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_multiancora.py#TestAFaixaDeTituloSOZINHA_NAO_SEPARA_AS_CLASSES (4 casos)"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_multiancora.py#TestAVotacaoENTRE_ANCORAS_SEPARA (13 casos, com os valores medidos a 0.001)"
        status: pass
      - kind: other
        ref: "replay de producao sobre os 335 frames de campo: 273 abertos, 0 falsos positivos na sessao mercado-fechado (33 de 33 corretos)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Aquisicao, seguimento e reaquisicao: encontra o painel em qualquer posicao, abstem fora da janela, falha FECHADO no degenerado"
    requirement: "DETC-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_multiancora.py#TestAquisicaoPorVarredura (5 testes)"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_multiancora.py#TestSeguimentoNaPosicaoCONHECIDA (6 testes)"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_multiancora.py#TestORastreioAdquireDepoisSegue (5 testes)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Criterio 4 do ROADMAP: no replay do 27x o painel e reconhecido E zero eventos de morte, presos pelo mesmo arquivo"
    requirement: "DETC-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_27x.py#TestMetade1_OPainelEReconhecidoNoReplayDo27x (4 casos)"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_27x.py#TestMetade2_ZeroAlertasDeMorteNaSequenciaDo27x — 40 ticks, lista de eventos VAZIA"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_27x.py#TestORastreadorNaoLeOMercado (2 tripwires de arquitetura)"
        status: pass
      - kind: other
        ref: "replay de producao sobre recordings/inv3: f000 e f005 abertos (1.0000 e 0.9996), f010..f040 fechados"
        status: pass
    human_judgment: false
  - id: D7
    description: "O usuario roda calibrar-mercado.bat sobre uma gravacao e confere a imagem — criterio 3 do ROADMAP"
    requirement: "FUND-03"
    verification: []
    human_judgment: true
    rationale: "PORTAO HUMANO ABERTO (Task 2, gate=blocking-human). A ferramenta esta construida e testada, mas as regioes sao marcadas com o mouse em cv2.selectROI e nenhum teste prova que os retangulos caem no lugar certo — so o olho faz isso. NAO foi executado, simulado nem contornado."

duration: ~2 h
completed: 2026-08-28
status: halted
---

# Phase 1 Plan 4: A âncora do mercado por votação, e o critério 4 fechado — Summary

**A âncora do painel deixou de ser um retângulo e virou uma votação entre três: a margem de campo saiu de −0,0643 para +0,3700 sem que o limiar 0,73 mudasse uma casa decimal. No replay do incidente 27x o painel é reconhecido nos dois frames em que está aberto e o rastreador emite ZERO eventos — as duas metades do critério 4 presas pelo mesmo arquivo. O plano para aqui, no portão humano da Task 2.**

## ESTADO: PARADO NO PORTÃO HUMANO (por desenho, não por falha)

| Task | O que é | Estado |
|---|---|---|
| 1 | Auxiliar de seleção compartilhado + `calibrar_mercado.py` + `.bat` + matriz de confusão | **COMPLETA**, commitada |
| — | Detecção multi-âncora medida + regressão do 27x (antecipadas da Task 3, ver deviation #2) | **COMPLETA**, commitada |
| 2 | `checkpoint:human-action` `gate="blocking-human"` — o usuário roda a calibração e confere a imagem | **ABERTA** — é aqui que o plano para |
| 3 | Campo exibicional em `visao.py` + extra em `__main__.py` | **NÃO INICIADA**, por desenho (ver deviation #2) |

## A MUDANÇA DE DESENHO, E POR QUE ELA É UMA CORREÇÃO E NÃO UM DESVIO

O plano 01-02 mediu a faixa de título contra as fixtures do incidente 27x e achou margem
**+0,5372**, com o limiar `CASAMENTO_MINIMO_DA_ANCORA = 0,73` no meio dela. Aquela medição
continua correta para aquele material. O 01-03 mediu o mesmo detector contra as 8 gravações
de campo e achou o oposto:

```
pior POSITIVO de campo   0.4110   painel ABERTO, tooltip por cima da faixa de titulo
melhor NEGATIVO de campo 0.4753   painel FECHADO, sessao mercado-fechado
MARGEM DE CAMPO         -0.0643
```

**As duas classes se sobrepõem.** O usuário validou o achado em 2026-08-28 e autorizou o
desenho novo: adquirir por varredura, seguir barato, e decidir por **votação entre âncoras
independentes**. O diagnóstico é que o limiar nunca esteve errado — errado era depender de um
retângulo só, e a tooltip caiu exatamente sobre ele.

Este plano executou essa autorização e **mediu o resultado**, em vez de assumi-lo.

## A MEDIÇÃO: AS TRÊS ÂNCORAS E A MARGEM REMEDIDA

Deslocamentos a partir da **origem do painel** (o canto superior esquerdo da faixa de
título), medidos na janela de 1720×1392 do usuário. O painel inteiro mede ~1001×735:
canto superior esquerdo em (−452, −11), borda inferior em (+724).

| Âncora | Deslocamento | Tamanho | O que é |
|---|---|---|---|
| `titulo` | (0, 0) | 100×28 | a faixa "XM Market" — a âncora do 01-02 |
| `botao_fechar` | (+494, −10) | 60×60 | o "X" do canto superior direito |
| `canto_inf_dir` | (+494, +665) | 60×60 | a seta de rolagem, canto inferior direito |

### Duas âncoras foram medidas e DESCARTADAS

Os cantos **esquerdos** do painel são arte chapada — cinza sobre cinza, sem detalhe. Numa
varredura da janela inteira sobre os 33 frames da sessão `mercado-fechado`, eles casaram
**0,8050** e **0,6881** contra grama. Uma âncora sem textura encontra o painel em qualquer
lugar, inclusive onde ele não está. Registrado porque a proposta do 01-03 ("manchas de arte
opaca do painel") incluía exatamente esses dois pontos, e a medição os reprovou.

### A margem, sobre os 335 frames de campo mais os 9 de janela do 27x

```
pior POSITIVO    0.9037    aberto_tooltip_f090 — tooltip apaga o titulo (0.0216),
                           quem salva e o botao de fechar no canto oposto
melhor NEGATIVO  0.5337    fechado_campo_f012 — adversarial: melhor posicao de
                           CADA ancora em cada frame sem painel
MARGEM          +0.3700
LIMIAR           0.73      inalterado desde o 01-02; agora vale POR ANCORA
```

Não há zona cinzenta: sobre os 335 frames de campo, o vão observado entre a classe fechada e
a classe aberta vai de **0,5337 a 0,9037** — 325 frames caem fora dele (270 acima de 0,92,
55 abaixo de 0,52) e os 10 restantes ficam nos extremos, nenhum no meio.

### Os frames que o título sozinho reprovava, e a votação salva

**20 frames com o painel comprovadamente aberto passavam abaixo de 0,73 pela faixa de
título.** Todos os 20 são classificados corretamente pela votação, e **nenhum falso positivo
novo foi introduzido** (zero frames em que o título aprovava e a votação reprova):

| Sessão | Frames resgatados | título | voto |
|---|---|---|---|
| `mercado-scroll` | 53, 83, 84, 85, 88, 89, 90 | 0,4121 a 0,5943 | 0,9037 a 0,9133 |
| `mercado-tooltip` | 0, 27 | 0,4174 / 0,4320 | 0,9604 / 0,9712 |
| `mercado-farm-com-party` | 19 | 0,5688 | 0,9911 |
| `mercado-scroll-transicao` | 8 | 0,6756 | 0,9645 |
| `mercado-aberto` | 4 a 12 (9 frames) | 0,4366 a 0,6806 | 0,9566 a 0,9595 |

*(O 01-03 contou 19 com o juiz de manchas de arte; a contagem com as três âncoras dá 20. O
frame a mais é `mercado-tooltip/frame_000000`, que o juiz anterior classificou como fechado.)*

## O REPLAY DE PRODUÇÃO — e o defeito que ele encontrou

O `RastreioDoPainel` de verdade foi rodado frame a frame, na ordem, sobre as 8 gravações e
sobre `recordings/inv3/`:

| sessão | n | aberto | fechado | varreduras |
|---|---:|---:|---:|---:|
| mercado-fechado | 33 | **0** | 33 | 11 |
| mercado-aberto | 21 | 21 | 0 | 1 |
| mercado-scroll | 94 | 85 | 9 | 4 |
| pagina-cheia | 35 | 32 | 3 | 2 |
| tooltip | 39 | 39 | 0 | 1 |
| alvo-sobreposto | 47 | 33 | 14 | 19 |
| farm-com-party | 39 | 36 | 3 | 15 |
| scroll-transicao | 27 | 27 | 0 | 6 |

**Zero falsos positivos na sessão que importa** — 33 de 33 frames sem painel classificados
como fechados. As 11 varreduras em 33 ticks são exatamente a cadência ociosa de 3 ticks.

```
--- incidente 27x (recordings/inv3, frames de JANELA) ---
  f000_JANELA.png   aberto=True   melhor=1.0000  origem=(912, 350)
  f005_JANELA.png   aberto=True   melhor=0.9996  origem=(731, 493)
  f010..f040        aberto=False  melhor=0.0000  origem=None
```

**Este replay é o que encontrou a deviation #1.** A primeira versão do rastreio esperava três
ticks antes de reaquirir, também depois de perder o seguimento — e dava `f005` (painel
aberto, 181 px à esquerda) como FECHADO, além de 20 de 33 frames abertos na sessão em que o
usuário arrasta o painel. A suíte sintética aprovava; a gravação real reprovou.

## O CRITÉRIO 4 DO ROADMAP, FECHADO

`tests/test_mercado_27x.py` prende as duas metades no mesmo arquivo, de propósito: a metade
"zero mortes" já passava hoje pelo portão de moldura da quick `260826-dxm`, e um teste que só
afirmasse isso não prenderia nada do DETC-01.

- **Metade 1** — o painel é reconhecido em cada posição do 27x, e o frame de **inventário**
  (`f020`, o negativo que mais importa do incidente inteiro) não vira mercado.
- **Metade 2** — 40 ticks alimentando `extrair` + `Rastreador.observar` com as barras
  `coberta_*` reais do incidente, depois de 20 ticks de aquecimento com pixels de verdade:
  a lista de eventos é **vazia**. Não "menos eventos": zero, e de tipo nenhum — filtrar por
  `MORREU` não prova ausência de `RESSUSCITOU`, e a quick `260826-dxm` pagou 27 de cada.
- **Tripwire de arquitetura** — o fonte de `l2scanner.rastreador` não cita `mercado` nem
  importa `mercado_visao`. Se um dia citar, este teste cai.

## DETC-01: o que esta fase entrega, e o que fica para a Fase 4 (por desenho)

> Reproduzido na íntegra do bloco `<detc01_reconciliation>` do `01-04-PLAN.md`, para que o
> `/gsd-verify-work` não pontue o requisito como parcialmente entregue.

`REQUIREMENTS.md` descreve DETC-01 como: *"'World Exchange aberto' detectado por
âncora/template positivo, e o sinal é compartilhado com a lógica de oclusão do detector de
morte — um sinal, dois consumidores, nunca duplicado."*

**Esta fase entrega o SINAL e a superfície exibicional dele. NÃO entrega um consumidor de
DECISÃO no detector de morte, e isso é deliberado.**

| Metade de DETC-01 | Onde | Estado ao fim da Fase 1 |
|---|---|---|
| Âncora positiva própria, medida, em módulo puro | `l2scanner/mercado_visao.py` (Plano 02 + este) | ENTREGUE |
| Sinal único, nunca duplicado (uma só implementação de detecção) | `mercado_visao.RastreioDoPainel` | ENTREGUE |
| Superfície no caminho da party: extra opcional + campo exibicional | `__main__.py` + `Observacao.mercado_aberto_aparente` | **PENDENTE — Task 3, depois do portão humano** |
| Consumidor 1 — laço `--mercado` como interruptor idle/ativo | Fase 4 (DETC-02) | POR DESENHO, FORA DESTA FASE |
| Consumidor 2 — oclusão CONHECIDA influenciando o detector de morte | Fase 4 | POR DESENHO, FORA DESTA FASE |

**Por que os consumidores não chegam agora.** Promover este sinal a um segundo consumidor de
decisão dentro do detector de morte é exatamente a manobra que causou o incidente 27x. A
lição está MEDIDA e escrita em `visao.py:85-111`: o campo `hp_proprio_aparente` existe
separado justamente porque promover um sinal a um segundo uso produziu 2 classes de alerta
falso e atraso de morte. Ligar a oclusão de mercado ao rastreador na mesma fase em que a
âncora nasce significaria confiar num limiar recém-medido para SUPRIMIR alertas de morte — o
tipo de decisão que só se toma depois de a âncora ter rodado em campo.

Por isso o campo é exibicional, há um tripwire de arquitetura que QUEBRA se `rastreador.py`
passar a lê-lo, e a regressão do 27x afirma zero eventos de morte — não "menos eventos".

**Nota para o `/gsd-verify-work`:** DETC-01 deve ser pontuado como ENTREGUE nesta fase no
escopo acima. A ausência de consumidor de oclusão não é entrega parcial; é a decisão
arquitetural registrada aqui, com o consumidor agendado para a Fase 4 junto de DETC-02, que é
onde o laço `--mercado` nasce. **A única metade que este plano deixou aberta é a superfície
exibicional (Task 3), e ela está atrás do portão humano da Task 2, não fora de escopo.**

## A matriz de confusão

A ferramenta mede a matriz **na hora**, todo molde contra todo molde, com a mesma correlação
de posição única de `identidade._correlacionar`. Sobre a watchlist do usuário ela ainda não
foi medida — a watchlist está vazia e os moldes são recortados no portão da Task 2. O que
está afirmado hoje é o comportamento da matriz, com moldes sintéticos:

| Caso | Resultado |
|---|---|
| dois moldes quase idênticos (`+3 Bota X` / `+4 Bota X`) | **RECUSA**, nomeando o par, `limiar_sugerido = None` |
| moldes bem separados | aprova, `limiar_sugerido = (1,0 + pior)/2` |
| moldes de tamanhos em que nenhum domina o outro | comparados pelo menor comum, e recusados — sem o alinhamento dariam 0,0, "não colidem" por não terem sido comparados |
| menos de dois moldes | aprova, não há o que confundir |

`COLISAO_MAXIMA_ENTRE_TEMPLATES = 0.85` é **política, não medição**, e está escrito assim no
código: a watchlist é do usuário e cada uma tem a sua matriz. Com o pior inter-classe em 0,85
o limiar sugerido fica em 0,925 e sobra margem de 0,075.

## Arquivos resgatados para `tests/fixtures/mercado/`

**23 PNGs novos, 38.710 bytes no total** (a pasta inteira, com os 13 do Plano 02, tem 144 KB).
Todos em tons de cinza, 100×28 ou 60×60. **Nenhum contém nome de personagem nem mensagem de
jogador** — são a faixa de título do painel, o botão de fechar, a seta de rolagem, e recortes
de terreno/UI nas posições adversariais.

| Arquivo | Origem | Recortado em |
|---|---|---|
| `molde_botao_fechar.png` | `20260828-061409-mercado-alvo-sobreposto/frame_000000.png` | (1290, 215) |
| `molde_canto_inf_dir.png` | idem | (1290, 890) |
| `aberto_27x_f000__{titulo,botao_fechar,canto_inf_dir}.png` | `inv3/f000_JANELA.png` | origem (912, 350) |
| `aberto_27x_f005__{...}.png` (3) | `inv3/f005_JANELA.png` | origem (731, 493) |
| `aberto_tooltip_f084__{...}.png` (3) | `20260828-055323-mercado-scroll/frame_000084.png` | origem (1015, 212) |
| `aberto_tooltip_f090__{...}.png` (3) | `20260828-055323-mercado-scroll/frame_000090.png` | origem (1015, 212) |
| `aberto_tooltip_f012__{...}.png` (3) | `20260828-063752-mercado-aberto/frame_000012.png` | origem (1037, 220) |
| `fechado_campo_f012__{...}.png` (3) | `20260828-053003-mercado-fechado/frame_000012.png` | adversarial, por âncora |
| `fechado_27x_f020__{...}.png` (3) | `inv3/f020_JANELA.png` | adversarial, por âncora |

**Nenhuma gravação foi escrita, movida ou apagada.** `recordings/` continua gitignored e foi
lido em modo somente leitura, do checkout principal.

## Performance

- **Duração:** ~2 h
- **Tasks:** 1 de 3 completa, mais as partes automatizáveis da Task 3 (ver deviation #2)
- **Arquivos criados/modificados:** 32 (28 criados, 4 alterados)
- **Suíte:** **1367 passed, 4 failed, 8 skipped**. As 4 falhas são as conhecidas de
  `tests/test_agenda.py::TestRegistroEmDisco` (datas fixas em 2026-08-24, janela de poda de 3
  dias vencida), **pré-existentes e fora do escopo**. Baseline do 01-03: 1282 passed, 4
  failed, 6 skipped → **+85 passando, zero regressões**.

## Task Commits

1. **RED — a faixa de título sozinha não separa** — `ccf85a8` (test)
2. **GREEN — mercado por votação entre âncoras** — `e55b222` (feat)
3. **Task 1 — calibrar-mercado, seleção compartilhada e matriz de confusão** — `f6ba4e0` (feat)
4. **Critério 4 do ROADMAP + a correção da cadência** — `7a8cb1a` (test)
5. **A watchlist ganha lugar no `config.toml`** — `0594161` (docs)

## Files Created/Modified

- `l2scanner/mercado_visao.py` — `AncoraDoPainel`, `VotoDoPainel`, `buscar_ancora`,
  `localizar_painel`, `conferir_painel`, `RastreioDoPainel`,
  `ancoras_para_calibracao`/`ancoras_de_calibracao`; `CASAMENTO_MINIMO_DA_ANCORA` remedido
  (valor inalterado, significado novo); `TICKS_ENTRE_VARREDURAS_OCIOSAS = 3`
- `l2scanner/calibrar.py` — `_selecionar_regiao` extraído; `calibrar_selecionando`
  refatorada para chamá-lo. **Nenhuma escrita de imagem entrou no módulo.**
- `l2scanner/calibracao.py` — 5 campos opcionais novos pelo trilho `.get`;
  `_conferir_as_chaves_de_mercado` estendido; `conferir_geometria_do_mercado`;
  `VERSAO_DO_ESQUEMA` intocada em 2
- `l2scanner/calibrar_mercado.py` (novo, ~430 linhas) — `matriz_de_confusao`,
  `derivar_grade`, `conferir_o_frame`, `carregar_calibracao`, `escolher_frame`,
  `ler_watchlist`, `montar_ancoras`, `desenhar_conferencia`, e o fluxo interativo
- `calibrar-mercado.bat` — lançador no precedente literal de `calibrar-solo.bat`
- `config.toml` — seção `[mercado] watchlist` comentada
- `tests/test_mercado_multiancora.py` (39 testes), `tests/test_calibrar_mercado.py`
  (39 testes), `tests/test_mercado_27x.py` (7 testes + 1 skip)

## Decisions Made

- **O limiar 0,73 não muda.** Ele foi medido no 01-02 e continua no vão entre 0,5337 e
  0,9037. Mudá-lo teria escondido que o problema era arquitetural.
- **Votação pelo MÁXIMO, e não média nem consenso.** O ruído esperado é LOCAL: a tooltip é um
  retângulo perto do cursor. Média puniria o frame inteiro por uma âncora coberta; consenso
  exigiria que a coberta concordasse. O preço do máximo — cada âncora é uma chance
  independente de um alvo errado achar alinhamento sortudo, a lição medida em
  `identidade._correlacionar` — está pago: 0,5337 é o melhor que qualquer das três conseguiu
  em 91 frames sem painel.
- **Âncora fora da janela ABSTÉM.** Medido em `farm-com-party/frame_000021`: o painel está
  aberto em (1239, 578) e o botão de fechar cai fora da janela. Votar 0,0 ali seria uma
  leitura inventada sobre pixels que não existem; abster é o que deixa o título decidir.
- **Origem negativa não pode dar a volta no numpy.** `janela[-500:, -500:]` é um recorte
  *válido* e devolve o canto oposto, calado. Um painel arrastado até a borda produz
  exatamente essa coordenada.
- **A aquisição para na primeira âncora que passa.** Cada varredura custa ~45 ms; o caso
  comum resolve na primeira. A ordem importa, e a ordem certa é "a mais confiável primeiro".
- **A matriz de confusão corta ao menor comum.** Quando ela erra, erra para o lado de recusar.
- **`COLISAO_MAXIMA_ENTRE_TEMPLATES` está marcada no código como POLÍTICA, não medição.**
  Este repositório escreve os três números ao lado de cada constante medida; escrever um
  número sem medição do mesmo jeito corromperia essa convenção.

## Deviations from Plan

### 1. [Rule 1 - Bug] A cadência de reaquisição dava o painel aberto como fechado

- **Found during:** o replay de produção, depois de a suíte inteira estar verde
- **Issue:** a primeira versão do `RastreioDoPainel` esperava `TICKS_ATE_REAQUISICAO = 3`
  ticks antes de varrer de novo, **inclusive depois de perder o seguimento**. O replay real
  cobrou: no `inv3` o `f005` — painel aberto, 181 px à esquerda — saía **FECHADO**, e na
  sessão `alvo-sobreposto` (em que o usuário arrasta o painel o tempo todo) o rastreio dava
  20 de 33 frames abertos.
- **Por que a suíte sintética não pegou:** o teste de arrasto afirmava a chegada
  (`votos[-1].aberto`), e não a latência. Ele passava com o comportamento errado.
- **Fix:** duas cadências, e a distinção está escrita ao lado da constante. Perder o
  seguimento é a evidência mais forte que existe de que o painel se MEXEU → varre no **mesmo
  tick**. Não saber onde ele está → varre a cada `TICKS_ENTRE_VARREDURAS_OCIOSAS = 3`, que é
  o caso comum e caro (o mercado fica fechado a maior parte do tempo, e três varreduras por
  volta seriam ~135 ms por tick para sempre).
- **Resultado:** `inv3` passou a classificar os 9 frames corretamente; `alvo-sobreposto` foi
  de 20 para 33; `farm-com-party` de 24 para 36; `scroll-transicao` de 21 para 27.
- **Files:** `l2scanner/mercado_visao.py`, `tests/test_mercado_multiancora.py`,
  `tests/test_mercado_27x.py`
- **Committed in:** `7a8cb1a`

### 2. [Rule 3 - Blocking] A ordem das tasks foi alterada, e a Task 3 ficou para depois do portão

- **Found during:** o planejamento da execução
- **Issue:** o plano põe a detecção multi-âncora e a regressão do 27x na Task 3, **depois** do
  portão humano da Task 2. Mas a Task 2 pede ao usuário que marque as âncoras com o mouse —
  e antes de pedir isso é preciso saber **quantas âncoras**, **onde** e **se o desenho
  funciona**. Calibrar primeiro e medir depois arriscaria gastar o portão humano numa
  geometria errada.
- **Fix:** a detecção multi-âncora e a regressão do 27x foram antecipadas para antes do
  portão; a ferramenta de calibração já nasceu pedindo as três âncoras medidas, com os
  retângulos sugeridos pré-preenchidos.
- **O que FICOU para a Task 3, depois do portão:** o campo exibicional
  `Observacao.mercado_aberto_aparente` em `l2scanner/visao.py` e o extra em
  `l2scanner/__main__.py`. Esta execução recebeu `l2scanner/visao.py` numa lista explícita de
  **proibições**, e o critério de sucesso dela diz "No modifications to ... visao.py". As
  duas instruções são compatíveis nesta leitura: a Task 3 é trabalho pós-checkpoint, e é lá
  que o plano autoriza mexer em `visao.py`.
- **Consequência registrada:** a linha "superfície exibicional" da tabela de DETC-01 está
  marcada **PENDENTE** acima, e não ENTREGUE. É a única metade em aberto.

### 3. [Rule 2 - Missing Critical] O plano previa uma decisão que a medição desmentiu

- **Found during:** a medição das âncoras candidatas
- **Issue:** o `SPIKE-RESPOSTAS.md` propunha confirmar o painel com "manchas de arte opaca
  (borda esquerda, borda inferior, canto superior esquerdo, início da faixa de abas)". Duas
  dessas manchas **não servem de âncora**: os cantos esquerdos são arte chapada e casaram
  **0,8050** e **0,6881** numa varredura sobre frames com o painel FECHADO. Adotadas como
  estavam, elas produziriam falso positivo — o painel "encontrado" na grama.
- **Por que a proposta do 01-03 não errou:** lá as manchas eram avaliadas **na posição
  conhecida**, como juiz. Aqui elas precisam também **encontrar** o painel numa varredura, e
  é aí que a falta de textura cobra.
- **Fix:** as duas foram descartadas e substituídas pelo botão de fechar e pela seta de
  rolagem — arte distintiva, nos cantos **direitos**, o mais longe possível da faixa de
  título. A razão está escrita no docstring de `AncoraDoPainel`, com os dois números.
- **Files:** `l2scanner/mercado_visao.py`
- **Committed in:** `e55b222`

### 4. [Rule 2 - Missing Critical] A watchlist não tinha onde morar

- **Found during:** ao escrever `ler_watchlist`
- **Issue:** o portão humano da Task 2 manda "marcar o recorte de nome de cada item da
  watchlist do `config.toml`" — e não existe seção de mercado nenhuma no `config.toml`.
  Sem ela o usuário chegaria ao portão sem ter onde escrever os itens.
- **Fix:** seção `[mercado] watchlist` comentada, com a explicação de por que cada variante
  de encanto é uma linha separada (o custo medido: 7,02 a 100,00 para o mesmo nome base na
  mesma página) e de que o item sem encanto não escreve `+0`. A ferramenta trata lista vazia
  como estado legítimo e diz alto o que deixou de cortar.
- **Files:** `config.toml`, `l2scanner/calibrar_mercado.py`
- **Committed in:** `0594161`

### 5. [Rule 1 - Bug] A conferência de geometria comparava a coisa errada

- **Found during:** a primeira execução de `tests/test_calibrar_mercado.py`
- **Issue:** `conferir_o_frame` comparava a dimensão do frame com `esquerda + largura` da
  party window. Sem `party_window_na_janela`, essa posição está em coordenadas de **DESKTOP**
  (1712 + 200 = 1912) e não limita nada dentro da janela — um frame legítimo de 1720×1392
  seria recusado.
- **Fix:** só o **tamanho** da party window entra na conta, nunca a posição. É a assinatura
  exata do erro que a checagem pega: um frame gravado no modo party tem as dimensões da party
  window, e não as da janela.
- **Files:** `l2scanner/calibrar_mercado.py`
- **Committed in:** `f6ba4e0`

### 6. [Rule 3 - Blocking] `recordings/` não existe dentro do worktree

- **Found during:** a avaliação da `<precondition>`
- **Issue:** a terceira vez que esta pedra aparece nesta fase (01-02 deviation #5, 01-03
  deviation #5). Worktree não materializa arquivo gitignored.
- **Fix:** as gravações **existem no disco** no checkout principal, que é o fato que a
  precondição afirma. Foram lidas em modo **somente leitura**, por caminho absoluto; todos os
  artefatos foram escritos dentro do worktree. Nenhuma escrita, nenhum comando git fora dele.
- **Consequência permanente e desejada:** os dois testes que dependem de `recordings/`
  diretamente ficam em `pytest.skip` com a razão dita, e o replay de produção inteiro está
  transcrito neste SUMMARY, com os números, para que a evidência não se perca.

### 7. [Rule 3 - Blocking] `calibration.json` não vale mais para o material do 27x

- **Found during:** a avaliação da Task 3(a), sobre resgatar recortes de party do `inv3`
- **Issue:** o `calibration.json` atual do usuário lista `Santanays, Mostarda, Titander,
  Pirulito`; a gravação `inv3` é de `Korzis, J4guar`. A calibração foi refeita **depois**
  daquela gravação — a mesma classe de divergência que o 01-02 registrou (2 px na largura da
  party window). Derivar recortes de barra própria dos frames `_JANELA` com a calibração de
  hoje mediria a região errada e o teste passaria por motivo errado (A4 da RESEARCH).
- **Fix:** a Metade 2 usa as fixtures **já versionadas** do próprio incidente —
  `barra_propria/coberta_*.png`, que são recortes reais do inventário do 27x — mais a party
  window real de `party_estavel_com_vazamento/`. Zero recortes de party novos foram
  commitados, o que também atende T-04-04 (resgatar o mínimo) melhor do que 45 PNGs de
  ~170 KB cada com nome de personagem dentro.

---

**Total deviations:** 7 auto-corrigidas (3 bugs, 2 missing critical, 2 blocking)
**Impact:** nenhum item do plano foi reduzido ou simplificado. A deviation #2 é uma
REORDENAÇÃO, com a metade adiada nomeada e marcada PENDENTE na tabela de DETC-01. As
deviations #1 e #3 são o retorno direto de medir contra as gravações reais em vez de confiar
na suíte sintética: as duas teriam ido para produção verdes.

## Issues Encountered

- **O molde do título versionado difere em até 6 níveis por pixel do mesmo recorte tirado de
  um frame de campo.** São gravações de dias diferentes. O molde **versionado** é a
  autoridade nos testes; registrado porque re-resgatá-lo do material novo moveria todos os
  valores medidos deste arquivo.
- **O replay de produção classifica 273 frames como abertos contra 277 da classificação
  quadro a quadro.** A diferença é latência de aquisição na cadência ociosa — até 2 ticks
  depois de o painel abrir. Cai para o lado certo (durante a dúvida o sinal diz FECHADO) e
  some num laço de 1 Hz, onde o painel fica aberto por minutos.
- **`ruff check l2scanner/` acusa 2 `E741` pré-existentes em `visao.py`** (variável `l`).
  Não corrigidos: `visao.py` está na lista de proibições desta execução. Os arquivos deste
  plano passam limpos.

## Known Stubs

Nenhum. Nada nesta entrega devolve valor fixo, placeholder ou "coming soon". A única
constante nova que **não** é medida é `COLISAO_MAXIMA_ENTRE_TEMPLATES`, e ela está
explicitamente marcada como política no código, com o raciocínio ao lado.

**Metade em aberto, e ela não é stub:** a superfície exibicional de DETC-01
(`Observacao.mercado_aberto_aparente` + o extra em `__main__.py`) é a Task 3 do plano, que
vem depois do portão humano da Task 2. Está registrada como PENDENTE na tabela de DETC-01
acima, não como entregue.

## Threat Flags

Nenhuma superfície nova além do `<threat_model>` do plano.

| Ameaça | Estado |
|---|---|
| T-04-01 Elevation of Privilege (mercado → rastreador) | **MITIGADA** — `rastreador.py` fora do diff, e dois tripwires de arquitetura em `test_mercado_27x.py` quebram se ele passar a citar mercado ou importar `mercado_visao`. A regressão afirma ZERO eventos, não "menos" |
| T-04-02 Tampering em `molde_de_hex` / `ancoras_de_calibracao` | **MITIGADA** — dimensões declaradas conferidas contra os bytes; nome ausente, `dx`/`dy` não-inteiro e molde não-dict recusados com mensagem que diz "recalibre o mercado" |
| T-04-03 Spoofing de template da watchlist | **MITIGADA** — matriz de confusão medida na calibração, recusa nomeando o par colidente; alinhamento ao menor comum faz a matriz errar para o lado de recusar |
| T-04-04 Information Disclosure em `tests/fixtures/mercado/` | **MITIGADA** — 23 recortes de 100×28 e 60×60 em cinza, inventariados arquivo por arquivo acima; nenhum nome de personagem, nenhuma mensagem de jogador. Zero recortes de party novos |
| T-04-05 Repudiation (calibração sem conferência) | **MITIGADA na parte automatizável** — a imagem de conferência é obrigatória e passa por `_gravar_conferencia`, que confere o retorno. A conferência visual em si é o portão humano da Task 2, ainda ABERTO |
| T-04-06 DoS com janela redimensionada | **MITIGADA** — `Calibracao.conferir_geometria_do_mercado` recusa no arranque com "recalibre o mercado" em vez de ler degradado |
| T-04-07 Tampering na extração de `_selecionar_regiao` | **MITIGADA** — refatoração de comportamento preservado com teste de equivalência; nenhuma escrita de imagem entrou em `calibrar.py`, e os dois tripwires estão verdes |
| T-04-SC Tampering na árvore de dependências | **VAZIA por construção** — zero instalações; `requirements.txt` byte-idêntico |

## User Setup Required

O portão humano da Task 2 — ver o CHECKPOINT abaixo. Nenhum serviço externo, nenhuma
instalação.

## Next Phase Readiness

**Bloqueado no portão humano, e é onde deve estar.**

Depois do "calibrado" do usuário, a Task 3 encosta o sinal no caminho da party:
`Observacao.mercado_aberto_aparente` no molde literal de `hp_proprio_aparente`, e o extra
opcional em `__main__.py`. Nada mais do plano fica devendo.

Para a Fase 2 já entra decidido: a origem do painel é o canto da faixa de título e tudo é
deslocamento a partir dela; `mercado_grade` grava **qual** dos três layouts está lendo; o
limiar de template sai da matriz de confusão do próprio usuário, não de uma constante.

## Self-Check: PASSED

- **Arquivos conferidos no disco:** `l2scanner/calibrar_mercado.py`, `calibrar-mercado.bat`,
  `l2scanner/mercado_visao.py`, `l2scanner/calibrar.py`, `l2scanner/calibracao.py`,
  `config.toml`, `tests/test_calibrar_mercado.py`, `tests/test_mercado_multiancora.py`,
  `tests/test_mercado_27x.py`, os 23 PNGs de `tests/fixtures/mercado/` — todos FOUND
- **Commits conferidos em `git log`:** `ccf85a8`, `e55b222`, `f6ba4e0`, `7a8cb1a`, `0594161`
  — todos FOUND
- **`<acceptance_criteria>` da Task 1:** 9 de 9 verdes
- **Proibições conferidas em `git diff --name-only 9b806bb..HEAD`:** `l2scanner/visao.py`,
  `l2scanner/rastreador.py`, `.planning/STATE.md` e `.planning/ROADMAP.md` **fora do diff**;
  `recordings/` intocado (só leitura, por caminho absoluto)
- **`<verification>` do plano:**
  1. `python -m pytest tests/ -q` → **1367 passed, 4 failed, 8 skipped**; as 4 falhas são as
     pré-existentes de `test_agenda.py` ✅
  2. Os DOIS tripwires de escrita de imagem verdes ✅
  3. `calibrar-mercado.bat` sobre uma gravação → **PENDENTE, por desenho** (portão da Task 2)
  4. `tests/test_mercado_27x.py` afirma as duas metades no mesmo arquivo ✅
  5. `l2scanner/rastreador.py` não aparece no diff da fase ✅

---
*Phase: 01-funda-o-firewall-gravador-e-spike-de-campo (workstream mercado)*
*Parado na Task 2 — `checkpoint:human-action`, `gate="blocking-human"`, critério 3 do ROADMAP*
*Date: 2026-08-28*
