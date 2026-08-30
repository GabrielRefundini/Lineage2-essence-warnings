---
task: 260830-ars
workstream: default
title: /desativarsoloboss e /ativarsoloboss — o boss cala inteiro, e o /status conta
status: complete
completed: 2026-08-30
subsystem: agenda + comandos
tags: [agenda, comandos, persistencia, solo-boss, estado-visivel]
key-files:
  created:
    - tests/test_desativar_solo_boss.py
  modified:
    - l2scanner/agenda.py
    - l2scanner/comandos.py
    - l2scanner/sessao.py
    - l2scanner/__main__.py
    - tests/test_agenda.py
    - tests/test_comandos.py
    - tests/test_presenca.py
    - README.md
    - config.toml
metrics:
  suite_antes: "1812 passed, 14 skipped (medido em d2cc8b4)"
  suite_depois: "1863 passed, 14 skipped"
  testes_novos: 51
  linhas_em_main: "27 insercoes, 1 delecao"
actuals:
  commits: 7
---

# Quick 260830-ars: /desativarsoloboss e /ativarsoloboss

**Os dois avisos do Solo Boss desligam juntos, por comando do WhatsApp, e o
desligamento sobrevive a fechar o `vigiar-party.bat` — com o `/status`
contando enquanto durar.**

## O que foi construido

| Comando | O que faz |
|---|---|
| `/desativarsoloboss` (`/desativarboss`) | Desliga a chamada de 110 min E o lembrete de 10 min, juntos |
| `/ativarsoloboss` (`/ativarboss`) | Religa os dois |

`/desativar-solo-boss` e `/desativar boss` chegam de graca: `interpretar` ja
tira hifens do miolo e junta as duas primeiras palavras. `/desativar` sozinho
NAO faz nada, de proposito — mesma disciplina do D-02 no `.loot`: comando sem
argumento nao pode mexer em estado duravel.

O `/status` passou a responder, enquanto durar:

```
Scanner: Vigiando normalmente, avisos DESATIVADOS de Solo Boss,
         proximo: Solo Boss as 18:00.
```

E a resposta do proprio comando diz o que caiu, com os minutos lidos do
`config.toml` e nao de um literal:

```
Yazalaque desativou os avisos do Solo Boss: nem a chamada de 110 minutos
antes, nem o lembrete de 10 minutos antes. Nada disso volta sozinho — nem
reiniciando o scanner. Mande /ativarsoloboss para religar tudo de uma vez.
```

## Onde o estado mora, e por que esse idioma

**`.agenda/evento_calado_solo-boss`** — um arquivo vazio, criado com
`O_CREAT | O_EXCL` e apagado com `unlink`. O mesmo idioma do
`RegistroEmDisco`, e nao o `os.replace` de JSON do `loot.py`.

O contra-argumento e real e estava no enunciado: isto e uma **flag mutavel de
dois estados**, e o marcador nasceu para fatos que so se acumulam. Ele perde
por tres razoes:

1. **A lista de presenca ja e uma flag de dois estados no mesmo diretorio.**
   `entrar` cria o arquivo, `sair` apaga. Ligar/desligar por criar/apagar
   arquivo nao e uma terceira invencao — e o quarto uso do mesmo idioma, e o
   segundo que apaga.
2. **Nao ha read-check-write para dar errado.** O usuario roda duas instancias
   (Yazalaque e Faerlina) sobre a mesma pasta. Desligar e uma criacao atomica,
   religar e um `unlink` atomico: em qualquer intercalacao o disco termina num
   dos dois estados validos, e exatamente uma instancia anuncia no grupo. Um
   mapa JSON de eventos calados teria que ser lido, alterado e reescrito, e a
   instancia que escrevesse por ultimo apagaria a decisao da outra — o
   `os.replace` e atomico para o ARQUIVO, nao para o mapa dentro dele.
3. **A direcao da falha de leitura ja vem certa.** `enviados()` devolve vazio
   em `OSError`, entao disco ilegivel = nenhum evento calado = **o aviso
   sai**. E a lei escrita no `marcar`: preferir o duplicado ao perdido, porque
   a party ignora uma repeticao e nao adivinha um boss que ninguem anunciou.
   Com JSON essa direcao teria que ser escolhida a mao, e escolher errado e
   silenciar o boss por causa de um disco travado.

O JSON do `loot.py` existe porque loot carrega **dado estruturado** (nick,
alvo, carimbo). Uma flag nao carrega nada.

**O marcador NAO tem data, e isso e a funcionalidade.** `podar` roda no
construtor, ou seja, a cada arranque; um marcador datado religaria o boss
sozinho em 3 dias, contra a decisao explicita do usuario. A poda ja ignora o
que nao sabe datar, entao a imortalidade sai de graca — mas ela e
**deliberada**, e `test_a_poda_nao_expira_o_desligamento` a prova com
`podar(hoje=2030-01-01)`.

### O tripwire de prefixo, e por que ele nao foi enfraquecido

`TestPodaAlcancaTodosOsPrefixos` derivava por introspecao: todo `PREFIXO_*` do
modulo tem que estar em `_PREFIXOS_CONHECIDOS`, senao "nasce imortal em
silencio". O caminho preguicoso seria por o prefixo novo la e deixar a poda
come-lo em 3 dias — o teste ficaria verde e o boss religaria sozinho.

Em vez disso o modulo passou a declarar **dois baldes**:
`_PREFIXOS_CONHECIDOS` (tem data, a poda alcanca) e `_PREFIXOS_SEM_DATA` (nao
expira nunca, por decisao). Todo prefixo futuro continua obrigado a escolher
um deles por escrito, e continua quebrando o teste enquanto nao escolher.
Ganhou de quebra um teste novo afirmando que os dois baldes **nao se
sobrepoem** — um prefixo nos dois seria a poda contradizendo a decisao com o
tripwire verde.

## Onde a supressao morde

**No funil de `avisos_devidos`**, que e onde `ANTES`, `AGORA` e `CHAMADA`
nascem na mesma lista de candidatos. Consequencias:

- **Nao existe sintaxe que cale metade.** Um `TipoDeAviso` futuro nasce calado
  junto, sem ninguem precisar lembrar disso.
- **A agenda nao encolhe.** `proxima_ocorrencia` continua sabendo que o boss
  existe (o `/status` acima ainda diz "proximo: Solo Boss as 18:00"),
  `ocorrencias_do_dia` continua servindo ao encaixe do `.pegou`, e a lista de
  presenca continua funcionando. O usuario pediu para calar avisos, nao para o
  boss deixar de existir.

O parametro nasce com default vazio, entao toda chamada que nao o conhece se
comporta byte a byte como antes.

**Os DOIS lacos obedecem.** `vigiar-party.bat` (via `sessao`) e
`avisos-tvt.bat` (`--so-agenda`) leem a mesma pasta e falam no mesmo grupo;
calar so um faria o boss ficar quieto num modo e falante no outro. O laco
principal tem teste de comportamento; o `--so-agenda` (um `while True` com
rede dentro) tem tripwire de fonte, o mesmo idioma que o repo ja usa para o
relogio monotonico.

O `sessao` le os calados **do disco a cada tick**, sem cache: o comando pode
chegar na outra instancia.

## Fronteira explicita: o que NAO foi calado

O **fechamento da lista de presenca** (`presenca.fechar_e_narrar`) nao passa
por `avisos_devidos` (D-12) e continua saindo. Nao e esquecimento: o usuario
nomeou dois avisos, e o fechamento nao e nenhum deles — ele e o desfecho de
uma lista que alguem montou a mao. Na pratica ele fica quieto sozinho: sem a
chamada ninguem da `/entrar`, e `fechar_e_narrar` pula ocorrencia sem
presentes.

## Autorizacao: nivel de DONO

Os dois ficaram **fora** de `COMANDOS_DE_MEMBRO`. Um `/entrar` de party-mate
mexe numa linha da lista de UMA ocorrencia e quem digitou ve o efeito. Isto
apaga 12 chamadas por dia da party INTEIRA, por tempo indeterminado, e o
efeito e a **ausencia** de mensagem — do lado dos outros quatro a oito
party-mates, indistinguivel do bot ter caido. Nao e um `/entrar` maior; e
outra categoria de estrago.

O tripwire derivado (`set(Comando) - COMANDOS_DE_MEMBRO`) ja recusaria os dois
sozinho. Foi escrita **tambem** uma prova nomeada, porque a razao deste par
ficar de fora e diferente da dos outros, e razao que so vive em comentario nao
sobrevive ao proximo ajuste.

## Generalizacao: geral no armazenamento, especifico na superficie

A chave em disco e o apelido do evento, o gate le um conjunto de apelidos e o
responder recebe o nome — tudo generico, e sem custar uma linha a mais. **O
enum ganhou exatamente os dois membros pedidos.** Um `/avisos <evento> off`
alcancaria TvT e Prime, que ninguem pediu, e a docstring do enum e explicita:
"a lista curta nao e falta de imaginacao — e o limite do estrago possivel".

De quebra, `apelido_do_evento` virou uma funcao so: a mesma expressao estava
escrita duas vezes (`Aviso.chave` e `chave_da_ocorrencia`) e agora tem tres
consumidores. Divergirem seria invisivel — o gate procuraria um apelido que a
agenda nunca escreve, sem excecao nenhuma, e o boss continuaria falando depois
de desligado.

## O toque em `__main__.py`

**27 insercoes, 1 delecao** (`git diff --stat` mostra `28 +++-`), em 4 hunks:

| Hunk | Linhas | O que |
|---|---|---|
| import | +3 | tres nomes acrescentados a lista existente, sem reordenar nada |
| `atender_comandos` | +13 | um ramo `elif` novo, inserido entre dois ramos existentes |
| `_obedecer_status` | +7 | seis linhas, sem mudar a assinatura |
| `laco_da_agenda` | +4/-1 | **a unica linha modificada do arquivo** — a chamada de `avisos_devidos` ganhou o kwarg e quebrou em quatro linhas |

Nenhuma reformatacao, nenhuma reordenacao, nenhuma linha vizinha tocada. Das
27 insercoes, 14 sao comentario. Toda a logica mora em `agenda.py` (+314) e
`comandos.py` (+65), que a sessao do `mercado` nao toca ha 10+ commits;
`sessao.py` levou +9/-1, tambem so um kwarg.

## Desvio (Rule 1): a frase que sugeria meia-mudez

A primeira versao respondia **"nem a chamada de 110 minutos antes, o lembrete
de 10 minutos antes"** — sem o segundo "nem". Le-se como se so a chamada
tivesse caido, que e exatamente a leitura que esta funcionalidade nao pode
produzir: numa regra de tudo-ou-nada, a frase que sugere metade e defeito de
produto, nao de redacao. Achado rodando o caminho de verdade contra o
`config.toml` do repositorio, depois de a suite estar verde — nenhum teste
olhava a conjuncao.

Conserto: `_o_que_o_evento_anuncia` devolve as **partes** e cada resposta poe
a propria cauda (`", nem "` num sentido, `" e "` no outro), porque uma frase
so leria errado num dos dois sentidos, sempre. Duas asercoes novas travam as
duas conjuncoes, mais uma para o evento de um aviso so (o `config.toml`
convida a apagar a linha `chamar_minutos_antes`).

Commit `12dfc07`.

## Verificacao

| Prova | Onde |
|---|---|
| Os dois avisos caem juntos, e o terceiro tipo tambem | `TestOGateCalaOsDoisAvisos` |
| O dia real do `config.toml` cai de 36 para 12 mensagens (numeros escritos a mao) | `TestNaAgendaRealDoRepositorio` |
| Reiniciar nao religa (objeto novo, mesma pasta) | `test_reiniciar_o_scanner_NAO_religa` |
| A poda de 2030 nao expira o desligamento | `test_a_poda_nao_expira_o_desligamento` |
| Duas instancias competindo: exatamente uma desativa | `test_duas_instancias_competindo_so_uma_desativa` |
| Escrita que falha nao vira sucesso (pasta apagada de verdade) | `test_a_escrita_que_falha_NAO_vira_sucesso` |
| Religar que falha diz que o boss CONTINUA calado (diretorio no lugar do marcador) | `test_religar_que_falha_diz_que_o_boss_CONTINUA_calado` |
| Nome truncado / lixo / pasta sumindo nao derrubam a leitura, e o aviso SAI | `TestDiscoEstragado` |
| O `/status` conta, e continua contando depois do restart | `TestOStatusRevela` |
| Os dois lacos obedecem | `TestOsDoisLacosObedecem` |
| Ponta a ponta por `atender_comandos`, com as cinco travas | `TestNaCostura` |
| Party-mate nao alcanca nenhum dos dois | `test_o_party_mate_NAO_cala_o_boss_da_party_inteira` |

**Nenhum relogio e nenhuma fonte foram monkeypatchados** — o tempo entra por
parametro e os casos de disco estragado sao produzidos apagando a pasta ou
criando um diretorio com nome de marcador.

**Suite: 1812 passed, 14 skipped (medido em `d2cc8b4`) -> 1863 passed, 14
skipped.** +51 testes, zero regressoes.

> **Nota sobre o numero da tarefa.** O enunciado citava `1444 passed, 2
> skipped`. Esse numero nao corresponde a este branch: o baseline foi
> **medido** exportando `d2cc8b4` para uma pasta limpa e rodando a suite la,
> dando `1812 passed, 14 skipped`. Reportar contra o numero do enunciado teria
> escondido 368 testes.

`ruff check` limpo nos arquivos tocados. Os 3 `F401` que o repo tem sao
pre-existentes e vivem em arquivos fora do escopo (`test_calibrar_mercado_bat`,
`test_navegador_de_frames`, `test_voce_na_party`).

## Restricoes respeitadas

- `l2scanner/notificador.py` — **nao tocado**.
- `.planning/workstreams/mercado/`, `discord/`, `.planning/research/` — **nao
  tocados**.
- Portugues sem acento em identificadores, comentarios e docstrings. README e
  `config.toml` mantiveram a acentuacao que ja tinham (prosa de usuario).

## O que ficou de fora, por escrito

- **O painel do console (`desenhar_status`) nao mostra o desligamento.** Ele
  mora em `__main__.py`, e a restricao de contencao de merge era explicita. O
  requisito decidido era o `/status`, e ele esta cumprido. Se o usuario quiser
  a linha no painel tambem, e uma linha — mas ela custa mais um hunk num
  arquivo em disputa, e nao valia hoje.
- **O eco no grupo sai mesmo quando nada mudou** ("ja estavam desativados").
  E a convencao ja existente do `.cancelar`, que tambem ecoa o no-op. Trocar
  isso mudaria o contrato de destino de um comando antigo junto com o novo.
- **Marcador orfao por renomeacao.** Se o usuario renomear o bloco
  `[[evento]]` depois de ter desligado, o marcador antigo fica inerte: nao
  cala nada (o gate compara com os eventos configurados) e nao aparece no
  `/status`. O comando ja **recusa** criar marcador para evento fora da
  agenda, entao esse estado so nasce de uma edicao posterior do
  `config.toml`.

## Commits

| Hash | Mensagem |
|---|---|
| `3ce2f40` | docs: o plano, com as quatro decisoes de desenho |
| `e36dd00` | test: o boss calado inteiro, afirmado antes de existir |
| `d4cf458` | feat: a agenda sabe calar um evento inteiro, e por que |
| `1b33bdc` | feat: o enum cresce dois, e nenhum deles e de membro |
| `04793d1` | feat: a costura — os dois lacos calam juntos e o /status conta |
| `44a054c` | docs: os dois comandos no README e no config.toml |
| `12dfc07` | fix: o segundo "nem" — a frase sugeria meia-mudez |

## Self-Check: PASSED

- `tests/test_desativar_solo_boss.py` — FOUND
- `.planning/workstreams/default/quick/260830-ars-desativar-solo-boss/PLAN.md` — FOUND
- Commits `3ce2f40 e36dd00 d4cf458 1b33bdc 04793d1 44a054c 12dfc07` — FOUND
