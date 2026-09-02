# Phase 1: A leitura da barra — pixel vira número, ou recusa · Pesquisa

**Pesquisado:** 2026-09-02
**Domínio:** leitura de números da HUD do L2 XM Essence — OCR do Windows, moldes de glifo,
calibração compartilhada e captura por janela. **Brownfield maduro:** ~41k linhas em `l2scanner/`,
102 arquivos em `tests/`.
**Confiança:** ALTA nos achados de código (todos com `arquivo:linha`, arquivos abertos com `Read`
nesta sessão); MÉDIA no comportamento do OCR sobre a fonte da barra (medido só no spike, com uma
única amostra); BAIXA em qualquer coisa que dependa da geometria da barra em px, que ninguém mediu.

> **Aviso ao planejador, na primeira linha porque é onde ele vai olhar:** esta pesquisa **refuta
> cinco premissas** do `CONTEXT.md`, do `ROADMAP.md` e do `CLAUDE.md`. Duas delas mudam o custo da
> fase, uma delas cancela uma tarefa inteira, e uma delas (a do espaço de coordenadas) mudaria o
> significado de todos os números do spike se estivesse errada na outra direção. A lista completa,
> com evidência, está na seção final **"O que o plano tem que decidir, e o que já está decidido"**,
> item **(c)**. Leia essa seção antes de escrever a primeira tarefa.

---

<user_constraints>
## Restrições do usuário (cópia verbatim do `01-CONTEXT.md`)

### Decisões travadas

**Área 1 — Qual leitor lê qual campo**

- **Adena e EXP: OCR do Windows (`l2scanner.ocr`).** Medido no spike: `ler_texto` devolveu
  `Special 58,40 13,091 10,679,769` do recorte **cru** da direita, e `ler_texto_ampliado`
  devolveu `EXP ⟨lixo⟩68.6738% 582% : 83` da esquerda. Os dois campos já saem; o trabalho é
  extração e validação, não reconhecimento.
- **Nível: glifos (`mercado_leitura.ler_glifos` + `moldes_da_tinta`).** O OCR cru devolveu
  vazio, e a máscara de branco que o faz funcionar (`vmin=210`) é exatamente o pré-processamento
  que `mascara_de_numero` já implementa. Dois dígitos, fonte fixa, conjunto fechado `0-9`: é o
  caso mais fácil que aquele leitor já resolve, e ele **recusa por pontuação** em vez de chutar.
  *Alternativa registrada:* OCR com máscara também funcionou (`210 → '66'`). Se montar os moldes
  do nível custar mais que uma tarefa, o OCR mascarado é aceitável — desde que a recusa nomeada
  continue de pé. Quem decide é a medição, e a medição é do plano.
- **A regra que não é negociável, seja qual for o leitor:** `numero_valido` e a recusa nomeada
  valem para os três campos. Nenhum caminho devolve número sem passar por validação.
- **Normalização de vírgula/ponto é reuso, não reescrita.** O jogo usa o mesmo caractere para
  decimal no EXP (`68.5632%`) e para milhar na adena (`10.673.628`), e o OCR devolveu
  `10,679,769`. `centesimos_de_moeda` e `inteiro_de_quantidade` já atravessaram essa dor.

**Área 2 — Como as quatro casas decimais ficam de pé**

- **Cruzamento de duas escalas.** O EXP é lido em 1x e em 2x; as duas leituras têm que dar o
  **mesmo número**. Divergiram → recusa. Isto é a rede que `manutencao.py` já usa para o banner
  e que `mercado_leitura._observar_o_cruzamento` usa para a adena. O custo é um segundo OCR de
  um recorte de 26 px; o benefício é que o modo de falha mais caro da milestone (quarta casa
  errada, invisível ao olho, taxa horária inteira de diferença) passa a exigir que **dois
  leitores errem igual**.
  *Alternativa registrada:* uma leitura só + monotonicidade entre amostras. Mais barata, mas só
  pega o erro **depois** de gravar — e o critério 3 diz que número errado gravado é veneno.
- **A forma é obrigatória, não opcional.** `\d{1,3}[.,]\d{4}%` — três casas ou cinco casas ou
  sem `%` é **recusa**, nunca arredondamento e nunca completar com zero. Um `68,56%` aceito e
  silenciosamente tratado como `68,5600` é uma mentira de 0,0032 de EXP que ninguém consegue ver
  depois.
- **O EXP interno é inteiro, não float.** Guardado em **décimos de milésimo de ponto
  percentual** (`68,5632%` → `685632`), pela mesma razão que o mercado guarda
  `total_em_centesimos`: comparação exata, sem erro de arredondamento acumulando na diferença
  entre amostras — e a diferença entre amostras é o produto inteiro desta milestone.

**Área 3 — Onde a calibração mora**

- **Chaves achatadas com prefixo `renda_`**, seguindo `mercado_*` e `tiat_*` que já ocupam o
  arquivo. Verificado: o `calibration.json` de hoje tem 44 chaves de topo, todas nesse padrão.
  Um sub-objeto aninhado `renda: {}` seria mais bonito e seria o **único** assim.
  *Alternativa registrada:* aninhar, se o revisor preferir — é troca interna, não muda requisito.
- **Chaves previstas** (o plano ajusta): `renda_nivel`, `renda_barra_esquerda`,
  `renda_barra_direita` (`Regiao`), e os limiares `renda_vmin_do_nivel`,
  `renda_limiar_de_glifo`, `renda_escalas_do_exp`.
- **Nenhum número do spike aparece no fonte.** `1368`, `246`, `210`, `500`, `470` são valores
  iniciais que o calibrador **grava**; eles podem aparecer em teste e em documentação, nunca em
  `l2scanner/*.py` fora de teste. O roadmap fez disso um critério verificável por `grep`.

**Área 4 — O calibrador, e a não-destruição que ele precisa PROVAR**

- **`calibrar-renda.bat` + `l2scanner/calibrar_renda.py`**, mesma família dos dois `.bat` que já
  existem. Seleção de retângulo por `cv2.selectROI` sobre um grab de tela cheia — o caminho que
  `tools/pick_region.py` e `calibrar_mercado.py` já usam.
- **O defeito a não repetir tem endereço.** `calibrar_mercado.py:2721` faz `cal.mercado_grade =
  grade` e, por isso, calibrar a aba Adena apagaria a grade de negociação. O `calibration.json`
  é dividido por **quatro** features. O calibrador desta fase **carrega o arquivo inteiro, muda
  só as chaves `renda_*`, e reemite tudo**.
- **E isso vira teste, não promessa.** Um teste carrega um `calibration.json` com chaves de
  party, mercado e tiat, roda o calibrador da renda, e afirma que **todas as outras chaves
  saíram bit-idênticas**. Sem esse teste o critério 5 do roadmap é uma frase.
- **O `vmin` do nível é calibrado com feedback visual.** A curva medida (`170 → vazio`,
  `190 → '6b'`, `210 → '66'`) mostra que a fronteira é estreita e que errar por 20 devolve um
  dígito errado — `6b` não é vazio, é uma leitura **errada**, que é pior. O calibrador tem que
  mostrar ao usuário o que a máscara está deixando passar, como o trackbar HSV do projeto faz.

**Área 5 — Mira: de qual personagem é esta leitura**

- **`--janela` é obrigatório**, não conveniente. O usuário roda duas instâncias (Yazalaque e
  Faerlina); EXP e adena são **do personagem**. Sem mira, o scanner lê a instância errada e
  produz uma taxa que não descreve ninguém — o modo de falha do REG-04.
- **Herda o caminho inteiro do `--mercado`**: resolução do título pela chave `[jogo] personagem`
  do `config.toml`, `captura_janela` por Windows Graphics Capture. A Fase 1 não inventa captura.
- **A leitura carrega o nome do personagem**, mesmo sem existir arquivo ainda. É o campo que a
  Fase 2 vai gravar, e decidi-lo agora custa zero; descobri-lo na Fase 2 custa mexer no esquema
  depois que o `dashboard` já está apontado para ele.

### Discrição do Claude

- Nomes exatos de módulo, função e chave de calibração.
- Se o nível usa glifos ou OCR mascarado — decidido por medição durante o plano, com a recusa
  nomeada obrigatória nos dois casos.
- Se a leitura da barra esquerda extrai também o `642%` (bônus) e o `83` — estão no mesmo
  recorte e sairiam de graça, mas nenhum requisito os pede. Preferência: **extrair e descartar**,
  para não fixar um formato de campo que ninguém pediu.

### Ideias adiadas (FORA DE ESCOPO)

- Ler o `642%` (bônus de XP) e o `83` como campos de primeira classe — estão no mesmo recorte,
  mas nenhum requisito os pede. Se virarem interessantes, o recorte já estará calibrado.
- Ler o L-Coin (`13.091`) e o XM (`58,40`) da barra direita. **Tentador e adjacente ao
  `mercado`**, que já converte adena→XM→BRL. Fica fora: é escopo do outro workstream e
  acrescentaria coluna a um esquema que o `dashboard` vai consumir.
- XP absoluto do chat (CHAT-01) — já está em v2 no `REQUIREMENTS.md`.
</user_constraints>

---

<phase_requirements>
## Requisitos da fase

| ID | Descrição (do `REQUIREMENTS.md`) | O que a pesquisa achou que habilita a implementação |
|----|----------------------------------|------------------------------------------------------|
| LEIT-01 | Ler o **nível** sob o retrato | `mercado_leitura.mascara_de_numero` (`:155`) é exatamente `hsv[:,:,2] > valor_minimo` — a máscara de branco do spike, com o piso **por parâmetro, sem default**. Dois caminhos viáveis: OCR sobre a máscara, ou `ler_celula`/`ler_glifos` com moldes. Custo dos moldes medido abaixo — é o achado mais caro desta pesquisa. |
| LEIT-02 | Ler **EXP% com quatro casas** | `ocr.ler_texto` (2x) e `ocr.ler_texto_ampliado` (3x) já são **duas escalas independentes** e o par já é usado como cruzamento em `manutencao.py:814-818` e `mercado_leitura._ler_o_nome:2311-2312`. A gramática de quatro casas **não existe** no projeto: `centesimos_de_moeda` trava em 2 casas (`:568`). É o único parser genuinamente novo da fase. |
| LEIT-03 | Ler **adena total** | **Executado nesta sessão:** `numero_valido("10,673,628") is True` e `inteiro_de_quantidade("10,673,628") == 10673628`. Reuso direto, com uma normalização `.`→`,` antes. |
| LEIT-04 | **Leitura duvidosa vira recusa** | `Descarte` (`mercado_leitura.py:1563`), `_recusar` (`:2379`) e as constantes `MOTIVO_*` (`:1514-1524`) são a forma da casa. **Atenção:** `Descarte` tem só `indice` e `motivo` — o `detalhe` vai para o log, não para o dado. |
| LEIT-05 | **Regiões e limiares no `calibration.json`** | `Calibracao` (`calibracao.py:181`) já tem o padrão de campo opcional por feature; `salvar` (`:668`) e `carregar` (`:771`) são o par a estender. Recipe exata na seção 4. |
| LEIT-06 | **Existe um calibrador** | `calibrar.calibrar_tiat` (`calibrar.py:1168-1250`) é o precedente exato e mínimo: 82 linhas, dois `_selecionar_regiao`, um `cal.salvar`. **É o template, não o `calibrar_mercado.py` de 3.359 linhas.** |
</phase_requirements>

---

## Sumário

Esta fase é quase inteiramente **composição de peças existentes**, e a pesquisa confirma isso —
com três exceções que custam trabalho de verdade e uma que cancela trabalho previsto.

**O que já está pronto e só precisa ser chamado.** A captura por janela (`JanelaSource`), a
resolução do título por `[jogo] personagem`, a máscara de brilho com piso parametrizado, a
gramática de milhar com blocos de três, o conversor `inteiro_de_quantidade`, a forma de recusa
`Descarte`/`_recusar`, o par de escalas de OCR e o padrão load-mutate-save do `calibration.json`
existem, estão testados e foram lidos linha a linha nesta sessão. A adena, medida por execução
real do parser, **já lê e já valida** com o que está no repositório mais uma linha de
normalização.

**O que custa trabalho novo, e quanto.** (1) A **gramática de quatro casas decimais com `%`** não
tem irmã no projeto: `centesimos_de_moeda` trava `len(decimal) != 2` em `mercado_leitura.py:568` e
só aceita vírgula. Copiar a *forma* dela é honesto; reusá-la não é. (2) O **cruzamento de duas
escalas** existe como padrão em dois lugares, mas nos dois ele compara *vereditos de catálogo*, não
*números* — a comparação de dois inteiros é nova, embora trivial. (3) O **calibrador com feedback
visual do `vmin`** não tem precedente: o projeto tem `_selecionar_regiao` (arrastar retângulo) e
tem o `_marcar` com sugestão, mas **não tem trackbar** — o `tools/calibrate_hsv.py` que o
`CLAUDE.md` descreve **não existe no repositório**.

**O que a pesquisa cancela.** O **defeito de não-destruição do `calibrar_mercado.py` já está
consertado** — consertado em `f8dbfe2 feat(05-04): o calibrador escreve POR LAYOUT, e --layout
adena deixa de ser bomba`, e prendido por `tests/test_calibrar_layout_nao_apaga_negociacao.py`. A
linha `cal.mercado_grade = grade` mora hoje em `calibrar_mercado.py:3182`, **depois** do `return`
de `:3155`. O risco real desta fase **não é** repetir aquele defeito: é o defeito *estrutural* de
`Calibracao.salvar` (`calibracao.py:668-758`), que emite uma **lista literal de chaves** e portanto
**apaga silenciosamente qualquer chave `renda_*` que não tenha sido declarada no dataclass E no
`salvar`**. Esse é o modo de falha que o teste precisa pegar, e ele é o oposto do que o
`CONTEXT.md` descreve.

**Recomendação primária:** trate a fase como **três módulos e um calibrador**, nesta ordem —
(1) estender `Calibracao` com seis campos `renda_*` + validadores, (2) `l2scanner/renda_leitura.py`
puro (`frame → LeituraDaRenda | RecusaDaRenda`), (3) `l2scanner/calibrar_renda.py` clonando a
*forma* de `calibrar_tiat`, (4) o teste de não-destruição por **enumeração de chaves do arquivo de
antes**, copiado de `tests/test_calibrar_layout_nao_apaga_negociacao.py`. E **meça a fonte da barra
antes de decidir moldes**: um conjunto de moldes para o nível é um trabalho de várias sessões, não
de uma tarefa.

---

## Mapa de responsabilidade arquitetural

| Capacidade | Camada primária | Camada secundária | Por que essa camada é dona |
|---|---|---|---|
| Achar a janela do personagem certo | Ferramenta/lançador (`.bat` + `config.ler_personagem_do_jogo`) | — | O `.bat` monta o título e passa `--janela`; o fonte nunca escreve `"Yazalaque"`. Precedente literal em `vigiar-mercado.bat` e a razão em `config.py:842-845`. |
| Entregar um frame da janela | Captura (`captura_janela.JanelaSource`) | — | Já resolve WGC, janela coberta, DPI e origem. Nada aqui é reescrito. |
| Recortar as três regiões | Puro (`renda_leitura`) | Calibração (fornece os `Regiao`) | O recorte é uma fatia de array; quem sabe ONDE é o `calibration.json`. |
| Pixel → texto | Puro (`ocr` e/ou `mercado_leitura.ler_celula`) | — | Os dois já existem e os dois já prometem **nunca levantar** (`ocr.py:197-212`, `mercado_leitura.py:1031`). |
| Texto → número, ou recusa | Puro (`renda_leitura`, gramáticas) | `mercado_leitura.numero_valido`/`inteiro_de_quantidade` | A gramática é a trava de validação, não só parsing (`mercado_leitura.py:606-645`). |
| Onde ficam os retângulos e limiares | Config (`calibracao.Calibracao` + `calibration.json`) | — | Regra dura do `CLAUDE.md`: nenhuma constante mágica no fonte. |
| Pôr os retângulos lá | Ferramenta (`calibrar_renda.py`) | — | Módulo de ferramenta, não de produção — `mercado_leitura.py:15-25` explica por que a seta aponta ferramenta→puro e nunca o contrário. |
| Não destruir o resto do arquivo | Config (`Calibracao.salvar`) + teste | Ferramenta | O `salvar` é o único ponto que decide o que sobrevive. O teste é o que prova. |

---

## Pilha padrão

**Nenhuma dependência nova.** Confirmado lendo `requirements.txt` inteiro: `mss`, `opencv-python`,
`numpy`, `windows-capture`, os seis `winrt-*` e `discord.py`. Tudo de que esta fase precisa já está
declarado. [VERIFIED: requirements.txt, lido nesta sessão]

| Peça | Onde | Por que é a escolha |
|---|---|---|
| OCR | `l2scanner/ocr.py` | Motor do Windows, zero instalador, import lazy dentro das funções (`ocr.py:113-116`). `disponivel()`/`motivo_indisponivel()` já dão o portão de arranque com texto de conserto. |
| Máscara de brilho | `mercado_leitura.mascara_de_numero:155` | `(hsv[:,:,2] > int(valor_minimo)).astype(uint8)` — literalmente a máscara do spike, com o piso **por parâmetro e sem default**. |
| Leitor de dígitos | `mercado_leitura.ler_celula:992` → `ler_glifos:869` | Feito para a fonte deste jogo, tudo-ou-nada, recusa por piso E margem. Depende de ter moldes (ver custo abaixo). |
| Gramática de milhar | `mercado_leitura.numero_valido:606` + `inteiro_de_quantidade:588` | Executado nesta sessão contra as strings do spike — funciona. |
| Captura | `captura_janela.JanelaSource:207` | Único caminho que enxerga a janela coberta. |
| Calibração | `calibracao.Calibracao:181` | Padrão de campo opcional + `.get` no `carregar` mantém `VERSAO_DO_ESQUEMA = 2` (`calibracao.py:23`) e não força recalibração de ninguém. |

### Alternativas consideradas

| Em vez de | Podia usar | Trade-off medido |
|---|---|---|
| `ler_glifos` + moldes para o nível | OCR sobre a máscara `vmin=210` | Moldes custam um conjunto fechado de 0-9 que **o nível não consegue mostrar** (ver "Não dá para fazer à mão"). O OCR mascarado já devolveu `66` no spike. **A alternativa registrada no CONTEXT.md é, medido, o caminho principal.** |
| Cruzamento 1x × 2x (o que o CONTEXT pede) | Cruzamento 2x × 3x (`ler_texto` × `ler_texto_ampliado`) | 1x **não é uma escala de leitura**: `ocr.py:33-45` documenta, com tabela medida, que 1x abstém nas duas imagens reais (lê `MOninutes`, guarda devolve `None`, "conferido 5 de 5, determinístico"). O par de produção é 2x × 3x. |
| `centesimos_de_moeda` para o EXP | Um irmão `decimos_de_milesimo_do_exp` | `centesimos_de_moeda` trava `len(decimal) != 2` (`:568`) e exige vírgula (`:566`). Executado: devolve `None` para `68,5632` e `68.5632`. Não generaliza. |
| `Descarte` para a recusa | `RecusaDaRenda(campo, motivo, detalhe)` | `Descarte` carrega `indice: int` (índice de **linha da grade do mercado**), que não significa nada para a renda, e **não** carrega `detalhe`. Copiar a forma, não a classe. |

**Instalação:** nenhuma. `uv`/`pip` não são tocados nesta fase.

---

## Auditoria de legitimidade de pacotes

**Não aplicável a esta fase: nenhum pacote externo é instalado.** Confirmado por leitura integral
de `requirements.txt` e pela ausência de qualquer import novo nos caminhos propostos. O firewall de
escopo (`tests/test_firewall_escopo.py`) varre `requirements.txt` declarado, o ambiente da suíte e
o `.venv` de produção atrás de bibliotecas de síntese de input — qualquer dependência nova entraria
nessa varredura. [VERIFIED: requirements.txt; tests/test_firewall_escopo.py:1-46]

---

## Resposta às sete perguntas

### 1 — `l2scanner/ocr.py`, lido inteiro (282 linhas)

**O que as duas funções fazem.** As duas são casca fina sobre `_ler(pixels, escala)`
(`ocr.py:197`), que faz, nesta ordem:

1. `pixels is None` → `None`; `pixels.size == 0` → `None` (guarda contra recorte vazio, **antes**
   de tudo, "um array de altura zero viraria uma exceção lá dentro do WinRT" — `ocr.py:206-212`).
2. `disponivel()` falso → `None`.
3. `_reconhecer`: se `ndim == 3`, `cvtColor(BGR2GRAY)` — **cinza antes de tudo**, e a docstring
   registra a medição que justifica: sobre `tests/fixtures/manutencao/banner_40min26s.png`, em COR
   o motor leu `__40nin? es` (parser → 0:00:26); em CINZA leu `40 minutes` (→ 0:40:26).
   "Não é ajuste fino — é a diferença entre acertar e errar por 40 minutos" (`ocr.py:236-240`).
4. Se `escala != 1`, `cv2.resize(..., INTER_CUBIC)`.
5. `cv2.imencode(".png", ...)` → `asyncio.run(_reconhecer_async(...))` → `SoftwareBitmap` →
   `OcrEngine.recognize_async`.

**As escalas — e aqui mora a primeira refutação.**

```
ocr.py:80   ESCALA_DE_DETECCAO   = 2
ocr.py:81   ESCALA_DE_CONFERENCIA = 3
ocr.py:172  def ler_texto(pixels)          -> _ler(pixels, ESCALA_DE_DETECCAO)     # 2x
ocr.py:186  def ler_texto_ampliado(pixels) -> _ler(pixels, ESCALA_DE_CONFERENCIA)  # 3x
```

`ler_texto` é **2x**, não 1x. `ler_texto_ampliado` é **3x**, não 2x. Não existe entrada pública em
1x: só `_ler(pixels, 1)`, privado. E o módulo argumenta explicitamente contra usar 1x
(`ocr.py:33-45`): *"1x ABSTEM NAS DUAS IMAGENS — le `MOninutes`, e a guarda de D-b devolve None
(conferido 5 de 5, determinístico). Ele NÃO serve como escala de leitura."* [VERIFIED:
l2scanner/ocr.py:33-45, 80-81, 172-196]

**Modos de falha e o que devolvem.** Todos devolvem `None`, nunca levantam. A docstring diz por
quê, e é a razão de projeto mais forte do módulo: *"Nunca levanta porque roda DENTRO do tick de
captura. Uma exceção aqui pararia o scanner de olhar a party — e a próxima morte real passaria
despercebida, que é o único defeito que este projeto trata como inaceitável"* (`ocr.py:198-203`).
Os três motivos de indisponibilidade são cacheados uma vez (`_CHECADO`/`_MOTIVO`/`_MOTOR`,
`ocr.py:104-106`) e o texto de `SEM_BINDINGS`/`SEM_MOTOR` (`ocr.py:87-99`) **carrega o conserto**,
porque "o usuário não é desenvolvedor".

**A tabela de custo, verbatim do docstring** (`ocr.py:26-31` e `ocr.py:59-62`):

```
# medição por imagem (fixture 360x135 / screenshot 385x285):
#   escala   fixture   screenshot   custo (fixture/screenshot)
#   1x       None      None         52 / 19 ms
#   2x       0:40:26   0:40:26      19 / 44 ms
#   3x       0:40:26   0:40:26      28 / 58 ms
#   4x       0:40:26   0:40:26      47 / 95 ms
#
# medição AQUECIDA, na banda de produção 732x240:
#   1x=10, 2x=23, 3x=31, 4x=55 ms
#
# (tabela ANTIGA, REFUTADA e mantida no fonte: 1x=44, 2x=158, 3x=308, 4x=680 ms
#  — estava inflada pela inicialização do motor amortizada em poucas chamadas)
```

Tradução para esta fase: **duas passadas de OCR sobre um recorte de 500×26 custam bem menos que os
23+31 ms medidos numa banda de 732×240** — a área é 6× menor. Orçamento não é restrição aqui.
[VERIFIED: l2scanner/ocr.py:26-31, 59-62]

**Existe um chamador que faz cruzamento de duas escalas? Sim — dois, e eles diferem.**

- `manutencao.py:814-820`: `barato = ler_texto` → se não parece banner, **para** (não paga a 3x);
  senão `caro = ler_texto_ampliado` → `julgar_as_duas_escalas(barato, caro, tolerancia)`. A
  docstring corrige a razão antiga em voz alta: *"A ORDEM IMPORTA, mas NÃO POR ORÇAMENTO — e vale
  dizer, porque a razão antiga caiu. […] O que a ordem preserva é DIVERSIDADE DE MÉTODO"*
  (`manutencao.py:800-806`).
- `mercado_leitura._ler_o_nome:2311-2312`: `barato = ler_texto(recorte)`,
  `caro = ler_texto_conferencia(recorte)`, e depois **resolve cada uma contra o catálogo** e
  compara as *chaves*, não os textos. Discordância → `_recusar(indice, MOTIVO_DA_DISCORDANCIA,
  f"2x=>>>{barato}<<< 3x=>>>{caro}<<<")` (`:2349-2360`).

**Para copiar:** a *forma* de `manutencao` (barata primeiro, cara só se a barata passar num teste
de forma) e o *texto de log* de `_ler_o_nome` (delimitadores `>>><<<`, porque espaço em branco
importa). O que **não** se copia é a resolução contra catálogo — a renda compara dois inteiros.
[VERIFIED: l2scanner/manutencao.py:800-822; l2scanner/mercado_leitura.py:2295-2362]

---

### 2 — `l2scanner/mercado_leitura.py`: de recorte BGR a string de dígitos

**A cadeia de produção, com assinaturas verbatim:**

```python
# mercado_leitura.py:155
def mascara_de_numero(bgr: np.ndarray, valor_minimo: int) -> np.ndarray:
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return (hsv[:, :, 2] > int(valor_minimo)).astype(np.uint8)

# mercado_leitura.py:95  (casca fina desde o 02-07)
def segmentar_glifos(recorte) -> tuple[tuple[int,int]|None, list[tuple[int,int]]]:
    return segmentar_glifos_no_brilho(recorte, VALOR_MINIMO_DO_TEXTO)   # identidade.py:56 == 180

# mercado_leitura.py:333
def moldes_da_tinta(bgr, valor_minimo, moldes, moldes_cromaticos) -> dict|None

# mercado_leitura.py:869
def ler_glifos(mascara, faixa, runs, moldes, piso, margem, *,
               largura_maxima_de_glifo: int, folga_de_cola: int|None) -> str|None

# mercado_leitura.py:992  (a composição que o chamador usa de verdade)
def ler_celula(bgr, moldes, piso, margem, *,
               valor_minimo: int, folga_de_cola: int|None) -> str|None
```

**O caminho, passo a passo.**

1. `moldes_da_tinta` decide **qual conjunto** de moldes descreve esta tinta. Ele mede a saturação
   **mediana dos pixels de tinta** (`saturacao_da_tinta:253`) e compara com
   `LIMIAR_DE_SATURACAO_DA_TINTA = 29` (`:250`). Tinta acromática → moldes brancos; tinta cromática
   com conjunto ciano completo → moldes cianos; senão → `None`, e o chamador **recusa**. O número
   29 é medido: varridas 4.248 células, o lado branco deu saturação **0 nas 3.422 sem exceção**, o
   lado cromático 113–118 (+1 artefato de scroll, 59); 29 é o meio do vão `[0, 59]`
   (`mercado_leitura.py:225-249`). **Relevante para a renda:** o texto da barra inferior é branco
   sobre fundo escuro — provavelmente acromático, mas **ninguém mediu**.
2. `ler_celula` → `segmentar_glifos_no_brilho(bgr, valor_minimo)` devolve `(faixa, runs)`. A faixa
   de linhas é **UMA só, compartilhada** por todo o retângulo, e isso é contrato: recortar cada
   glifo na própria altura "deixaria a vírgula com 3 px e o dígito com 8, descartando a posição
   vertical relativa — que é precisamente o que distingue uma vírgula (baixa) de um dígito"
   (`:110-116`). **Qualquer coluna vazia separa**, sem tolerância de lacuna, "porque a menor lacuna
   real medida entre dois glifos vizinhos é de exatamente uma coluna" (`:120-123`).
3. `ler_glifos` classifica cada run contra os moldes por `pontuar_glifos:648`, que alinha por
   preenchimento e pontua com `mercado_visao.casamento_da_ancora`. **Tudo ou nada:** basta um run
   abaixo do `piso` **ou** da `margem` para a célula inteira virar `None` (`:958-966`). Run mais
   largo que qualquer molde → guarda: com `folga_de_cola=None` cai fechado; com inteiro, tenta
   `particionar_run`.
4. `numero_valido:606` afirma que a **forma** está inteira (blocos de exatamente 3, último podendo
   ter 2). Ela não converte. `centesimos_de_moeda`/`inteiro_de_quantidade` convertem.

**Onde os moldes moram, e a forma exata — confirmado abrindo o arquivo.**

`Calibracao.mercado_templates_de_digito: list | None = None` (`calibracao.py:329`), serializado em
`salvar` (`:704`) e lido com `.get` em `carregar` (`:845`). O conteúdo real do
`calibration.json` desta máquina, inspecionado nesta sessão:

```
mercado_templates_de_digito :: 13 itens
  [(',',9,1), ('0',9,4), ('1',9,4), ('2',9,4), ('3',9,4), ('4',9,6), ('5',9,4),
   ('6',9,4), ('7',9,4), ('8',9,4), ('9',9,4), ('Adena',10,35), ('XM Coin',8,44)]
  cada item: {"glifo": "5", "altura": 9, "largura": 4,
              "molde": {"altura": 9, "largura": 4, "bytes": "ffffffffff000000ff…"}}
```

Empacotado por `mercado_visao.glifos_para_calibracao:630` (usa `molde_para_hex:207`), desempacotado
por `mercado_visao.glifos_de_calibracao:667` — que trata a lista como **entrada não confiável** e
confere altura dominante, rótulo repetido e dimensão declarada. [VERIFIED: calibration.json
(inspecionado); l2scanner/calibracao.py:329,704,845; l2scanner/mercado_visao.py:207,630,667]

**Como o conjunto é construído, e QUANTO CUSTA construir um equivalente para o nível.**

O laço é `calibrar_mercado.cortar_glifos:2206`. O usuário **confere um número por vez** — a
ferramenta desenha o retângulo proposto e o ENTER aceita — e cada número confirmado é fatiado em
glifos automaticamente. Medido na docstring: 10 de 10 linhas em `frame_000012` e 6 de 6 em
`frame_000010`, contagens `5,5,5,5,5,5,5,5,5,5` e `6,4,5,4,5,4` batendo caractere a caractere
(`:2220-2228`). Depois, `_conferir_os_glifos:2455` roda a **matriz de confusão** e **recusa gravar**
se os glifos não forem separáveis (`raise MercadoNaoCalibravel("nada foi gravado: os glifos
precisam ser separáveis primeiro")`, `:2485`). E `cobertura_dos_glifos:1113` nomeia os que faltam.

**O custo honesto para o NÍVEL, e é a descoberta cara desta pesquisa:**

- O conjunto tem de ser **completo**. `conjunto_descreve_numeros:312` exige `GLIFOS_DO_NUMERO =
  frozenset("0123456789,")` inteiro, e a docstring mede por que meio conjunto é pior que nenhum:
  um `8` sem molde de `8` casa com `0` a 0,7826 contra piso 0,4698 — *"um `8` viraria `0` com a
  mesma confiança com que hoje um `0` vira `8`"* (`:314-331`).
- **O nível não consegue mostrar dez dígitos.** Ele exibe dois caracteres e muda uma vez por
  sessão, na melhor das hipóteses. Cortar `0-9` da região do nível exigiria dez valores de nível
  diferentes — meses de jogo. Isso não é uma tarefa; é uma impossibilidade prática.
- O contorno seria cortar os moldes de **outra** região com a mesma fonte e a mesma curva tonal (a
  barra inferior tem dígitos variados o tempo todo). Mas o próprio repositório proíbe fundir
  conjuntos de iluminações diferentes com argumento medido: *"fundir moldes cortados de uma aba com
  iluminação diferente entra em `mercado_templates_de_digito`, que é chave de TOPO, e arriscaria o
  conjunto de que a NEGOCIAÇÃO depende"* (`calibrar_mercado.py:3125-3131`). Um `renda_templates_*`
  separado evitaria contaminar o mercado, mas continuaria precisando de que a curva tonal do nível
  (sobre a arte do retrato) e a da barra inferior (sobre fundo escuro chapado) **sejam a mesma** —
  e o spike já mostrou que não são: a barra lê no cru, o nível só lê com `vmin=210`.
- Some-se a geometria: os moldes do mercado têm **9 px de altura**. O crop do nível é `30x20`, o
  da barra `500x26`. Se as alturas de glifo diferirem, `_alinhar_por_preenchimento` põe um dígito
  pequeno dentro de uma caixa grande e o casamento passa a ser dominado por área vazia — o mesmo
  argumento que `_conferir_os_glifos:2469-2473` usa para **nunca** misturar dígitos com palavras
  na mesma matriz.

**Veredito, com a evidência acima:** montar um conjunto de moldes para o nível é um trabalho de
**várias sessões com o jogo aberto e sorte de composição de tela**, não "mais que uma tarefa". A
alternativa que o `CONTEXT.md` registrou — **OCR sobre a máscara `vmin` calibrada** — é o caminho
principal, não o plano B. O spike já mediu que ele funciona (`210 → '66'`). [VERIFIED:
l2scanner/mercado_leitura.py:309-331; l2scanner/calibrar_mercado.py:2206-2265, 2455-2490,
1113-1126, 3123-3133; calibration.json inspecionado]

---

### 3 — As quatro primitivas de gramática, executadas contra as strings da renda

Rodei o parser real do repositório nesta sessão. Resultado bruto:

| entrada | `numero_valido` | `inteiro_de_quantidade` | `centesimos_de_moeda` |
|---|---|---|---|
| `10,673,628` (adena, OCR) | **True** | **10673628** | None |
| `10.673.628` (adena, tela) | False | None | None |
| `13,091` (L-Coin) | True | 13091 | None |
| `58,40` (XM) | True | None | 5840 |
| `66` (nível) | **True** | **66** | None |
| `68,5632` (EXP) | **False** | None | **None** |
| `68.5632` (EXP) | False | None | None |
| `685632` (EXP sem separador) | False | 685632 | None |
| `1234` (milhar perdido) | **False** | 1234 | None |
| `10,673,62` (dígito perdido no fim) | **True** | **None** | 1067362 |

[VERIFIED: execução de `l2scanner.mercado_leitura` nesta sessão, com os literais acima]

**O que é reusável como está:**

- **`numero_valido` (`:606`) — reusável para adena e nível, e é a peneira que pega glifo perdido e
  glifo a mais.** Note `numero_valido("1234") is False`: a vírgula do milhar perdida só aparece
  aqui, e a docstring é explícita sobre isso ser "onde ela ganha o salário" (`:632-637`). A
  docstring também declara o que ela **não** pega: substituição — `0`↔`8` mantém a gramática
  intacta, e o par é o mais estreito do sistema (margem medida 0,0370, `:626-631`). É exatamente o
  argumento a favor do cruzamento de escalas do LEIT-02.
- **`inteiro_de_quantidade` (`:588`) — reusável para adena e nível**, com uma normalização
  `.`→`,` antes. Sozinha ela é insuficiente: aceita `1234`. O par `numero_valido` **e**
  `inteiro_de_quantidade` é complementar e o par é o contrato — `10,673,62` passa numa e cai na
  outra.

**O que NÃO generaliza, e por quê (a pergunta direta do briefing):**

`centesimos_de_moeda` (`:559`) é, sim, o análogo mais próximo de "EXP em décimos de milésimo de
ponto percentual". Mas ela **não generaliza**, e a razão está em três linhas de corpo:

```python
# mercado_leitura.py:565-568
if not texto or "," not in texto:      # exige VÍRGULA. O EXP na tela usa PONTO.
    return None
partes = texto.split(",")
decimal = partes[-1]
if len(decimal) != 2 or not decimal.isdigit():   # trava em DUAS casas.
    return None
```

Além disso ela impõe a gramática de milhar aos grupos anteriores (`len(grupo) != 3`, `:576`), que o
EXP não tem — `68,5632` só tem um grupo inteiro de 2 dígitos e um decimal de 4. Parametrizar
`len(decimal)` mudaria uma função que hoje é chamada no caminho que decide **preço de mercado**,
com 3.823 células medidas por trás dela; o custo de regressão é alto e o ganho é nenhum.

**A resposta honesta é copiar a FORMA, não a função.** A forma que vale copiar:
(a) devolver `int | None`, nunca levantar; (b) a gramática ser **trava de validação e não só
parsing** — a docstring de `centesimos_de_moeda` diz isso com todas as letras: *"um dígito perdido
pelo casamento de molde produz `5,00,000` ou `62,000`, que violam a regra e derrubam a linha - em
vez de virar um número plausível e errado"* (`:569-573`); (c) inteiro escalado, não float.

**`Descarte` (`:1562-1577`) — e aqui há uma correção ao `CONTEXT.md`.** A classe real é:

```python
@dataclass(frozen=True)
class Descarte:
    indice: int
    motivo: str
```

Dois campos, não três. O `detalhe` existe só no **helper** `_recusar(indice, motivo, detalhe)`
(`:2379`), que o escreve no `log.warning` e o joga fora. E a docstring registra a razão da ausência
de rate-limit: *"o log rotativo é a única ferramenta de forense pós-farm do projeto — são
exatamente estas linhas que respondem 'por que não gravou'"* (`:2386-2388`).

Para a renda, `indice: int` (índice de linha da grade do mercado) não significa nada. **Irmã
específica obrigatória:** algo como `RecusaDaRenda(campo: str, motivo: str, detalhe: str)`, com as
constantes de motivo no padrão `MOTIVO_*` de `:1514-1524` (que são strings simples: `"oclusao"`,
`"numero"`, `"cruzamento"`, `"tinta"`, `"faixa-cinzenta"`, `"discordancia-entre-escalas"`).
[VERIFIED: l2scanner/mercado_leitura.py:559-645, 1514-1577, 2379-2390]

---

### 4 — `l2scanner/calibracao.py`: a receita exata para uma feature nova

**A dataclass** (`calibracao.py:181`) é `@dataclass` **mutável** (não frozen), com campos
obrigatórios da party no topo e **todo campo de feature opcional com default `None`**. O padrão,
com o comentário que o justifica, aparece três vezes — `banner_manutencao:249`, `tiat_chat/
tiat_alvo:254-255`, e o bloco de mercado a partir de `:259`:

> *"OPCIONAIS de propósito, e por isso a VERSAO_DO_ESQUEMA SEGUE EM 2 […]: o `carregar` recusa
> qualquer versão diferente da constante, então subir para 3 invalidaria o `calibration.json` que o
> usuário mediu à mão e o obrigaria a recalibrar tudo por causa de campos que ele talvez nem use.
> Uma instalação sem calibração de mercado carrega igual e a feature simplesmente fica OFF."*
> — `calibracao.py:259-266`

**Como o carregamento valida.** `carregar` (`:771`) faz, nesta ordem: existência do arquivo →
`json.loads` com `CalibracaoInvalida` no `JSONDecodeError` → **portão de versão**
(`versao != VERSAO_DO_ESQUEMA` → recusa) → `_conferir_as_chaves_de_mercado(dados)` (`:944`) →
construção com `dados["…"]` para os campos da party e **`dados.get("…")` para todo campo
opcional**. A razão de `.get` está escrita e é dinheiro: *"uma única `dados["..."]` aqui faria o
calibration.json do usuário, que não tem nenhuma delas, levantar KeyError no arranque e levar junto
os 13 moldes de glifo e as 3 âncoras que só a mão dele produz"* (`:851-856`).

Os `_conferir_*` são funções de módulo, puras sobre o `dict` bruto, chamadas do portão único
`_conferir_as_chaves_de_mercado` → `_conferir_as_chaves_da_leitura_de_pagina:1596`. Elas moram no
arranque e não no consumidor, *"porque é no arranque que a mensagem ainda pode dizer 'recalibre'
com o usuário olhando para o console. O consumidor roda às duas da manhã, no meio do farm"*
(`:946-949`). O modelo mais próximo do `renda_vmin_do_nivel` é
`_conferir_o_piso_de_brilho_da_quantidade:1505`: inteiro em `[1, 254]`, `None` passa (feature OFF),
`bool` recusado **explicitamente** porque é subclasse de `int`, e a mensagem carrega o conserto.

**A RECEITA EXATA para acrescentar `renda_*`** — quatro edições, todas em `calibracao.py`:

1. **Declarar no dataclass**, depois do bloco de mercado, com bloco de comentário próprio:
   ```python
   # --- Renda (barra inferior: nível, EXP%, adena) ---
   # OPCIONAIS, VERSAO_DO_ESQUEMA SEGUE EM 2, pela razão já escrita acima.
   # REFERENCIAL: coordenadas do canto da JANELA do jogo, como `hp_proprio`
   # e `tiat_*` — nunca desktop. Ver a seção 6 desta pesquisa.
   renda_nivel: Regiao | None = None
   renda_barra_esquerda: Regiao | None = None
   renda_barra_direita: Regiao | None = None
   renda_vmin_do_nivel: int | None = None
   ```
2. **Serializar em `salvar`** (`:668`) — acrescentar as chaves ao dict literal, com o mesmo
   idioma condicional das irmãs:
   ```python
   "renda_nivel": self.renda_nivel.como_dict() if self.renda_nivel else None,
   "renda_vmin_do_nivel": self.renda_vmin_do_nivel,
   ```
   **Esquecer este passo é o defeito mais caro possível desta fase.** Ver seção 5.
3. **Ler em `carregar`** (`:771`) com `.get`:
   ```python
   renda_nivel=(Regiao.de_dict(dados["renda_nivel"]) if dados.get("renda_nivel") else None),
   renda_vmin_do_nivel=dados.get("renda_vmin_do_nivel"),
   ```
4. **Escrever `_conferir_as_chaves_da_renda(dados)`** no molde de
   `_conferir_o_piso_de_brilho_da_quantidade:1505` e chamá-la de `carregar`, ao lado de
   `_conferir_as_chaves_de_mercado` (`:790`). Para o `vmin`: inteiro, `None` passa, `bool` recusado
   explicitamente, faixa fechada dos dois lados com a razão de cada extremo escrita — `0` faz a
   máscara cheia e todo dígito vira ruído com confiança, `255` faz a máscara vazia e o nível some
   sem uma linha de log. Para as três `Regiao`: dimensão positiva (precedente:
   `_conferir_uma_coluna:1202`).

**`VERSAO_DO_ESQUEMA` fica em 2.** É a decisão que todos os precedentes tomaram, pelo mesmo motivo,
e mudá-la obrigaria o usuário a refazer os 13 moldes de glifo à mão. [VERIFIED:
l2scanner/calibracao.py:23, 181, 249-266, 668-768, 771-900, 944-949, 1505-1548, 1596-1613]

---

### 5 — O RISCO DE NÃO-DESTRUIÇÃO: o defeito citado **não é real**, e o real é outro

Esta é a seção de maior valor da pesquisa. Abri os dois calibradores e segui o caminho de gravação
inteiro dos dois.

#### 5a. O defeito citado (`calibrar_mercado.py:2721`) foi consertado, e há teste prendendo

`grep -n "cal\.mercado_grade\s*="` sobre `l2scanner/` devolve **uma única ocorrência**:

```
l2scanner/calibrar_mercado.py:3182:    cal.mercado_grade = grade
```

Não `:2721` — a linha 2721 hoje está dentro de `_conferir_a_base_do_layout`, uma função de
**recusa antecipada**. E a linha 3182 é inalcançável para uma rodada que não seja de negociação,
porque `:3155` retorna antes:

```python
# calibrar_mercado.py:3155-3166
if not e_negociacao:
    return _gravar_o_layout_aninhado(
        cal, arquivo, layout, grade, caixas_de_coluna, origem,
        cabecalho, limiar_do_cabecalho, conferencia,
    )

# calibrar_mercado.py:3168+  — daqui para baixo é SÓ negociação
tx, ty, tlarg, talt = caixas["titulo"]
cal.mercado_ancora = Regiao(...)
...
cal.mercado_grade = grade          # :3182
```

O conserto tem commit com nome: `f8dbfe2 feat(05-04): o calibrador escreve POR LAYOUT, e --layout
adena deixa de ser bomba`. E tem guarda: `tests/test_calibrar_layout_nao_apaga_negociacao.py`,
cuja docstring descreve o dano exato que o `ROADMAP.md` cita — *"Até 2026-09-01 `calibrar` gravava
as chaves de TOPO incondicionalmente […] qualquer que fosse o `--layout`"* — no **pretérito**.
[VERIFIED: grep sobre l2scanner/; l2scanner/calibrar_mercado.py:3155-3182; git log de
l2scanner/calibrar_mercado.py; tests/test_calibrar_layout_nao_apaga_negociacao.py:1-13]

**Mas o incidente REAL existiu, e foi do outro lado.** `calibrar.py:1300-1345`
(`fundir_com_a_calibracao_em_disco`) documenta: em **2026-08-30** uma rodada de `calibrar.bat`
apagou os 13 moldes de glifo, as 3 âncoras, a grade e o `mercado_limiar_de_glifo`, mais
`banner_manutencao`, `tiat_chat` e `tiat_alvo`. Mecanismo: `calibrar_automatico` montava uma
`Calibracao` **do zero** e o `salvar` gravava o objeto inteiro — *"este caminho era
load-mutate-save SEM o load"*. O arquivo é gitignored (`.gitignore:51`), então o resgate foi
manual: `calibration.RESGATE-13-glifos.json`, que **ainda está na raiz do repositório**.

#### 5b. O caminho de gravação dos dois calibradores, hoje

| Caminho | Load? | Muta o quê | Emite o quê |
|---|---|---|---|
| `calibrar.py --auto/--selecionar` | **Sim, por subtração** — `fundir_com_a_calibracao_em_disco(cal, ARQUIVO_CALIBRACAO):1300`, chamado em `:1596` antes do `salvar:1597` | os 13 campos de `CAMPOS_DA_PARTY:1281`; **todo o resto vem do disco** por `for campo in fields(Calibracao): if campo.name in CAMPOS_DA_PARTY: continue; setattr(...)` (`:1338-1342`) | arquivo inteiro |
| `calibrar.py --tiat` (`calibrar_tiat:1168`) | **Sim, direto** — `Calibracao.carregar(ARQUIVO_CALIBRACAO)` na primeira linha útil (`:1188`) | `cal.janela`, `cal.tiat_chat`, `cal.tiat_alvo` (`:1234-1236`) | arquivo inteiro |
| `calibrar.py --solo` | **Sim** — `Calibracao.carregar` em `:917` | `hp_proprio`, `nome_proprio` | arquivo inteiro |
| `calibrar_mercado.py` (3 pontos de `salvar`: `:2645`, `:2824`, `:3243`) | **Sim** — `Calibracao.carregar(caminho)` em `:718` | só campos `mercado_*`, e vários deles **condicionalmente** (`if cabecalho is not None: … elif cal.mercado_cabecalho_de_coluna: print("Mantido…")`, `:3202-3209`) | arquivo inteiro |

**Resposta direta à pergunta:** os dois calibradores fazem **load → mutate → full re-emit**.
Nenhum escreve dict parcial. A escrita é atômica: `caminho.with_name(nome + ".tmp")` →
`write_text(json.dumps(dados, indent=2, ensure_ascii=False))` → `os.replace`
(`calibracao.py:761-768`), com a razão escrita (*"ou fica o arquivo antigo inteiro, ou o novo
inteiro. Nunca meio"*).

O achado de projeto mais bonito é o de `CAMPOS_DA_PARTY`: a lista enumera o que a party **possui**,
e o preservado sai por **subtração** de `dataclasses.fields(Calibracao)`. O comentário explica por
quê, e é a regra que a renda tem de herdar:

> *"Com uma lista de DONOS, o campo novo nasce PRESERVADO por omissão […]. O default de um campo
> desconhecido tem de ser SOBREVIVER, nunca ser apagado."* — `calibrar.py:1270-1277`

#### 5c. O RISCO REAL desta fase, e ele é o oposto do que o `CONTEXT.md` descreve

`Calibracao.salvar` (`:668-758`) monta `dados` a partir de uma **lista literal de 44 chaves**. Ele
**não** lê o arquivo antigo e **não** preserva chaves desconhecidas. Consequência exata:

> **Se `calibrar_renda.py` escrever `renda_*` diretamente no JSON sem que os campos existam no
> dataclass E no `salvar`, a próxima rodada de QUALQUER outro calibrador — party, tiat, mercado —
> apaga as chaves `renda_*` em silêncio.** E a recíproca: se os campos forem declarados no
> dataclass mas **esquecidos no `salvar`**, o próprio `calibrar_renda.py` grava e some no mesmo ato.

Não achei teste que amarre "toda `field(Calibracao)` aparece em `salvar`". `tests/
test_calibracao_mercado.py` tem `test_ida_e_volta_devolve_os_mesmos_valores:479` e
`test_sem_a_chave_o_campo_sai_None:454`, mas parametrizados por lista de campos escrita à mão — o
mesmo esquecimento que quebraria a renda passaria por eles. **Este é o teste estrutural que a fase
deveria acrescentar e que hoje falta ao repositório inteiro:**

```python
def test_todo_campo_do_dataclass_sobrevive_a_ida_e_volta(tmp_path):
    """Um campo declarado e ESQUECIDO no salvar some sem uma linha de erro."""
    cal = _uma_calibracao_com_todo_campo_preenchido()   # via fields(Calibracao)
    cal.salvar(tmp_path / "c.json")
    dados = json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))
    faltam = [f.name for f in fields(Calibracao) if f.name not in dados]
    assert faltam == [], faltam
```

#### 5d. O padrão que `calibrar_renda.py` DEVE seguir, e o teste que prova

**Padrão (copiado de `calibrar_tiat:1168-1250`, que é o precedente mais curto e mais limpo):**

1. `cal = Calibracao.carregar(ARQUIVO_CALIBRACAO)` **na primeira linha útil**, com `try/except`
   que imprime sem traceback e devolve `1` (`calibrar.py:1187-1191`). Nunca montar `Calibracao`
   do zero — foi assim que o incidente de 2026-08-30 aconteceu.
2. Resolver a janela: `alvo = titulo or cal.janela`, e se nada, `listar_janelas_do_jogo()` com
   recusa quando houver mais de uma (`:1193-1200`).
3. `fonte = JanelaSource(alvo, Regiao(0, 0, 1, 1))` → `time.sleep(0.3)` →
   `pixels = fonte.capturar_completo()` → `finally: fonte.fechar()` (`:1202-1211`).
4. `_selecionar_regiao(pixels, titulo, instrucao)` uma vez por região (`calibrar.py:486`); `None`
   é o ESC do usuário e **preserva o valor anterior**, não zera.
5. **Mutar SÓ `cal.renda_*`.** Nenhum outro atributo. `cal.janela` é o único empréstimo legítimo,
   e `calibrar_tiat` já o faz (`:1234`).
6. `cal.salvar(ARQUIVO_CALIBRACAO)` dentro de `try/except OSError` com mensagem que diz "a
   calibração NÃO foi salva" e o motivo mais comum (`calibrar_mercado.py:3239-3247`).
7. Gravar imagem de conferência com retângulos desenhados, e **conferir o retorno de
   `cv2.imwrite`** — ele devolve `False` em silêncio com o arquivo travado, e o projeto já anunciou
   uma imagem velha por causa disso (`__main__.py:2110-2113`).

**O teste que prova a não-destruição.** O molde é
`tests/test_calibrar_layout_nao_apaga_negociacao.py`, e a docstring dele já derrubou os dois
critérios que pareceriam óbvios:

> *"`git status --porcelain calibration.json` sai VAZIO SEMPRE. O arquivo é gitignored […]. Um
> teste construído sobre ele passaria com a calibração no lixo. […] **O QUE DISCRIMINA é comparar o
> CONTEÚDO PARSEADO antes e depois, chave por chave, com as chaves ENUMERADAS a partir do arquivo
> de ANTES** — assim o caso cobre também as chaves de topo que ainda nem existem."*
> — `tests/test_calibrar_layout_nao_apaga_negociacao.py:16-29`

Os quatro casos, com as chaves exatas a afirmar:

| # | Caso | Asserção |
|---|---|---|
| 1 | **Nenhuma chave mudou de valor.** Semeia um `calibration.json` em `tmp_path` com party + mercado + tiat, roda `calibrar_renda`, compara chave a chave | `{k: (antes[k], depois[k]) for k in antes if k != "renda_*" and antes[k] != depois[k]} == {}` |
| 2 | **Nenhuma chave DESAPARECEU** | `[k for k in antes if k not in depois] == []` |
| 3 | **Os 13 moldes de glifo continuam lá, byte a byte** | `depois["mercado_templates_de_digito"] == antes["mercado_templates_de_digito"]` — e afirmar `len(...) == 13` primeiro, com a mensagem "a fixtura mudou de 13 moldes — retarget" (idioma copiado de `:318-338`) |
| 4 | **CONTROLE POSITIVO** — sem ele os três acima são vácuos: um calibrador que não escrevesse nada passaria com louvor | rodada com retângulos DIFERENTES dos semeados → `depois["renda_barra_esquerda"] != antes["renda_barra_esquerda"]` |

**Disciplina inegociável, herdada dos dois arquivos precedentes:** todo caso monkeypatcha
`l2scanner.calibrar_renda.ARQUIVO_CALIBRACAO` (ou passa `--calibracao`) para dentro de `tmp_path`.
*"É a única coisa que mantém o `calibration.json` da máquina do usuário fora do alcance desta
suíte. Quem remover a linha achando que é ruído reproduz o incidente dentro do CI, e desta vez sem
resgate."* (`tests/test_calibrar_nao_apaga_mercado.py:29-33`)

**E acrescente o caso 5, que nenhum dos dois precedentes tem:** *depois* de `calibrar_renda`
gravar, rodar `calibrar_tiat` (ou o ramo `--auto` da party) e afirmar que **`renda_*` sobreviveu**.
É esse o caso que pega o esquecimento no `salvar` — o risco real da seção 5c.

---

### 6 — Captura: espaço de coordenadas, e a resposta muda o que o spike significa

**A sequência mínima para um leitor de tiro único**, extraída de `mercado_modo.py:427-441` e
`calibrar.py:1202-1211`:

```python
from l2scanner.captura_janela import JanelaSource
from l2scanner.frames import Regiao

# 1. O TÍTULO vem do .bat, que já o monta a partir de [jogo] personagem:
#    ler_personagem_do_jogo() + cliente.SEPARADOR + cliente.NOME_DO_CLIENTE
#    (config.py:831 / cliente.py:50,53). O fonte NUNCA escreve "Yazalaque".
titulo = args.janela

# 2. A janela INTEIRA, relativa=True. O carimbo de tamanho está na calibração.
carimbo = cal.mercado_geometria_da_captura or {}   # {"largura":1720,"altura":1392}
fonte = JanelaSource(
    titulo,
    Regiao(esquerda=0, topo=0, largura=int(carimbo["largura"]), altura=int(carimbo["altura"])),
    relativa=True,
)
frame = fonte.capturar()          # -> Frame(pixels, indice, saude)
janela = frame.pixels             # BGR, (altura, largura, 3)
fonte.fechar()

# 3. Recorte de cada região, em coordenadas DA JANELA:
r = cal.renda_barra_esquerda
recorte = janela[r.topo : r.topo + r.altura, r.esquerda : r.esquerda + r.largura]
```

Alternativa ainda mais curta, para o calibrador e para um comando de leitura única, que é o que
`calibrar_tiat` usa: `JanelaSource(titulo, Regiao(0,0,1,1))` + `time.sleep(0.3)` +
`capturar_completo()` — devolve a janela inteira sem passar pelo recorte
(`captura_janela.py:326-335`; `calibrar.py:1203-1205`). Vantagem: não precisa do carimbo de
geometria do mercado, que é do outro workstream.

**A resposta à pergunta que "importa enormemente": o frame é RELATIVO À JANELA.**

O cabeçalho de `captura_janela.py:13-18` declara a diferença como uma das duas que moldam o módulo:
*"**O referencial das coordenadas muda.** A calibração está em coordenadas de DESKTOP; o frame da
WGC começa no canto da JANELA."* E `capturar():380` implementa os dois modos:

```python
# captura_janela.py:396-402
if self._relativa:
    x, y = self._regiao.esquerda, self._regiao.topo          # já é janela
else:
    ox, oy = origem_da_janela(self._hwnd)                    # DWM, não GetWindowRect
    x = self._regiao.esquerda - ox
    y = self._regiao.topo - oy
```

**E os números do spike?** O script que os produziu está na raiz do repo, não rastreado:
`_olhar_tela.py` faz `sct.grab({"left": 0, "top": 0, "width": 1700, "height": 1400})` — um grab de
**desktop** por `mss`. Portanto os números são, formalmente, coordenadas de desktop. **Mas eles
coincidem com coordenadas de janela**, e a evidência é aritmética:

| evidência | número | fonte |
|---|---|---|
| grab do spike | `0,0 1700x1400` | `_olhar_tela.py:18` |
| janela do jogo carimbada | `1720 x 1392` | `calibration.json → mercado_geometria_da_captura` |
| barra direita do spike | `1230 + 470 = 1700` — **exatamente a largura do grab** | spike |
| barra esquerda/direita, y | `1368 + 26 = 1394` ≈ altura da janela `1392` | spike vs carimbo |
| nível do spike | `246,736 30x20` | spike |
| `hp_proprio` (declarado **relativo à janela**, `calibracao.py:200-206`) | `298,711 182x24` | `calibration.json` |

O nível cai 52 px à esquerda e 25 px abaixo do canto do `hp_proprio` — exatamente "sob o retrato",
ao lado da barra de HP própria. Uma janela de 1720×1392 posicionada no canto `(0,0)` do desktop
reproduz **todos** esses números. **Conclusão:** durante o spike a janela do jogo estava em
`(0,0)`, e as coordenadas medidas são utilizáveis diretamente como **valores iniciais
janela-relativos**. A história do roadmap ("digitar os números do spike no calibrador") **continua
de pé**. [VERIFIED: _olhar_tela.py:16-18; calibration.json (inspecionado);
l2scanner/calibracao.py:200-206; l2scanner/captura_janela.py:13-18, 396-402]

**Duas ressalvas que o plano tem de escrever, porque a coincidência é frágil:**

1. A barra direita foi medida **encostada na borda do grab** (`1230+470 = 1700`), e a janela tem
   1720 px. **Faltam ~20 px de barra que o spike nunca viu.** Se a adena estiver colada à direita,
   o recorte do spike pode estar cortando dígito. Isso é uma **hipótese, não uma medição** — e
   explicaria por que a leitura saiu íntegra mesmo assim (o `[adena]` fica antes do fim). O
   calibrador tem de deixar o usuário esticar até a borda.
2. `calibration.json` de hoje diz `party_window.esquerda = 1738` e
   `party_window_na_janela.esquerda = 18` → origem de janela `x = 1720`. Ou seja: **a janela
   calibrada hoje NÃO está em (0,0)**. O spike foi feito na outra instância, ou depois de arrastar
   a janela. Isso não invalida nada — só confirma que os números são ponto de partida e que
   guardar em **coordenadas de janela** é a decisão certa, porque arrastar o jogo deixa de custar
   uma recalibração.

**Decisão que cai fora disso, e é para o plano escrever no fonte:** guardar `renda_*` em
coordenadas **de janela** (`relativa=True`), pelo precedente de `tiat_*`, `hp_proprio` e
`party_window_na_janela`, e não pelo de `party_window`. `origem_da_janela` usa
`DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS)` e não `GetWindowRect`, com 7 px de diferença
medidos (`captura_janela.py:179-192`) — mais um motivo para não passar por desktop de graça.

**Personagem:** `cliente.nome_do_personagem(titulo)` (`cliente.py:111-117`) faz
`titulo.rsplit(" - ", 1)[0].strip()`. `cliente.esta_na_tela_de_login(titulo)` (`:92`) compara
**exatamente** com `"XM Essence"` — e a docstring diz por que não é `endswith`. Os dois já dão o
campo `personagem` que o REG-04 vai gravar na Fase 2. [VERIFIED: l2scanner/cliente.py:50-117]

---

### 7 — A convenção dos `.bat`

Li os quatro relevantes. Há **dois dialetos**, e a escolha importa.

**Dialeto A — completo (`vigiar-mercado.bat`, 150 linhas).** Procura o Python em cinco lugares,
rejeita o stub da Microsoft Store por substituição de string nativa do `cmd`, cria o `.venv` na
primeira execução, roda `pip install -r requirements.txt`, sonda os imports
(`mss,cv2,numpy,windows_capture,winrt.windows.media.ocr,winrt.windows.graphics.imaging`), monta o
título por um `python -c` embutido, e **põe os blocos de erro ANTES da linha de execução** — com a
razão escrita: *"não é estilo: é o que torna ESTRUTURAL a promessa de que nada é impresso depois de
o programa rodar"*.

**Dialeto B — mínimo (`calibrar-tiat.bat`, 30 linhas).** Assume que o `.venv` existe, e se não
existir manda rodar `vigiar-party.bat` uma vez:

```bat
@echo off
setlocal
REM ==== bloco de comentário que ENSINA o usuário ====
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo.& echo  O ambiente ainda nao foi preparado.& echo  Rode vigiar-party.bat uma vez primeiro.& echo.
    pause & exit /b 1
)
".venv\Scripts\python.exe" -m l2scanner.calibrar --tiat %*
echo.
pause
```

**`calibrar-renda.bat` deve ser o dialeto B**, mais duas coisas que `calibrar-mercado.bat` ensina:

1. **`%*` repassado**, e o bloco de conferência **guardado por `if errorlevel 1`**. O
   `calibrar-mercado.bat` traz o defeito medido por escrito: *"uma chamada sem argumento (ou uma
   recusa da matriz de confusão) imprimia mesmo assim 'ABRA a imagem de conferência' — mandando o
   usuário conferir um arquivo que nunca foi gerado"*.
2. **Não citar o nome da imagem de conferência no `.bat`.** `calibrar-mercado.bat` explica: o
   `.bat` não sabe qual foi, porque `_gravar_conferencia` cai para um nome com horário quando o
   arquivo padrão está travado no visualizador de fotos. Citar o nome de sempre manda o usuário
   **validar a rodada nova olhando a imagem da anterior**.
3. **Cabeçalho `REM` que ensina.** Todos os quatro têm. É a única documentação que o usuário lê.

Como `calibrar-renda.bat` precisa de `--janela` (a mira é obrigatória, Área 5), ele tem duas
opções: (a) copiar o bloco de resolução de título do `vigiar-mercado.bat` — 12 linhas, incluindo o
`for /f` com o `python -c` sem aspas simples; ou (b) confiar em `cal.janela`, que
`calibrar_tiat:1193` já usa como padrão (`alvo = titulo or cal.janela`). **A (b) é mais barata e
já é precedente**; a (a) só se paga se o usuário quiser calibrar a instância que **não** é a da
calibração de party. [VERIFIED: calibrar-tiat.bat; calibrar-mercado.bat; calibrar.bat;
vigiar-mercado.bat — os quatro lidos integralmente]

---

### 8 — Convenções de teste

**Naming.** `tests/test_<assunto>.py`, 102 arquivos. Duas famílias de nome: descritiva
(`test_mercado_leitura.py`, `test_calibracao_mercado.py`) e **de invariante em forma de frase**
(`test_calibrar_nao_apaga_mercado.py`, `test_calibrar_layout_nao_apaga_negociacao.py`,
`test_desativar_solo_boss.py`). O teste de não-destruição desta fase pertence à segunda família:
`tests/test_calibrar_renda_nao_apaga_nada.py`.

Nomes de teste são **frases em português**, longas, afirmando a invariante e não a mecânica —
`test_nenhuma_chave_de_topo_de_mercado_mudou_de_valor`, `test_os_TREZE_moldes_de_glifo_continuam_la`,
`test_o_CONTROLE_NEGATIVO_cortar_glifos_roda_na_negociacao`. **Maiúsculas para ênfase** no meio do
nome é convenção da casa. Classes `TestXxx` agrupam por invariante, não por função.

**Docstring de módulo é obrigatória e longa.** Ela nomeia o incidente ou o dano que o arquivo
existe para impedir, e frequentemente **derruba explicitamente critérios plausíveis mas vácuos**
(ver o bloco de `test_calibrar_layout_nao_apaga_negociacao.py:16-29` citado na seção 5d). Isso não
é enfeite — é a diferença entre o teste sobreviver ao próximo mantenedor e ser "simplificado".

**Fixtures de imagem: sim, versionadas, em `tests/fixtures/<assunto>/`.** 107 arquivos, 9
subpastas: `mercado/`, `manutencao/`, `identidade/`, `cliente/`, `gameplay/`, `barra_propria/`,
`sessao_morte_e_ressurreicao/`, `party_estavel_com_vazamento/`,
`barras_vazias_estado_desconhecido/`. Nomes carregam a proveniência:
`glifos_precos_f010.png`, `janela_negociacao_f005.png`, `banner_40min26s.png`. E o motivo de serem
**resgatadas** de `recordings/` em vez de lidas de lá está escrito:

> *"Tudo aqui roda sobre duas fixtures RESGATADAS de uma gravação de verdade
> (`recordings/20260828-060622-mercado-pagina-cheia/frame_000010.png`), e nunca sobre
> `recordings/` — a pasta é gitignored e não vem de clone limpo, então um teste que dependesse dela
> ficaria verde nesta máquina e amarelo em toda outra."* — `tests/test_mercado_glifos.py:4-8`

Há também uma **semente de calibração versionada**: `tests/fixtures/mercado/
calibracao_de_fixture.json` — o molde exato de que a renda precisa.

**Como um teste fornece um frame falso.** Três idiomas, todos por *duck typing* na porta
`FrameSource`, sem `Mock`:

```python
# tests/test_mercado_modo.py:126  — a porta capturar() -> Frame
class FonteFalsa:
    def __init__(self, quadros): self._quadros = list(quadros); self._indice = 0; self.fechada = False
    def capturar(self) -> Frame:
        if self._indice >= len(self._quadros): raise StopIteration
        pixels = self._quadros[self._indice]; self._indice += 1
        return Frame(pixels=pixels, indice=self._indice, saude=SaudeDoFrame.OK)
    def fechar(self): self.fechada = True

# tests/test_calibrar_nao_apaga_mercado.py:413  — a porta capturar_completo() -> ndarray
class _JanelaFalsa:
    def capturar_completo(self): return self._pixels
```

Para o calibrador, o monkeypatch é triplo: `JanelaSource` → `_JanelaFalsa`, `_selecionar_regiao` →
função que devolve o retângulo semeado, e `_gravar_conferencia` → no-op. O precedente completo está
em `tests/test_calibrar_layout_nao_apaga_negociacao.py:169-240` (`_rodar`, `_selecao_falsa`,
`_bomba`, `_fala`).

**`conftest.py`** só cala o log nativo do OpenCV, por uma razão medida (avisos nativos vazando para
dentro do índice da gravação em ~metade das rodadas). Não há fixtures compartilhadas — cada arquivo
monta as suas. [VERIFIED: tests/ (listado); tests/conftest.py:1-56; tests/test_mercado_glifos.py:1-40;
tests/test_mercado_modo.py:126-150; tests/test_calibrar_layout_nao_apaga_negociacao.py:1-70,114-240]

---

## Padrões de arquitetura

### Diagrama do fluxo

```
  config.toml [jogo] personagem          calibration.json (44 chaves + renda_*)
            │                                        │
   ler_personagem_do_jogo()                Calibracao.carregar()
   + cliente.SEPARADOR                     ├─ portão de versão (== 2)
   + cliente.NOME_DO_CLIENTE               ├─ _conferir_as_chaves_de_mercado
            │                              └─ _conferir_as_chaves_da_renda  ◄── NOVO
     "Yazalaque - XM Essence"                        │
            │                                        │
            └──────────► JanelaSource(titulo, Regiao(0,0,L,A), relativa=True)
                                 │  WGC ~38 fps, guarda o mais recente
                                 ▼
                          frame.pixels  (BGR, coordenadas DA JANELA)
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
       renda_nivel        renda_barra_esq    renda_barra_dir
        (30x20)              (500x26)            (470x26)
              │                  │                  │
     mascara_de_numero      ocr.ler_texto (2x)  ocr.ler_texto (2x)
     (vmin calibrado)       ocr.ler_texto_ampl. (3x)      │
              │                  │  as duas têm de        │
       OCR sobre a máscara       │  dar o MESMO inteiro   │
       (ou ler_celula, se        ▼                        ▼
        houver moldes)      extrai \d{1,3}[.,]\d{4}%   extrai o último
              │             → décimos de milésimo      grupo de milhar
              │                    (int)                     │
              ▼                    ▼                         ▼
        numero_valido        gramática NOVA          normaliza "."→","
      inteiro_de_quantid.    (irmã de                numero_valido
              │              centesimos_de_moeda)    inteiro_de_quantidade
              │                    │                         │
              └────────────────────┼─────────────────────────┘
                                   ▼
                 LeituraDaRenda(personagem, nivel, exp_em_decimos_de_milesimo,
                                adena, carimbo)          ← tudo INTEIRO
                                   │
                                   └─ ou ─► RecusaDaRenda(campo, motivo, detalhe)
                                            + log.warning com >>>texto<<<
```

**A Fase 1 termina na caixa de baixo.** Nenhuma taxa, nenhum arquivo, nenhum laço — é o que o
`<domain>` do `CONTEXT.md` fecha, e é o que torna a fase verificável sem o jogo aberto.

### Estrutura de arquivos recomendada

```
l2scanner/
├── renda_leitura.py      # PURO. frame+Calibracao -> LeituraDaRenda | RecusaDaRenda.
│                         #   Não abre janela, não lê teclado, não escreve arquivo,
│                         #   não tem relógio. Charter idêntico ao de mercado_leitura.py.
├── calibrar_renda.py     # FERRAMENTA. Importa cv2 com janela, chama selectROI.
│                         #   A seta aponta ferramenta -> puro, NUNCA o contrário.
└── calibracao.py         # +4 campos, +4 linhas em salvar, +4 em carregar, +1 validador.

tests/
├── test_renda_leitura.py                  # o transform puro, contra fixtures
├── test_calibrar_renda_nao_apaga_nada.py  # a invariante do arquivo compartilhado
└── fixtures/renda/
    ├── barra_esquerda_<data>.png          # RESGATADAS, nunca lidas de recordings/
    ├── barra_direita_<data>.png
    ├── nivel_<data>.png
    └── calibracao_de_fixture.json         # molde: tests/fixtures/mercado/…

calibrar-renda.bat                          # dialeto B (calibrar-tiat.bat) + guarda de errorlevel
```

### Padrão 1 — O charter do módulo puro

`mercado_leitura.py:1-25` é o texto a imitar, e a razão é operacional e não estética:

> *"A razão NÃO é estética: `calibrar_mercado.py` chama `tornar_consciente_de_dpi()` NO IMPORT e
> carrega `argparse` e as chamadas de JANELA do OpenCV. Um módulo de produção que o importasse
> pagaria esse efeito colateral só por existir, e uma janela de conferência acabaria abrindo dentro
> do tick de captura."*

E há um **teste de fonte** prendendo isso: `tests/test_mercado_leitura.py` varre o arquivo inteiro
atrás de nomes de chamada de janela, **inclusive em comentário** — *"um teste de fonte que aceitasse
menção em comentário deixaria de pegar a chamada de verdade no dia em que ela entrasse comentada e
fosse descomentada"*. O `renda_leitura.py` merece o mesmo guarda.

### Padrão 2 — Limiar por parâmetro, sem valor de fábrica

Regra escrita em `mercado_leitura.py:34-44`:

> *"`piso`, `margem`, o limiar de dispersão da sonda e o limiar do cabeçalho vêm todos do
> `calibration.json`, medidos no frame do próprio usuário. **Nenhum deles tem default**: um default
> é um número mágico que entra por omissão, e este projeto já perdeu uma medição assim
> (`MINIMO_PARA_PROPOR_ROTULO = 0.95` deixava a ferramenta muda e ninguém saberia)."*

Mecanicamente: parâmetro **somente-nomeado** (`*,`) e sem default — ver `ler_celula:992-999`. Vale
para `vmin_do_nivel` e para qualquer piso que o `renda_leitura` receba.

### Padrão 3 — Recusa nomeada, com o texto no log e o motivo no dado

```python
# a forma, de mercado_leitura.py:2379-2390
def _recusar(campo: str, motivo: str, detalhe: str) -> RecusaDaRenda:
    log.warning("campo %s RECUSADO (%s): %s", campo, motivo, detalhe)
    return RecusaDaRenda(campo=campo, motivo=motivo, detalhe=detalhe)
```

Os delimitadores `>>><<<` em torno do texto lido são obrigatórios ("`Lv. 1` e `Lv.1` são leituras
diferentes"), e **não há rate-limit**, porque o log rotativo é a única forense pós-farm do projeto.

### Antipadrões a evitar

- **Montar `Calibracao` do zero num calibrador.** Foi o incidente de 2026-08-30 (`calibrar.py:1305-1312`).
- **Colapsar as duas escalas de OCR "para economizar 23 ms".** `ocr.py:64-70` já avisa: *"estará
  economizando o que não aperta e gastando a única guarda que pega erro de método."*
- **Completar decimal com zero.** `68,56%` → `68,5600` é uma mentira de 0,0032 que ninguém vê
  depois. Decisão travada no `CONTEXT.md`.
- **Usar `float` para o EXP.** Precedente `total_em_centesimos`; a diferença entre amostras é o
  produto inteiro da milestone.
- **Ler o valor de `cv2.imwrite` como sucesso sem conferir.** Devolve `False` em silêncio com o
  arquivo aberto no visualizador de fotos — já mordeu o projeto (`__main__.py:2110-2113`).
- **Depender de `recordings/`** num teste: gitignored, verde nesta máquina e amarelo em toda outra.

---

## Não construir à mão

| Problema | Não escreva | Use | Por quê |
|---|---|---|---|
| Achar a janela do jogo | `EnumWindows` próprio | `captura_janela.achar_janela:61` / `listar_janelas_do_jogo:123` | Já filtra por `l2.bin` (`:93`) e por título |
| Origem da janela | `GetWindowRect` | `origem_da_janela:179` | 7 px de borda invisível **medidos**; usa DWM |
| Capturar a janela coberta | `PrintWindow`/`BitBlt` | `JanelaSource` | D3D devolve preto; validado no spike 001 (443 de 456 frames distintos) |
| Máscara de brilho | `cv2.inRange` novo | `mascara_de_numero:155` | Idêntico, com o piso já parametrizado e a guarda de recorte vazio |
| Gramática de milhar | regex própria | `numero_valido:606` | Pega glifo perdido E glifo a mais; a docstring declara o que ela **não** pega |
| Milhar → int | `int(t.replace(",",""))` | `inteiro_de_quantidade:588` | O `replace` aceita `1234` e `1,0000`; a função recusa |
| Escrita do JSON | `caminho.write_text` | `Calibracao.salvar:668` | Atômica por `.tmp` + `os.replace`; um JSON truncado derruba **o scanner de party inteiro** |
| Preservar chaves de outra feature | `dict.update` no JSON | load → mutate → `cal.salvar` | O `salvar` é lista literal: só sobrevive o que está no dataclass **e** no `salvar` |
| Detectar tela de login | `title.endswith("XM Essence")` | `cliente.esta_na_tela_de_login:92` | `endswith` casaria `Faerlina - XM Essence`, o oposto do desejado |
| Extrair o personagem | `title.split("-")[0]` | `cliente.nome_do_personagem:111` | `rsplit(" - ", 1)`, e nomes não têm espaço |

**A intuição central:** neste repositório, cada uma dessas funções carrega uma **medição** na
docstring que a versão à mão não teria. Reescrever é jogar a medição fora e descobrir o mesmo
defeito de novo às 4 da manhã.

---

## Inventário de estado em runtime

Esta fase não renomeia nada, mas **escreve num arquivo compartilhado por quatro features**, o que a
coloca na mesma classe de risco.

| Categoria | O que foi achado | Ação exigida |
|---|---|---|
| **Dados armazenados** | `calibration.json` na raiz, **44 chaves de topo**, gitignored (`.gitignore:51`). Contém 13 moldes de glifo brancos + 13 cianos + 3 âncoras que **só a mão do usuário produz**. Já foi destruído uma vez (2026-08-30); o resgate manual `calibration.RESGATE-13-glifos.json` ainda está na raiz, junto de 5 outros `.bak`/rascunhos. | Load → mutate `renda_*` → full re-emit, provado por teste com controle positivo |
| **Config de serviço vivo** | Nenhum. Esta fase não fala com Chatwoot, Discord nem n8n. | Nenhuma |
| **Estado registrado no SO** | Nenhum. Os `.bat` são invocados à mão pelo usuário; não há Task Scheduler nem pm2 nesta árvore. | Nenhuma |
| **Segredos / variáveis de ambiente** | Nenhum tocado. O token do Chatwoot vive fora deste caminho. | Nenhuma |
| **Artefatos de build** | `.venv/` montado pelos `.bat`; nenhuma dependência nova → nenhum `pip install` novo. `__pycache__` normal. | Nenhuma |

**Pergunta canônica respondida:** depois de a fase escrever `renda_*`, o único sistema que ainda
carrega estado é o `calibration.json` — e o risco não é que a renda o corrompa, é que **outro
calibrador apague o que a renda escreveu**, porque `salvar` é enumeração literal. Ver seção 5c.

---

## Armadilhas comuns

### Armadilha 1 — Escrever `renda_*` sem declarar no `salvar`

**O que dá errado:** as chaves somem na próxima rodada de qualquer outro calibrador, sem uma linha
de log. **Por que acontece:** `Calibracao.salvar:668` monta um dict literal de 44 chaves e não
preserva desconhecidas. **Como evitar:** as quatro edições da seção 4, na ordem, mais o teste
estrutural `test_todo_campo_do_dataclass_sobrevive_a_ida_e_volta`. **Sinal de alarme:** rodar
`calibrar-renda.bat` e depois `calibrar-tiat.bat`, e o `renda_*` sumir.

### Armadilha 2 — Achar que `ler_texto` é 1x

**O que dá errado:** o plano escreve "cruzamento 1x × 2x" e o executor descobre que não há entrada
pública em 1x — ou, pior, chama `ocr._ler(pixels, 1)` e recebe `None` sempre, interpretando como
"campo vazio". **Por que acontece:** o `CONTEXT.md` e o spike rotularam as escalas errado.
**Como evitar:** o par é `ler_texto` (2x) × `ler_texto_ampliado` (3x). **Sinal:** uma das escalas
abstendo em 100% das leituras.

### Armadilha 3 — Reusar `centesimos_de_moeda` para o EXP

**O que dá errado:** `None` em toda leitura, e o EXP vira "recusa permanente". **Por quê:**
`len(decimal) != 2` (`:568`) e exigência de vírgula (`:566`). **Como evitar:** irmã própria.
**Sinal:** medido nesta sessão — `centesimos_de_moeda("68,5632") is None`.

### Armadilha 4 — Confiar no caractere separador

O jogo, segundo a transcrição do spike, escreve `68.5632%` (decimal com **ponto**), `58,40`
(decimal com **vírgula**) e `10.673.628` (milhar com **ponto**) **na mesma barra**; o OCR devolveu
`58,40 13,091 10,679,769` — vírgula em tudo. Não há documentação de que `Windows.Media.Ocr` faça
normalização de locale (pesquisa feita, nada encontrado); a leitura mais econômica é **confusão de
glifo**: num texto de 26 px a cauda que separa vírgula de ponto tem ~1 px, e "OCR não consegue
sempre distinguir ponto de vírgula" é falha documentada de forma genérica na indústria.
**Consequência de projeto:** a gramática tem de ser **posicional** (contagem de dígitos), não
baseada no caractere. `[.,]` na regex, e a decisão sai do **número de dígitos depois do separador**:
4 → EXP; 3 → milhar. **Sinal de alarme:** um EXP validado com 3 casas.

### Armadilha 5 — `vmin` do nível errado por 20 devolve dígito ERRADO, não vazio

Medido no spike: `170 → ''`, `190 → '6b'`, `210 → '66'`. `'6b'` não é falha de leitura, é uma
leitura errada com forma plausível. **Prevenção:** a gramática (`numero_valido('6b') is False`,
porque `'6b'.isdigit()` é falso) **pega este caso**, mas só porque o caractere errado não é dígito.
Um `'68'` onde a tela diz `'66'` passaria. **Por isso o calibrador precisa de feedback visual** —
e por isso a monotonicidade do nível (só sobe, nunca desce, nunca pula) é uma guarda barata que
vale escrever já na Fase 1, como regra pura sobre um par de leituras.

### Armadilha 6 — Testar contra `recordings/`

Gitignored. Verde aqui, amarelo em qualquer clone. **Resgate as fixtures** para
`tests/fixtures/renda/` e cite a gravação de origem na docstring, como
`tests/test_mercado_glifos.py:4-8` faz.

### Armadilha 7 — O recorte direito do spike encosta na borda do grab

`1230 + 470 = 1700` = largura exata do `mss.grab` de `_olhar_tela.py`. A janela tem 1720 px.
**~20 px de barra nunca foram vistos.** Assumido, não medido. O calibrador tem de permitir esticar
até a borda da janela.

---

## Exemplos de código

### A leitura de tiro único, ponta a ponta

```python
# Fonte: composição de calibrar.py:1202-1211 e mercado_modo.py:427-441
import time
from l2scanner.calibracao import Calibracao
from l2scanner.calibrar import ARQUIVO_CALIBRACAO
from l2scanner.captura_janela import JanelaSource
from l2scanner.cliente import nome_do_personagem
from l2scanner.frames import Regiao

cal = Calibracao.carregar(ARQUIVO_CALIBRACAO)     # já valida e já recusa alto
fonte = JanelaSource(args.janela, Regiao(0, 0, 1, 1))
try:
    time.sleep(0.3)                                # a WGC precisa entregar um frame
    janela = fonte.capturar_completo()             # BGR, coordenadas DA JANELA
finally:
    fonte.fechar()

if janela is None or janela.size == 0:
    return _recusar("frame", MOTIVO_SEM_FRAME, "nenhum frame utilizavel — minimizada?")

def recorte(r: Regiao):
    return janela[r.topo : r.topo + r.altura, r.esquerda : r.esquerda + r.largura]

leitura = ler_a_renda(
    nivel=recorte(cal.renda_nivel),
    esquerda=recorte(cal.renda_barra_esquerda),
    direita=recorte(cal.renda_barra_direita),
    vmin_do_nivel=cal.renda_vmin_do_nivel,
    personagem=nome_do_personagem(args.janela),
)
```

### O cruzamento de duas escalas, para o EXP

```python
# Fonte: a FORMA de manutencao.py:814-820 + o log de mercado_leitura.py:2349-2360
from l2scanner import ocr

def exp_da_barra(recorte) -> int | RecusaDaRenda:
    """Décimos de milésimo de ponto percentual, ou recusa. Nunca levanta."""
    barato = ocr.ler_texto(recorte)            # 2x  — ocr.py:80,172
    a = _decimos_de_milesimo(barato)
    if a is None:
        return _recusar("exp", MOTIVO_DA_GRAMATICA, f"2x=>>>{barato}<<<")

    caro = ocr.ler_texto_ampliado(recorte)     # 3x  — ocr.py:81,186
    b = _decimos_de_milesimo(caro)
    if b is None:
        return _recusar("exp", MOTIVO_DA_DISCORDANCIA,
                        f"so a 2x leu. 2x=>>>{barato}<<< 3x=>>>{caro}<<<")
    if a != b:
        return _recusar("exp", MOTIVO_DA_DISCORDANCIA,
                        f"2x=>>>{barato}<<< ({a}) 3x=>>>{caro}<<< ({b})")
    return a
```

### A gramática nova — irmã, não parametrização

```python
# Fonte: a FORMA de mercado_leitura.centesimos_de_moeda:559-586.
# NÃO reusa aquela função: ela trava len(decimal)==2 (:568) e exige vírgula (:566).
import re

_FORMA_DO_EXP = re.compile(r"(\d{1,3})[.,](\d{4})%")

def decimos_de_milesimo(texto: str | None) -> int | None:
    """`68.5632%` -> 685632. `None` para tudo que não respeita a gramática.

    QUATRO CASAS OU NADA. Três casas, cinco casas ou ausência do `%` são
    RECUSA, nunca arredondamento e nunca completar com zero: um `68,56%`
    tratado como `68,5600` é uma mentira de 0,0032 de EXP que ninguém consegue
    ver depois de gravada.

    O SEPARADOR É `[.,]` PORQUE ELE NÃO CARREGA SEMÂNTICA NESTA TELA. Medido no
    spike: o jogo escreve `68.5632%` e `58,40` na mesma barra, e o OCR devolveu
    `10,679,769` para `10.673.628` na tela. Quem decide é a CONTAGEM de dígitos
    depois do separador, e não o caractere.
    """
    if not texto:
        return None
    achado = _FORMA_DO_EXP.search(texto)
    if achado is None:
        return None
    return int(achado.group(1)) * 10_000 + int(achado.group(2))
```

### A adena, reusando o que já existe

```python
# Fonte: execução real de mercado_leitura nesta sessão.
#   numero_valido("10,673,628") is True ; inteiro_de_quantidade(...) == 10673628
from l2scanner.mercado_leitura import inteiro_de_quantidade, numero_valido

def adena_da_barra(texto: str | None) -> int | None:
    """O ÚLTIMO grupo de milhar da barra direita.

    A NORMALIZAÇÃO É `.`->`,` E NÃO O CONTRÁRIO, porque as duas funções do
    mercado falam VÍRGULA (`inteiro_de_quantidade` faz `texto.split(",")`,
    mercado_leitura.py:592).

    O PAR É COMPLEMENTAR, E NENHUMA DAS DUAS BASTA SOZINHA — medido:
      numero_valido("1234") is False        <- a vírgula do milhar perdida
      inteiro_de_quantidade("1234") == 1234 <- ela sozinha ACEITARIA
      numero_valido("10,673,62") is True    <- ela sozinha ACEITARIA
      inteiro_de_quantidade("10,673,62") is None
    """
    if not texto:
        return None
    candidato = _ultimo_grupo(texto).replace(".", ",")
    if not numero_valido(candidato):
        return None
    return inteiro_de_quantidade(candidato)
```

---

## Estado da arte

| Abordagem antiga | Abordagem atual | Quando mudou | O que significa aqui |
|---|---|---|---|
| `ocr` 1x como escala de detecção | 2x detecta, 3x confere | documentado em `ocr.py:33-70`, com a tabela antiga mantida **refutada** no fonte | Não escreva "1x" no plano |
| Calibrador monta `Calibracao` do zero | Load-mutate-save em todos os caminhos | party: `fundir_com_a_calibracao_em_disco` (após o incidente de 2026-08-30); mercado: CR-04 | O calibrador da renda nasce já correto |
| `--layout adena` regravava chaves de topo | Early-return para `_gravar_o_layout_aninhado` | `f8dbfe2`, "…deixa de ser bomba" | **O defeito citado pelo roadmap não existe mais** |
| `mercado_templates_de_nome` cortado à mão | Nome lido por OCR + agrupamento por similaridade | 2026-08-29 (`calibrar_mercado.py:3225-3230`) | Precedente forte de **abandonar moldes** quando o OCR resolve — exatamente a decisão que o nível enfrenta |
| Um conjunto de moldes | Dois (acromático + cromático), com `moldes_da_tinta` como seletor | `e09a860` | Se a renda precisar de moldes, ela precisa de **chave própria**, nunca fundir com a do mercado |

**Depreciado / que não existe apesar de citado:**
- `tools/pick_region.py` — **não existe**. O `CLAUDE.md` e o `CONTEXT.md` o citam.
- `tools/record.py` — **não existe**. Gravação é a flag `--record` de `l2scanner/__main__.py:2874`.
- `tools/calibrate_hsv.py` (trackbar HSV) — **não existe**. O `CLAUDE.md` o descreve como "construa
  na Fase 1"; ninguém construiu.
- `rich` — **não está em `requirements.txt` nem é importado em lugar nenhum de `l2scanner/`**.

---

## Ambiente

| Dependência | Exigida por | Disponível | Versão | Alternativa |
|---|---|---|---|---|
| Python 3.13 (64-bit) | tudo | ✓ (a suíte roda no Python global, 3.12 nos `.pyc`) | — | — |
| `mss`, `opencv-python<5`, `numpy` | recorte e máscara | ✓ declarados | `>=10.2 / >=4.10,<5 / >=2.0` | — |
| `windows-capture` | `JanelaSource` | ✓ declarado | `>=1.4` | nenhuma; é a única API que vê janela coberta |
| 6× `winrt-*` | `ocr.py` | ✓ declarados, e o `CONTEXT.md` registra `disponivel() == True` nesta máquina | `>=3.2.1` | `mercado_leitura.ler_celula` com moldes — mas ver o custo dos moldes |
| Pacote de idioma `en-US` em `C:\Windows\OCR` | `OcrEngine` | assumido presente (o `ocr.py:96-99` fala dele no texto de conserto) | — | `try_create_from_user_profile_languages()` já é o fallback (`ocr.py:135-137`) |
| `rich` | — | **✗ e NÃO é necessário** | — | O console do projeto é ANSI cru (`console.py:21-26`) |

**Faltando sem alternativa:** nada.
**Faltando com alternativa:** nada nesta fase. (`rich` faltando importa para a **Fase 3**, não para
esta — mas está registrado aqui porque o `ROADMAP.md` o dá como presente.)

---

## Domínio de segurança

`security_enforcement: true`, `security_asvs_level: 1`. Esta fase não tem rede, não tem
autenticação, não tem sessão, não tem persistência de dado de usuário e não tem superfície de
serviço. As categorias ASVS que se aplicam de verdade são duas.

| Categoria ASVS | Aplica | Controle padrão neste repositório |
|---|---|---|
| V2 Autenticação | não | sem identidade |
| V3 Sessão | não | sem sessão |
| V4 Controle de acesso | não | processo local do próprio usuário |
| **V5 Validação de entrada** | **sim** | `calibration.json` é **entrada não confiável**: portão de versão + `_conferir_*` no `carregar`, `Regiao.de_dict` com `int()` explícito, `glifos_de_calibracao` conferindo dimensão declarada contra bytes reais. A renda herda isso escrevendo `_conferir_as_chaves_da_renda`. |
| V6 Criptografia | não | nada cifrado nesta fase |
| **V12/V5 Path handling** | **sim (fraco)** | O calibrador escreve num caminho derivado de `RAIZ` (`calibrar.py:68`) e nos temporários `.tmp` ao lado. Nenhum caminho vem de entrada do usuário além de `--calibracao`, que é a flag que os testes usam para não tocar o arquivo real. |

| Padrão de ameaça | STRIDE | Mitigação já existente |
|---|---|---|
| `calibration.json` adulterado leva a leitura silenciosamente errada | Tampering | Falha fechada: gramática + recusa nomeada + validadores no arranque com mensagem de conserto |
| Escrita interrompida corrompe o arquivo e derruba o scanner de party inteiro | DoS | `.tmp` + `os.replace` atômico (`calibracao.py:761-768`), coberto por `test_uma_escrita_interrompida_preserva_o_arquivo_ANTERIOR` |
| Biblioteca de síntese de input entrar na árvore | Elevation (risco de ban) | `tests/test_firewall_escopo.py`, três varreduras + prova por mutação |
| Reflexo do que se lê da tela ir para log/arquivo sem sanear | Information disclosure | Trivial aqui: os campos são números; o log usa `>>><<<` e o arquivo é local |

**Restrição fundadora, reafirmada:** esta fase **só lê pixel**. Nenhuma leitura de memória, nenhum
pacote, nenhum input. Nada nas recomendações acima chega perto disso.

---

## Registro de suposições

| # | Afirmação | Seção | Risco se estiver errada |
|---|---|---|---|
| A1 | O texto da barra inferior é **acromático** (saturação ~0), então a máscara de brilho basta e `tinta_fora_da_curva_dos_moldes` não recusaria | 2 | Se for colorido, o caminho de moldes recusa tudo e o OCR pode degradar. Mitigação barata: medir `saturacao_da_tinta` num recorte real antes de escolher. |
| A2 | A altura de glifo da barra inferior **não** é 9 px como a do mercado | 2 | Se coincidir, os moldes do mercado poderiam ser reusados e o custo cairia muito. Vale **medir**, não assumir — inverte a decisão do nível. |
| A3 | O `.`→`,` do OCR é **confusão de glifo**, não normalização de locale | 4 | Se for locale, a correção seria de configuração e não de gramática. Consequência prática nula: a gramática posicional funciona nos dois casos. |
| A4 | Faltam ~20 px de barra à direita que o spike nunca capturou | 6 | Se a adena estiver colada à direita, o recorte do spike corta dígito e o calibrador precisa disso explicitado. |
| A5 | A janela do jogo estava em `(0,0)` durante o spike | 6 | Se não, os números do spike são desktop puro e precisam de translação. Evidência aritmética forte (4 coincidências independentes), mas é **inferência**. |
| A6 | A fonte do EXP tem seis dígitos significativos em ~26 px e o OCR os resolve de forma repetível | 4 | É a especificação mais apertada da milestone e o spike só a exercitou **duas vezes**. Se a repetibilidade for baixa, o cruzamento de escalas vira recusa crônica e LEIT-02 precisa de outra técnica. |
| A7 | O pacote de idioma `en-US` está em `C:\Windows\OCR` nesta máquina | Ambiente | `disponivel()` já responde; o `CONTEXT.md` registra `True`. Baixíssimo. |

---

## Perguntas em aberto

1. **A fonte da barra inferior é a mesma dos preços do mercado?**
   - Sabemos: os moldes do mercado têm 9 px de altura, 4–6 px de largura, cortados sobre texto
     branco com pico de V 226–230.
   - Não sabemos: a altura de glifo na barra inferior e no nível.
   - Recomendação: **primeira tarefa do plano** — um script de bancada que rode
     `segmentar_glifos_no_brilho` sobre um recorte real e imprima a faixa e as larguras. É de graça
     e decide o item 2 inteiro.

2. **O nível vai por OCR mascarado ou por moldes?**
   - Sabemos: OCR cru → `''`; OCR mascarado `vmin=210` → `'66'`; moldes exigem conjunto completo
     `0-9` que a região do nível nunca mostra.
   - Recomendação: **OCR mascarado**, com `numero_valido` + monotonicidade. Registre a refutação da
     decisão do `CONTEXT.md` no fonte, com o custo medido dos moldes ao lado — é a disciplina que o
     `ROADMAP.md` chama de "um número que caiu precisa dizer que caiu".

3. **Quantas casas o EXP realmente tem, e sempre?**
   - O spike viu `68.5632%` e `68.6738%` — quatro casas nas duas. Mas um EXP abaixo de 10% seria
     `9.1234%` (1+4) e acima de 100% não existe. A regex `\d{1,3}` cobre; falta confirmar que o jogo
     não suprime zeros à esquerda de forma que mude a contagem.
   - Recomendação: fixture de um EXP baixo, se houver como produzir. Senão, aceitar `\d{1,3}` e
     documentar que 5 casas ou 3 casas são recusa por decisão, não por observação.

4. **O `642%` e o `83` da barra esquerda atrapalham a extração do EXP?**
   - Estão no mesmo recorte e o OCR os devolve juntos (`EXP 68.6738% 582% : 83`). Note que a
     transcrição do spike diverge entre as duas leituras (`642%` na tela, `582%` no OCR) — **o OCR
     erra esse campo**, o que é irrelevante para nós, mas é evidência de que a regex tem de ancorar
     no `%` **imediatamente após quatro dígitos**, e não pegar "o primeiro número com `%`".

5. **O calibrador precisa mesmo de trackbar, ou uma varredura basta?**
   - A curva `170/190/210` sugere que uma **varredura automática** (testar `vmin` de 150 a 250 de 10
     em 10, mostrar a máscara e a leitura de cada um, e deixar o usuário escolher pelo número) é
     mais barata que um trackbar e produz **evidência gravada**. O projeto não tem trackbar; tem
     `_marcar` com sugestão, que é o mesmo espírito de "a ferramenta propõe e o usuário confirma".
   - Recomendação: varredura com proposta, não trackbar.

---

## Fontes

### Primárias (confiança ALTA — arquivos abertos e lidos nesta sessão)
- `l2scanner/ocr.py` (282 linhas, integral) — escalas, tabela de custo, modos de falha
- `l2scanner/mercado_leitura.py` — `:1-360`, `:553-700`, `:860-1040`, `:1514-1580`, `:2295-2400`
- `l2scanner/calibracao.py` — `:180-280`, `:640-960`, `:1505-1560`
- `l2scanner/calibrar.py` — `:68`, `:486-530`, `:1168-1250`, `:1270-1345`
- `l2scanner/calibrar_mercado.py` — `:2206-2265`, `:2440-2680`, `:3100-3290`
- `l2scanner/captura_janela.py` — `:1-60`, `:176-420`
- `l2scanner/cliente.py` — `:50-125`
- `l2scanner/mercado_modo.py` — `:1-40`, `:400-470`
- `l2scanner/console.py`, `l2scanner/__main__.py:2100-2150`, `l2scanner/identidade.py:56`
- `calibration.json` — inspecionado por `json.load`: 44 chaves, 13+13 moldes com dimensões
- `requirements.txt`, `.gitignore`, `.planning/config.json` (integrais)
- `calibrar.bat`, `calibrar-mercado.bat`, `calibrar-tiat.bat`, `vigiar-mercado.bat` (integrais)
- `tests/conftest.py`, `tests/test_calibrar_nao_apaga_mercado.py:1-80`,
  `tests/test_calibrar_layout_nao_apaga_negociacao.py:1-70` + outline,
  `tests/test_mercado_glifos.py:1-55`, `tests/test_mercado_modo.py:126-150`,
  `tests/test_firewall_escopo.py:1-46`
- `_olhar_tela.py` (o script do spike, integral)
- **Execução real** de `l2scanner.mercado_leitura` contra as 10 strings da tabela da seção 3
- `git log` de `l2scanner/calibrar_mercado.py`

### Secundárias (confiança MÉDIA)
- `.planning/spikes/renda-barra-inferior.md` — medições de campo, uma amostra por região
- `.planning/workstreams/renda/{REQUIREMENTS,ROADMAP}.md` e `01-CONTEXT.md`

### Terciárias (confiança BAIXA — busca web, sem achado autoritativo)
- Busca por comportamento documentado de `Windows.Media.Ocr` quanto a separador decimal/milhar:
  **nada encontrado** na documentação da Microsoft. O que existe é o fato genérico da indústria de
  que OCR não distingue ponto de vírgula de forma confiável, e de que separadores regionais são
  fonte conhecida de erro de extração. Ver [OcrEngine Class (Microsoft Learn)](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine?view=winrt-26100),
  [Common OCR Errors](https://www.gennai.io/blog/common-ocr-errors-fix-them),
  [IBM Support — period vs comma in currency OCR](https://www.ibm.com/support/pages/node/6575229),
  [Decimal separator (Wikipedia)](https://en.wikipedia.org/wiki/Decimal_separator).
  **Conclusão para o plano:** não há comportamento documentado a explorar; a defesa é gramática
  posicional. [ASSUMED — a ausência de documentação não prova ausência de comportamento]

---

## O que o plano tem que decidir, e o que já está decidido

### (a) Fatos agora estabelecidos por leitura de código

1. `ler_texto` é **2x** e `ler_texto_ampliado` é **3x** (`ocr.py:80-81, 172-196`). Não há entrada
   pública em 1x, e o módulo argumenta contra ela com medição.
2. As duas escalas custam, aquecidas, **23 ms e 31 ms numa banda de 732×240** (`ocr.py:59-62`). Os
   recortes desta fase são 6× menores. Orçamento não é restrição.
3. O par de escalas já é usado como cruzamento em **dois** lugares (`manutencao.py:814-820`,
   `mercado_leitura.py:2311-2360`), com log delimitado por `>>><<<` e sem rate-limit.
4. **Adena: reuso direto, medido por execução.** `numero_valido("10,673,628") is True`,
   `inteiro_de_quantidade(...) == 10673628`. Falta só normalizar `.`→`,`.
5. **Nível: reuso direto para a validação.** `numero_valido("66") is True`,
   `inteiro_de_quantidade("66") == 66`.
6. **EXP: parser novo, obrigatoriamente.** `centesimos_de_moeda` trava em 2 casas decimais
   (`:568`) e exige vírgula (`:566`). Executado: `None` para `68,5632` e `68.5632`.
7. `mascara_de_numero(bgr, valor_minimo)` (`:155`) **é** a máscara do spike, com o piso já por
   parâmetro e sem default.
8. `Descarte` tem **dois** campos (`indice`, `motivo`); o `detalhe` vive só no log
   (`:1562-1577`, `:2379-2390`).
9. Os moldes de dígito moram em `mercado_templates_de_digito` como lista de
   `{glifo, altura, largura, molde:{altura,largura,bytes-hex}}`; 13 itens, dígitos de **9 px de
   altura** e 4–6 px de largura.
10. `Calibracao.salvar` (`:668`) emite **lista literal de 44 chaves** e **não** preserva
    desconhecidas. `carregar` (`:771`) usa `.get` para todo campo opcional e mantém
    `VERSAO_DO_ESQUEMA = 2`.
11. **Ambos** os calibradores fazem load → mutate → full re-emit, com escrita atômica
    (`.tmp` + `os.replace`, `:761-768`).
12. `calibrar_tiat` (`calibrar.py:1168-1250`, 82 linhas) é o template correto para
    `calibrar_renda.py`. `calibrar_mercado.py` (3.359 linhas) não é.
13. **O frame de `JanelaSource` é relativo à JANELA** (`captura_janela.py:13-18, 396-402`), e as
    coordenadas do spike coincidem com esse espaço porque a janela estava em `(0,0)` — quatro
    coincidências aritméticas independentes o sustentam.
14. Nenhuma dependência nova. Nenhuma auditoria de pacote necessária.

### (b) Escolhas genuinamente abertas, do planejador

1. **Nomes.** Módulo (`renda_leitura.py`?), tipos (`LeituraDaRenda`, `RecusaDaRenda`), chaves
   (`renda_nivel`, `renda_barra_esquerda`, `renda_barra_direita`, `renda_vmin_do_nivel`).
2. **Qual leitor para o nível.** A pesquisa recomenda **OCR mascarado**, com evidência de custo
   (item c3 abaixo). O plano pode discordar, mas tem de escrever por quê e tem de orçar as sessões
   de coleta de glifo.
3. **Se o EXP paga a 3x sempre, ou só quando a 2x passa na forma.** `manutencao` só paga a cara
   depois de a barata passar num teste barato. Aqui o teste barato é "a regex casou". Recomendo
   copiar essa ordem — ela também dá um motivo de recusa mais preciso.
4. **Onde mora o comando de leitura única.** Uma flag em `__main__.py` (precedente:
   `--testar-manutencao`, `:2937`), um `python -m l2scanner.renda_leitura`, ou dentro do próprio
   `calibrar_renda.py` como conferência pós-calibração. A terceira é a mais barata e a que o
   usuário mais provavelmente usa.
5. **A varredura de `vmin` no calibrador**: faixa, passo, e como mostrar. Não há precedente exato.
6. **Se a monotonicidade do nível entra já na Fase 1** como regra pura sobre um par. O `CONTEXT.md`
   admite a monotonicidade do EXP; a do nível é ainda mais barata (só sobe, de 1 em 1).
7. **Se `renda_*` também guarda um carimbo de geometria da janela**, no molde de
   `mercado_geometria_da_captura` + `conferir_geometria_do_mercado:900`. Barato e pega
   "o usuário redimensionou a janela" antes de virar leitura errada.
8. **Quantas fixtures resgatar** e de onde. Precisa do jogo aberto pelo menos uma vez.

### (c) O que CONTRADIZ o `CONTEXT.md`, o `ROADMAP.md` ou o `CLAUDE.md` — **leia isto**

**c1. O defeito de não-destruição citado NÃO EXISTE MAIS, e o risco real é outro.** ⚠️ ALTO IMPACTO

- O `CONTEXT.md` (Área 4) e o `ROADMAP.md` (Riscos da Fase 1) dizem: *"`calibrar_mercado.py:2721`
  faz `cal.mercado_grade = grade` e, por isso, calibrar a aba Adena apagaria a grade de
  negociação."*
- **Medido:** a única atribuição está em `calibrar_mercado.py:3182`, e `:3155` retorna antes dela
  para todo layout que não seja negociação. Consertado em `f8dbfe2 feat(05-04): … --layout adena
  deixa de ser bomba` e prendido por `tests/test_calibrar_layout_nao_apaga_negociacao.py`, cuja
  docstring narra o dano **no pretérito**.
- **O risco real, que nenhum dos dois documentos menciona:** `Calibracao.salvar:668` é uma
  **enumeração literal de 44 chaves**. Uma chave `renda_*` que não esteja **no dataclass E no
  `salvar`** é apagada em silêncio pela próxima rodada de qualquer calibrador. Não existe hoje
  teste que amarre `fields(Calibracao)` ao dict de `salvar`.
- **Consequência para o plano:** o teste de não-destruição **muda de forma**. Além dos quatro casos
  da seção 5d, ele precisa do **caso 5** — rodar `calibrar_renda`, depois `calibrar_tiat`, e
  afirmar que `renda_*` sobreviveu — e do teste estrutural
  `test_todo_campo_do_dataclass_sobrevive_a_ida_e_volta`. Um plano que apenas "não repita o defeito
  de 2721" estará defendendo um flanco que já está defendido e deixando o de verdade aberto.

**c2. `ler_texto` NÃO é 1x, e não existe 1x público.** ⚠️ MUDA UMA DECISÃO TRAVADA

- O `CONTEXT.md` Área 2 diz *"O EXP é lido em 1x e em 2x"*. O spike rotula a barra direita como
  "escala 1x" e a esquerda como "escala 2x".
- **Medido:** `ESCALA_DE_DETECCAO = 2` (`ocr.py:80`), `ESCALA_DE_CONFERENCIA = 3` (`:81`). O par de
  produção é **2x × 3x**. E `ocr.py:33-45` documenta que 1x **abstém** nas duas imagens reais
  medidas ("conferido 5 de 5, determinístico") e "NÃO serve como escala de leitura".
- **Consequência:** o cruzamento continua sendo a decisão certa; só o par muda. Se o plano
  escrevesse "1x", o executor construiria uma guarda que abstém sempre e a interpretaria como campo
  vazio — falha silenciosa exatamente no critério mais caro da fase.

**c3. Montar moldes de glifo para o nível é MUITO mais caro que "mais que uma tarefa".** ⚠️ ALTO IMPACTO

- O `CONTEXT.md` Área 1 trava *"Nível: glifos (`mercado_leitura.ler_glifos` + `moldes_da_tinta`)"*
  e registra o OCR mascarado como alternativa *"se montar os moldes do nível custar mais que uma
  tarefa"*.
- **Medido:** `conjunto_descreve_numeros:312` exige `"0123456789,"` **inteiro**, e a docstring
  mostra por que meio conjunto é pior que nenhum (um `8` sem molde de `8` casa com `0` a 0,7826
  contra piso 0,4698). O nível exibe **dois caracteres** e muda uma vez por sessão: cortar `0-9`
  dali exigiria dez valores de nível diferentes. Cortar de outra região colide com a regra medida
  contra fundir iluminações (`calibrar_mercado.py:3125-3131`) e com a diferença de curva tonal que
  o próprio spike achou (a barra lê no cru; o nível só com `vmin=210`). E os moldes existentes têm
  9 px de altura, contra um crop de nível de `30x20` cuja geometria de glifo ninguém mediu.
- **Consequência:** a alternativa registrada é o **caminho principal**. O plano deve inverter a
  decisão, escrever a refutação no fonte com a medição ao lado (disciplina do `ROADMAP.md`), e
  **manter a recusa nomeada obrigatória**, que era a condição da alternativa. Há precedente forte
  no repositório para essa inversão: os moldes de nome de item foram **abandonados** em 2026-08-29
  em favor de OCR + agrupamento (`calibrar_mercado.py:3225-3230`).

**c4. Três ferramentas citadas não existem.** ⚠️ MUDA O ORÇAMENTO DO CALIBRADOR

- O `CONTEXT.md` Área 4 diz *"o caminho que `tools/pick_region.py` e `calibrar_mercado.py` já
  usam"*, e a seção `<specifics>` diz *"o projeto já tem `tools/record.py`"*. O `CLAUDE.md` lista
  `tools/calibrate_hsv.py` (trackbar HSV) e manda construí-lo na Fase 1.
- **Medido:** `ls tools/` devolve 12 arquivos, e **nenhum** deles é `pick_region.py`,
  `record.py` ou `calibrate_hsv.py`. Gravação é a flag `--record` de `__main__.py:2874`.
  Seleção de retângulo é `calibrar._selecionar_regiao:486` (que existe e é boa). **Trackbar HSV não
  existe em lugar nenhum do repositório.**
- **Consequência:** o feedback visual do `vmin` (Área 4) **não tem infraestrutura para reusar**. Ou
  o plano orça um trackbar do zero, ou adota a varredura-com-proposta que a pergunta aberta 5
  recomenda — que é mais barata, produz evidência gravada e segue o idioma "a ferramenta propõe, o
  usuário confirma" que `_marcar` já estabeleceu.

**c5. `rich` não está na árvore.** ⚠️ IMPACTA A FASE 3, NÃO ESTA — mas o roadmap está errado hoje

- O `ROADMAP.md` lista *"Painel `rich.Live` | `l2scanner/console.py`, `mercado_console.py`"* e
  fecha as restrições dizendo *"`mss`, `cv2`, `numpy`, `winrt` e `rich` já estão na árvore"*. O
  `REQUIREMENTS.md` CONS-01 diz *"Mesmo `rich.Live` das telas que já existem"*. O `CLAUDE.md` fixa
  `rich 15.0.0`.
- **Medido:** `grep -rn "import rich\|from rich" l2scanner/` devolve **zero**. `requirements.txt`
  não o declara. `console.py:21-26` são códigos ANSI crus com `_habilitar_cor`, e
  `mercado_console.py` importa `textwrap` e `console`, não `rich`.
- **Consequência:** a Fase 3 vai **ou** adotar uma dependência nova (decisão de pesquisa com
  justificativa, pela doutrina de zero-install do próprio roadmap) **ou** seguir o idioma ANSI
  existente. Isso não é problema desta fase, mas é uma premissa falsa que o roadmap propaga, e
  corrigi-la agora custa uma linha.

**c6. Contradições menores, registradas para não voltarem por baixo.**

- **Slug do diretório.** O `ROADMAP.md` ("Nota de nomenclatura") diz que os diretórios de fase
  levam prefixo `renda-`, "pelo mesmo motivo do `mercado`, do `tiat` e do `dashboard`". O diretório
  real é `01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa`, **sem** prefixo — e o `mercado`
  também não tem (`05-a-aba-adena-e-a-taxa-de-cambio`); só o `dashboard` tem. Escopo de commit é
  o que importa; o plano decide o escopo, não o diretório.
- **"Nenhum módulo deste projeto chama `datetime.now()`".** Falso como afirmação global:
  `console.py:143`, `dashboard.py:542,604`, `gravador.py:78`, `mercado_console.py:688` e
  `__main__.py:2104` chamam. A regra vale para **módulos de lógica pura**, e nesses ela é real
  (`loot.py`, `presenca.py`, `acervo.py`, `aprendiz.py`, `esquecimento.py` documentam a ausência).
  A Fase 1 não mede tempo; o carimbo entra por parâmetro se entrar.
- **`Descarte(indice, motivo, detalhe)`.** O `CONTEXT.md` descreve três campos; a classe real tem
  dois (`:1563-1577`). O `detalhe` é do log.
- **44 chaves.** Confirmado, exatamente 44. O `CONTEXT.md` acertou.
- **"O spike leu com `ler_texto` sobre o recorte cru"** — plausível e provavelmente verdadeiro,
  mas note que isso significa **2x**, não 1x como o spike rotulou. É a mesma raiz do c2.

---

## Metadados

**Distribuição de confiança**
- Peças existentes e assinaturas: **ALTA** — todos os arquivos abertos com `Read`/`sed` nesta
  sessão, todas as citações com `arquivo:linha`, e os parsers **executados** contra as strings reais
- Caminho de não-destruição do `calibration.json`: **ALTA** — os dois calibradores lidos ponta a
  ponta, `git log` conferido, testes precedentes lidos
- Espaço de coordenadas: **ALTA para o mecanismo** (`captura_janela.py:396-402`), **MÉDIA para a
  interpretação dos números do spike** (inferência aritmética a partir de 4 coincidências, não
  medição direta)
- Custo dos moldes de glifo: **ALTA no mecanismo** (conjunto completo obrigatório, medido no fonte),
  **MÉDIA na conclusão** (depende de A1/A2, que ninguém mediu)
- Comportamento do OCR sobre a fonte da barra: **MÉDIA** — uma amostra por região, do spike
- Comportamento de separador do `Windows.Media.Ocr`: **BAIXA** — nada autoritativo encontrado

**Data da pesquisa:** 2026-09-02
**Válido até:** ~2026-10-02 para os achados de código (o repositório muda rápido: `calibrar_mercado.py`
mudou 5 vezes em 6 dias). **Reconfira a seção 5 se `calibracao.py` ou `calibrar_mercado.py` receberem
commit antes de a fase começar.**
