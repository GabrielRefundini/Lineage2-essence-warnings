# Phase 2: A conta e o registro — Research

**Researched:** 2026-09-02
**Domain:** código deste repositório. Zero pesquisa web — a pilha está travada no `CLAUDE.md` e
nada que esta fase precisa mora fora da árvore.
**Confidence:** HIGH nas oito perguntas (tudo lido com `arquivo:linha`); MEDIUM só na
proveniência dos números de campo que o `02-CONTEXT.md` cita — ver §Contradições, item C-6.

---

## Summary

A Fase 1 deixou **mais** pronto do que o `02-CONTEXT.md` afirma, e **menos** do que o
`ROADMAP.md` promete, e as duas divergências importam para o plano.

Mais: `renda_leitura.py` entrega quatro regras de par puras, sem chamador, com o par de campo
real do level up já congelado em teste — a Fase 2 é literalmente o chamador que elas esperam. O
dialeto do `mercado_registro.py` está fatiado exatamente na linha certa: `conferir_o_terminador`
não conhece coluna nenhuma e é copiável sem uma vírgula de mudança. O relógio já entra por
parâmetro em toda a árvore, e há um `Maquina` de teste com `pular_parede()` que simula o dual
boot em uma linha.

Menos: há **um teste da Fase 1 que a Fase 2 derruba por construção**
(`tests/test_renda_par.py:591-623` proíbe qualquer módulo de `l2scanner/` de chamar as regras de
par); a promessa do `ROADMAP.md` de que o `dashboard` lê `.renda/` "acrescentando uma lista de
colunas" está **refutada pelo código** — `conferir_o_cabecalho` fecha sobre um `COLUNAS` global e
`payload` é mercado inteiro; e a forma "um arquivo por personagem por dia" que o `02-CONTEXT.md`
atribui ao `.mercado/` e ao `.loot/` **não existe em nenhum dos dois**.

Também não há, em 41 mil linhas, **nenhuma** taxa por hora sobre janela móvel. A Fase 2 inventa a
aritmética. O que ela não inventa é a *forma*: `Evidencia(n, piso)` viajando dentro do resultado,
recência separada do valor, e `Fraction`/inteiro no lugar de `float`.

**Primary recommendation:** três módulos novos e nenhum arquivo alheio editado —
`renda_conta.py` (puro: deltas, janela, taxas), `renda_registro.py` (o dialeto copiado, com
leitor tolerante próprio), e três linhas em `calibracao.py` para a ponte de XP. E, como Tarefa 1,
**aposentar deliberadamente** o portão de `tests/test_renda_par.py:591` invertendo-o: de "ninguém
chama" para "quem chama é este módulo, e só ele".

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Diferença entre duas amostras (level up, gasto, salto do relógio) | Módulo puro novo (`renda_conta.py`) | `renda_leitura.conferir_o_par` | Função pura sobre um par por parâmetro, no molde já estabelecido em `renda_leitura.py:1584-1608` |
| Janela móvel, denominador sem lacuna, `n` e recência | Módulo puro novo | — | Não existe precedente; a *forma* vem de `mercado_analise.Evidencia` (`mercado_analise.py:226-249`) |
| Ponte XP↔pp | `calibracao.py` (dado) + módulo puro (consumo) | — | Precedente literal de `renda_por_personagem`: dict CRU no `Calibracao`, decodificação no consumidor (`calibracao.py:670-675`) |
| Append de uma linha com contrato | `renda_registro.py` (novo) | dialeto de `mercado_registro.py` | O escritor é dono do arquivo; o portão mora FORA da classe (`mercado_registro.py:405-409`) |
| Leitura tolerante da cauda de `.renda/` | `renda_registro.py` (novo) | forma de `dashboard_dados.observacoes_ao_vivo` | O `dashboard_dados` arrasta `cv2` (§3); importar dali é proibido de fato |
| Laço ao vivo, captura, painel | **Fase 3** | — | `<domain>` do `02-CONTEXT.md:18-21` fecha a fase sem laço |

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

*(cópia verbatim de `02-CONTEXT.md:28-102`)*

**Área 1 — A janela móvel, e o que ela faz na lacuna**

- **Janela por TEMPO, não por número de amostras.** "Últimos 10 minutos" é o que o usuário
  entende; "últimas 40 amostras" varia de significado quando a cadência muda ou quando o scanner
  fica cego. E a Fase 3 vai ter cadência variável por natureza (o OCR custa dezenas de ms e o
  jogo às vezes some).
- **O tempo cego SAI do denominador.** Se o scanner ficou 20 minutos sem ler, esses 20 minutos
  não foram farmados *do ponto de vista da medição* — dividir por eles produz uma taxa
  artificialmente baixa que o usuário não tem como distinguir de "o farm piorou". A regra: o
  denominador é a soma dos intervalos **entre amostras consecutivas aceitas**, e um intervalo
  maior que um limiar calibrado é **excluído e contado à parte** como lacuna.
  *Alternativa registrada:* dividir pelo relógio de parede. É o padrão silencioso, é mais simples,
  e é a razão de esta decisão estar escrita — sem escrevê-la, alguém a implementa sem perceber.
- **Toda taxa carrega `n` e a janela que cobriu.** Vem do roadmap e do `--mercado`. Uma taxa de
  40 segundos se anuncia como ruído.
- **Duas taxas, não uma:** a da **janela móvel** (o que está acontecendo agora) e a da **sessão
  inteira** (o que a noite rendeu). Elas respondem perguntas diferentes e o usuário quer as duas.
  Medido hoje: a média de 8h45 deu 226 mil adena/h e a janela curta deu 466 mil/h — a diferença é
  o tempo parado, e apresentar só uma das duas mente por omissão.

**Área 2 — Level up e gasto: os dois deltas negativos**

- **Level up (REND-03):** `(100 − anterior) + atual`, e um nível a mais. **A regra só dispara
  quando o nível REALMENTE mudou** — e aqui a Fase 1 deixou uma dívida que esta fase herda: o
  nível é o campo mais frágil dos três. Se o nível vier recusado e o EXP cair, a fase **não pode
  adivinhar**: registra a amostra como descontinuidade nomeada e não computa ganho naquele passo.
  Inventar um level up é pior que perder um.
  *Alternativa registrada:* assumir level up sempre que o EXP cair muito (>50 pp). Mais simples,
  e erra exatamente quando o usuário morre e perde EXP — que também é queda grande.
- **Gasto (REND-04):** queda no contador de adena é **gasto**, registrado à parte, fora da taxa
  de ganho. Ganho bruto = soma dos deltas positivos.
- **Farm × venda:** decidido **marcador explícito, não heurística.** O arquivo carrega a coluna,
  e quem sabe preenche. Hoje ninguém sabe, então ela sai como "indeterminado" — e isso é honesto.
  *Por quê:* o roadmap oferece três caminhos (forma do salto, painel do mercado aberto, marcador).
  Os dois primeiros são inferência por limiar mágico sobre um dado que o consumidor não pode
  auditar. D-02 do projeto: um número exibido tem de ter existido. Uma coluna "indeterminado"
  que o dashboard mostra como indeterminado é melhor que um balde errado com cara de certo.

**Área 3 — A ponte XP↔porcentagem (REND-08)**

- **A constante mora no `calibration.json`, por personagem E por nível.** `renda_ponte_de_xp:
  {Faerlina: {67: {xp_por_ponto: 383124, medido_em: ..., n_abates: ..., n_linhas: ...}}}`.
  Por nível porque o custo do nível muda; por personagem porque o multiplicador de XP é do
  personagem (562% na Faerlina).
- **Sem constante para o nível atual, o XP absoluto é DECLARADO INDISPONÍVEL.** Nunca convertido
  com a constante do nível anterior. O painel mostra pontos percentuais e diz por que o absoluto
  não está lá. Mesma disciplina do câmbio XM→BRL no `dashboard`: sem taxa informada, mostra XM e
  diz que o R$ está indisponível.
- **A constante carrega a sua procedência**, não só o valor: quantas linhas de chat, quantos
  abates, que janela. Uma constante medida em 6 minutos e uma medida em 3 horas não valem o
  mesmo, e quem lê tem de conseguir saber qual é qual.
- **Esta fase NÃO mede a constante em laço** — ela a consome. Medir exige ler o chat em
  cadência alta, e isso é ferramenta de calibração (Fase 3 ou tarefa própria), não conta.

**Área 4 — O arquivo em `.renda/`**

- **Dialeto do `mercado_registro`, colunas próprias.** `;`, `csv` da stdlib, cabeçalho como
  contrato que desliga alto, append por linha com flush, `ArquivoRecortado` no leitor. A
  refutação do "sem um segundo parser" já está escrita no REG-03 e vai repetida no fonte.
- **Um arquivo por personagem por dia**, na forma que o `.mercado/` e o `.loot/` já usam.
- **Colunas previstas** (o plano ajusta): `carimbo`, `personagem`, `nivel`, `exp_decimos`,
  `adena`, `motivo_da_recusa`, `origem_do_ganho`.
- **As RECUSAS também são gravadas**, com o motivo. Um arquivo que só tem sucessos não permite
  responder "por que a taxa desta hora tem n=12 se o scanner rodou 40 minutos". A taxa de recusa
  é dado, não ruído — a Fase 1 já mediu 21% na adena e 79% no nível.
  *Alternativa registrada:* gravar só as aceitas, arquivo menor e mais limpo. Perde a auditoria.
- **Append-only, nunca podado.** Mesma razão do `.loot/`.

**Área 5 — O relógio**

- **Entra por parâmetro, em tudo.** Nenhum `datetime.now()`. Não é estilo: o PC é dual boot e o
  Windows volta ~3h adiantado do Linux, e uma taxa por hora com relógio que pula é lixo
  silencioso. `relogio.py` já resolveu isso.
- **Um salto do relógio para trás entre amostras é DESCONTINUIDADE nomeada**, não um intervalo
  negativo. É o mesmo formato dos outros dois deltas negativos desta fase, e pela mesma razão.

### Claude's Discretion

- Nomes de módulo, função e coluna.
- O tamanho padrão da janela móvel e o limiar de lacuna — devem ser calibrados, não fixos.
- Se a sessão é delimitada por processo ou por lacuna longa.

### Deferred Ideas (OUT OF SCOPE)

- A **ferramenta que mede a ponte** (ler o chat em cadência alta e calcular a constante). Ela
  existe hoje como script de bancada no scratchpad do agente; virar comando é trabalho da Fase 3
  ou de uma tarefa própria. Esta fase só **consome** a constante.
- SP por hora — mesma linha do chat, mesma ponte, nenhum requisito pede.
- Comparar renda entre locais de farm (REND-07, já em v2).
- Avisar no WhatsApp quando a renda cair (ALER-01, já em v2).

---

## Phase Requirements

| ID | Descrição (de `REQUIREMENTS.md`) | O que desta pesquisa habilita |
|----|-------------|------------------|
| REND-01 | XP por minuto e por hora, em pontos percentuais (`REQUIREMENTS.md:239`) | §7 — não há precedente de taxa; a forma vem de `Evidencia` |
| REND-02 | Adena por minuto e por hora (`:241`) | idem |
| REND-03 | `(100 − anterior) + atual`, e um nível a mais (`:243-245`) | §1 — `o_exp_andou_para_tras` **já se abstém** quando o nível mudou (`renda_leitura.py:1498-1499`); o par de campo está congelado em `tests/test_renda_par.py:99-100` |
| REND-04 | Queda no contador é gasto, à parte (`:247-250`) | §1 — `a_adena_saltou_ordem_de_grandeza` é *bidirecional de propósito* (`renda_leitura.py:1543-1549`) e não conflita com gasto |
| REND-05 | Tempo até o nível = `(100 − exp%) / (exp%/h)` (`:252`) | §7 — divisão sobre `Fraction`, nunca `float`, no molde de `dashboard_dados.py:624-628` |
| REND-06 | Janela móvel que diz de quantas amostras veio (`:257`) | §7 — `Evidencia(n, piso)` viaja DENTRO do resultado (`mercado_analise.py:230-232`) |
| REND-08 | XP absoluto por ponte calibrada por nível (`:167-221`) | §6 — receita completa da terceira chave |
| REND-09 | O bônus JÁ está no total; não somar o parênteses (`:223-232`) | Consumido só pela ferramenta de medição (deferida); nada nesta fase parseia o chat |
| REG-01 | Uma linha append-only em `.renda/`, com carimbo (`:265`) | §2 — receita do dialeto |
| REG-02 | Sobrevive a reinício; primeira amostra é âncora, não delta (`:269`) | §2 + §5 — o índice em memória de `mercado_registro` é reconstruído do CSV (`mercado_registro.py:616-618`) |
| REG-03 | Mesmo contrato que o `dashboard` já sabe ler (`:272-285`) | §3 — **a correção do REQUIREMENTS ainda é otimista demais**; ver C-2 |
| REG-04 | O registro diz de qual personagem (`:287-294`) | §1 — `CamposDaRenda.personagem` e `LeituraDaRenda.personagem` já existem (`renda_leitura.py:1285`, `:1315`) |

---

# 1. `renda_leitura.py` — o que a Fase 2 pode chamar

**1.608 linhas, lidas inteiras.** Tudo abaixo com linha.

## A superfície pública que a Fase 2 consome

| Símbolo | Linha | Assinatura exata | Devolve |
|---|---|---|---|
| `RecusaDaRenda` | `:145-160` | `@dataclass(frozen=True)`, campos `campo: str`, `motivo: str`, `detalhe: str` | — |
| `ValorDaRenda` | `:163-183` | campos `campo: str`, `valor: int`, `escalas: int`, `texto: str` | nível e EXP |
| `ValorDaAdena` | `:186-208` | campos `campo: str`, `valor: int`, `glifos: int`, `texto: str` | só adena |
| `CamposDaRenda` | `:1268-1297` | `personagem: str`, `nivel: ValorDaRenda \| RecusaDaRenda`, `exp: ...`, `adena: ValorDaAdena \| RecusaDaRenda`; `@property por_campo -> dict` | os três, cada um inteiro OU recusa |
| `LeituraDaRenda` | `:1300-1319` | `personagem: str`, `nivel: int`, `exp: int`, `adena: int`, `carimbo: float` | só quando os TRÊS saíram |
| `ler_os_tres_campos` | `:1322` | `(frame, *, personagem, calibracao) -> CamposDaRenda` | nunca aborta no primeiro problema |
| `ler_a_renda` | `:1415-1417` | `(frame, *, personagem, calibracao, carimbo: float) -> LeituraDaRenda \| RecusaDaRenda` | a PRIMEIRA recusa em `ORDEM_DOS_CAMPOS` |

Constantes verbatim (`renda_leitura.py:74-142`):

```
CAMPO_DO_EXP = "exp"
CAMPO_DO_NIVEL = "nivel"
CAMPO_DA_ADENA = "adena"
ORDEM_DOS_CAMPOS = (CAMPO_DO_NIVEL, CAMPO_DO_EXP, CAMPO_DA_ADENA)
SUBCHAVE_DO_EXP = "barra_esquerda"
SUBCHAVE_DA_ADENA = "barra_direita"
SUBCHAVE_DO_NIVEL = "nivel"
MOTIVO_DO_RECORTE_FORA_DO_FRAME = "recorte-fora-do-frame"
MOTIVO_DO_CAMPO_VAZIO = "campo-vazio"
MOTIVO_DA_GRAMATICA = "gramatica"
MOTIVO_DA_DISCORDANCIA = "discordancia-entre-escalas"
MOTIVO_DO_PERSONAGEM = "personagem-sem-calibracao"
MOTIVO_DO_CONJUNTO_DE_MOLDES = "conjunto-de-moldes"
MOTIVO_DA_PONTUACAO = "pontuacao-dos-glifos"
MOTIVO_DO_EXP_PARA_TRAS = "exp-andou-para-tras"
MOTIVO_DO_NIVEL_PARA_TRAS = "nivel-andou-para-tras"
MOTIVO_DO_SALTO_DA_ADENA = "adena-saltou-ordem-de-grandeza"
```
[VERIFIED: l2scanner/renda_leitura.py:74-142]

E a unidade do EXP, verbatim (`renda_leitura.py:326`): `DECIMOS_DE_MILESIMO_POR_PONTO = 10_000`.
Logo `8,0012%` viaja como `80012`, e o par de campo do level up está congelado em
`tests/test_renda_par.py:99-100` como:

```
LEVEL_UP_ANTES = leitura(nivel=66, exp=685_632, adena=10_673_628)
LEVEL_UP_DEPOIS = leitura(nivel=67, exp=80_012, adena=13_160_684)
```
[VERIFIED: tests/test_renda_par.py:99-100]

## As quatro regras de par — assinaturas exatas e retorno

| Função | Linha | Assinatura | Retorno |
|---|---|---|---|
| `o_exp_andou_para_tras` | `:1479` | `(anterior, atual) -> RecusaDaRenda \| None` | `None` = tudo bem |
| `o_nivel_andou_para_tras` | `:1512` | `(anterior, atual) -> RecusaDaRenda \| None` | `None` = tudo bem |
| `a_adena_saltou_ordem_de_grandeza` | `:1538-1540` | `(anterior, atual, *, fator_de_salto: int) -> RecusaDaRenda \| None` | `None` = tudo bem |
| `conferir_o_par` | `:1584-1586` | `(anterior, atual, *, fator_de_salto: int) -> tuple[RecusaDaRenda, ...]` | **tupla VAZIA = par coerente** |

Comportamentos que decidem o desenho da Fase 2:

1. **`o_exp_andou_para_tras` se abstém quando o nível mudou, em qualquer direção**
   (`:1498-1499`: `if int(anterior.nivel) != int(atual.nivel): return None`). Isto é *exatamente*
   o que REND-03 precisa: o level up verdadeiro passa pela regra em silêncio. Ela **não calcula**
   `(100 − anterior) + atual` — isso a Fase 2 escreve.
2. **`o_nivel_andou_para_tras` só olha para baixo** (`:1527-1528`). Nível subindo nunca recusa.
3. **`a_adena_saltou_ordem_de_grandeza` é bidirecional de propósito** e a docstring já antecipa
   esta fase (`:1543-1545`): *"Gastar adena e normal — e a Fase 2 ja trata renda negativa"*. Ela
   **não** confunde gasto com salto: o critério é a **razão**, por multiplicação inteira
   (`:1572`: `if maior <= menor * int(fator_de_salto): return None`), e ela **se abstém quando
   qualquer lado é zero** (`:1569-1570`).
4. **`fator_de_salto` é somente-nomeado e SEM default**, e a docstring diz de onde ele vem
   (`:1562-1565`): *"Quem tem duas leituras e a Fase 2, e e la que o fator vem de cima — do
   `config.toml` do usuario, e nao deste fonte."* → **item de plano: a chave nova no `config.toml`
   e no `pydantic`/validador de config.**

## Elas compõem na conta, ou há lacuna?

**Há lacuna, e ela é de três formas.** A composição não é automática:

| O que a Fase 2 precisa | Existe? | Onde fica a lacuna |
|---|---|---|
| Detectar level up | Parcial | `o_exp_andou_para_tras` **se cala**; ninguém *afirma* "houve level up". A afirmação é `atual.nivel > anterior.nivel`, e a Fase 2 é quem escreve |
| Ganho no level up `(100−ant)+atual` | **Não** | Nenhuma linha de `renda_leitura.py` faz essa conta. Em décimos: `(1_000_000 − anterior.exp) + atual.exp` |
| Gasto = delta negativo de adena | **Não** | `a_adena_saltou_...` só recusa *ordem de grandeza*; um gasto normal passa e a Fase 2 tem de segregá-lo |
| **Nível recusado + EXP caindo** | **Não, e é a dívida nomeada no `02-CONTEXT.md:51-54`** | As quatro regras exigem `LeituraDaRenda` (os TRÊS inteiros — `:1431-1437`). Com o nível recusado **não existe par para conferir**. `conferir_o_par` não pode ser chamada; a Fase 2 precisa de um caminho próprio sobre `CamposDaRenda` |
| Salto do relógio para trás | **Não** | Nenhuma das quatro olha para `carimbo`. Ver §4 |

**A lacuna do nível recusado é a mais cara e é estrutural.** `ler_a_renda` devolve `RecusaDaRenda`
assim que **um** campo cai (`:1427-1430`), e `LeituraDaRenda` exige os três (`:1315-1319`). Se o
plano quiser gravar adena quando o nível recusou — e o `02-CONTEXT.md:90-93` **exige** gravar as
recusas —, ele consome `ler_os_tres_campos` (`CamposDaRenda`) e **não** `ler_a_renda`. Isso
significa que **`ler_a_renda` provavelmente não é chamada por esta fase**, apesar de o
`02-CONTEXT.md:116-117` a listar como ativo reusável.

## Confirmação: NENHUM chamador de produção — e o teste que prova isso é o que a Fase 2 derruba

Varredura da árvore inteira, excluindo `.claude/worktrees/`:

```
l2scanner/renda_modo.py:98      ler_os_tres_campos,          (import)
l2scanner/renda_modo.py:363     campos = ler_os_tres_campos(frame, personagem=personagem, calibracao=cal)
```
Nenhum outro. As quatro regras de par **não têm um único chamador fora de `renda_leitura.py`**
(a composição interna em `:1601-1607` não conta). [VERIFIED: varredura `grep` sobre `l2scanner/`
e `tests/`, cruzada com o portão de AST abaixo]

E o portão que **prende** isso:

```python
# tests/test_renda_par.py:591-623
def test_NENHUM_CAMINHO_DE_PRODUCAO_DESTA_FASE_CHAMA_AS_TRES_REGRAS(self):
    raiz = FONTE_DO_MODULO_PURO.parent            # -> l2scanner/
    das_regras = {"o_exp_andou_para_tras", "o_nivel_andou_para_tras",
                  "a_adena_saltou_ordem_de_grandeza", "conferir_o_par"}
    for modulo in sorted(raiz.glob("*.py")):      # TODO l2scanner/*.py
        ...
    de_fora = [c for c in chamadas if not c.startswith("renda_leitura.py")]
    assert not de_fora, (... "\nA Fase 1 nao tem a leitura anterior. Quem chama e a Fase 2")
```
[VERIFIED: tests/test_renda_par.py:591-623]

> ### ⚠️ ACHADO C-1 — este teste FALHA no instante em que a Fase 2 escreve a primeira chamada.
> Ele varre `l2scanner/*.py` com `Path.glob`, não uma lista. Um `renda_conta.py` que chame
> `conferir_o_par` é acusado com nome e linha. **A Tarefa 1 do plano tem de invertê-lo**, não
> apagá-lo: de "ninguém chama" para "o único chamador é `<módulo novo>.py`, e a Fase 1 continua
> sem chamador". A mensagem de erro dele já antecipa o evento ("Quem chama e a Fase 2"), mas
> quem executa às 2h da manhã vê um teste vermelho e não uma transição planejada.

---

# 2. `mercado_registro.py` — o dialeto, fatiado em copiável × mercado-específico

**881 linhas.** A boa notícia: o corte já está feito no fonte, e está documentado por quê
(`mercado_registro.py:405-409`): *"As duas conferencias sao sobre o ARQUIVO e nao sobre o
REGISTRO, entao moram no modulo e a classe as CHAMA."*

## Como uma linha é apendada, passo a passo

`RegistroDeObservacoes.registrar` (`:799-881`):

1. `if not self.ligado: return False` (`:828-829`) — desligamento é para a **sessão inteira**.
2. Dedup em memória **antes de tocar o disco** (`:831-833`).
3. `campos = campos_da_observacao(linha, agora)` (`:835`) — o carimbo entra por parâmetro
   (`:176-179`) e sai `agora.isoformat()` (`:191`), datetime ingênuo, hora local, sem fuso.
4. A escrita, verbatim (`:852-855`):
   ```python
   try:
       with self.arquivo.open("a", encoding="utf-8", newline="") as destino:
           csv.writer(destino, delimiter=SEPARADOR).writerow(campos)
           destino.flush()
   except OSError as erro:
   ```
5. `except OSError` **e só** (`:843-851`, com os quatro errno medidos: 13, 2, 17). Não
   `except Exception`.
6. Falha → `self.ligado = False`, **definitivo para a sessão, sem retry** (`:857-861`).
7. `self.chaves.add(chave)` **só depois de a linha chegar ao arquivo** (`:876-880`).

Arquivo novo: `carregar` (`:650-693`) pega `FileNotFoundError` e chama `_criar_com_cabecalho`
(`:788-795`), que abre em `"w"` e escreve `COLUNAS` — modo `"w"` só alcança arquivo que não
existe. Zero bytes é o **único** caso que não passa pelo portão (`:673-687`).

As três decisões de escrita, com os números medidos (`:810-826`):
- `flush()` sem `fsync()` — 0,0037 ms contra 1,5990 ms, 432×.
- **Abrir e fechar por linha** — 0,1295 ms; com a alça já aberta, marcar somente-leitura **não**
  impede a escrita, o `PermissionError` só nasce no `open`.
- `newline=""` — sem ele o `csv` escreve `\r\r\n` no Windows.

## A receita que `renda_registro.py` copia — e o que NÃO copia

| Peça | Linha | Dialeto (copiar) | Mercado-específico (NÃO copiar) |
|---|---|---|---|
| `SEPARADOR = ";"` | `mercado_catalogo.py:688` | ✅ importar ou redefinir; a razão está em `:684-687` (vírgula decimal colapsaria o Sheets) | — |
| `RAIZ = Path(__file__).resolve().parent.parent` | `raiz.py:88` | ✅ **importar de `raiz.py`, nunca redefinir** (`raiz.py:12-15`) | — |
| `conferir_o_terminador(bruto, arquivo)` | `:412-477` | ✅ **corpo inteiro, sem uma linha de mudança** — não conhece coluna nenhuma | ❌ o texto `"MERCADO DESLIGADO — …"` (`:464`) e a frase sobre alertas de party (`:473-474`) |
| `conferir_o_cabecalho(linhas, arquivo)` | `:480-513` | ✅ a **forma** (três estados: ausente / idêntico / divergente, `:490-492`) | ❌ **`COLUNAS` é global fechado** (`:495`: `if encontrado == COLUNAS`). Não é parametrizável hoje |
| `ContratoDoArquivoQuebrado` | `:139-146` | ✅ a doutrina (arquivo INTEIRO recusado ≠ linha ruim) | ❌ a classe em si — herdar de `mercado_registro` acoplaria os dois workstreams. Classe própria |
| `_criar_com_cabecalho` | `:788-795` | ✅ literal | — |
| `registrar` (o corpo do `try`/`except OSError`) | `:852-874` | ✅ literal, inclusive o `ligado = False` sem retry | ❌ a **dedup por chave** (`:831-833`) — ver abaixo |
| `escrever_leiame` | `:383-402` | ✅ o padrão (escrever só se ausente, nunca sobrescrever, `:386-391`) | ❌ o `TEXTO_DO_LEIAME` (`:301-380`) |
| `observacoes_do_arquivo` | `:516-604` | ✅ a estrutura: ler → terminador → `csv.reader` → cabeçalho → laço com `warning` por linha ruim | ❌ `chave_dos_campos`, `ObservacaoLida`, `residuo_dos_campos` |
| `COLUNAS` | `:129-136` | ❌ **nada aqui serve** | ❌ `chave_da_serie, nome_exibido, primeira_vez, total_em_centesimos, quantidade, residuo_do_cruzamento` |

> ### ⚠️ ACHADO C-3 — a dedup do `.mercado/` é ativamente ERRADA para o `.renda/`.
> `chave_da_observacao` exclui o carimbo de propósito (`:161-163`): *"incluir o carimbo tornaria a
> dedup VACUA: cada tick tem carimbo diferente, entao toda observacao seria nova e o arquivo
> cresceria uma linha por segundo sobre o mesmo anuncio."* No `.renda/` **uma linha por tick é
> exatamente o produto** — é o denominador da taxa. Copiar a dedup apagaria toda amostra em que o
> nível, o EXP e a adena não mudaram, que é a maioria delas a 1 Hz, e destruiria o denominador.
> **O `renda_registro` não tem dedup, não tem `self.chaves` e não tem índice em memória.**
>
> Consequência para REG-02: o "reiniciar não inventa nem apaga renda" **não** vem do índice em
> memória (esse era o mecanismo do mercado, `:616-618`). Vem de outra coisa: a primeira amostra
> após o arranque não tem `anterior`, logo é âncora e não delta. Isso é regra da **conta**, não do
> **registro** — e o `ROADMAP.md:39-41` já tinha dito exatamente isso ("REG-02 é uma regra de taxa
> vestida de persistência"), mas o `02-CONTEXT.md` não repete.

Constantes verbatim para copiar com a convenção certa:
```
ARQUIVO_DE_OBSERVACOES = "observacoes.csv"        # mercado_registro.py:96
ARQUIVO_DO_LEIAME = "LEIAME.txt"                  # mercado_registro.py:103
PASTA_DO_MERCADO = RAIZ / ".mercado"              # mercado_catalogo.py:681
SEPARADOR = ";"                                    # mercado_catalogo.py:688
```
[VERIFIED: l2scanner/mercado_registro.py:96,103; l2scanner/mercado_catalogo.py:681,688]

> ### ⚠️ ACHADO C-4 — `.renda/` não está no `.gitignore`, e nada no plano o menciona.
> `.gitignore:30,33,38` lista `.agenda/`, `.loot/` e `.mercado/`, cada uma com a razão escrita
> ao lado (`:34-38`: *"estado local, DURAVEL e sem poda"*). `.renda/` **não está lá**. Sem a
> entrada, o primeiro `git status` depois de rodar a Fase 3 despeja o CSV de farm no repositório.
> Uma linha, e ela some do radar se não estiver no plano.

> ### ⚠️ ACHADO C-5 — "um arquivo por personagem por dia, na forma que o `.mercado/` e o `.loot/`
> já usam" (`02-CONTEXT.md:87`) descreve uma forma que **nenhum dos dois tem**.
> - `.mercado/` é **um arquivo só, que cresce, SEM ROTAÇÃO** — dito com essas letras em
>   `mercado_registro.py:610`: *"UM ARQUIVO SO, QUE CRESCE, SEM ROTACAO (D-09)"*.
> - `.loot/` **não é CSV**: é uma pasta de marcadores vazios com prefixo, `pegou_{YYYY-MM-DD}-
>   {HHMM}_{slug}`, `nick_{slug}` e `proximo.json` (`loot.py:181-190`, formato em `:57`
>   `_FORMATO_CARIMBO = "%Y-%m-%d-%H%M"`).
> - Um arquivo por dia **não existe em lugar nenhum da árvore**. A única `strftime` com data é
>   `gravador.py:78`, e é nome de **pasta de gravação**, não rotação de registro.
>
> O plano tem que decidir a forma de verdade, e a escolha **muda o esquema que o `dashboard`
> consome** — ou seja, é irreversível barato só antes da Fase 3. As duas saídas honestas:
> **(a)** um arquivo só com coluna `personagem` (é o precedente real do `.mercado/`, e REG-04 já
> pede a coluna); **(b)** `.renda/<Personagem>/<AAAA-MM-DD>.csv`, que é forma nova neste
> repositório e precisa do argumento escrito, incluindo o que o leitor faz na virada da meia-noite
> no meio de uma janela móvel de 10 minutos.

---

# 3. `dashboard_dados.py` — `ArquivoRecortado`, `observacoes_ao_vivo`, e a refutação do ROADMAP

## Como a leitura tolerante funciona

`observacoes_ao_vivo(arquivo)` (`:380-469`) — **20 linhas de mecânica, 50 de prosa**:

```python
corte = bruto.rfind("\n")                       # :444
if corte < 0:
    return LeituraAoVivo(cauda_incompleta=True) # :445-448
completo = bruto[: corte + 1]                   # :450
cauda    = bruto[corte + 1 :]                   # :451
return LeituraAoVivo(
    observacoes=mercado_registro.observacoes_do_arquivo(
        ArquivoRecortado(caminho_real=arquivo, texto=completo)),   # :454-456
    linhas_completas=max(0, len([l for l in completo.splitlines() if l.strip()]) - 1),
    cauda_incompleta=bool(cauda),               # :468
)
```
[VERIFIED: l2scanner/dashboard_dados.py:444-469]

O ponto de desenho está em `:399-404`: *"O CORTE ACONTECE ANTES DO PORTAO, E POR ISSO O PORTAO
CONTINUA EXISTINDO."* O texto entregue termina em `\n` por construção, então
`conferir_o_terminador` é chamada e **passa**; `conferir_o_cabecalho` é chamada e **continua
desligando alto**. Nenhum portão foi afrouxado.

`ArquivoRecortado` (`:271-342`) é um `@dataclass(frozen=True)` com `caminho_real: Path`,
`texto: str`, e três métodos: `open(*args, **kwargs) -> io.StringIO` (argumentos **aceitos e
ignorados**, `:330-335`), `__str__` e `__fspath__` (`:338-342`). O preço está dito em voz alta
(`:316-321`): é **acoplamento de FORMA** — se o parser passar a chamar `.stat()`, quebra com
`AttributeError`.

A medição que sustenta tudo (`:406-418`): **zero** leituras sem terminador em **22.970** sondagens
durante 200.000 appends; controle positivo (escrita em duas chamadas com pausa) acusou **3.252 de
4.079**. E a conclusão que o plano precisa herdar (`:420-424`): *"esta degradacao e REDE DE
SEGURANCA, e nao o caminho normal."*

## O que o `dashboard` precisaria para ler `.renda/` — e por que "uma lista de colunas" é falso

> ### 🔴 ACHADO C-2 — A afirmação do `ROADMAP.md:274` e do `REQUIREMENTS.md:284` — *"O `dashboard`
> acrescenta uma lista de colunas, não um parser"* — **está errada, e o código diz onde.**

A cadeia real, com linha:

1. `observacoes_ao_vivo` **chama `mercado_registro.observacoes_do_arquivo` por nome**
   (`dashboard_dados.py:454`). Não recebe o parser por parâmetro. Não há ponto de injeção.
2. `observacoes_do_arquivo` chama `conferir_o_cabecalho(linhas, arquivo)`
   (`mercado_registro.py:560`), que compara contra o **global** `COLUNAS`
   (`mercado_registro.py:495`: `if encontrado == COLUNAS: return`). Não é parâmetro. Um CSV de
   renda com cabeçalho próprio **levanta `ContratoDoArquivoQuebrado` na primeira linha**.
3. O laço de tipagem chama `chave_dos_campos(campos)` (`:570`) e monta `ObservacaoLida` com
   `campos[COLUNAS.index("nome_exibido")]`, `COLUNAS.index("primeira_vez")`,
   `residuo_dos_campos(campos)` (`:586-601`). Cada uma dessas três é mercado puro.
4. Acima disso, `payload(pasta_do_mercado, agora, cambio=None)` (`:918`) constrói
   `ModeloDeMercado.de_observacoes(...)`, filtra por `CHAVE_DA_SERIE_DA_ADENA`, e chama
   `menor_pedido_visivel`, `mediana_dos_unitarios`, `recencia_do_preco` (`:977-982`), decide entre
   cinco `ESTADOS` (`:984-990`) e aplica câmbio. **Nada disso tem significado para uma amostra de
   renda.**

**A conta honesta do que o `dashboard` precisa:** um `LeituraAoVivo` próprio (ou um genérico), um
parser de linha próprio, um `payload_da_renda` próprio, e uma seção própria na página. Ou seja:
**um segundo parser**, exatamente o que o REG-03 disse que não haveria. O que **de fato** se
reusa, e é bastante, é (a) o algoritmo de corte de cauda — 6 linhas, `:444-451`; (b) a forma do
`ArquivoRecortado`; (c) `conferir_o_terminador` **inteiro**, que é o único trecho genuinamente
agnóstico de coluna.

**E há um segundo motivo, de custo de import, para não tentar:** `dashboard_dados.py:71-77`
importa de `mercado_console`, que importa `console` → `rastreador` → `visao` → `cv2`
(`raiz.py:53-54`, com o número medido: 350 módulos com `cv2` e `numpy`). Um `renda_registro.py`
que importasse `ArquivoRecortado` de `dashboard_dados` arrastaria OpenCV para dentro do registro.
**A cópia de 6 linhas é mais barata que o import**, e o `raiz.py:44-63` já escreveu a doutrina.

**Redação sugerida para o fonte (a refutação vai escrita, como o REG-03 pede):**
> `dashboard_dados.observacoes_ao_vivo:454` chama `mercado_registro.observacoes_do_arquivo` por
> nome, e ela confere o cabeçalho contra o global `COLUNAS` (`mercado_registro.py:495`). Um CSV
> de renda levanta `ContratoDoArquivoQuebrado` na primeira linha. "Uma lista de colunas" é falso;
> o que atravessa é o **dialeto** e a **disciplina de falha**, não o parser.

---

# 4. `relogio.py` — o tempo por parâmetro, e o buraco do salto para trás

## A disciplina, medida

`grep` sobre `l2scanner/*.py` por `datetime.now()` / `time.time()`: **17 ocorrências, e nenhuma
em módulo de cálculo.** As que existem são casca (`__main__.py:2165`, `dashboard.py:542,604`),
cosmético de tela (`console.py:143`, `mercado_console.py:688`) ou nome de pasta
(`gravador.py:78`). Os módulos puros **declaram a ausência na docstring**: `acervo.py:46`,
`aprendiz.py:12`, `loot.py:23-25`, `presenca.py:26`, `esquecimento.py:51`,
`mercado_console.py:360`, `dashboard_dados.py:925`. [VERIFIED: varredura `grep` sobre `l2scanner/`]

## O padrão exato que a Fase 2 segue

Há **duas** convenções na casa, e a Fase 2 já herdou uma delas da Fase 1:

| Convenção | Tipo | Onde | Quem usa |
|---|---|---|---|
| `agora: datetime` por parâmetro em toda função | `datetime` ingênuo, hora local | `mercado_registro.campos_da_observacao(linha, agora)` `:173`; `dashboard_dados.payload(..., agora, ...)` `:918`; `loot.responder_consulta(..., agora)` `:888` | tudo que escreve carimbo ou desenha recência |
| `carimbo: float` (epoch) por parâmetro | `float` | `renda_leitura.LeituraDaRenda.carimbo` `:1319`; `ler_a_renda(..., carimbo: float)` `:1416` | **a Fase 1 da renda** |

> **Item de plano, pequeno e chato:** a Fase 1 escolheu `float` epoch (`renda_leitura.py:1319`) e
> o dialeto do registro escreve `agora.isoformat()` (`mercado_registro.py:191`). A Fase 2 é onde
> as duas se encontram. Recomendação: **manter `float` na aritmética** (subtração de epochs é
> exata e é o denominador da taxa) e **converter para `datetime` só na fronteira do disco**, com
> `datetime.fromtimestamp(carimbo)` — que é literalmente o que `Relogio.agora` faz
> (`relogio.py:163`). Uma conversão, num lugar, com o motivo escrito.

A fonte de verdade: `Relogio.agora() -> datetime` (`relogio.py:156-163`) e
`Relogio.agora_epoch() -> float` (`:146-154`). A Fase 2 recebe o número, **nunca o `Relogio`** —
receber o objeto reintroduziria a chamada de relógio dentro do módulo puro.

## O relógio que anda para trás: há precedente, mas ele é fraco, e a Fase 2 é a primeira a nomear

**O que `relogio.py` resolve:** depois de ancorado, o avanço vem do monotônico
(`:152-154`), então um pulo de 3h no Windows **não move** a hora
(`tests/test_relogio.py:105-118`).

**O que ele NÃO resolve, e são dois buracos que caem exatamente nesta fase:**

1. **Sem âncora, o pulo aparece inteiro.** `agora_epoch` cai em `self._parede()` quando
   `_ancora_epoch is None` (`:147-151`), e há teste *exigindo* esse comportamento:
   `test_sem_ancora_o_pulo_aparece_porque_o_fallback_e_honesto`
   (`tests/test_relogio.py:120-134`) afirma `relogio.agora_epoch() - antes == TRES_HORAS`. Sem
   Chatwoot (offline, Cloudflare barrando, `.env` ausente) a Fase 2 recebe carimbos que saltam.
2. **A reancoragem periódica pode mover a hora PARA TRÁS no meio da sessão.** `sincronizar()`
   troca a âncora sem comparar com a anterior (`:121-122`:
   `self._ancora_epoch = float(epoch); self._ancora_mono = (antes + depois) / 2`), e há teste
   afirmando que a segunda âncora vale (`tests/test_relogio.py:90-101`). O laço roda a cada
   `INTERVALO_PADRAO = 1800.0` (`:50`). Se o Windows estava 3h adiantado e o Chatwoot corrige,
   **duas amostras consecutivas podem ter `carimbo` decrescente**.

**Precedente para tratar tempo que anda para trás — existe UM, e é raso:**

```python
# mercado_catalogo.py:858-861 (docstring de `registrar`)
"`primeira_vez` e MIN e `ultima_vez` e MAX, e nao 'a que chegou por ultimo': horario de
 verao e ajuste de NTP andam para tras de verdade, e um tick com relogio atrasado nao pode
 fazer a serie parecer mais nova nem mais velha do que o material prova."
```
[VERIFIED: l2scanner/mercado_catalogo.py:858-861]
Implementado como `min`/`max` (`:877-878`). Isso **absorve** o salto — não o **nomeia**.

**Veredito:** a Fase 2 é a **primeira** deste repositório a tratar um salto para trás como
*evento nomeado*. O `02-CONTEXT.md:101-102` acerta ao exigi-lo. E o formato já existe: a
descontinuidade é uma `RecusaDaRenda`-alike com `motivo` próprio — o molde de `_recusar`
(`renda_leitura.py:211`) e dos três `MOTIVO_*_PARA_TRAS` (`:140-142`). Um quarto irmão,
`"relogio-andou-para-tras"`, fecha a simetria que o `02-CONTEXT.md:102` pede: *"É o mesmo formato
dos outros dois deltas negativos desta fase."*

**E o teste é de graça:** `tests/test_relogio.py:45-47` já tem `Maquina.pular_parede(segundos)`,
com a docstring *"O que o dual boot faz: so o relogio de parede salta."*

---

# 5. `loot.py` e `sessao.py` — a pergunta de reuso, respondida com NÃO

## `sessao.py` não é o que o nome sugere

`Sessao` (`sessao.py:189-194`) é: *"Estado de UMA execução do scanner, e o que fazer a cada
frame."* — o **núcleo testável do laço de alertas de party**. O `__init__` recebe 20 parâmetros
(`:196-219`): `rastreador`, `eventos_agendados`, `despachante`, `leitor_de_comandos`, `gravador`,
`loot`, `manutencao`, `membros`, `mercado`, `bosses`, `regras_de_respawn`, `aprendiz`, `acervo`,
`pendentes_de_batismo`. Ela importa `agenda`, `aprendiz`, `batismo`, `console`, `frames`, `loot`,
`notificador`, `presenca`, `rastreador`, `respawn`, `visao` (`:44-74`) — ou seja, `cv2` e a
árvore inteira.

Ela **não acumula amostras**, **não escreve linhas** e **não calcula taxa**. Ela decide, despacha
e registra eventos de morte/saída/ressurreição por frame.

**Veredito: outra coisa inteiramente. A Fase 2 não reusa, não estende, e não deve nem importar.**
Reusá-la puxaria o notificador do WhatsApp e o OpenCV para dentro de um módulo que o
`02-CONTEXT.md:18-21` fecha explicitamente sem laço. E há um agravante: a Fase 3 (`--renda`) é um
**processo separado** (`ROADMAP.md:307`), então nem lá `Sessao` serve.

## `loot.py` é precedente de doutrina, não de código

`RegistroDeLoot` (`loot.py:178-225`) é uma pasta de marcadores vazios criados com
`os.O_CREAT|os.O_EXCL` (`:208-210`), tri-estado `criado|ja_existia|falhou` (`:199-216`). Zero CSV.
O que a Fase 2 herda dele são **duas frases**, e as duas já estão citadas no `02-CONTEXT.md`:

```
# loot.py:11-14
1. **Pasta propria, sem poda.** O `.agenda/` apaga marcadores com prefixo de data depois de
   3 dias — certo para "ja avisei", fatal para estatistica. O `.loot/` NUNCA e podado:
   "quantos loots o J4guar pegou" e uma pergunta sobre meses, nao sobre a semana.
```
```
# loot.py:23-25
MESMA DISCIPLINA DA AGENDA: o tempo entra por parametro em tudo. Nenhum `datetime.now()`,
nenhum relogio proprio — e o que permite testar a corrida de duas instancias e o consumo
atrasado em milissegundos.
```
[VERIFIED: l2scanner/loot.py:11-14, 23-25]

## O analógo de verdade é `mercado_modo.py`, e ninguém o citou

O que se parece com "uma sessão que acumula e escreve linhas" é o par
`Contagem` + `processar_a_pagina_aceita` do `mercado_modo.py`:

```python
# mercado_modo.py:137-151
@dataclass
class Contagem:
    """O que a costura viu, em tres numeros que nao se disfarcam um do outro. ...
    `duplicadas` e `perdidas` sao FATOS DIFERENTES e por isso sao campos diferentes."""
    observacoes: int = 0
    duplicadas: int = 0
    perdidas: int = 0
    series: set[str] = field(default_factory=set)
```
[VERIFIED: l2scanner/mercado_modo.py:137-151]

E `processar_a_pagina_aceita(linhas, *, modelo, catalogo, registro, trava_do_destaque, contagem,
agora)` (`:207-216`) — a extração do corpo do laço, que **devolve textos em vez de imprimir**
(`:225-229`), com `contagem` mutada no lugar. Fechada por `mercado_console.resumo_da_sessao(leitor,
contagem, motivos, orcamento)` (`mercado_console.py:668-685`), que separa três blocos: o que a
TELA entregou, o que foi para o DISCO, e os motivos de descarte agregados.

**Esta é a forma que a Fase 2 deve copiar.** É exatamente a estrutura que o `02-CONTEXT.md:90-93`
descreve sem nomear ("por que a taxa desta hora tem n=12 se o scanner rodou 40 minutos"): uma
`Contagem` com `aceitas`, `recusadas_por_motivo` e `lacunas` — três fatos que não se somam. E ela
é pura, sem laço, testável em milissegundos.

---

# 6. `calibration.json` + `calibracao.py` — o custo exato de `renda_ponte_de_xp`

## Os quatro lugares, e a ordem

| # | Arquivo | Linha de referência | O que fazer |
|---|---|---|---|
| 1 | `l2scanner/calibracao.py` | ao lado de `:749` | `renda_ponte_de_xp: dict \| None = None`, com o bloco de comentário no molde das irmãs (`:665-748`) |
| 2 | `l2scanner/calibracao.py` | `salvar`, após `:914` | `"renda_ponte_de_xp": self.renda_ponte_de_xp,` — dict CRU, sem reconstrução |
| 3 | `l2scanner/calibracao.py` | `carregar`, após `:1078` | `renda_ponte_de_xp=dados.get("renda_ponte_de_xp"),` |
| 4 | `l2scanner/calibracao.py` | `_conferir_as_chaves_da_renda`, após `:1628` | `_conferir_a_ponte_de_xp(dados.get("renda_ponte_de_xp"))` + a função, no molde de `_conferir_a_renda_por_personagem` (`:1382-1440`) |
| **5** | **`tests/test_calibracao_renda.py`** | **`VALORES_ESPECIAIS`, `:134-151`** | **`"renda_ponte_de_xp": ponte_de_xp_de_exemplo(),`** — ver o achado abaixo |

`VERSAO_DO_ESQUEMA` **fica em 2** (`calibracao.py:23`) — as chaves da renda são opcionais e a
Fase 1 já provou o caminho: *"ambas opcionais com a `VERSAO_DO_ESQUEMA` intacta em 2"*
(`01-01-SUMMARY.md:79-80`).

E o acessor, no molde de `renda_do_personagem` (`:1082-1104`): um
`ponte_do_nivel(personagem, nivel) -> dict | None` que devolve a entrada **daquele nível daquele
personagem** ou **nada** — nunca a do nível anterior, que é o que o `02-CONTEXT.md:70-72` exige.

## Confirmação: o teste estrutural PEGA o esquecimento — e o controle positivo prova

```python
# tests/test_calibracao_renda.py:200-210
def diferenca_entre_campos_e_chaves(dados: dict) -> tuple[set[str], set[str]]:
    """`(campos sem chave, chaves sem campo)`. As DUAS direcoes importam."""
    campos = {f.name for f in dataclasses.fields(Calibracao)}
    chaves = set(dados)
    return campos - chaves, chaves - campos
```
```python
# tests/test_calibracao_renda.py:216-232
def test_NENHUM_CAMPO_DO_DATACLASS_FICA_DE_FORA_DO_SALVAR(self, tmp_path):
    ...
    assert not sem_chave, (f"estes campos existem no dataclass e NAO sao emitidos pelo "
                           f"`salvar`: {sorted(sem_chave)}. ...")
    assert not orfas, (...)
```
[VERIFIED: tests/test_calibracao_renda.py:200-232]

**Sim, ele pega — e nas duas direções.** Um campo no dataclass sem entrada no `salvar` é acusado
**pelo nome**. O controle positivo do lado (`:234-252`) deleta `renda_por_personagem` do dict
emitido e afirma `sem_chave == {"renda_por_personagem"}`; o irmão (`:254-264`) injeta uma chave
órfã e afirma `orfas == {"renda_piso_de_brilho"}`. E há um terceiro guarda que impede o teste de
ficar vácuo: `test_A_MONTAGEM_NAO_DEIXA_NENHUM_CAMPO_NO_DEFAULT` (`:266-278`).

Há ainda um **quarto** portão, mais forte, em outro arquivo: `TestOControleDoCampoNovo`
(`tests/test_calibrar_renda_nao_apaga_nada.py:513-539`) sintetiza uma dataclass com
`fields(Calibracao)` **mais um campo** (`NOME_DO_CAMPO_NOVO = "renda_um_campo_que_ainda_nao_existe"`,
`:529`) e prova que a conferência pegaria um campo que ainda não existe — *"que e o modo de falha
de verdade, porque ninguem remove uma chave do `salvar` de proposito, mas todo mundo acrescenta
campo ao dataclass"* (`:519-521`).

> ### ⚠️ ACHADO — o passo 5 da tabela é obrigatório e é fácil de esquecer.
> `_valor_por_tipo(campo)` (`tests/test_calibracao_renda.py:154-181`) despacha **por tipo**, e
> `dict | None` cai em `:173-174` → `{"uma": "coisa"}`. Se a Fase 2 escrever
> `_conferir_a_ponte_de_xp` com validação de forma (e o `02-CONTEXT.md:73-78` **exige** que a
> constante carregue procedência, o que é forma), `{"uma": "coisa"}` **não passa no validador** e
> `test_TODO_CAMPO_SOBREVIVE_AO_SALVAR_MAIS_CARREGAR` (`:284-288`, que chama `Calibracao.carregar`)
> quebra. A correção é uma entrada em `VALORES_ESPECIAIS` (`:134-151`), exatamente como
> `renda_por_personagem` e `renda_moldes_da_barra` já têm (`:137-138`).
>
> **É o mesmo trabalho que a Fase 1 já fez duas vezes.** Não é surpresa — é uma linha que precisa
> estar no plano, senão vira 40 minutos de depuração.

E a preservação contra os outros calibradores é **de graça, e está provado**: o
`fundir_com_a_calibracao_em_disco` preserva por **subtração** de `fields(Calibracao)`, não por
lista escrita a mão — *"ela sobrevive por SUBTRACAO de `fields(Calibracao)`, e nao por alguem ter
lembrado de inscreve-la numa lista"* (`tests/test_calibrar_renda_nao_apaga_nada.py:456-458`). Há
teste para o calibrador da party, o do TvT e o da renda (`:451-510`).

---

# 7. Precedente de taxa por hora — **não existe**, e a forma que existe é outra

## O achado

`grep` sobre `l2scanner/*.py` por `por_hora`, `/ 3600`, `total_seconds()`, `taxa_por`,
`_por_minuto`: **nenhuma taxa de grandeza por unidade de tempo.** As 30 ocorrências de `3600` são
formatação de duração (`__main__.py:681,2054`, `manutencao.py:603-604`), cadência de laço
(`mercado_modo.py:643`, `bosses.py:381`), recência textual (`mercado_console.py:511-518,782-788`)
ou contas de volume de log em comentário. [VERIFIED: varredura `grep` sobre `l2scanner/`]

Os três candidatos, checados um a um:
- `mercado_analise.py` — `unitario()` é `total/quantidade` (`:178`), não por tempo. `tendencia()`
  faz regressão sobre o **ordinal** `1..n` e **proíbe o carimbo como eixo x**, com o motivo
  medido (`:431-443`).
- `agenda.py` — só aritmética de alvo/tolerância (`:347`).
- `dashboard_dados.py` — `baldes()` (`:612-650`) agrega por janela de tempo, mas devolve
  `median_low` **de valores**, não uma taxa.

**A Fase 2 inventa a aritmética.** É o único trecho desta fase sem precedente na árvore.

## A forma que ela deve seguir — e essa existe, verificada

### (a) `n` viaja DENTRO do resultado, com o piso junto

```python
# mercado_analise.py:226-249
@dataclass(frozen=True)
class Evidencia:
    """Quantas ofertas distintas sustentam este numero, e quantas faltariam.

    ELA VIAJA DENTRO DE TODO RESULTADO, e nao ao lado dele: estatistica sem `n`
    e adivinhacao com cara de numero, e um `n` que quem desenha pode esquecer de
    pedir e um `n` que uma hora nao vai ser exibido.

    ABAIXO DO PISO A RESPOSTA E O QUE FALTA, NUNCA UM NUMERO ..."""
    n: int
    piso: int
    @property
    def suficiente(self) -> bool: return self.n >= self.piso
    @property
    def faltam(self) -> int: return max(0, self.piso - self.n)
```
[VERIFIED: l2scanner/mercado_analise.py:226-249]

Pisos existentes, verbatim (`mercado_analise.py:152,162,170`):
`N_MINIMO_PARA_MENOR = 1`, `N_MINIMO_PARA_MEDIANA = 5`, `N_MINIMO_PARA_TENDENCIA = 8`.
E a natureza deles está declarada em `dashboard_dados.py:265-267`: *"ESCOLHA, NAO MEDICAO, no
molde de `N_MINIMO_PARA_MEDIANA`."*

### (b) Abaixo do piso, a resposta é o MOTIVO — nunca um número

```python
# mercado_analise.py:414-425
@dataclass(frozen=True)
class Tendencia:
    """`variacao_percentual` e `None` sempre que nao ha numero a dizer, e
    `motivo_da_ausencia` diz POR QUE ..."""
    evidencia: Evidencia
    variacao_percentual: float | None
    motivo_da_ausencia: str | None
```
[VERIFIED: l2scanner/mercado_analise.py:414-425]
Retorno abaixo do piso: `motivo_da_ausencia="evidencia insuficiente"` (`:464`).

**Aplicação direta a REND-05:** "tempo até o nível" com `exp_por_hora == 0` é o mesmo caso do
`intercept == 0` (`:474-479`) — motivo nomeado, nunca divisão por zero escapando, nunca `inf`.

### (c) A UNIDADE da janela é obrigatória e é o requisito

```python
# mercado_analise.py:405-411
# ELA E OBRIGATORIA E A ESCOLHA DELA E O REQUISITO. "Ofertas distintas" e o que
# impede o usuario de ler a reta como "o preco caiu tanto por cento nas ultimas
# dez HORAS". Nao existe serie temporal de preco neste CSV ...
UNIDADE_DA_JANELA = "ofertas distintas"
```
[VERIFIED: l2scanner/mercado_analise.py:405-411]
Na renda a unidade **é** tempo, e a escolha é a mesma família: `"minutos farmados"` (denominador
sem lacuna) ≠ `"minutos de relógio"`. O `02-CONTEXT.md:34-38` decide por farmados; a palavra tem
de ir junto do número, senão o usuário lê errado.

### (d) A recência é um fato SEPARADO do valor

`recencia_do_preco` (`mercado_analise.py:375-398`) devolve `max(primeira_vez)` e a docstring gasta
15 linhas explicando que **não é** o carimbo do menor pedido: *"exibir o minimo de terca ao lado
da recencia de hoje seria a mesma mentira, dentro da mesma linha."* (`:389-391`).

### (e) Nada de `float` no que é diferenciado

```
# dashboard_dados.py:624-628
O INDICE E INTEIRO EXATO: `(t - ancora) // largura` opera sobre os microssegundos inteiros do
`timedelta`. `total_seconds()` devolveria `float` — medido, **69713.696** contra **69713**
inteiro — e `float` e como um centavo aparece do nada.
```
[VERIFIED: l2scanner/dashboard_dados.py:624-628]
E o `assert in` por balde (`:636-638`) como forma executável do D-02.
Para a renda: EXP em décimos de milésimo (`renda_leitura.py:326`), adena em unidades, tempo em
segundos, e **`Fraction` na divisão da taxa** — nunca `float`. O precedente de `Fraction` está em
`mercado_analise.unitario` (`:178`) e no tipo de `baldes` (`:613`).

---

# 8. Convenções de teste para código dependente de tempo

## Idioma A — o relógio congelado (o mais usado)

```python
# tests/test_janela_no_relogio.py:115-126
class RelogioParado:
    """O relogio de verdade pergunta a hora ao Chatwoot. Este nao pergunta nada.

    Sem ele o teste dependeria do `.env` do usuario e da rede — as duas coisas
    que OPER-03 proibe."""
    def __init__(self, quando: datetime) -> None:
        self._quando = quando
    def agora(self) -> datetime:
        return self._quando
```
[VERIFIED: tests/test_janela_no_relogio.py:115-126]
Duplicado inline em `tests/test_agenda.py:1205-1210`, injetado por
`monkeypatch.setattr(principal, "montar_relogio", lambda *a, **k: RelogioParado(self.QUANDO))`
(`test_agenda.py:1218-1220`).

## Idioma B — a máquina que anda e que PULA (o que esta fase precisa)

```python
# tests/test_relogio.py:27-53
class Maquina:
    """O relogio da maquina, sob controle do teste."""
    def __init__(self, mono: float = 1000.0, parede: float = EPOCH_SERVIDOR) -> None:
        self.mono = mono
        self.parede = parede
    def monotonico(self) -> float: return self.mono
    def de_parede(self) -> float:  return self.parede
    def andar(self, segundos: float) -> None:
        """Tempo passando de verdade: os dois relogios andam juntos."""
        self.mono += segundos
        self.parede += segundos
    def pular_parede(self, segundos: float) -> None:
        """O que o dual boot faz: so o relogio de parede salta."""
        self.parede += segundos

def montar(maquina: Maquina, fonte) -> Relogio:
    return Relogio(fonte=fonte, monotonico=maquina.monotonico, parede=maquina.de_parede)
```
[VERIFIED: tests/test_relogio.py:27-53]
Com as constantes: `EPOCH_SERVIDOR = datetime(2026, 8, 25, 11, 46, 9, tzinfo=timezone.utc).timestamp()`
e `TRES_HORAS = 3 * 3600.0` (`tests/test_relogio.py:23-24`).

E a doutrina do arquivo (`tests/test_relogio.py:9-11`):
> *"Todo teste aqui injeta monotonico e parede. Nao ha rede, nao ha sleep e nao ha monkeypatch em
> lugar nenhum — a mesma disciplina de agenda.py, onde o tempo entra por parametro."*

## Idioma C — o mais simples, e o que a Fase 2 vai usar em 90% dos testes

Como a Fase 2 é **função pura sobre uma sequência de amostras**, a maioria dos testes não precisa
de relógio nenhum: monta-se `LeituraDaRenda(..., carimbo=0.0)`, `carimbo=60.0`, `carimbo=3600.0`.
É exatamente o que `tests/test_renda_par.py:85-93` já faz:

```python
def leitura(*, nivel: int, exp: int, adena: int, carimbo: float = 0.0):
    """Uma `LeituraDaRenda` montada a mao. Sem pixel, sem OCR, sem relogio."""
    return LeituraDaRenda(personagem="Faerlina", nivel=nivel, exp=exp,
                          adena=adena, carimbo=carimbo)
```
[VERIFIED: tests/test_renda_par.py:85-93]

**Uma noite inteira de farm cabe num teste** porque o carimbo é um `float` que o teste escolhe.
Isso é o que o `02-CONTEXT.md:18-21` promete, e o código já permite.

## Idioma D — o portão de fonte, quando a regra é "nunca chame o relógio"

`tests/test_renda_par.py:534-589` (`memoria_de_modulo`) lê a árvore sintática do módulo e acusa
escopo global mutável — **com controle positivo** que sintetiza um arquivo com `global` e afirma
`len(achados) == 2` (`:576-589`). O mesmo molde serve para "nenhum `datetime.now()` neste módulo".

---

## Don't Hand-Roll

| Problema | Não construa | Use | Por quê |
|---|---|---|---|
| Detectar cauda truncada no CSV | contagem de campos, validação por tipo | `conferir_o_terminador` copiado literal | Medido: das 5 truncagens byte a byte, **2 produzem 6 campos parseáveis** com `80` virando `8` (`mercado_registro.py:415-423`). Só o terminador pega, 5 de 5 |
| Ler o CSV enquanto o outro processo escreve | `csv.reader` direto | o corte `rfind("\n")` + o parser único | *"Duas implementacoes de leitura sao duas chances de uma delas nao ter o portao"* (`dashboard_dados.py:305-310`) |
| Migrar um cabeçalho divergente sozinho | `if cabecalho != COLUNAS: reescrever` | levantar e desligar a feature alto | `mercado_registro.py:481-492` — *"migrar sozinho um arquivo que o usuario edita a mao e importa no Sheets e exatamente como se corrompe dado calado"* |
| Reparar a cauda antes do próximo append | completar com `\n` | recusar e mandar o humano olhar | `mercado_registro.py:447-452` — a opção (b) *"e a PIOR das tres, porque preserva a linha possivelmente truncada E A PROMOVE"* |
| Índice de balde temporal | `total_seconds()` | `//` sobre `timedelta` | `dashboard_dados.py:624-628` — 69713.696 contra 69713 |
| Mediana que inventa valor | `statistics.median` | `statistics.median_low` + `assert in` | `dashboard_dados.py:630-638` — `median` sobre 4 `Fraction` devolveu `13/42`, *"um valor que nao esta na lista"* |
| Regressão com o carimbo no eixo x | `linear_regression(carimbos, valores)` | ordinais `1..n` | `mercado_analise.py:431-443` — carimbos separados por microssegundos dão inclinação absurda **sem levantar** |
| Escrever `calibration.json` | `caminho.write_text` | o `Calibracao.salvar` que já existe | `calibracao.py:916-939` — `.tmp` ao lado + `os.replace`; direto deixa JSON truncado e mata **o scanner de party inteiro** |
| Preservar chaves alheias ao calibrar | lista de campos a mão | subtração de `fields(Calibracao)` | `tests/test_calibrar_renda_nao_apaga_nada.py:456-458` |
| Ancorar baldes num instante arbitrário | primeira observação | `ancora_da_meia_noite` | `dashboard_dados.py:594-603` — âncora às 15:00 parte o dia civil ao meio |

**Key insight:** neste repositório, quase toda tentação de "fazer simples" já foi tentada, medida
e refutada por escrito no fonte, com o número ao lado. Antes de escrever qualquer conta nova, o
plano deve procurar a docstring que já a recusou.

---

## Common Pitfalls

### Pitfall 1: gravar `float` no CSV e diferenciar depois
**O que dá errado:** a taxa acumula erro binário invisível ao longo de uma noite.
**Por quê:** `renda_leitura.py:1304-1308` já escreveu a regra — *"Nenhum `float` atravessa esta
fronteira -- o produto inteiro da milestone e uma DIFERENCA entre duas leituras, e diferenca sobre
binario de ponto flutuante acumula erro que ninguem consegue ver depois de gravado."*
**Como evitar:** EXP em décimos de milésimo (`:326`), adena em unidades, `Fraction` só na divisão
final da taxa, `float` só na formatação.
**Sinal de alerta:** um `str(valor)` no `campos_da_...` que produza `.0` ou notação científica.

### Pitfall 2: copiar a dedup do `mercado_registro`
**O que dá errado:** a 1 Hz, com o personagem parado, a chave se repete e o arquivo grava uma
linha a cada mudança em vez de uma por tick. **O denominador da taxa some.**
**Por quê:** `mercado_registro.py:161-163` desenhou a chave **para** deduplicar sobre o tempo.
**Como evitar:** `renda_registro` **sem** `chaves`, **sem** `chave_da_observacao`, **sem**
`_montar_o_indice`. O `carregar` do arranque só confere os dois portões e para.
**Sinal de alerta:** um `set` no `__init__` do registro novo.

### Pitfall 3: chamar `ler_a_renda` e perder a adena quando o nível recusa
**O que dá errado:** o nível é o campo mais frágil (Fase 1 mediu 4 leituras erradas em 18 no
nível, `01-MEDICOES-DE-CAMPO.md:402`). `ler_a_renda` devolve a **primeira** recusa em
`ORDEM_DOS_CAMPOS`, e `nivel` é o **primeiro** (`renda_leitura.py:83`). Uma amostra com EXP e
adena perfeitos vira `RecusaDaRenda` do nível e some.
**Como evitar:** consumir `ler_os_tres_campos` → `CamposDaRenda`, que preserva os três
(`:1334-1335`), e gravar campo a campo com a recusa nomeada ao lado — que é o que o
`02-CONTEXT.md:90-93` exige de qualquer forma.
**Sinal de alerta:** `ler_a_renda` no import do módulo novo.

### Pitfall 4: assumir que o carimbo só cresce
**O que dá errado:** `intervalo = atual.carimbo - anterior.carimbo` fica negativo, entra no
denominador, e a taxa vira negativa ou infinita — **sem levantar**.
**Por quê:** `relogio.py:147-151` e `:121-122`, mais os dois testes que **exigem** o
comportamento (`tests/test_relogio.py:120-134`, `:90-101`).
**Como evitar:** `if atual.carimbo < anterior.carimbo:` → descontinuidade nomeada, amostra é
âncora, ganho não computado. É o mesmo tratamento do level up com nível recusado.
**Sinal de alerta:** um `abs()` sobre um intervalo, ou um `max(0, ...)` que engole o sinal.

### Pitfall 5: um teste que fica verde por vacuidade
**O que dá errado:** uma janela móvel que nunca inclui nada passa em "a taxa não mente".
**Por quê:** a casa já resolveu isso três vezes — controle positivo em
`tests/test_renda_par.py:576-589`, em `tests/test_calibracao_renda.py:234-264`, e a sonda de
truncagem em `dashboard_dados.py:415-418` (*"um controle positivo ... acusou 3.252 de 4.079"*).
**Como evitar:** todo portão desta fase nasce com o seu controle positivo, e o controle usa **a
mesma função** do portão.

### Pitfall 6: uma constante de janela ou de limiar no fonte
**O que dá errado:** `JANELA_PADRAO = 600` no módulo puro.
**Por quê:** `CLAUDE.md` — *"Nada de constante mágica no fonte"* — e
`renda_leitura.py:1562-1565`, que **recusou dar default a `fator_de_salto`** por essa razão exata.
**Como evitar:** janela, limiar de lacuna e `fator_de_salto` vêm do `config.toml`, somente-nomeados
e sem default. `02-CONTEXT.md:107` já os marcou como discricionários **e calibráveis**.

---

## Code Examples (esqueletos, não implementação)

### Portão de contrato copiado, com o texto trocado
```python
# renda_registro.py — o corpo é de mercado_registro.py:459-477, sem uma linha de lógica mudada.
def conferir_o_terminador(bruto: str, arquivo: Path) -> None:
    if bruto.endswith("\n"):
        return
    cauda = bruto[bruto.rfind("\n") + 1 :]
    mensagem = ("REGISTRO DE RENDA DESLIGADO — ... A cauda crua e %r, e ela esta INTACTA no "
                "disco: nenhum byte foi removido, reparado ou reescrito. ...")
    log.error(mensagem, arquivo, cauda)
    raise ContratoDoArquivoDeRendaQuebrado(mensagem % (arquivo, cauda))
```
Fonte da lógica: `l2scanner/mercado_registro.py:459-477`.

### O append, literal
```python
# renda_registro.py — corpo de mercado_registro.py:852-874.
try:
    with self.arquivo.open("a", encoding="utf-8", newline="") as destino:
        csv.writer(destino, delimiter=SEPARADOR).writerow(campos)
        destino.flush()
except OSError as erro:
    self.ligado = False        # DEFINITIVO PARA A SESSAO, sem retry (mercado_registro.py:857-861)
    log.error(...)
    return False
```

### O corte de cauda, 6 linhas
```python
# renda_registro.py — corpo de dashboard_dados.py:444-451.
corte = bruto.rfind("\n")
if corte < 0:
    return LeituraDeRendaAoVivo(cauda_incompleta=True)
completo = bruto[: corte + 1]
cauda = bruto[corte + 1 :]
```

### A forma do resultado da taxa
```python
# renda_conta.py — forma de mercado_analise.py:414-425 + :226-249.
@dataclass(frozen=True)
class TaxaDaRenda:
    evidencia: Evidencia            # n = amostras que entraram; piso = do config
    por_hora: Fraction | None       # None quando não há número a dizer
    motivo_da_ausencia: str | None  # e o motivo diz POR QUE
    janela_farmada: float           # o denominador REAL, sem as lacunas
    lacunas_excluidas: int          # contadas à parte (02-CONTEXT.md:34-38)
    ate: float                      # a recência, SEPARADA do valor (mercado_analise.py:389-391)
```

---

## State of the Art (dentro deste repositório)

| Antes | Agora | Quando mudou | O que significa para a Fase 2 |
|---|---|---|---|
| `from .config import RAIZ` | `from .raiz import RAIZ` | `raiz.py:17-42` | `renda_registro.py` importa de `raiz.py`, nunca de `config.py` — senão arrasta `cv2` |
| Adena por OCR | Adena por glifo | LEIT-09 / `01-04-SUMMARY.md:17` | irrelevante para a conta; relevante para saber que `ValorDaAdena` tem `glifos` e não `escalas` |
| Cruzamento entre escalas como defesa principal | **Regras de par da Fase 2** como defesa principal | LEIT-11 / `REQUIREMENTS.md:163-165` | **a Fase 2 herda o papel de defesa principal contra número plausível e errado** |
| Um piso de brilho único | Piso por região por personagem | LEIT-08 / M-E | a Fase 2 não toca em piso; a banda que anda com o cenário é LEIT-10, dona: Fase 3 |

**Depreciado / não use:**
- `ler_a_renda` para esta fase — ver Pitfall 3.
- `Sessao` de `sessao.py` — ver §5.
- Importar qualquer coisa de `dashboard_dados.py` — ver §3, custo de import.

---

## Project Constraints (from CLAUDE.md)

| Diretiva | Onde ela morde nesta fase |
|---|---|
| Detecção 100% passiva; nunca input ao jogo | Nenhum toque — a fase não captura nada |
| `pyautogui` **fora da árvore de dependências** | Nada a acrescentar; a fase é stdlib pura |
| `config.toml` (humano, `tomllib`) × `calibration.json` (máquina, `json`) | Janela, limiar de lacuna e `fator_de_salto` → **`config.toml`** (limiares que o usuário ajusta). Ponte de XP → **`calibration.json`** (o calibrador escreve). O `02-CONTEXT.md:68` acerta na ponte; **é o plano que decide onde ficam os outros três** |
| `pydantic` 2.13.4 para validação de config | As chaves novas de `config.toml` entram no modelo, e um valor negativo falha no arranque |
| **Nada de constante mágica no fonte** | Ver Pitfall 6 |
| Inteiro escalado em vez de `float` | Ver Pitfall 1 |
| `stdlib logging` com `RotatingFileHandler` | O `log.warning` por linha ruim segue o molde de `mercado_registro.py:576-583` (número da linha, motivo, conteúdo cru em `%r`) |
| GSD: nada de edição direta fora de comando GSD | Esta pesquisa não edita fonte |

---

## Environment Availability

Nenhuma dependência externa nova. A fase é `dataclasses`, `csv`, `json`, `pathlib`, `fractions`,
`logging` — tudo stdlib.

| Dependência | Necessária para | Disponível | Observação |
|---|---|---|---|
| `pytest` | a suite | ✓, mas **não no `.venv`** | `01-01-SUMMARY.md:36` e `tests/test_medir_a_renda.py:22-26`: *"o `.venv` de producao NAO tem pytest; o Python global NAO tem as bindings de OCR"*. Rodar com `PYTHONPATH=".;<repo>/.venv/Lib/site-packages"` |
| OCR / WinRT | — | não é usada | a fase não lê pixel; os testes montam `LeituraDaRenda` a mão |
| Jogo aberto | — | não é necessário | é o ponto do `<domain>` |

---

## Security Domain

Fase local, sem rede, sem entrada de usuário remoto. As categorias ASVS relevantes:

| ASVS | Aplica | Controle padrão da casa |
|---|---|---|
| V5 Input Validation | **sim** | O `calibration.json` e o `.renda/*.csv` são **entrada não confiável** — o usuário os edita a mão e importa no Sheets. Validação no arranque (`calibracao.py:1615-1628`) e portão de contrato no leitor (`mercado_registro.py:412-513`) |
| V12 Files | **sim** | O caminho vem **sempre de `RAIZ`, nunca de entrada do usuário** — *"um caminho vindo de fora seria uma travessia de diretorio de graca"* (`mercado_catalogo.py:678-680`). `.renda/` segue igual |
| V2/V3/V4 Auth/Sessão/Acesso | não | processo local, monousuário |
| V6 Cryptography | não | nada cifrado nesta fase |
| V7 Error handling | **sim** | `except OSError` e só (`mercado_registro.py:843-851`); nunca `except Exception`, que *"esconderia um `AttributeError` de refactor como se fosse disco cheio"* |

| Padrão de ameaça | STRIDE | Mitigação já escrita |
|---|---|---|
| CSV editado a mão com cabeçalho trocado → append em colunas erradas | Tampering | `conferir_o_cabecalho` desliga a feature alto, sem migrar (`mercado_registro.py:481-492`) |
| Escrita interrompida → linha parseável e errada | Tampering | `conferir_o_terminador`, 5 de 5 (`:415-423`) |
| `calibration.json` truncado por Ctrl-C → scanner de party inteiro morre | DoS | `.tmp` + `os.replace` (`calibracao.py:916-939`) |
| Disco cheio no meio do farm derruba os alertas de morte | DoS | degradar a FEATURE e nunca o PRODUTO (`mercado_registro.py:802-805`) |

---

## Assumptions Log

| # | Afirmação | Seção | Risco se errada |
|---|---|---|---|
| A1 | Os números de campo do `02-CONTEXT.md:145-153` (466 mil/h, 226 mil/h, 2,41 M XP/h, ~104 abates/min, recusa 21%/79%/0% em 14 amostras) vieram do script de bancada no scratchpad e **não estão em nenhum artefato versionado** | Contradições C-6 | Testes construídos sobre números que ninguém pode reproduzir a partir de um clone |
| A2 | O `dashboard` **ainda não** aponta para `.renda/` e não vai apontar durante esta fase | §3 | Se o outro agente já tiver começado, o esquema deixa de ser reversível |
| A3 | `nyquist_validation: false` em `.planning/config.json:31` → a seção Validation Architecture é omitida | — | Nenhum — verificado no arquivo |
| A4 | `Fraction` é o tipo certo para a divisão da taxa (não medido nesta fase; inferido do precedente de `mercado_analise.py:178` e `dashboard_dados.py:613`) | §7 | Baixo — se `Fraction` pesar, a alternativa é inteiro escalado, mesma família |

---

## O que o plano tem que decidir, e o que já está decidido

### (a) Fatos estabelecidos por leitura de código — não se discutem mais

1. **As quatro regras de par existem, são puras, e não têm chamador de produção.** Assinaturas em
   `renda_leitura.py:1479`, `:1512`, `:1538-1540`, `:1584-1586`. `conferir_o_par` devolve **tupla
   vazia** para par coerente (`:1595`).
2. **`o_exp_andou_para_tras` já se abstém no level up** (`:1498-1499`). REND-03 não precisa de
   guarda extra contra falso positivo — precisa da **conta**, que não existe.
3. **`a_adena_saltou_ordem_de_grandeza` não conflita com REND-04.** A docstring diz, com essas
   letras, que *"a Fase 2 ja trata renda negativa"* (`:1544`). Ela é bidirecional, por
   multiplicação inteira (`:1572`), e se abstém no zero (`:1569-1570`).
4. **`fator_de_salto` não tem default, de propósito, e vem do `config.toml`** (`:1562-1565`).
5. **`ler_a_renda` esconde os outros dois campos quando o nível recusa** (`:1427-1430`, `ORDEM_DOS_
   CAMPOS` com `nivel` primeiro em `:83`). A fase consome `ler_os_tres_campos`.
6. **O par de campo real do level up está congelado**: `nivel=66, exp=685_632, adena=10_673_628` →
   `nivel=67, exp=80_012, adena=13_160_684` (`tests/test_renda_par.py:99-100`). O ganho correto,
   em décimos: `(1_000_000 − 685_632) + 80_012 = 394_380` (= 39,438 pp).
7. **`conferir_o_terminador` é copiável literal**; `conferir_o_cabecalho` **não é** — fecha sobre o
   global `COLUNAS` (`mercado_registro.py:495`).
8. **A dedup do `.mercado/` é ativamente errada aqui** (`:161-163` contra o denominador da taxa).
9. **`.mercado/` é um arquivo só, sem rotação** (`:610`); `.loot/` são marcadores, não CSV
   (`loot.py:181-190`).
10. **`observacoes_ao_vivo` chama o parser do mercado por nome** (`dashboard_dados.py:454`), e
    `dashboard_dados` arrasta `cv2` por `mercado_console` (`:71-77` + `raiz.py:53-54`).
11. **Nenhum módulo calcula taxa por unidade de tempo.** A forma a copiar é
    `Evidencia`/`Tendencia`/`recencia_do_preco` (`mercado_analise.py:226-249`, `:414-425`,
    `:375-398`), não a aritmética.
12. **A terceira chave do `calibration.json` custa 5 lugares**, e o quinto é
    `VALORES_ESPECIAIS` em `tests/test_calibracao_renda.py:134-151`. O portão estrutural
    (`:216-232`) **pega o esquecimento nas duas direções**, com controle positivo (`:234-264`).
    `VERSAO_DO_ESQUEMA` fica em 2 (`calibracao.py:23`).
13. **O idioma do relógio falso existe e está pronto:** `Maquina.pular_parede()`
    (`tests/test_relogio.py:45-47`), `RelogioParado` (`test_janela_no_relogio.py:115-126`), e o
    construtor de `LeituraDaRenda` com `carimbo: float = 0.0` (`test_renda_par.py:85-93`).

### (b) Escolhas genuinamente abertas — o plano decide

1. **Um arquivo ou muitos.** Ver C-5. Precedente real = **um arquivo só com coluna `personagem`**.
   `.renda/<Personagem>/<data>.csv` é forma nova e precisa do argumento escrito, incluindo o que o
   leitor faz na virada da meia-noite dentro de uma janela de 10 minutos.
2. **Onde moram os três limiares.** Janela móvel, limiar de lacuna e `fator_de_salto`: `config.toml`
   (humano, com comentário) ou `calibration.json` (máquina)? O `CLAUDE.md` sugere `config.toml`
   para o que o usuário ajusta; a Fase 1 já mandou `fator_de_salto` para lá por escrito (`:1565`).
3. **Fronteira de tipo do tempo.** `float` epoch na aritmética + `datetime.fromtimestamp` só no
   disco, ou `datetime` em toda a fase? A Fase 1 escolheu `float` (`:1319`); o dialeto escreve
   `isoformat()` (`mercado_registro.py:191`). Alguém tem que ceder, e o plano diz quem.
4. **O que é "a sessão".** Processo, ou lacuna longa? (`02-CONTEXT.md:108`.) Decide se
   `Contagem` nasce no arranque ou se o leitor a reconstrói do arquivo.
5. **Colunas finais.** As sete previstas (`02-CONTEXT.md:88-89`) não têm coluna para o campo
   `escalas`/`glifos` (a guarda que sustentou cada leitura), nem para a descontinuidade do
   relógio. Vale acrescentar? O esquema se decide **uma vez** (`ROADMAP.md:36-37`).
6. **Os pisos de `Evidencia`.** Quantas amostras para uma taxa deixar de ser ruído? É escolha, não
   medição — e a casa exige que isso vá escrito (`dashboard_dados.py:265-267`).
7. **Como a descontinuidade viaja.** `RecusaDaRenda` reusada com motivo novo, ou tipo próprio? Ela
   não é recusa de *leitura*, é recusa de *par* — e `conferir_o_par` já devolve `RecusaDaRenda`
   para as três irmãs (`:1601-1607`), o que argumenta pelo reuso.

### (c) O que CONTRADIZ o `02-CONTEXT.md` ou o `ROADMAP.md` — a parte que vale o dobro

> **C-1 — A Fase 2 derruba um teste verde da Fase 1, e ninguém escreveu isso.**
> `tests/test_renda_par.py:591-623` varre `l2scanner/*.py` com `Path.glob` e falha se **qualquer**
> módulo chamar `o_exp_andou_para_tras`, `o_nivel_andou_para_tras`,
> `a_adena_saltou_ordem_de_grandeza` ou `conferir_o_par`. O `02-CONTEXT.md:116-119` diz que as
> regras estão *"escritas, puras, e ainda sem chamador por desenho"* e que *"esta fase é o
> chamador"* — sem notar que existe um portão executável prendendo a ausência. **A primeira
> chamada da Fase 2 põe a suite em vermelho.** O portão tem de ser **invertido** (não apagado) na
> Tarefa 1, e a inversão tem de preservar a metade que continua valendo: `renda_leitura.py`
> permanece sem chamador **dentro dele mesmo**, e o novo chamador é **um só, nomeado**.

> **C-2 — "O `dashboard` acrescenta uma lista de colunas, não um parser" é FALSO, e o roadmap
> repete a frase duas vezes.**
> `ROADMAP.md:274` e `REQUIREMENTS.md:284` afirmam isso como a "correção medida" do REG-03. Mas:
> `observacoes_ao_vivo` chama `mercado_registro.observacoes_do_arquivo` **por nome**
> (`dashboard_dados.py:454`), sem ponto de injeção; `conferir_o_cabecalho` compara contra o global
> `COLUNAS` (`mercado_registro.py:495`) e **levanta na primeira linha** de um CSV de renda;
> `chave_dos_campos`, `ObservacaoLida` e `residuo_dos_campos` são mercado puro (`:570-601`); e
> acima disso `payload` é `ModeloDeMercado` + `CHAVE_DA_SERIE_DA_ADENA` + cinco `ESTADOS` + câmbio
> (`dashboard_dados.py:955-1010`). **O `dashboard` precisará de um segundo parser.** A correção do
> REG-03 corrigiu a promessa uma vez e parou uma camada acima do fundo. O que sobrevive é o que
> realmente importa e continua verdadeiro: **nenhuma decisão de formato nova, nenhuma armadilha
> nova, nenhuma medição refeita** — e isso é o suficiente para o requisito. Mas a frase "uma lista
> de colunas" tem de cair, e cair **escrita**, com estas linhas ao lado.

> **C-3 — Copiar "o dialeto do `mercado_registro`" inclui uma peça que destrói o produto.**
> O `02-CONTEXT.md:84-86` manda copiar o dialeto sem excluir a dedup. `chave_da_observacao` exclui
> o carimbo **de propósito**, para que o arquivo *não* cresça uma linha por segundo
> (`mercado_registro.py:161-163`). No `.renda/` uma linha por tick **é** o produto — é o
> denominador. Copiar a dedup apaga toda amostra em que os três campos não mudaram. **O plano tem
> de dizer, no fonte, que a dedup fica de fora e por quê.**

> **C-4 — `.renda/` não está no `.gitignore`.**
> `.gitignore:30,33,38` tem `.agenda/`, `.loot/`, `.mercado/`. Não tem `.renda/`. Uma linha, e
> nenhum documento a menciona.

> **C-5 — "Um arquivo por personagem por dia, na forma que o `.mercado/` e o `.loot/` já usam"
> (`02-CONTEXT.md:87`) descreve uma forma que nenhum dos dois tem.**
> `.mercado/` é *"UM ARQUIVO SO, QUE CRESCE, SEM ROTACAO (D-09)"* (`mercado_registro.py:610`).
> `.loot/` é uma pasta de marcadores vazios (`loot.py:181-190`), não CSV. **Arquivo por dia não
> existe nesta árvore.** A frase dá cobertura de precedente a uma decisão que na verdade é nova, e
> decisões novas de esquema com consumidor externo se tomam **uma vez** (`ROADMAP.md:36-37`).

> **C-6 — Os números de campo que a Fase 2 vai usar como caso de teste não são reproduzíveis a
> partir de um clone.**
> O `02-CONTEXT.md:145-153` cita 466 mil adena/h, 226 mil/h, 2,41 M XP/h, ~104 abates/min e
> "recusa: adena 21%, nível 79%, EXP 0% (14 amostras)". **Nenhum desses números aparece em
> `01-MEDICOES-DE-CAMPO.md`, `01-MEDICOES.md` ou em qualquer SUMMARY.** O que está versionado é:
> - `01-MEDICOES-DE-CAMPO.md:299-301` — **≈ 232 mil adena/h** em ~8,5 h (não 226), com o
>   denominador (1.974.095 de delta) escrito ao lado;
> - `01-MEDICOES-DE-CAMPO.md:399-403` — a tabela de erro é de **aceitas e ERRADAS**, não de
>   recusadas: adena **5/10 (50%)**, nível 4/18 (22,2%), EXP 3/27 (11,1%), sobre 124 unidades por
>   campo.
>
> São grandezas **diferentes** com números parecidos, e a confusão é perigosa nas duas direções: o
> `02-CONTEXT.md` cita "adena 21%" como taxa de *recusa* (baixa, tranquilizadora) onde o versionado
> mede **50% das adenas aceitas erradas** (alto, alarmante). **Isso muda o desenho da fase**: se
> metade das leituras de adena que passam pelos filtros da Fase 1 está errada, as regras de par não
> são "última defesa" — são a defesa, e o LEIT-11 (`REQUIREMENTS.md:163-165`) já dizia exatamente
> isso: *"A defesa principal são as regras de par da Fase 2."*
>
> **O que fazer:** o plano usa como fixtura **apenas** número com procedência versionada. Se os
> números do scratchpad forem os certos, eles têm de ir para um `02-MEDICOES.md` **com o
> denominador junto**, antes de virarem asserção — foi exatamente a disciplina que fez a Fase 1
> refutar o próprio plano cinco vezes.

> **C-7 — REG-02 não é resolvido pelo mecanismo que o `02-CONTEXT.md` implica.**
> O `02-CONTEXT.md:84-86` manda copiar o dialeto inteiro, e o critério 4 do `ROADMAP.md:255-257`
> pede que reiniciar não invente nem apague renda. No `.mercado/` isso vem do **índice em memória
> reconstruído do CSV** (`mercado_registro.py:616-618`) — que é justamente a peça que C-3 manda
> **não** copiar. A garantia real vem de outro lugar: **a primeira amostra depois do arranque não
> tem `anterior`, logo é âncora e não delta**. É regra da conta, não do registro. O `ROADMAP.md:39-41`
> já tinha visto isso (*"REG-02 é uma regra de taxa vestida de persistência"*); o `02-CONTEXT.md`
> não repete, e um plano que só leia o CONTEXT vai procurar a garantia no lugar errado.

> **C-8 — A ponte de XP entra no `calibration.json` mas a fase que a mede está deferida, e o
> critério 1 do painel depende dela.**
> `02-CONTEXT.md:79-80` defere a ferramenta de medição para a Fase 3. `02-CONTEXT.md:70-72` manda
> declarar o XP absoluto **INDISPONÍVEL** sem constante para o nível atual. Consequência aritmética:
> ao fim desta fase, **`renda_ponte_de_xp` estará vazia** (o único valor medido — 383.124 no nível
> 67 da Faerlina, `REQUIREMENTS.md:185` — está em prosa, não em `calibration.json`), então o caminho
> "XP absoluto disponível" **não terá nenhum dado real para exercitar**. Não é impedimento — é um
> aviso de que REND-08 fecha nesta fase apenas na metade "declaro indisponível e digo por quê", e o
> plano deve dizer isso em voz alta em vez de o verificador descobrir. Uma saída barata: o plano
> semeia a entrada do nível 67 da Faerlina **a mão**, com a procedência que o `02-CONTEXT.md:76-78`
> exige (6 minutos, 240 linhas de chat, 622 abates), e o caminho fica exercitável de ponta a ponta.

---

## Sources

### Primária (HIGH) — código lido nesta sessão, com linha
- `l2scanner/renda_leitura.py` — 1.608 linhas, integral
- `l2scanner/mercado_registro.py` — `:90-200`, `:380-620`, `:620-881`
- `l2scanner/dashboard_dados.py` — `:55-100`, `:260-480`, `:591-672`, `:918-1010`
- `l2scanner/relogio.py` — integral
- `l2scanner/loot.py` — `:1-30`, `:176-230`
- `l2scanner/sessao.py` — `:1-80`, `:189-300`
- `l2scanner/calibracao.py` — `:660-760`, `:831-945`, `:1382-1440`, `:1615-1645`
- `l2scanner/mercado_analise.py` — `:145-300`, `:375-500`
- `l2scanner/mercado_catalogo.py` — `:675-700`, `:840-885`
- `l2scanner/mercado_modo.py` — `:130-260`
- `l2scanner/mercado_console.py` — `:660-700`
- `l2scanner/raiz.py` — `:1-90`
- `l2scanner/renda_modo.py` — `:340-400`
- `tests/test_renda_par.py` — `:51-100`, `:534-623`
- `tests/test_calibracao_renda.py` — `:100-300`
- `tests/test_calibrar_renda_nao_apaga_nada.py` — `:440-540`
- `tests/test_relogio.py` — `:1-140`
- `tests/test_janela_no_relogio.py` — `:100-150`
- `tests/test_agenda.py` — `:1195-1240`
- `tests/conftest.py` — `:1-40`
- `.gitignore` — `:27-40`
- `.planning/config.json`

### Primária — documentos de planejamento
- `.planning/workstreams/renda/ROADMAP.md` — `:11-26` (tabela do que não se reconstrói), `:207-301`
- `.planning/workstreams/renda/REQUIREMENTS.md` — `:135-300`
- `.planning/workstreams/renda/phases/02-.../02-CONTEXT.md` — integral
- `.../01-MEDICOES-DE-CAMPO.md` — integral (448 linhas)
- `.../01-01-SUMMARY.md`, `.../01-04-SUMMARY.md`
- `.claude/CLAUDE.md`

### Nenhuma fonte web consultada
A pilha está travada e nada desta fase mora fora da árvore.

---

## Metadata

**Confiança por área:**
- Superfície de `renda_leitura` — HIGH — arquivo lido inteiro, assinaturas e constantes citadas verbatim
- Dialeto do registro — HIGH — corpo do `registrar` e dos dois portões lidos linha a linha
- Refutação do "uma lista de colunas" — HIGH — a cadeia de chamada foi seguida até o `COLUNAS` global
- Relógio — HIGH — módulo e testes lidos integralmente; os dois buracos têm teste que os **exige**
- Reuso de `sessao.py` — HIGH — `__init__` e imports lidos; o veredito é "outro assunto"
- Receita da terceira chave — HIGH — os cinco lugares verificados, incluindo o `VALORES_ESPECIAIS`
- Ausência de precedente de taxa — HIGH — varredura por 6 padrões distintos
- Convenções de teste de tempo — HIGH — quatro idiomas, todos citados verbatim
- Proveniência dos números de campo do CONTEXT — **MEDIUM** — a ausência foi verificada por grep;
  a origem (scratchpad) é inferida do próprio `02-CONTEXT.md:159-161`

**Data:** 2026-09-02
**Válido até:** enquanto `renda_leitura.py`, `mercado_registro.py` e `dashboard_dados.py` não forem
editados. As linhas citadas são o contrato desta pesquisa.
