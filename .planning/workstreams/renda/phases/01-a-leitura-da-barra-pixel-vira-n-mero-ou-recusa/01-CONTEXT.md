# Phase 1: A leitura da barra — pixel vira número, ou recusa - Context

**Gathered:** 2026-09-02
**Status:** Ready for planning
**Mode:** Smart discuss em modo autônomo — o usuário foi dormir e pediu explicitamente para o
trabalho seguir. As áreas cinzentas abaixo foram **decididas por mim**, com a alternativa de
cada uma registrada ao lado para ele poder discordar de manhã sem ter que reconstruir o
raciocínio.

<domain>
## Phase Boundary

Esta fase transforma **pixel em número, ou em recusa nomeada** — e nada além disso.

Dentro: capturar os três recortes (nível, esquerda da barra, direita da barra), lê-los,
validá-los, devolvê-los como estrutura, e um calibrador que põe todo retângulo e todo limiar no
`calibration.json`.

Fora, e não por acaso: **nenhuma taxa, nenhuma diferença entre amostras, nenhum arquivo de
registro, nenhum laço ao vivo.** A Fase 1 não sabe o que é "por hora". Ela é uma função de
`frame → LeituraDaRenda | Recusa`, e a única coisa que a torna verificável sozinha é justamente
não ter estado. A monotonicidade do EXP entre amostras (critério 3 do roadmap) é a única
exceção, e ela entra como **regra pura sobre um par de leituras passado por parâmetro** — não
como memória viva dentro do leitor.

</domain>

<decisions>
## Implementation Decisions

### Área 1 — Qual leitor lê qual campo

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

### Área 2 — Como as quatro casas decimais ficam de pé

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

### Área 3 — Onde a calibração mora

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

### Área 4 — O calibrador, e a não-destruição que ele precisa PROVAR

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

### Área 5 — Mira: de qual personagem é esta leitura

- **`--janela` é obrigatório**, não conveniente. O usuário roda duas instâncias (Yazalaque e
  Faerlina); EXP e adena são **do personagem**. Sem mira, o scanner lê a instância errada e
  produz uma taxa que não descreve ninguém — o modo de falha do REG-04.
- **Herda o caminho inteiro do `--mercado`**: resolução do título pela chave `[jogo] personagem`
  do `config.toml`, `captura_janela` por Windows Graphics Capture. A Fase 1 não inventa captura.
- **A leitura carrega o nome do personagem**, mesmo sem existir arquivo ainda. É o campo que a
  Fase 2 vai gravar, e decidi-lo agora custa zero; descobri-lo na Fase 2 custa mexer no esquema
  depois que o `dashboard` já está apontado para ele.

### Claude's Discretion

- Nomes exatos de módulo, função e chave de calibração.
- Se o nível usa glifos ou OCR mascarado — decidido por medição durante o plano, com a recusa
  nomeada obrigatória nos dois casos.
- Se a leitura da barra esquerda extrai também o `642%` (bônus) e o `83` — estão no mesmo
  recorte e sairiam de graça, mas nenhum requisito os pede. Preferência: **extrair e descartar**,
  para não fixar um formato de campo que ninguém pediu.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `l2scanner/ocr.py` — `disponivel()`, `motivo_indisponivel()`, `ler_texto()`,
  `ler_texto_ampliado()`. Confirmado funcionando nesta máquina: `disponivel() == True`.
- `l2scanner/mercado_leitura.py` — `segmentar_glifos`, `ler_glifos`, `moldes_da_tinta`,
  `mascara_de_numero`, `numero_valido`, `inteiro_de_quantidade`, `centesimos_de_moeda`,
  `pontuar_glifos`, e `Descarte` como forma de recusa já estabelecida no projeto.
- `l2scanner/calibracao.py` — `Calibracao` (dataclass), `LimiaresDeCor`, `Regiao`,
  `CalibracaoInvalida`, e os `_conferir_*` que validam no carregamento.
- `l2scanner/calibrar_mercado.py` — o padrão de calibrador interativo. **E o defeito da
  linha 2721 para não repetir.**
- `l2scanner/captura_janela.py`, `cliente.py` — captura por janela e `nome_do_personagem`.

### Established Patterns
- **Chaves de calibração achatadas com prefixo de feature.** 44 chaves de topo hoje; `mercado_`
  (30), `tiat_` (2), o resto da party.
- **Recusa nomeada em vez de valor degradado.** `Descarte(indice, motivo, detalhe)` no mercado.
  Esta fase segue a mesma forma.
- **Inteiro escalado em vez de float** para tudo que vai ser comparado ou diferenciado
  (`total_em_centesimos`).
- **Relógio por parâmetro.** Nenhum módulo chama `datetime.now()`. Vale aqui mesmo a fase não
  medindo tempo — a leitura pode carregar um carimbo, e ele **entra**, não é lido do sistema.
- **Nada de constante mágica no fonte** — regra escrita no `CLAUDE.md` do projeto.

### Integration Points
- `calibration.json` — arquivo compartilhado por quatro features. Ponto de maior risco da fase.
- `config.toml` — `[jogo] personagem` para resolver o título da janela.
- `l2scanner/__main__.py` — onde um comando de leitura única entraria. A Fase 1 entrega a
  leitura; o modo `--renda` de laço é da Fase 3.

</code_context>

<specifics>
## Specific Ideas

- O critério 1 do roadmap é conferível a olho: rodar o comando e comparar com o monitor. O
  spike já capturou a tela com os valores `nível 66`, `EXP 68,5632%`, `adena 10.673.628` — eles
  servem de fixture, e as capturas de tela estão no scratchpad da sessão.
- Gravar fixtures reais dos três recortes durante o desenvolvimento (o projeto já tem
  `tools/record.py` e uma pasta `recordings/` com 18 gravações). Sem fixture, todo bug de
  leitura exige o jogo aberto na hora certa.

</specifics>

<corrections>
## Correções medidas pela pesquisa (2026-09-02) — leia ANTES das decisões acima

O `01-RESEARCH.md` abriu o código e refutou cinco coisas que eu tinha escrito por suposição.
As decisões acima ficam como estão **para o histórico**; o que vale é a correção.

1. **O defeito de não-destruição que eu citei NÃO EXISTE MAIS.** `cal.mercado_grade = grade`
   está em `calibrar_mercado.py:3182`, e `:3155` retorna antes dele para todo layout que não
   seja negociação. Foi consertado no commit `f8dbfe2` e está preso por
   `tests/test_calibrar_layout_nao_apaga_negociacao.py`. **O risco real é outro, e é pior:**
   `Calibracao.salvar` (`calibracao.py:668`) é uma enumeração literal de 44 chaves e **não
   preserva chave desconhecida**. Uma chave `renda_*` que exista no arquivo mas não esteja no
   dataclass **e** no `salvar` some calada na próxima rodada de qualquer calibrador. Não há
   teste hoje amarrando `fields(Calibracao)` ao dict de `salvar`. A Área 4 continua sendo a de
   maior risco da fase — mas por um motivo diferente do que eu escrevi, e o teste que ela pede
   é outro.

2. **As escalas do OCR são 2x e 3x, não 1x e 2x.** `ocr.py:80-81`: `ler_texto` é 2x e
   `ler_texto_ampliado` é 3x. Não existe entrada pública em 1x, e o módulo documenta com
   medição que 1x **abstém**. O cruzamento da Área 2 continua certo; o par muda para 2x×3x.

3. **Moldes de glifo para o nível são impraticáveis, não caros.** `conjunto_descreve_numeros`
   exige o conjunto `0-9` inteiro, e a região do nível mostra dois caracteres que mudam uma vez
   por sessão — nunca haverá de onde extrair os dez moldes. A **alternativa** que eu registrei
   na Área 1 (OCR mascarado, `vmin=210 → '66'`) vira o **caminho principal**. Há precedente:
   os moldes de nome de item foram abandonados em favor de OCR em 2026-08-29.

4. **`centesimos_de_moeda` NÃO generaliza para o EXP.** Ele trava em `len(decimal) != 2` e
   exige vírgula; devolve `None` tanto para `68,5632` quanto para `68.5632` (medido por
   execução). O EXP precisa de irmã própria, copiando a forma. Já a adena reusa como está:
   `numero_valido("10,673,628") is True` e `inteiro_de_quantidade(...) == 10673628`, medidos.

5. **`tools/pick_region.py`, `tools/record.py` e o trackbar HSV não existem no repositório**, e
   **`rich` não está instalado nem importado em lugar nenhum** (confirmado à parte:
   `ModuleNotFoundError: No module named 'rich'`, zero imports em `l2scanner/`). O `CLAUDE.md` e
   o `ROADMAP.md` citam os quatro como existentes. Quem planejar não pode contar com eles. O
   `rich` é problema da Fase 3, e já está anotado lá.

**Resolvido, e a favor do plano:** o frame de `JanelaSource` é **relativo à janela**
(`captura_janela.py:396-402`), e as coordenadas do spike já estão nesse espaço — a janela
carimbada é 1720x1392, `1230+470 = 1700` e `1368+26 ≈ 1392`, e o nível `246,736` cai ao lado do
`hp_proprio` `298,711`, que é declaradamente janela-relativo. A história "os números do spike
são o ponto de partida do calibrador" sobrevive intacta.

</corrections>

<deferred>
## Deferred Ideas

- Ler o `642%` (bônus de XP) e o `83` como campos de primeira classe — estão no mesmo recorte,
  mas nenhum requisito os pede. Se virarem interessantes, o recorte já estará calibrado.
- Ler o L-Coin (`13.091`) e o XM (`58,40`) da barra direita. **Tentador e adjacente ao
  `mercado`**, que já converte adena→XM→BRL. Fica fora: é escopo do outro workstream e
  acrescentaria coluna a um esquema que o `dashboard` vai consumir.
- XP absoluto do chat (CHAT-01) — já está em v2 no `REQUIREMENTS.md`.

</deferred>
