# Phase 3: Persistência de observações - Research

**Researched:** 2026-08-30
**Domain:** CSV append-only em disco local (stdlib), tolerância a truncagem, importação no Google Sheets
**Confidence:** HIGH nas quatro lacunas (três fechadas por MEDIÇÃO nesta máquina; a quarta fechada por fonte oficial + um resíduo que só o portão humano fecha)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**As colunas do CSV**

- **O RESÍDUO DO CRUZAMENTO entra como coluna própria.** A Fase 2 o calcula em
  `LinhaLida.residuo_do_cruzamento` e registrou por escrito que a decisão de persistir é
  desta fase. Ele é a **única pista independente** de que uma leitura de número pode estar
  errada — a guarda que o consumiria foi medida e REPROVOU (fechamento 0,6525 contra 0,99
  exigido; detecção 0,0164 contra 0,90), então o resíduo virou observação em vez de gate.
  Jogá-lo fora perderia informação que já custou uma wave inteira para existir.
- **O UNITÁRIO DERIVADO NÃO vira coluna.** Total e quantidade bastam, e o critério 1 da fase
  exige "unitário derivado, nunca confundido". Uma coluna derivada dentro do arquivo convida
  alguém a tratá-la como dado — e o unitário EXIBIDO pelo jogo é arredondado a 2 casas
  (`40,00 ÷ 48` aparece como `0,83`), medido na Fase 1. Reconstruir o total a partir dele
  devolve um número que nunca existiu.
- **O NOME LEGÍVEL e a CHAVE DA SÉRIE vão os dois.** O nome é o que o usuário lê; a chave é o
  que agrupa. Só o nome perde o agrupamento quando o OCR oscila; só a chave é ilegível — e
  este arquivo existe para ser lido a olho nu e entregue a outra IA.
- **Só o CARIMBO DE TEMPO como proveniência — nada de gravação ou frame.** Eles são artefatos
  de replay: no farm ao vivo não existe "frame 78". Persistir campo que só tem valor em
  bancada é convidar a confusão entre teste e produção.

**O que é "a mesma observação"**

- **A chave de dedup é `série + total + quantidade`.** É o que identifica um anúncio. **Sem o
  tempo**, deliberadamente: incluí-lo tornaria a dedup vácua, porque cada tick teria carimbo
  diferente e toda observação seria "nova".
- **O mesmo anúncio visto em dias diferentes é UMA linha, com a data da PRIMEIRA vez.** O
  usuário quer saber que o anúncio existe e por quanto — não quantas vezes olhou para ele.
- **As chaves são carregadas EM MEMÓRIA no arranque, do próprio CSV.** Há **um único
  escritor** — o mercado lê sempre do Yazalaque, corrigido pelo usuário em 2026-08-28 — e o
  volume é de milhares de linhas, não milhões.
- **Chave igual com conteúdo diferente é impossível por construção**, porque a chave É o
  conteúdo. Se acontecer, é bug — e o aviso sai ALTO em vez de escolher um dos dois.

**O arquivo**

- **UM arquivo só, que cresce.** Rotação seria complexidade a serviço de um problema que não
  existe neste volume.
- **Mora em `.mercado/`**, ao lado do `catalogo-de-nomes.csv` que a Fase 2 já escreve.
- **O CABEÇALHO é escrito UMA VEZ, na criação, e CONFERIDO na abertura.**
- **O cabeçalho é CONTRATO: se o do disco divergir do esperado, a feature DESLIGA ALTO** em
  vez de escrever desalinhado.

**Falha**

- **"Desligar alto" é: aviso no console E no log, a feature de mercado para, e os alertas de
  party continuam chegando.**
- **A linha truncada é detectada na LEITURA do arranque**, por contagem de campos — descarta
  só ela, com aviso, e nunca trata o arquivo inteiro como corrompido.
- **Escrita por APPEND com `flush` linha a linha.** Escrita atômica do arquivo inteiro
  (`os.replace`) aqui perderia a sessão toda num corte de energia. São problemas diferentes.
- **O carimbo usa o RELÓGIO ANCORADO que o projeto já tem**, nunca `datetime.now()` solto.

**Do `<specifics>`, e igualmente travado**

- Separador `;`. Preços como inteiros em centésimos (`1139` é `11,39`), nunca float.
- O critério 2 exige **importação REAL no Google Sheets**, não presumida. É portão humano.

### Claude's Discretion

- Nomes exatos das colunas e a ordem delas, desde que legíveis a olho e coerentes com o que
  o resto do projeto já chama pelos mesmos nomes.
- Forma interna do índice de chaves em memória.
- Como o aviso alto é formatado, desde que apareça no console E no log.

### Deferred Ideas (OUT OF SCOPE)

- **Série temporal por dia** — o mesmo anúncio visto em dias diferentes vira uma linha só.
- **Rotação de arquivo** (por mês ou por ano) — desnecessária neste volume.
- **Exportar/importar de volta** — o arquivo é de mão única por ora.
- **Persistir os motivos de descarte** — a contagem "li N, perdi M" é da Fase 4.
- **A fusão `B-grade Gemstone` × `C-grade Gemstone`** (0,9375, letra de grade) continua
  aberta desde a Fase 2.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERS-01 | Observações gravadas como linhas num CSV com carimbo do relógio ancorado, uma linha por observação, legível a olho nu e importável no Google Sheets sem conversão | § Lacuna 1 (o diálogo do Sheets não tem preset "ponto e vírgula" — instrução exata para o portão humano), § Lacuna 3 (o `csv` da stdlib com `;` sobrevive a todo caractere que o OCR pode devolver, medido), § Relógio ancorado (`l2scanner/relogio.py:156` `Relogio.agora()`) |
| PERS-02 | Revisitar uma página não duplica observações — dedup por chave de conteúdo, conferida em memória antes de escrever | § Lacuna 4 (a leitura de arranque que popula o índice tem de recusar a linha truncada ANTES de ela virar chave), § Padrão 2 |
| PERS-03 | Falha de escrita desliga só a feature de mercado e avisa alto — nunca derruba o núcleo de alertas | § Lacuna 5 (os três modos de falha do critério 5 medidos no Windows desta máquina, com os `errno` exatos), § Padrão 3, § Armadilha 4 |
</phase_requirements>

## Summary

Esta fase tem um analog direto no repositório — `l2scanner/mercado_catalogo.py`, a classe
`Catalogo` — e o desenho certo é copiar dele tudo menos a estratégia de escrita. O catálogo
reescreve o arquivo inteiro de forma atômica (`os.replace`) porque `avistamentos` sobe sem o
arquivo crescer; este arquivo cresce por construção e a decisão travada é append. Essa é a
única divergência estrutural entre os dois, e ela é deliberada.

**O achado que muda o plano:** a regra que o CONTEXT trava — *"a linha truncada é detectada
na leitura por contagem de campos"* — **não é suficiente, e isso está MEDIDO**. Cortando o
último campo de uma linha de 6 colunas byte a byte, dois dos cinco cortes produziram
exatamente **6 campos** com o último campo *parcial*: `'80'` virou `'8'`. Contagem de campos
aprova essa linha, e um resíduo de 8 centésimos onde o disco dizia 80 é precisamente o modo
de falha que o FUND-01 existe para impedir — dado parcial com aparência plausível. Existe um
critério exato e barato que pega 100% dos cortes medidos: **`csv.writer.writerow` emite UMA
única chamada `write()` contendo a linha inteira MAIS o terminador** (medido), logo *um
registro está completo se, e somente se, o arquivo termina em newline*. Contagem de campos
continua valendo como segunda rede; ela não pode ser a primeira.

**O segundo achado:** `fsync` não é necessário aqui, e agora há número. `flush()` sozinho
custa **0,0037 ms** por linha; `flush()+os.fsync()` custa **1,5990 ms** — **432× mais caro**.
E o que o `fsync` compra não é o modo de falha do critério 4: `flush()` já entrega a linha
inteira ao SO numa chamada só, então morte de processo (Ctrl+C, exceção, taskkill) **não
produz linha truncada** — ou a linha inteira está no SO, ou ela nunca começou. Truncagem de
verdade exige queda de energia/BSOD ou disco cheio no meio do `flush`, e para esses o `fsync`
ajuda só no primeiro, ao custo de 432×. A decisão travada (append + flush) está correta e
agora está medida.

**Primary recommendation:** copiar a forma de `Catalogo` (mesma pasta, mesmo `;`, mesmo
`newline=""`, mesma leitura defensiva que nomeia a linha ruim), trocar `gravar()` atômico por
**abrir-escrever-flush-fechar por linha** (medido: 0,1295 ms — 12× mais barato que `fsync` e
irrelevante num tick de 1 Hz), e acrescentar à leitura de arranque o teste *"o arquivo termina
em newline?"* antes de qualquer validação de campo.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Formatar uma `LinhaLida` como registro de CSV | Módulo puro (novo `mercado_registro.py` ou metade nova de um módulo) | — | Sem relógio, sem disco: recebe `LinhaLida` + `datetime` e devolve uma tupla de strings. É o que permite testar a coluna sem tocar arquivo. |
| Chave de dedup (`série + total + quantidade`) | Módulo puro | — | Função de 1 linha sobre a `LinhaLida`; o índice em memória é do dono do arquivo. |
| Ler o arquivo no arranque, recusar truncagem, montar o índice | Camada de disco (a classe que possui o arquivo) | — | Precedente literal: `Catalogo.carregar` + `Catalogo._serie_da_linha`. |
| Escrever a observação nova (append+flush) | Camada de disco | — | Único escritor. Nunca levanta para fora. |
| Decidir se a feature de mercado sobe ou desliga | Montagem (`__main__.montar_*`) | Camada de disco (reporta o motivo) | `montar_despachante` / `montar_gravador` já são o trilho: tenta, degrada com log, devolve `None`, deixa o scanner subir. |
| Carimbo de tempo | `l2scanner/relogio.py` (já existe) | — | `Relogio.agora()` entra por PARÂMETRO, como em `Catalogo.registrar(chave, nome, agora)`. |
| Ligar isso no laço ao vivo | **Fase 4** | — | Ver § Armadilha 5: `Catalogo` ainda não tem nenhum instanciador de produção. |

## Project Constraints (from CLAUDE.md)

| Diretiva | Efeito nesta fase |
|----------|-------------------|
| Detecção 100% passiva; nunca enviar input ao jogo | Nada aqui toca input. **FIRE-01** proíbe biblioteca de síntese na árvore, e `tests/test_firewall_escopo.py` varre o venv instalado. |
| "Nada de constante mágica — limiar mora no `calibration.json`" | Esta fase não tem limiar. Nome de arquivo e nome de coluna são *contrato*, não limiar: moram em constantes do módulo, exatamente como `ARQUIVO_DO_CATALOGO` e `COLUNAS` em `mercado_catalogo.py:375,383`. Não inventar chave nova no `calibration.json`. |
| "Hardcoded HSV constants" / "PyYAML" / "storing token in config" — a tabela *What NOT to Use* | Nenhuma se aplica: zero dependência nova, zero segredo, zero pixel. |
| `.env` / segredos | Não aplicável — este arquivo não carrega credencial. |
| Preços como inteiros, nunca float | Reafirmado no REQUIREMENTS.md § "O que NÃO muda". A coluna do total é `int`; formatação decimal é assunto de LEITURA humana (§ Lacuna 1). |

---

# As quatro lacunas

## Lacuna 1 — O Google Sheets, de verdade

### O que o diálogo de importação realmente oferece

O diálogo "Import file" do Google Sheets, na Ajuda oficial, oferece em **Separator character**
exatamente quatro opções: **"Detect automatically", "Tab", "Comma", "Custom"**
[CITED: support.google.com/docs/answer/40608].

Três consequências diretas, e a segunda é a que decide a instrução:

1. **Não existe preset "Semicolon".** Quem quiser forçar tem de escolher **"Custom"** e digitar
   `;`. Uma instrução do tipo "escolha ponto e vírgula na lista" mandaria o usuário procurar
   uma opção que não existe.
2. **"Detect automatically" é o default**, e para um arquivo em que toda linha tem o mesmo
   número de `;` e nenhuma vírgula fora de campo citado, a detecção acerta — mas isso é
   inferência, não documentado [ASSUMED]. Por isso o roteiro do portão humano manda usar
   **Custom `;`**: ele não depende de heurística.
3. **A página de Ajuda não documenta nenhum checkbox** de "converter texto em números, datas e
   fórmulas" no diálogo do Sheets [CITED: support.google.com/docs/answer/40608] — esse
   controle é do *Text Import Wizard* do Excel, não do Sheets. Ou seja: **não há como pedir ao
   Sheets que não interprete o conteúdo.** Isso importa para o `+6` da § Armadilha 1.

**O caminho de importação importa.** `File > Import > Upload` abre o diálogo acima. Abrir o
`.csv` com duplo clique no Drive **não abre diálogo nenhum** e cai na detecção automática
[ASSUMED — não confirmado em fonte oficial]. O roteiro do portão humano tem de dizer qual dos
dois caminhos usar, porque só um deles deixa escolher `;`.

### A tensão real entre o critério 1 e o critério 2, e a proposta

O critério 1 quer que o usuário **ENTENDA** o que lê; a decisão travada grava `6200` onde a
tela dizia `62,00`. Quatro saídas foram consideradas:

| Saída | O que custa | Veredito |
|---|---|---|
| **(a) O NOME DA COLUNA carrega a unidade** — `total_em_centesimos` | Zero. O cabeçalho já é contrato travado e já é escrito uma vez. | **RECOMENDADA.** `6200` sob um cabeçalho que diz "em centésimos" é autoexplicativo para o olho humano *e* para a outra IA que vai receber o arquivo — que lê o cabeçalho antes de tudo. É também o nome que `mercado_leitura.LinhaLida.total_em_centesimos:1159` já usa, então o CLAUDE.md ("coerente com o que o resto do projeto já chama pelos mesmos nomes") o escolhe sozinho. |
| **(b) Uma linha de instrução no topo do arquivo** | Quebra o CSV: vira uma linha de 1 campo, quebra o cabeçalho-contrato, e o Sheets a importa como dado. | **REJEITADA.** |
| **(c) Um `LEIAME.txt` ao lado, em `.mercado/`** | Escrito uma vez, na criação da pasta. Não toca o CSV, não entra na importação. | **RECOMENDADA como complemento de (a)** — é onde mora o roteiro de importação (`File > Import > Upload`, `Custom` = `;`) e a frase "os preços são inteiros em centésimos: `6200` é `62,00`". Custa ~15 linhas e resolve o critério 2 na origem. |
| **(d) Uma coluna a mais `total_exibido` = `"62,00"`** | Dois campos para o mesmo fato, e o `62,00` é interpretado pelo Sheets conforme a **localidade da planilha**: em pt-BR vira o número 62; em en-US vira texto [ASSUMED — comportamento de localidade, não medido]. E vai contra a mesma objeção que derrubou a coluna do unitário: coluna derivada convida a ser tratada como dado. | **NÃO recomendada para o v1** — fica registrada como a alternativa que o usuário pode pedir no portão do critério 2 se `6200` cru o incomodar na prática. |

**Proposta:** (a) + (c). O cabeçalho explica a unidade; o `LEIAME.txt` explica a importação.
A decisão travada não muda uma vírgula, e o critério 1 fica atendido pelo nome da coluna, que
é justamente a área de discrição desta fase.

---

## Lacuna 2 — Append + `flush` no Windows: o que sobrevive de verdade

### O mecanismo, em três degraus (não opinião)

| Degrau | Chamada | O que ela move | Sobrevive a |
|---|---|---|---|
| 1 | `csv.writer.writerow(...)` | monta a linha inteira + `\r\n` numa string e chama `file.write()` **uma única vez** [VERIFIED: medido nesta sessão — ver abaixo] | nada; está no buffer do Python |
| 2 | `file.flush()` | do buffer do Python para o SO (uma `WriteFile`) | **morte do processo**: Ctrl+C, exceção não tratada, `taskkill`, fechamento do console |
| 3 | `os.fsync(fd)` | do cache do SO para o prato/NAND (no Windows, `_commit`/`FlushFileBuffers`) | **queda de energia, BSOD, reset** |

**Medição de que `writerow` é uma chamada só** (arquivo falso contando `write`):

```
chamadas: ['a;b;c\r\n', 'x;"Common; Aztac";z\r\n']
```

Duas `writerow`, duas `write` — cada uma com a linha **e o terminador juntos**. Esse é o fato
que sustenta a Lacuna 4 inteira.

### O custo do `fsync`, medido nesta máquina

Windows 11, CPython 3.12.10 x64, 300 linhas de ~102 bytes, `.csv` em `%TEMP%`:

```
so flush     n=300  mediana=  0.0037 ms  p95=  0.0059 ms  max= 0.3241 ms  total=   1.85 ms
flush+fsync  n=300  mediana=  1.5990 ms  p95=  2.1815 ms  max= 3.4105 ms  total= 459.47 ms
```

**432× mais caro na mediana.** [VERIFIED: medido nesta sessão]

Em números absolutos 1,6 ms dentro de um tick de 1 Hz é acessível — o argumento contra o
`fsync` **não é o custo**, é que ele não compra o modo de falha do critério 4.

### O critério 4 acontece com append+flush? A resposta é: quase nunca, e por três caminhos

| Cenário | Produz linha truncada? | Por quê |
|---|---|---|
| **Ctrl+C / exceção / `taskkill` / fechar o console** | **NÃO** | A linha ou está inteira no buffer (e some inteira — o arquivo termina no `\r\n` anterior) ou já foi entregue ao SO inteira, porque `writerow`+`flush` é uma `write()` só. Não há estado intermediário observável no arquivo. |
| **Queda de energia / BSOD** | **SIM** | O cache do SO é perdido; o NTFS pode deixar a cauda cortada em byte arbitrário, e a escrita preguiçosa pode até deixar um rabo de `\x00`. É o único cenário que o `fsync` mitigaria — e mesmo com `fsync` você só troca "as últimas N linhas somem" por "as últimas N linhas ficam". |
| **Disco cheio (`ENOSPC`) no meio do `flush`** | **SIM** | O `flush` levanta `OSError`, e uma escrita PARCIAL pode já ter chegado ao arquivo. O `fsync` não ajuda aqui. É o mesmo `OSError(28)` que `gravador.py:181-192` já documenta por extenso. |

**Conclusão para o plano:** manter `flush()` sem `fsync()`, como o CONTEXT travou — agora com
o número que justifica. O dado desta fase é **re-derivável** (o mercado será lido de novo), e
perder as últimas linhas de uma sessão num corte de energia é uma perda pequena; aceitar uma
linha truncada como dado não é. **O esforço vai todo para o lado da LEITURA** (Lacuna 4), não
para o lado da durabilidade da escrita.

### E um achado colateral que muda o desenho da alça

Medido: **com a alça já aberta, marcar o arquivo como somente-leitura NÃO impede a escrita** —
o `writerow` + `flush` passaram e o conteúdo chegou ao disco. O `PermissionError` só nasce no
**`open`**. [VERIFIED: medido nesta sessão]

Isso decide entre as duas formas de escrever:

| Forma | Custo/linha (medido) | Comportamento no critério 5 |
|---|---|---|
| Alça aberta a sessão inteira | 0,0037 ms | Uma falha que aparece **depois** do arranque (usuário trava o arquivo no meio do farm) é **invisível** |
| **`open("a")` + `writerow` + `flush` + `close` por linha** | **0,1295 ms** (p95 0,3068; máx 0,6851) | Detecta a falha **no instante em que ela aparece**, com `PermissionError` no `open` |

0,13 ms por linha, num tick de 1 Hz que grava algumas linhas por página aceita, é ruído.
**Recomendação: abrir e fechar por linha.** Ainda é "append com flush linha a linha" — a
decisão travada — e ganha o critério 5 de graça, além de nunca segurar uma alça sobre um
arquivo que o usuário quer abrir no Sheets.

---

## Lacuna 3 — `csv` da stdlib com `;` e conteúdo brasileiro

### O que o `csv.writer(delimiter=";")` faz com conteúdo hostil — medido, ida e volta

Cada caso foi escrito e relido. Nenhum perdeu informação. [VERIFIED: medido nesta sessão]

| Conteúdo do campo | Sai no arquivo como | Volta do `csv.reader` como |
|---|---|---|
| `Common; Aztac` (delimitador dentro do nome) | `"Common; Aztac"` | `Common; Aztac` ✅ |
| `Hardin's "Soul" Crystal` (aspas) | `"Hardin's ""Soul"" Crystal"` | `Hardin's "Soul" Crystal` ✅ |
| `Common\nAztac` (quebra de linha) | `"Common\nAztac"` | `Common\nAztac` ✅ |
| `Common\rAztac` (CR sozinho) | `"Common\rAztac"` | `Common\rAztac` ✅ |
| `Common\tAztac` (tab) | `Common\tAztac` (sem aspas) | `Common\tAztac` ✅ |
| `62,00` (vírgula decimal) | `62,00` **sem aspas** | `62,00` ✅ |
| `=SOMA(A1:A2)` | `=SOMA(A1:A2)` sem aspas | idem ✅ (mas ver Armadilha 1) |
| `+6 Agathion` | `+6 Agathion` sem aspas | idem ✅ (mas ver Armadilha 1) |

O `QUOTE_MINIMAL` (default) cita exatamente os quatro casos que precisam: delimitador, aspas,
`\r` e `\n`. **A vírgula decimal não é citada, e é isso que se quer** — `62,00` sai limpo, e o
`;` como delimitador nunca colide com ela. A decisão travada do separador está estruturalmente
correta e o módulo `csv` a sustenta sem configuração extra.

### O que o OCR pode devolver que quebraria o CSV — e a resposta é: nada

O nome vem do motor de OCR do Windows sobre o recorte da coluna do nome (LEIT-01/LEIT-05).
Ele pode devolver, em ordem de plausibilidade decrescente: um `;` alucinado a partir de um
`:` ou de um pixel de ornamento; aspas a partir de um apóstrofo (`Hardin's` é nome real neste
jogo); um `\n` se o recorte pegar duas alturas de texto; pontuação Unicode qualquer. **Todos
os quatro sobrevivem ao round-trip acima.** Não é preciso sanear o nome antes de escrever, e
sanear seria pior: alteraria o rótulo que o usuário lê.

**A única condição não-negociável é o `newline=""`** nos dois lados (`open` de leitura e de
escrita). Está escrito por extenso no analog, `mercado_catalogo.py:456-457` e `:592-596`:
sem ele o `csv` não remonta um campo que contém quebra de linha, e na escrita o Python
traduziria o `\r\n` do `csv` produzindo `\r\r\n` no Windows.

### `mercado_catalogo.py` já resolveu isso, e serve — com uma ressalva

Serve **integralmente para a escrita**: `SEPARADOR = ";"` (`:381`), `csv.writer(destino,
delimiter=SEPARADOR)` (`:600`), `newline=""` (`:599`), `encoding="utf-8"`. Copiar.

**Não serve para o modo de abertura.** `Catalogo.gravar` abre em `"w"` **porque o destino é o
temporário do `os.replace`** (`:598`) — esta fase abre em `"a"` sobre o destino real. É a
única linha do analog que não se transporta, e ela é a diferença entre as duas fases.

Uma coisa a **não** copiar: `assinatura_por_ocr` já garante que a chave da série não contém
`;` (o `SEPARADOR_DA_ASSINATURA = "#"` foi escolhido *exatamente* para não colidir com o `;`
da Fase 3 — `mercado_catalogo.py:97-102`). A chave é segura por construção; o **nome exibido**
não é, e é ele que o `QUOTE_MINIMAL` protege.

---

## Lacuna 4 — Detecção da linha truncada na leitura

### `csv.reader` NUNCA levanta com uma última linha incompleta — ele engole

Seis formas de arquivo truncado, todas lidas sem exceção: [VERIFIED: medido nesta sessão]

| Arquivo termina em... | O que o `csv.reader` devolve |
|---|---|
| `xx;Common Az` (meio de campo) | `['xx', 'Common Az']` — 2 campos |
| `xx;Common Aztac;6200;` (exatamente num `;`) | `['xx', 'Common Aztac', '6200', '']` — 4 campos, último vazio |
| `xx;Common Aztac;6200` (campos a menos) | `['xx', 'Common Aztac', '6200']` — 3 campos |
| `xx;"Common\nAz` (**aspas não fechadas**) | `['xx', 'Common\nAz']` — **não levanta**, fecha o campo no EOF |
| linha completa **sem `\n` final** | 5 campos, correta |
| arquivo terminando em `\n` | nada extra |

Nunca há `csv.Error`. **Só existe uma via de detecção: inspecionar os campos.**

### E o achado que derruba "contagem de campos basta"

Linha de 6 colunas `k;nome;2026-08-30T14:03:21;6200;48;80\r\n`, cortada byte a byte a partir
do fim: [VERIFIED: medido nesta sessão]

```
corte= 36 bytes -> ['k','nome','2026-08-30T14:03:21','6200','48','8']  campos=6 (esperado 6)  termina_em_newline=False
corte= 35 bytes -> ['k','nome','2026-08-30T14:03:21','6200','48','']   campos=6 (esperado 6)  termina_em_newline=False
corte= 34 bytes -> ['k','nome','2026-08-30T14:03:21','6200','48']      campos=5 (esperado 6)  termina_em_newline=False
corte= 33 bytes -> ['k','nome','2026-08-30T14:03:21','6200','4']       campos=5 (esperado 6)  termina_em_newline=False
corte= 31 bytes -> ['k','nome','2026-08-30T14:03:21','6200']           campos=4 (esperado 6)  termina_em_newline=False
```

**Dois dos cinco cortes passam pela contagem de campos.** O primeiro é o pior caso possível:
6 campos, todos parseáveis, e um resíduo de **8** onde o disco dizia **80**. A regra travada
("descarta por contagem de campos") aprovaria essa linha, e ela viraria observação — e, pior,
viraria **chave de dedup** que bloqueia a gravação da observação correta mais tarde.

Note também o corte 33: `'4'` no lugar de `'48'` — a *quantidade*, que entra na chave de dedup.

### O critério exato, e ele é uma linha

Como `writerow` emite linha **e** terminador numa `write()` só (§ Lacuna 2), vale a
bicondicional:

> **Um registro está completo se, e somente se, o arquivo termina em newline.**

Nos cinco cortes acima, `termina_em_newline` foi `False` em **5 de 5**; num arquivo íntegro,
`True`. É o único critério medido com 100% de cobertura.

**Recomendação para a leitura de arranque, em três redes, nesta ordem:**

1. **Ler o texto inteiro uma vez** (`arquivo.read_text(encoding="utf-8")` ou o `open` com
   `newline=""` já usado). Se ele não é vazio e **não termina em `\n`**, o ÚLTIMO registro é
   suspeito de truncagem → descartar **só ele**, com o aviso alto que nomeia a linha, no
   mesmo formato de `Catalogo._serie_da_linha` (`mercado_catalogo.py:498-506`).
2. **Contagem de campos** por linha — o que o CONTEXT travou; continua valendo como segunda
   rede e pega as linhas que o usuário quebrou editando à mão no meio do arquivo.
3. **Validação por tipo de cada campo** — `int()` no total, na quantidade e no resíduo;
   `datetime.fromisoformat()` no carimbo. Precedente literal em
   `mercado_catalogo.py:517-530`. É a terceira rede, e é a que pega `'8'`… **não**: `'8'` é
   um `int` válido. Por isso a rede 1 é obrigatória e não opcional.

### O `mercado_catalogo.py` serve de precedente literal — e onde ele fica curto

**Serve, e deve ser copiado quase palavra por palavra:**

- `carregar()` (`:442-486`): `FileNotFoundError` → dicionário vazio, sem levantar ("primeira
  execução numa máquina limpa é estado legítimo"); `OSError` → aviso e sessão VAZIA sem tocar
  o disco; cabeçalho pulado; `enumerate(..., start=1)` para o aviso citar o número da linha.
- `_serie_da_linha()` (`:488-538`): a função interna `recusar(motivo)` que loga com o número
  da linha **e o conteúdo cru** (`SEPARADOR.join(campos)`), porque "a forense deste projeto
  acontece DEPOIS do farm, com o log na mão".
- A frase-guia, que é o critério 4 palavra por palavra (`:443-451`): *"descartar a linha
  malformada com aviso, e NUNCA tratar o arquivo inteiro como corrompido"*.

**Fica curto em dois pontos, e os dois são desta fase:**

1. **A verificação de fim-de-arquivo não existe lá**, porque o catálogo é escrito por
   `os.replace` atômico — ele *não pode* truncar, e por isso nunca precisou dessa rede. Este
   arquivo pode. É a única lógica realmente nova da leitura.
2. **O cabeçalho lá é conveniência, aqui é CONTRATO.** `Catalogo.carregar:478-481` diz
   literalmente *"um arquivo sem ele ainda carrega"*. O CONTEXT desta fase trava o oposto:
   cabeçalho divergente **desliga a feature alto**. Não copiar esse trecho — invertê-lo, e
   distinguir três estados: (a) arquivo ausente → cria com cabeçalho, normal; (b) cabeçalho
   idêntico → segue; (c) cabeçalho presente e diferente, **ou ausente num arquivo não-vazio**
   → DESLIGA ALTO.

---

## Lacuna 5 (bônus, e ela é do critério 5) — os modos de falha do Windows, medidos

O critério 5 nomeia três: *"travado, read-only, ou pasta inexistente"*. Medidos nesta máquina,
no `open("a", encoding="utf-8", newline="")`: [VERIFIED: medido nesta sessão]

| Cenário | Exceção | `errno` / `winerror` |
|---|---|---|
| Arquivo somente-leitura | `PermissionError` | errno 13 |
| Pasta inexistente | `FileNotFoundError` | errno 2 |
| Nome ocupado por um DIRETÓRIO | `PermissionError` | errno 13 |
| `mkdir(parents=True, exist_ok=True)` sobre o nome de um ARQUIVO | `FileExistsError` | errno 17, winerror 183 |

Todas são subclasses de `OSError` — **um `except OSError` cobre as quatro**.

**Duas armadilhas de teste que a medição revelou:**

- **`os.chmod(pasta, S_IREAD)` NÃO torna a pasta somente-leitura no Windows.** Medido: criar
  subpasta e criar arquivo dentro dela **funcionaram** com o bit ligado. Um teste que tentar
  reproduzir "pasta read-only" desse jeito passará por acidente. Os cenários **reprodutíveis**
  em teste são: arquivo somente-leitura (`os.chmod(arquivo, S_IREAD)`), pasta inexistente com
  o `mkdir` desligado, e nome ocupado por diretório. É a mesma família do levantamento já
  citado em `gravador.py:146-149`.
- **O `mkdir(parents=True, exist_ok=True)` do construtor de `Catalogo`** (`:432`) **pode
  levantar** (`FileExistsError` errno 17, medido) — e ele roda *antes* de qualquer `try`. Se
  esta fase copiar esse construtor tal e qual, a montagem tem de envolvê-lo, pelo trilho de
  `montar_gravador` (`__main__.py:225+`, que existe *precisamente* porque
  `Gravador.__init__` fazia `mkdir` e `open` fora de qualquer `try` e derrubava o scanner).

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `csv` (stdlib) | — | Escrever e ler o arquivo com `delimiter=";"` | Já é o dialeto do analog (`mercado_catalogo.py:381,462,600`). `QUOTE_MINIMAL` resolve os quatro caracteres hostis sem configuração. |
| `pathlib` (stdlib) | — | Caminho a partir de `config.RAIZ` | `PASTA_DO_MERCADO = RAIZ / ".mercado"` já existe (`mercado_catalogo.py:374`) e o comentário lá explica por que o caminho **nunca** vem de entrada do usuário. |
| `logging` (stdlib) | — | O aviso alto | `log = logging.getLogger(__name__)`, `log.warning` para linha descartada e `log.error` para feature desligada — o padrão já usado. |
| `datetime` (stdlib) | — | `datetime.fromisoformat` na leitura, `.isoformat()` na escrita | Precedente exato: `mercado_catalogo.py:518-519` e `:609-610`. |
| `l2scanner.relogio.Relogio` | interno | `Relogio.agora()` → `datetime` | É o relógio ancorado que o CONTEXT trava. Entra por PARÂMETRO (`agora: datetime`), como `Catalogo.registrar` já faz — é o que dispensa monkeypatch nos testes. |
| CPython | **3.12.10 x64** (Python GLOBAL desta máquina) | Runtime dos testes | Medido nesta sessão. Não é o 3.13 do CLAUDE.md — nada nesta fase depende de 3.13, mas o plano não deve assumir sintaxe posterior a 3.12. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `flush()` só | `flush()` + `os.fsync()` | 432× mais caro (medido) e compra apenas o cenário de queda de energia. Rejeitado. |
| Abrir/fechar por linha | Alça aberta a sessão toda | 35× mais barato por linha (0,0037 vs 0,1295 ms) mas **cego** para falhas que aparecem depois do arranque (medido). A 1 Hz, 0,13 ms é ruído. |
| `csv.writer` | `";".join(campos)` à mão | Perderia o `QUOTE_MINIMAL` — um `;` alucinado pelo OCR dentro de um nome quebraria o arquivo em silêncio. |
| Arquivo texto | `sqlite3` (stdlib, sem dependência nova) | Já derrubado pelo usuário em 2026-08-29 e analisado ponto a ponto no REQUIREMENTS.md. **Não reabrir.** |

**Installation:** nenhuma. Zero dependência nova — a restrição inegociável da fase e o que
`tests/test_firewall_escopo.py` protege.

## Package Legitimacy Audit

**Não aplicável.** Esta fase **não instala nenhum pacote externo**. Todo o material é stdlib
(`csv`, `json`, `pathlib`, `logging`, `datetime`, `os`) mais módulos internos do
`l2scanner/`. Nenhum nome de pacote foi consultado em registro; nenhuma verificação de
legitimidade é devida.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
  Fase 2 (fechada)                       │  Fase 3 (esta)                     │ Fase 4
                                         │                                    │
  frame ─► LeitorDePagina.tick()         │                                    │
             │                           │                                    │
             ├─ 2 frames concordam? ──NÃO─► (nada)                            │
             │                     SIM   │                                    │
             ▼                           │                                    │
        PaginaAceita                     │                                    │
         .linhas: (LinhaLida, ...) ──────┼──► [PURO] chave_da_observacao(l)   │
                                         │      = série + total + quantidade  │
                                         │            │                       │
                                         │            ▼                       │
                                         │      já está no índice? ──SIM──► descarta (dedup)
                                         │            │ NÃO                   │
                                         │            ▼                       │
                                         │      [PURO] linha_do_csv(l, agora) │
                                         │            │  ◄── Relogio.agora()  │
                                         │            ▼                       │
                                         │      [DISCO] RegistroDeObservacoes │
                                         │        open("a") → writerow → flush│
                                         │            → close                 │
                                         │            │         │             │
                                         │      OSError?        └─► índice[chave] = ✓
                                         │            │                       │
                                         │            ▼                       │
                                         │      DESLIGA ALTO ─► log.error + console
                                         │      (mercado para; party segue)   │
  ─────────────────────────────────────────────────────────────────────────────
  ARRANQUE (uma vez):                    │                                    │
   .mercado/observacoes.csv ─► existe? ──NÃO──► cria com cabeçalho ─► índice vazio
             │ SIM                       │                                    │
             ▼                           │                                    │
   lê texto inteiro                      │                                    │
     ├─ cabeçalho != contrato? ──SIM──► DESLIGA ALTO                          │
     ├─ não termina em "\n"? ──SIM──► descarta ÚLTIMO registro, aviso alto    │
     ├─ por linha: nº de campos != nº de colunas ──► descarta linha, aviso    │
     ├─ por linha: int()/fromisoformat() falha ──► descarta linha, aviso      │
     └─ OSError ──► DESLIGA ALTO                                              │
             │                                                                │
             ▼                                                                │
   índice de chaves em memória ──────────────────────────────► consumido pela Fase 4
```

### Recommended Project Structure

```
l2scanner/
└── mercado_registro.py     # NOVO. Metade pura (chave de dedup + formatação da linha)
                            # + metade de disco (RegistroDeObservacoes).
                            # Mesmo desenho de duas metades que mercado_catalogo.py
                            # documenta em :9-12 — "cada metade dá para afirmar sozinha".
.mercado/
├── catalogo-de-nomes.csv   # Fase 2, dono: Catalogo. NÃO TOCAR.
├── observacoes.csv         # Fase 3, dono: RegistroDeObservacoes.
└── LEIAME.txt              # § Lacuna 1, saída (c). Escrito uma vez.
tests/
└── test_mercado_registro.py
```

### Pattern 1: Duas metades no mesmo módulo, com a fronteira escrita

**What:** funções puras (sem disco, sem relógio) em cima; a classe que possui o arquivo
embaixo, separadas por um comentário-régua.
**When to use:** sempre neste repositório — é o desenho de `mercado_catalogo.py:9-12` e a
régua literal está em `:364-366`.
**Why:** permite testar "esta linha vira este CSV" sem `tmp_path`, e testar "este arquivo
truncado é recusado" sem `LinhaLida`.

### Pattern 2: Tempo por parâmetro, pasta por parâmetro

```python
# Source: l2scanner/mercado_catalogo.py:426-434 e :542-544 (precedente do repositório)
class RegistroDeObservacoes:
    def __init__(self, pasta: Path) -> None:
        # A pasta chega no construtor, e nao derivada aqui dentro, pelo mesmo
        # motivo de `Catalogo.__init__` e de `RegistroDeLoot.__init__`: e o que
        # permite ao teste apontar para `tmp_path` sem nunca tocar a `.mercado/`
        # do usuario. Producao passa `PASTA_DO_MERCADO`.
        ...

    def registrar(self, linha: LinhaLida, agora: datetime) -> bool:
        ...
```

Nem relógio nem caminho nascem lá dentro. É o que dispensa monkeypatch — e o que impede um
teste de escrever na `.mercado/` real do usuário, que é dado acumulado e sem desfazer.

### Pattern 3: Tenta, degrada, avisa alto, e deixa o scanner subir

```python
# Source: l2scanner/__main__.py:189-224 (montar_despachante) e :225+ (montar_gravador)
def montar_registro_de_mercado(...) -> RegistroDeObservacoes | None:
    try:
        return RegistroDeObservacoes(PASTA_DO_MERCADO)
    except OSError as erro:
        log.error(
            "MERCADO DESLIGADO — nao consegui abrir %s (%s). Os alertas de "
            "party continuam normalmente; nenhuma observacao sera gravada "
            "nesta sessao.", ..., erro,
        )
        return None
```

`OSError` cobre os quatro modos medidos na § Lacuna 5. `montar_gravador` existe no repositório
**exatamente porque** `Gravador.__init__` fazia `mkdir` + `open` fora de qualquer `try` e
derrubava o scanner inteiro por um `recordings/` somente-leitura.

### Anti-Patterns to Avoid

- **Deixar a contagem de campos ser a única rede contra truncagem** — medido: 2 de 5 cortes
  passam. Ver Lacuna 4.
- **`os.replace` / reescrita atômica do arquivo inteiro** — é o padrão certo para o
  `calibration.json` e para o catálogo, e o errado aqui: perderia a sessão inteira num corte.
  Travado no CONTEXT.
- **Abrir sem `newline=""`** — produz `\r\r\n` na escrita e impede a leitura de um campo com
  quebra de linha. Escrito por extenso em `mercado_catalogo.py:456-457` e `:592-596`.
- **Escrever a chave da série sem o nome, ou o nome sem a chave** — travado no CONTEXT: vão
  os dois.
- **Gravar `descartadas`/`motivos` de `PaginaAceita` no CSV** — proibido pela D-17 da Fase 2,
  reescrito em `mercado_leitura.py:1174-1176`.
- **Sanear o nome antes de escrever** — desnecessário (Lacuna 3) e alteraria o rótulo que o
  usuário lê.

## Don't Hand-Roll

| Problema | Não construa | Use | Por quê |
|---|---|---|---|
| Citar campos com `;`, aspas e quebra de linha | `";".join(...)` e um escapador próprio | `csv.writer(delimiter=";")` | `QUOTE_MINIMAL` já cobre os quatro casos, medido, e o `reader` desfaz simetricamente. |
| Parsear a linha de volta | `linha.split(";")` | `csv.reader(delimiter=";")` | `split` quebra num nome que contém `;` — o exato caso que o writer citou. |
| Carimbo de tempo | `datetime.now()` | `Relogio.agora()`, recebido por parâmetro | O PC é dual boot e o Windows pode ficar ~3h adiantado (`relogio.py:1-13`). |
| Caminho da pasta | Concatenar strings, ou aceitar caminho de fora | `RAIZ / ".mercado"` | Caminho vindo de fora é travessia de diretório de graça — já escrito em `mercado_catalogo.py:370-373`. |
| Durabilidade da linha | Um esquema de checksum/marcador de fim por linha | O terminador que o `csv.writer` já emite + o teste "termina em newline" | Medido: cobre 5 de 5 cortes, custa uma linha, e não polui o arquivo que o usuário lê. |

**Key insight:** o `csv` da stdlib já resolve *ida e volta* tudo que o OCR pode devolver. O
único problema que ele **não** resolve é o de fim-de-arquivo, e esse não pede biblioteca:
pede uma linha de código e a medição que a justifica.

## Common Pitfalls

### Armadilha 1: `+6 Agathion Alpha Hunter Sealed` vira fórmula no Sheets

**O que dá errado:** nomes de item deste jogo começam com `+` — `+6 Agathion Alpha Hunter
Sealed`, `+4 ...`, `+2 ...` estão medidos nos artefatos da Fase 2 e vão para a coluna
`nome_exibido`. O Google Sheets trata uma célula que começa com `+` como início de fórmula,
não acha referência de célula, e devolve erro [CITED: thebricks.com — fonte **não**
autoritativa; **não medido no Sheets**]. E a Ajuda oficial **não** documenta nenhum checkbox
de "não converter" no diálogo de importação [CITED: support.google.com/docs/answer/40608].
**Por que acontece:** herança da compatibilidade com Lotus, presente no Excel e replicada no
Sheets.
**Como evitar:** **NÃO** prefixar `'` no arquivo — isso suja o dado que a outra IA vai ler e
o que o usuário lê no editor (critério 1). O certo é **carregar essa pergunta específica para
dentro do portão humano do critério 2**, que já é humano de qualquer jeito: o roteiro tem de
mandar o usuário conferir **uma linha cujo nome comece com `+`** e reportar se ela caiu como
texto ou como `#ERROR!`. Se cair como erro, a saída (d) da Lacuna 1 — ou um `'` só na coluna
do nome — volta à mesa **com medição**.
**Sinal de alerta:** a coluna do nome mostrando `#ERROR!`, `#NAME?` ou o número `6` no lugar
de `+6 Agathion...`.

### Armadilha 2: contagem de campos aprova a linha truncada

Ver § Lacuna 4. **Sinal de alerta:** um resíduo de 1 dígito onde os vizinhos têm 2-3, ou uma
quantidade suspeitamente redonda na última linha do arquivo.

### Armadilha 3: o arquivo que o usuário editou à mão não termina em newline

**O que dá errado:** a rede 1 (§ Lacuna 4) descarta o último registro de todo arquivo que não
termina em `\n`. Um editor que salva sem newline final faria a rede 1 comer uma observação
legítima que o usuário acabou de corrigir no Sheets.
**Por que acontece:** o critério "termina em newline" não distingue truncagem de estilo de
editor.
**Como evitar:** o aviso tem de dizer **as duas hipóteses** por extenso — *"o arquivo não
termina em quebra de linha: ou a última gravação foi interrompida, ou ele foi editado à mão e
salvo sem newline final. A última linha foi DESCARTADA; se ela era boa, ela será regravada na
próxima vez que o item aparecer na tela"* — e essa última cláusula é verdadeira **porque a
observação é re-derivável**. Descartar continua sendo a escolha certa: um resíduo errado não
se detecta depois; uma observação perdida se refaz sozinha.
**Sinal de alerta:** o aviso saindo em toda execução, o que significa que o escritor está
deixando o arquivo sem terminador — bug, não edição.

### Armadilha 4: o `mkdir` do construtor levanta fora de qualquer `try`

Ver § Lacuna 5. É o bug que `montar_gravador` foi escrito para consertar, e copiar
`Catalogo.__init__` sem envolvê-lo o reintroduz. **Sinal de alerta:** traceback cru no
arranque em vez do aviso alto.

### Armadilha 5: esta fase não tem consumidor de produção, e isso é normal

**O que dá errado:** um plano que tente "ligar no laço" vai procurar onde `PaginaAceita` é
consumida ao vivo e não vai achar. Confirmado por grep: **`Catalogo` não tem nenhum
instanciador em `l2scanner/`** — só testes e `tools/`. O modo `--mercado` é **DETC-02, Fase
4**, e o CONTEXT diz literalmente que esta fase "NÃO tem modo de invocação próprio".
**Como evitar:** a Fase 3 entrega o módulo, os testes, e (se couber) a função de montagem
`montar_registro_de_mercado(...) -> ... | None` **sem chamador ainda** — é o que a Fase 4
liga. Não tocar `rastreador.py` nem o gate de brilho de `visao.py`.

### Armadilha 6: `os.chmod(pasta, S_IREAD)` não faz nada no Windows

Ver § Lacuna 5. Um teste do critério 5 escrito assim **passa por acidente**. Usar arquivo
somente-leitura, pasta inexistente, ou nome ocupado por diretório.

## Code Examples

### Escrever uma observação, com o modo e as flags que importam

```python
# Source: l2scanner/mercado_catalogo.py:598-613 (forma), com "w"->"a" e sem os.replace
# (a UNICA divergencia estrutural entre o catalogo e este arquivo, e ela e a decisao
#  travada do CONTEXT: append, porque este arquivo cresce).
with self.arquivo.open("a", encoding="utf-8", newline="") as destino:
    csv.writer(destino, delimiter=SEPARADOR).writerow(campos)
    destino.flush()   # do buffer do Python para o SO. Sem os.fsync: 432x mais caro
                      # (medido: 1,5990 ms contra 0,0037 ms) e so compra queda de energia.
```

### A rede que a contagem de campos não pega

```python
# Source: medicao desta sessao. `csv.writer.writerow` emite UMA `write()` com a linha
# E o terminador juntos, entao a bicondicional vale: registro completo <=> arquivo
# termina em newline. Medido: 5 de 5 cortes byte-a-byte detectados; contagem de
# campos sozinha deixou passar 2 de 5, um deles com '80' virando '8'.
bruto = self.arquivo.read_text(encoding="utf-8")
ultima_incompleta = bool(bruto) and not bruto.endswith("\n")
```

### O carimbo, e por que ele entra por parâmetro

```python
# Source: l2scanner/mercado_catalogo.py:542-544 (assinatura) + l2scanner/relogio.py:156
def registrar(self, linha: LinhaLida, agora: datetime) -> bool: ...

# producao:  registro.registrar(linha, relogio.agora())
# teste:     registro.registrar(linha, datetime(2026, 8, 30, 14, 3, 21))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| SQLite + WAL + `INSERT OR IGNORE` | CSV `;` append-only, dedup em memória | 2026-08-29 (usuário) | Duas das três justificativas do SQLite já tinham caído em 2026-08-28 (escritor único). A terceira perdeu para "ler a olho, jogar no Sheets, entregar a outra IA". **Não reabrir.** |
| Guarda de cruzamento como *gate* | Resíduo como *observação*, coluna do CSV | Fase 2, por medição (fechamento 0,6525 vs 0,99; detecção 0,0164 vs 0,90) | É por isso que o resíduo tem coluna: o número que a guarda não pôde usar ainda é a única pista independente de leitura errada. |
| Truncagem detectada por contagem de campos | Contagem de campos **mais** o teste de fim-de-arquivo | Esta pesquisa, 2026-08-30, por medição | A regra travada continua valendo — ela só deixou de ser a primeira rede. |

**Deprecated/outdated:** `rapidfuzz` como métrica de nome (refutado por medição na Fase 2 —
`mercado_catalogo.py:21-45`); qualquer dependência nova (FIRE-01).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | O Sheets, em "Detect automatically", acerta o `;` num arquivo bem formado | Lacuna 1 | Baixo — o roteiro proposto manda usar **Custom `;`**, que não depende disso. |
| A2 | Abrir o `.csv` por duplo clique no Drive não oferece diálogo de separador | Lacuna 1 | Médio — se oferecer, a instrução fica desnecessariamente restritiva. Sem custo real. |
| A3 | O Sheets trata uma célula iniciada em `+` como fórmula | Armadilha 1 | **ALTO — é o único risco real ao critério 2.** Fonte não autoritativa, não medida. Nomes com `+N` existem neste dado. Mitigação: entra explicitamente no roteiro do portão humano. |
| A4 | `62,00` numa coluna extra seria lido como número em planilha pt-BR e como texto em en-US | Lacuna 1, saída (d) | Baixo — a saída (d) não é a recomendada. |
| A5 | Um corte de energia pode deixar cauda de `\x00` (escrita preguiçosa do NTFS) | Lacuna 2 | Baixo — a rede "termina em newline" pega esse caso de qualquer jeito. |
| A6 | Ctrl+C não pode interromper o `write()` do `csv` no meio | Lacuna 2 | Baixo — sinal do Python só roda em fronteira de bytecode; e mesmo se ocorresse, a rede 1 pega. |

## Open Questions

1. **A rede "termina em newline" deve descartar a última linha mesmo quando ela valida
   inteira?**
   - O que sabemos: 5 de 5 truncagens medidas deixam o arquivo sem newline final; 2 delas
     produzem uma linha que valida.
   - O que não está claro: com que frequência o usuário vai editar à mão e salvar sem newline
     final.
   - Recomendação: **descartar sempre**, com o aviso de duas hipóteses da Armadilha 3. O dado
     é re-derivável; o resíduo errado não é detectável depois. É decisão do planejador levar
     isto ao usuário ou aceitar a recomendação — ela endurece uma regra travada, não a
     contradiz.

2. **A coluna do nome sobrevive à importação no Sheets com nomes `+N`?** (Armadilha 1 / A3)
   - Recomendação: **não resolver por código agora.** Acrescentar ao roteiro do portão humano
     do critério 2 um item explícito: *"confira a linha do `+6 Agathion Alpha Hunter Sealed` —
     a célula mostra o nome, ou um erro?"*. O portão já é humano; a pergunta é de graça lá.

3. **`LEIAME.txt` entra nesta fase ou vira nota do portão?**
   - Recomendação: entra — 15 linhas, escrito uma vez ao criar a pasta, e é onde o roteiro de
     importação (`File > Import > Upload`, separador **Custom** `;`) fica onde o usuário vai
     olhar seis meses depois.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| CPython (global, o que roda o pytest) | testes | ✓ | **3.12.10 x64** (medido) | — |
| `csv`, `json`, `pathlib`, `logging`, `datetime`, `os` | tudo | ✓ | stdlib | — |
| `.mercado/` no `.gitignore` | não versionar dado acumulado | ✓ | `.gitignore:34-38` (medido) | — |
| `l2scanner/relogio.py` `Relogio.agora()` | PERS-01 | ✓ | `relogio.py:156` | — |
| Google Sheets (conta do usuário) | critério 2 (portão humano) | — | — | Nenhum: é portão humano por definição |

**Missing dependencies with no fallback:** nenhuma.
**Missing dependencies with fallback:** nenhuma.

> Nota: o CLAUDE.md prescreve Python 3.13; o interpretador **global** desta máquina, que é
> onde o pytest roda (fato operacional da fase), é 3.12.10. Nada nesta fase precisa de 3.13,
> mas o plano não deve usar sintaxe posterior a 3.12.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | não | Sem autenticação — arquivo local, processo local |
| V3 Session Management | não | Sem sessão |
| V4 Access Control | não | Sem multiusuário |
| **V5 Input Validation** | **sim** | Toda linha lida do disco é entrada não confiável: contagem de campos + `int()` + `datetime.fromisoformat()` + a rede de fim-de-arquivo. Precedente: `mercado_catalogo._serie_da_linha`. |
| **V12 Files & Resources** | **sim** | Caminho derivado de `config.RAIZ`, **nunca** de entrada do usuário (`mercado_catalogo.py:370-373`) — travessia de diretório impossível por construção. |
| V6 Cryptography | não | Sem segredo, sem token |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| **CSV/formula injection** — um nome vindo de OCR começando com `=`, `+`, `-` ou `@` vira fórmula ao ser aberto numa planilha | Tampering | Reconhecido e **não mitigado no arquivo**, deliberadamente: o vetor exige que o próprio usuário abra o próprio arquivo local, e prefixar `'` sujaria o dado que o critério 1 manda ser legível. Fica como item do portão humano (Armadilha 1). |
| Travessia de diretório pelo nome do arquivo | Tampering | Nome de arquivo é constante do módulo; pasta vem de `RAIZ`. |
| Linha truncada aceita como observação | Tampering / Information Disclosure | § Lacuna 4, três redes. É a mesma família do FUND-01. |
| Disco cheio derruba o scanner e mata os alertas de morte | Denial of Service | `except OSError` na montagem e no `registrar`; nunca `raise` para fora. É o `OSError(28)` de `gravador.py:181-192`. |

## Sources

### Primary (HIGH confidence)

- **Medição direta nesta sessão**, CPython 3.12.10 x64 no Windows 11 desta máquina —
  comportamento de `csv.writer`/`csv.reader` com `;` e conteúdo hostil; contagem de chamadas
  `write()` por `writerow`; cortes byte a byte de linha truncada; custo de
  `flush` vs `flush+fsync` vs `open/close` por linha; `errno`/`winerror` dos modos de falha
  de `open("a")`; inércia do `chmod` sobre pasta no Windows.
- **Código do próprio repositório**, lido nesta sessão: `l2scanner/mercado_catalogo.py`
  (integral), `l2scanner/mercado_leitura.py:1131-1180`, `l2scanner/mercado_pagina.py:182-220`,
  `l2scanner/relogio.py:1-80,146-170`, `l2scanner/gravador.py:140-200`,
  `l2scanner/__main__.py:189-240`, `l2scanner/config.py:40`, `.gitignore:34-38`.
- **`.planning/workstreams/mercado/`**: `03-CONTEXT.md`, `REQUIREMENTS.md`, `ROADMAP.md:118-145`.

### Secondary (MEDIUM confidence)

- [support.google.com/docs/answer/40608](https://support.google.com/docs/answer/40608) —
  opções do diálogo de importação do Sheets: "Detect automatically", "Tab", "Comma", "Custom";
  ausência de checkbox de conversão.
- [support.google.com — thread sobre CSV com ponto e vírgula](https://support.google.com/docs/thread/213833310/imported-csv-file-is-using-semicolons-instead-of-commas-as-delimiter?hl=en)

### Tertiary (LOW confidence)

- [thebricks.com — símbolo `+` no Google Sheets](https://www.thebricks.com/resources/guide-how-to-add-plus-symbol-in-google-sheets)
  — comportamento de célula iniciada em `+`. Blog, não fonte oficial. **É a base de A3, o
  único risco alto desta pesquisa, e por isso ele foi empurrado para o portão humano em vez
  de virar código.**

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — stdlib, e o analog no repositório já usa exatamente estes módulos.
- Arquitetura / padrões: **HIGH** — três precedentes lidos no fonte (`Catalogo`,
  `montar_despachante`, `montar_gravador`).
- Lacuna 2 (flush/fsync): **HIGH** — medido nesta máquina, com números.
- Lacuna 3 (csv + `;`): **HIGH** — medido, round-trip em 8 casos.
- Lacuna 4 (truncagem): **HIGH** — medido, e o achado contradiz a suposição inicial.
- Lacuna 1 (Sheets): **MEDIUM** — o diálogo está confirmado em fonte oficial; o
  comportamento do `+` inicial não, e por isso virou item do portão humano.

**Research date:** 2026-08-30
**Valid until:** 2027-02-28 para tudo que é stdlib e código deste repositório (nada aqui se
move); ~30 dias para o comportamento do diálogo do Google Sheets, que é produto vivo.
