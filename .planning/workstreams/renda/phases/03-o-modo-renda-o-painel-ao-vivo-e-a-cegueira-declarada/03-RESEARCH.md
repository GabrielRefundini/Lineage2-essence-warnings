# Phase 3: O modo `--renda` — Research (CÓDIGO, não web)

**Pesquisado:** 2026-09-03
**Domínio:** o laço de produção, a tela de console, a cegueira declarada, o lançador
**Confiança:** ALTA — tudo abaixo saiu de `Read` sobre o fonte desta árvore, com `arquivo:linha`.
Nenhuma busca na web foi feita; a pilha está travada e o material estava todo no repositório.

**Recomendação primária:** copiar `mercado_modo.laco_do_mercado` estrutura por estrutura, trocar
`LeitorDePagina` por `renda_leitura.ler_os_tres_campos`, `Catalogo`+`RegistroDeObservacoes` por
`renda_conta`+`RegistroDaRenda`, e **não** copiar nada de mercado (destaque, modelo, watchlist,
receitas, layout, painel). O laço da renda é ~40% do tamanho do de mercado.

---

<user_constraints>
## User Constraints (do `03-CONTEXT.md`)

### Decisões travadas

- **Área 1 — a tela.** `rich` não está instalado e não é importado; o `ROADMAP.md` e o
  `CLAUDE.md` estão velhos. A tela da renda é construída sobre `console.py`, na forma do
  `mercado_console`. Sem dependência nova. *Alternativa registrada:* instalar `rich`.
- **Área 1 — a forma.** O plano decide a forma **medindo**, com os valores reais.
  `console.LARGURA` é 58 e não vai ser aumentado por esta fase sem argumento.
- **Área 2 — três estados:** *lendo*, *cego*, *parado*. **"Parado" GRAVA normalmente e só muda a
  TELA.** Só a cegueira suspende a gravação. *Alternativa registrada:* tratar parado como lacuna.
- **Área 2 — cegueira é REUSO.** `frames.SaudeDoFrame`, `FRAMES_IDENTICOS_PARA_CONGELADO = 30`,
  `cliente.EstadoDoCliente.TELA_DE_LOGIN`, `esta_na_tela_de_login`, `captura_janela.JanelaSource`.
  Esta fase **classifica e nomeia**, não detecta de novo.
- **Área 2 — "coberto" não é cegueira**, e isso é medição. **Minimizado continua impossível.**
- **Área 3 — LEIT-10.** Antes de declarar cegueira, o laço tenta os pisos **vizinhos** da banda
  gravada e usa o que produzir leitura válida, **registrando qual piso usou**. O piso que
  funcionou **não é gravado de volta** no `calibration.json`. *Alternativa registrada:*
  auto-recalibrar.
- **Área 4 — `vigiar-renda.bat`, processo separado.** `--janela` obrigatório. Cadência calibrada,
  default no `config.toml`, seção `[renda]`.

### Claude's Discretion

- Nomes de módulo e função; a forma exata do painel dentro da restrição de `console.LARGURA`.
- Se o laço vive em `renda_modo.py` (que já existe) ou em módulo próprio.
- Quantos pisos vizinhos tentar e em que ordem.

### Deferred (FORA DE ESCOPO)

- A ferramenta que mede a ponte de XP em laço.
- A página da renda no navegador (workstream `dashboard`).
- Avisar no WhatsApp quando a renda cair (ALER-01, v2).
</user_constraints>

<phase_requirements>
## Requisitos desta fase

| ID | Descrição (fonte) | O que a pesquisa achou que o sustenta |
|----|-------------------|----------------------------------------|
| CONS-01 | `REQUIREMENTS.md:300-302` — painel ao vivo com nível, EXP%, adena, taxas/min e /h, tempo até o nível, há quanto tempo a sessão corre | `mercado_console.linha_ao_vivo` (`mercado_console.py:167`) + `resumo_da_sessao` (`:668`); `as_duas_taxas` (`renda_conta.py:1074`); `tempo_ate_o_nivel` (`:1146`) |
| CONS-02 | `REQUIREMENTS.md:304-305` — modo próprio `--renda`, lançador próprio, processo separado | `__main__.py:3068` (`--mercado`), `:3204-3207` (despacho), `vigiar-mercado.bat:154-159` |
| CEGO-01 | `REQUIREMENTS.md:307-309` — jogo fechado, minimizado ou login → pausa declarada, nada gravado | `frames.py:37-42`, `captura_janela.py:203`, `cliente.py:61-70,92`, `captura_janela.py:462` |
| CEGO-02 | `REQUIREMENTS.md:311-313` — valores bit-idênticos por N amostras → "parado", não renda zero | **NÃO EXISTE NADA.** Ver §3 — é a única peça genuinamente nova da fase |
| LEIT-10 | `REQUIREMENTS.md:140-151` — piso vizinho antes de declarar cegueira, registrando qual usou | `renda_leitura.py:1322-1412` (piso é parâmetro), `calibration.json` guarda `largura_da_banda`, `calibrar_renda.py:189` (`PASSO_DA_GRADE_DE_PISOS = 5`) |
| LEIT-11 | `REQUIREMENTS.md:153-163` — concordância não prova acerto | Já fechado na Fase 2 pelas regras de par; esta fase **não pode** chamá-las (portão em `tests/test_renda_par.py:704`) |

</phase_requirements>

---

## 1. `mercado_modo.py` — o esqueleto exato a copiar

`mercado_modo.py:1-10` se descreve: *"Ele e o CHAMADOR que faltava. A Fase 2 entregou
`LeitorDePagina` e `Catalogo` sem chamador de producao; a Fase 3 entregou `RegistroDeObservacoes`
e `montar_registro_de_mercado` sem chamador, de proposito."* A situação da renda é literalmente a
mesma (§5).

### 1.1 A assinatura, e ela é o contrato de teste

```python
def laco_do_mercado(args, cal, *, fonte=None, ler_texto=None, ler_texto_conferencia=None,
                    relogio=None, pasta=None, ticks_maximos=None,
                    watchlist=None, receitas=None):
```
`mercado_modo.py:328-340`. A docstring (`:341-350`) diz: *"OS PARAMETROS NOMEADOS SAO INJECAO DE
DEPENDENCIA, e producao nao passa nenhum. (...) `ticks_maximos=None` significa laco infinito, que
e o caso de producao."* **Devolve o código de saída, nunca levanta.**

### 1.2 A ordem literal do arranque

| # | Linha | O que acontece |
|---|-------|----------------|
| 1 | `:351-352` | `principal = _modulo_do_arranque()` e `_garantir_log(principal)` |
| 2 | `:362-375` | portão do OCR — só pergunta se ninguém injetou leitora; recusa com código 2 |
| 3 | `:377-400` | portão da calibração — `pecas_de_calibracao_de_mercado_faltando(cal)` |
| 4 | `:402-418` | portão do layout |
| 5 | `:420-431` | **a linha de arranque que conta o orçamento** — antes de qualquer captura |
| 6 | `:433-455` | **os dois destinos de escrita, ANTES da captura.** Comentário em `:428-431`: *"descobrir que a pasta nao abre depois de a janela estar de pe custaria uma sessao WGC por nada"* |
| 7 | `:466-486` | carga do modelo, **uma vez, no arranque**; `try` que **degrada a análise e não o modo** |
| 8 | `:497-541` | leitura de config no arranque, nunca por tick (`:522-524`: *"reler o `config.toml` por secao abriria corrida com o usuario editando o arquivo"*) |
| 9 | `:543-544` | `relogio = principal.montar_relogio(args)` |
| 10 | `:546-564` | a fonte |
| 11 | `:566-578` | o leitor |
| 12 | `:580-597` | contadores e latches, **fora do `while`** |
| 13 | `:637-648` | primeiro desenho + `proxima_secao` + `TravaDoDestaque` |

### 1.3 Como adquire a janela

```python
carimbo = cal.mercado_geometria_da_captura or {}
if fonte is None:
    from .captura_janela import JanelaSource
    fonte = JanelaSource(
        args.janela,
        Regiao(esquerda=0, topo=0,
               largura=int(carimbo["largura"]), altura=int(carimbo["altura"])),
        relativa=True,
        minimum_update_interval=MS_ENTRE_FRAMES_DO_MERCADO,
    )
```
`mercado_modo.py:546-564`. **O import de `captura_janela` mora DENTRO do `if`** — é o que deixa a
suíte rodar no Python global sem as bindings WinRT.

**A renda tem o análogo exato do `carimbo`:** `calibration.json` guarda
`renda_por_personagem[<nome>].geometria_da_janela = {"largura": 1720, "altura": 1392}` — conferido
no arquivo real, nas duas instâncias. É o mesmo par largura/altura, e `Regiao(0,0,L,A)` com
`relativa=True` é exatamente o espaço de coordenadas em que os retângulos da renda foram gravados
(M-A, `01-MEDICOES-DE-CAMPO.md:26-30`).

`MS_ENTRE_FRAMES_DO_MERCADO = 250` (`mercado_modo.py:128`) com a justificativa inteira em
`:107-127`: *"250 E ESCOLHA, E NAO MEDICAO"*, e o motivo de não ser 1000 é que a deriva de fase
dispara falso congelamento. **Vale igual para a renda a 1 Hz.**

### 1.4 A forma do tick

```
:654   while ticks_maximos is None or ticks < ticks_maximos:
:655       ticks += 1
:656       inicio = time.monotonic()
:658-676   try: frame = fonte.capturar()
             except StopIteration -> log + break
             except Exception -> erros_seguidos += 1; se >= 10: saida=1; break
                                 senão: sleep(intervalo); continue
:678       erros_seguidos = 0
:679       pagina = leitor.observar(frame.pixels)
:685-706   deltas de contador para descobrir o estado DESTE tick (sem espiar privado)
:712       acumular_motivos(motivos, leitor.ultima_leitura)   # TODO tick, não só os aceitos
:714-732   if pagina is not None:  agora = relogio.agora(); processar; cadência de gravação
:755-765   if aberto_agora: log.info("%s", linha_ao_vivo(...))
:767-769   if time.monotonic() >= proxima_secao: desenhar_a_analise(); proxima_secao = ...
:778-779   trabalhado = time.monotonic() - inicio; orcamento.registrar(trabalhado)
:784-786   dormir = intervalo - trabalhado; if dormir > 0: sleep(dormir)
```

Três invariantes que a docstring justifica e que a renda herda:

1. **A cadência é compensada, nunca `sleep(intervalo)` puro** (`:781-783`): *"com ~110 ms de
   trabalho o tick viraria 1,11 s e o console mentiria sobre a propria cadencia"*.
2. **A linha ao vivo sai DEPOIS do bloco de processamento** (`:748-751`): antes, mostraria o
   estado do tick anterior.
3. **Os motivos são somados TODO tick** (`:710-712`): *"a leitura recusada e justamente a que
   carrega o motivo, e ler so as aceitas esconderia a metade perdida"*.

### 1.5 Captura que falha

`mercado_modo.py:658-676`. `StopIteration` → `break` limpo (é a fonte de replay/teste acabando).
Qualquer outra `Exception` → conta, loga com `log.exception`, e **só depois de
`ERROS_SEGUIDOS_PARA_DESISTIR = 10` (`:134`) sai com `SAIDA_CEGA = 1` (`:95`)**. Copiado
literalmente de `__main__.laco_principal:2724-2735`. Um único sucesso zera o contador (`:678`).

### 1.6 O encerramento

```python
except KeyboardInterrupt:   log.info("Encerrado pelo usuario")        # :788-789
finally:
    fonte.fechar()                                                     # :792
    catalogo.gravar()                                                  # :795
    log.info("\n%s", resumo_da_sessao(...))                            # :796-798
    log.info("Arquivos: %s e %s", registro.arquivo, catalogo.arquivo)  # :799
return saida                                                           # :801
```
`Ctrl+C` **não é erro**: vira log e cai no `finally`. O resumo da sessão sai SEMPRE, inclusive na
recusa — e o `vigiar-mercado.bat:129-135` depende disso: *"Aqui nao ha bloco de encerramento
nenhum: o resumo da sessao sai do proprio programa."*

### 1.7 Como fia o console

**Nunca imprime.** `mercado_console.py:1-10`: *"ELAS DEVOLVEM TEXTO E NUNCA IMPRIMEM (...) Quem
imprime e o laco, com `log.info`, e assim a mesma string vai para o console E para o `scanner.log`
rotativo."* Todas as chamadas de tela no laço são `log.info("%s", funcao(...))` — `:609`, `:723`,
`:756`, `:796`.

`Contagem` (`mercado_modo.py:138-152`) é `@dataclass` **mutada no lugar**, com três inteiros que
não se somam. `ContagemDaRenda` (`renda_conta.py:1197-1225`) já foi escrita "no molde de
`mercado_modo.Contagem`" — a docstring diz isso literalmente.

### 1.8 O que é DO MERCADO e NÃO se copia

| Peça | Onde | Por que não |
|------|------|-------------|
| `ModeloDeMercado`, `secao_do_vale_quanto`, `secao_da_margem`, `SEGUNDOS_ENTRE_SECOES` | `:466-486`, `:599-643` | é análise de preço; a renda não tem "vale quanto" |
| `TravaDoDestaque`, `destaque_ao_vivo`, `vereditos_da_pagina` | `:648`, `:207-326` | trava de anúncio de oferta barata |
| `watchlist`, `receitas`, `ReceitaInvalida` | `:497-541` | filtros de item |
| `Catalogo`, `PAGINAS_ENTRE_GRAVACOES_DO_CATALOGO = 20` | `:105`, `:725-731` | catálogo de nomes de item; a renda **não tem** arquivo reescrito por inteiro — `RegistroDaRenda.registrar` abre-escreve-fecha por linha (`renda_registro.py:1032-1042`) |
| `transicao_do_painel`, o latch de painel aberto/fechado | `:684-694` | "painel aberto" é estado do World Exchange. **A renda não tem análogo:** a barra de EXP está sempre na tela |
| Portão de layout (`:402-418`) | | não existe layout na renda |
| A dedup / índice de chaves | `mercado_registro` | **proibido** na renda: `renda_registro.py:895-903` diz *"uma linha por tique E O PRODUTO, porque ela e o denominador da taxa"*, e há portão de AST |

**Uma peça que o mercado NÃO tem e a renda precisa:** o mercado nunca chama
`fonte.estado_do_cliente()`. Só o laço da party chama (`sessao.py:468-470`). CEGO-01 exige.

---

## 2. `console.py` e `mercado_console.py` — a convenção real

### 2.1 O que `console.py` dá

`console.py:18` — `LARGURA = 58`.

- **`_pintar(texto, cor)`** (`:79-82`): devolve `f"{cor}{texto}{_RESET}"` **só se** `_habilitar_cor()`
  disser sim. `_habilitar_cor` (`:31-76`) respeita `NO_COLOR`, exige `isatty()` e liga
  `ENABLE_VIRTUAL_TERMINAL_PROCESSING` via ctypes no Windows. **Em teste com `caplog`, cor é
  sempre desligada** (`isatty()` falso) — as asserções são sobre texto puro.
- **`moldurar(texto, hora, marca="*")`** (`:97-119`): **três linhas** — borda, miolo com carimbo
  alinhado à direita, borda. E a linha que decide tudo:
  ```python
  largura = max(LARGURA, len(miolo) + len(carimbo))    # console.py:110
  ```
  **`LARGURA` é um PISO, não um teto.** Conteúdo maior faz a moldura crescer, não estourar.
  `destacar` (`:135-137`) escreve isso: *"O bloco cresce se o texto for longo, em vez de estourar
  a moldura"*.
- **`destacar(texto, tipo, hora)`** (`:122-147`): `moldurar` + cor por `TipoDeEvento` + linha em
  branco antes e depois. **Depende de `rastreador.TipoDeEvento`** (`console.py:16`) — a renda não
  tem TipoDeEvento; `_ESTILO.get(tipo, ("*", _CIANO))` (`:139`) aceita `None` e cai no default.

### 2.2 Como `linha_ao_vivo` compõe e como repinta

```python
def linha_ao_vivo(leitor, contagem, ultimo_item, *, layout_recusado: bool) -> str:
    linha = (f"mercado | lidas {leitor.paginas_lidas} | "
             f"perdidas {leitor.paginas_perdidas} | "
             f"gravadas {contagem.observacoes} | "
             f"ultimo item: {ultimo_item if ultimo_item else '(nenhum ainda)'}")
    if layout_recusado:
        linha = f"{linha} | {AVISO_DO_LAYOUT_RECUSADO}"
    return linha
```
`mercado_console.py:167-217`.

> ### ⚠️ ACHADO 1 — **não há repintura. Nenhum `\r`, nenhum clear, nenhum `print`.**
>
> `mercado_modo.py:755-765` emite `log.info("%s", linha_ao_vivo(...))`. Varredura de
> `l2scanner/*.py`: **zero** ocorrências de `\r` isolado, `end=`, `flush=` em caminho de tela.
> A palavra "repintada" na docstring (`mercado_console.py:167`) descreve a **cadência** (uma linha
> nova por tick), não a técnica. O "ao vivo" desta casa é **log rolando**.
>
> Isso **muda o problema da Área 1 do `03-CONTEXT.md`**: não há um retângulo de tela a caber. Há
> uma linha de log por tick, e a única pergunta real é quantas linhas por tick o log aguenta.

### 2.3 A medição pedida: os ~10 valores cabem em 58?

Medido agora, com os valores reais do `03-CONTEXT.md`:

| Candidato | Colunas |
|---|---|
| `nivel 67 \| EXP 79,2568% \| adena 17.592.060 \| 2,41 M XP/h \| 466 mil adena/h \| falta 3h20` | **87** |
| `renda \| nivel 67 \| EXP 79,2568% \| adena 17.592.060` | 50 |
| `  2,41 M XP/h (n=142, ha 3s) \| 466 mil adena/h (n=88, ha 3s) \| falta 3h20` | 73 |
| `PARADO: os valores nao mudam ha 5 min - voce esta sem matar nada` | 64 |

**Não cabem em 58.** Mas — e este é o ponto —

> ### ⚠️ ACHADO 2 — **`LARGURA = 58` nunca governou a linha ao vivo, e a linha que existe hoje já tem 84–255 colunas.**
>
> Medido sobre o fonte real:
> - `linha_ao_vivo` com um nome de item típico: **84 colunas**.
> - `AVISO_DO_LAYOUT_RECUSADO` (`mercado_console.py:160-166`): **168 colunas**, numa string só.
> - A linha ao vivo **com** o aviso colado: **255 colunas**.
>
> `linha_ao_vivo` não importa `LARGURA`, não chama `moldurar`, não trunca e não quebra.
> `console.LARGURA` só é lida em `console.py:110`, dentro de `moldurar`, e lá é um **piso**.
>
> Logo: a restrição *"console.LARGURA é 58 e não vai ser aumentado por esta fase"* é **verdadeira
> e irrelevante** — nada precisa ser aumentado, porque a linha ao vivo nunca passou por ali.

### 2.4 Precedente de bloco multi-linha: existe, e é forte

- `resumo_da_sessao` (`mercado_console.py:668-741`) devolve **~25 linhas** com
  `"\n".join(linhas)`, abrindo com `console.moldurar(...)`, e é emitido com
  `log.info("\n%s", ...)` (`mercado_modo.py:796-798`). Linhas medidas: 37 e 61 colunas.
- `secao_do_vale_quanto` (`:599`) e `secao_da_margem` (`:903`) — mesmos moldes, emitidos por
  **intervalo** (`SEGUNDOS_ENTRE_SECOES = 60.0`, `:497`), nunca por tick, com a razão escrita em
  `:490-496`: *"Repintar um bloco de dezenas de linhas por segundo afogaria a linha ao vivo"*.
- `LARGURA_DO_AVISO = 76` (`:748`) — *"a largura em que ela cabe num console padrao de 80"*. **Este
  é o número real de largura de console desta casa, e não 58.**
- `__main__.desenhar_status` (`:753-830`) monta bloco multi-linha e sai por
  `--status-a-cada` (default 30 s, `__main__.py:3017-3023`).

**Conclusão prescritiva:** a forma que o repositório já tem é **uma linha por tick** + **um bloco
por intervalo**. Copiar isso resolve CONS-01 sem inventar convenção. Os ~10 valores dividem-se
naturalmente: os três que a tela do jogo afirma (nível/EXP/adena) na linha do tick; as quatro
taxas + ETA + duração da sessão no bloco de intervalo, onde já cabem `n` e recência.

---

## 3. As peças da cegueira

### 3.1 `frames.SaudeDoFrame`

```python
class SaudeDoFrame(Enum):      # frames.py:37-42
    OK = "ok"
    FALHA_DE_CAPTURA = "falha_de_captura"
    CONGELADO = "congelado"
```
Produzida por `_ClassificadorDeSaude.classificar(pixels) -> SaudeDoFrame` (`frames.py:132-150`):

| Condição | Resultado | Linha |
|---|---|---|
| `pixels.size == 0` | `FALHA_DE_CAPTURA` | `:133-134` |
| `pixels.mean() < LIMIAR_BRILHO_MINIMO` (`= 8.0`, `:28`) | `FALHA_DE_CAPTURA` | `:136-137` |
| `blake2b` igual ao anterior por `FRAMES_IDENTICOS_PARA_CONGELADO = 30` (`:34`) vezes | `CONGELADO` | `:139-148` |
| resto | `OK` | `:150` |

O chamador distingue por `frame.saude is SaudeDoFrame.X`, ou pelo atalho
`Frame.utilizavel` (`frames.py:73-75`) que é `saude is OK`. `Frame` é
`@dataclass(frozen=True, eq=False)` (`:45`) — **`eq=False` é obrigatório** por causa do ndarray;
`tests/test_dataclass_com_ndarray.py` prende isso.

### 3.2 `captura_janela.JanelaSource`

Construtor: `JanelaSource(titulo, regiao, relativa=False, extras=None, minimum_update_interval=None)`
(`captura_janela.py:232-238`). No `__init__`: `achar_janela(titulo)` (`:245`) — **levanta
`JanelaNaoEncontrada` se o jogo não estiver aberto** — e `_esperar_primeiro_frame()` (`:299`), que
levanta `RuntimeError` depois de `SEGUNDOS_PARA_PRIMEIRO_FRAME = 5.0` (`:35`) com a mensagem
*"A janela esta minimizada? Janela minimizada nao produz frame — nenhuma API do Windows contorna
isso"* (`:322-325`).

Métodos que importam:

| Método | Devolve | Linha |
|---|---|---|
| `capturar()` | `Frame` **com `saude` classificada sobre o RECORTE** | `:380-441` |
| `capturar_completo()` | `np.ndarray \| None` — a janela inteira, **sem `saude` nenhuma** | `:326-335` |
| `completo_do_frame_atual()` | a janela que produziu o frame corrente, `None` se cega | `:363-378` |
| `estado_do_cliente()` | `EstadoDoCliente` | `:462-488` |
| `apontar_para(regiao)` | troca o recorte; **`ValueError` se `relativa=False`** | `:336-361` |
| `fechar()` | para a thread, join 2 s | `:490-493` |

E, solto no módulo, sem chamador nenhum na árvore:
```python
def esta_minimizada(hwnd: int) -> bool:      # captura_janela.py:203-204
    return bool(_user32.IsIconic(hwnd))
```

> ### ⚠️ ACHADO 3 — `esta_minimizada` tem **zero** chamadores. É o único sinal direto de
> "minimizado" na árvore, e CEGO-01 nomeia minimizado explicitamente.
> `JanelaSource` não expõe o hwnd por propriedade pública (é `self._hwnd`, `:245`), então o laço
> precisa ou de um método novo na fonte, ou de `achar_janela(titulo)` próprio.

> ### ⚠️ ACHADO 4 — **`renda_modo._frame_de_janela` usa o caminho SEM saúde.**
> `renda_modo.py:263-286` constrói `JanelaSource(titulo, Regiao(0, 0, 1, 1), relativa=True)` e
> chama `capturar_completo()`. Isso **pula `capturar()` inteiro** e portanto **não classifica
> saúde, não detecta congelamento e não detecta frame preto**. Para leitura única está certo; para
> o laço, é exatamente a peça que CEGO-01 e CEGO-02 precisam. O laço tem de usar o molde do
> mercado: `Regiao(0, 0, largura, altura)` da `geometria_da_janela` + `capturar()`.

### 3.3 `cliente.EstadoDoCliente` e `esta_na_tela_de_login`

```python
class EstadoDoCliente(Enum):   # cliente.py:61-70
    EM_JOGO = "em_jogo"
    TELA_DE_LOGIN = "tela_de_login"
    DESCONECTADO = "desconectado"
    DESCONHECIDO = "desconhecido"   # "Nunca vira evento: na duvida o scanner nao inventa nada"
```

```python
def esta_na_tela_de_login(titulo: str | None) -> bool:   # cliente.py:92-110
    # "Yazalaque - XM Essence" -> False ;  "XM Essence" -> True
    return titulo.strip() == NOME_DO_CLIENTE            # comparação EXATA, nunca endswith
```

`JanelaSource.estado_do_cliente()` (`:462-488`) monta um `VigiaDoCliente` sob demanda e chama
`avaliar(titulo_da_janela(self._hwnd), self.capturar_completo, time.monotonic())`.
`VigiaDoCliente.avaliar` (`cliente.py:248-276`):

| Entrada | Saída | Linha |
|---|---|---|
| `titulo is None` (a janela **não existe mais**: `IsWindow` falso — `cliente.py:83-84`) | `DESCONHECIDO` | `:259-260` |
| título == `"XM Essence"` | `TELA_DE_LOGIN` | `:263-265` |
| `matchTemplate` do diálogo ≥ 0.90, com cadência de 5 s | `DESCONECTADO` | `:267-276` |
| resto | `EM_JOGO` | `:274-276` |

**A cadência é o ponto:** o título custa ~0,001 ms e o `matchTemplate` ~45 ms; `avaliar` só chama
`obter_pixels()` quando a busca vence (`:250-252`, `:266-272`). E o veredito de desconexão
**gruda** entre buscas (`:242-246`).

### 3.4 Como um chamador distingue os estados — a tabela que o plano precisa

| Situação real | O sinal que a árvore produz hoje | Quem o produz |
|---|---|---|
| Jogo **fechado antes** do arranque | `JanelaNaoEncontrada` no `__init__` | `captura_janela.py:61-91` |
| Jogo **minimizado** no arranque | `RuntimeError` em `_esperar_primeiro_frame` | `:307-325` |
| Jogo **fechado no meio** | `estado_do_cliente()` → `DESCONHECIDO`; e a WGC para de entregar → `_ultimo` congela → `CONGELADO` em ~30 ticks | `cliente.py:259` + `frames.py:147` |
| Jogo **minimizado no meio** | idêntico ao acima: para de renderizar, `CONGELADO` em ~30 ticks | `frames.py:30-34` |
| **Tela de login** | `estado_do_cliente()` → `TELA_DE_LOGIN` (**imediato**, pelo título) | `cliente.py:263-265` |
| **Desconectado** (diálogo modal) | `DESCONECTADO`, até 5 s de atraso | `cliente.py:266-276` |
| **Coberto por outra janela** | nada: a WGC lê normal. **Medido** — `01-MEDICOES-DE-CAMPO.md:1-6` | — |
| Frame **preto** | `FALHA_DE_CAPTURA` (brilho médio < 8.0) | `frames.py:136-137` |
| Sessão WGC morta com o jogo vivo | `CONGELADO` — o caso medido de `recaptura.py:3-17` | `recaptura.py` |

### 3.5 A pergunta de desenho do roadmap, respondida

**Qual sinal mapeia para "cego":**

- `SaudeDoFrame.FALHA_DE_CAPTURA` → cego, sem ambiguidade.
- `SaudeDoFrame.CONGELADO` → cego, e é o sinal que **cobre jogo fechado e jogo minimizado no
  meio**, ao custo de ~30 s de latência.
- `EstadoDoCliente.TELA_DE_LOGIN` → cego, **imediato e nomeado**, e é o único que dá ao usuário
  a frase acionável (`__main__.py:776-784` já faz isso: *"'SEM VISAO' e verdade mas nao ajuda;
  'JOGO CAIU - TELA DE LOGIN' diz o que fazer a respeito"*).
- `EstadoDoCliente.DESCONHECIDO` → jogo fechado, imediato.
- `EstadoDoCliente.DESCONECTADO` → cego.
- `esta_minimizada(hwnd)` → **disponível e não usado**; é o único caminho para dizer "minimizado"
  em vez de esperar 30 s de congelamento.

**Qual sinal mapeia para "parado":**

> ### ⚠️ ACHADO 5 — **NENHUM. A verificação do roadmap CONFIRMA: não existe nada que rastreie
> staleness de VALOR nesta árvore.**
>
> Varredura completa de `l2scanner/*.py` por acumulador de leitura repetida. O que existe são
> **três** detectores, e os **três são de PIXEL**:
>
> 1. `frames._ClassificadorDeSaude` — hash `blake2b` do recorte, 30 iguais → `CONGELADO`
>    (`frames.py:139-148`).
> 2. `recaptura.FonteRecuperavel` — 3 `CONGELADO` seguidos → reconstrói a fonte
>    (`recaptura.py:60`, `:131-151`).
> 3. `mercado_pagina` — `JANELAS_IGUAIS_PARA_CONGELAR = 3` janelas inteiras bit-idênticas → recusa
>    páginas, com LATCH (`mercado_pagina.py:102`, `:789-814`).
>
> Nenhum compara **o valor lido**. A camada que CEGO-02 pede é nova, e é a **única** peça
> genuinamente nova da fase. O roadmap está certo (`ROADMAP.md:433-439`) e o `03-CONTEXT.md`
> Área 2 está certo.
>
> **Nuance que só o fonte revela, e que o plano precisa:** com o EXP em décimos de milésimo de
> ponto percentual e o degrau de um abate medido em **0,001 pp = 10 unidades**
> (`renda_ponte.py:33-35`, censo de 55 Hz), "bit-idêntico" é literal e barato: `valor_atual ==
> valor_anterior`. **Mas a adena recusa em 21% dos tiques e o nível em 79%**
> (`renda_conta.py:245-248`, `:696-698`) — então "o valor não mudou" e "o valor não foi lido"
> precisam ser fatos separados, exatamente como `ContagemDaRenda` já separa `lacunas` de
> `recusadas_por_motivo` (`renda_conta.py:1219-1223`). Contar uma recusa como "parado" faria o
> painel dizer PARADO em 79% dos tiques com o usuário matando mob.

---

## 4. O jogo sumindo no meio — as DUAS behaviours que já existem

### 4.1 O laço da party: **religa, e depois roda cego, mas NÃO sai**

A fonte não é `JanelaSource` crua — é um envelope:

```python
def construir():
    return JanelaSource(args.janela, regiao,
                        relativa=cal.party_window_na_janela is not None,
                        extras=extras or None)
fonte = FonteRecuperavel(construir)          # __main__.py:2300-2311
```

`FonteRecuperavel.capturar` (`recaptura.py:131-151`):
- `CONGELADO` → `_congelados_seguidos += 1`; em `CONGELADOS_SEGUIDOS_PARA_RELIGAR = 3` (`:60`)
  chama `_religar()`.
- `_religar` (`:184-237`): teto de `TENTATIVAS_DE_RELIGACAO = 5` (`:69`), espaçadas por
  `SEGUNDOS_ENTRE_TENTATIVAS = 30.0` (`:78`), **por comparação de instantes, nunca `sleep`**
  (`:189-198`). Constrói a nova **antes** de fechar a antiga (`:214-222`).
- Esgotado o teto: `_avisar_que_desistiu` (`:259-276`) — *"UMA vez, alto, e o laco segue rodando
  cego. **Nao sai, nao levanta, nao silencia.**"*
- **O frame desta volta é sempre devolvido**, inclusive no tick da reconstrução (`:147-151`).
- O orçamento só é devolvido num frame **saudável** (`:138-145`), não na construção — porque *"A
  WGC entrega sessoes que constroem sem erro nenhum e continuam mortas — foi EXATAMENTE o caso
  medido em campo"*.

Em paralelo, no tick: transição de saúde loga uma vez (`__main__.py:2738-2743`), e
`sessao.ticks_cego == TICKS_CEGO_PARA_SUGERIR_RECALIBRAR` (`= 30`, `:192`) sugere recalibrar uma
única vez (`:2812-2817`); aos 45 o reancorador procura a party window (`:2833-2836`).

O único caminho de **saída** é `except Exception` na captura: 10 seguidas → `return 1`
(`:2727-2735`).

### 4.2 O laço do mercado: **pausa declarada, e roda para sempre**

`laco_do_mercado` **não usa `FonteRecuperavel`** — constrói `JanelaSource` direto
(`mercado_modo.py:547-564`). E uma sessão WGC morta **não levanta**: `capturar()` devolve o último
frame para sempre. Logo o `except Exception`/10 (`:663-676`) **nunca dispara** nesse cenário. O
que dispara é `mercado_pagina` acusando 3 janelas bit-idênticas, com LATCH de log
(`mercado_pagina.py:796-814`), e o laço segue de pé sem gravar linha.

### 4.3 O que isso obriga

> ### ⚠️ ACHADO 6 — há **duas** behaviours, não três, e elas divergem numa coisa só:
> **quem tem `FonteRecuperavel` religa; quem não tem, congela em silêncio.**
> A Fase 3 não deve inventar uma terceira. Ela deve escolher entre:
>
> **(A) Party:** `FonteRecuperavel(construir)`. Custo: ~1 linha. Ganho: o incidente medido de 33
> minutos cegos (`recaptura.py:3-17`) não se repete numa farmada noturna — que é exatamente o caso
> de uso desta fase. **Recomendado.**
>
> **(B) Mercado:** `JanelaSource` cru. Mais simples, e herda o defeito que `recaptura.py` existe
> para consertar.
>
> `FonteRecuperavel` delega `estado_do_cliente` por `__getattr__` (`recaptura.py:171-177`) — e a
> escolha é deliberada e documentada em `:124-129`, porque `MssSource` não tem o método. Com
> `JanelaSource` dentro, `envelope.estado_do_cliente()` funciona. Há teste prendendo o contrário
> para o envelope cru (`tests/test_recaptura.py:535-546`): o envelope **não declara** o método,
> ele **encaminha**.

**Nenhum dos dois laços sai por causa de cegueira sozinha.** Os dois só saem por 10 exceções
seguidas na captura. CEGO-01 diz "pausa declarada", não "encerra" — os dois precedentes concordam.

---

## 5. `renda_conta.py` e `renda_registro.py` vistos de fora

### 5.1 O que o laço tem de segurar entre ticks

| Estado | Tipo | Por quê |
|---|---|---|
| `anterior: CamposDaRenda \| None` | o objeto do tick passado | `passo_entre_campos` precisa dos dois lados |
| `carimbo_anterior: float \| None` | epoch | `CamposDaRenda` **não carrega carimbo** — `renda_conta.py:659-662` |
| `passos: list[PassoDaRenda]` | a sequência inteira | `as_duas_taxas` recebe a sequência (`:1074`) |
| `contagem: ContagemDaRenda` | mutada no lugar | `contar_o_passo` devolve `None` de propósito (`:1227`) |
| `ajustes: AjustesDaRenda` | lido **uma vez no arranque** | `config.py:1714`; reler por tick abriria corrida |
| `registro: RegistroDaRenda` | escritor por personagem | `renda_registro.py:917` |
| `relogio: Relogio` | injetável | `__main__.montar_relogio(args)` |

### 5.2 A sequência exata de um tick

```python
# 1. pixels -> três campos (Fase 1, pura)
campos = renda_leitura.ler_os_tres_campos(frame.pixels, personagem=P, calibracao=cal)
#    renda_leitura.py:1322 — devolve CamposDaRenda com nivel/exp/adena, cada um
#    ValorDaRenda|ValorDaAdena OU RecusaDaRenda. NUNCA levanta.

agora = relogio.agora_epoch()          # relogio.py:146 — EPOCH float, não datetime

# 2. o passo (Fase 2, pura). SOMENTE-NOMEADOS, SEM DEFAULT.
passo = renda_conta.passo_entre_campos(
    anterior, campos,
    carimbo_anterior=carimbo_anterior,      # None no primeiro tick -> ancora
    carimbo=agora,
    fator_de_salto=ajustes.fator_de_salto_da_adena,
    limiar_de_lacuna_em_segundos=ajustes.lacuna_maxima_segundos,
)   # renda_conta.py:638-645. anterior=None -> ancora_da_sequencia (:565)

# 3. a contagem, mutada no lugar
renda_conta.contar_o_passo(passo, contagem)         # :1227-1254

# 4. o disco. UMA LINHA POR TIQUE, sempre — inclusive com campo recusado.
registro.registrar(campos, carimbo=agora,
                   descontinuidade=passo.descontinuidade,
                   origem_do_ganho=renda_registro.ORIGEM_INDETERMINADA)
                                                     # renda_registro.py:990-996

# 5. a sequência
passos.append(passo)
anterior, carimbo_anterior = campos, agora

# 6. os números da tela (puros, sobre a sequência)
xp = renda_conta.as_duas_taxas(passos, grandeza=renda_conta.GRANDEZA_DO_EXP,
        janela_em_segundos=ajustes.janela_movel_minutos * 60,
        piso_de_amostras=ajustes.amostras_minimas_para_taxa,
        piso_da_janela_em_segundos=ajustes.janela_minima_para_taxa_segundos)   # :1074
ad = renda_conta.as_duas_taxas(passos, grandeza=renda_conta.GRANDEZA_DA_ADENA, ...)
eta = renda_conta.tempo_ate_o_nivel(exp_atual_em_decimos=<int>, taxa=xp.janela)  # :1146
```

Notas que o plano tem de honrar:

- **`registrar` devolve `bool` e NUNCA levanta** (`renda_registro.py:997-999`). No primeiro
  `OSError` ele faz `self.ligado = False` **definitivo para a sessão** (`:1043-1058`) — sem retry.
- **`RegistroDaRenda.__init__` SE DEFENDE = não.** `renda_registro.py:911-919`: *"O CONSTRUTOR NAO
  SE DEFENDE, e isso e deliberado (...) Quem envolve tudo num `try` e a montagem, pelo trilho de
  `montar_gravador`."* Faltando: um `montar_registro_da_renda(pasta, personagem)` em `__main__.py`
  no molde de `montar_registro_de_mercado` (`__main__.py:573-650`), que devolve `None` e nunca
  levanta. **Não existe.** É trabalho desta fase.
- **`carimbo` é epoch float.** A única conversão para `datetime` da fase é de saída, em
  `campos_da_linha` (`renda_registro.py:585`).
- **`passos_da_janela` assume a sequência cronológica e NÃO ordena** (`:1046-1050`) — porque
  relógio embaralhado tem nome próprio (`relogio-andou-para-tras`).
- **`AsDuasTaxas` sempre traz as duas** (`:1057-1072`): janela e sessão. *"Apresentar so uma MENTE
  POR OMISSAO, e o tamanho da mentira esta medido: 226 mil adena/h contra 466 mil/h"*.
- **`TaxaDaRenda` nunca é número nu** (`:847-885`): traz `evidencia` (`n`/`piso`),
  `motivo_da_ausencia`, `janela_farmada_em_segundos`, `unidade_da_janela` (`"minutos farmados"`,
  `:308`), `lacunas_excluidas`, `segundos_em_lacuna`, `ate` (recência). **É o `n`+recência que
  CONS-01 pede "colados nos números como o `--mercado` já faz".**

### 5.3 Os marcadores de `descontinuidade`

> ### ⚠️ ACHADO 7 — **são SETE, não cinco.** A pergunta do briefing diz cinco; o
> `02-02-SUMMARY.md:270` diz *"SEIS valores possiveis alem do vazio"* e em seguida **lista sete**;
> e o commit `3db84e7` desta árvore é literalmente *"docs(02): a coluna descontinuidade tinha SETE
> valores e documentava tres"*. **O fonte é a verdade:**

| # | Constante | Valor | `renda_conta.py` | Só um laço ao vivo produz? |
|---|---|---|---|---|
| 1 | `DESCONTINUIDADE_DA_ANCORA` | `ancora` | `:195` | **Não.** Qualquer `anterior=None` |
| 2 | `DESCONTINUIDADE_DA_LACUNA` | `lacuna` | `:200` | **SIM.** Exige dois carimbos reais separados por mais de `lacuna_maxima_segundos` — só o tempo de parede de um laço produz |
| 3 | `DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS` | `relogio-andou-para-tras` | `:204` | **SIM na prática.** É o dual boot do usuário mexendo no relógio entre dois ticks |
| 4 | `..._NIVEL_INDISPONIVEL_COM_EXP_CAINDO` | `nivel-indisponivel-com-exp-caindo` | `:213` | Não — é do par |
| 5 | `..._NIVEL_INDISPONIVEL_COM_EXP_SUBINDO` | `nivel-indisponivel-com-exp-subindo` | `:238` | Não — é do par. **E não exclui:** é procedência (`:273-275`) |
| 6 | `DESCONTINUIDADE_DO_EXP_INDISPONIVEL` | `exp-indisponivel` | `:250` | Não |
| 7 | `DESCONTINUIDADE_DA_ADENA_INDISPONIVEL` | `adena-indisponivel` | `:251` | Não |
| — | `SEM_DESCONTINUIDADE` | `""` | `:280` | — |

**Resposta direta:** só **`lacuna`** e **`relogio-andou-para-tras`** dependem de um laço ao vivo.
Os outros cinco são funções puras de um par de amostras e já são exercitados sem jogo aberto.

E isto é o que fecha a fronteira que o `03-CONTEXT.md` cravou: **a Fase 3 não constrói portão
novo.** Os "motivos de recusa que só um laço ao vivo produz" (jogo fechado, minimizado, login,
frames congelados) **não são `descontinuidade`** — a `descontinuidade` é do par, e a Fase 2 é dona
dela. O que a cegueira faz é **não chamar `registrar`**; e o efeito no arquivo é uma diferença de
carimbo grande, que o próximo par converte sozinho em `lacuna` pela regra que já existe.

> ### ⚠️ ACHADO 8 — **isso significa que a cegueira NÃO precisa de coluna nova nem de valor novo.**
> Basta o laço parar de chamar `registrar` e continuar chamando `passo_entre_campos` com o
> `carimbo_anterior` de antes da cegueira. `lacuna_maxima_segundos = 60` (`config.py:1658`) e a
> cegueira dura mais que isso por construção. `DESCONTINUIDADES_DO_TEMPO` (`:255-259`) tira o
> passo do denominador, e `TaxaDaRenda.lacunas_excluidas`/`segundos_em_lacuna` (`:881-882`)
> mostram na tela quanto tempo foi cego. **A fase inteira do CEGO-01 já está construída.**

---

## 6. A família `.bat`

### 6.1 O molde compartilhado

`vigiar-mercado.bat` e `vigiar-party.bat` compartilham, byte a byte:
- `@echo off` / `setlocal` / `cd /d "%~dp0"` (`vigiar-mercado.bat:1-2,38`)
- busca do Python em 5 lugares, guardando **caminho completo** (`:46-57`), com a razão escrita
- rejeição do stub da Microsoft Store (`:59-62`)
- criação do `.venv` na primeira execução (`:75-87`) e sonda de dependências (`:89-105`), que
  inclui `winrt.windows.media.ocr`
- blocos `:erro_venv` / `:erro_deps` **ANTES** da linha de execução (`:129-152`), com a razão em
  `:129-135`: *"e o que torna ESTRUTURAL a promessa de que nada e impresso depois de o programa
  rodar"*

### 6.2 A resolução de `--janela` a partir de `[jogo] personagem`

```bat
set "PERSONAGEM_PADRAO=Yazalaque"                            REM :44
set "JANELA="
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import sys; from l2scanner.config import ler_personagem_do_jogo; from l2scanner.cliente import NOME_DO_CLIENTE, SEPARADOR; print((ler_personagem_do_jogo() or sys.argv[1]) + SEPARADOR + NOME_DO_CLIENTE)" "%PERSONAGEM_PADRAO%" 2^>nul') do if not defined JANELA set "JANELA=%%t"
if not defined JANELA ( ...erro, pause, exit /b 1 )          REM :119-127
...
".venv\Scripts\python.exe" -m l2scanner --mercado --janela "%JANELA%" %*   REM :159
pause                                                                       REM :161
```
`vigiar-mercado.bat:107-117,159`. A cadeia é:
`[jogo] personagem` (com `config.local.toml` vencendo) → `config.ler_personagem_do_jogo()` →
`+ cliente.SEPARADOR (" - ") + cliente.NOME_DO_CLIENTE ("XM Essence")` → `--janela "<título>"`.
**Sem aspas dentro do `-c`** (`:113-115`): o `for /f` recorta entre aspas simples.

### 6.3 O que `vigiar-renda.bat` tem de conter

Cópia integral de `vigiar-mercado.bat` com **quatro** trocas:
1. o cabeçalho `REM` (o que ele é, o que não é, o que precisa — a calibração da renda por
   `calibrar-renda.bat`, e que `.renda/` é o produto);
2. `--mercado` → `--renda` na linha `:159`;
3. o `--personagem` **não entra**: o nome sai do título, como já faz `renda_modo.py:330`;
4. nada mais. A resolução de janela é idêntica, e o `03-CONTEXT.md` Área 4 e o
   `ROADMAP.md:445-449` mandam copiar, não reinventar.

**Testes de `.bat` são obrigatórios nesta casa.** `tests/test_vigiar_mercado_bat.py` tem 11
testes (`:82-245`), incluindo: ASCII puro lido em `cp1252`, a flag do modo na linha de execução,
`--janela` com valor e não pelado, a mira vindo da chave do config, nenhum `echo` fora de guarda
de `errorlevel`, e nenhum `echo` mandando rodar o lançador da party. O molde de leitura é
`_texto()` em `cp1252` e `_posicao_do_echo` que **ignora `REM`** (`tests/test_calibrar_renda_bat.py:40-63`) —
com a história de por que a versão ingênua passava com o `.bat` quebrado.

---

## 7. LEIT-10 — onde o retry de piso cabe

### 7.1 O piso É parâmetro. Confirmado.

```python
def exp_da_barra(recorte, *, piso_de_brilho: int)      # renda_leitura.py:497-498
def nivel_da_regiao(recorte, *, piso_de_brilho: int)   # renda_leitura.py:985-986
def adena_da_barra(recorte, *, piso_de_brilho: int, moldes, piso_de_leitura,
                   margem_de_leitura, folga_de_cola)   # renda_leitura.py:1102-1110
```
As três são puras e sem default de piso. Quem resolve retângulo e piso é
`ler_os_tres_campos` (`renda_leitura.py:1322`), no helper interno `_ler` (`:1375-1389`), que faz
`leitor(recorte, int(bloco["piso_de_brilho"]))`.

**A pureza da Fase 1 é PRESA POR TESTE:** `tests/test_renda_par.py:601-630`
(`TestOPortaoDaAusenciaDeMemoria`) varre a AST de `renda_leitura.py` procurando `global` e
literal mutável de nível de módulo, com controle positivo. Um cache de piso dentro de
`renda_leitura.py` deixa o portão **vermelho**.

> **Conclusão:** o retry de piso mora **no laço** (ou num módulo puro chamado pelo laço), e chama
> `ler_os_tres_campos` — ou os três leitores — mais de uma vez com pisos diferentes. A memória do
> piso que funcionou é estado do laço, nunca do leitor.

**Custo a medir:** o `03-CONTEXT.md` Área 4 diz que uma leitura completa custa *"dezenas de ms a
alguns segundos (o OCR domina)"*. Um retry de 2 vizinhos triplica o pior caso. `OrcamentoDoTick`
(`mercado_console.py:81-133`) já existe para medir isso e mostrar p50/p95/máximo no resumo — e
`OrcamentoDoTick(limite=float(args.intervalo))` (`mercado_modo.py:582`) conta os estouros.

### 7.2 A calibração guarda a largura da banda. Confirmado, e com números.

`calibration.json` real, ambas as instâncias:

| região | campo | `piso_de_brilho` | `largura_da_banda` |
|---|---|---|---|
| `barra_esquerda` | EXP | 155 | **4** |
| `barra_direita` | adena | 190 | **3** |
| `nivel` | nível | 210 | **5** |

Validação em `calibracao.py:1530-1540`: opcional, inteiro, `>= 1`. Comentário de esquema em
`:624-628`.

**E a semântica é a que o retry precisa** — mas com uma pegadinha:

- `BandaUtil.largura` é `len(self.pisos)` (`calibrar_renda.py:457-459`) — **contagem de pisos na
  grade, não amplitude em unidades de brilho**.
- A grade anda de `PASSO_DA_GRADE_DE_PISOS = 5` (`calibrar_renda.py:189`), com a história do passo
  10 que produziu uma conclusão errada (`:179-188`).
- `escolher_o_piso` devolve `banda.pisos[banda.largura // 2]` — **o CENTRO** (`:504-516`), *"Um
  piso na borda da banda funciona hoje e esta a uma mudanca de gamma (...) de cair fora dela"*.

**Logo o retry tem um mapa exato:** piso gravado é o centro; os vizinhos legítimos são
`piso ± 5`, `piso ± 10`, …, até `(largura_da_banda // 2) * 5`. Para os valores reais:

| campo | piso | largura | banda reconstruída | vizinhos dentro da banda |
|---|---|---|---|---|
| EXP | 155 | 4 | 145, 150, **155**, 160 | −10, −5, +5 |
| adena | 190 | 3 | 185, **190**, 195 | −5, +5 |
| nível | 210 | 5 | 200, 205, **210**, 215, 220 | ±5, ±10 |

E o M-S mediu que a banda do EXP **andou** de `140..170` para `160..180` em 8,5 h
(`01-MEDICOES-DE-CAMPO.md:423-435`) — 4 passos de deslocamento. **Andar só dentro da banda gravada
não alcança o cenário medido.** O plano tem de decidir se o retry sai da banda; e se sair, a
`largura_da_banda` deixa de ser o limite e vira só a origem.

`largura_da_banda` é **opcional** no esquema (`calibracao.py:1530`) — calibrações antigas não têm.
O retry precisa de um default quando ela falta.

---

## 8. Convenção de teste para um laço

### 8.1 O idioma exato — `tests/test_mercado_modo.py`

**Fonte falsa que implementa a porta e acaba:**
```python
class FonteFalsa:                                   # tests/test_mercado_modo.py:121-149
    def __init__(self, quadros):
        self._quadros = list(quadros); self._indice = 0; self.fechada = False
    def capturar(self) -> Frame:
        if self._indice >= len(self._quadros):
            raise StopIteration                      # o mesmo sinal de ReplaySource
        pixels = self._quadros[self._indice]; self._indice += 1
        return Frame(pixels=pixels, indice=self._indice, saude=SaudeDoFrame.OK)
    def fechar(self): self.fechada = True
```
`self.fechada` existe *"para o teste provar que o `finally` do laco fechou a captura"* (`:127-129`).

**`args` sintético, sem `argparse`:**
```python
def argumentos(**extras) -> argparse.Namespace:      # :164-167
    base = {"janela": "Lineage II", "intervalo": 0.0}
    base.update(extras); return argparse.Namespace(**base)
```
**`intervalo=0.0` é o que torna o teste instantâneo** — o `sleep` compensado
(`mercado_modo.py:784-786`) só dorme se `dormir > 0`.

**A chamada completa:**
```python
codigo = laco_do_mercado(argumentos(), cal,
    fonte=FonteFalsa(quadros), ler_texto=duas, ler_texto_conferencia=tres,
    relogio=Relogio(), pasta=tmp_path, ticks_maximos=4)      # :196-205
assert codigo == 0
assert fonte.fechada
```

**As quatro alavancas, e são quatro:** `fonte=` (frames), `ler_*=` (OCR), `relogio=` (tempo),
`pasta=tmp_path` (disco), mais `ticks_maximos=` (limite). Nada de `sleep`, nada de thread, nada de
jogo.

**Console por `caplog`:**
```python
with caplog.at_level(logging.INFO):
    laco_do_mercado(..., ticks_maximos=4)
assert "paginas lidas" in caplog.text                  # :225-238
```
Funciona porque `_garantir_log` **não reconfigura** quando a raiz já tem manipulador — que é
exatamente o caso do `caplog` (`mercado_modo.py:194-199`).

### 8.2 Relógio injetado

`Relogio(fonte=..., parede=lambda: HORA_DO_SERVIDOR)` — `tests/test_relogio_no_laco.py:100,155,213`.
`Relogio.agora_epoch()` (`relogio.py:146`) e `.agora()` (`:156`) e `.confiavel` (`:166`).
Para a renda, o carimbo é `agora_epoch()` (epoch float) — e a aritmética de
`passos_da_janela`/`taxa_por_hora` é subtração de epochs, exata.

### 8.3 O que a renda tem — e o que NÃO tem

**Tem:**
- `tests/fixtures/renda/montagem_completa.png` e `montagem_da_janela.png`, ambas **1720×1392** —
  janela inteira, exatamente a `geometria_da_janela` gravada.
- `tests/fixtures/renda/calibracao_de_fixture.json` e os 14 recortes por campo.
- Verdade de campo escrita (`tests/fixtures/renda/LEIA-ME.md:14-22`).
- Gate de OCR ausente com skip nomeado (`tests/test_renda_completa.py:588` etc.), que **um teste
  de laço com leitura injetada não precisa**.

**NÃO tem — e isto é decisão de plano:**

> ### ⚠️ ACHADO 9 — **não existe seam de injeção de leitura para a renda.**
> `renda_leitura.py:66` faz `from .ocr import ler_texto, ler_texto_ampliado` — **import de nome no
> topo do módulo**, chamado direto em `:538` e `:1019`. Não há parâmetro `ler_texto=`, ao
> contrário de `LeitorDePagina`, que recebe as duas leitoras por construtor
> (`mercado_modo.py:566-578`).
>
> Consequência: um teste de laço da renda ou (a) monkeypatcha
> `l2scanner.renda_leitura.ler_texto`, o que a casa evita; ou (b) o laço recebe
> `ler_campos=renda_leitura.ler_os_tres_campos` como parâmetro nomeado com default de produção —
> **e esse é o seam que segue a disciplina da casa**, um nível acima do mercado. Recomendado (b).
>
> **Segunda consequência:** só há **uma** janela completa por fixtura, e um laço precisa de uma
> **sequência com valores que mudam** para produzir delta, taxa e ETA. Com o seam (b), a sequência
> é uma lista de `CamposDaRenda` montada à mão — que é exatamente como
> `tests/test_renda_conta.py` já constrói os 286 casos que passam hoje.

### 8.4 Os portões que uma peça nova pode derrubar

> ### ⚠️ ACHADO 10 — **`tests/test_renda_par.py:704-735` afirma que o conjunto de módulos que
> chamam as regras de par é EXATAMENTE `{renda_conta.py}`.**
> `O_UNICO_CHAMADOR = "renda_conta.py"`, `A_COMPOSICAO = "conferir_o_par"` (`:98-101`).
> Se o módulo do laço chamar `conferir_o_par`, `o_exp_andou_para_tras`,
> `o_nivel_andou_para_tras` ou `a_adena_saltou_ordem_de_grandeza`, o portão fica **vermelho**.
> O laço chama `passo_entre_campos` e mais nada.

E `tests/test_renda_par.py:631-650` estende o portão de ausência de memória a `renda_conta.py` e
`renda_registro.py`. Os dois seguem sem estado; o estado do laço mora no laço.

`tests/test_firewall_escopo.py` é só sobre bibliotecas de síntese de input — **não** tem lista de
módulos permitidos, então um módulo novo não precisa de cadastro lá.

---

## Assumptions Log

| # | Afirmação | Onde | Risco se errada |
|---|---|---|---|
| A1 | `largura_da_banda` é contagem de passos de 5 e o piso gravado é o centro, logo os vizinhos são `piso ± 5k` | derivado de `calibrar_renda.py:457-459` + `:189` + `:504-516`; **não** há teste afirmando essa leitura de fora | o retry de LEIT-10 anda no passo errado e não acha nada |
| A2 | Jogo fechado/minimizado no meio manifesta-se como `CONGELADO` em ~30 ticks e nunca como exceção | inferido de `captura_janela.py:281-296` (a thread guarda `_ultimo` e `on_closed` é `pass`) + `frames.py:139-148`; **não reproduzido em campo nesta rodada** | CEGO-01 espera 30 s a mais do que o plano supôs; ou pior, o plano confia numa exceção que não vem |
| A3 | Com `intervalo=0.0` um teste de laço da renda é instantâneo | vale para o mercado (`tests/test_mercado_modo.py:165`); a renda faz OCR, e nas fixturas o OCR pode não estar disponível | teste de laço fica lento ou dependente das bindings |
| A4 | Nada do workstream `dashboard` lê `.renda/` hoje | `grep renda l2scanner/dashboard*.py` → vazio | — (confirma a fronteira do `03-CONTEXT.md`) |

---

## O que o plano tem que decidir, e o que já está decidido

### (a) Fatos estabelecidos por leitura de código — não precisam de decisão

1. **`.renda/` não existe no disco.** `ls .renda` → ausente. `PASTA_DA_RENDA`
   (`renda_registro.py:144`), `RegistroDaRenda`, `renda_conta` inteiro e `amostras_ao_vivo`
   têm **zero** chamadores de produção. O `03-CONTEXT.md` está certo: esta fase é o chamador.
2. **O esqueleto do laço está em `mercado_modo.py:328-801`** e é copiável estrutura por estrutura.
   Arranque com portões (recusa com código 2, nunca sobe degradado), destinos de escrita antes da
   captura, config lida uma vez, tick com cadência compensada, `finally` com `fechar` + resumo.
3. **A tela é `log.info` de texto puro.** Sem `rich`, sem `\r`, sem repintura. `linha_ao_vivo`
   devolve uma string e o laço a emite. `LARGURA = 58` é piso de `moldurar`, não teto da linha ao
   vivo — a linha ao vivo do mercado já roda **84–255 colunas**. A largura de console real citada
   no fonte é **76** (`mercado_console.py:748`).
4. **Precedente de bloco multi-linha existe e é o certo para os ~10 valores:**
   `resumo_da_sessao` / `secao_do_vale_quanto`, emitidos por **intervalo** e não por tick
   (`SEGUNDOS_ENTRE_SECOES = 60.0`).
5. **Toda a detecção de cegueira já existe.** `SaudeDoFrame` (3 estados),
   `FRAMES_IDENTICOS_PARA_CONGELADO = 30`, `EstadoDoCliente` (4 estados),
   `esta_na_tela_de_login`, `esta_minimizada` (sem chamador), `JanelaSource.estado_do_cliente()`.
6. **Staleness de VALOR não existe em lugar nenhum.** Três detectores de pixel, zero de valor.
   CEGO-02 é a única peça nova da fase.
7. **CEGO-01 não precisa de valor novo de `descontinuidade`:** basta não chamar `registrar`, e o
   próximo par vira `lacuna` sozinho (`lacuna_maxima_segundos = 60`).
8. **Só `lacuna` e `relogio-andou-para-tras` são produzidos exclusivamente por um laço ao vivo.**
9. **Duas behaviours para o jogo sumindo, não três:** party religa via `FonteRecuperavel` (3
   congelados → 5 tentativas espaçadas 30 s → avisa uma vez e roda cego, **sem sair**); mercado
   congela em silêncio. Nenhum dos dois sai por cegueira; os dois saem por 10 exceções seguidas.
10. **O piso é parâmetro** nas três funções de leitura, e a pureza de `renda_leitura.py` é presa
    por portão de AST. O retry de LEIT-10 mora no laço.
11. **`largura_da_banda` está gravada e populada** (4/3/5 nas duas instâncias), e a semântica
    (centro + passo 5) dá o mapa dos vizinhos.
12. **O `.bat` é cópia com quatro trocas**, e a resolução de `--janela` é
    `[jogo] personagem` → `ler_personagem_do_jogo()` → `+ SEPARADOR + NOME_DO_CLIENTE`.
13. **O idioma de teste de laço está pronto**: `FonteFalsa` com `StopIteration`,
    `argparse.Namespace(intervalo=0.0)`, `relogio=Relogio(...)`, `pasta=tmp_path`,
    `ticks_maximos=N`, console por `caplog`.

### (b) Escolhas genuinamente abertas

1. **Religa ou não?** `FonteRecuperavel(construir)` (party) vs `JanelaSource` cru (mercado).
   Recomendação: **religa** — o caso medido de 33 minutos cegos (`recaptura.py:3-17`) é exatamente
   uma farmada noturna, que é o uso desta fase. Custo: 1 linha e um `def construir()`.
2. **O seam de injeção de leitura.** `ler_campos=renda_leitura.ler_os_tres_campos` como parâmetro
   nomeado (recomendado) vs monkeypatch de `l2scanner.renda_leitura.ler_texto`. Sem seam não há
   teste de laço sem OCR.
3. **A linha do tick vs o bloco do intervalo — o que vai em cada um.** Recomendação: os três
   valores que a tela do jogo afirma (nível, EXP%, adena) + o estado (LENDO/PARADO/PAUSADO) na
   linha; as quatro taxas + ETA + duração + `n`/recência + as taxas de recusa por campo no bloco.
4. **O N do CEGO-02, e sobre qual valor.** O EXP anda 10 unidades por abate; a adena recusa em
   21% e o nível em 79%. "Parado" tem de ser medido sobre o campo que quase nunca recusa (EXP), e
   "não lido" tem de ser um estado distinto de "não mudou".
5. **Quantos pisos vizinhos e em que ordem** (discricionário no `03-CONTEXT.md`) — e, mais
   importante, **se o retry pode sair da banda gravada**. O M-S mediu deslocamento de 4 passos;
   ficar dentro de `largura_da_banda` (3 a 5) não alcança o cenário medido.
6. **Onde o laço mora.** `renda_modo.py` já tem `argparse` próprio para leitura única, e
   `calibrar_renda.py:991` importa `_frame_de_imagem` e `_frame_de_janela` de lá — essas duas não
   podem sumir nem mudar de nome. Módulo novo é mais limpo.
7. **A chave da cadência no `[renda]`.** Ver contradição (c-4).
8. **`montar_registro_da_renda(pasta, personagem)`** — onde mora. O precedente é
   `__main__.montar_registro_de_mercado` (`__main__.py:573-650`), chamado pelo laço via
   `_modulo_do_arranque()`. Não existe ainda.

### (c) O que CONTRADIZ o `03-CONTEXT.md` ou o `ROADMAP.md` — a parte que vale mais

**C-1. `mercado_console.linha_ao_vivo` NÃO é "uma linha repintada". Não há repintura nenhuma.**
O `03-CONTEXT.md` Área 1 diz: *"É `mercado_console.linha_ao_vivo`, que devolve **uma linha**
repintada"*. Devolve uma linha, sim; **repintada, não**. Zero `\r`, zero clear, zero `print` no
caminho de tela em `l2scanner/*.py`. O laço faz `log.info("%s", ...)`
(`mercado_modo.py:755-765`) e a linha **rola**. A palavra "repintada" na docstring
(`mercado_console.py:167`) descreve a cadência.
**Por que importa:** o CONTEXT derrubou `rich.Live` corretamente, mas manteve a imagem mental de
uma tela que se sobrescreve. Ela não existe. Se o plano tentar reproduzir "um painel que se
atualiza no lugar", inventa a segunda convenção de tela que a decisão da Área 1 existe para
evitar — só que por outro caminho.

**C-2. `console.LARGURA = 58` nunca governou a linha ao vivo, e a medição pedida responde outra
pergunta.** O `03-CONTEXT.md` Área 1 manda medir *"o que cabe"* em 58 colunas, e o `ROADMAP.md:442`
lista *"largura"* entre as decisões de tela. Medido: a linha ao vivo do mercado já tem **84**
colunas em operação normal e **255** com o aviso de layout colado; `AVISO_DO_LAYOUT_RECUSADO`
sozinho tem **168**. `linha_ao_vivo` não importa `LARGURA`, não chama `moldurar` e não trunca.
`LARGURA` só aparece em `console.py:110`, como `max(LARGURA, ...)` — **um piso**. A largura de
console que o fonte de fato cita é **76** (`LARGURA_DO_AVISO`, `mercado_console.py:748`, *"a
largura em que ela cabe num console padrao de 80"*).
**Por que importa:** a medição continua valendo — os 87 caracteres não cabem numa linha de 80 e o
console vai quebrar num lugar imprevisível, que é exatamente o defeito que `LARGURA_DO_AVISO`
existe para evitar. Mas o número é **76/80**, não 58, e a restrição *"não vai ser aumentado"* é
sobre uma constante que ninguém precisa tocar.

**C-3. `descontinuidade` tem SETE marcadores, não cinco.** A pergunta do briefing pede "os cinco";
o `02-02-SUMMARY.md:270` diz "SEIS além do vazio" e lista sete; `renda_conta.py:195-251` define
sete. O commit `3db84e7` desta árvore já corrigiu a documentação
(*"a coluna descontinuidade tinha SETE valores e documentava tres"*), o que confirma que a
contagem circulou errada.
**Por que importa:** um plano que enumere cinco deixa dois casos sem teste, e os dois esquecidos
mais prováveis são `exp-indisponivel` e `adena-indisponivel` — os que a taxa de recusa medida (21%
da adena) torna comuns, um em cada cinco tiques.

**C-4. A chave de cadência que o `03-CONTEXT.md` diz que já existe NÃO existe.** Área 4:
*"O default vai no `config.toml`, na seção `[renda]` que o `02-01` já criou."* A seção existe,
com **cinco** chaves e nenhuma delas é cadência: `janela_movel_minutos`,
`lacuna_maxima_segundos`, `fator_de_salto_da_adena`, `amostras_minimas_para_taxa`,
`janela_minima_para_taxa_segundos` (`config.py:1592-1597`, `:1657-1661`; `config.toml` traz as
cinco comentadas). `AjustesDaRenda` é `@dataclass(frozen=True)` com esses cinco campos
(`config.py:1601,1657-1661`).
**Por que importa:** acrescentar a sexta chave é trabalho real — a constante, o campo do
dataclass, o `_inteiro_da_renda`, o `_EXEMPLO_DA_RENDA` (`config.py:1665-1674`), o `config.toml`
comentado e o teste em `tests/test_config_da_renda.py`. **E há um caminho mais barato que o plano
deve considerar antes:** `__main__` já tem `--intervalo` com `INTERVALO_PADRAO = 1.0`
(`__main__.py:187`, `:3013-3018`), e `laco_do_mercado` lê `float(args.intervalo)` e nada mais. Um
`--renda` despachado por `__main__` herda a cadência de graça.

**C-5. `renda_modo._frame_de_janela` é o caminho ERRADO para o laço, e é o precedente mais óbvio
a copiar.** `renda_modo.py:263-286` usa `Regiao(0, 0, 1, 1)` + `capturar_completo()`, que
**pula a classificação de saúde inteira** — sem `SaudeDoFrame`, sem congelamento, sem frame preto.
O `03-CONTEXT.md` cita `renda_modo.py` como candidato a abrigar o laço e cita `SaudeDoFrame` como
reuso, sem notar que o caminho de pixel que já está lá não produz `SaudeDoFrame` nenhum.
**Por que importa:** um executor que "reusa `_frame_de_janela`" entrega um laço com CEGO-01 e
CEGO-02 estruturalmente impossíveis, e a suíte fica verde porque nenhum teste existente olha para
isso. O molde certo é `mercado_modo.py:546-564`.

**C-6. O `ROADMAP.md` diz que "a cegueira é reuso" e está certo — mas subestima o quanto.**
`ROADMAP.md:415-421` lista as peças. O que a leitura do fonte acrescenta é que **CEGO-01 já está
inteiro**: a pausa não precisa de coluna nova, de valor de `descontinuidade` novo nem de segundo
portão — basta não chamar `registrar`, e `DESCONTINUIDADE_DA_LACUNA` +
`TaxaDaRenda.lacunas_excluidas`/`segundos_em_lacuna` fazem o resto sozinhos
(`renda_conta.py:200-202`, `:255-259`, `:881-882`). A fronteira que o CONTEXT protege
(*"Duas portas para o mesmo arquivo"*) não é só respeitável: é **gratuita**.

**C-7. `esta_minimizada` existe, não tem chamador, e é a única forma de cumprir a palavra
"minimizado" de CEGO-01 sem esperar 30 s.** Nem o `ROADMAP.md` nem o `03-CONTEXT.md` a citam —
os dois citam `SaudeDoFrame`, `FRAMES_IDENTICOS_PARA_CONGELADO`, `EstadoDoCliente`,
`esta_na_tela_de_login` e `JanelaSource`. `captura_janela.py:203-204`.
**Por que importa:** minimizado é o único estado que o `PROJECT.md` declara impossível de contornar
— e "declarar a pausa em vez de prometer contorná-la" (Área 2) fica muito melhor se a declaração
sair no segundo em que o usuário minimiza, e não meio minuto depois com a palavra errada
("congelado").

**C-8. O portão de chamador do `test_renda_par.py` é uma armadilha para o módulo novo.**
`tests/test_renda_par.py:704-735` afirma que o conjunto de módulos que chamam as regras de par é
**exatamente** `{renda_conta.py}`. Nem o `ROADMAP.md` nem o `03-CONTEXT.md` mencionam este portão.
Um laço que, por exemplo, chamasse `a_adena_saltou_ordem_de_grandeza` para recuperar a rede que
`passo_entre_campos` admite perder no ramo incompleto (`renda_conta.py:695-707`) deixaria a suíte
vermelha — e a própria docstring daquela função já **recusou** essa manobra por antecipação.

**C-9. `ROADMAP.md:455-457` (Progress) e `:461-486` (Coverage) estão desatualizados.**
A tabela de Progress diz Fases 1 e 2 *"Not started, 0/?"*; as duas estão mescladas com testes
passando. A Coverage lista 18 requisitos e **não inclui LEIT-10**, embora `:404-410` o tenha
acrescentado a esta fase e o `REQUIREMENTS.md:148` nomeie a Fase 3 como dona. Cosmético, mas o
plano vai citar a Coverage e ela não bate com os requisitos da fase.

**C-10. O `.renda/` nasce com um LEIAME, e ninguém escreveu isso em lugar nenhum do plano.**
`RegistroDaRenda.__init__` chama `escrever_leiame(self.pasta)` logo depois do `mkdir`
(`renda_registro.py:932-936`, função em `:388`). No primeiro arranque do `--renda` a pasta nasce
com `LEIAME.txt` além do CSV. É bom — só não pode surpreender o critério de verificação
("`.renda/` deixou de estar vazio" vai ser verdade com **dois** arquivos, não um).

---

## Sources

Todos primários, todos desta árvore, lidos nesta sessão:

`l2scanner/mercado_modo.py`, `l2scanner/mercado_console.py`, `l2scanner/console.py`,
`l2scanner/frames.py`, `l2scanner/cliente.py`, `l2scanner/captura_janela.py`,
`l2scanner/recaptura.py`, `l2scanner/__main__.py`, `l2scanner/renda_modo.py`,
`l2scanner/renda_leitura.py`, `l2scanner/renda_conta.py`, `l2scanner/renda_registro.py`,
`l2scanner/renda_ponte.py`, `l2scanner/renda_semeadura.py`, `l2scanner/calibracao.py`,
`l2scanner/calibrar_renda.py`, `l2scanner/config.py`, `l2scanner/mercado_pagina.py`,
`vigiar-mercado.bat`, `vigiar-party.bat`, `calibrar-renda.bat`, `calibration.json`, `config.toml`,
`tests/test_mercado_modo.py`, `tests/test_renda_par.py`, `tests/test_vigiar_mercado_bat.py`,
`tests/test_calibrar_renda_bat.py`, `tests/test_relogio_no_laco.py`, `tests/fixtures/renda/`,
`.planning/workstreams/renda/ROADMAP.md`, `.../REQUIREMENTS.md`,
`.../phases/01-*/01-MEDICOES-DE-CAMPO.md`, `.../phases/02-*/02-0[1-4]-SUMMARY.md`,
`.../phases/03-*/03-CONTEXT.md`.

Medições executadas nesta sessão: largura em colunas das linhas candidatas e das linhas reais do
`mercado_console`; `python -m pytest tests/ -k renda` → **662 passed, 48 skipped** (skips todos
por bindings de OCR ausentes no Python global); núcleo `renda_conta`+`renda_registro`+
`renda_completa`+`renda_par`+`config_da_renda`+`conta_tracer` → **286 passed, 21 skipped**;
`ls .renda` → ausente; dimensões de `montagem_completa.png` → 1720×1392.

**Confiança:** ALTA em tudo, exceto A1 e A2 do Assumptions Log (MÉDIA — derivação de fonte sem
reprodução em campo).
