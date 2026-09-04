---
phase: quick-20260904
plan: 01
subsystem: renda
type: tdd
autonomous: true
tags: [renda, painel, adena, pack, REND-05, CONS-01]
requirements: []
---

# Quick 20260904: O ETA do proximo pack de adena no painel do `--renda`

## Objetivo

O bloco por intervalo do `--renda` passa a responder **"quando fecha o proximo pack
de adena"**, do mesmo jeito e com o mesmo vocabulario com que ele ja responde
"quando eu subo de nivel".

Tres das quatro coisas que o usuario pediu ja existem e nao se mexe nelas: o nick
do char (no titulo do bloco, `RENDA - TioMad`), o EXP como NUMERO
(`renda_console.linha_do_tique`, e ele CONTINUA numero — nao se desenha barra) e o
total de adena. Falta so o ETA do pack.

## O que "fechar o proximo pack" quer dizer, com o numero do usuario

Com **27.309.465** de adena e um pack de **5.000.000**, cinco packs estao fechados
(25.000.000) e o **sexto fecha em 30.000.000**. Faltam **2.690.535**. A taxa medida
da janela curta e ~**466 mil/h** (`03-CONTEXT.md`), entao:

    2.690.535 x 3600 / 466.000 = 20.785,25 s = 5h46m25s  ->  `5h46`

O usuario disse "~5h47" de cabeca; `duracao_curta` TRUNCA (nunca arredonda para
cima, porque truncar nunca superestima a renda), entao a tela diz `5h46`. Os dois
numeros ficam escritos no teste, lado a lado, para ninguem "consertar" o truncamento.

**O alvo e o proximo multiplo ESTRITAMENTE MAIOR**, e nao um teto:
`alvo = (adena // pack + 1) * pack`. Com exatamente 25.000.000 na bolsa, um `ceil`
devolveria 25.000.000, "faltam 0" e um ETA de zero segundo — uma previsao com cara
de certa dizendo que o usuario ja tem o que ainda nao tem. Com o multiplo
estritamente maior, `faltam` e SEMPRE >= 1 e o zero no numerador nunca existe.

## Contexto

- @l2scanner/renda_conta.py — `tempo_ate_o_nivel` / `TempoAteONivel` sao o molde
  EXATO. Copia-se a forma, nao se inventa uma segunda maneira de dizer um ETA.
- @l2scanner/renda_console.py — `bloco_da_renda`, `_linhas_do_eta`, `_linha`,
  `_dobrar`, `duracao_curta`, `_grafia_curta`, `COLUNA_DO_ROTULO=32`,
  `LARGURA_DO_BLOCO=76`.
- @l2scanner/renda_laco.py — `_tempo_ate_o_nivel` (o molde da casca) e a chamada de
  `bloco_da_renda`.
- @l2scanner/config.py — `AjustesDaRenda`, `_inteiro_da_renda`, `_EXEMPLO_DA_RENDA`.
- @.claude/CLAUDE.md — Licoes 1, 2, 3, 4 e 6.

### Os tres numeros iguais a 5.000.000, e eles sao TRES fatos diferentes

Ja existem dois `5_000_000` na arvore, e a decisao de mante-los separados ja foi
tomada e escrita (`quick/260903-bd8`: *"`UNIDADE_DA_TAXA` e `ADENA_POR_INCREMENTO`
continuam DUAS constantes apesar de valerem o mesmo"*):

| onde | o que e | quem pode mudar |
|---|---|---|
| `mercado_console.UNIDADE_DA_TAXA` | a ESCALA EM QUE A TAXA SE FALA na tela do mercado | ninguem: e a coluna `5 mln increment` do jogo |
| `mercado_leitura.ADENA_POR_INCREMENTO` | o TAMANHO DO INCREMENTO que o World Exchange vende | ninguem: idem |
| **`AjustesDaRenda.tamanho_do_pack_de_adena` (NOVO)** | **a META DE FARM do usuario** | **o usuario, e e o unico dos tres que ele ajusta** |

O terceiro entra como chave de config e nao como constante importada porque ele e o
unico que responde a uma pergunta do USUARIO ("de quanto em quanto eu quero ser
avisado"), e nao ao formato do jogo. Reusar `ADENA_POR_INCREMENTO` amarraria a meta
de farm a uma coluna de UI do mercado: no dia em que o jogo virasse `10 mln`, a meta
do usuario mudaria sozinha sem ninguem decidir.

### A cerca das CINCO chaves cai, e ela diz por que caiu (Licao 6)

`tests/test_renda_no_main.py::test_a_secao_renda_continua_com_CINCO_chaves` afirma
hoje que `AjustesDaRenda` tem EXATAMENTE cinco campos. A razao escrita ao lado dela e
especifica e continua verdadeira:

> *"A cadencia ja tem dois argumentos de linha de comando (`--intervalo`,
> `--status-a-cada`) e inventar a chave duplicaria a verdade sobre ela."*

Essa cerca e sobre **CADENCIA**, e o tamanho do pack nao e cadencia: ele nao tem
nenhuma outra casa hoje, e sem ele o numero seria constante magica em
`l2scanner/*.py` — que e exatamente o que o pedido proibe. A cerca **continua sendo
de conjunto exato** (uma setima chave ainda a derruba); o que muda e o conjunto, e a
razao antiga fica escrita no lugar, ao lado da nova.

## Tarefas

<task id="1" type="auto" tdd="true">
  <name>A conta: `tempo_ate_o_pack`, o gemeo de `tempo_ate_o_nivel`</name>
  <files>l2scanner/renda_conta.py, tests/test_renda_conta.py</files>
  <behavior>
    Em `tests/test_renda_conta.py`, uma classe `TestOTempoAteOProximoPackDeAdena`,
    no molde de `TestOTempoAteOProximoNivel` e usando as MESMAS fabricas de
    sequencia que ja existem no arquivo (`passos_dos_campos`, `sequencia_regular`) —
    nunca um `TaxaDaRenda` montado a mao quando a producao consegue produzir um:

    1. `test_O_ALVO_E_O_PROXIMO_MULTIPLO_E_O_ETA_SAI_EM_SEGUNDOS` — com a adena real
       do usuario (27.309.465), pack 5.000.000 e a taxa de adena de uma sequencia
       real: `alvo == 30_000_000`, `faltam == 2_690_535`, e `segundos` igual a
       `Fraction(faltam * 3600, por_hora)` calculado a mao no teste, com a conta
       escrita por extenso.
    2. `test_COM_UM_PACK_JA_FECHADO_O_ALVO_E_O_SEGUINTE_E_NUNCA_ZERO` — adena
       EXATAMENTE 25.000.000: `alvo == 30_000_000`, `faltam == 5_000_000`,
       `segundos > 0`. Este teste e o que mata a implementacao com `ceil`.
    3. `test_COM_A_TAXA_DE_ADENA_ZERADA_O_MOTIVO_E_NOMEADO_E_NAO_HA_DIVISAO` —
       `segundos is None` e `motivo == MOTIVO_DA_TAXA_DE_ADENA_ZERADA`.
    4. `test_COM_A_TAXA_NEGATIVA_O_MOTIVO_E_OUTRO` — `MOTIVO_DA_TAXA_DE_ADENA_NEGATIVA`.
       Este e o UNICO caso que precisa de um `TaxaDaRenda` construido a mao, e a
       razao vai escrita na docstring do teste: `_adena_do_par` devolve ganho `>= 0`
       nos DOIS unicos caminhos que produzem `ganho_de_adena`
       (`renda_conta.py:549` e `:742`), entao uma taxa de adena negativa e HOJE
       inalcancavel pela producao. O ramo existe como guarda estrutural — um
       divisor negativo devolveria um ETA NEGATIVO, uma previsao apontando para o
       passado —, e o teste afirma o ramo dizendo que ele e inalcancavel.
    5. `test_COM_EVIDENCIA_INSUFICIENTE_O_MOTIVO_HERDA_O_DA_TAXA` — o motivo e o
       `motivo_da_ausencia` da propria taxa, e `"amostras_minimas_para_taxa"` aparece
       nele.
    6. `test_OS_TRES_MOTIVOS_DE_AUSENCIA_SAO_TEXTOS_DIFERENTES` — `len({...}) == 3`.
    7. `test_ALVO_E_FALTAM_EXISTEM_MESMO_SEM_ETA` — com a taxa sem numero, `alvo` e
       `faltam` continuam preenchidos: eles nao dependem da taxa, e apaga-los faria o
       painel esconder uma conta que ele sabe fazer.
    8. `test_UM_PACK_DE_TAMANHO_INVALIDO_LEVANTA_E_NAO_DIVIDE` — `tamanho_do_pack=0`
       levanta `ValueError`. Quem sabe que a conta nao pode ser feita nao a faz.
    9. `test_OS_DOIS_MOTIVOS_NOVOS_ENTRAM_NO_PORTAO_DA_DISTINCAO` — nao e teste novo:
       `TestOPortaoDaDistincaoDosMotivosDaConta` ja varre `MOTIVO_*` do modulo e tem
       de continuar verde com os dois nomes novos.
  </behavior>
  <implementation>
    Em `l2scanner/renda_conta.py`, ao lado de `tempo_ate_o_nivel`:

    - `MOTIVO_DA_TAXA_DE_ADENA_ZERADA = "taxa-de-adena-zerada"` e
      `MOTIVO_DA_TAXA_DE_ADENA_NEGATIVA = "taxa-de-adena-negativa"`, com o mesmo
      comentario de tres consertos que os do EXP tem.
    - `@dataclass(frozen=True) class TempoAteOPack` com
      `tamanho_do_pack: int`, `adena_atual: int | None`, `alvo: int | None`,
      `faltam: int | None`, `segundos: Fraction | None`, `motivo_da_ausencia: str | None`.
      Os quatro primeiros existem para a tela poder MOSTRAR A CONTA (D-02: um numero
      que o usuario nao pode conferir e um numero que ele nao pode confiar).
    - `def tempo_ate_o_pack(*, adena_atual: int, tamanho_do_pack: int, taxa: TaxaDaRenda) -> TempoAteOPack`.
      `ValueError` se `tamanho_do_pack <= 0`. `alvo = (adena // pack + 1) * pack`.
      As tres ausencias tratadas ANTES da divisao, na ordem evidencia -> zero ->
      negativo, exatamente como o gemeo. `Fraction`, nunca `float`.
    - Nada de `math.inf` e nada de `except ZeroDivisionError`: o portao de arvore de
      sintaxe de `TestOTempoAteOProximoNivel` varre o modulo INTEIRO e continua valendo.
  </implementation>
  <verify>
    `python -m pytest -q tests/test_renda_conta.py tests/test_renda_par.py` verde.
    MUTACAO: trocar `(adena // pack + 1) * pack` por `math.ceil`-equivalente
    (`-(-adena // pack) * pack`) tem de deixar o teste 2 VERMELHO.
    CONTROLE: extrair o alvo para uma funcao nomeada tem de ficar VERDE.
  </verify>
  <done>Os nove criterios acima passam e o resto do arquivo continua verde.</done>
</task>

<task id="2" type="auto" tdd="true">
  <name>A casca: a sexta chave de `[renda]` e o `--pack-de-adena` que a vence</name>
  <files>
    l2scanner/config.py, l2scanner/__main__.py, l2scanner/renda_laco.py,
    config.toml, tests/test_config_da_renda.py, tests/test_renda_no_main.py
  </files>
  <behavior>
    1. `tests/test_config_da_renda.py`: sem arquivo / sem secao / sem a chave, o
       default e `5_000_000`; com `tamanho_do_pack_de_adena = 10000000` ele chega;
       `0`, `-1`, `true` e `5000.5` sao recusados por `_inteiro_da_renda` com a
       mensagem que MOSTRA a secao pronta (o `_EXEMPLO_DA_RENDA` cresce junto e o
       teste afirma que a chave nova aparece nele).
    2. `tests/test_renda_no_main.py`: a cerca vira
       `test_a_secao_renda_tem_SEIS_chaves_e_a_SEXTA_tem_nome`, com o conjunto exato
       de seis e a razao antiga (cadencia) preservada na mensagem ao lado da nova.
    3. `tests/test_renda_no_main.py`: `--pack-de-adena 3000000` CHEGA em
       `args.pack_de_adena` no laco (mesmo molde de
       `test_os_valores_pedidos_na_linha_de_comando_CHEGAM`); sem a flag ele e `None`.
    4. `tests/test_renda_laco.py`: uma classe nova mede a PRECEDENCIA — com
       `--pack-de-adena` presente o valor usado e o da linha de comando, e o log traz
       UMA linha que NOMEIA o vencedor e cita os dois numeros; sem a flag, nada e
       logado e o valor e o do config. O molde e a regra ja escrita para
       `config.local.toml` vencendo *"com aviso que NOMEIA o vencedor"*.
  </behavior>
  <implementation>
    - `config.py`: `CHAVE_DO_TAMANHO_DO_PACK = "tamanho_do_pack_de_adena"`, campo
      `tamanho_do_pack_de_adena: int = 5_000_000` em `AjustesDaRenda` com a razao do
      default escrita (a coluna `5 mln increment` do jogo, que e o que o usuario
      chama de "pack de +5kk"), a leitura por `_inteiro_da_renda` e a sexta linha do
      `_EXEMPLO_DA_RENDA`. Os textos que dizem "os cinco numeros" viram "os seis".
    - `__main__.py`: `--pack-de-adena`, `type=int`, `default=None`, `dest="pack_de_adena"`,
      help dizendo que ele vence a chave do `config.toml` SO NESTA RODADA.
    - `renda_laco.py`: logo depois de `ler_ajustes_da_renda()`, uma funcao
      `_com_o_pack_da_linha_de_comando(ajustes, args)` que usa
      `getattr(args, "pack_de_adena", None)` (os `argparse.Namespace` dos testes
      existentes nao tem o campo, e um `AttributeError` derrubaria o laco),
      `dataclasses.replace`, e um `log.info` que nomeia o vencedor quando os dois
      numeros diferem. Valor `<= 0` na linha de comando recusa o ARRANQUE com a
      mesma frase da secao — a linha de comando nao pode ser mais frouxa que o arquivo.
    - `config.toml`: a sexta linha entra no bloco `[renda]` COMENTADO, junto das outras.
  </implementation>
  <verify>
    `python -m pytest -q tests/test_config_da_renda.py tests/test_renda_no_main.py tests/test_renda_laco.py` verde.
    MUTACAO: fazer a precedencia ao contrario (config vence a flag) tem de deixar o
    teste 4 VERMELHO.
  </verify>
  <done>A chave e a flag chegam; a cerca de conjunto exato continua de pe, com seis.</done>
</task>

<task id="3" type="auto" tdd="true">
  <name>A tela: a secao do proximo pack no bloco por intervalo</name>
  <files>
    l2scanner/renda_console.py, l2scanner/renda_laco.py, tests/test_renda_console.py
  </files>
  <behavior>
    Em `tests/test_renda_console.py`, `TestOProximoPackDeAdena`:

    1. `test_A_CONTA_INTEIRA_APARECE_E_NAO_SO_A_RESPOSTA` — as quatro linhas trazem
       `27.309.465`, `30.000.000`, `2.690.535` e `5h46`, cada uma com rotulo proprio.
    2. `test_O_TAMANHO_DO_PACK_CONFIGURADO_APARECE_NO_TITULO` — com pack de 10.000.000
       o titulo diz `10,00 M` e nao `5,00 M`. Sem isso o usuario nao tem como saber
       de que pack a tela esta falando.
    3. `test_SEM_TAXA_A_LINHA_DIZ_POR_QUE_e_NUNCA_UM_NUMERO` — os TRES textos de
       ausencia sao diferentes entre si, e nenhum deles e `0`, `--` ou `infinito`.
    4. `test_MESMO_SEM_ETA_O_ALVO_E_O_QUE_FALTA_CONTINUAM_NA_TELA`.
    5. `test_COM_A_ADENA_RECUSADA_A_SECAO_DIZ_QUE_FOI_A_LEITURA` — o motivo herdado
       cita o campo, e nao ha alvo inventado.
    6. `test_NENHUMA_LINHA_NOVA_PASSA_DE_76_COLUNAS` — nos QUATRO casos (com ETA e
       nos tres sem), medindo `len(linha)` de cada linha do bloco inteiro.
    7. `test_A_SECAO_FICA_NO_BLOCO_E_NUNCA_NA_LINHA_DO_TIQUE` — `linha_do_tique`
       continua sem nenhuma das palavras novas, e continua dentro do orcamento de
       76 colunas medido no `03-02`.
  </behavior>
  <implementation>
    - `renda_console.py`: `TEXTO_DA_TAXA_DE_ADENA_ZERADA` ("sem previsao: voce nao
      esta ganhando adena. Va farmar."), `TEXTO_DA_TAXA_DE_ADENA_NEGATIVA` (que diz
      que a taxa BRUTA saiu negativa e que isso e defeito do scanner, nao do farm —
      porque `_adena_do_par` nao produz ganho negativo) e reuso de
      `TEXTO_SEM_EVIDENCIA`.
    - `_linhas_do_pack(pack) -> list[str]`: titulo
      `O PROXIMO PACK DE ADENA (pack de {_grafia_curta(tamanho)}):`, depois
      `adena de agora`, `o proximo pack fecha em`, `falta juntar` e
      `falta para o proximo pack` — o ultimo rotulo e a MESMA gramatica de
      `falta para o nivel 69`.
    - As linhas de ausencia saem no molde de `_linhas_de_uma_taxa`: rotulo sozinho +
      `_dobrar(texto)`. `_dobrar` usa `textwrap` contra `LARGURA_DO_BLOCO`, entao 76
      colunas fica garantido por construcao e nao por sorte. **Nao** se usa
      `_linha(rotulo, texto_longo)`, que e o que estoura (ver o achado medido abaixo).
    - `bloco_da_renda` ganha `pack` como parametro POSICIONAL logo depois de `eta` —
      sem default: "nao ha pack" nao e estado legitimo, ao contrario de `pisos_em_uso`.
    - `renda_laco.py`: `_tempo_ate_o_pack(campos, passos, ajustes)`, gemeo de
      `_tempo_ate_o_nivel` — mesma taxa da JANELA (a pergunta e "no ritmo de AGORA"),
      e com a adena recusada devolve `TempoAteOPack` com o motivo HERDADO da recusa,
      sem alvo. Passa o resultado a `bloco_da_renda`.
  </implementation>
  <verify>
    `python -m pytest -q tests/test_renda_console.py tests/test_renda_laco.py tests/test_renda_cegueira.py tests/test_renda_leit10.py` verde.
    MUTACAO: trocar `_dobrar` por `_linha` numa das linhas de ausencia tem de deixar
    o teste 6 VERMELHO.
    CONTROLE: extrair o titulo da secao para uma constante de modulo tem de ficar VERDE.
  </verify>
  <done>Os sete criterios passam; a rodada UNICA de pytest fecha no piso medido + os testes novos.</done>
</task>

## Verificacao final

Uma rodada so, saida inteira, depois do ultimo commit:

    python -m pytest -q --deselect tests/test_agenda.py

O piso medido NESTE worktree, ANTES da primeira edicao:

    15 failed, 6231 passed, 87 skipped, 145 deselected, 5 warnings in 111.24s

As 15 sao as CONHECIDAS e de outra area (`test_janela_no_relogio` 7,
`test_sessao` 6, `test_respawn` 2) — bombas-relogio de `date.today()`, nao minhas.
(`PYTHONPATH` com o `site-packages` do `.venv` foi RECUSADO pelo sandbox deste
worktree; a rodada foi no python global sem ele, e por isso ha 87 skips de
ambiente em vez dos 85 que o `quick/260903-bd8` mediu no checkout principal.)

## Achado ja medido, e que NAO se conserta aqui (fora de escopo)

`_linhas_do_eta` estoura as 76 colunas em DOIS dos tres casos de ausencia. Medido
chamando o proprio `renda_console._linha` (Licao 1 — nunca uma conta por fora):

    TEXTO_DA_TAXA_ZERADA    52 chars  -> 87 colunas   ESTOURA
    TEXTO_DA_TAXA_NEGATIVA  53 chars  -> 88 colunas   ESTOURA
    TEXTO_SEM_EVIDENCIA     38 chars  -> 73 colunas   cabe

(A estimativa a mao dizia `86` para o primeiro e "os tres estouram"; a chamada a
producao devolveu `87`, `88` e `73`. Fica escrito que caiu.)

`TestALarguraDoBloco` nao pega isso porque as duas medicoes dele rodam com um ETA
NUMERICO. E defeito pre-existente do `03-01`, em linha que este plano nao toca; vai
para `deferred-items.md` e para o SUMMARY, e as linhas NOVAS usam `_dobrar`
justamente para nao repeti-lo.

## Restricoes

- Nenhuma dependencia nova. `rich` continua fora e nao se desenha barra de XP.
- Nenhum `datetime.now()` no caminho novo: o tempo entra por parametro (`agora`).
- O laco chama `renda_conta`, nunca as regras de par (portao de `tests/test_renda_par.py`).
- Nenhum arquivo do workstream `dashboard`. Nenhum toque em `calibration.json`,
  `.renda/` ou `.mercado/`.
- Commits atomicos, um por tarefa.
