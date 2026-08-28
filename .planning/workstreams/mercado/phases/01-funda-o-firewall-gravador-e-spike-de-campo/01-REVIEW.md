---
phase: 01-funda-o-firewall-gravador-e-spike-de-campo
reviewed: 2026-08-28T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - l2scanner/calibrar_mercado.py
  - l2scanner/calibrar.py
  - l2scanner/mercado_visao.py
  - l2scanner/sessao.py
  - l2scanner/visao.py
  - tools/conferir_spike_respostas.py
  - tools/diagnosticar_selecao.py
  - calibrar-mercado.bat
findings:
  critical: 5
  warning: 13
  info: 6
  total: 24
status: fixed
---

# Phase 01: Code Review Report (incremental — wave 2)

**Reviewed:** 2026-08-28
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Nota sobre a revisao anterior

Esta revisao SUBSTITUI a de 2026-08-27, que cobria `gravador.py`, `__main__.py`,
`test_gravador_honesto.py`, `test_firewall_escopo.py` e a primeira versao de
`mercado_visao.py`/`calibracao.py`. Os 2 BLOCKERs e 8 WARNINGs de la foram
corrigidos. Os dois que caem dentro do escopo de arquivos desta rodada foram
conferidos no codigo de hoje:

- **WR-04 (molde transposto)** — `molde_de_hex` agora tem o guard de dimensao
  nao-positiva e o parametro `forma_esperada` (`mercado_visao.py:227-278`). O
  guard existe; **nenhum chamador de producao o usa** — ver WR-01 abaixo.
- **WR-07 (campos de mercado sem validacao)** — `_conferir_as_chaves_de_mercado`
  (`calibracao.py:519-632`) confere tipo e faixa de todas as chaves. Fechado.

Suite: `1457 passed, 2 skipped`. Verde nao e evidencia de correcao — cinco dos
achados abaixo estao em caminhos que a suite nao exercita (o `calibrar()`
ponta-a-ponta, o navegador de frames, e o portao do spike, que nao tem arquivo
de teste nenhum).

## Summary

O firewall do incidente 27x **aguenta**, e essa e a parte boa: `visao.py` so
recebeu o campo `mercado_aberto_aparente` (o diff e aditivo puro — nada em
`barra_propria_legivel`, `_moldura_da_barra_propria` ou
`_bordas_da_barra_intactas` foi tocado), `sessao.tick` calcula o sinal DEPOIS de
`rastreador.observar` ja ter devolvido a lista de eventos, e o unico consumidor
do campo no projeto inteiro e uma linha de console. A garantia e estrutural, e
nao uma regra a lembrar.

O problema esta em toda a **superficie de calibracao**, e ele e do tipo caro:

1. **A janela onde o usuario desenha os retangulos encolheu 5x, e isso e
   medido.** `namedWindow(..., WINDOW_NORMAL)` — o workaround de posicionamento
   que a propria medicao de campo declarou inocente do sintoma, e que foi
   mantido — mostra um frame de 1600x1295 dentro de **304x281 px** nesta
   maquina. Antes da mudanca, `selectROI` sozinho abria em `WINDOW_AUTOSIZE`, a
   1600x1295. Isso atinge a calibracao de party COMPARTILHADA, que funcionava.
2. **A ferramenta de mercado promete uma imagem de conferencia que pode nao
   existir** — o retorno de `_gravar_conferencia` e descartado e o `.bat` cita o
   nome do arquivo na mao. E o defeito FUND-01, verbatim, do outro lado da
   parede.
3. **Duas afirmacoes sem lastro sao impressas e gravadas:** uma matriz de
   confusao "APROVADA" com zero pares comparados, e o limiar 0.5 que sai dela
   direto para o `calibration.json`.
4. **O portao do spike aceita `NAO VERIFICADO` como selo VERIFICADO** — medido,
   nao suposto. O arquivo que existe para tornar evidencia fabricada impossivel
   promove uma resposta explicitamente negativa a positiva.

Cinco BLOCKERs, treze WARNINGs, seis INFOs.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `WINDOW_NORMAL` encolhe a area de desenho de 1600x1295 para 304x281 — medido — e isso regride a calibracao de party

**File:** `l2scanner/calibrar.py:424-429` (o site compartilhado),
`l2scanner/calibrar_mercado.py:338-357` (o navegador de frames)

**Issue:** `_selecionar_regiao` cria a janela com `cv2.WINDOW_NORMAL` antes de
chamar `selectROI` no MESMO titulo. Uma janela `WINDOW_NORMAL` **nao se
redimensiona para a imagem** — ela nasce no tamanho padrao do Win32 e a imagem e
espremida dentro dele. `selectROI` chama `namedWindow` internamente, e
`namedWindow` sobre uma janela existente **nao faz nada** (comportamento
documentado do OpenCV), entao a janela pequena e a que o usuario recebe.

Medido nesta maquina, OpenCV 4.14.0, com uma imagem de 1600x1295:

```
AUTOSIZE  : (268, 291, 1600, 1295)     <- o que o codigo fazia ANTES
NORMAL    : (164, 187,  304,  281)     <- o que o codigo faz HOJE
NORMAL x2 : (190, 213,  304,  281)     <- um segundo imshow nao corrige
```

`getWindowImageRect` = 304x281 para uma imagem de 1600x1295: **fator 5,26x na
horizontal e 4,61x na vertical.** Cada pixel de mouse do usuario vale ~5,3 px da
visualizacao — que ja e uma visualizacao reescalada — e depois mais 1/`escala`
para voltar ao original. Numa janela de 1720 px, um pixel de mouse vale ~5,7 px
gravados no `calibration.json`.

Isso ataca exatamente o que a docstring da propria funcao chama de "o defeito
mais caro que uma ferramenta de calibracao pode ter":

> "Errar essa divisao produz um retangulo plausivel na posicao errada"

Consequencias concretas, nas duas metades:

- **Party (COMPARTILHADO, funcionava antes desta fase):** `calibrar_selecionando`
  passou a herdar a janela de 304 px. A party window, a ancora e o passo entre
  membros — tudo que a deteccao de morte usa — saem de um arrasto com 5,7 px de
  granularidade. Antes desta mudanca esse arrasto era 1:1.
- **Mercado:** as ancoras sao recortes de 100x28 e 60x60. Com ±6 px de erro em
  cada borda, o molde de 60x60 do `botao_fechar` sai com ate 20% da area errada,
  e `dx`/`dy` saem deslocados — e `conferir_painel` compara em UMA posicao so, de
  proposito. Um `dx` errado por 6 px derruba o casamento de seguimento sem uma
  linha de erro.
- **Navegador de frames (`calibrar_mercado.py:338`):** o mesmo `WINDOW_NORMAL`.
  Um frame de 1720x1392 reduzido para 1400 e depois espremido em 304x281 e
  ~18% do tamanho real. A funcao inteira existe para o usuario **ver** se ha
  tooltip por cima do painel — a propria docstring diz que calibrar sobre frame
  ocluido "e a mesma familia do incidente 27x". A 18% ninguem ve uma tooltip.

O bloco de comentario diz que `namedWindow`+`moveWindow` existe para a janela
nascer onde o usuario a encontre. O objetivo e legitimo; o flag e que esta
errado — `moveWindow` funciona igual sobre `WINDOW_AUTOSIZE`.

**Fix:** manter o posicionamento, devolver o tamanho.

```python
# WINDOW_AUTOSIZE: `moveWindow` posiciona igual, e a imagem aparece 1:1.
# Com WINDOW_NORMAL a janela nasce em 304x281 (medido, cv2 4.14) e o
# usuario desenha num quinto da resolucao — o retangulo sai plausivel e
# no lugar errado, que e o defeito que esta funcao existe para evitar.
cv2.namedWindow(titulo, cv2.WINDOW_AUTOSIZE)
cv2.moveWindow(titulo, 40, 40)
```

Se por algum motivo `WINDOW_NORMAL` precisar ficar (monitor menor que o frame),
entao o tamanho tem de ser declarado explicitamente logo depois:

```python
cv2.resizeWindow(titulo, visao.shape[1], visao.shape[0])
```

Aplicar nos dois sites. E um teste estrutural barato fecha a porta: afirmar que
o modulo nao chama `namedWindow` com `WINDOW_NORMAL` sem um `resizeWindow` ao
lado.

---

### CR-02: A calibracao de mercado manda ABRIR uma imagem que pode nao existir — e o `.bat` cita o nome velho

**File:** `l2scanner/calibrar_mercado.py:588` e `613`, `calibrar-mercado.bat:60-69`

**Issue:** Linha 588:

```python
_gravar_conferencia(desenhar_conferencia(pixels, regioes))
```

O retorno e **descartado**. Linha 613, incondicional:

```python
print("\nABRA a imagem de conferencia e confira os retangulos.")
```

E o `.bat`, no caminho de sucesso (`errorlevel` 0), imprime uma terceira vez,
agora **com o nome do arquivo escrito na mao**:

```
ABRA a imagem calibracao-conferencia.png e confira se os
retangulos verdes caem onde voce espera
```

`_gravar_conferencia` devolve `None` quando nao conseguiu gravar em lugar
nenhum, e devolve um caminho **alternativo** (`calibracao-conferencia-HHMMSS.png`)
quando o destino padrao esta travado — o cenario que a docstring dela diz ser o
mais comum, porque a propria ferramenta manda o usuario abrir a imagem no
visualizador de fotos. Nos dois casos o usuario e mandado para
`calibracao-conferencia.png`, que ou nao existe, ou **e a imagem da calibracao
anterior**. Literalmente o defeito que o modulo diz ter matado, na sua propria
docstring de abertura:

> "o calibrador anunciava uma imagem que nao existia — o usuario conferia
> A IMAGEM VELHA e validando uma calibracao errada"

E `cal.salvar(arquivo)` (linha 605) ja rodou: a calibracao **foi gravada** e o
unico passo de conferencia foi substituido por uma promessa vazia.

`calibrar.py` trata isto certo nos dois consumidores dele
(`conferir_visualmente:571-575` e `_texto_final_do_solo:622-644`, com o teste
`test_texto_final_do_solo_so_manda_conferir_quando_ha_imagem`). O modulo novo
importou a funcao e deixou o tratamento para tras.

**Fix:** capturar o caminho, e so prometer o que existe.

```python
conferencia = _gravar_conferencia(desenhar_conferencia(pixels, regioes))
...
cal.salvar(arquivo)
...
if conferencia is None:
    print("\nA CONFERENCIA VISUAL NAO ACONTECEU: nenhuma imagem foi gravada.")
    print("Os retangulos acima estao no calibration.json e NINGUEM os olhou.")
    print("Feche o visualizador de fotos e rode de novo antes de confiar nisto.")
else:
    print(f"\nABRA {conferencia}")
    print("e confira se os retangulos verdes caem onde voce espera.")
```

E o `.bat` nao pode citar o nome: ele nao sabe qual foi. Trocar o bloco final
por "a mensagem acima diz qual imagem abrir". Um teste no molde do
`test_texto_final_do_solo_*` prende o comportamento.

---

### CR-03: Uma watchlist de 0 ou 1 item imprime "matriz APROVADA" sobre zero comparacoes — e grava limiar 0.5

**File:** `l2scanner/calibrar_mercado.py:171-178`, `125-131`, `601`

**Issue:** Com menos de dois moldes, `matriz_de_confusao` devolve
`pior_score=0.0` e `limiar_sugerido=(1.0 + 0.0) / 2`. Executado:

```
ZERO moldes: aprovado=True limiar=0.5
   Matriz de confusao APROVADA: o pior score entre dois itens diferentes e 0.0000. Limiar sugerido: 0.5000.
UM molde:    aprovado=True limiar=0.5
   Matriz de confusao APROVADA: o pior score entre dois itens diferentes e 0.0000. Limiar sugerido: 0.5000.
```

Duas mentiras numa frase so:

1. **"o pior score entre dois itens diferentes e 0.0000"** — nao houve par
   nenhum. Nenhum score foi calculado. A frase afirma uma medicao que nao
   aconteceu, e afirma o valor mais tranquilizador possivel. Com a watchlist
   vazia, ela sai depois do aviso "nenhum molde de nome foi cortado", o que
   torna a contradicao visivel na mesma tela.
2. **`limiar_sugerido = 0.5` vai para o disco** (linha 601,
   `cal.mercado_limiar_de_template`) apresentado como derivado da matriz. Um
   limiar de 0.5 para casamento de nome e permissivo a ponto de casar quase
   tudo — o proprio modulo mede o pior inter-classe tolerado em 0.85 e a margem
   em 0.075. `_conferir_as_chaves_de_mercado` aceita 0.5 sem reclamar (a faixa
   valida e `(0, 1]`), entao nada a jusante vai pegar isso: a Fase 2 herda um
   numero fabricado com aparencia de medido.

Este e o padrao que o `<threat_model>` da fase chama de afirmacao confiante sem
lastro, dentro da ferramenta que grava a calibracao.

**Fix:** nao aprovar o que nao foi medido, e nao gravar limiar sem matriz.

```python
if len(nomes) < 2:
    # NAO ha par para comparar. Aprovar e correto; afirmar um "pior score"
    # medido nao e, e um limiar derivado de zero comparacoes e um numero
    # inventado com cara de medido.
    return ResultadoDaConfusao(
        aprovado=True, pior_score=0.0, par_colidente=None, limiar_sugerido=None
    )
```

```python
def explicar(self) -> str:
    if self.aprovado and self.limiar_sugerido is None:
        return (
            f"Matriz de confusao NAO RODOU: {len(self.matriz)} pares para "
            f"comparar. Com menos de dois moldes nao ha o que confundir, e "
            f"nenhum limiar de template foi derivado."
        )
```

e na gravacao, so mexer no campo quando ha o que dizer:

```python
if resultado.limiar_sugerido is not None:
    cal.mercado_limiar_de_template = resultado.limiar_sugerido
```

---

### CR-04: Rodar de novo sem watchlist APAGA os moldes de nome ja calibrados, calado

**File:** `l2scanner/calibrar_mercado.py:555-562`, `597-601`

**Issue:** `cal.mercado_templates_de_nome` recebe uma lista construida a partir
de `moldes_de_nome`, **sem condicao**:

```python
cal.mercado_templates_de_nome = [
    {"nome": nome, "molde": molde_para_hex(molde)}
    for nome, molde in moldes_de_nome.items()
]
```

Com a watchlist vazia isso e `[]`, e `cal.salvar` regrava o arquivo inteiro. Os
moldes de uma calibracao anterior desaparecem. O caminho e trivial de alcancar:

- `ler_watchlist` devolve `[]` quando **o `config.toml` nao existe** (linha
  441-442) — por exemplo rodando de outro checkout ou de um worktree;
- ou quando o usuario comentou a watchlist para reajustar so uma ancora;
- ou quando ele escreveu `[mercado]` sem a chave `watchlist`.

O console diz apenas:

> "Sem watchlist no config.toml: nenhum molde de nome foi cortado.
>  **As ancoras e a grade acima ja ficam gravadas**"

O que afirma um comportamento aditivo que nao e o que acontece. A ferramenta se
descreve, no cabecalho do modulo, como "muta so os campos de mercado" — mutar
para vazio e destruir, e este e o unico caminho do projeto que apaga trabalho de
calibracao sem perguntar. O prejuizo e proporcional a watchlist: cada molde
custou um arrasto de mouse sobre um frame gravado.

**Fix:** so escrever o que foi cortado; preservar o que nao foi.

```python
if moldes_de_nome:
    cal.mercado_templates_de_nome = [...]
elif cal.mercado_templates_de_nome:
    # Sem watchlist NAO significa "apague os moldes que ja existiam": esta
    # ferramenta ACRESCENTA campos, e o usuario que roda so para reajustar
    # uma ancora nao esta pedindo para perder os recortes de nome.
    print(
        f"\nMantidos os {len(cal.mercado_templates_de_nome)} molde(s) de nome "
        f"da calibracao anterior — nenhum foi recortado nesta rodada."
    )
```

O mesmo raciocinio vale para `mercado_limiar_de_template` (ver CR-03).

---

### CR-05: O portao do spike conta `NAO VERIFICADO` como selo `VERIFICADO`

**File:** `tools/conferir_spike_respostas.py:160-173`

**Issue:** `Secao.selos` procura os selos por substring, na ordem de `SELOS`, que
comeca por `"VERIFICADO"`. Executado contra uma secao real:

```
texto:  "NAO VERIFICADO em campo -- nao deu tempo."
selos:  ['VERIFICADO']
```

Uma resposta que o usuario **rebaixou explicitamente** e contada como selo
POSITIVO. O efeito em cascata e todo na direcao errada:

- passa na conferencia 2 (exatamente um selo);
- entra em `SELO_POSITIVO`, entao a conferencia 3 exige um frame — e qualquer
  frame que exista serve;
- e a tabela final do relatorio **imprime `VERIFICADO`** ao lado do numero da
  secao, que e a saida que um leitor futuro vai usar como resumo.

A docstring do proprio metodo diz que isto e prevenido:

> "`NAO RESPONDIDO` e procurado antes e removido do texto, senao ... o
> `VERIFICADO` dentro de 'NAO VERIFICADO' seria [o problema]"

O codigo faz o oposto (`for selo in SELOS` = VERIFICADO primeiro), e mesmo a
ordem descrita nao resolveria: `"NAO RESPONDIDO"` nao contem `"VERIFICADO"`, e
remove-lo antes nao apaga o `"NAO VERIFICADO"` de outra frase. A protecao nunca
existiu; a docstring afirma que sim.

Num arquivo cujo proposito declarado e "que a mesma mentira nao volte pela porta
da analise", promover um selo negativo a positivo e o modo de falha exato que
ele existe para impedir — e o `<threat_model>` T-03-01 e literalmente isto.

**Fix:** casar o selo com fronteira, e recusar a negacao explicitamente.

```python
import re

# `(?<![A-Z])` impede que o `VERIFICADO` de "NAO VERIFICADO" conte como selo
# positivo: o usuario que rebaixa uma resposta escrevendo a negacao seria
# promovido de volta, e a tabela final imprimiria VERIFICADO para ele.
_NEGACAO = re.compile(r"\bNAO\s+(VERIFICADO|PARCIAL)\b")

@property
def selos(self) -> list[str]:
    achados: list[str] = []
    restante = _NEGACAO.sub("NAO RESPONDIDO", sem_acento(self.texto))
    for selo in ("NAO RESPONDIDO", "VERIFICADO", "PARCIAL"):
        n = restante.count(selo)
        achados.extend([selo] * n)
        restante = restante.replace(selo, "")
    return achados
```

(Rebaixar `NAO VERIFICADO` para `NAO RESPONDIDO` e a leitura conservadora, e e a
que o resto do modulo ja assume: falhar para o lado do selo mais fraco.) Um
arquivo `tests/test_conferir_spike_respostas.py` com este caso, o de dois selos
e o da legenda fora da contagem — ver WR-11.

---

## Warnings

### WR-01: O guard `forma_esperada` foi adicionado e NENHUM chamador de producao o usa

**File:** `l2scanner/mercado_visao.py:581`, `l2scanner/calibracao.py:462-474` e `614-631`

**Issue:** `molde_de_hex` ganhou `forma_esperada` (a correcao do WR-04 anterior)
e a docstring dele e enfatica: "**Passe sempre que tiver.**". Varredura do
projeto: o unico lugar que passa o argumento sao os testes
(`tests/test_mercado_ancora.py:259,264`). Em producao:

- `ancoras_de_calibracao:581` chama `molde_de_hex(molde)` — sem forma. E este e o
  caminho **usado de verdade** pelo `RastreioDoPainel`;
- `Calibracao.carregar` nem decodifica `mercado_molde_da_ancora`, so o repassa
  cru.

Pior, `calibracao.py:619-620` afirma o contrario num comentario:

> "o molde e conferido (`mercado_visao.molde_de_hex`, argumento
> `forma_esperada`)"

Nao e. O molde transposto — 100x28 declarado como 28x100 — continua carregando
sem erro, e `conferir_painel` devolve 0.0 para sempre: o mercado some sem uma
linha de log, que e verbatim o desfecho que o guard existe para impedir.

`AncoraDoPainel` nao guarda largura/altura separadas do molde, entao a forma
esperada precisa vir da calibracao. O caminho mais barato e gravar as dimensoes
ao lado de `dx`/`dy`:

**Fix:**

```python
# ancoras_para_calibracao
{"nome": a.nome, "dx": ..., "dy": ...,
 "altura": int(a.molde.shape[0]), "largura": int(a.molde.shape[1]),
 "molde": molde_para_hex(a.molde)}

# ancoras_de_calibracao
forma = None
if isinstance(bruto.get("altura"), int) and isinstance(bruto.get("largura"), int):
    forma = (bruto["altura"], bruto["largura"])
molde=molde_de_hex(molde, forma_esperada=forma)
```

E, no minimo, corrigir o comentario de `calibracao.py:619-620`, que hoje diz que
uma checagem acontece quando ela nao acontece.

---

### WR-02: O portao do spike resolve `recordings/../qualquer/coisa.png` e aceita um diretorio como evidencia

**File:** `tools/conferir_spike_respostas.py:118`, `242`, `291`

**Issue:** duas frouxidoes na resolucao de evidencia:

1. `CAMINHO_DE_FRAME = re.compile(r"recordings/[^\s)`]+\.png")` aceita `..` no
   meio. Confirmado nesta maquina: `(raiz / "recordings/../l2scanner/visao.py")`
   resolve `True`. Uma citacao `recordings/../tests/fixtures/x.png` satisfaz o
   portao inteiro sem tocar em gravacao nenhuma. O prefixo `recordings/` da a
   impressao de que o escopo esta contido; ele nao esta.
2. `.exists()` em vez de `.is_file()` (linhas 242 e 291). Um **diretorio**
   chamado `frame_000012.png` passa — e o modo de falha deterministico dos
   testes deste projeto e exatamente esse (ver o comentario em
   `__main__.py:1735`, onde `is_file` foi escolhido de proposito pelo mesmo
   motivo). Um arquivo de 0 byte tambem passa.

O cabecalho do modulo promete "RESOLVE cada caminho no sistema de arquivos". Um
caminho que sai da arvore de gravacoes foi resolvido, mas nao e evidencia.

**Fix:**

```python
# `..` sairia da arvore de gravacoes: `recordings/../tests/x.png` existe e
# nao e evidencia de spike nenhum. `is_file` porque um diretorio com nome de
# PNG e o modo de falha deterministico dos testes deste projeto.
def _resolvido(raiz: Path, citado: str) -> bool:
    if ".." in Path(citado).parts:
        return False
    return (raiz / citado).is_file()
```

e usar nos dois pontos, com a mensagem de recusa distinguindo "nao existe" de
"aponta para fora de recordings/".

---

### WR-03: As teclas do navegador de frames colidem: `S` maiusculo anda para FRENTE, e as setas nao funcionam no Windows

**File:** `l2scanner/calibrar_mercado.py:371-378`

**Issue:**

```python
if tecla in (ord("d"), ord("D"), 83):     # 83 == ord("S")
elif tecla in (ord("a"), ord("A"), 81):   # 81 == ord("Q")
elif tecla in (ord("w"), ord("W"), 82):   # 82 == ord("R")
elif tecla in (ord("s"), ord("S"), 84):   # ord("S") == 83, ja consumido acima
```

Os codigos 81-84 sao as setas do backend **GTK/Linux**. Em ASCII eles sao
`Q`, `R`, `S`, `T`. Duas consequencias:

- **`S` maiusculo faz o oposto do `s` minusculo**: cai no primeiro ramo e avanca
  um frame, em vez de voltar dez. `ord("S")` no ultimo ramo e **codigo morto** —
  nunca alcancavel.
- **No Windows as setas nao chegam.** `waitKey` devolve `0x250000` e derivados
  para as setas; `& 0xFF` (linha 359) zera isso. As quatro linhas de ajuda
  impressas em 331-332 ("seta direita -> proximo frame") anunciam teclas mortas
  na unica plataforma suportada pelo projeto.

**Fix:** ler o codigo cheio antes de mascarar, e tirar os codigos GTK.

```python
bruto = cv2.waitKey(0)
tecla = bruto & 0xFF
# Setas no Windows: waitKeyEx devolve 2555904 (dir), 2424832 (esq),
# 2490368 (cima), 2621440 (baixo). Os codigos 81-84 sao as setas do GTK e
# colidem com Q/R/S/T em ASCII: com eles, 'S' maiusculo andava para frente.
SETA_DIR, SETA_ESQ, SETA_CIMA, SETA_BAIXO = 2555904, 2424832, 2490368, 2621440
if tecla in (ord("d"), ord("D")) or bruto == SETA_DIR:
    ...
```

ou, mais simples, remover as setas da ajuda e suportar so D/A/W/S.

---

### WR-04: Fechar o navegador de frames no X trava a ferramenta para sempre

**File:** `l2scanner/calibrar_mercado.py:359`

**Issue:** `cv2.waitKey(0)` bloqueia indefinidamente. Se o usuario fecha a janela
no X — coisa que o texto impresso nao proibe, ao contrario do bloco de selecao,
que avisa "NAO feche no X" (linha 529) — nao ha mais janela para receber tecla e
o `waitKey(0)` nunca retorna. O console fica parado na tela de instrucoes, sem
janela e sem mensagem, e a unica saida e Ctrl-C.

**Fix:** usar timeout e conferir se a janela ainda existe.

```python
tecla = cv2.waitKey(50)
if cv2.getWindowProperty(janela, cv2.WND_PROP_VISIBLE) < 1:
    raise MercadoNaoCalibravel(
        "a janela do navegador foi fechada -- nada foi gravado. "
        "Use ESC para cancelar ou ENTER para escolher o frame."
    )
if tecla == -1:
    continue
```

e acrescentar "NAO feche no X" ao bloco de ajuda, como ja existe para a selecao.

---

### WR-05: O dreno da fila de teclas para no PRIMEIRO `-1` — mais fraco que o diagnostico que achou o bug

**File:** `l2scanner/calibrar.py:420-422`, contra `tools/diagnosticar_selecao.py:75-88`

**Issue:** a correcao do vazamento de ENTER e:

```python
for _ in range(20):
    if cv2.waitKey(1) == -1:
        break
```

Sai na primeira sondagem vazia — ~1 ms de bombeamento. A ferramenta que
diagnosticou o defeito documenta, MEDIDO, que isso nao basta:

> "ele nao para no primeiro -1 (**uma tecla pode chegar alguns milissegundos
> depois**) e ele IMPRIME o que achou"

e usa 300 ms. O caminho de risco nao e so o navegador: `calibrar()` faz **5 + N**
selecoes seguidas, e a tecla que confirma a selecao *k* e candidata a vazar para
a selecao *k+1*. Quando isso acontece, `_selecionar_regiao` devolve `(0,0,0,0)`,
`_marcar` levanta `MercadoNaoCalibravel("selecao cancelada — nada foi gravado")`
e **todos** os retangulos ja marcados sao perdidos. E o sintoma original, so que
agora no meio do fluxo em vez de no comeco.

**Fix:** drenar por tempo, nao por primeira leitura vazia.

```python
# NAO parar no primeiro -1: medido em `tools/diagnosticar_selecao`, a tecla
# pode chegar alguns ms depois da janela anterior fechar. Parar cedo deixa
# o ENTER vazar para a proxima selecao, que devolve (0,0,0,0) e joga fora
# todos os retangulos ja marcados.
fim = time.perf_counter() + 0.15
while time.perf_counter() < fim:
    cv2.waitKey(1)
```

---

### WR-06: `config.toml` invalido, `watchlist` com o tipo errado, ou falha de gravacao viram traceback depois de todo o trabalho de mouse

**File:** `l2scanner/calibrar_mercado.py:443-445`, `605`, `636-640`

**Issue:** tres superficies sem tratamento, todas depois de o usuario ja ter
marcado 5+ retangulos:

1. `tomllib.loads(caminho.read_text(...))` (linha 443) sem `try`. Um
   `config.toml` com erro de sintaxe levanta `TOMLDecodeError`, que `main` nao
   captura (linha 638 so pega `MercadoNaoCalibravel`) — traceback, tudo perdido.
   E a leitura acontece **depois** das ancoras e da grade (linha 555), maximizando
   o prejuizo.
2. `[str(item) for item in itens ...]` (linha 445) sem checar o tipo. Com
   `watchlist = "Bota"` (string em vez de lista), itera **caracteres**: a
   ferramenta pede quatro recortes, `B`, `o`, `t`, `a`, e monta uma matriz de
   confusao sobre eles.
3. `cal.salvar(arquivo)` (linha 605) sem `try`. Pasta somente-leitura, disco
   cheio ou arquivo travado por antivirus produzem `OSError` cru.

**Fix:** encaixar tudo em `MercadoNaoCalibravel`, que ja imprime limpo e devolve
1 (e o `.bat` ja trata o `errorlevel`).

```python
try:
    dados = tomllib.loads(caminho.read_text(encoding="utf-8"))
except (tomllib.TOMLDecodeError, OSError) as erro:
    raise MercadoNaoCalibravel(
        f"nao consegui ler {caminho.name}: {erro}\n"
        f"  Conserte o config.toml e rode de novo."
    ) from erro
itens = dados.get("mercado", {}).get("watchlist", [])
if not isinstance(itens, list):
    raise MercadoNaoCalibravel(
        f"[mercado] watchlist precisa ser uma LISTA, veio "
        f"{type(itens).__name__}. Exemplo: watchlist = [\"+3 Bota X\"]"
    )
```

E ler a watchlist **antes** de abrir a primeira janela de selecao: falhar antes
de o usuario gastar cinco arrastos e mais barato que falhar depois.

---

### WR-07: `_MODO_DPI` e calculado e nunca conferido — justamente na ferramenta que PERSISTE coordenadas

**File:** `l2scanner/calibrar_mercado.py:49-51`

**Issue:** o modulo abre com

```python
_MODO_DPI = tornar_consciente_de_dpi()
```

e o comentario acima diz "DPI PRIMEIRO, pelo mesmo motivo de `calibrar.py`: a
ferramenta e o scanner precisam concordar sobre o que e um pixel". Mas
`calibrar.py:824` e `__main__.py:2078` fazem mais que chamar — os dois testam
`_MODO_DPI.startswith("FALHOU")` e avisam:

> "AVISO: nao consegui declarar consciencia de DPI. Se a escala da sua tela nao
> for 100%, as coordenadas sairao erradas."

`calibrar_mercado.py` nao testa nada; a variavel fica sem uso. Numa falha de DPI
o scanner apenas le errado naquela execucao — mas o **calibrador grava** as
coordenadas erradas no `calibration.json`, onde elas ficam. E a instancia em que
o aviso vale mais, e e a unica das tres que nao o tem.

**Fix:** copiar o bloco de `calibrar.py:824-826` para dentro de `main()`, antes
de `calibrar(args)`.

---

### WR-08: `ANCORAS_SUGERIDAS` diz que a ferramenta "mostra cada regiao e o usuario confirma" — ela nao mostra

**File:** `l2scanner/calibrar_mercado.py:95-103`, `535-542`, `592`

**Issue:** a constante carrega `dx`/`dy` medidos em campo e a docstring afirma:

> "Sao SUGESTOES pre-preenchidas, nao verdade: **a ferramenta mostra cada regiao
> e o usuario confirma ou ajusta**."

No laco de 535-540, `_dx` e `_dy` sao desempacotados e descartados; nada e
pre-desenhado; `_marcar` abre um `selectROI` vazio. A unica coisa que sobrevive
das medicoes e o texto `(sugerido: 100x28)`. Num codebase cuja docstring e o
contrato, isto e uma afirmacao de comportamento inexistente — e ela importa
porque a alternativa (desenhar o retangulo sugerido sobre o frame antes do
arrasto) e uma defesa real contra CR-01.

Acoplamento relacionado, na linha 592:

```python
cal.mercado_molde_da_ancora = molde_para_hex(ancoras[0].molde)
```

`ancoras[0]` so e o `titulo` porque `caixas` preserva a ordem de insercao de
`ANCORAS_SUGERIDAS` e `titulo` esta primeiro. Reordenar a constante — o que a
propria docstring de `localizar_painel` incentiva ("a ordem certa e a mais
confiavel primeiro") — passa a gravar o molde de uma ancora ao lado do retangulo
de outra, em `mercado_ancora`.

**Fix:** ou desenhar a sugestao (e cumprir a docstring), ou corrigir a docstring
para "sugestoes impressas no texto". E indexar por nome:

```python
molde_do_titulo = next(a.molde for a in ancoras if a.nome == "titulo")
cal.mercado_molde_da_ancora = molde_para_hex(molde_do_titulo)
```

---

### WR-09: `derivar_grade` devolve "1 linha" para uma grade degenerada e nunca confere contra o numero medido do layout

**File:** `l2scanner/calibrar_mercado.py:237`

**Issue:**

```python
linhas = max(1, galt // altura_da_linha)
```

O `max(1, ...)` transforma "a area da lista e menor que uma linha" — um retangulo
obviamente marcado errado — em `linhas_por_pagina: 1`, gravado com a mesma
confianca de um valor correto. Confirmado: grade de 20 px de altura com linha de
45 px devolve `linhas_por_pagina: 1`.

E a docstring **ja sabe a resposta certa**:

> "10 linhas na grade de negociacao, passo de 45 px exatos; 9 na tela de busca"

mas `layout` so e gravado, nunca usado para conferir. Com CR-01 em vigor (arrasto
com ~5,7 px de granularidade), errar a altura da primeira linha em 5 px sobre
450 px de grade ja troca 10 por 9 — silenciosamente, e a Fase 2 le uma linha a
menos por pagina para sempre.

**Fix:** recusar o degenerado e avisar alto sobre a divergencia do esperado.

```python
LINHAS_ESPERADAS = {"negociacao": 10, "adena": 10, "busca": 9}

if altura_da_linha > galt:
    raise MercadoNaoCalibravel(
        f"a primeira linha ({altura_da_linha} px) e mais alta que a area da "
        f"lista ({galt} px) — os dois retangulos parecem trocados. Remarque."
    )
linhas = galt // altura_da_linha
esperado = LINHAS_ESPERADAS.get(layout)
if esperado is not None and linhas != esperado:
    print(
        f"\nATENCAO: sairam {linhas} linhas por pagina, e o layout "
        f"'{layout}' foi MEDIDO em campo com {esperado} (passo de 45 px). "
        f"Confira a imagem de conferencia antes de confiar nesta grade."
    )
```

---

### WR-10: A leitura de mercado que EXPLODE some no `DEBUG` — sem o aviso unico que o vizinho tem

**File:** `l2scanner/sessao.py:313-317`

**Issue:**

```python
except Exception:
    log.debug("Leitura do mercado falhou neste tick", exc_info=True)
    return None
```

Dez linhas acima, o caminho irmao (recorte ausente) usa
`_ja_avisou_do_mercado_sem_recorte` + `log.warning`, com um comentario que
argumenta exatamente contra o que este `except` faz:

> "Um vigia ligado que nunca recebe pixels e degradacao SILENCIOSA — o console
> simplesmente nunca fala do mercado e o usuario conclui que o painel nunca
> abriu."

Um molde corrompido, uma janela num formato inesperado ou um `cv2.error`
persistente produzem exatamente esse desfecho, para sempre, em `DEBUG` — que nao
esta ligado num farm normal. `NUNCA LEVANTA` esta certo; ficar mudo nao.

**Fix:** mesmo trilho do vizinho — um `WARNING` uma vez, `DEBUG` nos demais.

```python
except Exception:
    if not self._ja_avisou_da_falha_do_mercado:
        self._ja_avisou_da_falha_do_mercado = True
        log.warning(
            "Leitura do mercado falhando neste frame e provavelmente nos "
            "proximos (molde corrompido ou janela em formato inesperado). "
            "Rode calibrar-mercado.bat. Todo o resto do scanner continua igual.",
            exc_info=True,
        )
    else:
        log.debug("Leitura do mercado falhou neste tick", exc_info=True)
    return None
```

---

### WR-11: O portao do spike nao tem um unico teste

**File:** `tools/conferir_spike_respostas.py` (modulo inteiro)

**Issue:** o irmao dele, `tools/conferir_gravacoes_do_spike.py`, tem
`tests/test_conferir_gravacoes_do_spike.py`. Este nao tem nada — nenhum arquivo
de teste no repositorio o importa. E ele decide se as 9 respostas que sustentam
a grade, os glifos e a forma da ancora se sustentam.

CR-05 sobreviveu por causa disso: um unico teste com o texto `"NAO VERIFICADO"`
o teria pego. O mesmo vale para a legenda-fora-da-contagem e para o
fechamento-por-nivel-de-cabecalho, dois comportamentos que os comentarios do
modulo descrevem como resultado de teste por mutacao — mas a mutacao foi feita a
mao e nao ficou presa.

**Fix:** `tests/test_conferir_spike_respostas.py` com, no minimo: selo negado
(`NAO VERIFICADO`), zero selos, dois selos, secao positiva sem frame, frame
citado inexistente, `..` no caminho, legenda com as tres palavras fora da
contagem, e numeracao com um numero pulado.

---

### WR-12: `calibrar_mercado` reescreve o `calibration.json` inteiro sem escrita atomica nem backup

**File:** `l2scanner/calibrar_mercado.py:605`, mecanismo em `l2scanner/calibracao.py:405-407`

**Issue:** `Calibracao.salvar` faz `caminho.write_text(...)` direto sobre o
arquivo final. Uma interrupcao no meio (Ctrl-C impaciente, disco cheio, antivirus
segurando o handle) deixa um JSON truncado, e a proxima carga levanta
"esta corrompido: recalibre" — para o **scanner de party inteiro**, nao so para o
mercado. O que se perde e a party window, os limiares HSV afinados a mao contra o
`Gamma=1.16` do usuario, o `hp_proprio` e as assinaturas de nome.

Isso ja existia, mas esta fase muda o perfil de risco: o `calibration.json` era
escrito uma vez, na calibracao inicial; agora ha um segundo escritor que o
usuario roda repetidamente, com uma matriz de confusao que pode recusar no meio.

**Fix:** escrita atomica, no lugar onde todos os escritores herdam.

```python
def salvar(self, caminho: Path) -> None:
    dados = {...}
    temporario = caminho.with_suffix(".json.tmp")
    temporario.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
    # os.replace e atomico no mesmo volume: ou o arquivo antigo inteiro, ou o
    # novo inteiro. Um JSON truncado aqui derruba a calibracao de PARTY junto,
    # e com ela os limiares HSV afinados a mao.
    os.replace(temporario, caminho)
```

---

### WR-13: `diagnosticar_selecao` le "processo caiu" como "defeito reproduzido"

**File:** `tools/diagnosticar_selecao.py:161-186`

**Issue:** o veredito de cada fase vem do `returncode` do subprocesso: `0` =
PASSOU, `1` = FALHOU, `2` = ERRO. Mas `1` tambem e o codigo com que o CPython sai
de **qualquer excecao nao tratada** — um `cv2.error`, um `ImportError`, um
`FileNotFoundError` no `--gravacao`. Nesse caso a ferramenta imprime

> "FALHOU -- voltou sozinho, sem esperar ninguem"
> "CONCLUSAO: a tecla vem do NAVEGADOR DE FRAMES."

que e uma conclusao afirmada sobre uma medicao que nunca aconteceu, na ferramenta
escrita justamente para trocar "tenta mais um fix" por "mede qual hipotese e a
verdadeira".

**Fix:** codigos distintos e nao sobrepostos ao default do interpretador (por
exemplo 10 = passou, 11 = falhou, 12 = erro esperado), e tratar qualquer outro
valor como `ERRO` explicito:

```python
rotulo = {10: "PASSOU", 11: "FALHOU", 12: "ERRO"}.get(codigo, f"CRASH ({codigo})")
```

e so tirar conclusao quando as duas fases devolveram codigos conhecidos.

---

## Info

### IN-01: `_selecionar_regiao` chama `destroyAllWindows`, nao `destroyWindow`

**File:** `l2scanner/calibrar.py:430`

**Issue:** destroi janelas que a funcao nao criou. Hoje ninguem mantem janela
aberta durante a selecao, entao e inofensivo — mas o `navegar_e_escolher` ja tem
o cuidado de destruir so a sua (`calibrar_mercado.py:361`), e a assimetria e uma
armadilha para o proximo chamador.

**Fix:** `cv2.destroyWindow(titulo)` dentro de um `try/except cv2.error`.

---

### IN-02: Dois blocos de comentario fundidos e deslocados do codigo que explicam

**File:** `l2scanner/calibrar.py:390-419`

**Issue:** o paragrafo do `namedWindow/moveWindow` termina em
"...em lugar nenhum previsivel." e a linha seguinte, sem linha em branco, abre
"# ESVAZIA A FILA DE TECLAS ANTES DE ABRIR A SELECAO." — dois workarounds
diferentes, de duas investigacoes diferentes, num bloco so. E o bloco inteiro
esta **acima** do laco de dreno, enquanto o `namedWindow` que a primeira metade
descreve so aparece 4 linhas depois. Num arquivo cujo comentario e o registro da
medicao, isso e o rastro visivel de dois fixes empilhados — e o primeiro deles e
o CR-01.

**Fix:** separar os dois blocos e por cada um colado no seu codigo.

---

### IN-03: Escrita morta em `sessao.tick`

**File:** `l2scanner/sessao.py:244`

**Issue:** `self.ultima_observacao = observacao` e a ultima instrucao do `try` e
e sobrescrita incondicionalmente na linha 258 pela versao com
`mercado_aberto_aparente`. Nenhum caminho le o valor intermediario.

**Fix:** remover a linha 244; o `except` acima ja garante que nada e publicado
quando a extracao falha.

---

### IN-04: `calibrar-mercado.bat` — `%*` sem aspas e um byte corrompido no comentario

**File:** `calibrar-mercado.bat:37`, `:41`

**Issue:** (a) `".venv\Scripts\python.exe" -m l2scanner.calibrar_mercado %*` — um
caminho de gravacao com espaco chega quebrado em dois argumentos. Hoje as pastas
sao `recordings\AAAAMMDD-HHMMSS-rotulo`, sem espaco, mas `--frame` aceita
qualquer caminho. (b) A linha 41 tem um byte fora do encoding (`0x97`) (`—` gravado em
UTF-8 num arquivo lido como CP1252 pelo `cmd`), o que suja o comentario.

**Fix:** (a) documentar que caminhos com espaco precisam de aspas, ou passar
`%*` ja entre aspas; (b) usar `--` em vez de travessao nos `.bat`.

---

### IN-05: `matriz_de_confusao` pode gravar um limiar 0.0 que o proprio carregador recusa

**File:** `l2scanner/calibrar_mercado.py:181-196`

**Issue:** `pior = -1.0` e sentinela. Se todo par pontuar exatamente `-1.0`
(moldes perfeitamente anticorrelacionados), o `if score > pior` nunca dispara:
`par` fica `None` e `limiar_sugerido` sai `(1.0 + -1.0) / 2 == 0.0`. Gravado,
`_conferir_as_chaves_de_mercado` recusa `0.0` (faixa valida `(0, 1]`) e a
calibracao acabada de gravar nao carrega mais — sem caminho de saida, ja que o
criterio do ROADMAP e "sem editar JSON a mao". Improvavel, mas o custo e o
arquivo inutilizado.

**Fix:** usar `pior = None` e `if par is None or score > pior`.

---

### IN-06: `RastreioDoPainel._varrer` guarda a origem mesmo quando o voto sai FECHADO

**File:** `l2scanner/mercado_visao.py:509-514`

**Issue:** quando `localizar_painel` acha uma origem cujas ancoras todas
abstem-se (painel encostado na borda da janela), `self._origem = origem` e
gravado e o voto devolvido tem `aberto=False`. A propriedade publica `origem`
passa a dizer "rastreado" para um painel que o modulo acabou de declarar
invisivel, e o proximo tick paga uma conferencia inutil antes de varrer de novo.

**Fix:** so persistir a origem quando o voto confirma:

```python
voto = conferir_painel(janela, origem, self._ancoras, self._limiar)
if voto.aberto:
    self._origem = origem
return voto
```

---

_Reviewed: 2026-08-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
