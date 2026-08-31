"""O REPLAY que transforma as gravacoes do censo num `observacoes.csv` de verdade.

O QUE ESTA FERRAMENTA NAO E — e esta e a confusao previsivel
=============================================================
Ela NAO e o modo `--mercado`. Aquilo e DETC-02, da Fase 4, e ainda nao existe.
Esta ferramenta le imagens de disco, nao captura tela, nao roda no laco do
scanner, nao acrescenta flag nenhuma a `l2scanner/__main__.py` e nao toca
`l2scanner/rastreador.py` nem o gate de brilho da barra propria em
`l2scanner/visao.py`.

Ela e de `tools/`, que e onde este repositorio ja poe o codigo que passa gravacao
REAL pelo pipeline para PRODUZIR DADO — `medir_oclusao.py`,
`medir_agrupamento_de_nome.py`, `medir_brilho_da_quantidade.py`.

POR QUE ELA EXISTE
===================
A Fase 3 entrega o registro de observacoes SEM CHAMADOR, de proposito. Mas os
criterios de sucesso da fase sao todos "o usuario abre, importa, conta e ve" —
e sem um arquivo com dado de verdade eles nao teriam sobre o que acontecer. Esta
ferramenta e o caminho pelo qual esse arquivo nasce.

Ela e tambem a UNICA forma de o usuario VER o aviso alto do PERS-03 nesta fase.
Ela monta o registro pela MESMA `montar_registro_de_mercado` do 03-02 — nunca
construindo `RegistroDeObservacoes` a mao — entao o texto que o usuario ve
quebrando a saida de proposito e byte a byte o texto que a Fase 4 vai mostrar.
Duas versoes da mesma frase e como elas divergem.

A SAIDA E OBRIGATORIA, E A PASTA DE PRODUCAO E RECUSADA
========================================================
`--saida` nao tem padrao, e isso e deliberado. Uma linha derivada de replay
carrega o carimbo de AGORA sobre um preco que foi visto dias atras. Misturar
isso com o registro ao vivo seria exatamente a confusao entre bancada e producao
que o CONTEXT proibe quando recusa colunas de gravacao e de frame (D-04). Um
padrao apontando para `.mercado/` faria a contaminacao ser o comportamento de
quem so digita o comando.

O CONJUNTO DE MEDICAO E FECHADO, E ISSO E UMA GUARDA
=====================================================
`recordings/` tem 16 pastas; o censo de 335 frames da pesquisa cobriu 8, e sao so
essas que entram. A lista e IMPORTADA de `tools/medir_oclusao.py` — redigita-la
criaria uma segunda verdade sobre o mesmo conjunto, e um glob sobre a pasta
arrastaria as 8 que estao FORA do censo, incluindo a `pre-voo`, que e de outro
dia e sozinha tem 1.502 PNGs. `recordings/` e aberta SOMENTE PARA LEITURA: nada
e escrito sob ela, nunca.

Uso (no checkout PRINCIPAL — `recordings/` e gitignored e nao se materializa em
worktree, e o motor de OCR so responde no `.venv`):

    .venv/Scripts/python.exe tools/gerar_observacoes_do_censo.py
        --saida C:/temp/portao-fase3

    ... e com `--gravacao <nome>` (repetivel) para rodar so parte do censo,
    quando dez minutos for demais e duas paginas bastarem.

Sai com 0 quando viu observacao — nova ou ja conhecida — e diferente de zero
quando nao viu nenhuma, quando a saida foi recusada, ou quando o registro nao
montou.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from l2scanner import ocr  # noqa: E402
from l2scanner.__main__ import (  # noqa: E402
    configurar_log,
    montar_registro_de_mercado,
)
from l2scanner.calibracao import Calibracao, CalibracaoInvalida  # noqa: E402
from l2scanner.mercado_pagina import LeitorDePagina  # noqa: E402
from l2scanner.mercado_registro import (  # noqa: E402
    ARQUIVO_DE_OBSERVACOES,
    PASTA_DO_MERCADO,
)
from l2scanner.mercado_visao import (  # noqa: E402
    RastreioDoPainel,
    ancoras_de_calibracao,
)
from l2scanner.relogio import Relogio  # noqa: E402


def _carregar_o_censo():
    """A lista das 8 gravacoes vive numa ferramenta so, e e importada daqui."""
    caminho = RAIZ / "tools" / "medir_oclusao.py"
    spec = importlib.util.spec_from_file_location("medir_oclusao", caminho)
    modulo = importlib.util.module_from_spec(spec)
    # Registrar ANTES de executar: `@dataclass` resolve as anotacoes por
    # `sys.modules[cls.__module__]`, e sem isto ele encontra None.
    sys.modules["medir_oclusao"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


_oclusao = _carregar_o_censo()
GRAVACOES_DO_CENSO = _oclusao.GRAVACOES_DO_CENSO


# Os codigos de saida, nomeados. Um numero cru no `return` obriga quem le o
# roteiro humano a contar linhas para descobrir o que 5 quer dizer.
SAIDA_OK = 0
SAIDA_RECUSADA = 2
SAIDA_SEM_GRAVACOES = 3
SAIDA_CENSO_INCOMPLETO = 4
SAIDA_SEM_OCR = 5
SAIDA_SEM_CALIBRACAO = 6
SAIDA_SEM_REGISTRO = 7
SAIDA_SEM_OBSERVACAO = 8


# ---------------------------------------------------------------------------
# A GUARDA DA SAIDA — a primeira coisa que roda, antes de qualquer `mkdir`
# ---------------------------------------------------------------------------


def _normalizado(caminho) -> str:
    """O caminho num formato so, para a comparacao poder ser de igualdade.

    `resolve()` desfaz o `..` do meio e transforma relativo em absoluto;
    `os.path.normcase` troca `/` por `\\` e baixa a caixa NO WINDOWS, e e um
    no-op onde a caixa importa de verdade. Os dois juntos sao a razao de a
    comparacao ser sobre CAMINHOS e nao sobre TEXTO: no Windows a mesma pasta
    chega escrita de tres jeitos, e uma comparacao de string aprovaria dois.
    """
    return os.path.normcase(str(Path(caminho).resolve()))


def razao_para_recusar_a_saida(saida) -> str | None:
    """A pasta de producao do registro nao pode ser saida do replay. Ou `None`.

    ELA NAO IMPRIME E NAO CRIA NADA — e uma pergunta, e quem chama decide. Isso
    e o que permite chama-la ANTES de qualquer `mkdir`, que e o unico momento em
    que a guarda ainda vale alguma coisa.

    A RAZAO POR EXTENSO, e nao so "recusado": uma linha derivada de replay
    carrega o carimbo de AGORA sobre um preco que foi visto dias atras. O
    registro de producao e dado acumulado e sem desfazer, e o CONTEXT ja recusou
    colunas de gravacao e de frame justamente para o arquivo nao virar um lugar
    onde bancada e producao se misturam (D-04).

    A subpasta e recusada junto com a raiz: deixar `--saida .mercado/rascunho`
    passar poria o arquivo dentro da pasta que o usuario abre no Sheets.
    """
    alvo = _normalizado(saida)
    producao = _normalizado(PASTA_DO_MERCADO)
    if alvo != producao and not alvo.startswith(producao + os.sep):
        return None
    return (
        "SAIDA RECUSADA: " + str(saida) + " e (ou esta dentro de) a pasta de "
        "PRODUCAO do registro, " + str(PASTA_DO_MERCADO) + ".\n"
        "  Uma linha derivada de replay carrega o carimbo de AGORA sobre um "
        "preco que foi visto dias atras.\n"
        "  O registro de producao e dado acumulado e SEM DESFAZER: misturar os "
        "dois estragaria o arquivo para sempre.\n"
        "  Aponte --saida para uma pasta de rascunho, por exemplo "
        "C:/temp/portao-fase3."
    )


# ---------------------------------------------------------------------------
# A COSTURA DE GRAVACAO — a unica parte testavel sem OCR e sem `recordings/`
# ---------------------------------------------------------------------------


@dataclass
class Contagem:
    """O que a costura viu, em tres numeros que nao se disfarcam um do outro.

    `duplicadas` e `perdidas` sao FATOS DIFERENTES e por isso sao campos
    diferentes. `registrar` devolve `False` nos dois casos — chave ja conhecida
    e registro desligado — e somar os dois faria o relatorio dizer "descartei
    300 duplicadas" sobre uma sessao em que o disco encheu na terceira linha.
    """

    observacoes: int = 0
    duplicadas: int = 0
    perdidas: int = 0
    series: set[str] = field(default_factory=set)

    def absorver(self, outra: "Contagem") -> None:
        self.observacoes += outra.observacoes
        self.duplicadas += outra.duplicadas
        self.perdidas += outra.perdidas
        self.series |= outra.series


def gravar_as_paginas(paginas, registro, relogio) -> Contagem:
    """Cada linha de cada pagina aceita vira uma tentativa de observacao.

    ELA LE SO `pagina.linhas`. Os campos `descartadas` e `motivos` da pagina
    aceita sao proibidos no CSV pela decisao da Fase 2: escrever a linha
    recusada misturaria descarte com dado, que e a confusao que a falha fechada
    existe para evitar.

    O CARIMBO VEM DO RELOGIO POR PARAMETRO (D-16). Este modulo nunca chama o
    relogio do sistema: num dual boot a hora crua do Windows esta errada, e o
    `Relogio` ancorado do projeto e o que corrige isso. Sem ancora ele degrada
    para a hora do Windows, que e o caminho HONESTO — e o proprio modulo de
    relogio o documenta e avisa em WARNING.
    """
    contagem = Contagem()
    for pagina in paginas:
        for linha in pagina.linhas:
            contagem.series.add(linha.chave_da_serie)
            if registro.registrar(linha, relogio.agora()):
                contagem.observacoes += 1
            elif registro.ligado:
                contagem.duplicadas += 1
            else:
                contagem.perdidas += 1
    return contagem


# ---------------------------------------------------------------------------
# A VARREDURA — um leitor POR GRAVACAO
# ---------------------------------------------------------------------------


def _novo_leitor(cal) -> LeitorDePagina:
    """A fiacao minima do leitor de pagina, com o catalogo em MEMORIA.

    O catalogo comeca vazio e morre com a gravacao, como o analog de
    `tests/test_mercado_replay.py` faz: o replay nao pode encanar nome no
    catalogo em disco do usuario, que e dado acumulado da Fase 2.
    """
    rastreio = RastreioDoPainel(
        ancoras_de_calibracao(cal.mercado_ancoras),
        float(cal.mercado_limiar_da_ancora),
    )
    return LeitorDePagina(
        rastreio, {}, ocr.ler_texto, ocr.ler_texto_ampliado, cal
    )


def varrer_uma_gravacao(pasta: Path, cal, registro, relogio):
    """Os frames de UMA gravacao, em ordem, por um leitor so dela.

    UM LEITOR POR GRAVACAO, e nunca um so para todas: duas gravacoes seguidas
    nao sao ticks vizinhos de uma sessao, e carregar a memoria de frame de uma
    para a outra afirmaria continuidade onde ha um corte. A razao e copiada do
    analog em `tests/test_mercado_replay.py`.
    """
    leitor = _novo_leitor(cal)
    aceitas: list = []
    arquivos = sorted(p for p in pasta.glob("frame_*.png") if p.is_file())
    lidos = 0
    for caminho in arquivos:
        frame = cv2.imread(str(caminho))
        if frame is None:
            continue
        lidos += 1
        pagina = leitor.observar(frame)
        if pagina is not None:
            aceitas.append(pagina)
    return lidos, len(aceitas), gravar_as_paginas(aceitas, registro, relogio)


# ---------------------------------------------------------------------------
# O programa
# ---------------------------------------------------------------------------


def _analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(
        description=(
            "Passa as gravacoes do censo pelo leitor de pagina da Fase 2 e "
            "grava o resultado no registro de observacoes da Fase 3."
        )
    )
    analisador.add_argument("--gravacoes", default=str(RAIZ / "recordings"))
    analisador.add_argument("--calibracao", default=str(RAIZ / "calibration.json"))
    # SEM `default`, e sem `required=True` disfarcado de padrao: o padrao seria
    # a pasta de producao, e contaminar o registro ao vivo com carimbo de agora
    # sobre preco de dias atras nao pode ser o comportamento de quem so digita
    # o comando.
    analisador.add_argument(
        "--saida",
        required=True,
        help="pasta de RASCUNHO onde o observacoes.csv sera escrito",
    )
    analisador.add_argument(
        "--gravacao",
        action="append",
        default=None,
        dest="subconjunto",
        help="roda so a(s) gravacao(oes) NOMEADA(s) do censo; repetivel",
    )
    return analisador


def _escolher_as_gravacoes(subconjunto):
    """O atalho do portao humano, sem virar a porta dos fundos do glob."""
    if not subconjunto:
        return list(GRAVACOES_DO_CENSO), []
    fora = [n for n in subconjunto if n not in GRAVACOES_DO_CENSO]
    return [n for n in subconjunto if n in GRAVACOES_DO_CENSO], fora


def main(argv=None) -> int:
    opcoes = _analisador().parse_args(argv)

    gravacoes = Path(opcoes.gravacoes).resolve()
    calibracao = Path(opcoes.calibracao).resolve()
    saida = Path(opcoes.saida)

    print("=" * 78)
    print("REPLAY DO CENSO -> observacoes.csv - 03-03")
    print("=" * 78)
    print("gravacoes : " + str(gravacoes))
    print("calibracao: " + str(calibracao))
    print("saida     : " + str(saida))

    # A GUARDA DA SAIDA VEM PRIMEIRO, ANTES DE QUALQUER CRIACAO DE PASTA. Uma
    # guarda que rodasse depois do `mkdir` ja teria deixado a marca do replay
    # dentro da pasta que ela existe para proteger.
    recusa = razao_para_recusar_a_saida(saida)
    if recusa is not None:
        print("")
        print(recusa)
        return SAIDA_RECUSADA

    if not gravacoes.is_dir():
        print("")
        print("ERRO: " + str(gravacoes) + " nao e um diretorio.")
        print(
            "  `recordings/` e gitignored e NAO se materializa em worktree. "
            "Rode no checkout PRINCIPAL."
        )
        return SAIDA_SEM_GRAVACOES

    nomes, fora = _escolher_as_gravacoes(opcoes.subconjunto)
    if fora:
        print("")
        print("ERRO: gravacao pedida que esta fora do censo:")
        for nome in fora:
            print("  - " + nome)
        print(
            "  O conjunto e FECHADO: 8 pastas nomeadas. Medir sobre outra "
            "produz um numero que nao se compara com nada deste projeto."
        )
        return SAIDA_CENSO_INCOMPLETO

    faltando = [n for n in nomes if not (gravacoes / n).is_dir()]
    if faltando:
        print("")
        print("ERRO: pasta esperada do censo AUSENTE:")
        for nome in faltando:
            print("  - " + nome)
        print(
            "  Ler um conjunto diferente do censo produz um arquivo que nao se "
            "compara com nenhum outro numero deste projeto. PARANDO."
        )
        return SAIDA_CENSO_INCOMPLETO

    if not ocr.disponivel():
        print("")
        print("ERRO: o motor de OCR nao respondeu neste interpretador.")
        print("  " + str(ocr.motivo_indisponivel()))
        print("  Rode pelo .venv: .venv/Scripts/python.exe tools/...")
        return SAIDA_SEM_OCR

    try:
        cal = Calibracao.carregar(calibracao)
    except CalibracaoInvalida as erro:
        print("")
        print("ERRO: " + str(erro))
        return SAIDA_SEM_CALIBRACAO

    if not cal.mercado_grade or not cal.mercado_coluna_do_nome:
        print("")
        print(
            "ERRO: o calibration.json nao traz mercado_grade com as colunas. "
            "Rode calibrar-mercado.bat sobre um frame da grade de negociacao."
        )
        return SAIDA_SEM_CALIBRACAO

    layout = (cal.mercado_grade or {}).get("layout")
    if layout != "negociacao":
        print("")
        print(
            f"ERRO: mercado_grade.layout e '{layout}', e esta leitura e da "
            "GRADE DE NEGOCIACAO. Recalibre."
        )
        return SAIDA_SEM_CALIBRACAO

    # O LOG DO PROJETO ANTES DA MONTAGEM, e nao depois. Sem isto o `log.error`
    # da montagem nao teria manipulador nenhum e o usuario nao veria nada — e o
    # criterio da fase e literalmente "o usuario VE o aviso alto". E o que faz a
    # metade CONSOLE do D-13 valer tambem fora do scanner.
    configurar_log(False)

    registro = montar_registro_de_mercado(saida)
    if registro is None:
        # NAO REPETIR O TEXTO DA MONTAGEM: ela ja imprimiu as duas mensagens no
        # console e no log, e duas versoes da mesma frase e como elas divergem.
        # A ferramenta so acrescenta o que e dela: nao vai sair arquivo.
        print("")
        print(
            "PARANDO: o registro de mercado nao montou, entao nenhum "
            "observacoes.csv vai ser produzido. As duas linhas de erro acima "
            "dizem o que quebrou e o que continua funcionando."
        )
        return SAIDA_SEM_REGISTRO

    relogio = Relogio()

    print("")
    print(f"Varrendo {len(nomes)} gravacao(oes)... (isto demora)")
    total = Contagem()
    frames = 0
    aceitas = 0
    for nome in nomes:
        lidos, paginas, contagem = varrer_uma_gravacao(
            gravacoes / nome, cal, registro, relogio
        )
        frames += lidos
        aceitas += paginas
        total.absorver(contagem)
        print(
            f"  {nome:<42} {lidos:>5} frames  {paginas:>4} paginas  "
            f"{contagem.observacoes:>4} novas"
        )

    print("")
    print("-" * 78)
    print(f"frames lidos            : {frames}")
    print(f"paginas aceitas         : {aceitas}")
    print(f"observacoes GRAVADAS    : {total.observacoes}")
    print(f"duplicadas descartadas  : {total.duplicadas}")
    print(f"series distintas        : {len(total.series)}")
    if total.perdidas:
        print(f"PERDIDAS (registro OFF) : {total.perdidas}")
    print(f"arquivo                 : {saida / ARQUIVO_DE_OBSERVACOES}")
    print("-" * 78)

    if not registro.ligado:
        print("")
        print(
            "O registro DESLIGOU no meio da varredura. O arquivo tem o que "
            "coube antes disso; as linhas de erro acima dizem o motivo."
        )
        return SAIDA_SEM_REGISTRO

    if total.observacoes == 0 and total.duplicadas == 0:
        print("")
        print(
            "NENHUMA observacao foi vista. Um arquivo vazio nao serve para o "
            "portao, e sair com 0 esconderia isso."
        )
        return SAIDA_SEM_OBSERVACAO

    if total.observacoes == 0:
        print("")
        print(
            "Zero observacoes NOVAS, e todas as vistas ja estavam no arquivo. "
            "Este e o desfecho ESPERADO da segunda rodada sobre a mesma saida "
            "(PERS-02) — o arquivo tem de continuar com o mesmo numero de "
            "linhas de antes."
        )

    return SAIDA_OK


if __name__ == "__main__":
    sys.exit(main())
