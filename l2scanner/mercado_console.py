"""O DESENHO do modo mercado: linha ao vivo e resumo da sessao (LEIT-04).

ELAS DEVOLVEM TEXTO E NUNCA IMPRIMEM
=====================================
E a disciplina que `console.moldurar` ja segue neste projeto, e o que torna o
desenho afirmavel por teste sem capturar stdout e sem montar um laco. Quem
imprime e o laco, com `log.info`, e assim a mesma string vai para o console E
para o `scanner.log` rotativo - que e onde a forense de um farm de tres horas
mora.

TEXTO PURO, SEM DEPENDENCIA NOVA
=================================
O `CLAUDE.md` recomenda `rich`, e ele NAO esta instalado. A razao de nao
instala-lo e DOUTRINA DE ZERO-INSTALL - o `vigiar-party.bat` roda
`pip install -r requirements.txt` na primeira execucao, e cada dependencia nova
e um jeito novo de esse arranque falhar na maquina do usuario.

A JUSTIFICATIVA ERRADA, CORRIGIDA POR ESCRITO: a primeira redacao do
`04-CONTEXT.md` dizia que o FIRE-01 barraria o `rich`. NAO BARRARIA. A banlist
do FIRE-01 (`tests/test_firewall_escopo.py`) e so de SINTESE DE INPUT -
`pyautogui`, `pynput`, `keyboard`, `mouse`, `pydirectinput`, autoit - e ela nao
tem nada a dizer sobre uma biblioteca de console. A decisao continua de pe pelo
zero-install; o argumento que a sustentava caiu, e um argumento que cai precisa
dizer que caiu.

AS DUAS METADES, SEMPRE
========================
No censo, 151 paginas lidas contra 189 PERDIDAS. Um console que mostrasse so a
metade boa faria o usuario confiar numa cobertura que nao existe e sair do farm
achando que coletou o dobro. Por isso "perdidas" aparece na linha ao vivo, no
resumo, e mesmo quando "lidas" e zero.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from . import console

# Os SETE contadores publicos do `LeitorDePagina`, com o rotulo que o usuario le.
# A ordem e a da leitura humana: primeiro as duas metades que julgam a sessao,
# depois os tres estados que explicam o que aconteceu com o resto, e por fim os
# dois sinais de saude da captura.
ROTULOS_DOS_CONTADORES = (
    ("paginas_lidas", "paginas lidas"),
    ("paginas_perdidas", "paginas PERDIDAS"),
    ("paginas_vazias", "paginas vazias (sem conteudo)"),
    ("paginas_de_outro_layout", "paginas de outro layout"),
    ("ticks_com_painel_aberto", "ticks com o painel aberto"),
    ("frames_congelados", "frames congelados"),
    ("linhas_descartadas", "linhas descartadas"),
)


@dataclass
class OrcamentoDoTick:
    """Quanto tempo cada volta custou, e quantas estouraram o intervalo.

    E a metade de DETC-02 que o programa PODE afirmar sobre si mesmo. O laco ja
    calcula `agora - inicio` para compensar a deriva da cadencia; guardar essa
    lista custa um `append` por tick e transforma "acho que nao pesou" num
    numero que o usuario le no fim da sessao.

    O que ela NAO mede esta escrito no resumo: contencao entre TRES processos e
    propriedade do SISTEMA (CPU, GPU, sessoes WGC, agendador do Windows), e so o
    portao humano de campo a fecha.
    """

    limite: float
    tempos: list[float] = field(default_factory=list)

    def registrar(self, segundos: float) -> None:
        self.tempos.append(float(segundos))

    @property
    def total(self) -> int:
        return len(self.tempos)

    @property
    def estouros(self) -> int:
        return sum(1 for t in self.tempos if t > self.limite)

    def _quantil(self, fracao: float) -> float:
        """Indexacao sobre a lista ORDENADA, sem dependencia nova.

        `statistics.quantiles` interpola e precisa de pelo menos dois pontos;
        aqui a amostra pode ter UM tick (o usuario fechou logo), e um resumo que
        levantasse ali seria pior que um numero grosseiro. O metodo e o do
        percentil mais proximo, que e o que se espera de "o tick tipico".
        """
        if not self.tempos:
            return 0.0
        ordenados = sorted(self.tempos)
        indice = min(len(ordenados) - 1, int(fracao * len(ordenados)))
        return ordenados[indice]

    @property
    def p50(self) -> float:
        return self._quantil(0.50)

    @property
    def p95(self) -> float:
        return self._quantil(0.95)

    @property
    def maximo(self) -> float:
        return max(self.tempos) if self.tempos else 0.0


def acumular_motivos(acumulados: Counter, leitura) -> None:
    """Soma os motivos de descarte DESTE tick no acumulado da SESSAO.

    O campo `motivos` de uma leitura carrega so o que aquele frame produziu, e
    nao um acumulado - somar por sessao e trabalho de quem chama, e e por isso
    que isto e uma funcao e nao uma propriedade do leitor. Sem ela o resumo
    diria "oclusao: 1" depois de uma hora com a tooltip aberta.

    `leitura` pode ser `None` (tick sem pagina lida) e isso nao e caso especial:
    nao havia motivo nenhum para somar.
    """
    if leitura is None:
        return
    acumulados.update(getattr(leitura, "motivos", ()) or ())


def linha_ao_vivo(leitor, contagem, ultimo_item) -> str:
    """A repintada de 1 Hz: as DUAS metades e o ultimo item reconhecido.

    Ela devolve UMA linha, na cadencia da captura - a mesma do resto do scanner.

    O QUE ELA NAO MOSTRA, E POR QUE: o `residuo_do_cruzamento`. A guarda de
    cruzamento esta DESLIGADA por medicao (02-02), entao o residuo e observacao
    e nao veredito; ele ja esta em coluna propria no CSV, para o usuario olhar no
    Sheets com calma. Num repintar de um segundo ele so competiria por atencao
    com os dois numeros que julgam a sessao.

    `ultimo_item` pode ser `None` no comeco, e ai a linha diz isso por extenso em
    vez de mostrar campo vazio: campo vazio parece defeito.
    """
    return (
        f"mercado | lidas {leitor.paginas_lidas} | "
        f"perdidas {leitor.paginas_perdidas} | "
        f"gravadas {contagem.observacoes} | "
        f"ultimo item: {ultimo_item if ultimo_item else '(nenhum ainda)'}"
    )


def transicao_do_painel(aberto: bool) -> str:
    """A UNICA linha que uma mudanca de estado do painel produz.

    Painel fechado e o estado NORMAL e majoritario de um farm real: uma linha
    por tick seriam 3.600 por hora, e o log rotativo perderia a forense que ele
    existe para guardar. O laco usa LATCH nas duas transicoes, no precedente ja
    usado tres vezes em `mercado_pagina.py` (`_layout_ja_recusado`,
    `_congelamento_ja_avisado`, `_falta_ja_avisada`).
    """
    if aberto:
        return "o painel do mercado ABRIU - lendo a grade a cada tick"
    return (
        "o painel do mercado esta FECHADO - nada a ler, e isto e normal. "
        "Abra o World Exchange na aba de negociacao para o modo coletar."
    )


def resumo_da_sessao(leitor, contagem, motivos, orcamento) -> str:
    """O fim da sessao, contando AS DUAS METADES e o que cada uma custou.

    TRES BLOCOS, e a separacao e o conteudo:

    1. Os SETE contadores do leitor - o que a TELA entregou.
    2. As tres contagens de escrita - o que foi para o DISCO. `observacoes`,
       `duplicadas` e `perdidas` sao fatos DIFERENTES e nao se somam: `registrar`
       devolve `False` para chave ja conhecida E para registro desligado, e somar
       os dois faria o resumo dizer "descartei 300 duplicadas" sobre uma sessao
       em que o disco encheu na terceira linha.
    3. Os motivos de descarte agregados por SESSAO, com a contagem de cada um -
       e o que diz ao usuario se vale mover a tooltip ou recalibrar. Os nomes sao
       as CONSTANTES de `mercado_leitura.py` (`oclusao`, `numero`, `cruzamento`,
       `faixa-cinzenta`, `discordancia-entre-escalas`), nunca as palavras do
       CONTEXT, que divergem delas.
    4. O orcamento de tick auto-medido.
    """
    linhas = [
        console.moldurar(
            "RESUMO DA SESSAO DE MERCADO", datetime.now().strftime("%H:%M")
        ),
        "",
        "O QUE A TELA ENTREGOU:",
    ]
    for atributo, rotulo in ROTULOS_DOS_CONTADORES:
        linhas.append(f"  {rotulo:<32} {getattr(leitor, atributo)}")

    linhas += [
        "",
        "O QUE FOI PARA O DISCO (tres fatos diferentes, que nao se somam):",
        f"  observacoes GRAVADAS             {contagem.observacoes}",
        f"  duplicadas descartadas           {contagem.duplicadas}",
        f"  PERDIDAS (registro desligado)    {contagem.perdidas}",
        f"  series distintas nesta sessao    {len(contagem.series)}",
    ]

    linhas += ["", "POR QUE AS LINHAS FORAM DESCARTADAS (somado na sessao):"]
    if motivos:
        for motivo, quantas in sorted(
            motivos.items(), key=lambda par: (-par[1], par[0])
        ):
            linhas.append(f"  {motivo:<32} {quantas}")
    else:
        linhas.append("  nenhuma linha foi descartada nesta sessao")

    linhas += [
        "",
        "O QUE ESTE PROCESSO CUSTOU POR TICK:",
        f"  p50                              {orcamento.p50 * 1000:.0f} ms",
        f"  p95                              {orcamento.p95 * 1000:.0f} ms",
        f"  maximo                           {orcamento.maximo * 1000:.0f} ms",
        f"  ticks que estouraram o orcamento {orcamento.estouros} "
        f"de {orcamento.total} (orcamento: {orcamento.limite:.1f}s)",
        "",
        "  Estes numeros dizem o que ESTE processo custou, e so isso. "
        "Contencao entre",
        "  os tres processos (duas partys mais o mercado) e propriedade do "
        "SISTEMA -",
        "  CPU, GPU, sessoes de captura, agendador do Windows - e nenhum "
        "numero daqui",
        "  a alcanca. Quem fecha isso e conferir os tres no Gerenciador de "
        "Tarefas.",
    ]
    return "\n".join(linhas)
