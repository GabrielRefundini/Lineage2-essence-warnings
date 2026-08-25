---
phase: quick-260825-bmw
plan: 01
subsystem: calibrador
tags: [calibracao, honestidade-de-erro, io, regressao]
status: complete

requires:
  - l2scanner/calibrar.py (conferir_visualmente, _conferencia_do_solo, main --solo)
provides:
  - "_gravar_conferencia(imagem) -> Path | None — unico ponto de escrita de imagem do modulo"
  - "_texto_final_do_solo(caminho: Path | None) -> None — bloco final do --solo, agora testavel"
affects:
  - "l2scanner/calibrar.py: _conferencia_do_solo passou a devolver Path | None"

tech-stack:
  added: []
  patterns:
    - "Falha de I/O silenciosa (retorno booleano ignorado) tratada como mentira do produto, nao como detalhe"
    - "Mensagem condicionada ao artefato: nenhum texto cita arquivo que nao foi escrito"
    - "Horario tirado do mtime do arquivo, nunca do relogio da chamada"

key-files:
  created:
    - tests/test_conferencia_gravada.py
  modified:
    - l2scanner/calibrar.py

decisions:
  - "O horario vem do mtime, nao do relogio: a pergunta do usuario e 'essa imagem e nova?' e so o mtime responde"
  - "As mensagens de falha nao citam nome de arquivo nenhum — citar seria repetir o bug uma linha acima"
  - "O teste de regressao exige caminho ABSOLUTO, porque a raiz do repo tem um calibracao-conferencia.png velho que faria um nome solto passar por acidente"

metrics:
  duration: ~25min
  completed: 2026-08-25
  tasks: 2
  commits: 2
  tests_added: 11
  tests_total: 466

actuals:
  tokens: 11900
  tasks: 2
  commits: 2
---

# Quick 260825-bmw: Calibrar — a imagem de conferencia nao era Summary

O calibrador parou de anunciar imagem de conferencia que ele nao conseguiu gravar: agora
ele entrega um arquivo alternativo com horario no nome quando o padrao esta travado, ou
diz alto que NAO ha imagem — e toda mensagem cita o caminho completo e o horario do
arquivo realmente escrito.

## O que foi construido

**`_gravar_conferencia(imagem) -> Path | None`** (`l2scanner/calibrar.py:381`) e o unico
ponto do modulo que escreve imagem. Ela tenta `RAIZ / "calibracao-conferencia.png"`; se
falhar, avisa que o arquivo esta travado e sugere fechar o visualizador de fotos, e tenta
`RAIZ / f"calibracao-conferencia-{HHMMSS}.png"`; se as duas falharem, devolve `None` e
diz que nao ha imagem para conferir.

A tentativa de escrita fica numa funcao interna com `try/except Exception` em volta do
`cv2.imwrite`, para que o `False` documentado e uma excecao inesperada caiam no MESMO
caminho de falha. Tratar so um dos dois deixaria metade do problema calada — que e
exatamente o defeito original.

`RAIZ` e lido como global no corpo da funcao (nao capturado em argumento com valor
padrao), o que e o que permite ao teste redirecionar toda a escrita para um `tmp_path`.

**`conferir_visualmente`** passou a condicionar TODO o texto seguinte ao retorno. A
legenda de cores saia incondicionalmente, e era ela que dava ar de que algo tinha sido
desenhado em algum lugar.

**`_conferencia_do_solo`** deixou de gravar por conta propria — desenha e delega — e agora
devolve `Path | None`.

**`_texto_final_do_solo(caminho)`** foi extraida do `main()` porque o bloco nao era
testavel de dentro dele. A frase "CONFIRA a imagem calibracao-conferencia.png" era
impressa incondicionalmente, com o nome do arquivo escrito a mao no codigo. Sem imagem,
o texto agora diz que ninguem conferiu o retangulo — e o alerta sobre a barra do alvo
selecionado fica mais forte, porque virou o unico aviso restante.

## O RED, registrado

O teste de regressao foi visto falhando antes da correcao, das duas formas exigidas.

Coleta do arquivo de teste contra o codigo de ontem:

    ImportError: cannot import name '_gravar_conferencia' from 'l2scanner.calibrar'

E a mentira em si, reproduzida contra o `conferir_visualmente` pre-correcao com `RAIZ`
apontando para uma pasta inexistente:

    PNGs citados na saida: ['calibracao-conferencia.png']
      'calibracao-conferencia.png': absoluto=False existe_no_cwd=True

    Imagem de conferencia: calibracao-conferencia.png
      amarelo = ancora da janela
      ...
    ABRA essa imagem e confira se os retangulos batem com a party window.

Nada foi gravado, e mesmo assim o calibrador mandou abrir a imagem.

**`existe_no_cwd=True` e o achado que vale mais que o teste.** O arquivo que o calibrador
citava EXISTE na raiz do repositorio — sobrou de uma rodada anterior. E por isso que o bug
nunca foi obvio: o usuario abria o nome anunciado, a imagem abria normalmente, e ele
conferia uma calibracao ANTIGA achando que estava conferindo a nova. Isso obrigou o teste
a exigir caminho **absoluto**, nao so existencia: uma checagem ingenua de `Path(nome).exists()`
teria passado por acidente contra o arquivo velho, repetindo o bug dentro do teste
que deveria pega-lo.

## Cobertura

11 testes novos em `tests/test_conferencia_gravada.py`: gravacao normal, caminho absoluto
+ horario na saida, destino travado por arquivo somente-leitura (com `pytest.skip` se o SO
ignorar a permissao), destino travado por diretorio (o caso deterministico em qualquer SO),
ausencia total de destino, os dois cenarios do modo solo, o texto final do `--solo`, e um
teste estrutural que compara as ocorrencias de `imwrite` no modulo com as de dentro do
auxiliar — se alguem duplicar a gravacao de novo, ele cai.

## Deviations from Plan

### 1. [Rule 3 - Blocking] O teste estrutural foi para o commit da Task 2, nao da Task 1

- **Onde:** o plano lista o teste de "ponto de escrita unico" no `<behavior>` da Task 1.
- **Problema:** ele compara o total de `imwrite` do modulo com o de dentro do auxiliar. Ao
  fim da Task 1 o total era 2 e o do auxiliar 1, porque a Task 1 proibe explicitamente
  mexer em `_conferencia_do_solo`. O teste so pode passar depois da Task 2.
- **Decisao:** o teste viajou junto com a mudanca que ele guarda, para nenhum commit ficar
  vermelho. Os tres testes do modo solo seguiram o mesmo caminho, pela mesma razao.
- **Commits:** `ccb9185` (Task 1, 7 testes), `f4dbe6b` (Task 2, +4 testes).

### 2. [Rule 1 - Bug] O comentario explicativo derrubava o teste estrutural

- **Encontrado em:** Task 2, na primeira rodada.
- **Problema:** o guarda conta ocorrencias TEXTUAIS de `imwrite` no fonte do modulo. O
  comentario que eu escrevi em `_conferencia_do_solo` explicando "era aqui que morava o
  segundo `cv2.imwrite`" contava como uma terceira ocorrencia: `assert 3 == 2`.
- **Correcao:** o comentario passou a dizer "segundo ponto de escrita" sem citar o nome da
  funcao, e ganhou uma linha explicando ao proximo leitor por que o nome nao aparece ali.
  Reescrever o comentario e melhor que afrouxar o guarda.
- **Arquivo:** `l2scanner/calibrar.py:544-548` — **Commit:** `f4dbe6b`.

### 3. [Ajuste de texto] A mensagem de "travado" foi suavizada

O plano pede uma mensagem dizendo que o arquivo esta travado e sugerindo fechar o
visualizador. Como esse mesmo caminho tambem e percorrido quando a pasta simplesmente nao
existe, o texto ficou "O motivo mais comum e ele estar aberto no visualizador de fotos" em
vez de afirmar a causa. Numa tarefa cujo assunto e o produto parar de afirmar o que nao
sabe, afirmar a causa errada seria incoerente.

## Verificacao

| Item | Resultado |
|---|---|
| `python -m pytest tests/ -q` | **466 passed** em 17,06 s |
| Linha de base sem o arquivo novo | 455 passed — nenhuma regressao |
| `grep -n imwrite l2scanner/calibrar.py` | 2 ocorrencias, ambas dentro de `_gravar_conferencia` (linhas 393 e 413) |
| Portao estrutural do plano | `total=2, auxiliar=2` — ponto de escrita unico OK |
| Conferencia manual do texto | nenhuma mensagem cita arquivo nao escrito (saida real inspecionada nos dois cenarios de falha) |

Observacao sobre a contagem: o `STATE.md` fala em 446 testes e o plano repete o numero; a
suite real ja estava em **455** antes desta tarefa. Os 11 novos levam a 466. Nenhum teste
existente quebrou — a diferenca e do numero registrado no STATE, nao da suite.

## Known Stubs

Nenhum.

## Threat Flags

Nenhum. `T-quick-01` foi mitigado como planejado: os dois destinos derivam de `RAIZ`,
nenhuma entrada do usuario entra na funcao, e `*.png` ja esta no `.gitignore`.

## Notas para o proximo

- `.gsd/` aparece como diretorio nao rastreado no `git status`. Nao e desta tarefa e nao
  foi tocado; se for scaffolding de runtime, merece uma linha no `.gitignore`.
- A raiz do repo tem um `calibracao-conferencia.png` de uma calibracao antiga. Ele e
  ignorado pelo git, mas e literalmente o arquivo que enganava o usuario — apagar da uma
  garantia a mais na proxima calibracao manual.

## Self-Check: PASSED

- FOUND: `l2scanner/calibrar.py`
- FOUND: `tests/test_conferencia_gravada.py`
- FOUND: commit `ccb9185`
- FOUND: commit `f4dbe6b`
