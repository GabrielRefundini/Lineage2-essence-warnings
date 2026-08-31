---
slug: sonda-do-fundo-recusa-nome-comprido
workstream: mercado
created: 2026-08-31
status: investigating
severity: alta
hypothesis: >
  A sonda de oclusao (mercado_sonda_do_fundo) esta geometricamente EM CIMA da
  metade direita da coluna do nome. Nome comprido invade a faixa, o fundo deixa
  de ser uniforme, e a linha e recusada como "ocluida" sem haver tooltip nenhuma.
next_action: >
  Reproduzir a recusa sobre um frame com nome comprido e MEDIR onde uma faixa de
  fundo fica limpa no pior caso, em vez de escolher a posicao a olho.
---

# A sonda de oclusao recusa linhas de nome comprido

## Sintoma, medido em campo

Sessao real do usuario, 2026-08-31 13:39, aba **Enhancement > Scrolls** (layout
`negociacao`, o mesmo calibrado):

    paginas lidas                    0
    paginas PERDIDAS                31
    ticks com o painel aberto       32
    frames congelados                0
    linhas descartadas             129
      oclusao                      104
      numero                        20
      discordancia-entre-escalas     5

**Nenhuma observacao gravada.** O `observacoes.csv` saiu com so o cabecalho.

## A correlacao

As linhas recusadas por `oclusao: fundo nao uniforme` foram **sempre** as de
indice 5, 7, 8 e 9 (base zero) — as **quatro** linhas de
`Protecting Scroll: Enchant C-grade Armor` (40 caracteres).

As **seis** linhas de `Scroll: Enchant D-grade Weapon` (29 caracteres) passaram
todas, em todos os 32 ticks.

Correlacao perfeita com o COMPRIMENTO DO NOME. Nao com posicao, nao com a
listra alternada, nao com a cor do icone.

## A geometria, medida do calibration.json

    borda esquerda da grade (dx)          -427
    coluna do NOME, no recorte da linha   42 .. 366   (largura 324)
    mercado_sonda_do_fundo                207 .. 417
    SOBREPOSICAO                          207 .. 366  = 159 px = 49% da coluna

A docstring de `linha_ocluida` (`l2scanner/mercado_leitura.py`, ~1207) afirma que
a sonda ve *"entre o fim dos nomes e o inicio dos numeros"*. **A geometria real
contradiz a docstring**: ela ve a metade direita da propria coluna do nome.

E nao ha vao para onde mover: a coluna de quantidade comeca em **366**,
exatamente onde a do nome termina.

## O ultimo elo

4 de 10 linhas recusadas => 6 aceitas.
`mercado_minimo_de_linhas_comparadas` = **7**.

Falta exatamente UMA linha. Por isso toda pagina e perdida.

## O leitor NAO esta errado

A linha 3 foi lida como `total=674 unitario=134 quantidade=5`; a tela mostrava
**6,74 / 1,34 / 5**. Digito por digito correto. O defeito e so a peneira.

## Restricoes do conserto

- **NAO afrouxar a sonda.** Ela e a guarda contra tooltip SEMITRANSPARENTE — a
  tooltip nao apaga o numero, ela o MISTURA, e numero misturado produz glifo
  plausivel com valor errado e confianca alta. E o modo de falha do incidente 27x.
- **NAO baixar o piso de 7** — mascararia o defeito em vez de conserta-lo.
- **A nova posicao da faixa precisa ser MEDIDA** contra frames com nome comprido,
  nunca escolhida a olho. O limiar mora no `calibration.json`, nunca no fonte.
- Se a conclusao for "nao existe faixa horizontal limpa no pior caso", isso e um
  achado legitimo e muda o desenho do sinal — reporte em vez de forcar.

## Evidencia que talvez falte

As gravacoes em `recordings/` sao da aba **Equipment**, onde os nomes sao curtos
(`Fire Spirit Evolution Stone`, `Phantom Mask Sealed`). **Pode nao existir frame
gravado com nome comprido.** Se for esse o caso, o portao e humano: o usuario
roda `--record` na aba Enhancement > Scrolls. Peca em vez de inventar frame.

## Fora de alcance

`rastreador.py` e o gate de brilho da barra propria em `visao.py` — intocaveis.
Nao escrever em `.mercado/` nem em `calibration.json`. `recordings/` e
somente-leitura e NUNCA usar glob nela (a pasta `pre-voo` sozinha tem 1502 PNGs).
Outro agente trabalha nos workstreams `tiat`/`identidade` nesta mesma arvore.
