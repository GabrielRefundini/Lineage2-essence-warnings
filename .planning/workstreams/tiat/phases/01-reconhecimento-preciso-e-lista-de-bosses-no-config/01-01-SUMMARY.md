---
phase: 01-reconhecimento-preciso-e-lista-de-bosses-no-config
workstream: tiat
plan: 01
subsystem: deteccao
tags: [regex, ocr, config-toml, tomllib, debounce, screen-reading]

requires:
  - phase: (nenhuma)
    provides: "primeira fase do workstream; parte de l2scanner/tiat.py, que ja funcionava"
provides:
  - "l2scanner/bosses.py — VigiaDeBosses, AvisoDeBoss, Boss, BossInvalido, padrao_do_anuncio, padrao_do_nome, _com_folga_de_ocr, _FOLGA_DE_OCR, _DIGITO_COM_FOLGA"
  - "l2scanner/config.py — ler_bosses, _boss_de_dict, _horas_de_respawn, _recusar_bosses_repetidos"
  - "l2scanner/__main__.py — montar_vigia_de_bosses(cal, na_janela, bosses)"
  - "l2scanner/sessao.py — Sessao(bosses=...), _processar_bosses, ResultadoDoTick.avisos_de_boss"
  - "config.toml — dois blocos [[boss]] (Tiat North e Tiat South, 6 e 8 horas)"
affects: [01-02, 01-03, 01-04, "Fase 2 (janela de respawn)"]

actuals:
  tokens: 19317
  tasks: 3
  commits: 7

tech-stack:
  added: []
  patterns:
    - "Padrao de OCR montado caractere a caractere com re.escape — texto de config nunca chega cru ao re.compile"
    - "Classe de digito tolerante a letra (_DIGITO_COM_FOLGA) no lugar de \\d+"
    - "Estado de debounce indexado por chave de dominio (dict por boss) em vez de flag global"
    - "avaliar devolve lista, nao Optional — um tick pode produzir N eventos"

key-files:
  created:
    - l2scanner/bosses.py
    - tests/test_bosses.py
  modified:
    - l2scanner/config.py
    - l2scanner/sessao.py
    - l2scanner/__main__.py
    - tests/test_sessao.py
    - config.toml
  deleted:
    - l2scanner/tiat.py
    - tests/test_tiat.py

key-decisions:
  - "D-09: a parte fixa da frase passa pela MESMA folga de OCR do nome; ! e colchetes opcionais; sem ancora de inicio de linha"
  - "D-10: a identidade do boss vem do [[boss]] do config.toml, procurada imediatamente antes de [Lv."
  - "D-11: o nivel entra no padrao (prova que a linha veio do servidor) e sai da decisao (casado e descartado)"
  - "D-12: o modulo vira bosses.py com VigiaDeBosses; os 7 testes migram sob contrato escrito"
  - "D-13: dois blocos [[boss]] separados, e nao um bloco com lista de nomes"
  - "D-14: a mensagem COMECA pelo nome do boss"
  - "calibracao.tiat_chat / tiat_alvo e frame.extras['tiat_chat'|'tiat_alvo'] NAO sao renomeados — renomear desligaria a vigilancia em silencio em todo calibration.json existente"
  - "A ordem das recusas do arranque poe lista vazia PRIMEIRO: e a recusa mais informativa"
  - "main() ganha except BossInvalido -> return 2; AgendaInvalida NAO e mexida nesta fase"

patterns-established:
  - "Folga de OCR bidirecional: a mesma tabela vale para o nome vindo do config e para a parte fixa da frase do servidor"
  - "Casamento LINHA A LINHA (splitlines) e nunca sobre o blob do OCR, para que \\s+ nao costure linhas de jogadores diferentes"
  - "Recusa de config espelhando _evento_de_dict: mesma forma de mensagem, mesma recusa de subir, arquivo ausente nao e erro"
  - "Booleano recusado ANTES do teste numerico, porque isinstance(True, int) e verdadeiro"

requirements-completed: [RECO-01, RECO-02, RECO-04, RECO-05, VIGI-01, VIGI-02, VIGI-04]

coverage:
  - id: D1
    description: "O alerta so sai quando o servidor anunciou um nascimento; chat digitado por jogador nao dispara"
    requirement: RECO-01
    verification:
      - kind: unit
        ref: "tests/test_bosses.py::TestOAnuncioDoServidorContraOChatDigitado"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py::TestOSeamDosBosses::test_a_pergunta_digitada_no_chat_nao_despacha_nada"
        status: pass
    human_judgment: false
  - id: D2
    description: "A mensagem nomeia QUAL boss nasceu, e o nome vem do config.toml e nunca do OCR"
    requirement: RECO-02
    verification:
      - kind: unit
        ref: "tests/test_bosses.py::TestAIdentidadeVemDoConfig"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py::TestOSeamDosBosses::test_o_anuncio_no_chat_vira_um_despacho_que_comeca_pelo_boss"
        status: pass
    human_judgment: false
  - id: D3
    description: "A frase degradada como o OCR degrada (T1a7 Nor7h [Lv. 8O]) produz o mesmo alerta"
    requirement: RECO-04
    verification:
      - kind: unit
        ref: "tests/test_bosses.py::test_trocas_classicas_do_ocr_ainda_encontram_o_nome"
        status: pass
      - kind: unit
        ref: "tests/test_bosses.py::TestOPadraoDoAnuncio"
        status: pass
    human_judgment: false
  - id: D4
    description: "O rearme e por boss; um tick pode entregar dois avisos"
    requirement: RECO-05
    verification:
      - kind: unit
        ref: "tests/test_bosses.py::TestORearmeEPorBoss"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py::TestOSeamDosBosses::test_chat_com_um_boss_e_alvo_com_outro_produzem_dois_despachos"
        status: pass
    human_judgment: false
  - id: D5
    description: "Quem e vigiado sai do codigo e vira um bloco [[boss]] no config.toml, lido e validado"
    requirement: VIGI-01
    verification:
      - kind: unit
        ref: "tests/test_bosses.py::TestLerBosses"
        status: pass
      - kind: integration
        ref: "tests/test_bosses.py::TestOConfigDoRepositorioProduzOAviso"
        status: pass
    human_judgment: false
  - id: D6
    description: "Um [[boss]] mal escrito derruba o arranque nomeando o boss e o campo, com codigo de saida 2"
    requirement: VIGI-02
    verification:
      - kind: unit
        ref: "tests/test_bosses.py::TestARecusaCitaOBossEOCampo"
        status: pass
      - kind: integration
        ref: "tests/test_bosses.py::TestOArranque::test_um_bloco_torto_derruba_o_arranque_com_codigo_2"
        status: pass
    human_judgment: false
  - id: D7
    description: "Sem nenhum [[boss]], o scanner SOBE e o console diz que a vigilancia esta desligada e como liga-la"
    requirement: VIGI-04
    verification:
      - kind: unit
        ref: "tests/test_bosses.py::TestOArranque::test_sem_bloco_nenhum_o_scanner_sobe_e_o_log_diz_como_ligar"
        status: pass
    human_judgment: false
  - id: D8
    description: "Verificacao de campo: a frase real do servidor, lida por OCR de verdade, dispara o alerta e a digitada nao"
    verification: []
    human_judgment: true
    rationale: "A frase `Tiat North [Lv. 60] has spawned!` e asserção do usuario a partir de um print, e nunca foi capturada pelo pipeline de OCR deste projeto. Toda a suite alimenta o vigia com texto ja decodificado — nenhum teste prova o que o Windows OCR realmente devolve para aquele recorte na fonte fina do jogo. O plano 01-04 constroi a ferramenta que confronta a frase real contra pixels; ate la, a folga de OCR e um palpite calibrado, nao uma medicao."

duration: 73min
completed: 2026-08-30
status: complete
---

# Phase 1 Plan 01: Reconhecimento preciso e lista de bosses no config — Summary

**O alerta de boss deixou de disparar com qualquer "tiat" no chat: agora exige a frase inteira do servidor (`<nome> [Lv. NN] has spawned`), nomeia qual boss nasceu, e quem e vigiado e uma linha do `config.toml` — dois blocos `[[boss]]` no arquivo, zero constantes de mob no codigo.**

## Performance

- **Duration:** ~73 min
- **Started:** 2026-08-30T16:50Z
- **Completed:** 2026-08-30T17:05Z (relogio de parede do agente; a duracao inclui as tres rodadas da suite inteira)
- **Tasks:** 3 de 3
- **Files modified:** 9 (2 criados, 5 modificados, 2 apagados pelo renomeio)
- **Suite:** 2143 passed / 14 skipped (baseline) -> **2197 passed / 14 skipped**. Zero testes existentes editados; zero enfraquecidos.

## Accomplishments

- **`l2scanner/bosses.py`** (renomeado de `tiat.py` com `git mv`, historico intacto): a folga de OCR agora e uma tabela de 10 letras aplicada CARACTERE A CARACTERE ao nome E a parte fixa da frase, com `re.escape` em cada caractere — o `nome` do `[[boss]]` nunca chega cru ao `re.compile`.
- **O debounce mudou de FORMA**: `_armado` e `_limpas` viraram `dict` indexados pelo nome do boss, e `avaliar` devolve `list[AvisoDeBoss]`. Um `Tiat South` alvejado durante os minutos em que o anuncio de `Tiat North` ainda persiste no chat deixou de ser engolido.
- **`ler_bosses` / `_boss_de_dict` em `config.py`**, espelhando `ler_agenda` / `_evento_de_dict`: arquivo ausente devolve `[]` e nao e erro; bloco torto derruba o arranque nomeando o boss e o campo; `main()` devolve 2 sem traceback.
- **A fatia vertical fecha nos dois extremos**: um teste le o `config.toml` DO REPOSITORIO com `ler_bosses`, monta o vigia com o resultado e afirma sobre `AvisoDeBoss.texto`; outro monta uma `Sessao` real e afirma sobre `resultado.despachos` com `Categoria.SEMPRE`.
- **O seam `_processar_bosses` ganhou teste** — ate aqui aquele caminho do tick nao tinha teste nenhum, que e exatamente a categoria de codigo que a docstring de `tests/test_sessao.py` acusa de ter produzido todos os bugs de integracao do projeto.

## Task Commits

| # | Tarefa | Commit | Tipo |
|---|--------|--------|------|
| 0 | O renomeio, sozinho, para preservar `git log --follow` nos DOIS arquivos | `c49b679` | refactor |
| 1 | Task 1 RED — a regua nova (7 migrados + guardas de RECO-01/02/04/05 + `ler_bosses`) | `b7622f9` | test |
| 1 | Task 1 GREEN — `bosses.py`, `ler_bosses`, os dois `[[boss]]`, o import de `__main__` | `4f7a05c` | feat |
| 2 | Task 2 RED — o seam `_processar_bosses` ganha teste | `fed7c91` | test |
| 2 | Task 2 GREEN — a costura do tick, `avisos_de_boss`, `Sessao(bosses=)` | `9d961e9` | feat |
| 3 | Task 3 RED — o arranque, `montar_vigia_de_bosses`, o tripwire de simbolo antigo | `7228192` | test |
| 3 | Task 3 GREEN — a ordem das recusas, a linha que nomeia, `except BossInvalido` | `289b50a` | feat |

## 1. A tabela dos sete pares (OBRIGATORIA — D-12)

O `git mv` levou os originais de `tests/test_tiat.py` embora. Sem esta tabela a categoria (b) do contrato so seria revisavel relendo o diff inteiro contra arquivos que o revisor da fase nao tem mais. Os literais abaixo sao os que entram no `Leitor`, na ordem `chat` e depois `alvo`.

| # | Teste (nome preservado literalmente) | Literal ANTIGO | Literal NOVO | Intencao preservada |
|---|---|---|---|---|
| 1 | `test_detecta_o_anuncio_no_chat` | chat: `"Raid boss Tiat has appeared"` | chat: `"Tiat North [Lv. 60] has spawned!"` | **devia disparar** -> anuncio COMPLETO de um boss do roster |
| 1 | (mesmo teste, segundo literal) | alvo: `"Orc"` | alvo: `"Orc"` — **inalterado** | **nao devia disparar** -> continua nao sendo o nome de nenhum boss |
| 2 | `test_detecta_quando_o_alvo_vira_tiat_mesmo_sem_anuncio_no_chat` | chat: `"mensagem comum"` | chat: `"mensagem comum"` — **inalterado** | **nao devia disparar** -> continua nao sendo anuncio |
| 2 | (mesmo teste, segundo literal) | alvo: `"Tiat"` | alvo: `"Tiat North"` | **devia disparar** -> no recorte do ALVO, o nome COMPLETO do boss do roster |
| 3 | `test_sinais_juntos_geram_uma_mensagem_combinada` | chat: `"TIAT apareceu"` / alvo: `"Tiat"` | chat: `"Tiat North [Lv. 60] has spawned!"` / alvo: `"Tiat North"` | **os dois deviam disparar** -> anuncio completo no chat, nome completo no alvo; a origem continua `CHAT_E_ALVO` |
| 4 | `test_trocas_classicas_do_ocr_ainda_encontram_o_nome` | chat: `"T1A7 apareceu"` | chat: `"T1a7 Nor7h [Lv. 8O] has spawned!"` | **devia disparar** -> continua sendo o caso "OCR degradou o nome", agora com a frase inteira degradada (e o exemplo literal do criterio 3 do ROADMAP) |
| 4 | (mesmo teste, segundo literal) | alvo: `"nenhum"` | alvo: `"nenhum"` — **inalterado** | **nao devia disparar** |
| 5 | `test_persistencia_do_chat_ou_alvo_nunca_spamma` | chat: `["Tiat"]*3` / alvo: `["Tiat"]*3` | chat: `[ANUNCIO]*3` / alvo: `["Tiat North"]*3` | **os seis deviam disparar**, nas mesmas seis posicoes; a asseracao `== 1` continua `== 1` |
| 6 | `test_so_rearma_depois_de_duas_leituras_limpas` | chat: `["Tiat", "", "", "Tiat"]` | chat: `[ANUNCIO, "", "", ANUNCIO]` | posicoes 1 e 4 **deviam disparar**; posicoes 2 e 3 eram **leitura limpa** (string vazia) e **continuam vazias byte a byte** |
| 6 | (mesmo teste, segundo literal) | alvo: `["", "", "", ""]` | alvo: `["", "", "", ""]` — **inalterado** | **leitura limpa** nas quatro posicoes |
| 7 | `test_falha_do_ocr_nao_derruba_o_vigia` | (nao usa `Leitor`; `ler_texto` levanta) | idem — o callable que levanta e **inalterado** | **nenhum literal**; a intencao e "o `except` do OCR nao derruba o tick" |

**Onde `ANUNCIO` = `"Tiat North [Lv. 60] has spawned!"`** — a frase real medida do print do usuario em 2026-08-30. Nenhum literal mudou de POSICAO na sequencia do `Leitor`: o terceiro texto continua sendo o terceiro texto.

### O diff da migracao, categoria por categoria

**(a) A linha de import.** `from l2scanner.tiat import OrigemDoTiat, VigiaDoTiat` -> `from l2scanner.bosses import Boss, BossInvalido, OrigemDoAviso, VigiaDeBosses, padrao_do_anuncio, padrao_do_nome` mais `from l2scanner.config import ler_bosses`. Os simbolos extras servem os testes NOVOS; os 7 migrados usam apenas `OrigemDoAviso`, `VigiaDeBosses` e `Boss`.

**(b) Os literais de entrada.** Exatamente a tabela acima. Quatro dos sete tiveram literal de chat trocado (1, 3, 4, 5, 6 — cinco, contando o 6); dois tiveram literal de alvo trocado (2, 3, 5); os demais ficaram inalterados. Todo literal que "nao devia disparar" e toda string vazia sobreviveram byte a byte.

**(c) A adaptacao de lista.** Tres formas, sempre na direcao MAIS FORTE:

| Teste | Antes | Depois |
|---|---|---|
| 1, 2, 3 | `aviso = v.avaliar(...)` + `assert aviso is not None` + `aviso.origem` | `avisos = v.avaliar(...)` + `assert len(avisos) == 1` + `avisos[0].origem` |
| 4 | `assert v.avaliar(...) is not None` | `assert len(v.avaliar(...)) == 1` |
| 5 | `sum(aviso is not None for aviso in avisos) == 1` | `sum(len(aviso) for aviso in avisos) == 1` — conta AVISOS, e nao ticks-com-aviso |
| 6 | `[a is not None for a in avisos] == [True, False, False, True]` | `[bool(a) for a in avisos] == [True, False, False, True]` — **lado direito byte a byte** |
| 7 | `assert v.avaliar(...) is None` | `assert v.avaliar(...) == []` |

**A aritmetica do debounce sobreviveu:** o `== 1` do teste 5 continua `== 1`; a lista de quatro booleanos do teste 6 continua `[True, False, False, True]`, na mesma ordem; `leituras_limpas_para_rearmar=2` e `segundos_entre_leituras=1` inalterados. **Nenhuma asseracao foi enfraquecida.**

### O desvio do contrato, e a razao escrita

**Uma quarta categoria de edicao mecanica foi usada, em UM teste, e ela deixa a asseracao mais forte — nunca mais fraca.**

`test_falha_do_ocr_nao_derruba_o_vigia` constroi o vigia DIRETO (`VigiaDoTiat(explode)`), e nao pelo helper `vigia(...)` que o plano autorizou a ganhar um roster padrao. Com `bosses=()` — o default — aquele vigia nao tem boss nenhum para avaliar, entao `avaliar` devolveria `[]` **mesmo que o `except` do OCR tivesse sido apagado**: a asseracao viraria vazia e o teste passaria provando nada. A construcao virou `VigiaDeBosses(explode, bosses=(NORTH,))`, que e o mesmo roster que o helper recebeu, aplicado no segundo ponto de construcao do arquivo. A razao esta escrita na docstring de modulo de `tests/test_bosses.py`, ao lado do contrato.

Um segundo ajuste, este fora dos 7 e sem relacao com o contrato: `TestOArranque.montar` **forca** `ocr.disponivel` nos dois sentidos em vez de herdar o ambiente. As bindings de OCR do Windows nao estao instaladas onde esta suite roda (sao a causa dos 14 skips do baseline), entao sem forcar o caminho "tudo pronto" nunca seria exercitado e dois testes passariam sem provar nada.

## 2. `_FOLGA_DE_OCR` e `_DIGITO_COM_FOLGA` como ficaram

A Fase 2 e o plano 01-04 dependem destes valores exatos.

```python
_FOLGA_DE_OCR: dict[str, str] = {
    "a": "aA4@",
    "b": "bB8",
    "e": "eE3",
    "g": "gG69",
    "i": "iI1l|",
    "l": "lL1I|",
    "o": "oO0Q",
    "s": "sS5$",
    "t": "tT7+",
    "z": "zZ2",
}

_DIGITO_COM_FOLGA = "0123456789OoQDlI|iSsZzBbgGAa"
```

**Como sao consumidas.** `_com_folga_de_ocr(texto)` percorre o texto caractere a caractere: espaco vira `\s+`; letra presente na tabela vira uma classe montada com `re.escape` sobre os caracteres do valor; **qualquer outro caractere vira `re.escape(caractere)`**. `_DIGITO_COM_FOLGA` vira uma classe pela mesma rotina (`_classe`) e e repetida `{1,3}`.

**O `\d+` esta PROIBIDO para o nivel, e o motivo esta escrito ao lado da constante:** o criterio 3 da fase exige que `T1a7 Nor7h [Lv. 8O] has spawned!` produza o mesmo alerta, e ali o segundo caractere do nivel e a **letra O**. Um `\d+` reprovaria naquele criterio — e reprovaria em silencio, que e o modo de falha caro (T-01-05). As duas unicas ocorrencias da sequencia `\d+` em `l2scanner/bosses.py` estao dentro do comentario que explica por que ela nao e usada.

**A forma do `padrao_do_anuncio`**, na ordem exata da concatenacao:

```
<nome com folga>  \s*  [\[\(\{]?  \s*  <"Lv" com folga>  \s*\.?\s*
<classe de digito tolerante>{1,3}  \s*  [\]\)\}]?  \s*
<"has spawned" com folga>  \s*  !?
```

com `re.IGNORECASE` e **sem `^`**. O nivel e o unico elemento obrigatorio alem do nome e de `has spawned`: e ele que separa o anuncio do servidor da linha digitada por um jogador.

## 3. Risco aberto para o roadmap — a origem ALVO nao prova nascimento

**Anotado aqui de proposito, como o plano exige, porque na Fase 2 ele muda de severidade.**

Hoje a origem `ALVO` produz o texto `<boss> nasceu! (seu alvo virou <boss>)`. **O alvo estar selecionado nao prova que o boss acabou de nascer** — o jogador pode ter alvejado um boss que esta vivo ha tres horas, ou clicado nele de passagem. E o texto travado em D-14 e fica como esta nesta fase, porque o custo de um erro aqui e uma mensagem inutil que um humano descarta.

**Na Fase 2 o custo muda de natureza.** O mesmo sinal passa a ser a ANCORA de uma contagem de 6 a 8 horas, e uma ancora errada produz uma previsao errada entregue horas depois, que a party nao tem como distinguir de uma certa. **A Fase 2 precisa decidir EXPLICITAMENTE se a origem `ALVO` tem direito de ancorar a contagem** — a leitura defensavel e que so `CHAT` (o anuncio do servidor) ancore, e que `ALVO` continue avisando sem ancorar. A decisao nao pode ser herdada por omissao.

O registro de ameacas ja antecipa a mesma inversao para T-01-01 (spoofing por jogador digitando a frase exata): `medium` / `accept` nesta fase, **`high` na Fase 2**, com reavaliacao obrigatoria antes de a ancora duravel existir. A alavanca registrada e nao usada continua disponivel: a linha do servidor sai em cor de sistema (laranja), distinta do texto dos jogadores.

## Files Created/Modified

- `l2scanner/bosses.py` — **criado por `git mv` de `l2scanner/tiat.py`**, depois reescrito em cima do conteudo movido. Reconhecimento, identidade e debounce por boss.
- `tests/test_bosses.py` — **criado por `git mv` de `tests/test_tiat.py`**. 55 testes: os 7 migrados, o par de guarda da mudanca de forma, as duas direcoes de RECO-01/RECO-04, `ler_bosses`, a fatia vertical contra o `config.toml` do repositorio, e o arranque.
- `l2scanner/config.py` — `ler_bosses`, `_boss_de_dict`, `_horas_de_respawn`, `_recusar_bosses_repetidos`; importa `Boss` e `BossInvalido` de `bosses`.
- `l2scanner/sessao.py` — kwarg `bosses=`, `self.bosses`, `_processar_bosses`, `ResultadoDoTick.avisos_de_boss` (pares `(boss, origem)`).
- `l2scanner/__main__.py` — `montar_vigia_de_bosses`, `ler_bosses()` em `laco_principal`, `except BossInvalido -> return 2` em `main()`.
- `tests/test_sessao.py` — `bosses=None` em `nova_sessao`, mais `TestOSeamDosBosses` (6 testes).
- `config.toml` — os dois blocos `[[boss]]` ao FINAL do arquivo, com cabecalho em comentario.

**Apagados pelo renomeio:** `l2scanner/tiat.py`, `tests/test_tiat.py`, `_TIAT`, `OrigemDoTiat`, `AvisoDeTiat`, `VigiaDoTiat`, `montar_vigia_do_tiat`.

**NAO mudaram de nome, deliberadamente:** `Calibracao.tiat_chat`, `Calibracao.tiat_alvo`, as chaves de mesmo nome no `calibration.json`, `frame.extras['tiat_chat'|'tiat_alvo']`, a flag `--tiat` e o `calibrar-tiat.bat`.

## Decisions Made

Todas as seis decisoes travadas do CONTEXT (D-09 a D-14) foram implementadas como escritas. As decisoes tomadas na execucao, dentro da discricao que o CONTEXT concedeu:

1. **A folga de OCR e uma tabela de substituicao percorrida caractere a caractere**, e nao uma regex por caractere escrita a mao. O CONTEXT deixou a escolha aberta "desde que valha para o nome E para a parte fixa" — a tabela vale para os dois porque a mesma funcao monta os dois lados, o que torna estruturalmente impossivel apertar um sem apertar o outro.
2. **`VigiaDeBosses` recebe os bosses NO CONSTRUTOR**, e pre-compila os dois padroes por boss ali. Nao e micro-otimizacao: e o que garante que um `nome` malformado exploda no ARRANQUE, com o usuario olhando para o console, e nao as 3h da manha.
3. **`Boss` e `BossInvalido` moram em `bosses.py`**, e nao em `config.py`, pela direcao de importacao ja fixa no pacote — `bosses` importa so stdlib. Mesmo raciocinio que trouxe `Membro` para `comandos.py`.
4. **Zero e recusado junto com negativo** nos campos de respawn: uma regra de respawn de zero hora nao descreve nada, e uma mensagem so e mais clara que duas parecidas.
5. **Nomes de boss repetidos sao recusados ignorando a caixa** (`casefold`), porque o padrao de reconhecimento e `IGNORECASE` — dois blocos que so diferem na caixa vigiariam o mesmo mob e cada nascimento sairia em dobro. Na Fase 2 dividiriam a mesma ancora em disco.
6. **O renomeio virou um commit proprio** (`c49b679`), antes do RED. Com a reescrita junto, a similaridade cai abaixo do limiar de deteccao do git e o renomeio e registrado como apagar+criar — e `git log --follow tests/test_bosses.py` perderia a historia do debounce. Os dois arquivos agora seguem ate `05696e5 feat: alert when Tiat appears`.

## Deviations from Plan

### 1. [Contrato D-12, categoria nova] O roster foi acrescentado a construcao direta em `test_falha_do_ocr_nao_derruba_o_vigia`

- **Encontrado durante:** Task 1
- **Problema:** O contrato autoriza o helper `vigia(...)` a ganhar um roster padrao, mas este teste constroi o vigia direto. Com roster vazio, `avaliar` devolve `[]` mesmo com o `except` do OCR apagado — a asseracao ficaria VAZIA.
- **Solucao:** `VigiaDeBosses(explode, bosses=(NORTH,))`. Mesmo roster do helper, no segundo ponto de construcao do arquivo. Deixa a asseracao mais forte, nunca mais fraca.
- **Escrito onde alguem vai olhar:** docstring de modulo de `tests/test_bosses.py`, ao lado do contrato.

### 2. [Rule 3 - Bloqueio] `TestOArranque` forca `ocr.disponivel` em vez de herdar o ambiente

- **Encontrado durante:** Task 3
- **Problema:** Os dois testes do caminho "tudo pronto" falharam porque as bindings de OCR do Windows nao estao instaladas onde a suite roda (mesma causa dos 14 skips do baseline). Herdar o ambiente faria o caminho feliz nunca ser exercitado nesta maquina.
- **Solucao:** o helper `montar` patcha `principal.ocr.disponivel` nos DOIS sentidos e restaura no `finally`. A razao esta na docstring do helper.
- **Commit:** `289b50a`

### 3. [Estrutura de commits] O renomeio virou um commit proprio, fora do ciclo RED/GREEN

- **Encontrado durante:** Task 1
- **Problema:** Com `git mv` e reescrita no mesmo commit, o git registrava `tests/test_tiat.py` como apagado e `tests/test_bosses.py` como criado — a historia do debounce nao sobreviveria ao `--follow` no arquivo de teste, que e justamente o ativo que D-12 protege.
- **Solucao:** `c49b679` move os dois arquivos e corrige APENAS as duas linhas de import, com a suite verde. O RED (`b7622f9`) vem depois.
- **Verificado:** `git log --follow` nos dois arquivos alcanca `05696e5`.

---

**Total de desvios:** 3 (1 do contrato de migracao, com justificativa exigida e escrita; 1 Rule 3; 1 estrutural). **Nenhum enfraquece asseracao, nenhum expande escopo.**

## Issues Encountered

**A suite baseline mediu 2143 passed / 14 skipped, e nao os 2155 passed / 2 skipped que o briefing anunciava.** O total coletado bate (2157); a diferenca esta na coluna de skips e vem do ambiente — as bindings de OCR do Windows nao estao instaladas neste worktree, entao 12 testes que dependem delas pulam em vez de rodar. Nenhum teste falha por isso, e a diferenca existia ANTES da primeira linha deste plano. Registrado aqui porque quem comparar os numeros depois vai tropecar nele; a comparacao valida e 2143 -> 2197 na mesma maquina.

## Known Stubs

Nenhum. Nao ha valor codificado que chegue a UI, nem componente sem fonte de dados, nem `TODO`/`FIXME` introduzido por este plano. Os campos `respawn_horas_min` / `respawn_horas_max` sao lidos, **validados** e nao usados nesta fase — isso e escopo declarado (a Fase 2 os consome), esta escrito na docstring do dataclass `Boss` e no cabecalho do `config.toml`, e tem o precedente nomeado de `silenciar_minutos` na Fase 6. Nao e stub: o dado atravessa a validacao inteira e o arranque recusa um valor torto.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. As quatro mitigacoes `mitigate` do registro estao implementadas e afirmadas:

| Ameaca | Mitigacao implementada | Teste |
|---|---|---|
| T-01-02 (costura de linhas) | `splitlines()` — casamento linha a linha, nunca no blob | `test_a_frase_e_casada_linha_A_linha_e_nunca_no_blob` |
| T-01-03 (`nome` cru no `re.compile`) | `_com_folga_de_ocr` monta com `re.escape` caractere a caractere | `TestONomeDoConfigNaoViraCuringa` (4 testes) |
| T-01-04 (OCR vazando para o WhatsApp) | o nome interpolado vem sempre do config; o texto lido e predicado booleano descartado | `test_o_nome_da_mensagem_vem_do_config_e_nunca_do_texto_lido` |
| T-01-05 (falso negativo silencioso) | `!` e colchetes opcionais, digito tolerante, folga na parte fixa, sem `^` | `TestOAnuncioDoServidorContraOChatDigitado` (7 testes, os dois sentidos) |

T-01-01 (jogador digitando a frase exata) segue `accept`, como o plano decidiu — **e precisa ser reavaliado na Fase 2**, onde vira `high`. Ver a secao 3 acima.

## Verification

| Comando | Resultado |
|---|---|
| `python -m pytest tests/ -q` | **2197 passed, 14 skipped** (baseline 2143 / 14) |
| `python -m pytest tests/test_bosses.py tests/test_sessao.py -q` | 55 + 59 = **114 passed** |
| `python -c "import l2scanner.__main__"` | OK |
| `git log --follow l2scanner/bosses.py` | alcanca `05696e5 feat: alert when Tiat appears` |
| `git log --follow tests/test_bosses.py` | alcanca `05696e5` |
| `python -c "...ler_bosses()..."` | `[('Tiat North', 6.0, 8.0), ('Tiat South', 6.0, 8.0)]` |
| `git diff --stat -- requirements.txt` | vazio — **nenhuma dependencia nova** |
| `git diff --stat -- l2scanner/ponte_*.py l2scanner/mercado_*.py l2scanner/calibrar_mercado.py` | vazio — **nenhum arquivo de workstream paralelo tocado** |
| `git diff --stat -- .planning/` | vazio — STATE.md e ROADMAP.md sao do orquestrador |

## Self-Check

Executado antes de escrever esta secao.

**Arquivos afirmados como criados:**
- `l2scanner/bosses.py` — FOUND
- `tests/test_bosses.py` — FOUND
- `.planning/workstreams/tiat/phases/01-.../01-01-SUMMARY.md` — FOUND

**Arquivos afirmados como apagados:**
- `l2scanner/tiat.py` — ausente, como esperado
- `tests/test_tiat.py` — ausente, como esperado

**Commits afirmados:** `c49b679`, `b7622f9`, `4f7a05c`, `fed7c91`, `9d961e9`, `7228192`, `289b50a` — todos os 7 FOUND em `git log`.

## Self-Check: PASSED
