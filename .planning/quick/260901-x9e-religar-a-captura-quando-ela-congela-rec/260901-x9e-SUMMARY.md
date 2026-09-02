---
phase: quick-260901-x9e
plan: 01
subsystem: captura
tags: [wgc, windows-capture, mss, recuperacao, envelope, frames]

requires:
  - phase: frames.py (`SaudeDoFrame.CONGELADO`, `FRAMES_IDENTICOS_PARA_CONGELADO`)
    provides: o detector de congelamento, que ja acertou em campo e NAO foi tocado
provides:
  - "`l2scanner/recaptura.py` — o envelope `FonteRecuperavel`, que reconstroi a fonte de frames apos N frames CONGELADO seguidos"
  - "`montar_fonte` em `__main__.py` — a escolha do backend fatorada, com cada caminho vivo virando uma fabrica sem argumentos"
  - "teto de tentativas, portao de espera sem `time.sleep`, orcamento devolvido por frame saudavel e religacao a prova de fabrica que explode"
affects: [captura, reancoragem, gravacao, sessao]

actuals:
  tokens: 11204        # 44.817 chars de diff realizado / 4
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Envelope de identidade estavel que troca o INTERIOR, para quem guardou a referencia (ou um metodo LIGADO) na construcao nao ficar com o objeto morto"
    - "Fabrica sem argumentos como UNICO site da lista de parametros da fonte — arranque e religacao chamam a mesma funcao"
    - "Portao de tempo por comparacao de instantes com relogio injetavel, nunca `time.sleep`, dentro de um laco que ja dorme por tick"

key-files:
  created:
    - l2scanner/recaptura.py
    - tests/test_recaptura.py
  modified:
    - l2scanner/__main__.py

key-decisions:
  - "O reset do orcamento e ancorado no FRAME SAUDAVEL, e nao no `__init__` ter retornado — a WGC devolve sessoes que constroem sem erro e continuam mortas, que foi o caso medido em campo"
  - "As tres constantes moram no codigo e nao no `calibration.json`, pelo mesmo motivo ja registrado para `PISO_DO_RESTO`: uma chave nova obrigatoria mataria o scanner no proximo arranque"
  - "`ReplaySource` fica fora do envelope: reconstruir um replay reiniciaria a gravacao e o harness de regressao deixaria de provar qualquer coisa"
  - "A delegacao do que nao e declarado vai por `__getattr__`, porque `sessao.py` decide por `hasattr(fonte, 'estado_do_cliente')` e `MssSource` nao tem esse metodo"
  - "A tentativa e contada ANTES de tentar, senao uma fabrica que explode gastaria tentativa nenhuma e o teto nunca chegaria"

patterns-established:
  - "Prova por CONTAGEM DE CONSTRUCOES: a fonte falsa incrementa um contador no proprio `__init__` e o teste afirma que o numero subiu — nunca que a funcao existe"
  - "Par honesto de medicao: a mesma bancada rodada com e sem a unica variavel em questao (com frame saudavel e sem ele), e os dois numeros escritos"

requirements-completed: [QUICK-260901-x9e]

duration: 38min
completed: 2026-09-02
status: complete
---

# Quick 260901-x9e: Religar a Captura Quando Ela Congela — Summary

**Depois de tres frames `CONGELADO` seguidos o scanner agora RECONSTROI a fonte de captura pela mesma fabrica que a construiu no arranque, com teto de cinco tentativas, 30 s de espera entre elas e orcamento devolvido por frame saudavel — fechando o buraco de 33 minutos cegos com o jogo vivo medido em 2026-09-01.**

## Performance

- **Duration:** ~38 min
- **Tasks:** 3/3
- **Commits:** 6 (RED + GREEN por tarefa)

## O defeito que fecha

Em 2026-09-01 as 23:18:39 o scanner logou `Imagem congelada — jogo travado ou
captura presa` e ficou 33 minutos em `[SEM VISAO]`. Tudo o que poderia estar
errado estava certo: a janela existia (hwnd 30216936), nao estava minimizada,
ocupava (1713,0)-(3447,1399); a geometria batia com `cal["geometria_da_tela"]`
(dx=0, dy=0); o recorte da party mostrava quatro membros legiveis; `hp_proprio`
lia `HP 5915/5915`; o `mss` via a tela MUDANDO (diffs 174.087 e 120.828); e uma
`JanelaSource` NOVA, construida naquele mesmo instante, funcionava (diffs
150.453 e 149.983, brilho medio 58,2).

O detector acertou. O que faltava era a cura: o laco escrevia um `log.warning` e
seguia chamando `capturar()` num objeto morto para sempre. Uma morte nessa
janela de 33 minutos nao teria sido anunciada.

## A MUTACAO MEDIDA (Tarefa 1) — obrigatoria, e aqui esta

Depois de os sete testes da Tarefa 1 passarem, a chamada de reconstrucao dentro
de `capturar()` em `l2scanner/recaptura.py` foi comentada — so ela, nada mais:

```python
            if self._congelados_seguidos >= CONGELADOS_SEGUIDOS_PARA_RELIGAR:
                pass  # MUTACAO TEMPORARIA: self._religar()
```

### Saida do pytest COM a mutacao (o teste FALHA)

```
$ python -m pytest tests/test_recaptura.py -q
.F..FF.                                                                  [100%]
================================== FAILURES ===================================
_ TestNCongeladosReconstroemAFonte.test_n_congelados_seguidos_reconstroem_a_fonte _

self = <test_recaptura.TestNCongeladosReconstroemAFonte object at 0x0000018D4C3E5EB0>

    def test_n_congelados_seguidos_reconstroem_a_fonte(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO))
        )

        for _ in range(CONGELADOS_SEGUIDOS_PARA_RELIGAR):
            envelope.capturar()

>       assert contador.construcoes == 2
E       assert 1 == 2
E        +  where 1 = <test_recaptura.Contador object at 0x0000018D4C3E4FB0>.construcoes

tests\test_recaptura.py:96: AssertionError
```

Os outros dois criterios da mesma tarefa cairam junto, e por motivos
independentes — o fechamento da fonte antiga e a identidade de quem responde:

```
>       assert contador.fechamentos == 1
E       assert 0 == 1
E        +  where 0 = <test_recaptura.Contador object at 0x000002DCB7816270>.fechamentos

tests\test_recaptura.py:137: AssertionError
```

```
>       assert envelope.capturar().indice == 2
E       AssertionError: assert 1 == 2
E        +  where 1 = Frame(pixels=array([[[0, 0, 0]]], dtype=uint8), indice=1, saude=<SaudeDoFrame.CONGELADO: 'congelado'>, momento=None, extras={}).indice

tests\test_recaptura.py:149: AssertionError
```

**Linha de resumo do pytest sob mutacao:**

```
=========================== short test summary info ===========================
FAILED tests/test_recaptura.py::TestNCongeladosReconstroemAFonte::test_n_congelados_seguidos_reconstroem_a_fonte
FAILED tests/test_recaptura.py::TestNCongeladosReconstroemAFonte::test_a_fonte_antiga_e_fechada_exatamente_uma_vez
FAILED tests/test_recaptura.py::TestNCongeladosReconstroemAFonte::test_a_instancia_nova_passa_a_responder
3 failed, 4 passed in 0.17s
```

### Saida DEPOIS de desfeita a mutacao (volta ao verde)

```
$ python -m pytest tests/test_recaptura.py -q
.......                                                                  [100%]
7 passed in 0.06s
```

E, com as tres tarefas completas:

```
$ python -m pytest tests/test_recaptura.py -q
.................................                                        [100%]
33 passed in 0.36s
```

A prova e CONTAGEM DE CONSTRUCOES: a fonte falsa incrementa um contador no
proprio `__init__`, e o teste afirma que esse numero subiu de 1 para 2. Um
criterio que apenas afirmasse que `_religar` existe teria passado com a chamada
removida — foi assim que os doze defeitos desta sessao nasceram.

## Os valores finais das tres constantes, e o porque de cada numero

| Constante | Valor | Por que este numero |
|---|---|---|
| `CONGELADOS_SEGUIDOS_PARA_RELIGAR` | **3** | `CONGELADO` ja e caro de ganhar: so sai depois de `FRAMES_IDENTICOS_PARA_CONGELADO` (30) frames byte-identicos, ou seja meio minuto a 1 Hz. Este numero nao e o debounce — o debounce ja aconteceu la dentro. Tres ticks sao ~3 s de confirmacao em cima de ~30 s de evidencia, e a primeira tentativa cai por volta dos 33 s de cegueira, e nao dos 33 minutos. |
| `TENTATIVAS_DE_RELIGACAO` | **5** | No caso MEDIDO a fonte nova funcionou na PRIMEIRA tentativa. O teto nao existe para aquele caso, existe para o outro: quando reconstruir nao resolve (driver caido, sessao WGC que nasce morta, jogo realmente travado). Sem teto seria uma sessao de captura nova por tick, para sempre, martelando a WGC e vazando uma thread a cada volta. |
| `SEGUNDOS_ENTRE_TENTATIVAS` | **30.0** | Cinco tentativas espacadas em 30 s dao ~2,5 min de esforco de recuperacao — atravessa um hiccup do compositor sem virar um laco de reconstrucao. Nao ha `time.sleep`: o portao e comparacao de instantes, porque o laco ja dorme `args.intervalo` por tick e bloquear aqui atrasaria os comandos e a agenda junto. |

As tres moram no CODIGO, e nao no `calibration.json`, pelo mesmo motivo ja
registrado para `PISO_DO_RESTO` em `mercado_catalogo.py:195-201`: uma chave nova
obrigatoria no arquivo de calibracao deixaria o scanner morto no proximo
arranque, ate o usuario recalibrar. `calibration.json` nao foi lido, escrito nem
tocado.

## Accomplishments

- **Tarefa 1 (tracer):** `l2scanner/recaptura.py` com as tres constantes e a
  fatia fina do envelope `FonteRecuperavel` — conta `CONGELADO` seguidos, zera a
  contagem em qualquer outra saude, e ao atingir o limite constroi pela MESMA
  fabrica, fecha a antiga e adota a nova. `montar_fonte` fatorado em
  `__main__.py`, com cada caminho vivo virando uma fabrica sem argumentos e o
  replay ficando de fora com o motivo escrito. **Mutacao aplicada, falha medida,
  saida copiada, mutacao desfeita.**
- **Tarefa 2:** teto, portao de espera com relogio injetavel, orcamento devolvido
  por frame saudavel, e religacao a prova de fabrica que explode. O teto foi
  MEDIDO duas vezes (`1 + TENTATIVAS_DE_RELIGACAO`, e o mesmo numero com dez
  vezes mais ticks). Esgotado o teto sai UM `log.error` — a contagem de registros
  nesse nivel e exatamente 1 — e `capturar()` continua devolvendo `Frame`.
- **Tarefa 3:** delegacao completa. Declarados so `capturar`,
  `capturar_completo`, `completo_do_frame_atual`, `apontar_para` e `fechar` — os
  metodos cujos donos guardam a referencia ou o metodo LIGADO atravessando a
  religacao. O resto por `__getattr__`. A regiao reancorada e guardada quando o
  interior aceita e reaplicada na fonte nova falhando fechada. Os dois backends
  vivos passam pelo mesmo envelope; o replay nao.

## A prova de que o reset esta ancorado no frame saudavel

Nao ha teste separado para isso, e de proposito: o teste do TETO **e** a prova.
Naquela bancada toda fonte nova CONSTROI sem erro e continua morta — o caso de
campo. Se o reset olhasse para o `__init__` ter retornado, o teto nunca seria
alcancado e o total de construcoes cresceria sem parar. O par honesto esta
escrito lado a lado:

- com um frame saudavel no meio: `contador.construcoes == 2 + TENTATIVAS_DE_RELIGACAO`
- sem frame saudavel nenhum: `contador.construcoes == 1 + TENTATIVAS_DE_RELIGACAO`

Mesma bancada, unica diferenca o frame bom.

## Verification Results

| # | Verificacao | Resultado |
|---|---|---|
| 1 | `python -m pytest tests/test_recaptura.py -q` | **33 passed in 0.36s** |
| 2 | A MUTACAO MEDIDA da Tarefa 1 | **3 failed, 4 passed in 0.17s** — copiada literalmente acima |
| 3 | `python -m pytest tests/test_mercado_firewall_de_fase.py -q` | verde (rodado junto com o item 1: **25 passed in 3.01s**) — `minimum_update_interval` continua ausente da construcao da party |
| 4 | `python -m pytest tests/ -q` | **4664 passed, 25 skipped, 4 warnings in 132.48s** — codigo 0 |
| 5 | `git diff --stat 6a19cba~1 HEAD` | apenas `l2scanner/recaptura.py`, `l2scanner/__main__.py`, `tests/test_recaptura.py` |
| 6 | Portao de sintese de input | `SINTESE DE INPUT: []`, exit 0 |

### Sobre a contagem da suite — leia o numero honesto

`4664 passed` esta **acima** do baseline de 4404. Os `25 skipped` (contra os 2
do baseline) **nao sao regressao e nao tem nada a ver com esta tarefa**: sao
todos skips AMBIENTAIS de assets gitignored que nao se materializam num
worktree. Conferido com `-rs`; as razoes sao literalmente, por exemplo:

- `recordings/ e gitignored e nao se materializa num worktree nem num clone limpo` (`test_mercado_replay.py`, `test_mercado_ancora.py`, `test_mercado_27x.py`, `test_mercado_multiancora.py`, `test_sugestao_de_calibracao.py`, `test_inventario_por_cima_da_barra_propria.py`)
- `calibration.json e gitignored e so existe no checkout principal` (`test_calibracao_mercado.py`)
- `.venv\Lib\site-packages nao existe` (`test_firewall_escopo.py`)
- `acervo real ausente nesta maquina` (`test_a_pergunta_leva_a_imagem.py`)

Rodado no python GLOBAL (3.12), nao no `.venv`. `tests/test_agenda.py:1141` nao
abortou a rodada.

## Deviations from Plan

Nenhum. O plano foi executado como escrito, com uma nota de FIDELIDADE, nao de
desvio: em `montar_fonte` os `log.info`/`log.warning` de cada braco foram
mantidos palavra por palavra E na mesma ordem relativa a construcao da fonte — o
`FonteRecuperavel(construir)` foi posicionado onde o `JanelaSource(...)` /
`MssSource(...)` estava, e nao no fim da funcao, justamente para a ordem das
linhas no console de arranque nao mudar.

Arquivos que o plano proibiu tocar e que continuam fora do diff:
`rastreador.py`, `visao.py`, `sessao.py`, `respawn.py`, `bosses.py`,
`agenda.py`, `identidade.py`, `discord/`, `pyproject.toml`, `calibration.json`.
Nenhuma dependencia nova. `VERSAO_DO_ESQUEMA` intocado. Nada escrito em
`.mercado/`. Nenhum glob amplo em `recordings/`.

## Known Stubs

Nenhum. Nao ha valor vazio hardcoded, placeholder, TODO nem FIXME no codigo
novo; nao ha teste pulado nem `<verify>` que nao tenha sido rodado.

## Threat Flags

Nenhuma superficie nova de seguranca. Os cinco itens do registro STRIDE do plano
foram mitigados como escrito:

| Threat ID | Mitigacao entregue |
|---|---|
| T-x9e-01 (DoS na WGC) | Teto `TENTATIVAS_DE_RELIGACAO` mais portao de espera, ambos com teste de contagem |
| T-x9e-02 (thread vazada) | Cada religacao chama `fechar()` na fonte antiga; teste afirma exatamente um fechamento |
| T-x9e-03 (dado falso vira alerta) | Nada de `visao.py`/`rastreador.py` foi tocado; a fonte nova traz `_ClassificadorDeSaude` limpo |
| T-x9e-04 (dependencias) | Zero pacote novo; `pyproject.toml` fora do diff; portao de sintese de input verde |
| T-x9e-05 (calibracao) | As tres constantes ficam no codigo; `calibration.json` nem lido nem escrito |

## Commits

| # | Hash | Mensagem |
|---|---|---|
| 1 | `6a19cba` | `test(x9e-01): a contagem de construcoes que prova a religacao, ainda vermelha` |
| 2 | `390e275` | `feat(x9e-01): N congelados seguidos reconstroem a fonte, ponta a ponta` |
| 3 | `90a1713` | `test(x9e-02): teto, espera, orcamento devolvido e religacao que explode — vermelhos` |
| 4 | `6d9e7a5` | `feat(x9e-02): a religacao fica limitada, pausada e a prova de fabrica que explode` |
| 5 | `6dad75b` | `test(x9e-03): os donos de referencia e os dois backends — vermelhos` |
| 6 | `4627db9` | `feat(x9e-03): os donos de referencia atravessam a troca de fonte` |

## TDD Gate Compliance

RED e GREEN existem, nesta ordem, para cada uma das tres tarefas: os commits
1/2, 3/4 e 5/6 acima. Nenhum teste passou antes da implementacao existir — a
primeira rodada da Tarefa 1 foi `ModuleNotFoundError: No module named
'l2scanner.recaptura'`, a da Tarefa 2 foi
`TypeError: FonteRecuperavel.__init__() got an unexpected keyword argument 'relogio'`
(13 failed, 7 passed) e a da Tarefa 3 foi
`AttributeError: 'FonteRecuperavel' object has no attribute 'apontar_para'`
(7 failed, 26 passed). Nao houve fase REFACTOR: nao houve nada a limpar.

## Self-Check: PASSED

Arquivos afirmados, conferidos no disco:

- FOUND: `l2scanner/recaptura.py`
- FOUND: `l2scanner/__main__.py`
- FOUND: `tests/test_recaptura.py`
- FOUND: `.planning/quick/260901-x9e-religar-a-captura-quando-ela-congela-rec/260901-x9e-SUMMARY.md`

Commits afirmados, conferidos no `git log`: `6a19cba`, `390e275`, `90a1713`,
`6d9e7a5`, `6dad75b`, `4627db9` — todos presentes, na ordem RED/GREEN escrita
acima, todos sobre o commit do plano (`2aea450`). Nenhum deles toca
`calibration.json`, `pyproject.toml` nem qualquer arquivo de agente paralelo.

---

## Verificacao independente do orquestrador

O executor relatou UMA mutacao. O orquestrador refez a prova por conta propria, em
worktree isolado no merge (`171b074`), e acrescentou mais duas — porque uma unica
mutacao prova que o teste do caminho feliz morde, e nao diz nada sobre o teto nem
sobre a espera.

| mutacao aplicada | resultado medido |
|---|---|
| (linha de base, sem mutar) | `33 passed in 1.39s` |
| comentar a chamada `self._religar()` | `16 failed, 17 passed in 0.94s` |
| remover o portao `>= TENTATIVAS_DE_RELIGACAO` (o teto) | `6 failed, 27 passed in 0.44s` |
| remover o portao `< SEGUNDOS_ENTRE_TENTATIVAS` (a espera) | `1 failed, 32 passed in 0.25s` |

As tres constantes de comportamento estao cobertas, cada uma por testes que caem quando
ela cai. Nenhuma passou de graca.

## O que o orquestrador conferiu alem da mutacao

**O risco do envelope, checado e limpo.** Declarar um metodo no envelope CRIA o atributo
mesmo quando a fonte de dentro nao o tem, o que quebraria qualquer `hasattr`. Varredura
do projeto inteiro: existe **um unico** `hasattr` sobre a fonte, em `sessao.py:453`, e e
sobre `estado_do_cliente` — que o envelope roteia por `__getattr__`, exatamente como a
docstring promete. Conferido tambem que `MssSource`, `ReplaySource` e `FrameSource` nao
tem `capturar_completo`, `completo_do_frame_atual` nem `apontar_para`, e que ninguem
consulta a existencia desses tres por `hasattr`.

**A suite que aborta NAO e desta tarefa.** No tronco a suite completa para em
`tests/test_agenda.py:1231` com `KeyboardInterrupt` depois de 188 testes, e tudo que vem
depois na ordem alfabetica nunca roda. Reproduzido em worktree detached no commit
`2aea450c` — ANTES de qualquer codigo desta tarefa existir — com o mesmo aborto na mesma
linha (`88 passed`, mesmo `KeyboardInterrupt`). O diff desta tarefa em `__main__.py` toca
as linhas ~95, ~2191 e ~2355; `laco_da_agenda` vive em 1756-1973 e ficou byte-identica.
E problema aberto do repositorio, de outra area, e esta registrado aqui so para nao ser
confundido com regressao desta entrega.

**A suite no tronco ja mesclado**, com o arquivo que aborta fora do caminho
(`python -m pytest -q --ignore=tests/test_agenda.py`): **4698 passed, 2 skipped em
218,69 s**, saida 0. Os **2** skips batem com a linha de base historica do repositorio —
os 25 que o executor viu eram artefato de worktree (`recordings/` e `calibration.json`
sao gitignored e nao materializam la), como ele proprio registrou.
