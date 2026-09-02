# Roadmap: Quanto rende esta hora (workstream `renda`)

**Workstream:** renda (`.planning/workstreams/renda/`)
**Milestone:** v1-renda — quanto rende esta hora, e quanto falta para o nível
**Criado:** 2026-09-02
**Granularidade:** coarse (3 fases)
**Ponto de partida:** um repositório maduro. `l2scanner/` tem **41.562 linhas** e 255+ testes,
e a maior parte do trabalho pesado desta milestone **já está escrita**. Este roadmap monta
peças existentes; ele quase não inventa.

## O que já existe e NÃO se reconstrói

Escrito aqui em cima, e não numa nota de rodapé, porque é a diferença entre esta milestone
ser três fases e ser oito.

| Peça | Onde | O que ela já resolve para nós |
|---|---|---|
| OCR do Windows (WinRT) | `l2scanner/ocr.py` — `ler_texto`, `ler_texto_ampliado`, `disponivel`, `motivo_indisponivel` | O spike leu `Special 58,40 13,091 10,679,769` da direita da barra com `ler_texto` sobre o recorte **cru**, sem pré-processamento nenhum. A leitura da adena já quase funciona. |
| Leitor de dígitos por molde de glifo | `l2scanner/mercado_leitura.py` — `segmentar_glifos`, `ler_glifos`, `moldes_da_tinta`, `mascara_de_numero`, `quantidade_de_adena`, `numero_valido` | Um leitor de números **feito para a fonte deste jogo**, com máscara por `valor_minimo`, pontuação de glifo e recusa nomeada. É o plano B do EXP% e do nível — e provavelmente o plano A do nível, que o OCR cru já devolveu vazio. |
| Calibração e o `calibration.json` | `l2scanner/calibracao.py`, `calibrar.py`, `calibrar_mercado.py` | A convenção inteira: `Regiao`, `LimiaresDeCor`, campos opcionais por feature, carregamento validado, e dois `.bat` que já ensinam o usuário a calibrar. |
| Captura e cegueira | `l2scanner/captura_janela.py`, `visao.py`, `frames.py` (`SaudeDoFrame`, `FRAMES_IDENTICOS_PARA_CONGELADO = 30`), `cliente.py` (`EstadoDoCliente.TELA_DE_LOGIN`, `esta_na_tela_de_login`) | Captura por janela (Windows Graphics Capture), detecção de frame escuro/congelado e reconhecimento da tela de login — endurecidos em **quatro rodadas de correção** no v1. CEGO-01 e CEGO-02 são reuso, não invenção. |
| Registro append-only com contrato | `l2scanner/mercado_registro.py` — `COLUNAS`, `conferir_o_cabecalho`, `conferir_o_terminador`, `ContratoDoArquivoQuebrado` | O dialeto (`;`, `csv` da stdlib, cabeçalho-contrato, `"a"` em vez de reescrita atômica) e as **quatro divergências deliberadas** já argumentadas por escrito. |
| Recorte da cauda para leitor ao vivo | `l2scanner/dashboard_dados.py` — `ArquivoRecortado`, `observacoes_ao_vivo` | A degradação "leio até a última linha completa", com a medição que a sustenta: **zero** leituras sem terminador em 22.970 sondagens durante 200.000 appends concorrentes, e um controle positivo que acusou 3.252 de 4.079 quando o defeito existia. |
| Painel `rich.Live` | `l2scanner/console.py`, `mercado_console.py` | A disciplina de tela da casa: `n` e recência coladas em todo número, `MARCA_DO_COMPONENTE_VELHO` para dado velho, `resumo_da_sessao` no fim. |
| Relógio que entra por parâmetro | `l2scanner/relogio.py` | **Nenhum módulo deste projeto chama `datetime.now()`.** O PC é dual boot e o Windows fica ~3h adiantado ao voltar do Linux; a hora vem do cabeçalho `Date` do Chatwoot uma vez e depois avança pelo monotônico. Para uma milestone que é **inteiramente taxa por unidade de tempo**, isto não é convenção de estilo — é a fundação. |

## Por que três fases e não as quatro que os requisitos sugeriram

O `REQUIREMENTS.md` propôs 1 leitura / 2 conta / 3 registro / 4 tela, e essa é a forma do
`v1-mercado`, que fechou 18/18. Duas fases dela foram fundidas, e o motivo é medível.

**REND-04 é um requisito sobre o REGISTRO que estava morando na fase da conta.** Ele diz, com
todas as letras, "uma queda no contador é um gasto, **registrado como tal**" e "o registro
precisa deixar farm e venda distinguíveis". Decidir o esquema do arquivo na Fase 3 e só
descobrir na Fase 2 que ele precisa de mais uma coluna significa mexer no esquema **depois** de
o workstream `dashboard` já estar apontado para ele. Esquema de arquivo com consumidor externo
se decide **uma vez**, com a conta inteira na mão.

**REG-02 é uma regra de taxa vestida de persistência.** "A primeira amostra depois de subir é
âncora, não delta" não é uma propriedade do disco: é o que a conta faz com uma lacuna. Não dá
para verificar sem a conta, e verificá-la duas vezes em duas fases é verificá-la mal.

**E a granularidade do projeto é `coarse`.** Uma fase de três requisitos cujo conteúdo maior é
"reusar o dialeto que `mercado_registro.py` já tem" é exatamente a fase fina que a calibração
coarse manda dobrar na vizinha.

**O que NÃO foi fundido, e por quê.** A leitura (Fase 1) fica sozinha porque é a única fase que
pode falhar por motivo de *pixel* — se o EXP% não sair com as quatro casas, nada depois existe,
e descobrir isso no meio de uma fase que também tem console é descobrir tarde. E a Fase 3 fica
sozinha porque ela é a única que precisa do jogo aberto e do olho do usuário.

---

## Phases

- [ ] **Phase 1: A leitura da barra — pixel vira número, ou recusa** - nível, EXP% com quatro casas e adena total saem da tela, ou saem como recusa nomeada; e todo retângulo e limiar mora no `calibration.json`, posto lá por um calibrador
- [ ] **Phase 2: A conta e o registro — de duas amostras para uma taxa, e uma linha no disco** - XP/h, adena/h e tempo até o nível, sem que subir de nível vire prejuízo nem gastar adena vire renda negativa; cada amostra aceita vira linha num arquivo que o `dashboard` consegue abrir
- [ ] **Phase 3: O modo `--renda` — o painel ao vivo e a cegueira declarada** - lançador próprio, processo separado, painel `rich.Live` com as taxas e o ETA, e "pausado"/"parado" ditos em voz alta em vez de renda zero afirmada

## Phase Details

### Phase 1: A leitura da barra — pixel vira número, ou recusa

**Goal**: com o jogo aberto, o scanner devolve **nível**, **EXP% com as quatro casas decimais**
e **adena total** como números — ou nomeia qual campo recusou e por quê. Nenhum retângulo,
nenhum `vmin`, nenhum limiar aparece no fonte: todos moram no `calibration.json`, colocados lá
por um calibrador da mesma família dos dois que já existem.

**Depends on**: Nada. É a primeira fase do workstream, e tudo de que ela precisa
(`ocr.py`, `mercado_leitura.py`, `calibracao.py`, `captura_janela.py`) já está no repositório e
verificado em campo.

**Requirements**: LEIT-01, LEIT-02, LEIT-03, LEIT-04, LEIT-05, LEIT-06

**O que o spike já entregou, e que esta fase NÃO precisa redescobrir** (`.planning/spikes/renda-barra-inferior.md`, medido na tela do usuário em 2026-09-01):

| região | recorte físico | leitura medida |
|---|---|---|
| barra esquerda | `0,1368 500x26` | `EXP 68.6738% 582% : 83` (escala 2x) |
| barra direita | `1230,1368 470x26` | `Special 58,40 13,091 10,679,769` (escala 1x) |
| nível | `246,736 30x20` | `''` no cru — precisa de máscara de branco |

E a curva do `vmin` da máscara `inRange(HSV, (0,0,vmin), (179,70,255))` para o nível:
`170 → ''`, `190 → '6b'`, `210 → '66'` OK. **Estes números são ponto de partida do calibrador,
não constante do produto.** Mover a janela não pode custar um commit — é a regra que o
`CLAUDE.md` deste projeto escreve como "nada de constante mágica no fonte".

**Success Criteria** (o que tem que ser VERDADE):

1. Com o jogo aberto, um comando de leitura única imprime os três campos batendo com o que está
   na tela: o nível `66`, o EXP `68,5632%` com as **quatro** casas e a adena `10.673.628`.
   Conferível olhando para o monitor e para o terminal ao mesmo tempo. — LEIT-01, LEIT-02, LEIT-03
2. Um EXP que saia sem as quatro decimais — `68,56%`, `685632`, `68,5632` sem o sinal de
   porcentagem — é **recusado com o motivo escrito**, nunca arredondado nem completado. As
   decimais são o que torna a taxa mensurável em minutos em vez de horas; perdê-las em silêncio
   é entregar um medidor que só funciona depois de uma hora de farm. — LEIT-02, LEIT-04
3. Cada modo de leitura duvidosa vira uma **recusa nomeada e distinguível**: campo vazio, EXP
   andando para trás sem mudança de nível, adena saltando ordem de grandeza. Nenhum deles vira
   número. Este é o critério mais importante da fase inteira, porque **depois de gravado, um
   número errado é indistinguível de um número certo** e envenena toda taxa dali para a frente. — LEIT-04
4. Mover a janela do jogo quebra a leitura; rodar o calibrador de novo a conserta — **sem editar
   uma linha de código**. Uma busca no fonte por qualquer um dos números do spike (`1368`,
   `246`, `210`) não acha nenhum deles fora de teste. — LEIT-05
5. `calibrar-renda.bat` abre em dois cliques, na mesma família do `calibrar-mercado.bat` e do
   `calibrar.bat`, e grava no mesmo `calibration.json` **sem apagar nada que já estava lá** —
   nem a calibração da party, nem a do mercado, nem a do tiat. — LEIT-05, LEIT-06

**Riscos e decisões que o planejamento tem que encarar**:

- **O `calibration.json` é compartilhado por quatro features e um calibrador já apagou o
  trabalho de outro.** Está medido e escrito no roadmap do `mercado`: `calibrar_mercado.py:2721`
  faz `cal.mercado_grade = grade`, e por isso calibrar a aba Adena **apagaria** a grade de
  negociação. O calibrador desta fase entra num arquivo que a party, o mercado e o tiat já
  dividem. Escrever campo novo é barato; escrever campo novo **sem carregar e reemitir os
  outros** é o defeito que já aconteceu nesta árvore. O plano tem que provar a não-destruição,
  não prometê-la.
- **Qual leitor para qual campo é decisão de medição, não deste roadmap.** O OCR do Windows já
  devolveu a adena inteira do recorte cru; devolveu o nível como `''`. O
  `mercado_leitura.ler_glifos` é o leitor de dígitos que este projeto construiu **para esta
  fonte**, com `moldes_da_tinta` e recusa por pontuação. A hipótese de trabalho é OCR para a
  barra e glifos para o nível, mas quem decide é o que o campo mede. O que **não** é negociável:
  seja qual for o leitor, `numero_valido` e a recusa nomeada valem para os três campos.
- **As quatro casas decimais são a especificação mais apertada da milestone.** `68,5632%` tem
  seis dígitos significativos num texto de ~26 pixels de altura. Um erro de um dígito na quarta
  casa é `0,0001` de EXP — invisível ao olho, e uma taxa horária inteira de diferença numa
  amostragem de um minuto. Cruzamento de leituras (duas escalas, dois leitores, ou a
  monotonicidade entre amostras consecutivas) é a rede que `manutencao.py` já usa para o banner
  e que aqui provavelmente se paga.
- **A vírgula e o ponto.** O jogo escreve `68.5632%` no EXP e `10.673.628` na adena — o mesmo
  caractere separando decimal num campo e milhar no outro, e o OCR devolveu
  `10,679,769` com vírgula. `centesimos_de_moeda` e `inteiro_de_quantidade` já
  atravessaram exatamente esta dor no mercado. Reusar a normalização, não escrever a segunda.
- **A janela é per-personagem, e o usuário roda duas.** `--janela` não é conforto: EXP e adena
  são do personagem, e sem mira o scanner lê a instância errada. `vigiar-mercado.bat` já resolve
  o título pela chave `[jogo] personagem` do `config.toml`; esta fase herda esse caminho inteiro.

**Plans**: TBD

---

### Phase 2: A conta e o registro — de duas amostras para uma taxa, e uma linha no disco

**Goal**: uma sequência de amostras aceitas responde **XP/min, XP/h, adena/min, adena/h e
quanto tempo falta para o próximo nível** — sem que subir de nível registre o pior número da
noite, e sem que gastar adena vire prejuízo. E cada amostra aceita vira **uma linha num arquivo
append-only em `.renda/`**, escrito no dialeto que o workstream `dashboard` já sabe atravessar.

**Depends on**: Phase 1 — a conta é sobre amostras, e amostra é o que a Fase 1 produz. Enquanto
a leitura não recusar direito, gravar é gravar veneno.

**Requirements**: REND-01, REND-02, REND-03, REND-04, REND-05, REND-06, REG-01, REG-02, REG-03,
REG-04

**As duas armadilhas, e por que cada uma ganhou critério próprio**: as duas foram levantadas
pelo spike, e as duas têm o mesmo formato — **um delta negativo que não é renda negativa**.
Elas não são casos de borda: subir de nível é a melhor coisa que acontece numa farmada, e gastar
adena é o que o usuário faz toda sessão. Uma milestone chamada "quanto rende esta hora" que
registra `-68,5%` quando o usuário sobe de nível não erra num canto — erra no meio.

**Success Criteria** (o que tem que ser VERDADE):

1. Uma sequência de amostras reais responde XP/min, XP/h, adena/min, adena/h e o tempo até o
   nível, e **todo número sai acompanhado de quantas amostras o produziram e de que janela de
   tempo ele cobre**. Quarenta segundos de sessão se anunciam como ruído, não se disfarçam de
   taxa horária — mesma disciplina de `n` e recência que o `--mercado` já aplica a todo número
   que vai à tela. — REND-01, REND-02, REND-05, REND-06
2. Uma sequência que atravessa um level up (EXP `68,9%` → `0,4%`, nível `66` → `67`) registra
   **ganho positivo**, calculado como `(100 - anterior) + atual` e um nível a mais. Nunca
   `-68,5`. — REND-03
3. Uma queda no contador de adena sai como **gasto registrado à parte**, fora da taxa de ganho;
   o ganho bruto continua sendo a soma dos deltas positivos, e o arquivo carrega o suficiente
   para que farm e venda no mercado não fiquem somados no mesmo balde. — REND-04
4. Matar o processo e subir de novo **não inventa nem apaga renda**: a primeira amostra depois
   do reinício é âncora e não delta, o arquivo de antes continua inteiro e legível, e a sessão
   nova apenda no fim em vez de reescrever. — REG-01, REG-02
5. O arquivo diz **de qual personagem** é cada linha, e as duas instâncias que o usuário roda
   lado a lado nunca somam a adena de uma com o EXP da outra. — REG-04
6. Um leitor apontado para `.renda/` atravessa o arquivo com o **mesmo dialeto e a mesma
   disciplina de falha** do `.mercado/observacoes.csv` — `;`, `csv` da stdlib, cabeçalho como
   contrato que desliga alto, e recorte na última linha completa durante a escrita. — REG-03

**Riscos e decisões que o planejamento tem que encarar**:

- **"Sem um segundo parser" precisa de correção honesta, e ela vale ser escrita.** REG-03 pede
  "o mesmo contrato que o `dashboard` já sabe ler". Medido: `dashboard_dados.observacoes_ao_vivo`
  delega para `mercado_registro.observacoes_do_arquivo`, que é **amarrada a `COLUNAS =
  (chave_da_serie, nome_exibido, primeira_vez, total_em_centesimos, quantidade,
  residuo_do_cruzamento)`**. Uma amostra de renda não é uma oferta de mercado, e nenhuma
  torção de nome de coluna faz uma virar a outra. **O que dá para reusar de verdade — e é
  bastante — é o dialeto e a disciplina**: `ArquivoRecortado`, `conferir_o_cabecalho`,
  `conferir_o_terminador`, o separador, o append por linha com flush. Esta fase entrega um
  arquivo que o `dashboard` abre acrescentando uma **lista de colunas**, não um parser. A
  promessa que sobrevive é a que importa: nenhuma decisão de formato nova, nenhuma armadilha
  nova, nenhuma medição refeita. Isto é uma refutação de um requisito e vai escrita no fonte.
- **Esta fase NÃO toca em nenhum arquivo do workstream `dashboard`.** Ele está sendo executado
  agora, em paralelo, por outro agente, e a Fase 1 dele já está em execução com 8 planos. O
  contrato entre os dois workstreams é **um arquivo em disco**, exatamente como o contrato entre
  `dashboard` e `mercado`. Nada de `dashboard.py`, `dashboard_dados.py` ou `dashboard_cambio.py`
  é editado aqui. Se o `dashboard` quiser a renda, ele lê `.renda/` quando quiser, no tempo dele.
- **A distinção farm × venda não é dedutível só do contador de adena, e o plano tem que
  encarar isso.** Uma venda no World Exchange e uma noite de farm produzem o mesmo tipo de
  evento: adena subiu. Distinguir exige informação de fora do contador — a forma do salto (venda
  é um caroço, farm é gotejamento), o painel do mercado estar aberto naquele instante (o
  `--mercado` sabe), ou um marcador explícito. **A escolha é do plano; o que não é negociável é
  que ela seja declarada no arquivo** e não inferida pelo consumidor a partir de um limiar
  mágico. D-02 vale inteiro: um número exibido tem de ter existido.
- **`.renda/` nunca é podado.** Mesma razão do `.loot/` e o oposto do `.agenda/`: "quanto eu
  rendia mês passado" é pergunta sobre meses. `loot.py` já escreve o argumento por extenso.
- **O tempo entra por parâmetro, em tudo.** Nenhum `datetime.now()` neste código. Não é estilo:
  o PC do usuário é dual boot e o Windows volta do Linux ~3h adiantado, e uma taxa por hora
  calculada com um relógio que pula é lixo silencioso. `relogio.py` já resolveu isso para a
  agenda e é o que permite testar uma noite inteira de farm em milissegundos.
- **Janela móvel: qual janela, e o que acontece na lacuna.** REND-06 pede taxa de janela móvel
  que se anuncia. Falta decidir o tamanho e, principalmente, o que a janela faz quando o scanner
  ficou cego por 20 minutos no meio dela — a lacuna divide o ganho por um tempo que não foi
  farmado. A resposta provável é excluir o tempo cego do denominador, e ela precisa estar
  escrita, porque o oposto (dividir pelo relógio de parede) é o padrão silencioso.

**Plans**: TBD

---

### Phase 3: O modo `--renda` — o painel ao vivo e a cegueira declarada

**Goal**: um lançador próprio sobe um **processo separado** que mostra, ao vivo, nível, EXP%,
adena, as quatro taxas, o tempo até o nível e há quanto tempo a sessão corre — e que diz
**"pausado"** ou **"parado"** em voz alta quando não está enxergando, em vez de afirmar renda
zero.

**Depends on**: Phase 2 — o painel exibe as taxas que a Fase 2 calcula, e a pausa protege o
arquivo que a Fase 2 escreve.

**Requirements**: CONS-01, CONS-02, CEGO-01, CEGO-02

**A fronteira com a Fase 2, que não se mexe**: o **portão de admissão** do registro é da Fase 2
— uma amostra ou é aceita ou é recusada com motivo. Esta fase não constrói um segundo portão:
ela apenas produz **motivos de recusa que só um laço ao vivo consegue produzir** (jogo fechado,
minimizado, tela de login, frames bit-idênticos) e os entrega ao portão que já existe. Duas
portas para o mesmo arquivo é como um arquivo passa a ter duas verdades.

**Success Criteria** (o que tem que ser VERDADE):

1. `vigiar-renda.bat` sobe em dois cliques e o painel mostra, atualizando ao vivo, nível, EXP%,
   adena, XP/min, XP/h, adena/min, adena/h, o tempo até o próximo nível e há quanto tempo a
   sessão corre — no mesmo `rich.Live` das telas que já existem, com `n` e recência colados nos
   números como o `--mercado` já faz. — CONS-01
2. Derrubar o `--renda` **não derruba** o `vigiar-party.bat` nem o `vigiar-mercado.bat`, e
   derrubar qualquer um deles não derruba o `--renda`. Quatro invocações, quatro janelas,
   nenhuma dependendo da outra para ficar de pé. — CONS-02
3. Fechar o jogo, minimizar a janela ou cair na tela de login faz o painel dizer **"pausado"
   com o motivo na tela**, e o arquivo em `.renda/` **não ganha nenhuma linha** durante a pausa.
   Nada de amostra de tela preta entrando como renda zero. — CEGO-01
4. Valores bit-idênticos por N amostras fazem o painel dizer **"parado"**, e "parado" e "renda
   zero" ficam visualmente distinguíveis na tela. Renda zero é o usuário sentado sem matar nada;
   parado é o scanner não estar vendo. Às 4 da manhã a diferença é a única coisa que importa. — CEGO-02

**Riscos e decisões que o planejamento tem que encarar**:

- **A cegueira é reuso, e a tentação é reescrevê-la.** `frames.SaudeDoFrame` e
  `FRAMES_IDENTICOS_PARA_CONGELADO = 30` já classificam frame escuro e congelado;
  `cliente.EstadoDoCliente.TELA_DE_LOGIN` e `esta_na_tela_de_login` já reconhecem a tela de
  login pelo título da janela; `captura_janela.py` já captura por janela e funciona com o jogo
  **coberto**. Foram **quatro rodadas de correção** no v1 para chegar até aqui. Uma segunda
  implementação de cegueira neste repositório é um passivo, não uma feature.
- **CEGO-02 tem um caso que o congelamento de frame não pega, e é o mais provável.** O jogo pode
  estar renderizando normalmente — o frame muda, nuvem passa, personagem respira — e mesmo assim
  o EXP e a adena não se moverem, porque o usuário está de fato parado. `SaudeDoFrame` diria
  "saudável". A staleness que CEGO-02 pede é sobre os **valores lidos**, não sobre os pixels do
  frame, e é uma segunda camada acima da que já existe. E note que ela colide com o caso
  legítimo: um usuário parado tem renda zero de verdade. **Distinguir "não vejo" de "vejo e não
  mudou" é o problema real desta fase** — o frame congelado e o valor congelado são sinais
  diferentes e não podem colapsar no mesmo aviso.
- **Minimizado continua impossível.** O `PROJECT.md` fecha esse assunto no v1: a captura por
  janela funciona com o jogo coberto, mas janela minimizada para de renderizar e não há API que
  contorne. Esta fase **declara** a pausa; ela não promete ler uma janela minimizada.
- **O painel é console, não navegador.** Este workstream não desenha tela de navegador — está
  escrito no `REQUIREMENTS.md` e é a divisão com o workstream `dashboard`. As decisões de tela
  aqui são as do `mercado_console.py`: largura, o que corta primeiro quando não cabe, como um
  número velho se marca. Uma `/gsd-ui-phase` de contrato visual seria cerimônia sobre um
  `rich.Table` de dez linhas — a menos que o executor discorde por um motivo que escreva.
- **A mira é obrigatória, como no `--mercado`.** `--renda` exige `--janela` pelo mesmo motivo
  que `--mercado` exige: duas instâncias na mesma máquina, e renda é do personagem. O
  `vigiar-mercado.bat` já resolve o título pela chave `[jogo] personagem`; copiar o caminho, não
  reinventar a resolução.

**Plans**: TBD
**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. A leitura da barra | 0/? | Not started | - |
| 2. A conta e o registro | 0/? | Not started | - |
| 3. O modo `--renda` | 0/? | Not started | - |

## Coverage

| Requisito | Fase |
|-----------|------|
| LEIT-01 | Phase 1 |
| LEIT-02 | Phase 1 |
| LEIT-03 | Phase 1 |
| LEIT-04 | Phase 1 |
| LEIT-05 | Phase 1 |
| LEIT-06 | Phase 1 |
| REND-01 | Phase 2 |
| REND-02 | Phase 2 |
| REND-03 | Phase 2 |
| REND-04 | Phase 2 |
| REND-05 | Phase 2 |
| REND-06 | Phase 2 |
| REG-01 | Phase 2 |
| REG-02 | Phase 2 |
| REG-03 | Phase 2 |
| REG-04 | Phase 2 |
| CONS-01 | Phase 3 |
| CONS-02 | Phase 3 |
| CEGO-01 | Phase 3 |
| CEGO-02 | Phase 3 |

**18 de 18 requisitos mapeados. Nenhum órfão, nenhum em duas fases.**

REG-04 **não existia** no `REQUIREMENTS.md` original: foi criado por este roadmap, e a razão
está na seção seguinte.

## O requisito que este roadmap acrescentou — REG-04

**O buraco:** o `PROJECT.md` diz que o usuário roda **duas instâncias** do jogo lado a lado
(Yazalaque e Faerlina) — é literalmente a razão de AGEN-07 existir. EXP e adena são **do
personagem**. Um `.renda/` sem a coluna do personagem soma a adena de um com o EXP do outro e
produz uma taxa que não descreve ninguém.

**Por que ele é obrigatório e não uma melhoria:** ele cai exatamente no modo de falha que
LEIT-04 existe para impedir — *"um número errado é indistinguível de um número certo depois de
gravado, e envenena toda taxa calculada dali para a frente"*. Uma renda misturada entre dois
personagens não parece errada em lugar nenhum. Ela só parece baixa.

**Por que ele é barato:** o caminho inteiro já existe. `vigiar-mercado.bat` resolve o título da
janela pela chave `[jogo] personagem` do `config.toml`, `cliente.nome_do_personagem` extrai o
nome do título, e `--janela` já é exigido pelo `--mercado` pelo mesmo motivo. REG-04 é uma
coluna e um parâmetro que já está sendo passado.

**Fica registrado para revisão de manhã**, junto das quatro premissas que o `REQUIREMENTS.md` já
lista na seção "Premissas assumidas (usuário dormindo)". Se o usuário quiser um arquivo por
personagem em vez de uma coluna, é troca de formato dentro da Fase 2 e não muda o roadmap.

## Restrições herdadas — valem no workstream inteiro

- **Nenhum input no jogo, nunca.** Restrição dura do projeto e do `CLAUDE.md`: nenhuma
  biblioteca de síntese de input entra na árvore. Este workstream só lê pixel.
- **Nada de leitura de memória nem de pacote.** Já fora de escopo no `PROJECT.md`, repetido aqui
  para o escopo não voltar por baixo.
- **Nada de constante mágica.** Todo retângulo e todo limiar no `calibration.json`, e o
  calibrador é quem escreve.
- **Falha fechada.** Dado ilegível ou incompleto é **descartado com motivo**, nunca interpretado,
  nunca arredondado, nunca completado.
- **Um número que caiu precisa dizer que caiu.** Refutação de requisito vai escrita no fonte, com
  a medição que a derrubou — é o que este roadmap já faz com a promessa de "sem um segundo
  parser" do REG-03.
- **O tempo entra por parâmetro.** Nenhum `datetime.now()` em módulo deste workstream.
- **Nunca acoplar ao detector de morte** (`rastreador.py`, `visao.py` no caminho da party). O
  `--renda` lê da mesma tela, num processo separado, e não pode fazer a vigilância da party cair.
- **Nenhum arquivo do workstream `dashboard` é editado aqui.** Ele roda em paralelo, com outro
  agente, e a Fase 1 dele já está em execução. O contrato entre os dois é um arquivo em disco.
- **Doutrina de zero-install.** Dependência nova é decisão de pesquisa com justificativa. Esta
  milestone, do jeito que está desenhada, **não pede nenhuma**: `mss`, `cv2`, `numpy`, `winrt` e
  `rich` já estão na árvore.

## Nota de nomenclatura

Os slugs de diretório de fase levam o prefixo `renda-`
(ex.: `phases/01-renda-a-leitura-da-barra/`), pelo mesmo motivo do `mercado`, do `tiat` e do
`dashboard`: escopos de commit não podem colidir entre workstreams que avançam ao mesmo tempo.

---
*Roadmap criado: 2026-09-02, a partir do `REQUIREMENTS.md` de v1-renda e do spike
`renda-barra-inferior.md`*
