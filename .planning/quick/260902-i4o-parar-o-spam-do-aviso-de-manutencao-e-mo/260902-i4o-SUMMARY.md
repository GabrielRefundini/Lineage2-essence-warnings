---
phase: quick-260902-i4o
plan: 01
subsystem: manutencao
tags: [ocr, ancora, dedup, whatsapp, chatwoot, consenso-temporal]

requires:
  - phase: 05-manutencao
    provides: VigiaDeManutencao, a ancora no relogio e o consenso temporal de duas leituras
provides:
  - O anuncio de manutencao virou UMA VEZ POR EPISODIO — so `_expirar` libera um novo
  - O segundo aviso passou a sair aos 10 minutos, dizendo sempre os minutos REAIS
  - A regra de re-armar o segundo aviso: so remarcacao confirmada acima do limiar
  - Os numeros de campo de 2026-09-02 escritos no cabecalho do modulo
  - O porque de a dedup em disco nao segurar, escrito onde ela mora
affects: [manutencao, sessao, agenda, alertas-no-whatsapp]

actuals:
  tokens: 10600
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Separar MOVER A ANCORA de RE-ARMAR O AVISO: a mesma linha fazia as duas coisas"
    - "Guarda de uma-vez-por-episodio mora no vigia; o disco so protege contra duas instancias"
    - "Prova por MUTACAO MEDIDA: rodar o teste contra a producao mutilada e publicar os dois numeros"

key-files:
  created: []
  modified:
    - l2scanner/manutencao.py
    - l2scanner/sessao.py
    - tests/test_manutencao.py
    - tests/test_sessao.py

key-decisions:
  - "D-01: ANTECEDENCIA passou de 5 para 10 minutos, a pedido literal do usuario"
  - "D-02: o membro do enum virou ANTES; o `.value` continua `faltam5`, com tripwire"
  - "D-03: o ramo da remarcacao parou de zerar `_emitidos`; so `_expirar` encerra o episodio"
  - "D-04: o segundo aviso so re-arma quando `duracao > ANTECEDENCIA`"
  - "Residuo aceito e MEDIDO: 6 avisos do segundo tipo no replay de campo, escrito e nao escondido"

metrics:
  duration: ~1h
  completed: 2026-09-02

status: complete
---

# Quick 260902-i4o: Parar o spam do aviso de manutencao e mover o segundo aviso para 10 minutos — Summary

Uma reancoragem dentro do mesmo episodio re-armava o anuncio de manutencao, e a dedup
em disco nao segurava porque a chave dela deriva da propria ancora que escorregou;
mover a ancora e re-armar o anuncio eram a mesma linha e viraram duas.

## O defeito, medido em campo

Em 2026-09-02, entre 11:58 e 12:52, o grupo de WhatsApp do usuario recebeu **~19 vezes
a mesma mensagem** `MANUTENCAO DO SERVIDOR em X (as HH:MM). Nao entre em instance.`
para **UMA unica manutencao**, mais 3 mensagens do segundo tipo (12:11, 12:41, 12:52).
Os 17 horarios-alvo que as mensagens carregaram se espalharam por 54 minutos:

```
12:59  12:56  12:59  13:05  12:18  12:11  12:26  12:29  12:30
12:34  12:35  12:37  12:38  12:40  13:05  12:43  12:56
```

O usuario: *"Funcionou perfeitamente mas esta spammando muito, avise apenas quando
aparece o anuncio e quando faltar 10m."*

**A mecanica:** uma leitura fora da tolerancia vira `_candidata`; a leitura seguinte
chega 5 s depois (`SEGUNDOS_ENTRE_LEITURAS`) repetindo o **mesmo erro sistematico de
OCR** e portanto cai dentro dos 60 s de `TOLERANCIA_DO_CONSENSO` em relacao a
candidata; a ancora troca — e a troca chamava `self._emitidos.clear()`, fazendo o
anuncio parecer novo. O consenso *temporal* e cego a erro de *metodo* por construcao,
e isso ja estava escrito na docstring de `VigiaDeManutencao` antes de custar 19
mensagens.

## A PROVA DE MUTACAO (o item obrigatorio do plano)

O teste de replay de campo foi rodado contra a producao **mutilada** — o
`self._emitidos.clear()` do ramo de remarcacao restaurado no lugar da guarda nova — e
contra a producao consertada. As duas saidas, literais:

### Com a mutacao aplicada (o defeito de volta) — FALHA

```
E       AssertionError: assert 14 == 1
E       AssertionError: assert 8 == 6
E       AssertionError: assert 11 == 1
=========================== short test summary info ===========================
FAILED tests/test_manutencao.py::TestOSpamDeCampoDe0209::test_a_sequencia_deslizante_do_campo_produz_UM_anuncio_so
FAILED tests/test_manutencao.py::TestOSpamDeCampoDe0209::test_o_segundo_aviso_do_campo_tem_o_residuo_MEDIDO_e_aceito
FAILED tests/test_sessao.py::TestManutencaoNoTick::test_a_ancora_deslizando_do_campo_produz_UM_anuncio_na_costura
3 failed, 1 passed in 1.75s
```

### Com o conserto restaurado — PASSA

```
....                                                                     [100%]
4 passed in 1.63s
```

O `git status` depois de restaurar veio **vazio**: a restauracao e byte-identica ao
que esta commitado.

### A contagem de anuncios, antes e depois

| Onde | Com o defeito | Com o conserto |
|---|---|---|
| Replay no vigia (`test_manutencao.py`) | **14** anuncios | **1** |
| Replay pela costura do `Sessao` (`test_sessao.py`) | **11** anuncios | **1** |
| Arquivos `*_anunciada` criados em `.agenda/` | **11**, com 11 nomes diferentes | **1** (`2026-09-02_manutencao-1259_anunciada`) |

Os 14 do vigia contra os 11 da costura sao a medida exata do quanto o disco ajudou:
ele barrou 3 das 14 emissoes, e **so** aquelas em que dois deslizes seguidos calharam
de arredondar para o mesmo minuto. Os 11 arquivos com 11 nomes diferentes sao a prova
direta de que `chave_do_marcador` deriva do momento da ancora arredondado ao minuto —
cada deslize produz chave inedita, e diante de chave inedita o `marcar` **cria** em vez
de barrar. Os ~19 do campo contra os 14 do replay se explicam pelos deslizes que caem
DENTRO da tolerancia e nem chegam ao ramo da remarcacao.

## O residuo aceito, medido e escrito

Depois do conserto, a mesma sequencia de campo produz **exatamente 6** avisos do
segundo tipo (as 12:08:05, 12:20, 12:25, 12:27, 12:35:35 e 12:46). Este numero e
**custo aceito, e nao regressao**:

- Ele vem da regra de re-armar (D-04): uma remarcacao confirmada que traz o alvo de
  volta para ACIMA de 10 minutos volta a armar o segundo aviso, e nesta sequencia o OCR
  faz isso seis vezes.
- O preco da alternativa e o que decide: nao re-armar nunca significaria que uma
  manutencao genuinamente **adiada** — de 4 para 25 minutos, digamos — nunca mais
  avisaria o grupo quando o horario novo chegasse perto. Perder o aviso de antecedencia
  de uma manutencao real custa a instance e o loot do chao; recebe-lo seis vezes custa
  incomodo.
- **Comparacao honesta com o campo:** la o segundo tipo saiu 3 vezes, com o limiar de 5
  minutos. Com o limiar de 10 a janela e o DOBRO, entao mais deslizes da ancora caem
  dentro dela. 6 e o preco do que o usuario pediu.
- Saldo do episodio inteiro: de **~22 mensagens** (~19 anuncios + 3) para **7**.

O numero esta afirmado com `== 6` no teste e a razao esta na docstring dele.

## A decisao sobre o nome e o valor do membro do enum (D-02)

O membro se chamava com o numero cinco dentro, e o cinco era o `ANTECEDENCIA` daquela
epoca. O limiar virou dez e o nome passou a mentir. Ele agora se chama **`ANTES`** — o
mesmo vocabulario que `agenda.TipoDeAviso.ANTES` ja usa. O **`.value` continua sendo a
string `faltam5`**, e o descasamento e deliberado. Os dois precos, escritos no enum:

| Escolha | Preco |
|---|---|
| **Trocar o valor** (`"antes"`) | Uma mensagem DUPLICADA no grupo por manutencao ja em andamento, para todo scanner reiniciado com o codigo novo: o marcador gravado em `.agenda/` deixaria de casar com a chave nova e o aviso ja enviado voltaria a parecer novo. |
| **Manter o valor** (`"faltam5"`) — **escolhido** | Um nome de arquivo em `.agenda/` que so faz sentido com a docstring ao lado. |

A decisao segue a lei que este modulo e o `agenda.py` (`TipoDeAviso.CHAMADA`) ja tinham
escrito: o valor e **identidade duravel**, nunca descricao. Um tripwire novo
(`TestOValorDuravelDoSegundoAviso`) trava a string e explica o porque.

## O que mudou, por arquivo

**`l2scanner/manutencao.py`**
- `ANTECEDENCIA`: `timedelta(minutes=5)` -> `timedelta(minutes=10)`, com a razao e o
  pedido literal do usuario no comentario.
- `TipoDeAvisoDeManutencao.FALTAM5` -> `.ANTES`, com `.value` inalterado e a decisao
  inteira na docstring do enum.
- `texto_de_5_minutos` -> `texto_de_antecedencia` (a funcao nunca imprimiu um cinco
  fixo na vida; nao era importada fora do modulo — conferido por busca).
- `_registrar`, ramo da remarcacao: a movimentacao da ancora, da duracao confirmada e a
  limpeza da candidata ficaram **byte-identicas**. Saiu o `self._emitidos.clear()`;
  entrou o descarte APENAS do segundo aviso, condicionado a `duracao > ANTECEDENCIA`.
  O primeiro ramo (deslize dentro da tolerancia) nao foi tocado.
- `_expirar`: a docstring registra que ele passou a ser o UNICO lugar que zera
  `_emitidos`.
- Cabecalho: terceira secao historica com a data, a janela, as contagens, os 17
  horarios-alvo e a mecanica.

**`l2scanner/sessao.py`** — **somente docstring**, `18 adicoes / 0 remocoes`. Nenhuma
linha de codigo de `_processar_manutencao` mudou.

**`tests/test_manutencao.py`** — o replay da sequencia de campo (3 testes), o limiar de
10 minutos nas duas bordas, os dois lados da regra de re-armar, o tripwire do valor
duravel, e as correcoes aritmeticas com a conta na docstring.

**`tests/test_sessao.py`** — a costura ponta-a-ponta com a ancora deslizando
(vigia -> marcador em disco -> resultado -> despacho), o `LeitorDeslizanteDoCampo`, e a
correcao aritmetica do teste do segundo aviso.

## `TestExpiracao` — o criterio de aceite contra o risco espelhado

O risco espelhado e uma guarda forte demais fazendo a manutencao **seguinte** ser
detectada, ancorada e nunca anunciada — o pior modo de falha deste projeto, porque de
fora parece funcionar.

```
tests/test_manutencao.py::TestExpiracao  ->  3 passed in 0.04s
```

E `git diff HEAD~3 -- tests/test_manutencao.py` **nao contem uma unica linha alterada
dentro dessa classe** — as unicas ocorrencias de `_expirar` no diff sao mencoes em
docstrings de testes NOVOS. Verde sem uma linha de edicao, como o plano exigiu.

## Contagem de testes: baseline e final

| Momento | Coletados | `passed` | `skipped` |
|---|---|---|---|
| **Baseline** (antes de tocar em producao, `git HEAD = f862eee`) | 5039 | **4986** | 53 |
| **Final** (`python -m pytest -q`, codigo 0) | 5048 | **4995** | 53 |

`4995 > 4986` — 9 testes novos, nenhum teste existente mudou de veredito por acidente.
Tempo: 118 s.

> Nota sobre o baseline: o plano registrava 4919 testes coletados; a suite ja estava em
> 5039 no commit base desta tarefa. Usei o numero **medido** no inicio da execucao,
> como o proprio criterio manda.

## Verificacao

1. `python -m pytest tests/test_manutencao.py tests/test_sessao.py -q` -> `191 passed`.
2. Mutacao medida -> as duas saidas estao acima, com as contagens.
3. `pytest tests/test_manutencao.py::TestExpiracao -q` -> `3 passed`, sem edicao na classe.
4. `python -m pytest -q` -> codigo 0, `4995 passed, 53 skipped`, acima do baseline.
5. `ruff check l2scanner/manutencao.py l2scanner/sessao.py tests/test_manutencao.py tests/test_sessao.py`
   -> `All checks passed!`
6. `git diff --stat HEAD~3` -> exatamente os quatro arquivos de `files_modified`:

```
 l2scanner/manutencao.py  | 146 +++++++++++++++---
 l2scanner/sessao.py      |  18 +++
 tests/test_manutencao.py | 379 +++++++++++++++++++++++++++++++++++++++++++++--
 tests/test_sessao.py     | 111 +++++++++++++-
 4 files changed, 616 insertions(+), 38 deletions(-)
```

Zero dependencia nova: `pyproject.toml` e `calibration.json` ficaram fora do diff.

## Commits

| Tarefa | Commit | Mensagem |
|---|---|---|
| 1 | `174a171` | `fix(quick-260902-i4o): mover a ancora e re-armar o anuncio eram a mesma linha` |
| 2 | `e2c9399` | `feat(quick-260902-i4o): o segundo aviso passa a sair aos 10 minutos` |
| 3 | `129eac1` | `docs(quick-260902-i4o): os numeros de 02/09 no cabecalho e o porque do disco` |

## Deviations from Plan

Nenhum desvio de comportamento. Tres ajustes de escopo documentados:

**1. [Rule 2 - consistencia] Prosa do modulo que citava "5 minutos" foi corrigida junto**
- **Encontrado em:** Tarefa 2
- **Situacao:** o plano listava o rename do membro e da funcao, mas tres trechos de
  prosa (`manutencao.py` linhas 40, 663 e 742) diziam "o aviso de 5 minutos" e
  passariam a mentir junto com os nomes.
- **Feito:** trocados para "o aviso de antecedencia" / "faltam 10 minutos".
- **Commit:** `e2c9399`

**2. [Rule 2 - consistencia] Variavel local `faltam5` em `test_manutencao.py`**
- **Situacao:** o plano mandava nao renomear fixtures nem textos de campo; esta era uma
  variavel local que guardava A CHAVE, nao o membro.
- **Feito:** renomeada para `do_segundo_aviso`. O literal `"faltam5"` continua intacto
  onde ele e o VALOR sob teste.
- **Commit:** `e2c9399`

**3. Assercao da costura trocada por uma nao-tautologica**
- **Situacao:** a primeira versao do teste de costura afirmava
  `len(despachos) == len(tipos)` para provar que o disco nao barrou nada. Isso e
  **sempre verdade**: `avisos_de_manutencao` so e preenchido DEPOIS de o `marcar`
  passar, entao a assercao nao media coisa alguma.
- **Feito:** trocada pela contagem de arquivos `*_anunciada` no `tmp_path`, com o nome
  exato esperado (`2026-09-02_manutencao-1259_anunciada`, o da PRIMEIRA ancora), e a
  medicao dos 11 arquivos sob mutacao escrita na docstring.
- **Commit:** `174a171`

## Threat Flags

Nenhuma superficie de seguranca nova. Os itens do `<threat_model>` do plano:

| Threat ID | Estado |
|---|---|
| T-i4o-01 (DoS por ruido) | **Fechado** — 14/11 anuncios -> 1, com mutacao medida. |
| T-i4o-02 (DoS por silencio, o risco espelhado) | **Fechado** — `TestExpiracao` verde sem edicao. |
| T-i4o-03 (identidade duravel) | **Fechado** — `.value` inalterado, tripwire novo. |
| T-i4o-04 (forense) | Aceito, como planejado — nenhuma linha de log foi reduzida. |
| T-i4o-05 (dependencias) | **Fechado** — zero pacote novo, `pyproject.toml` fora do diff. |

## Known Stubs

Nenhum. Nenhum `TODO`, `FIXME`, teste pulado ou `<verify>` nao executado foi introduzido.

## Self-Check: PASSED

- `l2scanner/manutencao.py` — FOUND
- `l2scanner/sessao.py` — FOUND
- `tests/test_manutencao.py` — FOUND
- `tests/test_sessao.py` — FOUND
- `.planning/quick/260902-i4o-parar-o-spam-do-aviso-de-manutencao-e-mo/260902-i4o-SUMMARY.md` — FOUND
- Commit `174a171` — FOUND
- Commit `e2c9399` — FOUND
- Commit `129eac1` — FOUND
