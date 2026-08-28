"""Portao executavel do SPIKE-RESPOSTAS.md (FUND-02, D-04).

POR QUE ESTE PORTAO EXISTE
--------------------------
Citar um caminho com FORMATO valido nao e citar evidencia.

Um portao que so casasse o formato aceitaria, satisfeito, a linha

    Evidencia: `recordings/20260827-1200-mercado-aberto/frame_000012.png`

sustentando uma resposta que ninguem nunca olhou. O caminho tem a forma certa,
o rotulo certo, o numero de frame certo -- e a pasta nao existe. E a mesma
classe de mentira que o `cv2.imwrite` sem retorno checado produzia no gravador:
um contador subindo, um relatorio bonito, e nenhum pixel no disco. O FUND-01
existe para consertar aquilo. Este arquivo existe para que a mesma mentira nao
volte pela porta da analise.

Nesta fase, cujo proposito declarado e que "evidencia nao-confirmada e o
pesadelo documentado deste projeto", o portao do spike nao pode aceitar
evidencia nao confirmada. Entao ele RESOLVE cada caminho no sistema de
arquivos com `Path.is_file()`, um por um, e nomeia os que nao existem. Um
caminho com `..` no meio e RECUSADO mesmo existindo: `recordings/../x.png`
sai da arvore de gravacoes e nao e evidencia de spike nenhum.

E o que este documento sustenta e caro: a grade e os glifos do `calibration.json`
saem das respostas 1, 2 e 3; a forma da ancora sai da resposta 8; o recorte dos
templates de encanto sai da resposta 7. Uma resposta errada aqui so aparece tres
fases adiante, quando ja houver codigo de leitura de preco construido em cima
dela.

AS CONFERENCIAS
---------------
1. As secoes de resposta sao os cabecalhos numerados (`^#{2,3}\\s+\\d+\\.`).
   Precisam ser exatamente 9, numeradas de 1 a 9, sem repetir e sem pular.
   Qualquer outro cabecalho (legenda, introducao, "Impacto no planejamento")
   fica FORA da contagem -- de proposito: a legenda contem as tres palavras de
   selo e nao pode satisfazer o portao sozinha.
2. Cada secao numerada carrega EXATAMENTE UM selo entre `VERIFICADO`, `PARCIAL`
   e `NAO RESPONDIDO`. Zero selos e uma resposta sem compromisso; dois selos e
   uma resposta que quer as duas coisas.
3. Toda secao selada `VERIFICADO` ou `PARCIAL` cita pelo menos um frame, e
   todos os frames que ela cita existem no disco. Um selo positivo sem frame e
   exatamente a afirmacao confiante sem lastro que o `<threat_model>` do plano
   registra como T-03-01.
4. Globalmente: todo caminho `recordings/...png` citado em qualquer lugar do
   documento existe no disco, inclusive dentro de uma secao `NAO RESPONDIDO` e
   inclusive fora das secoes numeradas.

Uma secao `NAO RESPONDIDO` nao precisa citar frame -- e o selo honesto para uma
pergunta que a gravacao nao responde, e exigir evidencia dele seria empurrar
quem escreve de volta para o palpite.

SOBRE A TASK 2 (o portao humano)
--------------------------------
O usuario vai EDITAR este documento: D-04 diz que ele valida ou corrige. Duas
consequencias no desenho deste script:

  * `NAO RESPONDIDO` tambem e aceito escrito com til (`NAO RESPONDIDO` com A
    acentuado). Quem esta rebaixando uma resposta minha por saber mais do jogo
    do que eu nao pode ver o portao reprovar por causa de um acento.
  * Rebaixar uma secao para `NAO RESPONDIDO` sem apagar as citacoes continua
    passando. Manter o frame ao lado da resposta rebaixada e uma informacao
    util, nao um erro.

SOBRE `--raiz`
--------------
`recordings/` esta no `.gitignore` e portanto NAO se materializa dentro de um
git worktree -- ele existe so no checkout principal. Sem `--raiz` este portao
seria improvavel de rodar exatamente onde a analise e feita. Mesmo precedente e
mesma razao de `--pasta-base` em `conferir_gravacoes_do_spike.py`.

Uso:
    python tools/conferir_spike_respostas.py
    python tools/conferir_spike_respostas.py --documento outro.md
    python tools/conferir_spike_respostas.py --raiz C:/caminho/do/checkout

Sai com codigo 0 quando tudo passa, e diferente de zero nomeando cada problema.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

DOCUMENTO_PADRAO = (
    RAIZ
    / ".planning"
    / "workstreams"
    / "mercado"
    / "phases"
    / "01-funda-o-firewall-gravador-e-spike-de-campo"
    / "SPIKE-RESPOSTAS.md"
)

# Uma secao de RESPOSTA e um cabecalho numerado. `## 1.` ou `### 1.`, nada mais.
# A legenda ("VERIFICADO = visto no frame...") vive sob um cabecalho NAO
# numerado justamente para nao ser contada: ela tem as tres palavras de selo e
# satisfaria a conferencia 2 sem responder pergunta nenhuma.
CABECALHO_NUMERADO = re.compile(r"^(#{2,3})\s+(\d+)\.")

# Uma secao numerada termina no proximo cabecalho de nivel IGUAL OU MAIOR (ou
# seja, com o mesmo numero de `#` ou menos). Sem isto, a secao 9 engoliria a
# secao "Impacto no planejamento" e os selos dela contariam junto.
#
# O nivel importa, e o teste por mutacao mostrou por que. A primeira versao
# encerrava a secao em QUALQUER cabecalho, e a resposta 8 -- que tem duas
# sub-secoes `###` -- ficava partida: tudo depois do primeiro `###` deixava de
# pertencer a secao 8. Os frames citados ali sumiam da conferencia por secao e
# so eram pegos pela conferencia global. Pior: uma resposta cujo selo viesse
# depois de um `###` seria acusada de nao ter selo, e uma cujas unicas citacoes
# viessem depois de um `###` seria acusada de nao ter evidencia. Duas reprovacoes
# FALSAS, num portao cujo valor inteiro e a confianca no veredito.
CABECALHO = re.compile(r"^(#{1,6})\s")

# `[^\s)\`]` para nao arrastar a crase de fechamento, o parentese de um link
# markdown nem a proxima palavra da frase.
CAMINHO_DE_FRAME = re.compile(r"recordings/[^\s)`]+\.png")

SELOS = ("VERIFICADO", "PARCIAL", "NAO RESPONDIDO")
SELO_POSITIVO = ("VERIFICADO", "PARCIAL")

# A ordem em que os selos sao PROCURADOS no texto -- diferente de `SELOS`, que e
# so a lista para as mensagens de erro. `NAO RESPONDIDO` sai primeiro para que a
# remocao dele nao deixe nenhum pedaco para tras.
ORDEM_DE_BUSCA = ("NAO RESPONDIDO", "VERIFICADO", "PARCIAL")

# A NEGACAO EXPLICITA, e por que ela precisa de uma regra propria.
#
# MEDIDO: `Secao.selos` procurava por substring, na ordem de `SELOS`, que comeca
# por `VERIFICADO`. Contra o texto real
#
#     "NAO VERIFICADO em campo -- nao deu tempo."
#
# ele devolvia `['VERIFICADO']`: um selo POSITIVO para uma resposta que o
# usuario tinha rebaixado de proposito. A cascata ia toda na direcao errada --
# passava na conferencia 2 (exatamente um selo), entrava em `SELO_POSITIVO` e
# passava a exigir um frame (qualquer frame que existisse servia), e a TABELA
# FINAL imprimia `VERIFICADO` ao lado do numero da secao, que e a saida que um
# leitor futuro usa como resumo. Num arquivo cujo proposito e "que a mesma
# mentira nao volte pela porta da analise", promover um selo negativo a positivo
# e o modo de falha exato que ele existe para impedir.
#
# A docstring do metodo AFIRMAVA que isso estava prevenido, dizendo que
# `NAO RESPONDIDO` era procurado antes e removido. O codigo fazia o oposto -- e
# mesmo a ordem descrita nao resolveria: `NAO RESPONDIDO` nao contem
# `VERIFICADO`, entao remove-lo nao apaga o `NAO VERIFICADO` de outra frase.
#
# Rebaixar para `NAO RESPONDIDO` e a leitura conservadora, e e a que o resto do
# modulo ja assume: na duvida, falhar para o lado do selo mais fraco.
NEGACAO_DE_SELO = re.compile(r"\bNAO\s+(?:VERIFICADO|PARCIAL)\b")

PERGUNTAS_ESPERADAS = 9


class Problema(Exception):
    """Falha de conferencia ja com a mensagem que o leitor precisa ler."""


def sem_acento(texto: str) -> str:
    """`NAO RESPONDIDO` com til vira `NAO RESPONDIDO` sem til.

    O usuario vai editar este documento no portao da Task 2 e pode muito bem
    escrever o selo com acento. Um portao que reprovasse por isso estaria
    punindo exatamente a correcao que D-04 pede.
    """
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c)
    )


class Secao:
    """Uma pergunta do spike: o numero, o selo e os frames que ela cita."""

    def __init__(self, numero: int, titulo: str, linha: int, nivel: int) -> None:
        self.numero = numero
        self.titulo = titulo
        self.linha = linha
        # quantos `#` abriram esta secao -- e o que decide qual cabecalho a fecha
        self.nivel = nivel
        self.corpo: list[str] = []

    @property
    def texto(self) -> str:
        return "\n".join(self.corpo)

    @property
    def selos(self) -> list[str]:
        """Os selos presentes, COM repeticao -- dois selos iguais tambem e erro.

        DOIS PASSOS, e o primeiro e o que importa:

        1. Toda NEGACAO EXPLICITA (`NAO VERIFICADO`, `NAO PARCIAL`) vira
           `NAO RESPONDIDO` antes de qualquer contagem. Sem isso, a busca por
           substring achava o `VERIFICADO` dentro de `NAO VERIFICADO` e promovia
           uma resposta rebaixada a mao para selo POSITIVO -- ver o comentario de
           `NEGACAO_DE_SELO`, com a medicao.
        2. So entao os selos sao contados e removidos, `NAO RESPONDIDO` primeiro
           para nao deixar pedaco para tras.

        A remocao a cada passo e o que impede um mesmo trecho de texto de contar
        duas vezes.
        """
        achados: list[str] = []
        restante = NEGACAO_DE_SELO.sub("NAO RESPONDIDO", sem_acento(self.texto))
        for selo in ORDEM_DE_BUSCA:
            n = restante.count(selo)
            achados.extend([selo] * n)
            restante = restante.replace(selo, "")
        return achados

    @property
    def frames(self) -> list[str]:
        return CAMINHO_DE_FRAME.findall(self.texto)


def evidencia_resolvida(raiz: Path, citado: str) -> bool:
    """O caminho citado aponta para um ARQUIVO, DENTRO da arvore de gravacoes?

    Duas frouxidoes que o `(raiz / citado).exists()` anterior deixava passar, as
    duas MEDIDAS nesta maquina:

    1. `..` NO MEIO DO CAMINHO. `CAMINHO_DE_FRAME` exige o prefixo
       `recordings/`, o que da a impressao de que o escopo esta contido -- e nao
       esta: `recordings/../l2scanner/visao.py` resolvia `True`. Uma citacao
       como `recordings/../tests/fixtures/x.png` satisfazia o portao inteiro sem
       tocar em gravacao nenhuma.
    2. `.exists()` ACEITA DIRETORIO. Um diretorio chamado `frame_000012.png`
       passava. E o modo de falha deterministico dos testes deste projeto e
       exatamente esse -- ver o comentario em `__main__.py`, onde `is_file` foi
       escolhido de proposito pelo mesmo motivo.

    O cabecalho deste modulo promete "RESOLVE cada caminho no sistema de
    arquivos". Um caminho que sai da arvore de gravacoes foi resolvido, mas nao
    e evidencia de spike nenhum.
    """
    return ".." not in Path(citado).parts and (raiz / citado).is_file()


def separar_secoes(texto: str) -> list[Secao]:
    secoes: list[Secao] = []
    corrente: Secao | None = None
    for numero_da_linha, linha in enumerate(texto.splitlines(), start=1):
        numerado = CABECALHO_NUMERADO.match(linha)
        if numerado:
            corrente = Secao(
                int(numerado.group(2)),
                linha.strip(),
                numero_da_linha,
                len(numerado.group(1)),
            )
            secoes.append(corrente)
            continue
        cabecalho = CABECALHO.match(linha)
        if cabecalho and corrente is not None:
            # Um `###` DENTRO de uma resposta `##` e sub-estrutura da resposta,
            # nao o fim dela. So um cabecalho de nivel igual ou mais alto fecha.
            if len(cabecalho.group(1)) <= corrente.nivel:
                corrente = None
            continue
        if corrente is not None:
            corrente.corpo.append(linha)
    return secoes


def conferir_a_numeracao(secoes: list[Secao]) -> None:
    """Conferencia 1: 9 secoes, numeradas de 1 a 9, sem repetir e sem pular."""
    if len(secoes) != PERGUNTAS_ESPERADAS:
        raise Problema(
            f"o documento tem {len(secoes)} secao(oes) numerada(s), e o spike "
            f"tem {PERGUNTAS_ESPERADAS} perguntas. Encontradas: "
            f"{[s.numero for s in secoes]}"
        )
    numeros = [s.numero for s in secoes]
    if numeros != list(range(1, PERGUNTAS_ESPERADAS + 1)):
        raise Problema(
            f"as secoes numeradas sao {numeros}, e deveriam ser "
            f"{list(range(1, PERGUNTAS_ESPERADAS + 1))} nesta ordem. Um numero "
            f"repetido ou pulado significa que uma pergunta do spike ficou sem "
            f"resposta ou foi respondida duas vezes."
        )


def conferir_a_secao(secao: Secao, raiz: Path) -> tuple[str, int, list[str]]:
    """Conferencias 2 e 3. Devolve (selo, frames confirmados, faltando)."""
    selos = secao.selos
    if not selos:
        raise Problema(
            f"secao {secao.numero} (linha {secao.linha}) nao tem selo. Toda "
            f"resposta carrega exatamente um entre {', '.join(SELOS)} -- uma "
            f"resposta sem selo e uma resposta sem compromisso."
        )
    if len(selos) > 1:
        raise Problema(
            f"secao {secao.numero} (linha {secao.linha}) tem {len(selos)} "
            f"selos ({', '.join(selos)}). Uma resposta nao pode ser duas coisas "
            f"ao mesmo tempo -- escolha o mais fraco dos dois."
        )

    selo = selos[0]
    frames = secao.frames
    faltando = [c for c in frames if not evidencia_resolvida(raiz, c)]

    if selo in SELO_POSITIVO and not frames:
        raise Problema(
            f"secao {secao.numero} (linha {secao.linha}) esta selada {selo} e "
            f"nao cita nenhum frame. Um selo positivo sem evidencia e "
            f"exatamente a afirmacao confiante sem lastro que este portao "
            f"existe para recusar: ou cite o frame que voce olhou, ou rebaixe "
            f"para NAO RESPONDIDO dizendo o que faltou gravar."
        )

    return selo, len(frames) - len(faltando), faltando


def conferir(documento: Path, raiz: Path) -> int:
    if not documento.is_file():
        print(f"REPROVADO -- {documento} nao existe.", file=sys.stderr)
        return 1

    texto = documento.read_text(encoding="utf-8")
    secoes = separar_secoes(texto)

    problemas: list[str] = []
    tabela: list[tuple[int, str, int]] = []

    try:
        conferir_a_numeracao(secoes)
    except Problema as erro:
        problemas.append(str(erro))

    for secao in secoes:
        try:
            selo, confirmados, faltando = conferir_a_secao(secao, raiz)
        except Problema as erro:
            problemas.append(str(erro))
            continue
        if faltando:
            problemas.append(
                f"secao {secao.numero}: cita {len(faltando)} frame(s) que NAO "
                f"existem no disco:\n      "
                + "\n      ".join(faltando)
            )
            continue
        tabela.append((secao.numero, selo, confirmados))

    # Conferencia 4, GLOBAL: nada no documento inteiro pode citar um caminho
    # inexistente -- nem uma secao NAO RESPONDIDO, nem a secao de impacto, nem
    # uma nota de rodape.
    todos = CAMINHO_DE_FRAME.findall(texto)
    orfaos = sorted({c for c in todos if not evidencia_resolvida(raiz, c)})
    ja_apontados = {c for p in problemas for c in CAMINHO_DE_FRAME.findall(p)}
    restantes = [c for c in orfaos if c not in ja_apontados]
    if restantes:
        problemas.append(
            f"{len(restantes)} caminho(s) citado(s) FORA das secoes conferidas "
            f"tambem nao existem no disco:\n      " + "\n      ".join(restantes)
        )

    if problemas:
        print(f"REPROVADO -- {len(problemas)} problema(s):\n", file=sys.stderr)
        for problema in problemas:
            print(f"  * {problema}\n", file=sys.stderr)
        print(f"(raiz das gravacoes conferida: {raiz})", file=sys.stderr)
        return 1

    print(f"APROVADO -- as {PERGUNTAS_ESPERADAS} respostas do spike se sustentam.\n")
    print(f"documento: {documento}")
    print(f"raiz das gravacoes: {raiz}")
    print(f"caminhos resolvidos no disco: {len(todos)}\n")
    print("secao  selo             frames confirmados")
    for numero, selo, confirmados in tabela:
        print(f"{str(numero).rjust(5)}  {selo.ljust(15)}  {str(confirmados).rjust(18)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="conferir_spike_respostas",
        description=(
            "Confere se o SPIKE-RESPOSTAS.md se sustenta: 9 secoes numeradas, "
            "um selo por secao, e todo frame citado RESOLVIDO no disco."
        ),
    )
    parser.add_argument(
        "--documento",
        type=Path,
        default=DOCUMENTO_PADRAO,
        help="o SPIKE-RESPOSTAS.md a conferir",
    )
    parser.add_argument(
        "--raiz",
        type=Path,
        default=RAIZ,
        help=(
            "de onde os caminhos `recordings/...` sao resolvidos. `recordings/` "
            "e gitignored e nao se materializa dentro de um git worktree, "
            "entao a analise precisa poder apontar para o checkout principal "
            "(padrao: a raiz deste repositorio)"
        ),
    )
    args = parser.parse_args(argv)
    return conferir(args.documento, args.raiz)


if __name__ == "__main__":
    raise SystemExit(main())
