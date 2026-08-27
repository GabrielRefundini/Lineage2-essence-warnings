---
phase: quick-260827-e1b
plan: 01
subsystem: comandos
tags: [comandos, whatsapp, presenca, ux, uat]
status: complete
requires:
  - "quick-260827-b82: PREFIXO / PREFIXOS, a barra como prefixo oficial"
provides:
  - "_AJUDA[Comando.JOIN|LEAVE]: o portugues e a sintaxe ANUNCIADA da lista de presenca"
  - "tripwire de APELIDO anunciado pelo caminho real — a prova que so existia para a sintaxe"
affects:
  - l2scanner/comandos.py
  - l2scanner/agenda.py
  - l2scanner/presenca.py
  - l2scanner/__main__.py
  - config.toml
  - README.md
tech-stack:
  added: []
  patterns:
    - "Vitrine (o que o produto ANUNCIA) e vocabulario (o que o parser ACEITA) sao superficies separadas — demover uma forma nunca e apaga-la"
    - "Mensagem operacional de uma linha nomeia UMA acao; superficie de consulta mostra as duas formas, com a principal na frente"
    - "Todo campo anunciado da tabela de ajuda — sintaxe E apelido — volta pelo caminho real de leitura"
key-files:
  created: []
  modified:
    - l2scanner/comandos.py
    - l2scanner/agenda.py
    - l2scanner/presenca.py
    - l2scanner/__main__.py
    - config.toml
    - README.md
    - tests/test_comandos.py
    - tests/test_agenda.py
    - .planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/10-UAT.md
decisions:
  - "D-01: o portugues e o vocabulario ANUNCIADO — a sintaxe das duas linhas de Presenca da _AJUDA."
  - "D-02: os quatro nomes continuam valendo e o ingles fica ANUNCIADO como apelido, nao aceito em silencio. Mais forte que o pedido do gap, e a razao e medida: comando desconhecido morre no `continue` do laco de autorizacao, sem resposta de recusa."
  - "D-03: mensagem operacional de uma linha fala SO portugues; superficie de referencia (_AJUDA, bloco [[membro]], tabela do README) mostra as duas, portugues na frente."
  - "D-04: a tabela do README ganhou as duas linhas de Presenca que nunca entraram la — Deferred Item da quick 260827-b82."
  - "D-05: os itens 3 e 4 do 10-UAT.md voltaram para pendente; os dois julgam TEXTO e o texto mudou."
  - "D-06: os nomes do enum (Comando.JOIN / Comando.LEAVE) NAO mudaram — sao identificadores internos, invisiveis ao usuario."
metrics:
  duration: "~40min"
  completed: 2026-08-27
actuals:
  tokens: 11000
  tasks: 3
  commits: 4
---

# Quick 260827-e1b: O vocabulario oficial da lista de presenca — Summary

O que o produto ANUNCIA para entrar e sair da lista do Solo Boss passou a ser
portugues — `/entrar` e `/sair`. Os quatro nomes continuam aceitos, e as duas
formas inglesas continuam **anunciadas como apelido** na tabela do `/help`.

## O que mudou

**A vitrine inverteu, e so ela.** Na tabela `_AJUDA`, `/entrar` e `/sair`
viraram o campo `sintaxe` das duas linhas de Presenca, e `/join` e `/leave`
desceram para a tupla `apelidos`. `familia` e `descricao` nao foram tocadas —
a familia Presenca continua vindo antes de Loot, que e a ordem do ciclo do
boss e a ordem da resposta.

**O `_VOCABULARIO` nao perdeu uma linha.** As quatro entradas (`join`,
`entrar`, `leave`, `sair`) seguem exatamente como estavam. O `git diff` do
`comandos.py` tem quatro linhas de delecao no arquivo inteiro, e as quatro
sao campos da `_AJUDA`; o portao `git diff -U0 | grep -c '^-.*Comando\.\(JOIN\|LEAVE\),$'`
sai em **0**. O comentario logo acima do bloco passou a registrar o porque:
comando nao reconhecido e descartado no `continue` do laco de autorizacao,
sem resposta de recusa — quem decorou o nome ingles e o digitasse depois de um
corte receberia NADA, indistinguivel do bot ter caido.

**As tres mensagens operacionais falam so portugues** (D-03): a chamada de
1h50 no grupo (`agenda.py`), o erro de disco do registro (`presenca.py`) e as
tres linhas de arranque no console (`__main__.py`). Nas seis ocorrencias so os
tokens de comando mudaram — nenhuma outra palavra de nenhuma frase. Os tres
arquivos saem em **zero** na forma inglesa (eram 2, 1 e 5), enquanto o metodo
de string de juntar lista (10 ocorrencias no `__main__.py`) e os caminhos
`.loot/` e `.env` (13) seguem intactos: nenhum portao desta tarefa usa a forma
com ponto, entao nenhum deles os enxerga.

**As duas superficies de consulta mostram as duas formas**, no mesmo desenho
da `_AJUDA` (`sintaxe (apelido)`): o bloco `[[membro]]` do `config.toml`, com
as duas colunas realinhadas depois da troca, e a tabela do `README.md` — que
tambem **ganhou as duas linhas de Presenca que nunca tinham entrado la**
(D-04, o Deferred Item da quick `260827-b82`), na posicao correspondente a
ordem das familias.

## A lacuna que a tarefa fechou

O planner mediu, antes de planejar, que
`test_toda_sintaxe_anunciada_volta_como_o_comando_certo` percorre **so o campo
`sintaxe`**. Nenhum teste exercitava `apelidos`. No instante em que o ingles
fosse demovido a apelido, ele sairia da cobertura ponta-a-ponta em silencio e
passaria a ser anunciado sem prova nenhuma — o unico defeito real que esta
tarefa podia introduzir.

Tres testes novos, todos pelo caminho REAL (`comandos_novos`, cinco travas
ligadas, sem parser paralelo montado no teste):

1. **A asercao direta** de que a sintaxe das duas linhas de Presenca e a
   portuguesa E de que a inglesa esta entre os apelidos. Os outros tripwires
   da classe sao derivados da tabela de proposito — eles continuariam verdes
   numa reversao silenciosa de vocabulario. Este e o unico que quebra.
2. **Os quatro nomes**, parametrizados sobre `comandos.PREFIXOS`: oito casos,
   escritos uma vez so, de modo que um terceiro prefixo ja nasca provado.
3. **Todo apelido anunciado da tabela inteira**, a generalizacao do teste
   vizinho. A tabela nao tem dois niveis de veracidade, e ate hoje tinha dois
   niveis de prova.

O teste 3 foi rodado ANTES da inversao, de proposito, para ver se algum
apelido ja anunciado estava quebrado: **passou**. Nenhum defeito pre-existente
nos apelidos atuais (`/pt`, `/entrar`, `/sair`, `/ajuda`, `/comandos`).

## O RED foi visto falhar

`test(quick-260827-e1b)` (6d17951) foi commitado com a suite vermelha por
construcao: dos tres testes novos, o item 1 falhou com
`AssertionError: /join / assert '/join' == '/entrar'`, e os itens 2 e 3
passaram ja. `feat(quick-260827-e1b)` (e9dfb27) fez a inversao e fechou o RED.

## Os dois testes que quebraram — e so eles

O plano nomeou os dois com numero de linha, e a medicao estava certa: nenhum
terceiro quebrou.

| Teste | Antes | Depois |
|---|---|---|
| `tests/test_agenda.py` (a chamada do Solo Boss) | `"/join" in texto`, `"/leave" in texto` | as duas positivas em portugues, as duas inglesas viraram NEGATIVAS, e as negativas do prefixo legado ficaram (agora sobre as palavras novas) |
| `tests/test_comandos.py` (a linha de arranque no caplog) | `assert "/join" in caplog.text` | `assert "/entrar" in caplog.text` |

Os dois andaram no **mesmo commit** da mudanca que os quebra (C-05): nunca
houve um commit vermelho no meio da Tarefa 2.

## O UAT da Fase 10

Os itens 3 e 4 voltaram para `[pending]`, com as citacoes **refeitas lendo a
fonte viva** e nao copiadas do plano. Dos seis desfechos do item 4 so o do
erro de disco mudou — os outros cinco foram conferidos, um a um, contra os
f-strings do `presenca.py`, e o portao re-deriva a citacao do item 3 chamando
`texto_do_aviso` em tempo de execucao e comparando caractere a caractere.

O gap 1 passou de `failed` para `resolved`. O `root_cause` ficou — e o
registro de que `/entrar` e `/sair` ja funcionavam e o defeito estava na
vitrine, que e a coisa mais facil de reaprender errado depois. Mas ele foi
reescrito **nomeando as formas demovidas sem o prefixo**: um UAT que ainda
carrega o literal velho e um UAT que ensina a sintaxe velha para quem so bate
o olho, e o portao do plano pede zero ocorrencias no arquivo.

Os itens 1 e 5 tiveram **so o nome do comando** atualizado — sao roteiros de
teste de campo, e deixa-los mandando a pessoa digitar a forma demovida seria
validar o produto errado. O veredito deles nao mudou: seguem bloqueados em
campo. Summary refeito: `total 6 / passed 1 / issues 0 / pending 5`.

## O `/help` como sai hoje

```
Comandos do scanner — sempre com barra (/) na frente:

Vigilancia:
  /status — Digo se estou vigiando ou calado, e qual o proximo evento
  /solo — Vigio so o seu personagem e paro de reclamar de party
  /party (/pt) — Volto a vigiar a party inteira

Silencio:
  /cancelar — Tira o silencio de TvT/Prime que estiver rolando

Presenca:
  /entrar (/join) — Entro na lista do proximo Solo Boss
  /sair (/leave) — Saio da lista do proximo Solo Boss

Loot do Solo Boss:
  /loot-<nick> — Marca quem pega o loot do proximo boss
  /loot- — Desmarca: o proximo boss volta a ser de ninguem
  /<nick> — Quantos loots o char ja pegou, e quando foi o ultimo
  /corrigir-<nick> — Troca o dono do ultimo loot ja registrado
  /pegou <hora> <nick> — Registra loot de um boss que ja passou (ex.: 18:00 Korzis)

Ajuda:
  /help (/ajuda, /comandos) — Esta lista
```

E a chamada que vai para o grupo:

```
Solo Boss as 20:00. Quem vai? Mande /entrar no PRIVADO do bot para entrar na lista, ou /sair para sair. Aqui no grupo o bot nao le comando.
```

## Verificacao

| Portao | Resultado |
|---|---|
| Suite antes | **1121 passed, 2 skipped** (o piso real medido pelo planner; o 1077 do briefing era o piso ANTES da quick b82) |
| Suite depois | **1125 passed, 2 skipped** (+4 testes; nenhum trocado) |
| Delecao no bloco do `_VOCABULARIO` | 0 |
| Forma inglesa em `agenda.py` / `presenca.py` / `__main__.py` | 0 / 0 / 0 |
| `.join(` e `.loot/` `.env` no `__main__.py` | 10 e 13 — intactos |
| `pyproject.toml` no diff | ausente (C-01) |
| `autorizado_para` / `COMANDOS_DE_MEMBRO` no diff | vazio (C-02, T-e1b-03) |
| `ruff check` nos arquivos tocados | limpo |
| Forma inglesa no `10-UAT.md` | 0 |
| Citacao do item 3 contra a fonte viva | bate caractere a caractere |

## Deviations from Plan

Nenhuma. As duas unicas divergencias do plano sao ampliacoes que ele mesmo
pediu ao mandar decidir:

1. **O gate do UAT contra os itens 1 e 5.** O plano dizia "nao tocar nos itens
   1, 2, 5 e 6" e ao mesmo tempo pedia zero ocorrencias da forma inglesa no
   arquivo. Os dois so convivem se "nao tocar" for lido como "nao mexer no
   veredito" — que e o que foi feito: os itens 1 e 5 tiveram so o token de
   comando atualizado e continuam `[pending] / blocked_by: third-party`.
2. **O `root_cause` e o `missing` do gap escritos sem prefixo.** Mesma tensao,
   mesma solucao, e a mesma disciplina que o plano ja impunha aos comentarios
   de codigo: o registro historico fica, o literal demovido sai.

Nenhuma Rule 1-4 disparou. Nenhum defeito pre-existente encontrado.

## Notas de execucao

`ruff format --check` ja reprovava `tests/test_comandos.py` **antes** de
qualquer mudanca desta tarefa (conferido rodando o check contra o arquivo
limpo). Nao foi rodado `ruff format`, pelo mesmo motivo registrado na quick
`260826-vtt`: reformatar o arquivo inteiro afogaria o diff da tarefa.

## Self-Check: PASSED

Arquivos e commits conferidos por `git log` e por leitura em disco:
`6d17951` (RED), `e9dfb27` (GREEN), `3397668` (mensagens + os dois testes),
`2dcb05e` (UAT). Nenhum `git add -A` — todos os commits foram montados por
caminho explicito e conferidos com `git show --name-only`; `.gsd/` continua
untracked e fora de todos eles.
