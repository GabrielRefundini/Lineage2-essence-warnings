---
phase: 02-dashboard-calculadora-de-rotas
plan: 02
subsystem: dashboard
tags: [calculadora, evidencia, fraction, cambio, guarda-de-exibicao, sonda]
status: complete

requires:
  - "02-01: dashboard_rotas.py, o bloco calculadora no payload, a quarta regiao"
  - "mercado_analise: N_MINIMO_PARA_MEDIANA, Evidencia, mediana_dos_unitarios"
  - "mercado_catalogo: CHAVE_DA_SERIE_DA_ADENA (sentinela)"
  - "mercado_console: formatador_do_unitario, formatar_centesimos"
provides:
  - "dashboard_rotas.N_MINIMO_PARA_O_VEREDITO: um piso de evidencia LIGADO ao da mediana"
  - "ROTA_SEM_EVIDENCIA e ROTA_E_A_PROPRIA_ADENA: os dois estados de linha que faltavam"
  - "VereditoDeRota.mediana (contexto) e VereditoDeRota.motivo (o que faltou)"
  - "dashboard_dados._diferenca_em_reais: a diferenca em R$ por unidade, exata"
  - "dashboard_dados._texto_do_unitario: UM ponto de guarda contra o numero zerado"
  - "tests/test_dashboard_rotas.py: 40 testes de JULGAMENTO, com sete controles"
affects:
  - "dashboard_dados: o estado de bloco sem_taxa passou a responder ao piso do veredito"
  - "dashboard_dados: FRASE_DE_SEM_TAXA_DA_ADENA virou molde e diz quantas faltam"
  - "tests/test_dashboard_rotas_tracer.py: fixturas engordadas ate o piso, derivadas da constante"

tech-stack:
  added: []
  patterns:
    - "piso de julgamento LIGADO a um piso que ja existe, e nunca copiado como literal"
    - "controle de ligacao por monkeypatch + importlib.reload, com a razao mecanica escrita"
    - "guarda de EXIBICAO que nao toca o resultado, com as duas metades ditas"
    - "sonda sobre o CODIGO Python (ast, sem docstring nem comentario), com controle nos dois sentidos"
    - "cruzamento de quatro casos com os que DISCRIMINAM nomeados por extenso"

key-files:
  created:
    - tests/test_dashboard_rotas.py
  modified:
    - l2scanner/dashboard_rotas.py
    - l2scanner/dashboard_dados.py
    - tests/test_dashboard_rotas_tracer.py

decisions:
  - "O veredito HERDA a evidencia da taxa: os dois lados respondem ao mesmo piso (a pergunta que o 02-01 deixou escrita)"
  - "N_MINIMO_PARA_O_VEREDITO le N_MINIMO_PARA_MEDIANA no import, para uma autoridade so"
  - "ROTA_E_A_PROPRIA_ADENA vem antes de ROTA_SEM_EVIDENCIA na precedencia"
  - "SEM_EVIDENCIA e E_A_PROPRIA_ADENA saem sem numero nenhum, como _margem_quebrada"
  - "Nao existe MOLDE_DA_DIFERENCA_EM_XM: o formatador ja entrega a frase completa"
  - "FRASE_DE_SEM_TAXA_DA_ADENA virou molde e MANTEVE o nome, para nao criar simbolo fantasma no index.html"

metrics:
  duration: "~2h"
  completed: 2026-09-04

actuals:
  tokens: 25241
  tasks: 3
  commits: 5
---

# Phase 2 Plan 02: O piso do veredito, o R$ que some sozinho, e a mediana como contexto — Summary

O plano 01 provou que o caminho existe; este prova que o numero que sai dele e
honesto. A calculadora passou a se recusar a eleger uma rota quando a evidencia
nao sustenta — **dos dois lados da comparacao** — e a linha em R$ passou a sumir
sozinha quando nao ha cambio, sem mover um bit do veredito.

## O que ficou de pe

**`N_MINIMO_PARA_O_VEREDITO`, ligado e nao copiado.** O CALC-04 pedia "os
`N_MINIMO_*` que ja existem" e proibia veredito sobre `n=1` — mas
`N_MINIMO_PARA_MENOR` vale UM, e reusa-lo literalmente produziria exatamente o
veredito proibido. A saida nao foi um terceiro numero: o piso do veredito LE
`mercado_analise.N_MINIMO_PARA_MEDIANA` no import, porque aquele piso ja
responde "quanta evidencia sustenta uma afirmacao sobre o mercado deste item".
A razao inteira — inclusive a marca **ESCOLHA, NAO MEDICAO** — esta no fonte, no
molde da secao de pisos do `mercado_analise`.

**A pergunta que o 02-01 deixou escrita foi RESPONDIDA: sim, o veredito herda a
evidencia da taxa.** A rota do NPC e `preco x taxa`, e a taxa saia do menor
pedido da Adena, cujo piso vale um. Exigir cinco de um lado aceitando um do
outro e uma regra que ninguem justifica depois. Agora os dois lados respondem ao
mesmo piso.

**Os dois estados de linha que faltavam.** `ROTA_SEM_EVIDENCIA` (a serie existe,
tem preco, e nao tem ofertas distintas suficientes) e `ROTA_E_A_PROPRIA_ADENA`
(o nome resolve para a serie sentinela). Os dois saem **sem numero nenhum**,
pela razao de `_margem_quebrada`: exibir as duas rotas e recusar a vencedora
deixaria o usuario fazer a subtracao de cabeca, e a recusa viraria decoracao.

**A diferenca nas tres formas, e o R$ sumindo sozinho.** `diferenca.reais` so
existe quando ha cambio; na ausencia e `null` — nao zero, nao cadeia vazia.
`vencedora`, `diferenca.xm` e `diferenca.percentual` sao **identicos campo a
campo** com e sem cambio, porque as duas rotas terminam multiplicadas pelo mesmo
fator e ele cancela.

**A mediana viaja como CONTEXTO**, com o proprio piso e a propria frase de falta,
e nunca decide nada.

## A medicao que obrigou a guarda a existir — e ela CONFIRMOU o numero do plano

O plano estimava que, na taxa real da Adena (`Fraction(9, 10000)` centesimos de
XM por adena), um preco de NPC abaixo de **~555,6 adena** por unidade faria o
unitario arredondar para zero centesimos. Recalculado com
`dashboard_rotas.custo_da_rota_do_npc` e `mercado_console.formatar_unitario_derivado`:

| Fato | Medido |
|---|---|
| maior preco inteiro cujo unitario arredonda para ZERO | **555 adena** |
| fronteira exata (`(1/2) / taxa`) | `Fraction(5000, 9)` = **555,5(5)** |
| o que o formatador de producao imprime em 555 | `0,00 por unidade (derivado)` |
| o que ele imprime em 556 | `0,01 por unidade (derivado)` |

**Nenhum numero do plano caiu.** O teste
`test_MEDICAO_o_limiar_sai_da_funcao_de_PRODUCAO` recalcula isso a cada rodada,
em vez de repetir o numero escrito.

## O `0,00` que ja estava na arvore — encontrado pela sonda, no vermelho

A sonda por token do plano nao era teatro: rodada **antes** da guarda existir,
ela ACUSOU um `0,00` real. O estado `ROTA_EMPATADA` com empate cravado imprimia
a diferenca como `0,00 por unidade (derivado)` — um numero perfeitamente
formatado ao lado de um veredito de empate, que se le como "nao custa nada". A
guarda `_texto_do_unitario` fechou os tres textos da regiao (lado do NPC, lado
do mercado, diferenca) num ponto so, e a de R$ ganhou a irma
`FRASE_DE_REAIS_INEXIBIVEL`.

## As provas de mutacao — cada guarda quebrada de proposito

| Mutacao na linha de producao | Resultado |
|---|---|
| o piso vira o literal `5` em vez de ler `N_MINIMO_PARA_MEDIANA` | **1 falha**, exatamente `test_CONTROLE_o_piso_ACOMPANHA_a_mediana_quando_ela_muda` |
| a taxa da Adena volta ao piso do menor (`if taxa is None:`) | **3 falhas**: cruzamento **2**, cruzamento **4**, e a frase que conta quantas faltam |
| a guarda do zero sai de `_texto_do_unitario` | **2 falhas**: a sonda por token e a linha do NPC barato |

**As duas previsoes do plano se confirmaram na medida.** A mutacao do piso deixa
`test_o_piso_e_o_da_MEDIANA_e_NAO_o_do_MENOR` **VERDE** — o plano ja dizia que
aquele criterio nao e o guarda, e a medicao mostra que ele nao e mesmo. E a
mutacao da taxa derruba **os cruzamentos 2 e 4 e nenhum outro**: o 1 e o 3
passam sobre as duas implementacoes, exatamente como o plano corrigiu por
escrito.

## Numeros pedidos pelo plano

- `python -m pytest tests/test_dashboard_rotas.py -q` -> **40 testes**, 0 falhas
  (pisos: 16 na tarefa 1, 28 no total).
- Suite do dashboard (6 arquivos + o novo): **290 -> 330 passed**, 1 skipped.
  **Delta: +40 testes, 0 falhas novas.**
- `grep -c "n=50" l2scanner/dashboard_dados.py` -> **>= 1** (a alternativa
  recusada sobrevive escrita, com a medicao).
- `git diff --numstat requirements.txt` -> **vazio**. Nenhuma dependencia nova.
- Cerca dura intacta: o diff da fase toca **quatro arquivos** —
  `dashboard_rotas.py`, `dashboard_dados.py` e dois de teste. Nenhum modulo do
  workstream `mercado`, nenhum arquivo web.
- Sonda de literal de nome de item sobre o codigo dos dois modulos de producao:
  **zero acusacoes**. Sonda de arredondamento sobre `dashboard_rotas.py`:
  **zero acusacoes**. As duas com controle nos dois sentidos.

## O que o `float` faz, e o que ele NAO conseguiu fazer

**Fechou pela saida (b)**, citando a medicao do 02-01 em vez de repetir a busca:
2,7 milhoes de sorteios naquele plano acharam **0 casos**, e as duas razoes
estruturais (conversao `Fraction`->`float` e monotonica; a grade de precos e
treze ordens de grandeza mais larga que o erro) ja estao presas como teste la.

**A propriedade pinada aqui atravessa o codigo NOVO:** com o par derivado de
`1/98` nao ser representavel, `_texto_do_unitario` — o ponto de producao por
onde todo numero desta regiao vira texto — imprime **`0,02`** pela conta exata e
**`0,01`** pela mesma conta em ponto flutuante.

**Uma busca nova foi feita, e ela DEU ZERO — e o zero ficou registrado.**
Procurou-se o par que faria a guarda nova mudar de ESTADO (exato caindo na frase
de inexibivel, float caindo num numero), varrendo `d` de 1 a 20.000 com
`taxa = 1/(2d)` e `preco = d`: **0 casos**. O erro do `float` naquela fronteira e
de um lado so. O zero esta preso como teste, para dizer que caiu se um dia
deixar de ser zero.

## Deviations from Plan

### [Escolha declarada] Nao existe `MOLDE_DA_DIFERENCA_EM_XM`

O plano pedia "os tres moldes da diferenca". Dois nasceram
(`MOLDE_DA_DIFERENCA_PERCENTUAL` ja existia do 02-01,
`MOLDE_DA_DIFERENCA_EM_REAIS` e novo). O terceiro **nao**, e a razao esta escrita
no fonte no lugar dele: a diferenca em XM ja sai COMPLETA de
`formatador_do_unitario` — `"58,86 por unidade (derivado)"`, com unidade e marca
de derivado dentro. Um molde em volta seria `"{valor}"`, que nao acrescenta
nada, ou acrescentaria texto — e ai seriam duas autoridades sobre como um numero
em centesimos se escreve, que e o segundo formatador que o DASH-03 recusa.

### [Escolha declarada] `FRASE_DE_SEM_TAXA_DA_ADENA` virou molde e MANTEVE o nome

A convencao da casa e `MOLDE_` para texto com `{campo}`. Esta constante deveria
ter sido renomeada e **nao foi**: o nome dela esta citado por extenso num
comentario do `index.html`, e a verificacao deste plano proibe tocar arquivo web.
Renomear deixaria um simbolo INEXISTENTE citado la — um erro de fato, pior que um
prefixo fora da convencao, porque o prefixo se desmente no primeiro `.format` do
sitio de uso e o simbolo fantasma nao se desmente nunca. A tensao esta registrada
no fonte, com o combinado de os dois se renomearem juntos no dia em que a
marcacao for mexida por outro motivo.

### [Regra 3 - Bloqueio] `tests/test_dashboard_rotas_tracer.py` foi alterado

Ele nao esta em `files_modified`, e teve de ser. **A mudanca que o proprio plano
exige quebrou 22 dos 75 testes de la**: todas as fixturas daquele arquivo tinham
UMA oferta por serie, e com o piso novo uma serie com `n=1` passou a cair em
`ROTA_SEM_EVIDENCIA` — que e o desfecho CERTO.

**As FIXTURAS foram corrigidas, e nao os testes.** Cada serie passou a ter o piso
em ofertas distintas, **com a mais barata cravada no valor que os testes ja
afirmavam** — entao toda assercao sobre menor pedido, unitario, vencedora e
diferenca continua valendo byte a byte. A contagem sai da constante
(`_piso()`), nunca de um numero a mao. Tres assercoes numericas acompanharam
(`n == 1` -> `n == _piso()`), a tupla de estados passou de quatro para seis com o
numero antigo registrado na docstring, e a frase de sem-taxa passou a ser
comparada pelo molde formatado.

### [Regra 2 - Funcionalidade critica] Duas constantes alem da lista do plano

`MOLDE_DE_ITEM_SEM_EVIDENCIA` e `FRASE_DE_REAIS_INEXIBIVEL` nao estavam na lista
de artefatos, e os `must_haves` os exigem: a truth diz que a linha abaixo do piso
"traz a frase de falta escrita pelo Python", e a sonda por token proibe `0,00` em
qualquer string do bloco — inclusive na de R$. Os dois nasceram nomeados, com a
razao ao lado, em vez de virarem texto inline.

### [Regra 1 - Bug no meu proprio teste] A sonda do fonte ancorava no lugar errado

`test_a_razao_do_piso_esta_ESCRITA_no_fonte` procurava a PRIMEIRA ocorrencia de
`N_MINIMO_PARA_O_VEREDITO` e olhava a janela de tras. **Medido:** a primeira
ocorrencia e a entrada em `__all__`, e a janela caia no cabecalho do modulo — o
teste reprovava com a razao escrita no lugar certo. E a mesma armadilha que
`mercado_analise` documenta ao manter o limiar de staleness FORA do `__all__`;
aqui a saida foi **apertar a sonda** (ancorar em `\nNOME = `) em vez de mexer na
lista de exportacao por causa de um teste. A medicao esta na docstring do teste.

## Known Stubs

Nenhum. Todos os vaos criados nesta fase sao preenchidos por codigo dela — as
quatro frases de quebra, a linha de R$, a de mediana, e as duas guardas de zero.

## Deferred Issues

**15 falhas PRE-EXISTENTES** em `tests/test_janela_no_relogio.py` (7),
`tests/test_sessao.py` (6) e `tests/test_respawn.py` (2) — subsistema de
party/bosses/agenda, fora do alcance deste plano e ja registradas como
pre-existentes no `02-01-SUMMARY.md` (que mediu o mesmo conjunto com a versao
anterior de `config.py` no lugar e obteve resultado identico).

**O delta desta fase e o que importa, e ele e limpo:** a suite do dashboard foi
de **290 passed / 1 skipped** para **330 passed / 1 skipped**. Rodada unica da
suite inteira: `6109 passed, 15 failed, 87 skipped`.

## Self-Check: PASSED

- Os 4 arquivos citados em `key-files` existem em disco.
- Os 5 commits citados existem: `9a16f2b`, `663b863`, `88dda93`, `e42e43e`,
  `738459c`.
- A contagem de testes confere: `tests/test_dashboard_rotas.py` -> 40 passed.
- As tres mutacoes foram executadas e REVERTIDAS; a arvore volta a 40 passed e o
  `git status` sai limpo.
- `git diff --numstat` da fase toca 4 arquivos, nenhum deles do workstream
  `mercado` nem web.

## Threat Flags

Nenhuma superficie nova alem da que o `<threat_model>` do plano ja previa.
T-02-07 (veredito sobre evidencia rala) e T-02-10 (item que e a propria Adena)
estao mitigadas com estado nomeado e par de testes na borda; T-02-09 (numero
zerado) com a guarda de limiar MEDIDO e a sonda por token com controle positivo;
T-02-SC com `requirements.txt` intacto.
