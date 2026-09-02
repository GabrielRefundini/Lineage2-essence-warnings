# `vendor/` — a biblioteca de grafico, e as tres provas que ela precisou dar

Esta pasta guarda o **primeiro e unico artefato de terceiro vendorizado deste projeto**.
Ele executa no navegador do usuario, na mesma maquina em que o jogo roda e na mesma arvore
em que mora o `.env` com o token do Chatwoot. Por isso ele nao entrou por download e pronto:
o `01-UI-SPEC.md`, secao `Registry Safety`, converte o portao em quatro provas separadas —
**VEND-1** (proveniencia conferivel), **VEND-2** (revisao do fonte, registrada), **VEND-3**
(um teste que quebra) e **VEND-4** (a CSP no cabecalho).

> **A condicao de bloqueio, dita por extenso no UI-SPEC:** biblioteca vendorizada sem
> VEND-1..4 completas no momento do merge e **BLOCK** no portao de verificacao da fase.
> Nao e ressalva, nao e divida tecnica anotada, nao e "resolve depois".

Onde cada prova mora:

| Prova | Onde ela esta |
|---|---|
| VEND-1 | a tabela de proveniencia logo abaixo, conferida por `tests/test_firewall_dashboard.py` |
| VEND-2 | a secao **Revisao do fonte** deste arquivo, conferida por `tests/test_firewall_dashboard.py` |
| VEND-3 | `tests/test_firewall_dashboard.py` — a varredura, o controle negativo, o guarda de alcance e o guarda contra vacuidade |
| VEND-4 | `l2scanner/dashboard.py` (a constante `CSP`), conferida por `tests/test_dashboard_tracer.py` |

**Este texto e ASCII puro, de proposito**, no mesmo idioma dos arquivos de `tests/`. A
Fase 01 registrou que o heredoc do shell desta maquina corrompe caractere nao-ASCII; um
documento cujo unico proposito e ser conferido byte a byte nao pode depender de sorte de
codificacao.

---

## VEND-1 — proveniencia

Biblioteca: **uPlot 1.6.32**, de Leon Sorokin (`github.com/leeoniya/uPlot`).
Licenca: **MIT** — permissiva, na lista que o UI-SPEC aceita (MIT / Apache-2.0 / ISC);
copyleft foi recusado por aquele documento. O texto da licenca acompanha o codigo na arvore,
em `uPlot.LICENSE`.

Data do download: **2026-09-01**.

| Arquivo | Versao | Licenca | Bytes | SHA-256 (recalculado em disco) | URL de origem |
|---|---|---|---|---|---|
| `uPlot.iife.min.js` | 1.6.32 | MIT | 51081 | `19c8d4c6ad88929a79f4ae49d6f7161566dfd0ba3d15cc495e974f787eb78f1f` | `https://cdn.jsdelivr.net/npm/uplot@1.6.32/dist/uPlot.iife.min.js` |
| `uPlot.min.css` | 1.6.32 | MIT | 1857 | `df630c6a8d6f8eeaff264b50f73ce5b114f646ffd9a0bb74f049b0a00135fa04` | `https://cdn.jsdelivr.net/npm/uplot@1.6.32/dist/uPlot.min.css` |
| `uPlot.LICENSE` | 1.6.32 | MIT | 1078 | `8f989229699b4fe2f1a0432d0e9edc338a8a911e250e2d1b01ecd770a5f5b1bd` | `https://cdn.jsdelivr.net/npm/uplot@1.6.32/LICENSE` |

**Sao DOIS arquivos de execucao, e nao um.** uPlot exige a folha de estilo junto com o
codigo — a pesquisa mediu isso e registrou como custo da escolha. Quem atualizar a versao
tem de trocar os dois, e recalcular os dois hashes.

**O tamanho em bytes esta na tabela para se conferir a olho.** Um hash diferente diz "mudou";
um tamanho de 197 KB onde deveria haver 51 KB diz *o que* mudou, sem ferramenta nenhuma.

### O SHA-256 foi RECALCULADO nesta arvore, e nao copiado da pesquisa

O `01-RESEARCH.md` avisa por escrito que o hash registrado la e o do artefato de uma CDN
especifica, e que um download de outra origem (GitHub Releases, por exemplo) pode diferir
legitimamente por convencao de fim de linha. Por isso os tres valores acima saem de
`sha256sum` sobre os arquivos **em disco nesta arvore**, hoje.

Resultado da conferencia contra a pesquisa:

| Arquivo | Hash da pesquisa | Hash recalculado | Diferenca |
|---|---|---|---|
| `uPlot.iife.min.js` | `19c8d4c6...eb78f1f` | `19c8d4c6...eb78f1f` | **nenhuma** — bate byte a byte, e os 51081 bytes tambem |
| `uPlot.min.css` | nao baixado na pesquisa (so o `content-length`, 1857) | `df630c6a...135fa04` | o hash **nasce aqui**; os bytes batem com o `content-length` medido la |
| `uPlot.LICENSE` | nao consta | `8f989229...5f5b1bd` | idem |

Nenhuma divergencia a explicar, portanto. Se algum dia houver, **o recalculado e o
autoritativo** e as duas linhas ficam registradas — esconder a diferenca seria trocar a
unica prova conferivel por uma declaracao.

**A validade declarada da pesquisa era de SETE DIAS** para hashes e versoes de biblioteca
(`01-RESEARCH.md`: *"Valido ate 2026-10-01 para a pilha... 7 dias para os hashes e versoes"*).
Esse prazo passou a nao importar: a partir deste arquivo, quem vale sao os hashes acima,
recalculados aqui e presos por teste. O documento de pesquisa nao envelhece mentindo porque
deixou de ser a fonte.

### `.gitattributes` — por que existe uma linha de configuracao do git nesta pasta

`git config core.autocrlf` devolve **`true`** nesta maquina. Sem `* -text` no
`.gitattributes` desta pasta, o git converteria LF para CRLF no checkout de um clone novo —
o `.js` tem 2 LF, a licenca tem 20 — e o hash mudaria numa arvore em que **nada de errado
aconteceu**.

Isso nao e teoria: e o que o git **ja faz** com todo arquivo de texto deste repo. Medido com
`git ls-files --eol`, lado a lado:

```
i/lf    w/crlf  attr/                   requirements.txt
i/lf    w/crlf  attr/                   l2scanner/dashboard.py
i/lf    w/crlf  attr/                   l2scanner/recursos/dashboard/dashboard.js
i/lf    w/lf    attr/-text              l2scanner/recursos/dashboard/vendor/uPlot.iife.min.js
i/lf    w/lf    attr/-text              l2scanner/recursos/dashboard/vendor/uPlot.LICENSE
```

As tres primeiras linhas sao o controle: `w/crlf`, ou seja, a conversao acontece. As duas
ultimas sao esta pasta, com `attr/-text`: `w/lf`, o byte preservado. A diferenca entre as duas
metades da tabela e literalmente o arquivo `.gitattributes` ao lado.

O custo disso nao seria o falso positivo. Seria que uma troca **de verdade** (T-01-14) viraria
indistinguivel do ruido de fim de linha, e o primeiro reflexo de quem visse o vermelho seria
"e o CRLF de novo". E assim que um guarda morre. O motivo esta escrito dentro do proprio
`.gitattributes`, que e onde quem for mexer vai ler.

---

## Revisao do fonte — VEND-2

O VEND-2 manda **ler o fonte procurando primitivas de rede e de execucao dinamica**, com a
regra: zero ocorrencias aprova; **qualquer** ocorrencia exige revisao humana explicita e
registrada antes de seguir, porque *uma biblioteca de grafico nao precisa de nenhuma dessas
primitivas*.

Varredura executada em **2026-09-01**, sobre os arquivos **em disco nesta arvore** (nao sobre
o que a pesquisa baixou no scratchpad). A mesma lista de primitivas que o
`tests/test_firewall_dashboard.py` usa, item a item:

| Primitiva | O que ela faz | `uPlot.iife.min.js` | `uPlot.min.css` |
|---|---|---|---|
| `fetch(` | busca de recurso por rede, forma moderna | **0** | **0** |
| `XMLHttpRequest` | busca de recurso por rede, forma antiga | **0** | **0** |
| `navigator.sendBeacon` | envio de sinal em segundo plano | **0** | **0** |
| `sendBeacon` | idem, sem o receptor colado (o minificador aliasa) | **0** | **0** |
| `eval(` | avaliacao dinamica de codigo | **0** | **0** |
| `new Function` | construcao de funcao a partir de string | **0** | **0** |
| `Function(` | idem, sem o `new` (o minificador tambem tira) | **0** | **0** |
| `import(` | importacao dinamica, que aceita URL externa | **0** | **0** |
| `createElement('script'` | criacao de elemento de script, aspa simples | **0** | **0** |
| `createElement("script"` | idem, aspa dupla | **0** | **0** |
| `WebSocket` | conexao de soquete bidirecional | **0** | **0** |

**Veredito VEND-2: aprovado.** Zero ocorrencias em todos os arquivos de codigo vendorizados.
**Nao houve** nenhuma linha `arquivo:linha` a registrar e **nao houve** interrupcao para
decisao do usuario — esse caminho existia no plano e nao foi tomado.

### A comparacao medida que sustentou a escolha

`dygraphs 2.2.2` **reprova este mesmo portao**, com **2 ocorrencias de `XMLHttpRequest`**. O
contexto exato, extraido do minificado dela:

```
"string"==i?M.detectLineDelimiter(a)?this.loadedEvent_(a):(t=window.XMLHttpRequest?
new XMLHttpRequest:new ActiveXObject("Microsoft.XMLHTTP"),...
```

Ou seja: dygraphs aceita **uma URL como fonte de dados** e a busca sozinha. **Isso e uma
funcionalidade, e nao telemetria** — e a distincao esta registrada aqui de proposito, para
ninguem ler esta secao como acusacao. Ainda assim o portao a reprova, porque **o portao e
sobre o fonte, e nao sobre a contencao**: escolher dygraphs obrigaria a revisao humana
explicita a acontecer e a ser escrita, e uma biblioteca de grafico nao precisa dessa
primitiva para desenhar duas series.

A terceira candidata, `lightweight-charts 5.2.1`, tem zero primitivas de rede, mas foi
descartada antes disso: o seam de legitimidade a marcou **SUS** (`too-new`, tres semanas de
publicada), o que exigiria um `checkpoint:human-verify`, e ela custa **197.922 bytes** —
quase quatro vezes o uPlot.

| Candidata | Veredito de legitimidade | Primitivas de rede no fonte | Total vendorizado |
|---|---|---|---|
| **uPlot 1.6.32** (escolhida) | **OK** | **0** | **52.938 bytes** (51.081 + 1.857) |
| dygraphs 2.2.2 | OK | **2x `XMLHttpRequest`** — reprova VEND-2 | 131.481 bytes |
| lightweight-charts 5.2.1 | **SUS** (`too-new`) | 0 (mas 5x `navigator.userAgent`) | 197.922 bytes |

Nenhum pacote marcado como suposto ou suspeito entrou nesta arvore, e por isso **nenhum
checkpoint humano de legitimidade era devido** nesta fase.

### A CSP conteria o estrago, e mesmo assim nao substitui esta leitura

`connect-src 'self'` (VEND-4) barraria no navegador qualquer chamada de rede que uma versao
futura da biblioteca viesse a fazer, sem ninguem precisar reler o `.min.js`. Isso e verdade,
e e exatamente por isso que a CSP existe.

Mas as **tres camadas nao sao redundantes** — cada uma cobre o que as outras nao cobrem:

| Camada | O que ela pega | O que ela **nao** pega |
|---|---|---|
| **VEND-2**, a leitura do fonte | intencao: a primitiva esta la, hoje, e alguem viu | a proxima versao, que ninguem vai reler |
| **VEND-3**, o teste que quebra | a proxima versao — automaticamente, no CI, sem leitura humana | o que a varredura literal nao ve (nome ofuscado, string montada em pedacos) |
| **VEND-4**, a CSP no cabecalho | a chamada em **execucao**, inclusive a ofuscada | nada informa: o navegador barra em silencio, e ninguem no projeto fica sabendo |

Trocar as tres por qualquer uma delas e trocar deteccao por contencao, ou o contrario.

### A suposicao do UI-SPEC que CAIU: zoom por roda do mouse

O `01-UI-SPEC.md` afirma, por extenso, que o planejador nao precisa exigir da biblioteca nada
alem de duas series, traco solido e tracejado, cor de eixo/grade, fonte dos rotulos, zoom e
pan — porque *"toda biblioteca dessa classe faz isso com config"*.

**Medido nesta arvore, sobre o arquivo em disco: falso.** Os nomes de evento que o
`uPlot.iife.min.js` de fato cita, com a contagem:

```
click        2
dblclick     1
mousedown    1
mouseenter   1
mouseleave   1
mousemove    1
mouseup      1
resize       1
scroll       1
```

`wheel`: **0 ocorrencias**. `deltaY`: **0 ocorrencias**. Nenhum registrador de roda, em lugar
nenhum do arquivo.

E o repositorio oficial diz o mesmo em palavras: *"No built-in drag scrolling/panning"*, e o
zoom por roda **"can be added externally via the plugin/hooks API"**, com dois demos oficiais
(`zoom-wheel.html`, `zoom-touch.html`).

**Consequencia, e o que ela NAO e.** O zoom por arrasto de selecao (box zoom, com rescale) e
nativo e cobre o caso principal; o botao `Ver todo o periodo` ja esta especificado. O que
falta e so a roda, e ela vira **codigo nosso** — cerca de 30 linhas de
`over.addEventListener("wheel", ...)` recalculando a escala e chamando `setScale`, pela API
de hooks, no **plano 01-07**. A refutacao vai escrita ao lado dessas linhas tambem, para
quem for mexer no grafico nao precisar chegar ate aqui para descobrir por que elas existem.

Isto **nao** foi uma surpresa: a escolha da biblioteca foi feita **sabendo** deste preco, e
contra a alternativa que trazia a roda de graca (`lightweight-charts`) pesavam o veredito
**SUS** e os 197 KB. Zero primitivas de rede valeu mais que uma roda de mouse.

---

## Como atualizar a versao, se um dia for preciso

1. Baixar `dist/uPlot.iife.min.js`, `dist/uPlot.min.css` e `LICENSE` da nova versao.
2. Recalcular os tres SHA-256 **em disco** e trocar a tabela de VEND-1 acima, junto com os
   bytes e a data.
3. Rodar a varredura de VEND-2 de novo e trocar a tabela de contagem. Se alguma primitiva
   deixar de ser zero, **parar** e levar a decisao ao usuario, com `arquivo:linha`.
4. Refazer a medicao dos eventos, porque a secao do zoom por roda pode ter deixado de ser
   verdade — e um documento que diz o contrario do arquivo e pior que documento nenhum.
5. `python -m pytest tests/test_firewall_dashboard.py -q` tem de ficar verde. Se ficar
   vermelho no hash, e porque um dos tres passos acima foi pulado.
