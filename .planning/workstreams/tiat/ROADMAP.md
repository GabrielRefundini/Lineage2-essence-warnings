# Roadmap: Aviso de nascimento de boss raro (workstream `tiat`)

**Workstream:** tiat (`.planning/workstreams/tiat/`)
**Milestone:** v1-tiat — reconhecimento preciso e previsão da janela de respawn
**Created:** 2026-08-30
**Granularity:** coarse (2 fases)
**Ponto de partida:** `l2scanner/tiat.py` já existe, está ligado em `sessao._processar_tiat`, despacha com `Categoria.SEMPRE` e tem 7 testes. Nada disso se reconstrói.

## Overview

A ordem das duas fases não é preferência: é a única ordem em que a segunda fase pode estar correta.

Hoje o gatilho é `re.compile(r"t[i1l][a4@][t7]")` procurando em qualquer lugar do recorte do chat. Isso basta enquanto o produto é "avisa agora", porque um falso positivo custa uma mensagem inútil no grupo e a party olha a tela e descobre em dez segundos. No momento em que esse mesmo sinal vira a **âncora de uma contagem de 6 horas**, o preço do falso positivo muda de categoria: alguém digitando "tiat ja nasceu?" no chat geral passa a agendar, para daqui a seis horas, um aviso de "a janela abriu" para um nascimento que nunca existiu — e a party se desloca. Uma previsão ancorada em ruído é estritamente pior do que não ter previsão nenhuma, porque a party não tem como distinguir uma da outra. Por isso a precisão (RECO) é **pré-condição** da janela (JANE), e não uma melhoria paralela.

Há um segundo motivo, mais mecânico e igualmente decisivo: a janela é **por boss**. `Tiat North` e `Tiat South` são dois mobs com dois relógios independentes, e é a identidade produzida por RECO-02/RECO-03 que vira **nome de arquivo durável** em disco. Construir JANE antes de RECO significaria ancorar num blob único chamado "tiat" e trocar a chave depois — e trocar a chave de um marcador durável é exatamente a coisa que a `Aviso.chave` do `agenda.py` existe para impedir: marcador antigo deixa de casar, e o aviso já enviado sai de novo.

VIGI mora **junto** de RECO, não depois. A frase do anúncio é por boss e a regra de respawn é por boss — são campos do mesmo bloco `[[boss]]`, lidos pela mesma função de validação. Separá-los criaria uma fase que embute `Tiat North`/`Tiat South` no código e uma fase que desembute: churn puro, sem nada verificável no meio.

Sobra a operação. OPER-01 (a calibração continua genérica) é consequência direta da Fase 1 e mora nela. OPER-02 (o console diz quem é vigiado **e** qual a próxima janela) só existe inteiro depois da Fase 2, e por isso é dela — a Fase 1 entrega a metade "quem é vigiado" por via de VIGI-04, que já exige a linha de arranque. OPER-03 (tudo demonstrável sem jogo e sem rede) é a disciplina que a Fase 1 já herda de graça e que a Fase 2 **estende**, porque nasce ali um módulo novo com tempo — e é por isso que ele é da Fase 2.

Duas fases, e não três. Uma terceira fase de "operação e console" teria um requisito e meio, objetivo de qualidade interna e critérios que se leem como tarefas — exatamente o formato de fase que este roadmap deve dobrar num vizinho em vez de criar.

## Onde o histórico de spawn mora em disco: `.agenda/`

Decidido aqui, e não deixado para o planejador, porque a escolha errada é silenciosa e cara.

**A âncora mora em `.agenda/`**, como um marcador vazio por nascimento, com um prefixo novo (candidato: `PREFIXO_NASCIMENTO = "nascimento_"`) e o nome na forma que a poda já sabe ler: `nascimento_<YYYY-MM-DD>_<boss-slug>-<HHMM>`.

Cinco razões, em ordem de peso:

1. **A âncora é efêmera por construção.** Sua vida útil termina no próximo nascimento — no máximo `respawn_horas_max` (8h para o Tiat) mais a tolerância. `.agenda/` poda em 3 dias (`DIAS_DE_MARCADOR = 3`), nove vezes a vida útil máxima da âncora: nada é apagado cedo, e nada fica para sempre.

2. **Uma âncora velha não é neutra, é perigosa** — e é isto que descarta `.loot/`, que nunca é podado. Uma âncora de duas semanas atrás teria sobrevivido a dezenas de ciclos que o scanner não viu, e o cálculo continuaria produzindo janelas: janelas erradas com cara de certas, entregues no grupo. É a família de defeito que este projeto já pagou caro. A poda de 3 dias é a garantia de que uma âncora abandonada **morre em vez de mentir** — e o console dizendo "ainda não vi nascimento deste boss" é a resposta correta, não uma degradação.

3. **A maquinaria já está lá e é exatamente a certa.** `O_CREAT|O_EXCL` (as duas instâncias do usuário), `marcar()` como *a* decisão de despacho e nunca uma checagem anterior, chave estruturada em vez do texto da mensagem, e `podar()` lendo `YYYY-MM-DD` logo depois do prefixo. Os avisos de janela (JANE-02, JANE-06) são, forma por forma, os mesmos marcadores dos avisos de agenda. Reimplementar isso em `.loot/` seria copiar quatro invariantes já testadas para um lugar que não as tem.

4. **`.loot/` é para estatística permanente** — quem pegou o quê: dado que só cresce e nunca invalida. Uma âncora é um **ponteiro vivo**, que o próximo nascimento substitui. Ciclos de vida opostos pedem namespaces diferentes.

5. **Consequência obrigatória, não opcional:** o prefixo novo tem que entrar em `_PREFIXOS_CONHECIDOS`, senão nasce imortal e cai direto na razão 2. **Atenção a um buraco real:** o guarda que deriva a tupla por introspecção (`tests/test_agenda.py::test_a_lista_de_prefixos_conhecidos_nao_deixa_ninguem_de_fora`) varre `vars(agenda)` — um `PREFIXO_*` declarado num módulo NOVO passa por ele sem levantar nada. Então ou o prefixo é declarado **dentro de `agenda.py`** (e o guarda existente cobre de graça), ou o guarda é estendido ao módulo novo na mesma fase. Não há terceira opção aceitável.

**Nota para o v2 (APRE-01):** aprender o tempo típico entre nascimento e morte pede um histórico **permanente e aditivo** — isso sim é estatística, e portanto do feitio de `.loot/`. É outro artefato, com outro ciclo de vida, em outra fase. Não é a âncora, e não deve ser construído agora só porque um dia vai ser preciso.

## A direção do erro é conhecida, e é sempre a mesma

Isto não é um detalhe de redação; é a conta que decide o texto de JANE-03, e um planejador que não a fizer entrega uma afirmação falsa no grupo.

O boss nasceu em `T` e a party o matou em `T+k`. O próximo nascimento cai em `[T+k+min, T+k+max]`. Nossa âncora é `T`, não `T+k`. Logo os dois avisos saem **`k` cedo demais — nunca tarde**, para qualquer `k ≥ 0`.

Consequências que o texto tem que respeitar:

- O aviso de **abertura** (`T+min`) é um **piso honesto**: antes disso ele comprovadamente não nasce. Essa é uma afirmação verdadeira e útil.
- O aviso de **fechamento** (`T+max`) **não pode dizer que a janela fechou**. Com o boss tendo ficado `k` vivo, em `T+max` a janela real pode nem ter aberto ainda (ela abre em `T+k+min`). O texto honesto é que o limite otimista passou e que, daqui para a frente, o nascimento pode acontecer a qualquer momento.
- Escrever "perdemos a janela" é a saída que um planejador desatento produz, e é falsa.
- O erro **não acumula entre ciclos**: cada nascimento detectado reancora do zero. Só o ciclo corrente carrega `k`.

## Phases

**Phase Numbering:**

- Integer phases (1, 2): trabalho planejado do milestone
- Decimal phases (1.1, 1.2): inserções urgentes (marcadas com INSERTED)

- [x] **Phase 1: Reconhecimento preciso e lista de bosses no config** - O alerta só sai quando o SERVIDOR anunciou um nascimento, diz QUAL boss nasceu, e a lista de vigiados é editável sem tocar em código
- [x] **Phase 2: Janela de respawn** - Quem está offline recebe que a janela abriu e que o limite passou, ancorado no último nascimento realmente visto, com a mensagem honesta sobre a origem do número

**Nota de nomenclatura:** os slugs de diretório usam o prefixo `tiat-` (ex.: `phases/01-tiat-reconhecimento-e-lista/`), pelo mesmo motivo do workstream `mercado`: escopos de commit não podem colidir com as fases do workstream `default`.

## Phase Details

### Phase 1: Reconhecimento preciso e lista de bosses no config

**Goal**: O alerta de boss raro só sai quando o servidor anunciou um nascimento, nomeia qual dos bosses nasceu, e quem é vigiado passa a ser uma linha do `config.toml` em vez de uma constante no código.

**Depends on**: Nothing (primeira fase; parte de `l2scanner/tiat.py`, que já funciona)

**Requirements**: RECO-01, RECO-02, RECO-03, RECO-04, RECO-05, VIGI-01, VIGI-02, VIGI-03, VIGI-04, OPER-01

**Success Criteria** (o que tem que ser VERDADE):

  1. Com o texto `Fulano: tiat ja nasceu?` entrando pelo OCR do chat, **nenhum** alerta sai. Com `Tiat North [Lv. 80] has spawned!` no mesmo lugar, sai um alerta, e a mensagem que vai para o WhatsApp contém `Tiat North`. Trocando `North` por `South`, a mensagem contém `Tiat South`. — RECO-01, RECO-02
  2. Com o chat mudo e o nome do alvo lido como `Tiat South`, sai um alerta que identifica `Tiat South` pelo alvo. A detecção pelo alvo continua sendo um caminho próprio e não depende de o chat ter anunciado nada. — RECO-03
  3. A mesma frase degradada como o OCR degrada (`T1a7 Nor7h [Lv. 8O] has spawned!`) produz o mesmo alerta e o mesmo boss. A precisão contra chat digitado **não** custou o reconhecimento do anúncio real — os dois lados são afirmados no mesmo conjunto de testes, um por direção. — RECO-04, RECO-01
  4. Chat e alvo mostrando o **mesmo** boss no mesmo tick geram **uma** mensagem. Chat mostrando um boss e alvo mostrando outro geram **dois** alertas, um por boss — o rearme deixa de ser um estado único e passa a ser um estado por boss, e um `Tiat South` alvejado durante os minutos em que o anúncio de `Tiat North` ainda persiste no chat não é engolido. — RECO-05
  5. Acrescentar um bloco `[[boss]]` no `config.toml` com o nome como aparece no jogo e `respawn_horas_min` / `respawn_horas_max` faz o scanner passar a vigiar aquele mob **sem nenhuma alteração em arquivo `.py`** — verificável acrescentando um boss inventado e vendo o anúncio dele disparar. O Tiat entra com 6 e 8. — VIGI-01, VIGI-02
  6. Um `[[boss]]` sem `nome`, com `respawn_horas_max` menor que o `min`, com horas negativas ou com booleano no lugar de número **derruba o arranque** com uma mensagem que cita o boss e o campo, no mesmo formato de `_evento_de_dict` ("o boss 'X' tem ..."). Nunca sobe vigiando errado em silêncio. — VIGI-03
  7. Sem nenhum `[[boss]]` no `config.toml`, o scanner **sobe** e o console diz que a vigilância de boss está desligada e como ligá-la — a mesma degradação que `montar_vigia_do_tiat` já faz hoje quando falta calibração. Arquivo ausente também não é erro. — VIGI-04
  8. `calibrar-tiat.bat` continua marcando as duas regiões, e nem ele nem o texto que ele imprime nomeiam um mob específico: a região é do **chat** e do **alvo**, e a mesma calibração serve para qualquer boss da lista. — OPER-01

**Riscos e decisões que o planejamento tem que encarar:**

- **A frase do anúncio é asserção do usuário, não evidência do repositório.** `<Nome> [Lv. NN] has spawned!` nunca foi capturada por este projeto. O plano precisa de um caminho para confrontar a frase real — o `gravador` e o `--replay` já existem e são o instrumento. Casar a parte fixa (`has spawned`) com folga de OCR é obrigatório: um gate estrito demais na parte fixa troca o falso positivo de hoje por um falso **negativo** silencioso, que é pior, porque ninguém percebe.
- **O nome do módulo vira mentira.** `tiat.py` deixa de descrever o que o módulo faz assim que a lista é configurável. Renomear é decisão do plano; a restrição é que os 7 testes de `tests/test_tiat.py` atravessem intactos, porque eles são a régua do debounce que esta fase não pode quebrar.
- **O debounce por rearme é o ativo mais valioso do módulo** e é o que muda de forma nesta fase (de global para por boss). Os testes existentes de persistência e de "duas leituras limpas" precisam continuar valendo para cada boss individualmente.

**Plans**: 4 plans (2 waves)

- [x] 01-01-PLAN.md — Tracer em três camadas: do `[[boss]]` no arquivo ao aviso (T1), do aviso ao despacho em `sessao.py` (T2), e `montar_vigia_de_bosses` no arranque (T3) — wave 1
- [x] 01-02-PLAN.md — OPER-01: a calibração deixa de nomear um mob, com guarda AST que impede a volta (wave 2 — o guarda importa `ler_bosses`, que nasce em `01-01`)
- [x] 01-03-PLAN.md — A matriz que torna os 8 critérios verdadeiros, o vetor de metacaractere fechado, e `bosses.py` no portão AST de relógio (wave 2)
- [x] 01-04-PLAN.md — A ferramenta que confronta a frase real contra pixels, o README, e a medição do sentido negativo contra `recordings/` (wave 2)

**Nota de planejamento — o desvio declarado de D-12:** o CONTEXT trava que os 7 testes de `tests/test_tiat.py` migrem "INTACTOS, só o import muda". Isso é impossível de cumprir literalmente e a impossibilidade é o objetivo da fase: quatro deles alimentam o vigia com `Tiat`, `TIAT apareceu` e `T1A7 apareceu`, e RECO-01 existe para que esses textos PAREM de disparar; um quinto ponto é que `avaliar` passa a devolver LISTA para que o critério 4 possa emitir dois alertas num tick. O que a restrição protege — o debounce — é preservado por um contrato escrito em `01-01-PLAN.md`: os 7 nomes sobrevivem, a aritmética sobrevive byte a byte, e só três categorias de edição mecânica são permitidas. Nenhuma asserção é enfraquecida.

### Phase 2: Janela de respawn

**Goal**: A party sabe, pelo WhatsApp e com o jogo fechado, que a janela do boss abriu e que o limite otimista passou — a partir do último nascimento que o scanner realmente viu, e com a mensagem dizendo de onde o número veio.

**Depends on**: Phase 1 (a âncora é a identidade produzida por RECO-02/RECO-03; ancorar numa detecção imprecisa é pior do que não prever nada)

**Requirements**: JANE-01, JANE-02, JANE-03, JANE-04, JANE-05, JANE-06, OPER-02, OPER-03

**Success Criteria** (o que tem que ser VERDADE):

  1. Depois de um nascimento detectado, existe em `.agenda/` um marcador nomeado com o prefixo novo, a data e o boss. Derrubando e subindo o scanner, a contagem continua do **mesmo instante** — o horário não vive em memória, e não vive no `outbox.jsonl`. — JANE-01
  2. Rodando o modo de relógio (`--so-agenda`: sem jogo, sem calibração, sem captura, sem rede) com o instante adiantado para `min` horas depois da âncora, sai **uma** mensagem dizendo que a janela abriu; adiantado para `max` horas, sai **uma** mensagem dizendo que o limite passou. Nada sai antes de `min`, e um aviso vencido há muito tempo não ressuscita ao subir o scanner. — JANE-02, JANE-05
  3. As duas mensagens citam o **nascimento que ancorou a conta** (dia e hora) e dizem que a contagem parte do nascimento anterior, não da morte. A mensagem de `max` **não afirma** que a janela fechou nem que a party perdeu — ver a seção "A direção do erro" acima; um teste recusa o texto que afirmar fechamento. — JANE-03
  4. Um nascimento novo detectado antes de os avisos do ciclo anterior saírem faz com que eles **nunca saiam**, e a conta recomeça do novo instante. Isso é estrutural e não precisa de marcador de cancelamento: o cálculo só olha a âncora **mais recente** por boss, então as chaves do ciclo anterior deixam de vencer sozinhas. — JANE-04
  5. Duas instâncias sobre a mesma `.agenda/` (Yazalaque e Faerlina) produzem **exatamente um** envio por aviso; reiniciar qualquer uma delas dentro da janela de tolerância não repete nada. A decisão de despachar é a própria chamada de `marcar`, nunca uma checagem anterior. — JANE-06
  6. No arranque, o console lista os bosses vigiados e, para cada um que tem âncora, quando a janela abre e quando o limite passa; para os que não têm, diz que ainda não viu nascimento nenhum daquele boss — e não inventa uma previsão. O mesmo vale no `--so-agenda`, que é o modo de quem mais precisa da linha. — OPER-02
  7. O módulo novo com lógica de tempo entra na tupla `MODULOS` do portão AST de relógio (`tests/test_presenca.py`) e o portão continua verde: nenhum `datetime.now()` na árvore, o instante entra por parâmetro. O prefixo novo é coberto pelo guarda de `_PREFIXOS_CONHECIDOS` — declarado em `agenda.py`, ou com o guarda estendido ao módulo novo. Toda a fase é demonstrável com o jogo fechado e sem rede. — OPER-03
  8. Os avisos de janela atravessam o silêncio de TvT (`Categoria.SEMPRE`), como já fazem os avisos de nascimento — um boss nascendo durante o Prime é exatamente a informação que ninguém quer perder.

**Riscos e decisões que o planejamento tem que encarar:**

- **Dois lugares de fiação, não um.** JANE-05 exige que a janela funcione no `laco_da_agenda` (jogo fechado) e no `laco_principal`. O código já registra por escrito que um conserto aplicado de um lado só faz os dois divergirem; a extração para uma função compartilhada, no molde de `_fechar_listas_de_presenca`, é o padrão que a casa já usa.
- **A chave dos avisos de janela tem que ser estruturada e derivada da âncora**, na forma `<YYYY-MM-DD>_<boss-slug>-<HHMM>_<tipo>` — a mesma de `Aviso.chave`, para que a poda por data funcione sem regra nova e para que melhorar a redação da mensagem nunca reenvie um aviso.
- **Não estender `TipoDeAviso` sem medir o preço.** Acrescentar `ABRE`/`FECHA` ao enum do `agenda.py` faz `avisos_devidos` ganhar ramos para um conceito que não é uma ocorrência recorrente de calendário. Um tipo próprio no módulo novo, dividindo apenas a **convenção de chave**, é a leitura padrão — mas a decisão é do plano, com a justificativa escrita.
- **A tolerância de 5 minutos vale aqui também.** Um aviso de janela que venceu há três horas não pode sair quando o usuário sobe o scanner às 22h.

**Plans**: 2 plans (2 waves)

- [x] 02-01-PLAN.md — Tracer: do nascimento na tela a ancora em disco e ao aviso de abertura no WhatsApp; as quatro mensagens honestas; os tres portoes (relogio, ancora imortal, apelido colidindo) — wave 1
- [x] 02-02-PLAN.md — O segundo sitio de fiacao (`--so-agenda`, jogo fechado), OPER-02 nos dois lacos, e o portao AST contra a divergencia — wave 2

**Nota de planejamento — as decisoes de discricao, resolvidas:** o modulo novo e
`l2scanner/respawn.py` (`janela.py` foi recusado porque `--janela`, `JanelaDeSilencio` e
`janela_de_selecao.py` ja usam a palavra para a janela do Windows). `TipoDeAviso` **nao**
ganha `ABRE`/`FECHA`: o tipo e proprio do modulo novo, dividindo com `agenda.py` apenas a
convencao de chave — a justificativa de quatro razoes que o ROADMAP exigiu esta escrita em
`02-01-PLAN.md`. A funcao compartilhada pelos dois lacos e `respawn.anunciar_janelas`, no
molde literal de `presenca.fechar_e_narrar`. O ponto cego do guarda de prefixos e fechado
pelas DUAS opcoes que o ROADMAP admitia, e nao por uma: o prefixo e declarado dentro de
`agenda.py` **e** o guarda passa a varrer o modulo novo.

**Nota de planejamento — a forma duravel das duas chaves, ja decidida:** o usuario decidiu
em 2026-08-30 que a ORIGEM entra no NOME da ancora, e `02-CONTEXT.md` (linhas 53-71)
registra a forma `nascimento_<YYYY-MM-DD>_<boss-slug>-<HHMM>_<origem>` dizendo que ela
substitui a escrita anterior. A razao: D-16 exige que a mensagem cite qual sinal ancorou, e
essa informacao precisa sobreviver as 6 a 8 horas (e ao reinicio) entre o nascimento e o
aviso; guarda-la no conteudo quebraria a propriedade de marcador vazio que faz
`O_CREAT|O_EXCL` ser sozinho a decisao de despacho. A decisao e de mao unica e esta travada
em D-18 no `02-01-PLAN.md` — os dois planos sao autonomos e nao tem nenhum gate humano.

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Reconhecimento preciso e lista de bosses no config | 0/4 | Planned | - |
| 2. Janela de respawn | 0/2 | Planned | - |

## Coverage

| Requirement | Phase |
|-------------|-------|
| RECO-01 | Phase 1 |
| RECO-02 | Phase 1 |
| RECO-03 | Phase 1 |
| RECO-04 | Phase 1 |
| RECO-05 | Phase 1 |
| VIGI-01 | Phase 1 |
| VIGI-02 | Phase 1 |
| VIGI-03 | Phase 1 |
| VIGI-04 | Phase 1 |
| OPER-01 | Phase 1 |
| JANE-01 | Phase 2 |
| JANE-02 | Phase 2 |
| JANE-03 | Phase 2 |
| JANE-04 | Phase 2 |
| JANE-05 | Phase 2 |
| JANE-06 | Phase 2 |
| OPER-02 | Phase 2 |
| OPER-03 | Phase 2 |

**18 de 18 requisitos v1 mapeados. Nenhum órfão, nenhum duplicado.**

**Nota sobre OPER-02:** o requisito é da Fase 2 porque só ali ele existe inteiro (a metade "próxima janela prevista" depende da âncora). A metade "quais bosses estão sendo vigiados" é entregue na Fase 1 por VIGI-04, que já exige a linha de arranque — a Fase 2 completa a linha, não a cria.

**Nota sobre OPER-03:** a disciplina de "tempo por parâmetro, OCR por dado" já vale na Fase 1 de graça (`VigiaDoTiat` recebe `agora` e um `ler_texto` injetável, e os testes já usam um leitor de fila). O requisito é da Fase 2 porque é ali que ele deixa de ser herança e vira trabalho: nasce um módulo com lógica de tempo que precisa **entrar** no portão AST.

## Restrições que atravessam as duas fases

Não negociáveis, aprendidas em 10 fases entregues:

- **Leitura passiva de tela apenas.** Nunca ler memória, injetar ou enviar input ao jogo. Bibliotecas de síntese de input são estruturalmente banidas da árvore de dependências.
- **Nenhuma dependência nova.**
- **Tempo entra por parâmetro.** Módulo novo com lógica de tempo entra no portão AST.
- **Estado durável usa `O_CREAT|O_EXCL`.** O usuário roda duas instâncias sobre a mesma `.agenda/`; exatamente uma anuncia, e a chamada que marca **é** a decisão de despacho.
- **Chave durável é estruturada, nunca o texto da mensagem.**
- **Prefixo novo entra em `_PREFIXOS_CONHECIDOS`**, ou nasce imortal.
- **Tudo demonstrável com o jogo fechado e sem rede.** A suíte tem ~1650 testes e segura essa linha.

---
*Roadmap criado: 2026-08-30*
