---
phase: 02-dashboard-calculadora-de-rotas
plan: 04
subsystem: dashboard
tags: [calc-05, generalidade, cinco-elos, controle-negativo, gate-de-escopo, prova-de-mutacao]
status: complete

requires:
  - "02-01: o bloco `calculadora` no payload, a quarta regiao, o molde da linha"
  - "02-02: `NOME_DO_TERCEIRO`, `NOMES_DO_ROADMAP`, `_so_o_codigo_python` e `_nomes_de_item_no_codigo` — a sonda de literal e as constantes de quem e o terceiro"
  - "02-03: `propriedades_do_item_consumidas`, `vaos_escritos_pela_pintura`, `vaos_de`, `caminho_existe`, `molde_da_linha` — os extratores de tela"
  - "01-08 / 01-VERIFICATION.md: o registro de que o elo de leitura de fonte passa por VACUIDADE sem controle negativo"
provides:
  - "tests/test_dashboard_rotas_generica.py: 53 testes — os cinco elos do CALC-05, o elo transversal e os tres gates de escopo"
  - "a sonda de literal de nome de item estendida ao `dashboard.js` e ao `dashboard.css` (ate aqui varria so os dois modulos Python)"
  - "`nomes_de_item_no_texto`: a sonda que recebe a lista de procurados e a limpeza, e por isso alcanca as tres linguagens"
  - "o elo da CONFIGURACAO: do `config.toml` em disco, e nao de um `ItemDeRota` montado a mao"
  - "o gate de DIRECAO da dependencia: a cerca dura do workstream `mercado` nao conhece o dashboard"
affects: []

tech-stack:
  added: []
  patterns:
    - "prova de generalidade por INSTANCIACAO, com o controle que discrimina em cada elo"
    - "a lista de procurados de uma sonda sai da CONFIGURACAO DE TESTE, e nunca de nomes escritos no arquivo de teste"
    - "chave de serie DERIVADA da funcao de producao (`chave_da_serie`), e nunca digitada"
    - "invariancia por RENOMEACAO como controle de mecanismo — mais forte que a ausencia de literal"
    - "gate de escopo medindo a DIRECAO da dependencia quando o git nao pode ser consultado"

key-files:
  created:
    - tests/test_dashboard_rotas_generica.py
  modified: []

decisions:
  - "ZERO arquivo de producao alterado — a generalidade EXISTIA, e nao precisou de uma linha"
  - "o terceiro item e o `NOME_DO_TERCEIRO` do 02-02, importado: uma autoridade so sobre quem e o terceiro"
  - "a sonda nova recebe lista e limpeza por parametro em vez de duplicar a do 02-02, e ha teste medindo que as duas CONCORDAM onde os dominios se sobrepoem"
  - "o gate 1 mede a DIRECAO da dependencia, e nao o diff: a branch e compartilhada e o diff cru acusa outros workstreams"
  - "a atribuicao por commit dos sete arquivos da cerca fica no SUMMARY, com a saida — nao cabe em teste sem git"

metrics:
  duration: "~1h30"
  completed: 2026-09-04

actuals:
  tokens: 14298
  tasks: 2
  commits: 3
---

# Phase 2 Plan 04: A prova de que a calculadora e generica — Summary

O CALC-05 esta fechado, e **o desfecho e o bom**: um terceiro item que o codigo
nunca viu atravessa a configuracao, o calculo, o payload, o servidor e os vaos da
marcacao produzindo um veredito de forma identica a dos dois primeiros — e
**nenhuma linha de codigo de producao foi escrita para isso acontecer**. Os dois
commits deste plano tocam **um arquivo**, e ele e de teste.

## A regra que definia este plano, e como ela terminou

O plano proibia tocar em arquivo de producao, e a razao nao era burocracia: era a
medicao. Se o terceiro item exigisse uma linha la, o desfecho honesto seria
registrar que a generalidade nao existia, e nao remendar o codigo dentro do plano
que o audita.

**Nao exigiu.** A cerca (`l2scanner/**` + `config.toml` + `requirements.txt`)
esta intacta, medida por `git diff --name-only` dos dois commits:

```
$ git diff --name-only fc5caf2..HEAD
tests/test_dashboard_rotas_generica.py
```

## O que este plano encontrou e que muda o mapa: o 02-02 ja tinha aberto o CALC-05

O plano assumia um arquivo novo com cinco elos. **Ao ler a arvore, metade do
elo 2 e todo o elo transversal do lado Python ja existiam**, em
`tests/test_dashboard_rotas.py`: `NOME_DO_TERCEIRO`, `_so_o_codigo_python`,
`_nomes_de_item_no_codigo` e a classe `TestAContaNaoConheceNomeDeItem`, com os
dois controles.

Escrever de novo teria criado exatamente as duas autoridades que esta arvore ja
pagou para nao ter. **Foram importadas**, e este arquivo ESTENDE:

| elo | existia no 02-02? | o que este plano acrescentou |
|---|---|---|
| 1 — configuracao | nao | do `config.toml` em disco por `ler_itens_de_rota`, e nao de um `ItemDeRota` montado a mao |
| 2 — calculo | parcialmente | invariancia por RENOMEACAO, vencedoras diferentes entre si, controle sobre a comparacao |
| 3 — payload | nao (so `_linha_da_rota`, a funcao privada) | o `payload` inteiro, com comparacao PROFUNDA de caminhos |
| 4 — servidor | nao | `GET /dados` num soquete real, campo a campo contra o `payload` |
| 5 — tela | nao | as propriedades que a pintura le, existindo nas TRES entradas |
| transversal | so os 2 modulos Python | **`dashboard.js` e `dashboard.css`** — a outra metade do que o CALC-05 proibe |

A extensao do transversal e a peca que faltava de verdade: o requisito diz "sem
codigo novo de calculo **nem de tela**", e ate este plano a metade da tela nao
tinha sonda nenhuma.

## As cinco provas de mutacao — e as cinco ficaram vermelhas

Nenhum verde foi assumido. Cada mutacao foi aplicada num arquivo de producao,
medida, e **REVERTIDA**; a arvore volta a 53 passed e o `git status` sai limpo.

| Mutacao na linha de producao | Resultado |
|---|---|
| um `if item.nome == <1o>` em `vereditos_das_rotas` | **1 falha**, a sonda de literal sobre `dashboard_rotas.py` |
| um `if (item.nome_exibido === <2o>)` em `dashboard.js` | **1 falha**, a sonda sobre `dashboard.js` — **cobertura que nao existia antes deste plano** |
| um seletor `[data-item="<3o>"]` no `dashboard.css` | **2 falhas**: a sonda sobre o CSS, e a varredura da arvore atras do nome do terceiro |
| `ler_itens_de_rota` truncando em `brutos[:2]` | **13 falhas, nos CINCO elos** |
| um import de volta (diferido) em `mercado_analise` | **1 falha**, o gate 1 |

**A quarta e a que mostra que a cadeia e mesmo uma cadeia.** Cortado o terceiro
item na CONFIGURACAO, ficam vermelhos os elos 1, 2, 3, 4 e 5 mais o transversal —
ou seja, o elo de baixo nao esta apenas ao lado dos de cima, ele os sustenta.

## Uma medicao que derrubou uma afirmacao do meu proprio teste, e ela ficou escrita

A primeira versao da tabela de fixture pedia `preco=20000, pacote=2` contra um
mercado a `500`, com o comentario afirmando "o mercado ganha". **Errado, e por
troca de lados:** o unitario do mercado ja E centesimo de XM (`500` = 5,00 XM),
enquanto o do NPC sai de adena e passa pela taxa (`20000` adena = **9 centesimos**
= 0,09 XM). O NPC era cinquenta e cinco vezes mais barato, e as tres vencedoras
sairam `npc`.

**Quem acusou foi a guarda anti-vacuidade que eu tinha acabado de escrever** —
`test_as_VENCEDORAS_dos_tres_NAO_sao_todas_a_mesma`, que existe precisamente para
o caso de a fixture degenerar. Sem ela, a igualdade de conjuntos de campos teria
passado sobre tres vereditos identicos, e a "generalidade" estaria provada sobre
um estado so.

O numero antigo e o novo estao escritos no fonte, ao lado da tabela, com a razao
por extenso (regra 6 do `CLAUDE.md`). O preco do segundo item subiu para
`1_000_000` adena (900 centesimos contra 500 do mercado, 44% de distancia).

## O gate 1, e por que ele nao e redundante com o Python — MEDIDO

A objecao obvia ao gate da cerca dura e que um import de volta ja quebra sozinho.
**Ela e metade verdadeira, e a medicao esta no fonte:**

- posto no TOPO de `mercado_analise.py`, `from . import dashboard_rotas` derruba
  a coleta inteira do pytest com `ImportError: cannot import name
  'N_MINIMO_PARA_MEDIANA' ... (most likely due to a circular import)`;
- posto DENTRO de `resolver_o_nome`, nao cria ciclo nenhum, a suite inteira sobe,
  e **nada quebra** — e essa e justamente a forma que alguem escreveria, porque e
  o conserto que o traceback do ciclo SUGERE.

Com o import diferido, o unico teste vermelho da arvore e
`test_o_modulo_da_cerca_NAO_importa_o_dashboard[mercado_analise.py]`. E ali que o
gate paga.

## A atribuicao por commit da cerca dura — com o comando e a saida

O `01-08` mediu que **um `git diff` cru contra a base nao mede o que esta fase
fez**: a branch e compartilhada, e o diff acusa commits de outros workstreams.
Confirmado de novo aqui, e de forma mais aguda do que o esperado — **o proprio
`--grep="(02-0"` colide**, porque os workstreams `renda`, `tiat` e `mercado`
reusam o mesmo escopo `(02-0N)` nos assuntos de commit. A busca por escopo trouxe
**mais de cem commits**, a maioria de outra gente.

A atribuicao correta e pelo CONJUNTO IDENTIFICADO de commits da fase, que os
SUMMARY do 02-01, 02-02 e 02-03 nomeiam:

```
$ git show --stat --oneline bfbb5ab 20984bc 24b3977 9d00547 25a6789 \
    9a16f2b 663b863 88dda93 e42e43e 738459c 5bed9c7 \
    9e1dafb 4b98866 a5a3d78 92edff2 db8b726 a850fb8
```

Os arquivos tocados pelos **17 commits** da fase, sem repeticao:

| arquivo | commits |
|---|---|
| `l2scanner/config.py` | 20984bc |
| `config.toml` | 20984bc |
| `l2scanner/dashboard.py` | 24b3977 |
| `l2scanner/dashboard_dados.py` | 24b3977, 663b863, e42e43e |
| `l2scanner/dashboard_rotas.py` | 24b3977, 663b863 |
| `l2scanner/recursos/dashboard/index.html` | 9d00547, 9e1dafb |
| `l2scanner/recursos/dashboard/dashboard.css` | 9d00547, 4b98866 |
| `l2scanner/recursos/dashboard/dashboard.js` | 9d00547, a5a3d78 |
| `tests/**` | 9 commits |
| `.planning/**` | 4 commits |

**Os sete arquivos da cerca dura — `rastreador.py`, `visao.py`, `console.py`,
`mercado_registro.py`, `mercado_analise.py`, `mercado_console.py`,
`mercado_catalogo.py` — nao aparecem em NENHUM dos dezessete commits.** Zero
linhas alteradas pela fase, atribuido por commit e nao por diff.

## Numeros pedidos pelo plano

- `python -m pytest tests/test_dashboard_rotas_generica.py -q` -> **53 testes**,
  0 falhas (pisos: 14 na tarefa 1, 20 no total; entregues **39** e **53**).
- Os cinco elos existem como cinco classes, **e cada uma tem ao menos um teste de
  controle** — `TestElo1..TestElo5`, mais `TestNenhumNomeDeItemEhLiteralNaProducao`.
- A sonda literal devolve **zero acusacoes** sobre os quatro arquivos varridos, e
  os controles acusam o texto de mentira nas **tres** linguagens.
- `grep -c "Gemstone" tests/test_dashboard_rotas_generica.py` -> **0**.
- `git diff --numstat requirements.txt` dos commits deste plano -> **vazio**.
- `git status --porcelain .mercado/` -> **vazio** depois da suite.
- `git diff --name-only` dos commits deste plano -> **um arquivo**, de teste.

## A rodada da suite, e o delta que e meu

Rodada unica, saida inteira: **15 failed, 6231 passed, 87 skipped** em 3min20.
O 02-03 mediu **15 failed, 6178 passed, 87 skipped** na mesma arvore.

**Delta desta fase: +53 testes, 0 falhas novas.**

## Deviations from Plan

### [Escolha declarada] O terceiro item e o do 02-02, importado — nao um nome novo

O plano dizia "escolha um terceiro item que nao aparece em nenhum arquivo desta
arvore". Um nome novo teria criado **duas respostas para "quem e o terceiro"**, e
a proxima pessoa a mexer nisso teria de descobrir qual vale. `NOME_DO_TERCEIRO`
do 02-02 satisfaz o criterio (ha teste neste arquivo varrendo `l2scanner/**` mais
o `config.toml` e exigindo zero ocorrencias, com controle) e mantem uma
autoridade so.

### [Escolha declarada] Uma sonda NOVA em vez de reusar `_nomes_de_item_no_codigo`

A diferenca nao e cosmetica e esta escrita no fonte: a do 02-02 tem a lista de
procurados FIXA dentro dela e so sabe ler Python. `nomes_de_item_no_texto` recebe
a lista (que sai da configuracao de teste, como o plano exige) e a limpeza (que
sai do arquivo que a definiu), e por isso alcanca os quatro arquivos.

**O risco de duas autoridades foi fechado com medida, e nao com promessa:**
`test_esta_sonda_CONCORDA_com_a_do_02_02_sobre_os_modulos_PYTHON` compara os dois
vereditos onde os dominios se sobrepoem. No dia em que uma delas for afrouxada,
esse teste fica vermelho em vez de a mais fraca sobreviver calada.

### [Escolha declarada] O gate 1 mede DIRECAO, e nao "nunca escreve"

O plano sugeria "os modulos do dashboard importam desses arquivos e nunca escrevem
neles". A metade do "nunca escreve" nao e afirmavel por leitura de fonte sem virar
um `assert "w" not in getsource(...)`, que e o criterio-que-afirma-existencia que
a regra 2 do `CLAUDE.md` proibe. O que ficou e mais forte e mede o mecanismo: **a
cerca nao conhece o dashboard**, com a guarda anti-vacuidade do outro lado (o
dashboard REALMENTE le a cerca) e a medicao do ciclo-vs-import-diferido acima.

### [Regra 1 - Bug no meu proprio teste] O controle do extrator de tela nao podia usar um JS sem a funcao

A primeira versao do controle negativo do elo 5 entregava ao extrator um JS sem
`montarUmaRota`, esperando conjunto vazio. **Medido: `_corpo_da_funcao` levanta
`ValueError`**, e nao devolve vazio.

O teste foi partido em dois, e a descoberta virou garantia: o controle de vazio
usa uma `montarUmaRota` PRESENTE e sem leitura nenhuma, e nasceu
`test_o_extrator_QUEBRA_quando_a_funcao_de_pintura_SUMIU` — que prende, como
propriedade da qual este arquivo DEPENDE, que o extrator explode em vez de fingir
ausencia. E o modo de falha mais perigoso de toda sonda por leitura de fonte, e
agora ele esta preso mesmo morando em outro arquivo.

### [Regra 1 - Bug no meu proprio teste] Duas frases do cabecalho quebradas pela margem

`test_o_cabecalho_diz_por_extenso_o_que_esta_prova_NAO_alcanca` procurava
`"VERIFICACAO HUMANA DECLARADA"` e `"legivel na tela"`, e as duas tinham quebra de
linha no meio. **A sonda esta certa e nao foi afrouxada** — o cabecalho foi
reescrito para as frases ficarem inteiras, que e o desfecho certo: uma frase de
fronteira partida ao meio e uma frase que a proxima edicao apaga sem perceber.

## Roteiro de verificacao humana — o teto que nenhuma assercao de fonte alcanca

Estas 53 assercoes garantem o PISO, e o piso e inteiro: a configuracao chega, a
conta roda, o payload carrega, o servidor entrega e os vaos existem para o
terceiro item exatamente como para os dois primeiros.

**Elas nao abrem um navegador.** Fica para a pessoa, com TRES itens no
`config.toml`:

1. conferir que as **tres linhas** aparecem, na ordem em que foram escritas no
   arquivo, e que a terceira nao esta espremida nem estourando a coluna;
2. conferir que a marca da vencedora continua chamando atencao com tres linhas
   empilhadas — com duas ela era obvia;
3. configurar o terceiro item com um nome que nao existe no CSV e conferir que a
   linha dele aparece com a frase de falta, sem afetar o desenho das outras duas.

## Known Stubs

Nenhum. Este plano nao criou vao, campo nem constante de producao — ele so mede.

## Deferred Issues

**15 falhas PRE-EXISTENTES**, identicas em nome e contagem as que o 02-01, o
02-02 e o 02-03 ja registraram: `tests/test_janela_no_relogio.py` (7),
`tests/test_sessao.py` (6), `tests/test_respawn.py` (2) — subsistema de
party/bosses/agenda, de outro workstream, com causa ja medida e registrada em
`deferred-items.md`.

**A instabilidade de soquete do 02-03** (`test_dashboard_servidor.py::
test_um_POST_em_OUTRO_caminho_responde_404`, `RemoteDisconnected` sob carga)
**nao reproduziu nesta rodada** — fica o registro para nao ser redescoberta como
novidade.

## Self-Check: PASSED

- O arquivo citado em `key-files.created` existe em disco:
  `tests/test_dashboard_rotas_generica.py` (1357 linhas).
- Os 2 commits de teste existem: `db8b726`, `a850fb8`.
- A contagem confere: **53 passed** no arquivo; **39** so com a tarefa 1, medido
  antes do commit dela.
- As 5 mutacoes foram executadas e REVERTIDAS; a arvore volta a 53 passed e o
  `git status` sai limpo.
- `git diff --name-only` dos commits deste plano lista **um** arquivo, em
  `tests/` — **nenhum caminho da cerca de producao**.
- Os sete arquivos da cerca dura nao aparecem em nenhum dos 17 commits da fase,
  atribuido por commit.

## Threat Flags

Nenhuma superficie nova — este plano nao acrescenta codigo de producao nenhum.
T-02-15 (prova de generalidade vazia) esta mitigada com controle em cada um dos
cinco elos, inclusive o do extrator vazio que o `01-VERIFICATION.md` exige;
T-02-16 (plano consertando o que audita) esta mitigada e MEDIDA — zero arquivos
de producao nos dois commits; T-02-17 (teste escrevendo no `.mercado/` real) tem
o gate 3 com impressao de tres componentes sobre copia temporaria, e
`git status --porcelain .mercado/` sai vazio; T-02-SC com `requirements.txt`
intacto e o guarda com controle.
