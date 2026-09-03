"""SEMEAR a ponte XP<->porcentagem no `calibration.json`: a DECISAO, sem o disco.

POR QUE ISTO NAO MORA DENTRO DA FERRAMENTA DE BANCADA
======================================================
As duas garantias desta operacao — **nao apagar chave alheia** e **nao
sobrescrever calada** — sao regras de negocio, e regra de negocio dentro de um
`argparse` e regra que nenhum teste alcanca. Qualquer forma de rodar uma
ferramenta de `tools/` a partir de um teste (`import`, `runpy`, `subprocess`)
poe o nome dela no arquivo de teste, e o portao desta arvore proibe isso.

Entao a decisao mora aqui: `semear` recebe uma `Calibracao` **ja carregada** e
devolve outra, e **nao le nem escreve arquivo nenhum**. Em `tools/` sobrou o
`argparse`. E o que faz "nenhum teste importa a ferramenta" e "as duas garantias
estao presas por teste" serem verdade ao mesmo tempo — antes eram mutuamente
impossiveis.

A ESCRITA PASSA PELO `salvar` QUE JA EXISTE, SEMPRE
====================================================
Este modulo nao grava, mas quem o usa grava — e grava pelo `Calibracao.salvar`,
com `.tmp` ao lado e troca atomica por `os.replace`. Escrever o
`calibration.json` a mao deixaria um JSON **truncado** se a escrita fosse
interrompida (Ctrl-C impaciente, disco cheio, antivirus segurando o handle), e o
que morre nao e a renda: e o **scanner de alertas de party inteiro**, que e o
produto. O arquivo carrega a party window, os limiares HSV afinados a mao contra
o Gamma da tela do usuario, o `hp_proprio`, treze moldes de glifo e as
assinaturas de nome — tudo desconhecivel a priori e caro de refazer.

A CONSTANTE E A PROCEDENCIA DELA, QUE E O PRODUTO TANTO QUANTO O NUMERO
=======================================================================
Faerlina, nivel 67, **388.700 XP por ponto percentual**, medida em
**2026-09-02** a **55 Hz**, com **240** linhas de chat e **114** eventos de
abate na janela de **150 segundos**. O que torna este numero confiavel e o
**censo completo**: a soma dos 188 degraus e 1903 unidades e a barra andou
exatamente 1903, com **zero** leituras negativas em 8.555 amostras. E ha uma
segunda medicao independente — 383.124, a 0,8 s de amostragem — **1,5% abaixo**,
que e o que da direito de chamar isto de constante e nao de leitura.

**Todos esses numeros estao versionados em
`.planning/workstreams/renda/REQUIREMENTS.md`, REND-08**, com o denominador ao
lado de cada um. Nenhum vira dado sem que exista, em um arquivo do repositorio,
de onde ele saiu.

**ESTE MODULO NAO MEDE NADA.** Medir a ponte exige ler o chat em cadencia alta,
e isso e ferramenta de calibracao — Fase 3 ou tarefa propria, deferida
explicitamente pelo `02-CONTEXT.md`. Aqui so se poe no arquivo um numero que ja
foi medido, e se diz de onde ele veio.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - so para o verificador de tipos
    from .calibracao import Calibracao

# Os dois desfechos possiveis. Textos e nao booleanos, porque quem chama precisa
# IMPRIMIR o desfecho, e um `False` nao diz por que.
SEMEADO = "semeado"
RECUSADO_SEM_CONFIRMACAO = "recusado-sem-confirmacao"


@dataclass(frozen=True)
class EntradaDaPonte:
    """De quem, de que nivel, e o que vai no arquivo.

    O personagem e o nivel viajam SEPARADOS dos valores porque eles sao as
    CHAVES: a constante nao existe sem saber de quem ela e (o multiplicador de
    XP e do personagem — a barra da Faerlina exibe 562%) nem de que nivel (o
    custo do nivel muda).
    """

    personagem: str
    nivel: int
    valores: dict


@dataclass(frozen=True)
class ResultadoDaSemeadura:
    """A `Calibracao` nova, o desfecho, e as DUAS entradas para quem quiser mostrar.

    `existente` e `entrando` viajam juntas mesmo no caso `semeado`, porque quem
    chama precisa poder dizer o que estava la antes — e no caso recusado elas
    sao o produto inteiro: sem as duas lado a lado, a recusa seria um "nao" sem
    argumento, e o usuario nao teria como decidir se confirma.
    """

    calibracao: "Calibracao"
    estado: str
    existente: dict | None
    entrando: dict


# A MEDICAO INTEIRA, COM A PROCEDENCIA JUNTO.
#
# Ela mora NESTE modulo e nao na ferramenta, e a razao e simples: e o teste que
# precisa dela para fechar a C-8. Um dado que so a ferramenta conhecesse seria um
# dado que nenhum teste ve — e o caminho "XP absoluto disponivel" terminaria a
# fase sem nunca ter rodado contra numero de verdade.
ENTRADA_MEDIDA = EntradaDaPonte(
    personagem="Faerlina",
    nivel=67,
    valores={
        "xp_por_ponto": 388_700,
        "medido_em": "2026-09-02",
        "n_abates": 114,
        "n_linhas_de_chat": 240,
        "janela_em_segundos": 150,
        "observacao": (
            "Censo COMPLETO a 55 Hz (0,018 s), 8.555 leituras de EXP em 2,5 "
            "minutos: a soma dos 188 degraus e 1903 unidades e a barra andou "
            "exatamente 1903 (nenhum evento escapou), com ZERO leituras "
            "negativas em 8.555, o que valida o leitor de EXP da Fase 1 de "
            "quebra. O aglomerado do abate isola-se em 114 eventos de media "
            "9,956 unidades, e o chat da 387 XP por abate sobre 240 linhas: "
            "387 / 0,0009956 = 388.700 XP por ponto percentual, e 38,87 "
            "milhoes no nivel. SEGUNDA MEDICAO INDEPENDENTE: 383.124 a 0,8 s "
            "de amostragem, 1,5% abaixo: sao duas medicoes que nao "
            "compartilham o metodo de agrupamento. AGLOMERADO NAO "
            "IDENTIFICADO, registrado e nao escondido: 50 eventos de ~3 "
            "unidades, a 20 por minuto, somando 7,9% do XP da janela; nao sao "
            "erro de leitura (nao ha degrau negativo) e nao sao abate (o chat "
            "mostra 363 a 439 XP por abate, um intervalo de 1,2x e nao de "
            "3x). Isso NAO afeta a constante: ela converte pontos percentuais "
            "em XP do nivel, seja qual for a origem do ganho. Tudo versionado "
            "em .planning/workstreams/renda/REQUIREMENTS.md, REND-08."
        ),
    },
)


def _entrada_existente(ponte: dict | None, personagem: str, nivel: int):
    """A entrada que ja esta la para aquele personagem naquele nivel, ou nada.

    AS DUAS FORMAS DA CHAVE CONTAM. Em memoria, antes do primeiro `salvar`, ela
    pode ser o inteiro `67`; depois da ida e volta pelo JSON, ela e o texto
    `"67"`. Um `semear` que so olhasse uma das duas sobrescreveria a outra
    calada — e ainda deixaria as DUAS no arquivo, o que e pior: um arquivo com
    duas constantes para o mesmo nivel, e a leitura escolhendo por ordem.
    """
    if not ponte:
        return None
    do_personagem = ponte.get(personagem)
    if not isinstance(do_personagem, dict):
        return None
    entrada = do_personagem.get(str(nivel))
    if entrada is None:
        entrada = do_personagem.get(nivel)
    return entrada if isinstance(entrada, dict) else None


def semear(
    calibracao: "Calibracao",
    entrada: EntradaDaPonte,
    *,
    confirmar: bool = False,
) -> ResultadoDaSemeadura:
    """Poe a constante medida na ponte, ou recusa e diz por que.

    ELA MUDA SO `renda_ponte_de_xp`, E SO A ENTRADA DAQUELE PERSONAGEM NAQUELE
    NIVEL. A preservacao das outras chaves ja e de graca — o `salvar` emite
    todos os campos de `fields(Calibracao)`, e a Fase 1 provou isso duas vezes.
    O que esta funcao acrescenta e a prova de que a MUDANCA e cirurgica, e ela e
    um teste de dicionario antes e depois com a chave da ponte removida dos dois
    lados.

    E ELA NAO SOBRESCREVE CALADA. Com entrada ja existente para o mesmo
    personagem e o mesmo nivel e sem `confirmar=True`, devolve
    `recusado-sem-confirmacao` carregando as DUAS entradas, e a `Calibracao`
    devolvida e literalmente a recebida. Uma constante recalibrada com mais
    tempo de medicao e melhor que a semeada — recalibrar por cima e o caminho
    normal previsto pela CTX-8 —, e nenhuma camada pode desfazer isso em
    silencio. **A decisao mora aqui, num lugar so**, e nao no `argparse`.

    NAO TOCA DISCO. Recebe uma `Calibracao` ja carregada e devolve outra; nao
    conhece caminho, nao chama `carregar` e nao chama `salvar`. E o que a torna
    testavel sem `runpy`, sem `subprocess` e sem nomear a ferramenta de bancada.
    """
    ponte = calibracao.renda_ponte_de_xp or {}
    existente = _entrada_existente(ponte, entrada.personagem, entrada.nivel)
    entrando = dict(entrada.valores)

    if existente is not None and not confirmar:
        return ResultadoDaSemeadura(
            calibracao=calibracao,
            estado=RECUSADO_SEM_CONFIRMACAO,
            existente=existente,
            entrando=entrando,
        )

    # Copia rasa por personagem: a `Calibracao` de quem chamou nao pode ser
    # mutada, senao a recusa perderia a entrada antiga que ela precisa mostrar.
    nova = {
        nome: dict(niveis) if isinstance(niveis, dict) else niveis
        for nome, niveis in ponte.items()
    }
    do_personagem = nova.setdefault(entrada.personagem, {})
    # A chave inteira sai junto: as duas formas sao a MESMA entrada, e deixar as
    # duas no arquivo daria duas constantes para um nivel so.
    do_personagem.pop(entrada.nivel, None)
    do_personagem[str(entrada.nivel)] = entrando

    return ResultadoDaSemeadura(
        calibracao=replace(calibracao, renda_ponte_de_xp=nova),
        estado=SEMEADO,
        existente=existente,
        entrando=entrando,
    )
