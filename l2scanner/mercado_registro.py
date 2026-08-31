"""As observacoes do World Exchange em `.mercado/observacoes.csv`.

Duas metades, separadas pelo comentario-regua la embaixo, no mesmo desenho de
`mercado_catalogo.py`: as funcoes PURAS em cima (sem disco, sem relogio) e a
classe que POSSUI o arquivo embaixo. Cada metade da para afirmar sozinha.

A FRONTEIRA COM A FASE 2, QUE NAO SE MEXE
==========================================
**A Fase 2 escreve o catalogo de NOMES; a Fase 3 escreve o CSV de OBSERVACOES.**
Dois arquivos, dois donos, nenhum compartilhado. Este modulo LE a chave que a
Fase 2 produziu e NUNCA escreve no catalogo dela.

ELE NAO ARRASTA A METADE DE VISAO. `LinhaLida` entra so sob `TYPE_CHECKING`: em
tempo de execucao as funcoes leem os campos POR NOME. Medido, e o numero e
exato: importar este modulo acrescenta EXATAMENTE UM modulo ao processo alem do
que `mercado_catalogo` ja carregava — ele mesmo — e `l2scanner.mercado_leitura`
continua FORA de `sys.modules`.

UM NUMERO QUE CAIU PRECISA DIZER QUE CAIU: o plano cobrava a forma mais forte
disto — `cv2` e `numpy` ausentes de `sys.modules` depois do import. Medido:
IMPOSSIVEL, e nao por culpa deste modulo. `mercado_catalogo` importa
`.config`, que importa `.agenda`/`.cliente`/`.visao`, e `visao` traz `cv2` e
`numpy` — entao `import l2scanner.mercado_catalogo` SOZINHO ja deixa os dois em
`sys.modules`. Como importar `PASTA_DO_MERCADO` e `SEPARADOR` de la, em vez de
redefinir, e contrato desta fase, as duas exigencias se contradiziam. Ficou a
que da para afirmar e que mede a mesma coisa: este modulo nao acrescenta peso
nenhum por conta propria. Aliviar a cadeia de `config` e outro assunto, de
outra fase.

AS QUATRO DIVERGENCIAS DELIBERADAS COM O ANALOG (`mercado_catalogo.py`)
=======================================================================
O resto e copiado dele quase palavra por palavra — mesma pasta, mesmo `;`,
mesmo `csv`, mesma leitura que NOMEIA a linha ruim. Estas quatro nao:

1. **`"a"` em vez de `"w"` + `os.replace`.** O catalogo reescreve o arquivo
   inteiro porque `avistamentos` sobe sem o arquivo crescer. Este arquivo cresce
   por construcao, e a reescrita atomica perderia a sessao inteira num corte de
   energia (D-15).
2. **`OSError` de LEITURA desliga a feature em vez de degradar para vazio.** O
   analog (`mercado_catalogo.py:465-472`) segue com catalogo VAZIO e avisa.
   Copiar isso aqui seria desastre: indice vazio faz a dedup falhar e o proximo
   tick reescreve tudo que ja esta no disco. Aqui o erro SOBE, e a montagem
   desliga a feature alto.
3. **O cabecalho e CONTRATO, nao conveniencia.** O analog pula o cabecalho e diz
   por escrito que "um arquivo sem ele ainda carrega". Aqui, cabecalho
   divergente — ou ausente num arquivo nao-vazio — desliga a feature. Migrar
   calado um arquivo que o usuario edita a mao e importa no Sheets e como se
   corrompe dado (D-11, D-12).
4. **Arquivo que nao termina em quebra de linha TAMBEM e contrato quebrado**
   (D-17). O analog grava por reescrita atomica e nao PODE truncar, entao nunca
   precisou desta rede. Este arquivo pode. A razao por extenso esta em
   `RegistroDeObservacoes.carregar`.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

# IMPORTADOS, E NAO REDEFINIDOS. Duas definicoes do mesmo ponto-e-virgula e como
# elas divergem: bastaria um dos dois arquivos mudar de dialeto para a pasta
# `.mercado/` passar a ter dois formatos e nenhum aviso. O comentario do
# `SEPARADOR` no catalogo (`mercado_catalogo.py:377-381`) ja fala com esta fase
# por nome — "a Fase 3 herda este dialeto" — e herdar e literalmente isto.
from .mercado_catalogo import PASTA_DO_MERCADO, SEPARADOR

if TYPE_CHECKING:  # pragma: no cover - so o verificador de tipos passa aqui
    from .mercado_leitura import LinhaLida

log = logging.getLogger(__name__)

__all__ = [
    "ARQUIVO_DE_OBSERVACOES",
    "COLUNAS",
    "ContratoDoArquivoQuebrado",
    "PASTA_DO_MERCADO",
    "RegistroDeObservacoes",
    "SEPARADOR",
    "campos_da_observacao",
    "chave_da_observacao",
    "chave_dos_campos",
    "residuo_dos_campos",
]

ARQUIVO_DE_OBSERVACOES = "observacoes.csv"

# A ORDEM espelha a do catalogo irmao na mesma pasta (chave, nome,
# primeira_vez, ...) para que dois arquivos vizinhos nao tenham convencoes
# diferentes, e os NOMES sao os mesmos campos que `LinhaLida` ja usa.
# `total_em_centesimos` carrega a UNIDADE no proprio nome do cabecalho: e o que
# faz `6200` ficar autoexplicativo para o olho humano e para a outra IA que vai
# receber o arquivo, sem nenhuma coluna derivada.
#
# AS TRES AUSENCIAS, E POR QUE SAO AUSENCIAS:
#
# 1. NAO HA COLUNA DE UNITARIO (D-02). O unitario que o jogo exibe e derivacao
#    ARREDONDADA a 2 casas, nao dado: `40,00` por 48 unidades aparece como
#    `0,83`, e `0,83 x 48 = 39,84` — um numero que nunca existiu. Total e
#    quantidade sao o que a tela AFIRMA; o unitario e o que ela CALCULOU.
# 2. NAO HA COLUNA DE GRAVACAO NEM DE FRAME (D-04). Sao artefato de bancada: no
#    farm ao vivo nao existe "frame 78", e uma coluna que so tem conteudo quando
#    se roda a suite e uma coluna que mente no uso real.
# 3. `indice` E `serie_nova` DA `LinhaLida` FICAM DE FORA, pelo mesmo criterio:
#    `indice` e a posicao na grade daquela pagina (proveniencia de leitura) e
#    `serie_nova` e um julgamento da Fase 2 sobre o catalogo, nao um fato sobre
#    o anuncio.
#
# O que ficou: a chave que AGRUPA e o nome que se LE (D-03, os dois porque o
# OCR faz o rotulo oscilar), o carimbo da PRIMEIRA vez (D-06), os dois inteiros
# que a tela afirma, e o residuo do cruzamento em coluna PROPRIA (D-01).
COLUNAS = (
    "chave_da_serie",
    "nome_exibido",
    "primeira_vez",
    "total_em_centesimos",
    "quantidade",
    "residuo_do_cruzamento",
)


class ContratoDoArquivoQuebrado(Exception):
    """O arquivo existe mas nao e mais o arquivo que este modulo escreveu.

    Ela existe para a montagem DESLIGAR A FEATURE ALTO em vez de escrever
    desalinhado sobre um arquivo que o usuario edita a mao e importa no Sheets.
    Nao e "linha ruim" — linha ruim cai sozinha com `warning` e o arquivo
    carrega. Isto e o arquivo INTEIRO recusado, e nada dele e lido.
    """


# ===========================================================================
# A METADE PURA: sem disco, sem relogio, sem `LinhaLida` em tempo de execucao
# ===========================================================================


def chave_da_observacao(linha: LinhaLida) -> tuple[str, int, int]:
    """A identidade de uma observacao: serie + total + quantidade (D-05).

    TUPLA, E NAO TEXTO JUNTADO: um `;` dentro da chave da serie tornaria duas
    observacoes distintas indistinguiveis se a chave fosse concatenacao. A
    tupla nao tem esse problema porque a fronteira entre os campos e estrutural.

    SEM O TEMPO, e a razao e que incluir o carimbo tornaria a dedup VACUA: cada
    tick tem carimbo diferente, entao toda observacao seria nova e o arquivo
    cresceria uma linha por segundo sobre o mesmo anuncio.

    SEM O NOME EXIBIDO, e a razao e o D-03: o nome e ROTULO e o OCR o faz
    oscilar (`Common Aztac` / `Cornmon Aztac`). Duas leituras do mesmo anuncio
    com rotulos diferentes tem de dar a MESMA chave, senao a dedup nao dedupa
    justamente no caso em que ela e necessaria.
    """
    return (linha.chave_da_serie, linha.total_em_centesimos, linha.quantidade)


def campos_da_observacao(linha: LinhaLida, agora: datetime) -> tuple[str, ...]:
    """Os seis campos da linha, na ordem de `COLUNAS`.

    O CARIMBO ENTRA POR PARAMETRO (D-16): este modulo nunca chama o relogio do
    sistema e nunca constroi um `Relogio`. Quem chama passa `Relogio.agora()`,
    que e um `datetime` INGENUO em hora local — e por isso o `.isoformat()` sai
    sem fuso, que e o formato que o resto do projeto ja usa.

    O RESIDUO `None` VIRA STRING VAZIA E O RESIDUO `0` VIRA `"0"` (D-01). Sao
    fatos DIFERENTES: `None` e "alguma das tres celulas nao leu, entao nao houve
    conferencia" e `0` e "conferi a aritmetica e ela bateu na casa do centesimo".
    Colapsar os dois num campo so apagaria a unica pista independente de leitura
    errada que esta fase tem.
    """
    residuo = linha.residuo_do_cruzamento
    return (
        linha.chave_da_serie,
        linha.nome_exibido,
        agora.isoformat(),
        str(linha.total_em_centesimos),
        str(linha.quantidade),
        "" if residuo is None else str(residuo),
    )


def chave_dos_campos(campos: Sequence[str]) -> tuple[str, int, int]:
    """O caminho de volta: seis campos do disco -> a chave. LEVANTA se nao servir.

    O motivo vem em TEXTO dentro do `ValueError` porque quem chama o imprime no
    aviso que NOMEIA a linha — a forense deste projeto acontece depois do farm,
    com o log na mao, e "linha 4 descartada" sem o motivo nao conserta nada.

    ESTA FUNCAO E AS DUAS REDES POR LINHA JUNTAS: a contagem de campos primeiro,
    a validacao por tipo depois. O que ela NAO consegue julgar e a CAUDA do
    arquivo — `'8'` e um inteiro perfeitamente valido, e foi assim que `'80'`
    truncado passou na medicao. Por isso o portao do terminador em
    `RegistroDeObservacoes.carregar` vem ANTES e nao e opcional (D-17).
    """
    if len(campos) != len(COLUNAS):
        raise ValueError(f"esperava {len(COLUNAS)} campos, veio {len(campos)}")

    bruta, _nome, carimbo, total, quantidade, residuo = campos

    chave = bruta.strip()
    if not chave:
        raise ValueError("chave da serie vazia")

    try:
        datetime.fromisoformat(carimbo.strip())
    except ValueError:
        raise ValueError("carimbo que nao e ISO-8601") from None

    try:
        centesimos = int(total.strip())
    except ValueError:
        raise ValueError("total que nao e inteiro") from None

    try:
        unidades = int(quantidade.strip())
    except ValueError:
        raise ValueError("quantidade que nao e inteiro") from None

    # O residuo e conferido aqui mas NAO entra na chave: ele e informacao sobre
    # a leitura, nao sobre o anuncio. Uma linha com residuo ilegivel e uma linha
    # que nao da para afirmar, entao ela cai inteira.
    if residuo.strip():
        try:
            int(residuo.strip())
        except ValueError:
            raise ValueError("residuo que nao e vazio nem inteiro") from None

    return (chave, centesimos, unidades)


def residuo_dos_campos(campos: Sequence[str]) -> int | None:
    """O residuo de volta: campo vazio -> `None`, `"0"` -> `0`. NUNCA um pelo outro.

    Ela existe separada de `chave_dos_campos` porque o residuo nao e identidade:
    ele nao entra na chave de dedup e nao pode entrar. Mas o D-01 exige que a
    distincao entre "nao mediu" e "conferi e bateu" sobreviva a IDA E A VOLTA, e
    uma volta que morasse no teste em vez de no modulo seria o teste provando a
    si mesmo.
    """
    bruto = campos[COLUNAS.index("residuo_do_cruzamento")].strip()
    if not bruto:
        return None
    return int(bruto)


# ===========================================================================
# A METADE DE DISCO: o arquivo que cresce por append
# ===========================================================================


class RegistroDeObservacoes:
    """O arquivo `.mercado/observacoes.csv`, e o unico escritor dele.

    UM ARQUIVO SO, QUE CRESCE, SEM ROTACAO (D-09). Ele mora ao lado do catalogo
    de nomes da Fase 2 (D-10) porque sao o mesmo assunto e o usuario abre os
    dois na mesma pasta. Nao tem poda pelo mesmo motivo do `.loot/`: estatistica
    de item e para sempre, e o volume medido no censo inteiro e de dezenas de
    series, nao de milhoes de linhas.

    O INDICE DE CHAVES VIVE EM MEMORIA e e reconstruido do PROPRIO CSV no
    arranque (D-07, PERS-02) — e o que faz a dedup de uma sessao nova enxergar o
    que a sessao anterior gravou.

    O CONSTRUTOR NAO SE DEFENDE, e isso e deliberado: `mkdir` pode levantar
    (`FileExistsError`, errno 17, medido) e `carregar` pode levantar
    `ContratoDoArquivoQuebrado` ou `OSError`. Quem envolve tudo num `try` e a
    montagem, pelo trilho de `montar_gravador` (`__main__.py:225+`), que existe
    precisamente porque um construtor que faz `mkdir` e `open` fora de qualquer
    `try` derrubava o scanner inteiro.
    """

    def __init__(self, pasta: Path) -> None:
        # A pasta chega no construtor, e nao derivada aqui dentro, pelo mesmo
        # motivo escrito em `mercado_catalogo.py:426-430`: e o que permite ao
        # teste apontar para `tmp_path` sem nunca tocar a `.mercado/` real, que
        # e dado acumulado e sem desfazer. Producao passa `PASTA_DO_MERCADO`.
        self._pasta = pasta
        self._pasta.mkdir(parents=True, exist_ok=True)
        self.ligado = True
        self.chaves: set[tuple[str, int, int]] = set()
        self.carregar()

    @property
    def arquivo(self) -> Path:
        return self._pasta / ARQUIVO_DE_OBSERVACOES

    # -- leitura ------------------------------------------------------------

    def carregar(self) -> set[tuple[str, int, int]]:
        """Le o arquivo e monta o indice. Ausente -> cria com cabecalho.

        `newline=""` TAMBEM NA LEITURA, e nao so na escrita: sem ele a traducao
        universal de quebras de linha alteraria um `nome_exibido` que contem
        `\\r`, que e um dos casos hostis medidos.

        `OSError` NAO E CAPTURADO AQUI, e essa e a divergencia 2 com o analog:
        `mercado_catalogo.py:465-472` degrada para catalogo VAZIO e segue.
        Copiar isso aqui seria desastre — indice vazio faz a dedup falhar e o
        proximo tick reescreve tudo que ja esta no disco. Aqui o erro sobe para
        a montagem desligar a feature.
        """
        self.chaves = set()
        try:
            with self.arquivo.open("r", encoding="utf-8", newline="") as fonte:
                bruto = fonte.read()
        except FileNotFoundError:
            # Primeira execucao numa maquina limpa e estado LEGITIMO, nao erro
            # (D-11). Nada a preservar, entao o cabecalho nasce aqui.
            self._criar_com_cabecalho()
            return self.chaves

        if not bruto:
            # O UNICO caso que NAO passa pelo portao de contrato, e a razao e
            # que nao ha dado a preservar: zero bytes nao tem byte do usuario
            # para ser destruido. O que aconteceu ali foi uma CRIACAO
            # interrompida, nao uma escrita perdida. Qualquer arquivo NAO vazio
            # que nao case com o contrato — inclusive um que contenha so o
            # cabecalho sem a quebra final — desliga a feature.
            log.warning(
                "O arquivo de observacoes %s tem ZERO BYTES: a criacao dele foi "
                "interrompida. Escrevi o cabecalho e seguindo com o indice "
                "VAZIO — nao havia dado nenhum ali para preservar.",
                self.arquivo,
            )
            self._criar_com_cabecalho()
            return self.chaves

        self._conferir_o_terminador(bruto)
        linhas = list(csv.reader(io.StringIO(bruto, newline=""), delimiter=SEPARADOR))
        self._conferir_o_cabecalho(linhas)
        self._montar_o_indice(linhas)
        return self.chaves

    # -- o portao de contrato ----------------------------------------------

    def _conferir_o_terminador(self, bruto: str) -> None:
        """O achado central da pesquisa: sem quebra final, o arquivo e recusado.

        A CONTAGEM DE CAMPOS NAO SERVE PARA ISTO, E ESTA MEDIDO. Sobre a linha
        de seis colunas `k;nome;2026-08-30T14:03:21;6200;48;80\\r\\n`, cortada
        byte a byte a partir do fim, os CINCO cortes deixam o arquivo sem quebra
        de linha final — mas DOIS deles produzem seis campos todos parseaveis,
        com `80` virando `8` e `48` virando `4`. Essa linha passaria pela
        contagem, viraria observacao, e pior: viraria CHAVE DE DEDUP que
        bloquearia a gravacao da observacao correta mais tarde. `'8'` e um
        inteiro perfeitamente valido, entao a validacao por tipo tambem nao a
        pega. So o terminador pega — 5 de 5.

        A BICONDICIONAL QUE SUSTENTA O CRITERIO TAMBEM FOI MEDIDA:
        `csv.writer.writerow` emite UMA unica chamada de escrita contendo a
        linha E o terminador, logo **um registro esta completo se e somente se o
        arquivo termina em quebra de linha**.

        UM ARQUIVO QUE NAO TERMINA EM QUEBRA DE LINHA NAO E "UM ARQUIVO BOM COM
        UMA LINHA RUIM NO FIM": e um arquivo cujo estado o programa nao consegue
        afirmar. Por isso o tratamento e o MESMO do cabecalho divergente — a
        feature desliga alto e um humano olha — e nao um tratamento proprio. E a
        doutrina que a fase ja tem (D-12), aplicada na mesma funcao de arranque
        e sobre o mesmo arquivo, e nao uma excecao inventada para este caso.

        AS DUAS OUTRAS SAIDAS FORAM CONSIDERADAS E RECUSADAS, e um numero que
        caiu precisa dizer que caiu:

        (a) REMOVER A CAUDA DO DISCO (truncar ate a ultima quebra de linha).
            Seria o programa apagando bytes do usuario num caminho de LEITURA. E
            uma das duas hipoteses do proprio aviso e "linha boa, salva a mao
            sem quebra final" — entao a saida apagaria dado BOM em metade dos
            casos que ela existe para tratar. Contradiz o D-12, que recusa mexer
            calado num arquivo que o usuario edita a mao e importa no Sheets.

        (b) COMPLETAR A CAUDA COM UMA QUEBRA DE LINHA antes do proximo append.
            E a PIOR das tres, porque preserva a linha possivelmente truncada E
            A PROMOVE: na leitura seguinte ela termina em newline, passa nas
            duas redes por linha, e vira observacao PERMANENTE. O `'80'` cortado
            para `'8'` tem seis campos validos e viraria preco errado para
            sempre — o defeito exato que esta fase existe para nao ter.

        CUSTO ACEITO, E ELE E REAL: uma queda de energia de verdade desliga o
        registro ate intervencao manual. Aceitavel porque a mensagem diz ao
        usuario exatamente o que fazer para religar, e porque a alternativa e
        preco errado gravado como bom.
        """
        if bruto.endswith("\n"):
            return

        cauda = bruto[bruto.rfind("\n") + 1 :]
        mensagem = (
            "MERCADO DESLIGADO — o arquivo de observacoes %s NAO TERMINA EM "
            "QUEBRA DE LINHA, e por isso NADA foi lido dele. Duas hipoteses, e "
            "o criterio nao consegue distinguir uma da outra: ou a ultima "
            "gravacao foi INTERROMPIDA (queda de energia, ou disco cheio no "
            "meio da escrita), ou o arquivo foi EDITADO A MAO e salvo sem a "
            "quebra de linha final. A cauda crua e %r, e ela esta INTACTA no "
            "disco: nenhum byte foi removido, reparado ou reescrito. O QUE "
            "FAZER: abra o arquivo, olhe a ultima linha, complete-a ou "
            "apague-a, e salve COM quebra de linha no fim — isso religa a "
            "feature no proximo arranque. Enquanto isso, os alertas de party "
            "(morte, saida e ressurreicao) seguem sendo detectados e entregues."
        )
        log.error(mensagem, self.arquivo, cauda)
        raise ContratoDoArquivoQuebrado(mensagem % (self.arquivo, cauda))

    def _conferir_o_cabecalho(self, linhas: list[list[str]]) -> None:
        """A mesma forma do analog, com o `else` INVERTIDO (D-11, D-12).

        Em `mercado_catalogo.py:478-481` o cabecalho e CONVENIENCIA para o olho
        humano, e esta escrito la que "um arquivo sem ele ainda carrega". Aqui
        ele e a IDENTIDADE do arquivo. A inversao tem motivo: migrar sozinho um
        arquivo que o usuario edita a mao e importa no Sheets e exatamente como
        se corrompe dado calado — o append escreveria valores nas colunas
        erradas e ninguem veria, porque o arquivo continuaria abrindo.

        Tres estados, e so tres: arquivo AUSENTE cria com cabecalho (tratado em
        `carregar`); primeiro registro IDENTICO a `COLUNAS` depois de `strip`
        segue; DIVERGENTE, ou ausente num arquivo nao-vazio, levanta.
        """
        encontrado = tuple(campo.strip() for campo in linhas[0]) if linhas else ()
        if encontrado == COLUNAS:
            return

        mensagem = (
            "MERCADO DESLIGADO — o cabecalho de %s nao e o que este programa "
            "escreve, e por isso NADA foi lido dele. Esperava %r e encontrei "
            "%r. NENHUM byte foi alterado: migrar sozinho um arquivo que voce "
            "edita a mao e importa no Sheets e como se corrompe dado calado, "
            "porque o append passaria a escrever valores nas colunas erradas e "
            "o arquivo continuaria abrindo. O QUE FAZER: restaure a primeira "
            "linha para o cabecalho esperado, ou renomeie o arquivo para o "
            "programa criar um novo — qualquer um dos dois religa a feature no "
            "proximo arranque. Enquanto isso, os alertas de party (morte, "
            "saida e ressurreicao) seguem sendo detectados e entregues."
        )
        log.error(mensagem, self.arquivo, COLUNAS, encontrado)
        raise ContratoDoArquivoQuebrado(
            mensagem % (self.arquivo, COLUNAS, encontrado)
        )

    # -- as duas redes por linha -------------------------------------------

    def _montar_o_indice(self, linhas: list[list[str]]) -> None:
        """Passado o portao, uma linha ruim cai SOZINHA e nunca condena o
        arquivo — o D-14 literal.

        REDE 1, A CONTAGEM DE CAMPOS: e a rede que a decisao travada nomeia, e
        ela continua valendo inteira. O que mudou foi o ALCANCE — ela nunca foi
        capaz de julgar a cauda do arquivo, e agora nao precisa. O que ela pega
        e a linha que o usuario quebrou editando no MEIO do arquivo.

        REDE 2, A VALIDACAO POR TIPO de cada campo. As duas moram dentro de
        `chave_dos_campos`, que devolve o motivo em texto para o aviso.
        """
        # numero da linha e nome exibido da PRIMEIRA vez que cada chave apareceu
        origem: dict[tuple[str, int, int], tuple[int, str]] = {}

        for numero, campos in enumerate(linhas, start=1):
            if numero == 1:
                continue  # o cabecalho, ja conferido
            if not campos or all(not campo.strip() for campo in campos):
                continue

            def recusar(motivo: str, numero: int = numero, campos=campos) -> None:
                # O molde literal de `mercado_catalogo.py:498-506`: numero da
                # linha, motivo em texto, conteudo cru em `%r`. A forense deste
                # projeto acontece DEPOIS do farm, com o log na mao — sem o
                # numero o usuario nao acha a linha para consertar no Sheets.
                log.warning(
                    "Observacoes, linha %d DESCARTADA (%s): %r. As demais "
                    "linhas do arquivo carregaram normalmente — uma linha ruim "
                    "nunca condena o arquivo inteiro.",
                    numero,
                    motivo,
                    SEPARADOR.join(campos),
                )

            try:
                chave = chave_dos_campos(campos)
            except ValueError as erro:
                recusar(str(erro))
                continue

            nome = campos[COLUNAS.index("nome_exibido")]
            if chave in self.chaves:
                primeira_linha, primeiro_nome = origem[chave]
                if primeiro_nome != nome:
                    # D-08: a chave E o conteudo, entao chave igual so pode
                    # significar que o ROTULO oscilou no OCR. `error` e nao
                    # `warning` porque isto e impossivel por construcao — mas a
                    # feature NAO desliga: o arquivo esta legivel, o que esta
                    # errado e uma etiqueta, e quem decide entre duas etiquetas
                    # e o usuario no Sheets.
                    log.error(
                        "Observacoes: a linha %d e a linha %d tem a MESMA chave "
                        "%r com nomes DIFERENTES (%r e %r). Isso e impossivel "
                        "por construcao — a chave e derivada do conteudo — "
                        "entao o que oscilou foi o rotulo do OCR. A primeira "
                        "(linha %d, %r) foi mantida, que e tambem a mais "
                        "antiga; NENHUMA das duas foi apagada do arquivo, e "
                        "quem escolhe entre as duas etiquetas e voce, no "
                        "Sheets. O registro continua LIGADO.",
                        primeira_linha,
                        numero,
                        chave,
                        primeiro_nome,
                        nome,
                        primeira_linha,
                        primeiro_nome,
                    )
                continue

            self.chaves.add(chave)
            origem[chave] = (numero, nome)

    def _criar_com_cabecalho(self) -> None:
        """Escreve o cabecalho num arquivo AUSENTE. Unica escrita do arranque.

        O modo e `"w"` e ele so alcanca arquivo que nao existe — nao ha byte do
        usuario para destruir. Nenhum outro caminho de leitura escreve.
        """
        with self.arquivo.open("w", encoding="utf-8", newline="") as destino:
            csv.writer(destino, delimiter=SEPARADOR).writerow(COLUNAS)

    # -- escrita ------------------------------------------------------------

    def registrar(self, linha: LinhaLida, agora: datetime) -> bool:
        """Uma observacao. Devolve se ela virou linha nova no arquivo.

        NUNCA LEVANTA PARA FORA (PERS-03). A doutrina da casa, ja escrita em
        `gravador.py:138-145`, e degradar a FEATURE e nunca o PRODUTO: uma
        excecao aqui derrubaria o scanner por causa de disco cheio, levando os
        alertas de morte da party junto.

        A DEDUP E CONFERIDA EM MEMORIA ANTES DE ESCREVER (PERS-02): o disco so e
        tocado quando a observacao e realmente nova.

        TRES DECISOES DE ESCRITA, cada uma com o numero medido:

        - **`flush()` sem `os.fsync()`.** Medido: `flush` sozinho custa 0,0037 ms
          e `flush+fsync` custa 1,5990 ms — 432x mais caro. E o que o `fsync`
          compra nao e o modo de falha desta fase: `writerow`+`flush` e UMA
          `write()` so, entao Ctrl+C, excecao ou `taskkill` nao produzem linha
          truncada. Ele so ajudaria numa queda de energia, e o dado desta fase e
          re-derivavel — o mercado sera lido de novo.
        - **Abrir e FECHAR por linha** (0,1295 ms, 12x mais barato que o fsync e
          ruido num tick de 1 Hz). Medido: com a alca JA ABERTA, marcar o arquivo
          como somente-leitura NAO impede a escrita — o `PermissionError` so
          nasce no `open`. Com a alca aberta a sessao inteira, uma falha que
          aparece DEPOIS do arranque seria invisivel. Ainda e "append com flush
          linha a linha", que e a decisao travada (D-15), e de quebra nunca
          segura uma alca sobre o arquivo que o usuario quer abrir no Sheets.
        - **`newline=""`** porque sem ele o modulo `csv` escreve `\\r\\r\\n` no
          Windows e nao consegue remontar um campo que contem quebra de linha.
        """
        if not self.ligado:
            return False

        chave = chave_da_observacao(linha)
        if chave in self.chaves:
            return False

        campos = campos_da_observacao(linha, agora)

        # O `try` envolve a ABERTURA, a ESCRITA e o `flush` — os tres, porque a
        # medicao mostrou que os erros nascem em pontos diferentes: o
        # `PermissionError` de arquivo somente-leitura nasce no `open`, e o
        # `ENOSPC` de disco cheio nasce no `flush`. Envolver so um dos dois
        # deixaria metade dos modos de falha subir.
        #
        # `except OSError` E SO, e a justificativa e medida: os quatro modos
        # desta maquina sao `PermissionError` (errno 13) para arquivo
        # somente-leitura e para nome ocupado por diretorio,
        # `FileNotFoundError` (errno 2) para pasta inexistente, e
        # `FileExistsError` (errno 17, winerror 183) para `mkdir` sobre nome de
        # arquivo — todas subclasses de `OSError`, e um `except` so cobre as
        # quatro. NAO `except Exception`: o analog do `Gravador` o usa e ele e
        # largo demais para o que a medicao mostrou — esconderia um
        # `AttributeError` de refactor como se fosse disco cheio.
        try:
            with self.arquivo.open("a", encoding="utf-8", newline="") as destino:
                csv.writer(destino, delimiter=SEPARADOR).writerow(campos)
                destino.flush()
        except OSError as erro:
            # DEFINITIVO PARA A SESSAO, e nao ha nova tentativa: um retry por
            # tick a 1 Hz encheria o log com o mesmo erro e daria ao usuario a
            # impressao de que ainda esta gravando. Quem religa e o proximo
            # arranque, depois de o usuario consertar o arquivo.
            self.ligado = False
            log.error(
                "MERCADO DESLIGADO — nao consegui escrever a observacao em "
                "%s: %s. O registro de mercado PAROU nesta sessao e nao vai "
                "tentar de novo; quem religa e o proximo arranque, depois de "
                "voce consertar o arquivo ou a pasta.",
                self.arquivo,
                erro,
            )
            log.error(
                "Todo o resto do scanner continua igual: morte, saida e "
                "ressurreicao seguem sendo detectadas e entregues."
            )
            return False

        # A CHAVE SO ENTRA DEPOIS DE A LINHA CHEGAR AO ARQUIVO. O indice e a
        # promessa de "isto ja esta no disco": uma chave la sem linha no arquivo
        # bloquearia PARA SEMPRE a gravacao da observacao correta — seria a
        # dedup trabalhando contra o proprio dado.
        self.chaves.add(chave)
        return True
