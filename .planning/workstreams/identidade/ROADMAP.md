# Roadmap: O scanner aprende quem e a party sozinho

**Workstream:** identidade
**Created:** 2026-08-30
**Granularity:** coarse
**Core Value:** Trocar a composicao da party deixa de exigir uma rodada de calibracao.

## Overview

Este workstream nao mexe na LEITURA. O `identidade.py` ja reconhece bem — 1.000 contra
0.454 de margem, medido — e o OCR ja foi medido e reprovado (1 acerto em 4 contra a party
real). O que sobra e o CADASTRO: hoje ele so nasce quando o usuario digita
`calibrar.bat --nomes "A,B,C,D"`. As tres fases abaixo fazem o cadastro nascer sozinho.

**A ordem e por corretude, e a decisao foi entre duas.**

A alternativa tentadora era **aprender primeiro** — reconhecer o desconhecido, gravar, e
deixar o armazenamento "simples por enquanto". Ela perde por dois motivos, e o segundo e
pior que o primeiro.

O primeiro e o que todo mundo ve: "simples por enquanto" significa `calibration.json`, e
`calibrar.py:1281` lista `nomes` e `assinaturas` dentro de `CAMPOS_DA_PARTY` — a lista de
DONOS. O `fundir_com_a_calibracao_em_disco` (calibrar.py:1300) preserva por SUBTRACAO
tudo o que a party nao possui, e esses dois campos a party possui: eles sao reescritos
por desenho, em toda rodada. WINDOWS #13, confirmado em campo hoje, e o mesmo mecanismo
custando 13 moldes de glifo. Um tracer que morre na primeira `calibrar.bat` seria um
tracer que ensina o usuario a nao confiar na feature — numa feature cuja promessa inteira
e "voce para de precisar rodar calibrar.bat".

O segundo motivo e o que decide. `Assinatura.nome` e um `str`, e ele desce por
`Casamento.nome` -> `LeituraDeLinha.nome` -> `_chave_da_linha` (rastreador.py:206). Uma
assinatura aprendida e ainda anonima, gravada em `cal.assinaturas` com um nome de
mentira, NAO seria so nao-duravel: ela promoveria uma linha anonima a SUJEITO e mataria a
degradacao segura do `#linhaN` — a unica coisa que hoje impede o scanner de anunciar um
evento sem dono. O aprendizado-primeiro nao trocaria durabilidade por velocidade; trocaria
a melhor garantia que o projeto ja tem por uma demonstracao.

Entao: **durabilidade primeiro** — mas nao "um arquivo". A Fase 1 entrega o acervo E o
caminho de LEITURA dele: uma assinatura sem nome existe, e reconhecida, e CALA. Com isso a
Fase 2 so precisa acrescentar a decisao de ESCREVER (quando o recorte esta estavel, e se
ele ja nao esta no acervo), e a Fase 3 so precisa acrescentar o NOME. Cada fase e uma
capacidade verificavel sozinha, e nenhuma delas pode ser demonstrada com uma mentira.

**A ordem tambem e obrigada pelo pino do BATI-03.** A resposta do WhatsApp e casada com a
assinatura pinada no momento da pergunta, e um pino e uma referencia PARA DENTRO do
acervo. So existe pino duravel se o que ele aponta ja tiver identidade duravel. Construir
o batismo contra um armazenamento que muda de chave depois significaria reescrever o pino
— que e exatamente a peca onde um erro christenaria a pessoa errada em silencio.

**Decisoes tomadas aqui para as fases nao as relitigarem:**

1. **O acervo mora em pasta propria, no precedente do `.loot/` — nunca no
   `calibration.json`.** O `calibration.json` tem um escritor que monta objeto e grava o
   todo; a pasta da `O_CREAT|O_EXCL` de graca para as duas instancias (DURA-03), e nao ter
   chave de tempo no layout faz "nunca podado" (DURA-04) ser estrutural em vez de politica
   — a mesma razao pela qual `.loot/` nao e podado.
2. **O batismo e do nivel de DONO, e fica FORA de `COMANDOS_DE_MEMBRO`.** Um nome errado
   e corrupcao duravel e dificil de notar num acervo que nunca e podado — a mesma familia
   de `/corrigir` e `/pegou`, que ja sao de dono pela mesma razao (comandos.py:819-853).
   `/entrar` e `/sair` alcancam o `[[membro]]` porque sao baratos e so falam do proprio
   remetente; batizar nao e nenhum dos dois.
3. **Todo comando novo entra no `_AJUDA`.** O tripwire `set(_AJUDA) == set(Comando)` de
   `tests/test_comandos.py` quebra a suite se nao entrar, e isso e desejado, nao um
   obstaculo.

## Phases

- [x] **Phase 1: O acervo e o silencio dele** - Onde a assinatura aprendida mora, como ela sobrevive a `calibrar.bat` e por que ela nao fala
- [ ] **Phase 2: Aprender sozinho** - A linha que ninguem reconhece deixa de ser misterio permanente
- [ ] **Phase 3: Batismo pelo WhatsApp** - O usuario da nome, do celular, a assinatura que o scanner PERGUNTOU

## Phase Details

### Phase 1: O acervo e o silencio dele

**Goal**: O scanner passa a ter um acervo duravel de assinaturas visuais que vive FORA do
`calibration.json`, e lido em todo arranque, sobrevive a uma rodada de `calibrar.bat`, e
cujas entradas SEM NOME sao reconhecidas sem virar sujeito de alerta nenhum.

**Depends on**: Nada (primeira fase)

**Requirements**: DURA-01, DURA-02, DURA-03, DURA-04, APRE-03, OPER-01, OPER-02

**Success Criteria** (o que precisa ser VERDADE):
  1. Com entradas ja no acervo, uma rodada completa de `calibrar.bat --nomes "A,B,C,D"`
     termina e TODAS elas continuam no disco, intactas — enquanto `cal.assinaturas` e
     `cal.nomes` sao reescritos exatamente como sao hoje. (DURA-01, OPER-02)
  2. `--nomes` continua entregando o mesmo resultado de hoje: quem prefere digitar digita,
     e as assinaturas calibradas e as do acervo convivem no mesmo reconhecimento sem uma
     sombrear a outra. (OPER-02)
  3. Derrubar e subir o scanner de novo mostra o MESMO acervo, com a mesma contagem —
     nada regenerado, nada perdido. (DURA-02)
  4. Dois processos apontados para a mesma pasta gravando a mesma assinatura produzem
     UMA entrada; uma falha de disco no meio nao deixa entrada pela metade nem
     silenciosamente perdida. (DURA-03)
  5. Avancar o relogio em dias/semanas — pelo tempo por parametro, nunca pelo relogio da
     maquina — nao remove nem uma entrada, e o modulo novo entra na tupla `MODULOS` do
     portao AST de `tests/test_presenca.py` e o portao segue verde. (DURA-04)
  6. Uma entrada do acervo SEM nome que casa com uma linha da party window deixa aquela
     linha como `#linhaN`: nenhum evento sai em nome dela, e o rotulo exibido continua
     "Membro N". (APRE-03)
  7. O arranque imprime quantas assinaturas o scanner conhece e quantas estao sem nome.
     (OPER-01)

**Decisao aberta que o plano desta fase precisa fechar**: a CHAVE da entrada. Ela tem de
ser estavel entre reinicios, independente da POSICAO da linha (posicao e lugar, nao
pessoa) e independente do NOME (o nome chega depois e pode ser corrigido — BATI-05). E
essa chave que a Fase 3 vai pinar.

**FECHADA. O 01-CONTEXT.md decidiu a forma; o usuario travou o formato exato em
2026-08-31 (D-06).** A chave e o `sha256` COMPLETO — 64 digitos hex, sem truncar — do
CONTEUDO da assinatura, sobre o material `altura x largura : bits`. As dimensoes entram
porque `packbits` de uma mascara 2x8 e de uma 4x4 produzem os mesmos bytes. Nao se trunca
porque uma colisao aqui nao e um erro: e "Korzis morreu" quando morreu o Kaus. Um arquivo
por entrada em `.identidades/`, com o nome no irmao `nome_<hash>`. Decisao de mao unica e
ja atravessada: os planos a implementam, nao a perguntam.

**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — o acervo, o silencio de uma entrada sem nome, e o elo `assinaturas_configuradas` que hoje nao existe em producao (DURA-02, DURA-03, DURA-04, APRE-03, OPER-01)
- [x] 01-02-PLAN.md — a sobrevivencia a uma rodada real de `calibrar.bat` e a convivencia com `--nomes` (DURA-01, OPER-02)

### Phase 2: Aprender sozinho

**Goal**: Uma linha ocupada que nao casa com nenhuma assinatura conhecida deixa de ser um
misterio permanente: o scanner grava a assinatura dela sozinho, depois de estavel, sem
calibracao e sem intervencao — e sem gravar a mesma pessoa duas vezes.

**Depends on**: Phase 1

**Requirements**: APRE-01, APRE-02, APRE-04

**Success Criteria** (o que precisa ser VERDADE):
  1. Reproduzindo uma gravacao onde uma linha fica ocupada e nao reconhecida por N leituras
     seguidas com o recorte do nome estavel, o acervo ganha EXATAMENTE uma entrada, sem
     nome — e aquela linha continua sem anunciar nada. (APRE-01)
  2. A mesma gravacao com o recorte MUDANDO entre as leituras (o cenario andando por tras
     do texto transparente, a linha piscando) nao grava nada: instabilidade e recusada, e
     nao mediada. A estabilidade e julgada pelo CONTEUDO do recorte, nao pelo indice da
     linha — a party compacta, e um contador por indice atravessaria pessoas diferentes.
     (APRE-02)
  3. Uma linha que casa com uma entrada do acervo — com nome ou sem — nao gera entrada
     nova: o casamento contra o que ja esta gravado acontece ANTES de aprender. (APRE-04)
  4. A pessoa que sai da party e volta na mesma sessao, e tambem depois de um reinicio do
     scanner, continua com UMA entrada so no acervo. (APRE-04)
  5. Reproduzir a mesma gravacao duas vezes seguidas deixa o acervo com a mesma contagem
     da primeira vez. (APRE-01, APRE-04)

**As nove decisoes do 02-CONTEXT.md (D-01 a D-09) estao FECHADAS** e os planos as
implementam sem as reabrir. Duas delas mudam o tamanho da fase e merecem estar aqui:

- **D-02 e mais forte do que o APRE-04 pede.** "O casamento contra as ja gravadas vem
  antes" nao pode significar apenas RODAR antes: tem de VETAR. `identificar_linhas`
  devolve `Casamento(None, ...)` por dois motivos opostos — "nao conheco ninguem
  parecido" (aprende) e "conheco DOIS parecidos demais" (cala). Aprender no segundo faz
  a pessoa PARAR de ser reconhecida: medido na Fase 1, virando 8 celulas de uma mascara
  de 2000, a original casa 1.000 e a copia 0.921, margem 0.079, abaixo dos 0.12 de
  `MARGEM_MINIMA_SOBRE_O_SEGUNDO`.
- **D-07 e requisito de plano, e nao "nice to have".** A recusa por instabilidade
  registra a DISTANCIA MEDIDA em celulas. Sem ela, o desfecho de um `celulas_toleradas`
  errado e a feature simplesmente nao acontecer, em silencio. Com ela, o modo de falha
  da fase e AUTO-DIAGNOSTICO, e o D-07 substitui a ferramenta de spike que o CONTEXT
  adiou.

**Descoberta do planejamento que decide o tamanho do tracer:** gravar a assinatura NAO
BASTA para a linha continuar calada. `Rastreador.assinaturas_configuradas` e calculado
UMA VEZ no arranque, e numa instalacao sem assinatura nenhuma — que e onde esta fase
mais importa — ele nasce `False`. Nesse estado `_rotular` cai em `nome_de(indice)` e a
pessoa recem-aprendida como ANONIMA seria anunciada com o nome de OUTRA. O criterio 1
exige as duas metades, entao o elo tem de ser ligado no instante do primeiro
aprendizado.

**Plans:** 2 plans

Plans:
- [x] 02-01-PLAN.md — a linha desconhecida vira UMA entrada sem nome e continua calada; instabilidade recusada com a distancia medida; o teto derivado da medida da Fase 1 (APRE-01, APRE-02)
- [ ] 02-02-PLAN.md — aprender a mesma pessoa duas vezes nao acontece por nenhum dos quatro caminhos: ja reconhecida, falha por margem, sai e volta, reinicio e replay (APRE-04)

### Phase 3: Batismo pelo WhatsApp

**Goal**: O usuario da nome, do celular, a uma assinatura que o scanner aprendeu — e so
consegue dar nome aquela que o scanner PERGUNTOU, nunca a "a linha 3 de agora". A partir
do batismo os alertas daquela pessoa saem com o nome certo.

**Depends on**: Phase 2

**Requirements**: BATI-01, BATI-02, BATI-03, BATI-04, BATI-05, OPER-03

**Success Criteria** (o que precisa ser VERDADE):
  1. Quando uma assinatura e gravada sem nome, UMA pergunta sai para o WhatsApp citando a
     posicao onde ela foi vista — e ela nao se repete a cada tick enquanto ninguem
     responde. (BATI-01)
  2. O comando de resposta batiza a assinatura, e a partir da leitura seguinte os alertas
     daquela linha saem com o nome dado. O comando aparece no `/help` porque entrou no
     `_AJUDA`, e o tripwire `set(_AJUDA) == set(Comando)` segue verde. (BATI-02)
  3. Numa gravacao onde a party se REORGANIZA entre a pergunta e a resposta, o nome vai
     para a assinatura PINADA na pergunta — provado pela chave da entrada no acervo, e nao
     pelo indice da linha. Quem esta na linha citada no momento da resposta e outra pessoa,
     e continua sem nome. (BATI-03)
  4. Batizar uma segunda assinatura com um nome que ja pertence a outra e RECUSADO, com a
     resposta dizendo qual entrada ja tem aquele nome, e o acervo fica inalterado — nem a
     nova nem a antiga mudam. (BATI-04)
  5. Um batismo errado e corrigido por comando, sem rodar `calibrar.bat`, e o acervo
     termina com uma entrada por pessoa — a corrigida com o nome certo, e o nome liberado
     de volta. (BATI-05)
  6. O comando de batismo e o de correcao sao recusados para um telefone `[[membro]]` e
     aceitos para um telefone de dono. (BATI-04, BATI-05)
  7. Tudo acima roda na suite com o jogo fechado e sem rede: pergunta observada no
     despacho capturado, resposta entrando pela funcao pura de interpretacao de comandos,
     tempo por parametro. (OPER-03)

**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. O acervo e o silencio dele | 2/2 | Complete | 2026-08-31 |
| 2. Aprender sozinho | 1/2 | In progress | - |
| 3. Batismo pelo WhatsApp | 0/? | Not started | - |

## Coverage

| Requirement | Phase |
|-------------|-------|
| APRE-01 | Phase 2 |
| APRE-02 | Phase 2 |
| APRE-03 | Phase 1 |
| APRE-04 | Phase 2 |
| BATI-01 | Phase 3 |
| BATI-02 | Phase 3 |
| BATI-03 | Phase 3 |
| BATI-04 | Phase 3 |
| BATI-05 | Phase 3 |
| DURA-01 | Phase 1 |
| DURA-02 | Phase 1 |
| DURA-03 | Phase 1 |
| DURA-04 | Phase 1 |
| OPER-01 | Phase 1 |
| OPER-02 | Phase 1 |
| OPER-03 | Phase 3 |

**16 de 16 requisitos v1 mapeados. Nenhum orfao, nenhum duplicado.**

### Duas escolhas de mapeamento que merecem justificativa

**APRE-03 esta na Fase 1, e nao na Fase 2, apesar de o texto dizer "recem-aprendida".** O
que carrega peso no requisito nao e o instante do aprendizado — e o TIPO e o caminho de
leitura: uma assinatura sem nome precisa ser representavel e precisa nao produzir nome. Se
o silencio so fosse afirmado na Fase 2, a Fase 1 entregaria um acervo cujas entradas ja
poderiam falar, e a Fase 2 seria construida sobre um tipo que mente. O verificador checa
isso na Fase 1 colocando uma entrada sem nome no acervo a mao e exigindo `#linhaN`.

**OPER-03 ("demonstravel sem jogo aberto e sem rede") esta na Fase 3.** A suite inteira ja
sustenta essa linha nas tres fases, mas na Fase 3 ele CUSTA: e a unica fase onde uma
implementacao ingenua precisaria de rede de verdade. Mapea-lo na Fase 1 o tornaria de
graca, e portanto sem significado.

---
*Roadmap created: 2026-08-30*
