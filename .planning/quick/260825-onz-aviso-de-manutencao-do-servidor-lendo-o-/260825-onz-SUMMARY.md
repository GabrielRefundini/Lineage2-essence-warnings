---
phase: quick-260825-onz
plan: 01
status: complete
subsystem: deteccao
tags: [ocr, winrt, manutencao, agenda, whatsapp, chatwoot]

requires:
  - phase: 5 — tela de login e desconexao do servidor
    provides: o reconhecimento do servidor DEPOIS que ele cai; esta tarefa e a outra metade
  - phase: 6 — a agenda como fonte de eventos
    provides: RegistroEmDisco (O_CREAT|O_EXCL, poda de 3 dias) e o molde de aviso duravel
  - phase: 7 — silenciamento por janela de evento
    provides: Categoria.SEMPRE, o unico jeito de um aviso atravessar o silencio de TvT/Prime
provides:
  - O grupo recebe UM aviso quando o banner de manutencao aparece, com o tempo como esta na tela e a hora em que o servidor cai
  - O grupo recebe um SEGUNDO aviso quando faltam 5 minutos, disparado pelo relogio ancorado — sobrevive ao banner sumir e ao OCR ficar cego
  - l2scanner/ocr.py, a primeira capacidade de ler TEXTO da tela neste projeto, com degradacao graciosa completa
  - python -m l2scanner --testar-manutencao, a ferramenta de conferencia humana
affects: [calibracao, qualquer recurso futuro que precise ler texto da tela]

actuals:
  tokens: 20586
  tasks: 4
  commits: 4

tech-stack:
  added:
    - winrt-Windows.Media.Ocr>=3.2.1 (e cinco namespaces companheiros)
  patterns:
    - "OCR isolado num modulo so, com import tardio: recurso opcional nunca derruba o produto"
    - "Ancoragem no relogio: uma leitura de tela vira um instante, e o recurso passa a viver do relogio"
    - "Consenso de duas leituras antes de anunciar qualquer coisa lida por OCR"

key-files:
  created:
    - l2scanner/manutencao.py
    - l2scanner/ocr.py
    - tests/test_manutencao.py
    - tests/test_ocr.py
  modified:
    - l2scanner/sessao.py
    - l2scanner/calibracao.py
    - l2scanner/__main__.py
    - tests/test_sessao.py
    - requirements.txt
    - vigiar-party.bat

key-decisions:
  - "A ancora no relogio (agora + tempo lido) e o link central: depois dela o recurso inteiro para de depender da tela, e e por isso que o aviso de 5 minutos sai com o jogo coberto."
  - "Consenso de DUAS leituras concordantes antes de anunciar. Custa uma cadencia (~5 s) numa contagem de 40 minutos e impede que um digito comido pelo OCR faca a party largar o farm."
  - "A normalizacao O/l/I/S -> digito vale SO em token que ja tem um digito de verdade. Normalizar o texto inteiro era o caminho obvio e quebraria a palavra `seconds`."
  - "`mainten` sozinho basta para detectar o banner; exigir tambem `server` seria PIOR (um `5erver` mal lido derrubaria tudo, e `server` aparece na frase que NAO e o banner)."
  - "VERSAO_DO_ESQUEMA da calibracao segue em 2. Um bump invalidaria o calibration.json que o usuario mediu a mao, por causa de um campo opcional."
  - "Em --replay o vigia nao e montado: uma sessao gravada nao tem banner, e os horarios do arquivo ancorariam um instante que nunca existiu."

patterns-established:
  - "Assercao estrutural com `ast`: a proibicao de importar winrt/cv2/ocr no modulo puro e um TESTE, nao um comentario."
  - "Teste de contrato honesto: `ler_texto` devolve None OU str nos DOIS ambientes — o teste nao finge provar o que nao foi provado."

requirements-completed: [QUICK-260825-onz]
---

# Quick 260825-onz: Aviso de manutencao do servidor Summary

O scanner passou a LER o banner de manutencao que o jogo mostra por cima da
party window e a avisar a party duas vezes: quando o anuncio aparece (com o
tempo exatamente como esta na tela e a hora em que o servidor cai) e quando
faltam 5 minutos — este segundo disparado pelo relogio ancorado, entao ele sai
mesmo com o banner sumido, o jogo coberto e o OCR devolvendo None.

## O problema que isto fecha

Em 2026-08-24 o scanner passou 90 s e depois 5 min repetindo "sem visao da
party" sem nunca dizer o motivo. O motivo era manutencao. A Fase 5 nasceu disso
e aprendeu a reconhecer o servidor DEPOIS que ele cai. Mas o jogo anuncia a
queda com 40 minutos de antecedencia, em texto, na tela — e o scanner
atravessava esse anuncio inteiro sem ver. Quem esta AFK perdia o loot do chao,
o buff e caia no meio de uma instance por falta de um aviso que estava escrito
na tela o tempo todo.

## Accomplishments

- **`l2scanner/manutencao.py` — a logica pura.** Reconhece o typo do jogo
  (`Maintence`) e a grafia correta (`Maintenance`) igualmente, em qualquer
  caixa; interpreta `40 minutes 26 seconds`, `5 minutes`, `26 seconds` e a
  forma com horas; normaliza as confusoes classicas do OCR (`4O` -> 40,
  `2l` -> 21) so em token que ja tem digito. Tempo por parametro, sem relogio
  proprio, sem disco, sem OCR — mesma disciplina de `agenda.py`.
- **A ancora no relogio (D-04).** Numa leitura bem sucedida
  `momento = agora + tempo_lido`, e dai em diante os dois avisos saem do
  relogio. E o que faz GOAL-02 sobreviver a cegueira.
- **Consenso, re-ancora, remarcacao e expiracao (D-05, D-10).** Uma leitura
  discrepante entre duas boas nao anuncia nada e nao derruba uma ancora ja
  confirmada; duas leituras concordantes num horario novo re-ancoram
  (manutencao remarcada); a ancora expira 10 min depois do momento e limpa os
  emitidos, senao a proxima manutencao de verdade seria detectada e nunca
  anunciada.
- **`l2scanner/ocr.py` — a primeira leitura de TEXTO deste projeto.** Unico
  arquivo que conhece WinRT, com import dentro das funcoes e checagem
  preguicosa. Sem as bindings devolve None, explica o motivo E o conserto, e o
  scanner sobe exatamente igual.
- **Costura no `Sessao` e no arranque.** Os dois avisos saem `Categoria.SEMPRE`
  (atravessam o silencio de TvT/Prime) dentro de `console.moldurar`, com o
  marcador duravel em `.agenda/` decidindo o despacho — as duas instancias do
  usuario produzem UMA mensagem so.
- **`--testar-manutencao`.** Mostra a regiao usada E de onde ela veio, salva o
  recorte em disco conferindo o retorno do `cv2.imwrite`, e imprime o texto CRU
  entre delimitadores mais o veredito do parser.

## Task Commits

| Task | Nome | Commit |
|------|------|--------|
| 1 (tracer) | O caminho inteiro, de um texto de banner ate a mensagem despachada | `974f37d` |
| 2 | O vigia completo — cadencia, consenso, re-ancora, 5 minutos e expiracao | `287e4e9` |
| 3 | `ocr.py` tolerante e a regiao do banner na calibracao | `bffb913` |
| 4 | Fiacao no arranque, `--testar-manutencao`, requirements e o `.bat` | `a2b4f44` |

## Verification

| Item | Resultado |
|------|-----------|
| `python -m pytest -q` (Python do sistema, SEM as bindings de OCR) | **683 passando** (634 antes) |
| `pytest tests/test_manutencao.py -k "Consenso or Ancora or Expiracao"` | 12 passando — a lista nominal do usuario, item a item |
| Calibracao REAL do usuario carrega | `Calibracao.carregar('calibration.json')` OK, `banner_manutencao: None` |
| `python -m l2scanner --help` mostra `--testar-manutencao` | sim |
| `vigiar-party.bat` tem UM bloco de checagem, com OCR | sim |
| Ortogonalidade: `visao.py`, `rastreador.py`, `identidade.py` intocados | **vazio** |
| Caminho REAL do OCR, no `.venv` | banner sintetico lido como `'Server Maintence 40 minutes 26 seconds'`; parser devolveu `0:40:26` |

O item mais importante e o primeiro: a suite inteira roda num Python que **nao
tem** as bindings de WinRT. Isso e a prova mais forte que existe de D-02 — o
caminho "sem OCR" nao e um caso de borda testado por educacao, e o caminho
padrao da suite.

## Deviations from Plan

None — o plano foi executado como escrito. Dois ajustes de forma, nenhum de
comportamento:

1. **`TestRegiaoDoBanner` monta a calibracao a partir da fixture real**
   (`tests/fixtures/party_estavel_com_vazamento/calibracao.json` + `replace`)
   em vez de instanciar `Calibracao` a mao. `LayoutDaParty` e `LimiaresDeCor`
   nao tem defaults, e uma calibracao inventada no teste divergiria do formato
   do usuario sem ninguem perceber — e o formato e justamente o que o teste
   guarda.
2. **A checagem do `.bat` confere DOIS modulos do winrt** (`media.ocr` e
   `graphics.imaging`), como o plano pediu em `<action>` ("Confira, alem do
   modulo de OCR, o de imagem").

## Known Stubs

Nenhum. Nenhum valor vazio codificado, nenhum TODO, nenhum teste pulado.

## Limitacao aceita, registrada de proposito

**A precisao do OCR na FONTE DO JOGO nao foi provada.** O spike leu um banner
sintetico (`cv2.putText`), e esta execucao reproduziu o mesmo resultado no
`.venv`: texto exato, typo incluso. Mas a fonte estilizada do XM Essence e
outra coisa, e so uma manutencao real (ou um PNG que o usuario salve numa)
prova o resto. **Nenhum criterio automatico deste trabalho depende disso** — e
`--testar-manutencao` existe exatamente para o usuario conferir sozinho quando
a proxima manutencao acontecer.

Aresta conhecida e aceita (D-09): as duas instancias podem implicar momentos
separados por ~1 s e, se esse instante cair em cima de um `:30`, cada uma
arredonda para um lado e o grupo recebe a mensagem em dobro. E a mesma
preferencia que o `RegistroEmDisco` ja declara — aviso duplicado e melhor que
aviso perdido, e aqui o aviso perdido e uma manutencao que ninguem soube.

## Conferencia humana pendente

1. Rodar `vigiar-party.bat` uma vez e ver o `.venv` se atualizar sozinho, com o
   arranque dizendo se o aviso de manutencao ligou ou por que nao.
2. Conferir que o `pip install` acrescentou somente pacotes `winrt-*`.
3. Rodar `vigiar-party.bat --testar-manutencao` com o jogo aberto, abrir o PNG
   salvo em `logs/` e ver se o recorte pega o lugar onde o banner aparece. Se
   nao pegar, o conserto e a chave `banner_manutencao` no `calibration.json` —
   sem tocar em codigo.
4. Na PROXIMA MANUTENCAO REAL, rodar `--testar-manutencao` com o banner na tela
   e comparar o texto lido com o da tela.

## Self-Check: PASSED

- `l2scanner/manutencao.py` — FOUND
- `l2scanner/ocr.py` — FOUND
- `tests/test_manutencao.py` — FOUND
- `tests/test_ocr.py` — FOUND
- commits `974f37d`, `287e4e9`, `bffb913`, `a2b4f44` — FOUND
