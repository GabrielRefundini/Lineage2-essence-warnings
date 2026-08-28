"""Portao executavel das gravacoes do spike do mercado (FUND-02).

O checkpoint desta fase decide se as 8 sessoes do usuario foram bem gastas. Ele
NAO pode ser so prosa: o sinal de alarme mais caro — um PNG de ~170 KB onde
deveria haver ~3,5 MB, ou seja, o recorte da party window gravado no lugar da
janela inteira — e verificavel por programa. Descobrir isso pelo olho custaria
abrir um PNG de cada pasta; descobrir tarde custaria as oito sessoes.

Cinco conferencias, por pasta, cada uma nomeando o problema:

  1. Os 8 sufixos do ROTEIRO-SPIKE.md tem pelo menos uma pasta em recordings/.
  2. `observacoes.jsonl` existe e tem mais de zero linhas.
  3. Todo `arquivo` citado no JSONL existe no disco (a mesma assertiva
     anti-orfao do FUND-01, agora aplicada as gravacoes de verdade).
  4. ZERO falhas de escrita, provado SEM depender de contador em memoria:
     linhas do JSONL == quantidade de `frame_*.png` no disco. Depois do FUND-01
     o JSONL so recebe frame confirmado, entao qualquer divergencia denuncia
     perda de escrita que ninguem viu passar.
  5. Dimensao correta: o primeiro e o ultimo `frame_*.png` sao lidos com
     `cv2.imread` e a forma precisa ser a da JANELA — nunca a do recorte da
     party window, que vem do `calibration.json`.

`is_file()` em todo glob de PNG, e nao o glob cru: um DIRETORIO ocupando o nome
`frame_000007.png` e justamente o modo de falha deterministico que os testes do
gravador usam para provocar erro de escrita. Um glob cru contaria o proprio
artefato da mentira como frame gravado — a conferencia que existe para provar
que o contador nao mente passaria a mentir junto.

Uso:
    python tools/conferir_gravacoes_do_spike.py
    python tools/conferir_gravacoes_do_spike.py --pasta-base recordings
    python tools/conferir_gravacoes_do_spike.py --calibracao calibration.json

Sai com codigo 0 quando tudo passa, e diferente de zero nomeando cada problema.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Os rotulos fixos do ROTEIRO-SPIKE.md, na ordem em que ele os grava. O `pre-voo`
# NAO entra: ele e a sessao de 5 segundos que prova o modo de gravacao e pode ser
# apagada depois. Estes oito sao a evidencia da fase.
SUFIXOS_DO_ROTEIRO = (
    "mercado-fechado",
    "mercado-aberto",
    "mercado-scroll",
    "mercado-pagina-cheia",
    "mercado-tooltip",
    "mercado-alvo-sobreposto",
    "mercado-farm-com-party",
    "mercado-scroll-transicao",
)


class Problema(Exception):
    """Falha de conferencia ja com a mensagem que o usuario precisa ler."""


def pngs_de_frame(pasta: Path) -> list[Path]:
    """Os `frame_*.png` REAIS da pasta, em ordem.

    O `is_file()` nao e decoracao — ver a docstring do modulo.
    """
    return sorted(p for p in pasta.glob("frame_*.png") if p.is_file())


def pastas_do_sufixo(pasta_base: Path, sufixo: str) -> list[Path]:
    """As gravacoes daquele cenario, da mais antiga para a mais recente.

    O nome da pasta e `{AAAAMMDD-HHMMSS}-{rotulo}`, entao o glob por sufixo
    EXATO tambem separa `mercado-scroll` de `mercado-scroll-transicao`: o
    fnmatch de `*-mercado-scroll` nao casa um nome que termina em
    `-mercado-scroll-transicao`.
    """
    if not pasta_base.is_dir():
        return []
    return sorted(p for p in pasta_base.glob(f"*-{sufixo}") if p.is_dir())


def dimensao_do_recorte_da_party(caminho_da_calibracao: Path) -> tuple[int, int] | None:
    """(altura, largura) do recorte da party window, ou None sem calibracao.

    E esta a forma que precisamos RECUSAR: e o que o `--record` sozinho grava, e
    e o engano que gastaria as oito sessoes.
    """
    if not caminho_da_calibracao.is_file():
        return None
    try:
        dados = json.loads(caminho_da_calibracao.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    regiao = dados.get("party_window_na_janela") or dados.get("party_window")
    if not isinstance(regiao, dict):
        return None
    try:
        return int(regiao["altura"]), int(regiao["largura"])
    except (KeyError, TypeError, ValueError):
        return None


def conferir_o_indice(pasta: Path) -> int:
    """Conferencias 2, 3 e 4. Devolve a quantidade de linhas do JSONL."""
    indice = pasta / "observacoes.jsonl"
    if not indice.is_file():
        raise Problema(f"{pasta.name}: nao tem observacoes.jsonl")

    linhas = [
        bruta
        for bruta in indice.read_text(encoding="utf-8").splitlines()
        if bruta.strip()
    ]
    if not linhas:
        raise Problema(
            f"{pasta.name}: observacoes.jsonl esta VAZIO — nenhum frame foi "
            f"confirmado nesta sessao. Regrave este cenario."
        )

    orfaos = []
    for numero, linha in enumerate(linhas, start=1):
        try:
            registro = json.loads(linha)
        except json.JSONDecodeError as erro:
            raise Problema(
                f"{pasta.name}: observacoes.jsonl linha {numero} esta "
                f"corrompida ({erro})"
            ) from erro
        nome = registro.get("arquivo")
        if not nome or not (pasta / nome).is_file():
            orfaos.append(nome or f"<linha {numero} sem campo 'arquivo'>")

    if orfaos:
        raise Problema(
            f"{pasta.name}: o indice cita {len(orfaos)} arquivo(s) que NAO "
            f"existem no disco (ex.: {orfaos[0]}). O indice esta mentindo "
            f"sobre a propria gravacao — regrave este cenario."
        )

    no_disco = len(pngs_de_frame(pasta))
    if no_disco != len(linhas):
        raise Problema(
            f"{pasta.name}: {len(linhas)} linhas no observacoes.jsonl mas "
            f"{no_disco} frame_*.png no disco. Depois do FUND-01 o indice so "
            f"recebe escrita CONFIRMADA, entao esta diferenca denuncia frames "
            f"perdidos. Regrave este cenario com espaco em disco sobrando."
        )
    return len(linhas)


def conferir_a_dimensao(
    pasta: Path, recorte_da_party: tuple[int, int] | None
) -> tuple[int, int]:
    """Conferencia 5. Devolve (altura, largura) dos frames desta pasta."""
    import cv2

    frames = pngs_de_frame(pasta)
    if not frames:
        raise Problema(f"{pasta.name}: nenhum frame_*.png no disco")

    # Primeiro E ultimo: uma sessao que comecou certa e degradou no meio (janela
    # minimizada, jogo reiniciado) precisa cair aqui, e nao passar pelo primeiro.
    a_conferir = {frames[0], frames[-1]}
    formas = {}
    for caminho in sorted(a_conferir):
        pixels = cv2.imread(str(caminho))
        if pixels is None:
            raise Problema(
                f"{pasta.name}: o cv2 nao conseguiu abrir {caminho.name} — o "
                f"PNG esta truncado ou corrompido"
            )
        formas[caminho.name] = (int(pixels.shape[0]), int(pixels.shape[1]))

    distintas = set(formas.values())
    if len(distintas) > 1:
        raise Problema(
            f"{pasta.name}: o primeiro e o ultimo frame tem dimensoes "
            f"DIFERENTES ({formas}). A janela mudou de tamanho no meio da "
            f"sessao e os recortes derivados nao valeriam. Regrave."
        )

    forma = distintas.pop()

    if recorte_da_party is None:
        raise Problema(
            f"{pasta.name}: sem calibration.json nao da para provar que "
            f"{forma[1]}x{forma[0]} e a JANELA e nao o recorte da party "
            f"window. Rode a calibracao (python -m l2scanner.calibrar) ou "
            f"aponte um arquivo com --calibracao."
        )

    if forma == recorte_da_party:
        raise Problema(
            f"{pasta.name}: os PNGs tem {forma[1]}x{forma[0]} — que e "
            f"EXATAMENTE o recorte da party window, nao a janela do jogo. "
            f"Esta sessao foi gravada com --record em vez de --record-janela e "
            f"nao contem um unico pixel do painel do mercado. Regrave com:\n"
            f"    python -m l2scanner --janela --record-janela "
            f"--rotulo {pasta.name.split('-', 2)[-1]} --dry-run"
        )

    altura_party, largura_party = recorte_da_party
    if forma[0] <= altura_party or forma[1] <= largura_party:
        raise Problema(
            f"{pasta.name}: os PNGs tem {forma[1]}x{forma[0]}, que nao e maior "
            f"que o recorte da party window ({largura_party}x{altura_party}). "
            f"A janela do jogo CONTEM a party window, entao um frame de janela "
            f"e sempre maior nas duas dimensoes. Regrave com --record-janela."
        )

    return forma


def tamanho_medio_kb(pasta: Path) -> int:
    frames = pngs_de_frame(pasta)
    if not frames:
        return 0
    return round(sum(p.stat().st_size for p in frames) / len(frames) / 1024)


def conferir(pasta_base: Path, caminho_da_calibracao: Path) -> int:
    recorte_da_party = dimensao_do_recorte_da_party(caminho_da_calibracao)

    problemas: list[str] = []
    tabela: list[tuple[str, str, int, str, str]] = []

    for sufixo in SUFIXOS_DO_ROTEIRO:
        candidatas = pastas_do_sufixo(pasta_base, sufixo)
        if not candidatas:
            problemas.append(
                f"{sufixo}: NENHUMA pasta {pasta_base}/*-{sufixo} — este "
                f"cenario do ROTEIRO-SPIKE.md ainda nao foi gravado."
            )
            continue

        # A mais recente e a que vale: regravar um cenario que saiu errado e o
        # conselho do proprio roteiro, e a pasta antiga pode ficar.
        pasta = candidatas[-1]
        try:
            frames = conferir_o_indice(pasta)
            forma = conferir_a_dimensao(pasta, recorte_da_party)
        except Problema as erro:
            problemas.append(str(erro))
            continue

        tabela.append(
            (
                sufixo,
                pasta.name,
                frames,
                f"{forma[1]}x{forma[0]}",
                f"{tamanho_medio_kb(pasta)} KB",
            )
        )

    if problemas:
        print(f"REPROVADO — {len(problemas)} problema(s):\n", file=sys.stderr)
        for problema in problemas:
            print(f"  * {problema}\n", file=sys.stderr)
        if tabela:
            print(f"({len(tabela)} de 8 cenarios passaram.)", file=sys.stderr)
        return 1

    largura_do_rotulo = max(len(linha[0]) for linha in tabela)
    largura_da_pasta = max(len(linha[1]) for linha in tabela)
    print("APROVADO — as 8 gravacoes do spike servem.\n")
    print(
        f"{'cenario'.ljust(largura_do_rotulo)}  "
        f"{'pasta'.ljust(largura_da_pasta)}  frames  dimensao   medio"
    )
    for rotulo, pasta, frames, forma, medio in tabela:
        print(
            f"{rotulo.ljust(largura_do_rotulo)}  {pasta.ljust(largura_da_pasta)}  "
            f"{str(frames).rjust(6)}  {forma.ljust(9)}  {medio.rjust(8)}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="conferir_gravacoes_do_spike",
        description=(
            "Confere se as 8 gravacoes do ROTEIRO-SPIKE.md servem: sufixos "
            "presentes, indice sem orfaos, zero falhas de escrita e PNGs na "
            "dimensao da JANELA e nao do recorte da party window."
        ),
    )
    parser.add_argument(
        "--pasta-base",
        type=Path,
        default=RAIZ / "recordings",
        help="onde as sessoes foram gravadas (padrao: recordings/)",
    )
    parser.add_argument(
        "--calibracao",
        type=Path,
        default=RAIZ / "calibration.json",
        help=(
            "de onde sai a dimensao do recorte da party window, que e a forma "
            "a RECUSAR (padrao: calibration.json na raiz)"
        ),
    )
    args = parser.parse_args(argv)
    return conferir(args.pasta_base, args.calibracao)


if __name__ == "__main__":
    raise SystemExit(main())
