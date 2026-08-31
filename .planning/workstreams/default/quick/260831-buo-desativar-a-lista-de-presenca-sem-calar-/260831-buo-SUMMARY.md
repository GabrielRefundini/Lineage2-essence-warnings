---
task: 260831-buo
workstream: default
title: /desativarlista e /ativarlista — a lista de presenca cai, o lembrete de 10 minutos NAO
status: complete
completed: 2026-08-31
subsystem: agenda + presenca + loot + comandos
tags: [agenda, presenca, loot, comandos, persistencia, solo-boss, estado-visivel]
key-files:
  created:
    - tests/test_desativar_lista_de_presenca.py
  modified:
    - l2scanner/agenda.py
    - l2scanner/presenca.py
    - l2scanner/loot.py
    - l2scanner/comandos.py
    - l2scanner/sessao.py
    - l2scanner/__main__.py
    - tests/test_comandos.py
    - tests/test_presenca.py
    - tests/test_desativar_solo_boss.py
    - config.toml
    - README.md
metrics:
  suite_antes: "3281 passed, 23 skipped (MEDIDO neste branch em b9d2e46)"
  suite_depois: "3406 passed, 23 skipped"
  testes_novos: 121
  linhas_em_main: "51 insercoes, 3 delecoes"
actuals:
  tokens: 96000
  tasks: 3
  commits: 3
---

# Quick 260831-buo: /desativarlista e /ativarlista

**A party parou de fazer Solo Boss em grupo. A maquinaria de montar grupo
desliga por comando do WhatsApp — e o aviso de que o boss vai nascer continua
chegando.**

## O que foi construido

| Comando | O que faz |
|---|---|
| `/desativarlista` (`/desativarpresenca`) | Para de montar grupo no Solo Boss |
| `/ativarlista` (`/ativarpresenca`) | Volta a montar |

`/desativar-lista` e `/desativar lista` chegam de graca: `interpretar` ja tira
hifens do miolo e junta as duas primeiras palavras.

**As quatro coisas que calam:** a chamada "Quem vai?", o `/entrar` e o `/sair`,
o fechamento da lista quando o boss nasce, e a designacao de loot
(`/loot-<nick>` e a linha `Loot:` do aviso).

**A coisa que NAO cala, e que e o pedido inteiro:** o lembrete de 10 minutos
antes. Conferido contra o `config.toml` do repositorio, pelo caminho de
verdade, depois de a suite estar verde:

```
18:10 (chamada, 110 min antes das 20:00): (nada)
19:50 (lembrete, 10 min antes das 20:00): Solo Boss comeca em 10 minutos,
                                          as 20:00. Hora de voltar para a
                                          cidade e se preparar.
```

## A garantia do lembrete e ESTRUTURAL, e nao um teste

Esta e a decisao que sustenta a tarefa inteira, e ela e sobre ONDE o `continue`
mora.

O gate do `/desativarsoloboss` fica no laco de **evento**, antes de os
candidatos nascerem — e por isso alcanca os tres tipos de aviso de uma vez.
Este fica **dentro do laco de tipo**, condicionado a `TipoDeAviso.CHAMADA`:

```python
if (
    tipo is TipoDeAviso.CHAMADA
    and apelido_do_evento(evento.nome) in listas_desligadas
):
    continue
```

O ramo do `ANTES` passa por ali e **nao consulta essa variavel**. Nao existe
caminho de codigo que leve a antecedencia ate ela. O teste-titulo
(`test_com_a_lista_desligada_o_LEMBRETE_de_10_minutos_continua_saindo`) existe
e e o primeiro do arquivo, mas ele **confirma um desenho, e nao segura um**.

Ele foi colado no `if evento.chamar_minutos_antes <= 0` que ja estava la, de
proposito: aquela linha e "chamada desligada pelo config" e esta e "chamada
desligada por comando". Quem for depurar uma chamada que nao saiu encontra os
dois motivos a mesma altura da tela.

## Um portao por superficie, no funil mais estreito de cada uma

Nada de `if lista_desligada` espalhado pelo `__main__.py`.

| Superficie | Onde | Por que ali |
|---|---|---|
| A CHAMADA | `avisos_devidos`, ramo da CHAMADA | o funil dos tres tipos, gateando so um |
| `/entrar` e `/sair` | guarda **prependido** em `presenca.py` | ver abaixo |
| O FECHAMENTO | `fechar_ocorrencias`, **antes** do `fechar` | ver abaixo |
| A DESIGNACAO | `nick_para_o_aviso` e `responder_designacao` | as duas unicas bocas do loot designado |

### Por que o guarda do `/entrar` e PREPENDIDO

Um guarda posto depois do `if not nick` deixaria o **dono sem bloco
`[[membro]]`** recebendo *"Adicione um bloco [[membro]] com nick e telefone no
config.toml"* — uma mensagem que manda a pessoa consertar um arquivo que nao
esta quebrado. Prependido, nenhuma linha existente muda de lugar (o caminho com
a lista ligada e byte a byte o de hoje, porque o helper devolve `None`) e toda
entrada responde a verdade.

**Gatear no resolvedor foi considerado e recusado.** Fazer
`ocorrencia_da_chamada` devolver `None` produziria a mensagem de
`_sem_chamada_na_agenda` — *"ponha `chamar_minutos_antes` no `[[evento]]` do
config.toml"* —, que e mentira: o config esta certo e foi um comando que
desligou. Mandar o usuario editar o arquivo errado e pior que nao responder.

### Por que o `continue` do fechamento vem ANTES do `fechar`

Mesmo argumento que a docstring da funcao ja fazia para a lista vazia: **um
tick que nao fala nao pode queimar o marcador.** Queimando-o, o usuario que
religasse a lista dentro dos 5 minutos de tolerancia encontraria a ocorrencia
ja fechada, e aquela lista ficaria muda **para sempre**, sem nada explicando
por que. Pulando antes, religar dentro da janela ainda fecha —
`test_religando_dentro_da_janela_o_fechamento_ainda_acontece`.

## O marcador, e por que ele nao tem data

`.agenda/lista_desligada_solo-boss` — arquivo vazio, `O_CREAT|O_EXCL` para
criar, `unlink` para apagar. O mesmo idioma do `evento_calado_`, cujo SUMMARY
irmao ja defende a escolha por escrito (sem read-check-write entre as duas
instancias; a direcao da falha de leitura ja vem certa).

Ele e o **segundo morador de `_PREFIXOS_SEM_DATA`**, e a ausencia de data e a
funcionalidade: `podar` roda no construtor, ou seja a cada arranque do scanner.
Um marcador datado religaria a lista sozinho em `DIAS_DE_MARCADOR` — a party
voltaria a receber "Quem vai?" tres dias depois de o usuario ter desligado,
sem ninguem mandar. `test_a_poda_nao_expira_o_desligamento_da_lista` prova com
`podar(hoje=2030-01-01)`.

O tripwire de introspecao (`todo PREFIXO_* escolhe um dos dois baldes`)
continua verde **sem ter sido enfraquecido**, e ganhou companhia: um teste
afirma que os dois baldes seguem disjuntos.

## Por evento, e nao global

O marcador e chaveado pelo `apelido_do_evento`, como o irmao. Um marcador
global unico foi considerado e recusado por tres razoes medidas:

1. **`presenca.py` ja e generico por construcao, e por escrito.** A docstring
   de `_sem_chamada_na_agenda` diz que citar "Solo Boss" ali seria o modulo
   conhecendo um nome de evento. Um marcador global obrigaria justamente esse
   modulo a assumir que a lista e de um evento so.
2. **`nomes_dos_eventos` serve as duas superficies sem uma linha nova.** Com
   marcador global o `/status` precisaria de uma segunda frase escrita a mao,
   com uma segunda fonte de verdade sobre qual evento tem lista.
3. **A inercia do marcador orfao vem de graca.** Renomear o `[[evento]]` depois
   de desligar deixa o marcador inerte nas duas pontas.

Geral no armazenamento, especifico na superficie: **o enum ganhou exatamente
os dois membros pedidos.**

## As duas chaves nao sao aninhadas, e o `/status` mostra as duas

| `/desativarsoloboss` | `/desativarlista` | O que o grupo recebe |
|---|---|---|
| ligado | ligada | chamada de 110 min + lembrete de 10 min + fechamento |
| ligado | **desligada** | **so o lembrete de 10 min** — o pedido desta tarefa |
| **desligado** | ligada | nada; `/entrar` ainda anota e a lista ainda fecharia |
| **desligado** | **desligada** | nada, e `/entrar` e `/loot-<nick>` tambem recusam |

**Precedencia: nenhuma.** O `/desativarsoloboss` e um martelo maior *na
chamada* (cala os tres tipos), mas nao alcanca `/entrar`, nem o fechamento, nem
a designacao. Nenhuma das duas contem a outra.

Por isso o `/status` **nomeia as duas separadamente** — e isso e correcao, nao
verbosidade: cada uma e desfeita por um comando diferente, e um `/status` que
as fundisse deixaria o usuario sem saber se manda `/ativarsoloboss` ou
`/ativarlista`. Mandar o errado devolve "ja estava ligado", que le como bot
quebrado.

**E a resposta do proprio comando consulta o outro estado.** A frase que faz
esta funcionalidade valer — *"o lembrete de 10 minutos CONTINUA chegando"* — e
**falsa** se o boss estiver calado. Prometer um aviso que nao vai chegar e o
pior defeito possivel aqui, entao `responder_lista_de_presenca` le
`registro.eventos_calados()` e troca a frase:

> ... O lembrete de 10 minutos antes **tambem nao esta saindo, mas por outro
> motivo**: os avisos do Solo Boss estao desativados. Mande /ativarsoloboss se
> quiser o lembrete de volta. ...

Os minutos saem de `evento.avisar_minutos_antes`, **nunca de um literal** —
mesma lei do `_o_que_o_evento_anuncia`, e ha teste com um evento de 25 minutos.

## A chamada encurtou (D4)

De 149 caracteres, doze vezes por dia no grupo, para:

```
Solo Boss as 20:00. Quem vai? (/entrar /sair no privado)
```

**A palavra "privado" sobreviveu de proposito**, e o comentario de cima diz por
que: a ponte Baileys desta conta vem com ingestao de grupo desligada (medido
2026-08-24). Uma chamada que nao diz onde responder colhe resposta num lugar
que o bot nunca le, e quem respondeu conclui que o scanner morreu. E o fato
mais caro de reaprender neste recurso, e o comentario agora avisa que a forma
curta ainda o carrega.

**`tests/test_agenda.py` nao precisou de uma linha.** Ele afirma a chamada por
substring (nove asercoes: `"Solo Boss"`, `"20:00"`, `"/entrar"`, `"/sair"`,
`"privado"`, mais quatro negativas), e o texto curto satisfaz todas — que era
exatamente o criterio do plano para saber se o encurtamento perdeu algum fato.

## A armadilha de TIPO da costura

`listas_desligadas()` devolve um **conjunto de apelidos**; `nick_para_o_aviso`
e `responder_designacao` recebem um **`bool`**. Passar o frozenset direto
compila, roda, e fica **truthy sempre que a lista de QUALQUER evento estiver
desligada** — a linha `Loot:` sumiria do TvT tambem, sem erro nenhum e sem
ninguem perceber.

A expressao e uma so, em exatamente tres lugares, e em nenhum outro:

| Onde | O que recebe |
|---|---|
| `sessao.py` (laco principal) | a local do tick |
| `__main__.py` (laco `--so-agenda`) | a local do tick |
| `__main__.py` (ramo `LOOT_DESIGNAR`) | leitura na hora — ali nao existe local de tick |

Ha um tripwire de fonte para cada laco, e um deles afirma explicitamente que o
laco `--so-agenda` **converte** em vez de passar o conjunto cru.

Os dois lacos leem o disco **a cada tick, sem cache** — o comando pode chegar
na outra instancia do usuario —, mas **uma unica vez por tick**: duas leituras
no mesmo tick poderiam discordar entre si.

## Fronteira explicita: o que NAO foi desligado

**Uma designacao que ja existia quando a lista foi desligada continua sendo
consumida** no horario do boss, e continua gravando em `.loot/`. Isso e D3
sendo obedecido, e nao esquecimento: o consumo e **historico**, e o usuario
disse para nao tocar no historico. Quem quiser desfazer usa `/loot-` antes do
horario, ou `/corrigir` depois. Escrito como teste
(`test_uma_designacao_ANTERIOR_ainda_e_consumida`) justamente para nao virar
surpresa.

**`/loot-` (cancelar) continua funcionando**, de proposito: bloquear a unica
forma de apagar uma designacao existente encalharia estado que o usuario nao
consegue mais ver — o aviso parou de mostrar a linha `Loot:`. Cancelar so
remove; nao ha estrago a conter.

**`/pegou`, `/corrigir` e `/<nick>` ficam inteiros.** Desligar a lista nao
encosta na pasta `.loot/`, e ha um teste grosseiro que compara o conteudo da
pasta antes e depois.

## Autorizacao: nivel de DONO

Os dois ficaram **fora** de `COMANDOS_DE_MEMBRO`. Mesma categoria de estrago do
`/desativarsoloboss` — muda o que a party inteira recebe por tempo
indeterminado, e o efeito e a **ausencia** de mensagem — com uma agravante
propria: **um party-mate podia desligar a lista de presenca de todos os
outros**. Alem do tripwire derivado, ha prova nomeada.

## Os QUATRO tripwires derivados (o plano previu tres)

| # | Onde | O que deriva | Estado |
|---|---|---|---|
| 1 | `test_comandos.py` | `set(_AJUDA) == set(Comando)` | verde, duas linhas novas em `_AJUDA` |
| 2 | fronteira de autorizacao | `set(Comando) - COMANDOS_DE_MEMBRO` | verde, os dois ja nascem fora |
| 3 | `test_presenca.py` | `TABELA` x comandos "antigos" | verde, duas linhas novas |
| **4** | `test_comandos.py:144` | `set(Comando) == {literal}` | verde, duas linhas novas |

**O quarto nao estava no plano** — veio da correcao do plan-checker.
`test_o_vocabulario_e_fechado` afirma igualdade contra um literal escrito a
mao, e ele fica vermelho no instante em que o enum cresce. Foi consertado na
mesma tarefa que o quebrou (Tarefa 2), somando os dois membros com um
comentario na voz do bloco acima.

**Nenhum dos quatro foi enfraquecido.** Em especial: a asercao do quarto
continua sendo igualdade e nao subset, e os dois comandos novos **nao** foram
postos em `COMANDOS_DE_MEMBRO` para escapar do terceiro — o caminho preguicoso
teria deixado a suite verde e a fronteira de autorizacao e que pagaria.

O `git diff` de `tests/test_presenca.py` tem **8 insercoes e ZERO delecoes**; o
de `tests/test_comandos.py`, **14 insercoes e zero delecoes**.

## O toque em `__main__.py`

**51 insercoes, 3 delecoes**, em 5 hunks (um a mais que o plano previa, por
causa do desvio do rename abaixo):

| Hunk | O que |
|---|---|
| import | dois nomes acrescentados a lista existente + o rename, sem reordenar |
| `atender_comandos` | um ramo `elif` novo, inserido entre dois existentes |
| `LOOT_DESIGNAR` | o kwarg `lista_desligada=` no ramo ja existente |
| `_obedecer_status` | a parte nova, sem mudar a assinatura |
| `laco_da_agenda` | a local do tick e os dois kwargs |

Nenhuma reformatacao, nenhuma reordenacao, nenhuma linha vizinha tocada. Toda a
logica mora em `agenda.py` (+279), `presenca.py` (+85), `comandos.py` (+75) e
`loot.py` (+48). `sessao.py` levou +31/-3.

## Desvios do plano

### 1. (Rule 3) O rename arrastou suas quatro referencias para a Tarefa 2

O plano punha o rename `nomes_calados` -> `nomes_dos_eventos` na **Tarefa 2**
(em `agenda.py`) e a atualizacao das quatro referencias — `__main__.py` e
`tests/test_desativar_solo_boss.py` — na **Tarefa 3**.

Isso deixaria o commit da Tarefa 2 **sem conseguir importar
`l2scanner.__main__`**, derrubando a suite inteira em vez dos tres testes da
TABELA que o straddle do plano previa. Um commit que nao importa nao e atomico.

**Conserto:** as quatro referencias entraram na Tarefa 2, junto com o rename
que as causou. Nenhuma asercao mudou de valor. Commit `c5e8ddf`.

### 2. (Rule 1) O teste novo mandava sempre o mesmo id de mensagem

`TestNaCostura._atender` usava o id fixo `909`. O teste que manda **dois**
comandos sobre o mesmo registro (`test_as_duas_chaves_convivem_pelo_caminho_
real`) tinha o segundo descartado pelo dedup do `comando_<id>` — que e o dedup
funcionando — e portanto afirmava o contrario do que pensava afirmar: passaria
igual se o ramo de despacho novo nao existisse.

**Conserto:** o id entra por parametro, com o motivo escrito na docstring do
helper. Commit `7c30981`.

### 3. Ambiente: `uv` nao esta no PATH desta maquina

Os `<verify>` do plano chamam `uv run pytest`. Nao ha `uv` no PATH nem no
disco alcancavel deste shell, e o `.venv/` do repositorio nao tem `pytest`. A
suite foi rodada com o Python 3.12 global, que tem `pytest` 9.1.1, `ruff`
0.15.20 e todas as dependencias do projeto (`cv2`, `numpy`, `mss` conferidos).
Os comandos tambem foram rodados **dentro do worktree**, e nao no
`C:\Users\refun\Desktop\Lineage2-warnings` que os `<verify>` do plano citam —
rodar la teria medido o codigo errado.

## Verificacao

| Prova | Onde |
|---|---|
| **O lembrete de 10 min sobrevive** (o pedido inteiro) | `TestOLembreteDeDezMinutosSobrevive` |
| O texto curto da chamada, e a palavra "privado" | `TestOTextoDaChamada` |
| A chamada cala; o AGORA e outro evento nao | `TestPortaoDaChamada` |
| `/entrar` e `/sair` recusam sem escrever em disco | `TestPortaoDoEntrarEDoSair` |
| O fechamento nao sai e o marcador NAO queima | `TestPortaoDoFechamento` |
| A linha `Loot:` some; `/loot-` continua | `TestPortaoDaDesignacao` |
| O historico intacto, e a designacao anterior ainda consome | `TestOHistoricoDeLootFicaInteiro` |
| Restart nao religa; a poda de 2030 nao expira | `TestOEstadoEmDisco` |
| Disco estragado faz a CHAMADA SAIR | `TestDiscoEstragado` |
| Duas instancias: exatamente uma desliga | `TestDuasInstancias` |
| O `/status` nas QUATRO combinacoes | `TestOStatusNasQuatroCombinacoes` |
| A resposta consulta o outro estado | `TestARespostaDoComando` |
| As quatro palavras, e o roster real ileso | `TestOsComandos` |
| Os dois lacos, um por comportamento e um por fonte | `TestOsDoisLacosObedecem` |
| Ponta a ponta por `atender_comandos` | `TestNaCostura` |

**Nenhum relogio e nenhuma fonte foram monkeypatchados** — o tempo entra por
parametro e os casos de disco estragado sao produzidos apagando a pasta ou
criando um diretorio com nome de marcador.

**Suite: 3281 passed, 23 skipped (MEDIDO neste branch em `b9d2e46`) -> 3406
passed, 23 skipped.** +125, e a conta fecha exatamente: 121 testes novos + 4
das duas linhas novas da `TABELA`, que alimenta dois testes parametrizados.
Zero regressoes.

> **Nota sobre o numero da tarefa.** O enunciado citava "~1863 testes". Esse
> numero e o do SUMMARY do irmao (quick 260830-ars) e nao corresponde mais a
> este branch: os workstreams `mercado` e `identidade` cresceram a suite para
> **3281** desde entao. O baseline foi medido rodando a suite no worktree em
> `b9d2e46` antes de escrever uma linha. Reportar contra o numero do enunciado
> teria escondido 1418 testes.

`ruff check` limpo em todos os arquivos tocados.

## Restricoes respeitadas

- `l2scanner/mercado_*.py`, `l2scanner/identidade.py`, `l2scanner/acervo.py`,
  `l2scanner/notificador.py` — **nao tocados**.
- `.planning/workstreams/mercado/`, `.planning/workstreams/identidade/`,
  `ROADMAP.md` — **nao tocados**.
- Portugues sem acento em identificadores, comentarios e docstrings. README e
  `config.toml` mantiveram a acentuacao que ja tinham (prosa de usuario).
- Um commit atomico por tarefa, so codigo.

## O que ficou de fora, por escrito

- **O painel do console (`desenhar_status`) nao mostra a lista desligada.** Ele
  mora em `__main__.py`, que estava em disputa de merge com duas outras
  sessoes. O requisito decidido era o `/status`, e ele esta cumprido.
- **Uma designacao anterior continua sendo consumida** — D3 obedecido, com
  teste.
- **Marcador orfao por renomeacao** de `[[evento]]`: inerte nas duas pontas,
  exatamente como o do `evento_calado_`.

## Commits

| Hash | Mensagem |
|---|---|
| `3520a83` | test: a lista cai, o lembrete de 10 minutos NAO — afirmado antes |
| `c5e8ddf` | feat: a lista de presenca desliga sozinha, e o boss continua avisando |
| `7c30981` | feat: a costura — os dois lacos obedecem e o /status conta as duas |

## Self-Check: PASSED

- `tests/test_desativar_lista_de_presenca.py` — FOUND
- `l2scanner/agenda.py` (`PREFIXO_LISTA_DESLIGADA`, `responder_lista_de_presenca`) — FOUND
- `l2scanner/presenca.py` (`_evento_com_lista_desligada`) — FOUND
- `l2scanner/loot.py` (`lista_desligada`) — FOUND
- `l2scanner/comandos.py` (`DESATIVAR_LISTA`, `ATIVAR_LISTA`) — FOUND
- Commits `3520a83 c5e8ddf 7c30981` — FOUND
