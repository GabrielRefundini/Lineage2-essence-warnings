"""Resgata de `recordings/` os recortes que a leitura da renda usa como fixtura.

POR QUE ISTO E UM SCRIPT DE `tools/` E NAO UMA FUNCAO DENTRO DO TESTE
=====================================================================
`recordings/` e gitignored. Um teste que lesse de la ficaria verde nesta
maquina e amarelo em todo clone — e o portao que prende isso e um grep dentro
de `tests/test_renda_tracer.py` procurando a string `recordings/`. Um trecho de
resgate morando naquele arquivo teria de nomear a pasta para funcionar, e
derrubaria o proprio portao que existe para provar que nenhum teste depende
dela.

As duas coisas nao cabem no mesmo arquivo, e quem cede e o resgate: ele roda
UMA vez, na mao de quem tem as gravacoes, e o que fica versionado sao os PNGs
que ele produziu. `tools/medir_largura_de_run.py` e `tools/record.py` ja moram
aqui pela mesma razao, e este script herda a disciplina delas: NENHUM teste o
importa.

O QUE ELE RESGATA, E POR QUE CADA UM
====================================
A fonte principal e a gravacao de campo de 2026-09-02, com as DUAS instancias
vivas. Ela e a unica desta arvore que mostra o NIVEL, e a unica que tem verdade
de campo escrita (`01-MEDICOES-DE-CAMPO.md`):

    Faerlina    nivel 67   EXP 8,0012%    adena 13.160.684
    Yazalaque   nivel 69   EXP 76,6646%   adena 1.696.020

Uma fixtura sem verdade de campo prova que o codigo faz alguma coisa; uma com
verdade de campo prova que ele faz a coisa certa.

As gravacoes ANTIGAS nao sao rascunho: elas cobrem estados que a de campo nao
tem — o EXP que o recorte cru PERDE (M4), o EXP que so a mascara recupera (M5),
os dois caminhos de leitura que DISCORDAM num digito (M6) e o campo da adena em
que o recorte cru nao mostra a adena (M7).

OS RETANGULOS SAO OS MEDIDOS, E O DA ADENA MUDOU DUAS VEZES
============================================================
`barra_direita` e `1540,1358 160x34` — o crop do M-O, escolhido por busca sobre
QUATRO frames de campo — e nunca o `1200,1368 520x24` da era do OCR nem o
`1500,1360 200x32` que o corrigiu.

O `520x24` morreu porque carregava cinco campos e meia duzia de icones. O
`200x32` morreu pelo mesmo motivo, em escala menor, e a morte dele e o registro
de uma licao repetida: ele foi medido em UMA fixtura (a Yazalaque das 00h45,
com L-Coin `9.790`, curta o bastante para terminar antes de `x=1500`) e aquilo
nao era margem, era sorte — o mesmo tipo de sorte que a banda de largura 1 do
M-E ja tinha flagrado.

Medido nas quatro fixturas com `segmentar_glifos_no_brilho` em `vmin` 180, 185 e
190, o `1500,1360 200x32` devolve um run de largura 17 NO MEIO das quatro: e o
icone da moeda de ouro, e a peneira de forma da leitura por glifo — um run largo
em cada ponta e nada largo no meio — recusaria em TODAS elas.

O `1540,1358 160x34` devolve, nas quatro e nos tres pisos, exatamente a forma
que a peneira pede, e a contagem do meio bate com a verdade de campo caractere
por caractere:

    00h45 faerlina   [14, 4, 4, 1, 4, 4, 4, 1, 4, 4, 6, 15]  meio=10  13,160,684
    00h45 yazalaque  [14, 4, 1, 4, 4, 4, 1, 4, 4, 4, 15]     meio=9   1,696,020
    09h30 faerlina   [14, 4, 4, 1, 4, 4, 6, 1, 5, 4, 4, 15]  meio=10  15,134,779
    09h30 yazalaque  [14, 6, 1, 6, 4, 4, 1, 4, 4, 4, 15]     meio=9

(Estas larguras estao na convencao de `segmentar_glifos_no_brilho`, que e
`fim - inicio` — a MESMA de `larguras_de_molde`, e portanto a que a peneira do
`01-05` vai usar. O `01-MEDICOES-DE-CAMPO.md` relata os mesmos runs numa
convencao INCLUSIVA, um a mais em cada largura. As duas descrevem a mesma tela;
quem escrever a peneira precisa saber em qual esta, porque uma guarda escrita na
convencao errada erra por um pixel em todo glifo.)

E O DIGITO DESTA FONTE NAO TEM UMA LARGURA SO. Nesta convencao ele sai com 4, 5
ou 6 px; a virgula com 1; os icones das pontas com 14 e 15. Uma peneira que
exigisse UMA largura de digito recusaria `15,134,779` inteiro.

A altura da `barra_esquerda` e 24 e nao 26: `1368 + 26 = 1394 > 1392`, e numpy
encurta o recorte EM SILENCIO (M12).

COMO RODAR

    .venv/Scripts/python.exe tools/resgatar_fixturas_da_renda.py

Ele nao sobrescreve nada em silencio: diz o que gravou, e reclama alto da
gravacao que nao encontrar.

`--gravacoes CAMINHO` existe porque `recordings/` e gitignored e portanto NAO
acompanha um worktree do git: quem resgata a partir de uma arvore de trabalho
paralela aponta para a pasta do checkout principal em vez de duplicar 5 PNGs de
janela inteira. O default continua sendo `recordings/` ao lado deste arquivo.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
GRAVACOES = RAIZ / "recordings"
DESTINO = RAIZ / "tests" / "fixtures" / "renda"

# Os retangulos da secao "Numeros medidos" do 01-01-PLAN.md, em coordenadas da
# JANELA — o frame da `JanelaSource` e janela-relativo e mede 1720x1392 (M-A).
BARRA_ESQUERDA = (0, 1368, 520, 24)  # o EXP; o nome mente e a mentira esta documentada
BARRA_DIREITA = (1540, 1358, 160, 34)  # a ADENA; o crop do M-O, medido em QUATRO frames
NIVEL_FAERLINA = (246, 736, 30, 20)  # M-F
NIVEL_YAZALAQUE = (236, 750, 30, 20)  # M-F: 14 px abaixo e 10 a direita do outro

GEOMETRIA_DA_JANELA = (1720, 1392)  # (largura, altura)

# (arquivo de saida, gravacao, frame, retangulo)
RESGATES = [
    # --- a gravacao de CAMPO, com as duas instancias vivas e o nivel visivel ---
    (
        "campo_faerlina_f000__barra_esquerda.png",
        "20260902-004500-renda-duas-instancias/frame_000000_faerlina.png",
        BARRA_ESQUERDA,
    ),
    (
        "campo_faerlina_f000__barra_direita.png",
        "20260902-004500-renda-duas-instancias/frame_000000_faerlina.png",
        BARRA_DIREITA,
    ),
    (
        "campo_faerlina_f000__nivel.png",
        "20260902-004500-renda-duas-instancias/frame_000000_faerlina.png",
        NIVEL_FAERLINA,
    ),
    (
        "campo_yazalaque_f001__barra_esquerda.png",
        "20260902-004500-renda-duas-instancias/frame_000001_yazalaque.png",
        BARRA_ESQUERDA,
    ),
    (
        "campo_yazalaque_f001__barra_direita.png",
        "20260902-004500-renda-duas-instancias/frame_000001_yazalaque.png",
        BARRA_DIREITA,
    ),
    (
        "campo_yazalaque_f001__nivel.png",
        "20260902-004500-renda-duas-instancias/frame_000001_yazalaque.png",
        NIVEL_YAZALAQUE,
    ),
    # --- o que a gravacao de campo NAO substitui ---
    # M2: o EXP legivel no recorte CRU, `57.9749%`.
    (
        "aba_para_calibrar_f000__barra_esquerda.png",
        "20260901-164159-aba-para-calibrar/frame_000000.png",
        BARRA_ESQUERDA,
    ),
    # M7: a adena que o recorte CRU nao mostra.
    (
        "aba_para_calibrar_f000__barra_direita.png",
        "20260901-164159-aba-para-calibrar/frame_000000.png",
        BARRA_DIREITA,
    ),
    # M4/M5: o EXP que SOME no cru e que a mascara recupera.
    (
        "adena_diagnostico_f005__barra_esquerda.png",
        "20260901-172911-adena-diagnostico/frame_000005.png",
        BARRA_ESQUERDA,
    ),
    # M6: os dois caminhos de leitura que discordam num digito da segunda casa.
    (
        "mercado_farm_com_party_f000__barra_esquerda.png",
        "20260828-063240-mercado-farm-com-party/frame_000000.png",
        BARRA_ESQUERDA,
    ),
    # --- a SEGUNDA rodada de campo, 8h30 depois, com outro cenario atras da
    # barra semitransparente. Ela e a que REFUTOU o retangulo `1500,1360
    # 200x32` (M-N): a L-Coin da Faerlina foi de `13.091` para `14.465` e o
    # recorte antigo passou a pegar a cauda dela mais o icone da moeda. Sem
    # estas duas fixturas versionadas, a correcao do M-O seria uma afirmacao de
    # prosa que ninguem conseguiria reproduzir a partir do clone.
    (
        "segundo_cenario_faerlina__barra_direita.png",
        "20260902-093000-renda-segundo-cenario/frame_faerlina.png",
        BARRA_DIREITA,
    ),
    (
        "segundo_cenario_yazalaque__barra_direita.png",
        "20260902-093000-renda-segundo-cenario/frame_yazalaque.png",
        BARRA_DIREITA,
    ),
    (
        "segundo_cenario_yazalaque__barra_esquerda.png",
        "20260902-093000-renda-segundo-cenario/frame_yazalaque.png",
        BARRA_ESQUERDA,
    ),
]

# A montagem sai dos recortes da Faerlina, colados nas posicoes de calibracao.
MONTAGEM = "montagem_da_janela.png"
PECAS_DA_MONTAGEM = [
    ("campo_faerlina_f000__barra_esquerda.png", BARRA_ESQUERDA),
    ("campo_faerlina_f000__barra_direita.png", BARRA_DIREITA),
]


def _recortar(frame: np.ndarray, retangulo) -> np.ndarray:
    esquerda, topo, largura, altura = retangulo
    if topo + altura > frame.shape[0] or esquerda + largura > frame.shape[1]:
        raise SystemExit(
            f"O retangulo {retangulo} nao cabe num frame {frame.shape[1]}x"
            f"{frame.shape[0]}. numpy encurtaria o recorte EM SILENCIO (M12)."
        )
    return frame[topo : topo + altura, esquerda : esquerda + largura]


def main(argv: list[str] | None = None) -> int:
    analisador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analisador.add_argument(
        "--gravacoes",
        type=Path,
        default=GRAVACOES,
        help="a pasta recordings/ de onde resgatar (default: a do repositorio)",
    )
    args = analisador.parse_args(argv)
    gravacoes = args.gravacoes

    DESTINO.mkdir(parents=True, exist_ok=True)

    for saida, origem, retangulo in RESGATES:
        caminho = gravacoes / origem
        if not caminho.exists():
            print(f"NAO ENCONTREI {caminho}", file=sys.stderr)
            return 1
        frame = cv2.imread(str(caminho))
        if frame is None:
            print(f"NAO CONSEGUI LER {caminho}", file=sys.stderr)
            return 1
        recorte = _recortar(frame, retangulo)
        cv2.imwrite(str(DESTINO / saida), recorte)
        print(f"{saida}  <- {origem}  {retangulo}  {recorte.shape}")

    # A MONTAGEM NAO E UMA CAPTURA, E ISSO VAI ESCRITO ONDE ELA E USADA.
    #
    # Ela e uma tela preta do tamanho da janela com os recortes REAIS colados
    # nas posicoes de calibracao. O que ela prova: geometria, posicao e o
    # caminho de ponta a ponta do comando de leitura unica. O que ela NAO
    # prova: nada sobre o resto da tela do jogo, que aqui e preto.
    #
    # A REGIAO DO NIVEL FICA PRETA DE PROPOSITO, e o motivo MUDOU. Antes ela
    # era preta porque nenhuma gravacao continha o nivel; hoje duas contem, e
    # ela e preta porque o caso de CAMPO VAZIO tambem precisa de uma fixtura —
    # e as de campo entregam o caso oposto. As duas existem, e cada uma prova
    # uma coisa.
    largura, altura = GEOMETRIA_DA_JANELA
    montagem = np.zeros((altura, largura, 3), dtype=np.uint8)
    for peca, retangulo in PECAS_DA_MONTAGEM:
        recorte = cv2.imread(str(DESTINO / peca))
        if recorte is None:
            print(f"NAO CONSEGUI RELER {peca}", file=sys.stderr)
            return 1
        e, t, la, al = retangulo
        montagem[t : t + al, e : e + la] = recorte
    cv2.imwrite(str(DESTINO / MONTAGEM), montagem)
    print(f"{MONTAGEM}  <- montagem {largura}x{altura}, regiao do nivel PRETA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
