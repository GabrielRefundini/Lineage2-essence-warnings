---
task: 260830-ars
workstream: default
title: /desativarsoloboss e /ativarsoloboss — o boss cala inteiro, e o /status conta
type: quick
requirements: []
---

# /desativarsoloboss e /ativarsoloboss

## Objetivo

Dois comandos novos que desligam e religam **todos** os avisos do evento
`Solo Boss` do `config.toml` — a chamada de `chamar_minutos_antes = 110` E o
lembrete de `avisar_minutos_antes = 10`, juntos, nunca um sem o outro. O
estado **sobrevive a reiniciar o `vigiar-party.bat`**, e o `/status` **diz**
quando esta desligado.

Meia-mudez e pior que qualquer um dos dois extremos: a chamada sem o lembrete
convida a party para um boss que ninguem lembra de ir; o lembrete sem a
chamada avisa 10 minutos antes uma party que nunca foi consultada. Por isso o
gate e por EVENTO, e nao por tipo de aviso — nao existe sintaxe para calar
metade.

## Decisoes do usuario (nao sao julgamento meu)

1. O estado PERSISTE em disco. Reiniciar nao religa. Nao expira sozinho.
2. O `/status` REVELA o desligamento. Um off-switch persistido que o `/status`
   nao mostra e exatamente o modo de falha de estado escondido que este repo
   combate em todo lugar.

## Decisao de desenho 1 — onde o estado mora

**Escolhido: o marcador `O_CREAT | O_EXCL` do `agenda.RegistroEmDisco`**
(`agenda.py:295-410`), namespace novo `evento_calado_<apelido>`.
**Recusado: o `os.replace` de JSON do `loot.py:260-305`.**

O contra-argumento estava no enunciado e e serio: isto e uma FLAG MUTAVEL DE
DOIS ESTADOS, e nao um fato que se acumula — e o marcador nasceu para fatos
que so crescem ("ja avisei", "ja cancelei"). Ele cai por tres razoes medidas:

- **A lista de presenca ja e uma flag de dois estados no mesmo namespace.**
  `entrar` cria o arquivo, `sair` faz `unlink` (`agenda.py:445-495`). Ligar e
  desligar por criar/apagar arquivo nao e uma quarta invencao: e o quarto uso
  do mesmo idioma, e o terceiro que apaga.
- **Nao ha read-check-write para o `O_EXCL` fechar — e nao ha nenhum para o
  JSON abrir.** O usuario roda duas instancias (Yazalaque e Faerlina). Com o
  marcador, `desativar` e uma criacao atomica e `ativar` e um `unlink`
  atomico: as duas instancias podem executar em qualquer ordem e o resultado
  e sempre um dos dois estados validos. Com um JSON por evento, duas
  instancias escrevendo eventos diferentes no mesmo arquivo se atropelam — o
  `os.replace` e atomico para o ARQUIVO, nao para o mapa dentro dele.
- **A direcao da falha ja esta certa de graca.** `enviados()` devolve conjunto
  vazio em `OSError` (`agenda.py:365`), entao disco ilegivel = nenhum evento
  calado = **o aviso sai**. E a lei escrita do `marcar`: "preferir o aviso
  duplicado ao aviso perdido — a party ignora uma repeticao, mas nao adivinha
  um boss que ninguem anunciou". Um JSON ilegivel exigiria escolher essa
  direcao a mao, e escolher errado e silenciar o boss por causa de um disco
  travado.

O JSON do `loot.py` existe porque loot carrega DADO ESTRUTURADO (nick, alvo,
carimbo). Uma flag nao carrega nada — serializar um booleano e o unico caso em
que o formato e puro custo.

**O marcador NAO entra em `_PREFIXOS_CONHECIDOS`, e isso e deliberado.** Aquela
tupla existe para a poda saber ler a data do nome; este marcador NAO TEM data,
porque nao pode expirar — a decisao 1 do usuario e explicitamente contra
expiracao automatica. A poda ja ignora o que nao sabe datar
(`except ValueError: continue`), entao a imortalidade sai de graca. Isso vira
teste: `podar(hoje=2030-01-01)` nao pode apaga-lo.

## Decisao de desenho 2 — onde a supressao morde

**No momento de AVISAR, em `avisos_devidos`** — e nao removendo o evento da
agenda.

`avisos_devidos` e o funil unico dos tres tipos (`ANTES`, `AGORA`, `CHAMADA`),
entao um filtro la cala os tres de uma vez e nao ha como calar metade. Tirar o
evento da lista quebraria `proxima_ocorrencia` (o console deixaria de saber
que o boss existe), `ocorrencias_do_dia` (o encaixe do `.pegou`) e a lista de
presenca — machinery que o usuario nao pediu para desligar.

Ganha um parametro `eventos_calados: frozenset[str] = frozenset()`. Default
vazio: toda chamada existente e todo teste continuam byte a byte como estao.

**FRONTEIRA EXPLICITA:** o FECHAMENTO da lista de presenca
(`presenca.fechar_e_narrar`) NAO passa por `avisos_devidos` (D-12) e **nao e
calado por este comando**. Nao e esquecimento: o usuario nomeou dois avisos, e
o fechamento nao e nenhum deles — ele e o desfecho de uma lista que alguem
montou a mao. Na pratica ele fica quieto sozinho: sem a chamada, ninguem da
`/entrar`, e `fechar_e_narrar` pula ocorrencia sem presentes.

## Decisao de desenho 3 — quem pode mandar

**Nivel de DONO. Fora de `COMANDOS_DE_MEMBRO`.**

Um `/entrar` de party-mate mexe numa linha da lista de UMA ocorrencia e o
efeito e visivel para quem digitou. `/desativarsoloboss` apaga 12 chamadas por
dia para a party INTEIRA, por tempo indeterminado, e o efeito e a AUSENCIA de
mensagem — indistinguivel, do lado de quem espera, do bot ter caido. Na duvida
o enunciado manda ficar no nivel mais restritivo; aqui nem ha duvida.

## Decisao de desenho 4 — geral no armazenamento, especifico no comando

A chave em disco e o apelido do evento (`evento_calado_solo-boss`), o gate le
um conjunto de apelidos, e o responder recebe o nome do evento. Tudo isso e
generico e nao custa uma linha a mais que uma flag so de Solo Boss.

**Mas o enum ganha exatamente DOIS membros**, os que o usuario pediu. A
docstring do `Comando` e explicita: "a lista curta nao e falta de imaginacao —
e o limite do estrago possivel". Comando para calar TvT ou Prime ninguem
pediu.

## Tarefas

1. `test(quick-260830-ars)`: os testes, vermelhos antes de existir o codigo —
   gate dos dois avisos, restart, poda, `/status`, disco corrompido,
   fronteira de autorizacao, e o vocabulario fechado crescendo de proposito.
2. `feat(quick-260830-ars)`: `agenda.py` — `apelido_do_evento`,
   `PREFIXO_EVENTO_CALADO`, `calar_evento`/`voltar_a_avisar`/`eventos_calados`,
   o parametro de `avisos_devidos`, `nomes_calados`, `responder_silenciamento`.
3. `feat(quick-260830-ars)`: `comandos.py` — dois membros no enum, o
   vocabulario e as duas linhas de `_AJUDA`.
4. `feat(quick-260830-ars)`: a costura — `sessao.py` (1 linha) e `__main__.py`
   (import, o kwarg no laco da agenda, o ramo de despacho, o `/status`).

## Verificacao

- Suite inteira verde, sem regressao do `1444 passed, 2 skipped`.
- `git diff --stat l2scanner/__main__.py` com o numero justificado no SUMMARY.
- Nenhum arquivo de `.planning/workstreams/mercado/`, `discord/`,
  `.planning/research/` ou `l2scanner/notificador.py` tocado.
