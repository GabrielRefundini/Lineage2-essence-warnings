---
task: 260831-buo
workstream: default
title: /desativarlista e /ativarlista — a lista de presenca cai, o lembrete de 10 minutos NAO
type: quick
requirements: []
files_modified:
  - tests/test_desativar_lista_de_presenca.py
  - l2scanner/agenda.py
  - l2scanner/presenca.py
  - l2scanner/loot.py
  - l2scanner/comandos.py
  - l2scanner/sessao.py
  - l2scanner/__main__.py
  - tests/test_desativar_solo_boss.py
  - tests/test_presenca.py
  - config.toml
  - README.md
autonomous: true
estimate:
  tokens: 120000
  raw_tokens: 60000
  tasks: 3
  confidence: low
must_haves:
  truths:
    - "Com a lista desligada, a CHAMADA (`Quem vai?`) para de sair no grupo."
    - "Com a lista desligada, o aviso de ANTECEDENCIA de 10 minutos CONTINUA saindo — este e o pedido inteiro (D3)."
    - "Com a lista desligada, `/entrar` e `/sair` respondem que a lista esta desligada e NAO escrevem nada em disco."
    - "Com a lista desligada, a mensagem de fechamento da lista nao sai quando o boss nasce, e o marcador `fechado_` NAO e queimado."
    - "Com a lista desligada, `/loot-<nick>` recusa sem gravar e a linha `Loot: <nick>` some do aviso de antecedencia."
    - "Com a lista desligada, `/pegou`, `/corrigir`, `/<nick>` e o consumo automatico continuam intactos — a pasta `.loot/` nao e tocada (D3)."
    - "O desligamento sobrevive a fechar e reabrir o `vigiar-party.bat`, e nao expira na poda."
    - "O `/status` diz a verdade nas QUATRO combinacoes de `/desativarsoloboss` x `/desativarlista`, nomeando cada chave separadamente."
    - "A CHAMADA passou a ser `{evento} as {hora}. Quem vai? (/entrar /sair no privado)` (D4)."
  artifacts:
    - "tests/test_desativar_lista_de_presenca.py — a suite nova, vermelha antes do codigo"
    - "l2scanner/agenda.py — PREFIXO_LISTA_DESLIGADA, desligar_lista/religar_lista/listas_desligadas, o gate de CHAMADA em avisos_devidos, responder_lista_de_presenca"
    - "l2scanner/presenca.py — o portao de /entrar, /sair e do fechamento"
    - "l2scanner/loot.py — o portao da DESIGNACAO (nick_para_o_aviso e responder_designacao)"
    - "l2scanner/comandos.py — DESATIVAR_LISTA e ATIVAR_LISTA no enum, no vocabulario e no _AJUDA"
  key_links:
    - "`avisos_devidos` recebe `listas_desligadas` e SO o ramo `TipoDeAviso.CHAMADA` o consulta — a ANTECEDENCIA nao pode alcancar essa variavel."
    - "`presenca.fechar_ocorrencias` le `registro.listas_desligadas()` ANTES de `registro.fechar(chave)`, para nao queimar o marcador."
    - "`PREFIXO_LISTA_DESLIGADA` entra em `_PREFIXOS_SEM_DATA` e nunca em `_PREFIXOS_CONHECIDOS`."
    - "`_AJUDA` ganha as duas linhas novas, senao o tripwire `set(_AJUDA) == set(Comando)` quebra a suite."
    - "Os dois comandos ficam FORA de `COMANDOS_DE_MEMBRO`."
    - "`tests/test_presenca.py` TABELA ganha as duas linhas, senao o TERCEIRO tripwire (`test_a_tabela_cobre_todo_comando_ANTIGO_do_enum`) quebra — ele deriva de `set(Comando) - COMANDOS_DE_MEMBRO`, e a decisao 5 poe os dois novos exatamente ali."
---

# /desativarlista e /ativarlista

## Objetivo

Dois comandos novos que desligam e religam **so a maquinaria de montar grupo**
do Solo Boss — a chamada "Quem vai?", o `/entrar`/`/sair`, o fechamento da
lista e a designacao de loot —, deixando o **aviso de antecedencia de 10
minutos intacto**. O estado sobrevive a reiniciar o `vigiar-party.bat`, nao
expira sozinho, e o `/status` conta.

E a irma fina do `/desativarsoloboss` da quick 260830-ars, e a diferenca e o
recurso inteiro: aquele cala o boss por completo, este **so para de perguntar
quem vai**. A party parou de fazer Solo Boss por enquanto e o usuario quer
continuar sabendo que o boss vai nascer.

De quebra, a chamada encurta (D4): a frase de hoje tem 149 caracteres e sai 12
vezes por dia no grupo.

## Decisoes do usuario (nao sao julgamento meu)

**D1.** O par e `/desativarlista` e `/ativarlista`, na MESMA forma do
`/desativarsoloboss`: marcador duravel e SEM DATA em disco, sobrevive a
reiniciar, nada religa sozinho, e o `/status` reporta.

**D2.** Com a lista desligada, exatamente QUATRO coisas calam:
  (a) a CHAMADA "Quem vai?";
  (b) `/entrar` e `/sair` respondem que a lista esta desligada, em vez de
      escrever presenca em disco;
  (c) a mensagem de fechamento da lista quando o boss nasce;
  (d) a DESIGNACAO de loot — a linha `Loot: <nick>` do aviso de 10 minutos e o
      comando `/loot-<nick>`.

**D3.** O que NAO pode calar, em hipotese nenhuma:
  - o aviso de **ANTECEDENCIA** (`avisar_minutos_antes = 10`) continua saindo
    normalmente. **E o pedido inteiro. Um plano que o cale esta errado.**
  - o **HISTORICO** de loot: `/pegou`, `/corrigir` e a consulta `/<nick>`
    continuam funcionando. Desligar a lista nao encosta em `.loot/`.

**D4.** A CHAMADA passa a ser exatamente:

```python
f"{aviso.evento} as {hora}. Quem vai? (/entrar /sair no privado)"
```

## Decisao de desenho 1 — o marcador e POR EVENTO, e nao global

**Escolhido: `PREFIXO_LISTA_DESLIGADA = "lista_desligada_"`, chaveado pelo
`apelido_do_evento`, exatamente como o `evento_calado_`.**
**Recusado: um marcador global unico (`lista_desligada`, sem chave).**

O contra-argumento do global e legitimo: hoje so o Solo Boss tem lista, porque
so ele tem `chamar_minutos_antes > 0`. Ele cai por tres razoes, e as tres sao
de reuso medido, nao de gosto:

- **`presenca.py` ja e generico por construcao, e por escrito.** `_com_chamada`
  filtra por `chamar_minutos_antes > 0` e a docstring de `_sem_chamada_na_agenda`
  e explicita: "Nomeia o CAMPO, e nao o evento... citar 'Solo Boss' aqui seria o
  modulo conhecendo um nome de evento". Um marcador global obrigaria justamente
  esse modulo a assumir que a lista e de um evento so — desfazendo o D-03 da
  Fase 10 para economizar um sufixo.
- **`nomes_calados` serve as duas superficies sem uma linha nova.** O corpo dela
  ja e `apelidos -> nomes conforme o config.toml`; com marcador por evento o
  `/status` da lista sai por reuso. Com marcador global o `/status` precisaria de
  uma segunda frase, escrita a mao, com uma segunda fonte de verdade sobre qual
  evento tem lista.
- **A inercia do marcador orfao vem de graca.** Se o usuario renomear o bloco
  `[[evento]]` depois de ter desligado a lista, o marcador antigo nao gateia nada
  (o gate compara com os eventos configurados) e nao aparece no `/status` — o
  mesmo desfecho ja documentado no `evento_calado_`. Um marcador global nao tem
  essa propriedade: ele continuaria valendo para um evento que nao existe mais.

**Geral no armazenamento, especifico na superficie** — a regra ja escrita no
enum `Comando`. A chave em disco e o apelido, o gate le um conjunto de apelidos,
o responder recebe o nome; **e o enum ganha exatamente DOIS membros**, os que o
usuario pediu.

**O marcador NAO TEM DATA e entra em `_PREFIXOS_SEM_DATA`.** Mesma razao,
palavra por palavra, do `PREFIXO_EVENTO_CALADO`: `podar` roda no construtor, ou
seja a cada arranque, e um marcador datado religaria a lista sozinho em
`DIAS_DE_MARCADOR` — contra a decisao explicita do usuario. O comentario novo
tem que dizer isso na mesma voz, e citar o irmao: sao os dois unicos namespaces
desta pasta que guardam uma **decisao** em vez de um **fato datado**, e e por
isso que os dois moram no mesmo balde.

## Decisao de desenho 2 — onde cada um dos quatro portoes mora

Um portao por superficie, no funil mais estreito de cada uma. **Nada de
`if lista_desligada` espalhado pelo `__main__.py`.**

### (a) A CHAMADA — em `avisos_devidos`, e SO no ramo da CHAMADA

Parametro novo `listas_desligadas: frozenset[str] | set[str] = frozenset()`,
**separado** do `eventos_calados` que ja existe. O teste dele:

```python
if tipo is TipoDeAviso.CHAMADA and apelido_do_evento(evento.nome) in listas_desligadas:
    continue
```

Ele vai **imediatamente ao lado** do `if evento.chamar_minutos_antes <= 0 and
tipo is TipoDeAviso.CHAMADA: continue` que ja esta la. Nao e arrumacao: aquela
linha e "chamada desligada pelo config" e esta e "chamada desligada por
comando", e as duas fontes do mesmo silencio tem que ser lidas juntas.

**E A GARANTIA DO D3 E ESTRUTURAL, NAO E UM TESTE.** O gate do
`eventos_calados` fica no `for evento`, antes dos candidatos, e por isso alcanca
os tres tipos. Este fica DENTRO do `for tipo, devido_em`, condicionado a
`TipoDeAviso.CHAMADA`. O ramo do `ANTES` nao consulta a variavel — nao ha como
ele cair. O teste de D3 existe assim mesmo (e ele e o teste-titulo desta
tarefa), mas ele confirma um desenho, e nao segura um.

Default vazio, como o irmao: toda chamada existente continua byte a byte.

### (b) `/entrar` e `/sair` — um guarda antes de tudo, em `presenca.py`

Helper novo `_evento_com_lista_desligada(eventos, desligadas)` devolvendo o
`nome` do primeiro evento de `_com_chamada` cujo apelido esta no conjunto (ou
`None`), e um guarda de tres linhas **prependido** a `responder_join` e a
`responder_leave`, lendo `registro.listas_desligadas()`.

**POR QUE PREPENDIDO E NAO NO MEIO.** Um guarda inserido depois do
`if not nick` deixaria o DONO sem bloco `[[membro]]` recebendo "Adicione um
bloco [[membro]]..." com a lista desligada — uma mensagem que manda a pessoa
consertar um arquivo que nao esta quebrado. Prependido, nenhuma linha existente
muda de lugar (o caminho com a lista LIGADA e byte a byte o de hoje, porque o
helper devolve `None`) e toda entrada responde a verdade.

**POR QUE NAO NO RESOLVEDOR (`ocorrencia_da_chamada` / `ocorrencia_do_join`).**
Foi considerado e recusado: fazer o resolvedor devolver `None` produziria a
mensagem `_sem_chamada_na_agenda`, que diz "ponha `chamar_minutos_antes` no
`[[evento]]` do config.toml" — mentira, o config esta certo e foi um comando que
desligou. Mandar o usuario editar o arquivo errado e pior que nao responder.

**O `/sair` tambem recusa, e o lixo em disco nao e permanente.** Uma presenca
gravada antes do desligamento fica em `.agenda/`; ela e `PREFIXO_PRESENCA`, que
esta em `_PREFIXOS_CONHECIDOS`, entao a poda a come em 3 dias. Desligar a lista
nao deixa residuo eterno.

### (c) O FECHAMENTO — em `fechar_ocorrencias`, antes do `fechar`

```python
for nome, alvo in ocorrencias_na_janela(agora, eventos):
    if apelido_do_evento(nome) in desligadas:
        continue
```

**A POSICAO E A DECISAO.** O `continue` vem **antes** do `registro.fechar(chave)`,
pela mesma razao ja escrita na docstring da funcao para o caso da lista vazia:
**um tick que nao fala nao pode queimar o marcador.** Assim, se o usuario
religar a lista dentro da janela de tolerancia, o fechamento ainda acontece. Se
o marcador fosse queimado, a lista daquela ocorrencia ficaria muda para sempre.

### (d) A DESIGNACAO de loot — duas superficies, em `loot.py`

- `nick_para_o_aviso(aviso, designacao, lista_desligada=False)`: uma QUARTA
  condicao, ao lado das tres que ja estao la, devolvendo `None`. A funcao e pura
  e continua pura — o booleano entra por parametro.
- `responder_designacao(..., lista_desligada=False)`: recusa **antes** de
  `registro.designar(...)`, e a recusa nao escreve nada.

**`/loot-` (cancelar) CONTINUA FUNCIONANDO, de proposito.** Bloquear a unica
forma de apagar uma designacao existente encalharia estado que o usuario nao
consegue mais ver — o aviso de antecedencia parou de mostrar a linha `Loot:`.
Cancelar so remove; nao ha estrago a conter.

**FRONTEIRA EXPLICITA, e ela vai para o SUMMARY:** uma designacao que ja
existia quando a lista foi desligada **continua sendo consumida** no horario do
boss e continua gravando em `.loot/`. Isso e D3 sendo obedecido, nao
esquecimento: o consumo e historico, e o usuario disse para nao tocar no
historico. Quem quiser desfazer usa `/loot-` antes do horario, ou `/corrigir`
depois.

## Decisao de desenho 3 — parametro so onde a pureza obriga

`avisos_devidos` e `nick_para_o_aviso` recebem o estado **por parametro**,
porque as duas sao **puras** e a docstring de `avisos_devidos` promete isso por
escrito ("Sem relogio, sem disco, sem rede").

`responder_join`, `responder_leave` e `fechar_ocorrencias` leem
`registro.listas_desligadas()` **por dentro**, porque as tres ja recebem o
`RegistroEmDisco` e ja tocam disco na linha seguinte. Enfiar um parametro nelas
nao compraria pureza nenhuma — compraria so mais dois pontos de edicao em
`__main__.py` e `sessao.py`.

O efeito pratico e o que a restricao de merge deste dia pede: **os portoes (b) e
(c) nao custam UMA linha em `__main__.py`**. Sobram os dois pontos que o
precedente ja tocou (o laco da agenda em cada arquivo) mais o ramo de despacho.

`sessao` e o laco `--so-agenda` leem **do disco a cada tick, sem cache** — o
comando pode chegar na OUTRA instancia do usuario, e um cache faria este
processo continuar chamando o que o outro acabou de desligar.

## Decisao de desenho 4 — a interacao com `/desativarsoloboss`

As duas chaves **nao sao aninhadas**, e e por isso que precisam ser mostradas
separadas.

| `/desativarsoloboss` | `/desativarlista` | O que o grupo recebe |
|---|---|---|
| ligado | ligada | chamada de 110 min + lembrete de 10 min + fechamento |
| ligado | **desligada** | **so o lembrete de 10 min** — o pedido desta tarefa |
| **desligado** | ligada | nada; `/entrar` ainda anota e a lista ainda fecharia |
| **desligado** | **desligada** | nada, e `/entrar` e `/loot-<nick>` tambem recusam |

**Precedencia: nenhuma. As duas valem, cada uma no que alcanca.** O
`/desativarsoloboss` e um martelo maior **na CHAMADA** (ele cala os tres tipos),
mas ele nao alcanca `/entrar`, nem o fechamento, nem a designacao — a quick
260830-ars deixou isso escrito como fronteira explicita. Logo nenhuma das duas
contem a outra, e um "desliguei tudo" unico esconderia metade.

**O `/status` nomeia as duas separadamente, e isso e correcao e nao verbosidade:
cada uma e desfeita por um COMANDO DIFERENTE.** Um `/status` que fundisse as
duas num "tudo desligado" deixaria o usuario sem saber se manda `/ativarsoloboss`
ou `/ativarlista` — e mandar o errado devolve "ja estava ligado", que le como bot
quebrado. Ordem: primeiro `avisos DESATIVADOS de ...` (o silencio maior), depois
`lista de presenca DESLIGADA de ...`.

**E a RESPOSTA do `/desativarlista` tem que consultar o outro estado.** A frase
que faz esta funcionalidade valer e "o lembrete de 10 minutos CONTINUA saindo" —
e ela e **falsa** se o boss estiver calado. Prometer um aviso que nao vai chegar
e o pior defeito possivel aqui, entao `responder_lista_de_presenca` le
`registro.eventos_calados()` e troca essa frase quando precisa.

## Decisao de desenho 5 — os nomes, e a auditoria de colisao

Formas aceitas, e o `interpretar` entrega as variantes de graca (ele tira hifen
e sublinhado do miolo e junta as duas primeiras palavras):

| Escrito | Cai em |
|---|---|
| `/desativarlista`, `/desativar-lista`, `/desativar lista` | `desativarlista` |
| `/desativarpresenca`, `/desativar-presenca`, `/desativar presenca` | `desativarpresenca` |
| `/ativarlista`, `/ativar-lista`, `/ativar lista` | `ativarlista` |
| `/ativarpresenca`, `/ativar-presenca`, `/ativar presenca` | `ativarpresenca` |

**O apelido aqui e SINONIMO, e nao abreviacao** — e a diferenca em relacao ao
precedente esta escrita para nao ser confundida. O `desativarboss` nasceu porque
`desativarsoloboss` tem 17 caracteres e a mao erra no meio do farm;
`desativarlista` ja tem 14 e nao precisa encolher. O risco aqui e outro: a
palavra. Quem pensa "presenca" em vez de "lista" digitaria uma forma que morre
no `continue` do laco de autorizacao, **sem resposta de recusa nenhuma** — e o
sintoma, do lado de quem digitou, e o bot ter caido.

**Auditoria de colisao com `_NICK_VALIDO` (`[A-Za-z0-9]{2,16}`)**, feita
exatamente como o comentario existente manda:

| Palavra | Letras | Casa `_NICK_VALIDO`? | Preco |
|---|---|---|---|
| `desativarlista` | 14 | **sim** | um char chamado `DesativarLista` deixa de responder a `/<nick>` |
| `ativarlista` | 11 | **sim** | idem para `AtivarLista` |
| `desativarpresenca` | 17 | nao (o teto e 16) | nenhum |
| `ativarpresenca` | 14 | **sim** | idem para `AtivarPresenca` |

Preco aceito e documentado, o mesmo ja pago por `desativarboss` (13 letras).
Nenhuma delas colide com o roster real (`TioMad`, `Kaus`, `Korzis`, `J4guar`,
`Yazalaque`, `Faerlina`) — e um teste confere que os nicks do `config.toml`
continuam resolvendo como consulta.

**`lista` sozinho NAO entra**, e a ausencia e deliberada em dobro: e a mesma
disciplina do D-02 (comando sem argumento nao mexe em estado duravel), e
"Lista" e um nome de personagem plausivel demais para queimar.

**Os dois ficam FORA de `COMANDOS_DE_MEMBRO`.** O efeito e a ausencia de
mensagem para a party inteira por tempo indeterminado — a mesma categoria de
estrago do `/desativarsoloboss`, e aqui com uma agravante: um party-mate podia
desligar a lista de presenca de todos os outros. Alem do tripwire derivado
(`set(Comando) - COMANDOS_DE_MEMBRO`), vai uma prova nomeada, porque a razao
deste par ficar de fora e propria dele.

## Decisao de desenho 6 — os textos, palavra por palavra

**A CHAMADA (D4):**

```
Solo Boss as 10:00. Quem vai? (/entrar /sair no privado)
```

**O comentario de cima da linha NAO E APAGADO JUNTO COM O TEXTO LONGO.** Ele
explica que "no PRIVADO" existe porque a ponte Baileys desta conta nao ingere
mensagem de grupo (medido 2026-08-24) — o fato mais caro de reaprender neste
recurso. A palavra "privado" sobreviveu dentro do parenteses de proposito, e o
comentario tem que dizer que a forma curta ainda carrega esse fato.

**`/entrar` e `/sair` com a lista desligada** — um texto so, que le certo para
os dois comandos, so no privado:

```
A lista de presenca do {nome} esta desligada: ninguem entra e ninguem sai
enquanto estiver assim. Quem religa e o dono, com /ativarlista.
```

Ele **nao promete nada sobre o lembrete de 10 minutos**, de proposito: quem
sabe se o boss tambem esta calado e o responder do dono, nao este. Superficie
que nao tem o fato nao faz a promessa.

**`/desativarlista`, com o boss FALANDO normalmente:**

```
{quem} desligou a lista de presenca do {nome}: paro de perguntar quem vai,
/entrar e /sair param de anotar, a lista nao fecha mais quando o boss nasce e
/loot-<nick> para de designar. O lembrete de {N} minutos antes CONTINUA
chegando, e o historico de loot (/pegou, /corrigir, /<nick>) continua inteiro.
Isto nao volta sozinho, nem reiniciando o scanner: mande /ativarlista.
```

`{N}` sai de `evento.avisar_minutos_antes`, **nunca de um literal** — mesma lei
do `_o_que_o_evento_anuncia`.

**`/desativarlista`, com o boss JA CALADO** (a frase do meio trocada):

```
... O lembrete de {N} minutos antes tambem nao esta saindo, mas por outro
motivo: os avisos do {nome} estao desativados. Mande /ativarsoloboss se quiser
o lembrete de volta. O historico de loot ...
```

**Os demais desfechos**, no tri-estado do irmao:

| Caso | Texto |
|---|---|
| ja desligada | `A lista de presenca do {nome} ja estava desligada. Mande /ativarlista quando quiser a chamada de volta.` |
| escrita falhou | `Nao consegui gravar o desligamento da lista do {nome} — o disco recusou. A chamada CONTINUA saindo e o /entrar continua anotando; mande /desativarlista de novo.` |
| religada | `{quem} religou a lista de presenca do {nome}: volto a perguntar quem vai, /entrar e /sair voltam a anotar, a lista fecha quando o boss nasce e /loot-<nick> volta a designar.` |
| ja ligada | `A lista de presenca do {nome} ja estava ligada. Nao mudei nada.` |
| religar falhou | `Nao consegui apagar o desligamento da lista do {nome} — o disco recusou. A lista CONTINUA desligada; mande /ativarlista de novo.` |
| evento fora da agenda | `Nao achei {nome} na agenda do config.toml — nao ha lista de presenca desse evento para desligar nem para religar.` |
| evento sem chamada | `O {nome} nao tem lista de presenca — falta chamar_minutos_antes no [[evento]] do config.toml. Nao ha o que desligar.` |

As duas ultimas recusas existem pela razao ja escrita em
`responder_silenciamento`: um marcador gravado para um evento que nao tem lista
nao gateia nada e nao aparece no `/status` — o bot responderia "desliguei" e as
duas superficies concordariam em nao mostrar nada, enquanto a chamada continuava
saindo. A segunda **nomeia o campo**, e nao o evento, seguindo
`_sem_chamada_na_agenda`.

**`/loot-<nick>` com a lista desligada:**

```
A lista de presenca do {nome} esta desligada, entao nao estou designando loot —
nada foi gravado. O historico continua: /pegou, /corrigir e /<nick> respondem
normalmente. Para voltar a designar, o dono manda /ativarlista.
```

**O `/status`:**

```
Scanner: Vigiando normalmente, lista de presenca DESLIGADA de Solo Boss, proximo: Solo Boss as 18:00.
```

## Nota de reuso — `nomes_calados` vira `nomes_dos_eventos`

A funcao mapeia `apelidos -> nomes conforme o config.toml` e **nunca soube por
que um apelido estava no conjunto**. O nome `nomes_calados` era verdadeiro
enquanto havia um namespace so; com o segundo ele passa a mentir na segunda
chamada. Renomear custa **quatro referencias** (`l2scanner/__main__.py` linhas
42 e 1318; `tests/test_desativar_solo_boss.py` linhas 48 e 490-498) e evita a
alternativa pior: uma copia da mesma expressao com outro nome, que e exatamente
o defeito que a docstring de `apelido_do_evento` documenta ter custado caro.

## Achado que economiza um arquivo

`tests/test_agenda.py:355-371` afirma a CHAMADA por **substring**, e nao por
igualdade: `"Solo Boss" in`, `"20:00" in`, `"/entrar" in`, `"/sair" in`,
`"privado" in texto.lower()`, mais as quatro negativas de `/join`, `/leave`,
`.entrar`, `.sair`. **O texto curto do D4 satisfaz todas as nove.** O
`test_a_chamada_nao_repete_nenhum_dos_dois_textos_de_hoje` tambem continua verde
(tres textos distintos). Logo `tests/test_agenda.py` **nao precisa ser editado**
— e se ele precisar, e sinal de que o texto novo perdeu um dos nove fatos.

**Este achado vale para `test_agenda.py` e para mais nenhum arquivo.** Dois
testes EXISTENTES sao editados nesta tarefa mesmo assim, e por razoes
diferentes: `test_desativar_solo_boss.py` pelo rename, e `test_presenca.py`
pelo terceiro tripwire da secao seguinte. Nenhum dos dois muda um veredito.

## Os TRES tripwires que um comando novo acorda

Este repo tem tres provas derivadas por introspecao, e um par de comandos novos
acorda **as tres**. Duas ja estavam no plano; a terceira mora num arquivo que
este plano quase declarou fora de escopo, e por isso ela ganha secao propria.

| # | Onde | O que deriva | O que fazer |
|---|---|---|---|
| 1 | `tests/test_comandos.py:263` | `set(_AJUDA) == set(Comando)` | duas linhas em `_AJUDA` (Tarefa 2) |
| 2 | fronteira de autorizacao | `set(Comando) - COMANDOS_DE_MEMBRO` recusa | nada — os dois ja nascem fora (Tarefa 2) |
| 3 | **`tests/test_presenca.py:1601`** | `antigos = set(Comando) - COMANDOS_DE_MEMBRO`, cruzado com a `TABELA` de destinos | **duas linhas na `TABELA` (Tarefa 3)** |

**O terceiro e o que morde.** `test_a_tabela_cobre_todo_comando_ANTIGO_do_enum`
monta `cobertos` interpretando o texto de cada linha da `TABELA` (linha 1509) e
afirma que `antigos - cobertos` e vazio. Pela **decisao 5 deste plano** os dois
comandos novos ficam FORA de `COMANDOS_DE_MEMBRO` — logo caem em `antigos`,
nao tem linha na `TABELA`, e o teste falha **dizendo o nome deles**. Nao ha
como escapar: e a mesma pinca que trouxe `.desativarsoloboss` para aquela
tabela, e o comentario que o irmao deixou la diz isso com todas as letras
("Nao sao 'antigos' — entraram nesta tabela porque o tripwire logo abaixo os
TROUXE").

As duas linhas sao:

```python
(".desativarlista", ".desativarlista", True),
(".ativarlista", ".ativarlista", True),
```

**O `True` e uma AFIRMACAO, e nao burocracia.** A mesma `TABELA` alimenta
`test_destino_de_cada_comando_antigo` (linha 1551), que com `True` exige
`despachante.alvos == ["1", None]` **e** texto identico nos dois destinos, e
`test_todo_destino_antigo_atravessa_o_silencio` (linha 1581), que exige
`Categoria.SEMPRE`. Ou seja: o `True` aqui tem que casar com o
`avisar_o_grupo = True` do hunk 2 da Tarefa 3. Escrever `False` numa ponta e
`True` na outra faz um dos dois testes falhar — que e exatamente o servico
desta tabela.

**E o `.` na frente e proposital**, seguindo as dez linhas que ja estao la: a
tabela exercita o parser pelo prefixo legado, que segue aceito e nunca
anunciado.

## Tarefas

<tasks>

<task type="tdd" tdd="true">
  <name>Tarefa 1: a suite, vermelha antes de existir o codigo</name>
  <files>tests/test_desativar_lista_de_presenca.py</files>
  <read_first>
tests/test_desativar_solo_boss.py (o irmao — copiar a forma do cabecalho, das
fixtures, e o estilo de nome de teste), tests/test_presenca.py,
l2scanner/agenda.py (avisos_devidos, RegistroEmDisco, responder_silenciamento),
l2scanner/presenca.py, l2scanner/loot.py.
  </read_first>
  <behavior>
Um arquivo novo, com o mesmo cabecalho-manifesto do irmao: o que este arquivo
prova, e por que cada prova existe. Nenhum relogio e nenhuma fonte
monkeypatchados — o tempo entra por parametro e o disco estragado se produz
apagando a pasta ou criando um diretorio com nome de marcador.

**O TESTE-TITULO, e ele vem primeiro no arquivo (D3):** com a lista desligada,
`avisos_devidos` no instante do `ANTES` continua devolvendo o aviso de
antecedencia do Solo Boss. Se este teste ficar vermelho no fim, a tarefa
falhou inteira, nao importa o resto.

Cobertura minima:

1. **O texto da CHAMADA (D4)** — igualdade exata contra
   `"Solo Boss as 20:00. Quem vai? (/entrar /sair no privado)"`, mais a
   afirmacao de que a palavra `privado` sobreviveu.
2. **Portao (a)** — lista desligada: zero `CHAMADA`; o `ANTES` **sai**; o
   `AGORA` de um evento que o tenha ligado **sai**; outro evento com chamada
   nao e afetado; sem o parametro tudo fica como estava.
3. **Portao (b)** — `/entrar` e `/sair` devolvem o texto de recusa, `grupo` e
   `None`, e **nenhum arquivo `presenca_*` aparece na pasta**; com a lista
   ligada os dois continuam com o comportamento de hoje.
4. **Portao (c)** — `fechar_ocorrencias` com presentes em disco e a lista
   desligada devolve `[]` **e o marcador `fechado_` NAO existe depois**;
   religando, o fechamento ainda acontece.
5. **Portao (d)** — `nick_para_o_aviso` devolve `None`; `responder_designacao`
   recusa e `registro.designacao()` continua o que era; `/loot-` (cancelar)
   continua funcionando.
6. **D3, o historico** — com a lista desligada: `responder_consulta`,
   `responder_correcao` e `responder_atribuicao` respondem igual, e
   `consumir(agora)` no horario do boss ainda grava (fronteira consciente,
   escrita como teste para nao virar surpresa).
7. **Duravel** — `RegistroEmDisco` NOVO sobre a mesma pasta continua vendo o
   desligamento; `podar(hoje=date(2030,1,1))` nao o expira; os dois baldes de
   prefixo continuam disjuntos e o tripwire de introspecao continua verde.
8. **Disco estragado** — nome truncado ignorado; pasta apagada faz
   `listas_desligadas()` devolver vazio, ou seja **a chamada SAI** (direcao
   segura, a lei do `marcar`); escrita que falha nao vira sucesso; religar que
   falha diz que a lista CONTINUA desligada.
9. **Duas instancias** — exatamente uma cria o marcador.
10. **`/status` nas QUATRO combinacoes** da tabela da decisao 4, cada uma com
    a sua asercao de texto.
11. **A resposta que consulta o outro estado** — com o boss falando, a resposta
    promete o lembrete de `{N}` minutos; com o boss calado, ela nao promete e
    aponta o `/ativarsoloboss`.
12. **Comandos** — as quatro palavras e as variantes com hifen/espaco caem nos
    dois membros novos; `/desativar` sozinho nao vira nada; os nicks do roster
    real continuam resolvendo como `/<nick>`; os dois membros novos estao FORA
    de `COMANDOS_DE_MEMBRO` (prova nomeada); `set(_AJUDA) == set(Comando)`
    continua verde.
13. **Os dois lacos obedecem** — o laco principal por comportamento, o
    `--so-agenda` por tripwire de fonte, no mesmo idioma do irmao.
14. **Ponta a ponta por `atender_comandos`**, com as cinco travas ligadas.
  </behavior>
  <action>
Escrever `tests/test_desativar_lista_de_presenca.py` cobrindo os 14 pontos
acima, em portugues sem acento nos identificadores e nos comentarios, com nomes
de teste que descrevem COMPORTAMENTO (o estilo do irmao: `test_com_a_lista_
desligada_o_LEMBRETE_de_10_minutos_continua_saindo`). Reaproveitar as fixtures
do irmao (`SEGUNDA`, `SOLO_BOSS`, `TVT`) em vez de inventar horarios novos, para
os dois arquivos falarem da mesma agenda.

Rodar a suite nova e confirmar que ela esta VERMELHA pelo motivo certo (nome
inexistente / comportamento ausente), e nao por erro de import trivial. Commit
com a suite vermelha, mensagem em portugues no estilo do repo.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; uv run pytest tests/test_desativar_lista_de_presenca.py -q 2&gt;&amp;1 | tail -5   # deve FALHAR: o codigo ainda nao existe</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; uv run pytest -q 2&gt;&amp;1 | tail -3   # baseline do resto: MEDIR e anotar o numero real deste branch</automated>
  </verify>
  <done>
**Os 14 pontos aparecem como TESTES NOMEADOS, e nao como cobertura declarada.**
`uv run pytest tests/test_desativar_lista_de_presenca.py --collect-only -q`
lista, para CADA um dos 14, ao menos um teste cujo nome diz de qual ponto ele
e — um ponto sem teste com nome proprio conta como ponto NAO entregue, mesmo
que alguma asercao solta o toque de raspao. Pontos com varios casos (2, 6, 8,
10, 12) rendem varios testes ou uma classe com varios metodos, nunca um teste
que faz tudo. Motivo: uma lista de 14 itens dentro de um arquivo so e
exatamente onde um plano volta mais fino do que prometeu, e um nome de teste e
a unica coisa que a suite consegue cobrar depois.

O arquivo esta vermelho pelos motivos certos (nome inexistente / comportamento
ausente, nunca `ImportError` trivial), e o numero de baseline da suite inteira
foi MEDIDO neste branch (nao copiado de nenhum enunciado nem do SUMMARY do
irmao) e anotado para a comparacao final.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Tarefa 2: a logica — agenda, presenca, loot e comandos</name>
  <files>l2scanner/agenda.py, l2scanner/presenca.py, l2scanner/loot.py, l2scanner/comandos.py</files>
  <read_first>
As secoes que a Tarefa 1 exercita, ja lidas. Em especial os comentarios de
`PREFIXO_EVENTO_CALADO`, `_PREFIXOS_SEM_DATA`, `calar_evento`,
`responder_silenciamento` e do bloco `DESATIVAR_SOLO_BOSS` no enum — o texto
novo tem que soar como continuacao deles, nao como enxerto.
  </read_first>
  <behavior>
Verde nos 14 pontos da Tarefa 1, e **zero veredito trocado** em qualquer teste
que ja existia.
  </behavior>
  <action>
**`agenda.py`:**

Declarar `PREFIXO_LISTA_DESLIGADA = "lista_desligada_"` com um comentario na voz
da casa explicando (i) que ele nao tem data porque guarda uma DECISAO do
usuario, (ii) que por isso ele entra em `_PREFIXOS_SEM_DATA` e nunca em
`_PREFIXOS_CONHECIDOS`, (iii) que sem isso a poda religaria a lista sozinha em
`DIAS_DE_MARCADOR` sem ninguem mandar, e (iv) que ele e o SEGUNDO morador
daquele balde e por que ele e da mesma familia do `PREFIXO_EVENTO_CALADO`.
Acrescenta-lo a `_PREFIXOS_SEM_DATA`.

Em `RegistroEmDisco`, na secao logo apos os eventos calados: `desligar_lista`,
`religar_lista` e `listas_desligadas`, espelhando `calar_evento`,
`voltar_a_avisar` e `eventos_calados` — mesmo tri-estado, mesmo `O_CREAT|O_EXCL`,
mesmo `unlink`, mesmo descarte de sufixo vazio. As docstrings apontam para as
irmas em vez de repetir o argumento inteiro, e dizem o que e DIFERENTE: aqui a
leitura vazia significa "lista ligada", ou seja **a chamada SAI**, que continua
sendo a direcao segura.

Em `avisos_devidos`: parametro `listas_desligadas` com default vazio e o
`continue` condicionado a `TipoDeAviso.CHAMADA`, colado no teste de
`chamar_minutos_antes <= 0`. Acrescentar a docstring um paragrafo curto
contrastando os DOIS gates: `eventos_calados` mora no laco de evento e alcanca
os tres tipos; `listas_desligadas` mora no laco de tipo e alcanca UM, e a
antecedencia nao pode alcancar essa variavel nem por acidente.

Em `texto_do_aviso`, ramo `CHAMADA`: o texto do D4. Manter e atualizar o
comentario sobre a ingestao de grupo desligada da ponte Baileys, dizendo que a
forma curta ainda carrega a palavra que importa.

Renomear `nomes_calados` para `nomes_dos_eventos` (e atualizar a docstring
explicando por que o nome antigo passou a mentir com o segundo namespace).

`NOME_DO_SOLO_BOSS` ja existe e serve aos dois pares — nao duplicar.

`responder_lista_de_presenca(registro, eventos, nome, desligar, quem)`, na
mesma forma de `responder_silenciamento`: recusa evento fora da agenda, recusa
evento sem `chamar_minutos_antes`, tri-estado nos dois sentidos, e a consulta a
`registro.eventos_calados()` para escolher entre as duas frases do lembrete. Os
textos sao os da secao "Decisao de desenho 6", literais.

**`presenca.py`:** primeiro o **import** — o bloco `from .agenda import (...)`
das linhas 43-50 ganha `apelido_do_evento`, que hoje **nao aparece nenhuma vez
no arquivo** (`grep -c` da zero) e e preciso pelos dois portoes deste modulo.
Depois `_evento_com_lista_desligada(eventos, desligadas)` sobre
`_com_chamada`; `_lista_desligada(nome) -> RespostaDePresenca` com o texto
unico, `grupo=None`; guarda prependido em `responder_join` e `responder_leave`
lendo `registro.listas_desligadas()`; e o `continue` em `fechar_ocorrencias`
antes do `registro.fechar`, com o comentario dizendo que a posicao existe para
nao queimar o marcador — o mesmo argumento que a docstring ja faz para a lista
vazia.

**`loot.py`:** quarta condicao em `nick_para_o_aviso` via
`lista_desligada: bool = False`; recusa em `responder_designacao` via
`lista_desligada: bool = False`, antes de `registro.designar`, com o texto da
decisao 6. Comentario dizendo, por escrito, que `responder_cancelamento`,
`responder_consulta`, `responder_correcao`, `responder_atribuicao` e `consumir`
ficam INTOCADOS por decisao do usuario (D3), e por que cancelar continua livre.

**`comandos.py`:** `DESATIVAR_LISTA` e `ATIVAR_LISTA` no enum, com o bloco de
comentario explicando o recorte (o que cai, o que NAO cai, e que a antecedencia
e o ponto inteiro) e por que os dois ficam fora de `COMANDOS_DE_MEMBRO`; as
quatro palavras no `_VOCABULARIO` com a auditoria de colisao da decisao 5
escrita ali, incluindo a observacao de que o apelido aqui e SINONIMO e nao
abreviacao; e as duas linhas de `_AJUDA` na familia `Silencio`, logo depois das
do `/desativarsoloboss`, com a descricao dizendo que o lembrete de 10 minutos
continua.

Nao tocar em `l2scanner/mercado_*.py`, `l2scanner/identidade.py`,
`l2scanner/acervo.py` nem em `l2scanner/notificador.py`.

**O STRADDLE ENTRE ESTA TAREFA E A SEGUINTE, dito antes de doer.** No instante
em que o enum cresce, aqui, o **terceiro tripwire** (`test_presenca.py`) fica
VERMELHO — ele deriva de `set(Comando)` e os dois membros novos passam a existir
sem linha na `TABELA`. E ele **nao pode ser consertado nesta tarefa**: as linhas
novas da tabela exercitam o ramo de despacho, que so nasce na Tarefa 3. Os tres
testes da `TABELA` (`..._tabela_cobre_...`, `..._destino_de_cada_...`,
`..._todo_destino_antigo_...`) pertencem portanto a Tarefa 3, e o `verify` desta
aqui os desmarca de proposito. **Isto e a unica vermelhidao esperada ao fim da
Tarefa 2. Qualquer outra e regressao.** Nao contornar mexendo no tripwire.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; uv run pytest tests/test_desativar_lista_de_presenca.py tests/test_agenda.py tests/test_loot.py tests/test_comandos.py tests/test_desativar_solo_boss.py -q 2&gt;&amp;1 | tail -5</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; uv run pytest tests/test_presenca.py -q -k "not tabela_cobre and not destino_de_cada and not todo_destino_antigo" 2&gt;&amp;1 | tail -5   # os TRES da TABELA sao da Tarefa 3 — ver a nota do straddle</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; uv run ruff check l2scanner/agenda.py l2scanner/presenca.py l2scanner/loot.py l2scanner/comandos.py</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; grep -n "PREFIXO_LISTA_DESLIGADA" l2scanner/agenda.py | head; grep -n "_PREFIXOS_SEM_DATA = " l2scanner/agenda.py</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; git diff --stat l2scanner/ | tail -6</automated>
  </verify>
  <done>
Os cinco arquivos de teste passam, e `tests/test_presenca.py` passa **exceto os
tres testes da `TABELA`**, que o straddle acima poe na Tarefa 3 — nenhuma outra
vermelhidao e aceita. `tests/test_agenda.py` passou **sem ser editado** (se ele precisou de edicao, o texto do D4 perdeu um dos nove fatos e
isso vira nota no SUMMARY); `PREFIXO_LISTA_DESLIGADA` aparece dentro de
`_PREFIXOS_SEM_DATA` e em nenhum lugar de `_PREFIXOS_CONHECIDOS`; `ruff check`
limpo nos quatro arquivos; nenhum arquivo de `mercado`, `identidade` ou
`acervo` no `git diff --stat`.
  </done>
</task>

<task type="auto">
  <name>Tarefa 3: a costura e a documentacao</name>
  <files>l2scanner/__main__.py, l2scanner/sessao.py, tests/test_desativar_solo_boss.py, tests/test_presenca.py, config.toml, README.md</files>
  <read_first>
`l2scanner/__main__.py` linhas 39-48 (imports da agenda), 1103-1116 (o ramo do
`/desativarsoloboss`), 1301-1322 (`_obedecer_status`), 1600-1615 (o laco da
agenda); `l2scanner/sessao.py` linhas 555-595. Ja lidos; nao reler o arquivo
inteiro. **Ainda nao lido:** `tests/test_presenca.py` linhas 1505-1535 (a
`TABELA` e o comentario que o irmao deixou nela) — ler so essa faixa.
  </read_first>
  <action>
**PRIMEIRO, A CONVERSAO — ela e a unica armadilha de tipo desta tarefa.**
`registro.listas_desligadas()` devolve um **conjunto de apelidos**;
`nick_para_o_aviso` e `responder_designacao` recebem um **`bool`**. Passar o
frozenset direto compila, roda, e fica **truthy sempre que a lista de QUALQUER
evento estiver desligada** — a linha `Loot:` sumiria do TvT tambem, sem erro
nenhum. A expressao e uma so, e e esta:

```python
apelido_do_evento(NOME_DO_SOLO_BOSS) in desligadas
```

Ela aparece em **exatamente tres lugares**, e em nenhum outro:

| Onde | Chamada |
|---|---|
| `sessao.py:583` | `nick_para_o_aviso(aviso, designacao, lista_desligada=...)` |
| `__main__.py:1612` | `nick_para_o_aviso(aviso, designacao, lista_desligada=...)` |
| `__main__.py:1123` | `responder_designacao(..., lista_desligada=...)` |

Nos dois primeiros, `desligadas` e a local do tick (a mesma que ja vai como
`listas_desligadas=` para o `avisos_devidos` logo acima — **uma leitura de
disco por tick, nao duas**). No terceiro, o ramo do `LOOT_DESIGNAR` le
`registro.listas_desligadas()` na hora, porque ali nao existe local de tick.

**`sessao.py`** — o import da linha 47 e `from .loot import Designacao,
nick_para_o_aviso` e nao muda; o da linha **45** (`from .agenda import
avisos_devidos, texto_do_aviso`) **ganha `NOME_DO_SOLO_BOSS` e
`apelido_do_evento`**, que hoje nao existem neste arquivo. Depois: ler o
conjunto UMA vez por tick para uma local, passar como `listas_desligadas=` no
`avisos_devidos` e a expressao acima como `lista_desligada=` no
`nick_para_o_aviso` do mesmo laco. Do disco a cada tick, sem cache: o comando
pode chegar na outra instancia. Nada mais muda — os portoes (b) e (c) leem por
dentro do `registro` e nao aparecem aqui.

**`__main__.py`**, e o toque tem que ser MINIMO porque duas outras sessoes estao
neste arquivo hoje. Exatamente quatro hunks:
  1. imports — no bloco `from .agenda import (...)` (linhas 36-49):
     acrescentar `apelido_do_evento` (**hoje ausente**; `NOME_DO_SOLO_BOSS` ja
     esta la, nao duplicar), mais `responder_lista_de_presenca`, e trocar
     `nomes_calados` por `nomes_dos_eventos`, **sem reordenar a lista**. O
     bloco `from .comandos import ...` ganha os dois membros novos se ele
     importar membros nomeados;
  2. `atender_comandos` — um `elif` novo para o par
     `DESATIVAR_LISTA`/`ATIVAR_LISTA`, inserido logo depois do ramo do
     `/desativarsoloboss`, com `avisar_o_grupo = True` (mesmo racional: o que
     muda e o que o GRUPO recebe daqui pra frente — **e esse `True` tem que
     casar com o `True` das duas linhas novas da `TABELA`**); e no ramo ja
     existente do `LOOT_DESIGNAR` (linha 1123), passar `lista_desligada=` com
     a expressao da tabela acima;
  3. `_obedecer_status` — a parte nova, depois de `avisos DESATIVADOS` e antes
     de `proximo:`, com um comentario dizendo por que as duas chaves aparecem
     separadas (cada uma e desfeita por um comando diferente);
  4. o laco da agenda (`--so-agenda`) — a local lida uma vez, o kwarg
     `listas_desligadas=` no `avisos_devidos` e o kwarg `lista_desligada=` no
     `nick_para_o_aviso` (linha 1612), este ultimo com a expressao da tabela
     acima e **nunca com o conjunto cru**.

Nao reformatar, nao reordenar, nao encostar em linha vizinha. Anotar a contagem
`git diff --stat l2scanner/__main__.py` para o SUMMARY, como o irmao fez.

**DOIS arquivos de teste EXISTENTES sao editados nesta tarefa, e nao um.**

**`tests/test_desativar_solo_boss.py`** — so o rename `nomes_calados` ->
`nomes_dos_eventos` (import na linha 48 e o corpo do teste em 490-498). Nenhuma
asercao muda de valor.

**`tests/test_presenca.py`** — as duas linhas novas no fim da `TABELA` (que
hoje termina em `(".ativarsoloboss", ".ativarsoloboss", True)`, linha ~1529):

```python
(".desativarlista", ".desativarlista", True),
(".ativarlista", ".ativarlista", True),
```

Isto NAO e opcional e NAO e cosmetico: e o **terceiro tripwire** da secao
homonima acima. `test_a_tabela_cobre_todo_comando_ANTIGO_do_enum` deriva
`antigos = set(Comando) - COMANDOS_DE_MEMBRO`, os dois comandos novos caem la
pela decisao 5 deste plano, e sem linha na tabela o teste falha **dizendo o
nome deles**. Estender tambem o comentario que ja esta acima das duas linhas do
`.desativarsoloboss`, dizendo que o par da lista entrou pela mesma pinca e com
o mesmo contrato de destino.

**O que NAO fazer com este tripwire:** nao enfraquece-lo, nao excluir os dois
comandos do conjunto derivado, e nao poe-los em `COMANDOS_DE_MEMBRO` para
escapar dele. O caminho preguicoso aqui e o mesmo que o irmao recusou por
escrito no tripwire de prefixo: o teste ficaria verde e a fronteira de
autorizacao e que pagaria — um party-mate passaria a poder desligar a lista de
presenca da party inteira.

**`config.toml`** — no bloco `[[evento]] Solo Boss`, um paragrafo IRMAO do que
ja termina em "mande /desativarsoloboss", explicando a chave fina e, sobretudo,
**a diferenca entre as duas**: uma cala o boss inteiro, a outra so para de
montar grupo e deixa o lembrete de 10 minutos chegando. Os dois paragrafos
ficam colados, porque confundir as duas e o unico jeito de o usuario desligar a
coisa errada. Acrescentar tambem uma linha no bloco de comentario dos
`[[membro]]`, dizendo que os dois comandos novos NAO sao de membro.

**`README.md`** — duas linhas na tabela de comandos, logo depois das do
`/desativarsoloboss`, e um paragrafo curto abaixo do que ja explica o
`/desativarsoloboss`, com a tabela das quatro combinacoes e a frase que importa:
o aviso de 10 minutos continua chegando. Manter a acentuacao que o README ja
usa (prosa de usuario).

Nao tocar em `.planning/workstreams/mercado/`, `.planning/workstreams/identidade/`,
nem em `ROADMAP.md`.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; uv run pytest tests/test_presenca.py -q -k "tabela or destino or silencio" 2&gt;&amp;1 | tail -5   # os TRES consumidores da TABELA</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; uv run pytest -q 2&gt;&amp;1 | tail -3   # comparar com o baseline MEDIDO na Tarefa 1</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; uv run ruff check l2scanner/__main__.py l2scanner/sessao.py</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; git diff --stat l2scanner/__main__.py</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; git status --short | grep -E "mercado|identidade|acervo|ROADMAP" || echo "nenhum arquivo proibido tocado"</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" &amp;&amp; grep -c "ativarlista" README.md config.toml</automated>
  </verify>
  <done>
A suite inteira verde e MAIOR que o baseline medido na Tarefa 1, com zero
regressao. Em especial os **tres consumidores da `TABELA`** passam com as duas
linhas novas — `test_a_tabela_cobre_todo_comando_ANTIGO_do_enum`,
`test_destino_de_cada_comando_antigo` e
`test_todo_destino_antigo_atravessa_o_silencio` — e nenhum deles foi
enfraquecido para isso (o `git diff` de `tests/test_presenca.py` tem **so
insercoes**: duas linhas de tabela e o comentario estendido, zero delecoes).
`ruff check` limpo nos dois arquivos de costura; o
`git diff --stat l2scanner/__main__.py` cabe em quatro hunks e o numero esta
anotado; `git status` nao lista nada de `mercado`, `identidade`, `acervo` nem
`ROADMAP.md`; README e config.toml citam o par novo.
  </done>
</task>

</tasks>

## Verificacao final

- Suite inteira verde, comparada contra um baseline **medido neste branch** na
  Tarefa 1 — nunca contra um numero herdado de enunciado ou de SUMMARY antigo.
  (O irmao ja pagou esse pedagio: o enunciado dele dizia `1444/2` e o branch
  media `1812/14`.)
- **A prova que manda:** com a lista desligada, o aviso de 10 minutos do Solo
  Boss sai. Se este for o unico teste verde do arquivo, a tarefa ainda cumpriu
  o pedido; se ele for o unico vermelho, nada mais importa.
- **Os tres tripwires derivados verdes sem terem sido enfraquecidos:**
  `set(_AJUDA) == set(Comando)`, a fronteira `set(Comando) -
  COMANDOS_DE_MEMBRO`, e a cobertura da `TABELA` em `test_presenca.py`. O
  `git diff` dos arquivos de teste existentes tem **zero delecoes**.
- `git diff --stat l2scanner/__main__.py` com o numero justificado hunk a hunk
  no SUMMARY.
- Nenhum arquivo de `l2scanner/mercado_*.py`, `l2scanner/identidade.py`,
  `l2scanner/acervo.py`, `l2scanner/notificador.py`,
  `.planning/workstreams/mercado/`, `.planning/workstreams/identidade/` ou
  `ROADMAP.md` no diff.
- Portugues sem acento em identificadores, comentarios e docstrings; README e
  `config.toml` mantem a acentuacao que ja tem.

## O que fica de fora, por escrito

- **O painel do console (`desenhar_status`) nao mostra a lista desligada.** Ele
  mora em `__main__.py`, que esta em disputa de merge hoje. O requisito decidido
  e o `/status`, e ele esta cumprido.
- **Uma designacao anterior continua sendo consumida** no horario do boss,
  gravando em `.loot/`. E D3 obedecido, nao esquecimento — e tem teste.
- **Marcador orfao por renomeacao** de `[[evento]]`: inerte nas duas pontas
  (nao gateia e nao aparece no `/status`), exatamente como o do
  `evento_calado_`.
