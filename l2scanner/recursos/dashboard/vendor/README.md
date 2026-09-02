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
| VEND-2 | a secao **Revisao do fonte** deste arquivo — ainda NAO escrita neste commit; ela e a tarefa seguinte |
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
