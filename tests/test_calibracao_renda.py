"""A amarra estrutural que este repositorio nunca teve: nenhum campo some calado.

O DANO QUE ESTE ARQUIVO EXISTE PARA IMPEDIR, NO TEMPO PRESENTE PORQUE ELE AINDA
E POSSIVEL HOJE
==============================================================================
`Calibracao.salvar` monta o dicionario a partir de uma **lista literal de
chaves**. Um campo declarado no dataclass e esquecido nessa lista e gravado como
se nada fosse — a `Calibracao` em memoria tem o valor, o arquivo em disco nao —
e **some na proxima leitura**, sem uma linha de erro. O usuario recalibra, ve o
console dizer que gravou, e no dia seguinte a feature esta desligada.

Isso nao e hipotetico nesta arvore. Em 2026-08-30 uma rodada de calibracao
montou uma `Calibracao` do zero e o `salvar` gravou o objeto inteiro por cima de
treze moldes de glifo, tres ancoras e a grade. O conserto daquele incidente foi
uma lista de DONOS de campo; o que faltava, e o que entra aqui, e a prova de que
a lista do `salvar` cobre o dataclass.

POR QUE OS DOIS TESTES QUE JA EXISTEM NAO PEGAM ISSO
=====================================================
`tests/test_calibracao_mercado.py` tem `test_sem_a_chave_o_campo_sai_None` e
`test_ida_e_volta_devolve_os_mesmos_valores`, e os dois sao parametrizados por
uma **lista de campos escrita a mao**. A mao que esquece o campo no `salvar` e a
mesma que esquece na lista do teste: os dois passam de maos dadas, e o campo
some do mesmo jeito.

Este arquivo tira a lista da mao e a **deriva de `dataclasses.fields`**. Um
campo novo entra na conferencia sozinho, no dia em que for declarado.

E ELE TEM CONTROLE POSITIVO, porque sem ele o teste seria vacuo: um `salvar` que
emitisse chave nenhuma e um `fields` que devolvesse nada passariam juntos. O
controle monta o dicionario emitido, remove UMA chave conhecida, e afirma que a
mesma conferencia acusa aquela chave **pelo nome**.

E A AMARRA VALE MAIS AGORA DO QUE VALIA ANTES, e a razao e desconfortavel: a
renda inteira mora atras de DUAS chaves. `renda_por_personagem` carrega, por
personagem, tres regioes e tres pisos; `renda_moldes_da_barra` carrega um
conjunto de moldes que so a mao do usuario produz. A amarra estrutural prova que
as chaves sao emitidas — ela **nao ve nada dentro delas**. Por isso ela ganha
irmaos: a ida e volta do ANINHADO, com dois personagens dentro e uma sub-chave
que este codigo nao conhece, e a ida e volta do conjunto INCOMPLETO de moldes.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path

import numpy as np
import pytest

from l2scanner.calibracao import Calibracao, CalibracaoInvalida
from l2scanner.frames import Regiao
from l2scanner.identidade import Assinatura
from l2scanner.mercado_leitura import conjunto_descreve_numeros

FIXTURA_DE_MERCADO = (
    Path(__file__).parent / "fixtures" / "mercado" / "calibracao_de_fixture.json"
)
FIXTURA_DE_RENDA = (
    Path(__file__).parent / "fixtures" / "renda" / "calibracao_de_fixture.json"
)


def renda_por_personagem_de_exemplo() -> dict:
    """Dois personagens, com retangulos de nivel DIFERENTES.

    Os dois valores sao os medidos em campo, e a diferenca entre eles e o achado
    inteiro: a janela de status de cada instancia foi posicionada a mao pelo
    usuario, e um retangulo unico leria o nivel certo de uma e um numero
    plausivel e errado da outra.
    """
    def entrada(nivel: Regiao) -> dict:
        return {
            "barra_esquerda": {
                "regiao": Regiao(0, 1368, 520, 24).como_dict(),
                "piso_de_brilho": 160,
                "largura_da_banda": 3,
            },
            "barra_direita": {
                "regiao": Regiao(1540, 1358, 160, 34).como_dict(),
                "piso_de_brilho": 185,
                "largura_da_banda": 3,
            },
            "nivel": {
                "regiao": nivel.como_dict(),
                "piso_de_brilho": 200,
                "largura_da_banda": 4,
            },
            "geometria_da_janela": {"largura": 1720, "altura": 1392},
        }

    return {
        "Faerlina": entrada(Regiao(246, 736, 30, 20)),
        "Yazalaque": entrada(Regiao(236, 750, 30, 20)),
    }


# O conjunto INCOMPLETO — oito rotulos mais a virgula, sem o `5` e sem o `7` — e
# o estado real de quem parou no meio de uma rodada do cortador. Cada molde
# carrega bytes DIFERENTES de proposito: um `salvar` que reordenasse ou
# normalizasse o conjunto seria pego pela comparacao byte a byte, e nao so pela
# contagem.
ROTULOS_INCOMPLETOS = "01234689,"


def moldes_da_barra_de_exemplo(rotulos: str = ROTULOS_INCOMPLETOS) -> dict:
    return {
        "moldes": [
            {
                "glifo": rotulo,
                "altura": 10,
                "largura": 5,
                "molde": {
                    "altura": 10,
                    "largura": 5,
                    "bytes": f"{indice:02x}" * 50,
                },
            }
            for indice, rotulo in enumerate(rotulos)
        ],
        "piso_de_leitura": 0.47,
        "margem_de_leitura": 0.037,
        "folga_de_cola": None,
    }


# A PROCEDENCIA MEDIDA, escrita uma vez e reusada por toda entrada de exemplo.
#
# Ela nao e enfeite de fixtura: o validador EXIGE os tres numeros, porque uma
# constante medida em seis minutos e uma medida em tres horas nao valem o mesmo,
# e quem le tem de conseguir saber qual e qual (CTX-8).
PROCEDENCIA_DE_EXEMPLO = {
    "medido_em": "2026-09-02",
    "n_abates": 114,
    "n_linhas_de_chat": 240,
    "janela_em_segundos": 150,
}


def ponte_de_xp_de_exemplo() -> dict:
    """Dois personagens, e DOIS NIVEIS dentro de um deles.

    O nivel 66 da Faerlina nao e enfeite: ele e o VIZINHO que o acessor nao
    pode devolver quando o nivel atual nao tem entrada. Sem ele dentro do
    arquivo, o teste da recusa passaria por vacuidade — estaria afirmando que
    nao houve queda para uma entrada que nunca existiu.
    """

    def entrada(xp_por_ponto: int) -> dict:
        return {
            "xp_por_ponto": xp_por_ponto,
            **PROCEDENCIA_DE_EXEMPLO,
            "observacao": (
                "censo completo a 55 Hz: 188 degraus somando 1903 unidades "
                "contra 1903 de avanco da propria barra, com zero leituras "
                "negativas em 8.555 amostras"
            ),
        }

    return {
        "Faerlina": {"66": entrada(383_124), "67": entrada(388_700)},
        "Yazalaque": {"70": entrada(410_000)},
    }


# Os campos cujo VALIDADOR e exigente demais para um valor generico por tipo.
# Eles sao overrides de VALOR, e nunca da LISTA: a lista continua saindo de
# `dataclasses.fields`, e um campo novo que este mapa nao conheca cai no
# despachante por tipo — e, se o tipo tambem for novo, o teste FALHA em vez de
# pular o campo em silencio.
VALORES_ESPECIAIS = {
    "mercado_limiar_de_template": 0.87,
    "mercado_tolerancia_do_cruzamento": 0.0,
    "renda_por_personagem": renda_por_personagem_de_exemplo(),
    "renda_moldes_da_barra": moldes_da_barra_de_exemplo(),
    # O QUINTO LUGAR DA TERCEIRA CHAVE, e o que some do radar.
    #
    # `_valor_por_tipo` despacha por TIPO, e `dict | None` cai no ramo generico
    # que devolve `{"uma": "coisa"}`. Como a ponte tem validador DE FORMA — a
    # CTX-8 exige que a constante carregue procedencia, e procedencia e forma —,
    # o valor generico nao passa e a ida e volta quebra com uma mensagem que nao
    # aponta para o motivo. Ja custou quarenta minutos duas vezes nesta arvore.
    "renda_ponte_de_xp": ponte_de_xp_de_exemplo(),
    "assinaturas": [
        Assinatura(nome="Faerlina", mascara=np.ones((4, 4), dtype=np.uint8))
    ],
    "nomes": ["Faerlina", "Yazalaque"],
    "mercado_templates_de_nome": [
        {"nome": "Adena", "altura": 9, "largura": 4, "molde": {
            "altura": 9, "largura": 4, "bytes": "ab" * 36}}
    ],
    "mercado_templates_de_digito_cromatico": [
        {"glifo": "0", "altura": 9, "largura": 4, "molde": {
            "altura": 9, "largura": 4, "bytes": "cd" * 36}}
    ],
}


def _valor_por_tipo(campo) -> object:
    """Um valor plausivel para o campo, escolhido pelo TIPO e nunca pelo nome.

    Enumerar nomes a mao e exatamente o defeito que este arquivo existe para
    pegar, entao o despachante e por tipo. O `raise` no fim e a parte que
    importa: um campo de tipo desconhecido derruba o teste com o nome dele, em
    vez de ser pulado em silencio e voltar a ser invisivel.
    """
    if campo.name in VALORES_ESPECIAIS:
        return copy.deepcopy(VALORES_ESPECIAIS[campo.name])
    tipo = str(campo.type)
    if tipo.startswith("Regiao"):
        return Regiao(esquerda=11, topo=22, largura=33, altura=44)
    if tipo.startswith("str"):
        return "valor-de-teste"
    if tipo.startswith("float"):
        return 0.5
    if tipo.startswith("int"):
        return 2
    if tipo.startswith("dict"):
        return {"uma": "coisa"}
    if tipo.startswith("list"):
        return [{"uma": "coisa"}]
    raise AssertionError(
        f"o campo {campo.name!r} tem tipo {tipo!r}, que este teste nao sabe "
        f"preencher. Ensine-o aqui: um campo que este arquivo pula volta a ser "
        f"um campo que pode sumir do `salvar` sem ninguem notar."
    )


def calibracao_com_todo_campo_preenchido() -> Calibracao:
    """Uma `Calibracao` sem nenhum campo no default, montada por `fields`.

    Ela parte da fixtura de mercado — que ja carrega valores que passam por
    todos os validadores do arranque — e preenche o que sobrou. A LISTA vem de
    `dataclasses.fields(Calibracao)`, sempre.
    """
    cal = Calibracao.carregar(FIXTURA_DE_MERCADO)
    for campo in dataclasses.fields(Calibracao):
        atual = getattr(cal, campo.name)
        vazio = atual is None or (isinstance(atual, (list, dict)) and not atual)
        if vazio:
            object.__setattr__(cal, campo.name, _valor_por_tipo(campo))
    return cal


def diferenca_entre_campos_e_chaves(dados: dict) -> tuple[set[str], set[str]]:
    """`(campos sem chave, chaves sem campo)`. As DUAS direcoes importam.

    Campo sem chave e o esquecimento no `salvar`: o valor existe em memoria e
    nao chega ao disco. Chave sem campo e uma chave orfa que o `carregar` nunca
    vai ler: ela sobrevive no arquivo do usuario dando a impressao de estar
    ligada, e nao esta.
    """
    campos = {f.name for f in dataclasses.fields(Calibracao)}
    chaves = set(dados)
    return campos - chaves, chaves - campos


class TestAAmarraEstrutural:
    """Todo campo do dataclass aparece como chave no JSON, e vice-versa."""

    def test_NENHUM_CAMPO_DO_DATACLASS_FICA_DE_FORA_DO_SALVAR(self, tmp_path):
        cal = calibracao_com_todo_campo_preenchido()
        alvo = tmp_path / "calibration.json"
        cal.salvar(alvo)
        dados = json.loads(alvo.read_text(encoding="utf-8"))

        sem_chave, orfas = diferenca_entre_campos_e_chaves(dados)
        assert not sem_chave, (
            f"estes campos existem no dataclass e NAO sao emitidos pelo "
            f"`salvar`: {sorted(sem_chave)}. Eles sao gravados como se nada "
            f"fosse e somem na proxima leitura, sem uma linha de erro."
        )
        assert not orfas, (
            f"estas chaves sao emitidas e NAO correspondem a campo nenhum: "
            f"{sorted(orfas)}. O `carregar` nunca vai le-las, e elas ficam no "
            f"arquivo do usuario parecendo ligadas."
        )

    def test_CONTROLE_POSITIVO_UMA_CHAVE_REMOVIDA_E_ACUSADA_PELO_NOME(
        self, tmp_path
    ):
        """Sem este controle o teste acima e vacuo.

        Um `salvar` que emitisse chave nenhuma e um `fields` que devolvesse nada
        passariam de maos dadas. Aqui a conferencia recebe um dicionario com uma
        chave a menos e tem de dizer QUAL.
        """
        cal = calibracao_com_todo_campo_preenchido()
        alvo = tmp_path / "calibration.json"
        cal.salvar(alvo)
        dados = json.loads(alvo.read_text(encoding="utf-8"))

        mutilado = dict(dados)
        del mutilado["renda_por_personagem"]
        sem_chave, orfas = diferenca_entre_campos_e_chaves(mutilado)
        assert sem_chave == {"renda_por_personagem"}
        assert not orfas

    def test_CONTROLE_POSITIVO_UMA_CHAVE_ORFA_TAMBEM_E_ACUSADA(self, tmp_path):
        cal = calibracao_com_todo_campo_preenchido()
        alvo = tmp_path / "calibration.json"
        cal.salvar(alvo)
        dados = json.loads(alvo.read_text(encoding="utf-8"))

        mutilado = dict(dados)
        mutilado["renda_piso_de_brilho"] = 180
        sem_chave, orfas = diferenca_entre_campos_e_chaves(mutilado)
        assert not sem_chave
        assert orfas == {"renda_piso_de_brilho"}

    def test_A_MONTAGEM_NAO_DEIXA_NENHUM_CAMPO_NO_DEFAULT(self):
        """A guarda da guarda: um campo vazio nao exercita o `salvar`."""
        cal = calibracao_com_todo_campo_preenchido()
        vazios = [
            f.name
            for f in dataclasses.fields(Calibracao)
            if getattr(cal, f.name) is None
            or (
                isinstance(getattr(cal, f.name), (list, dict))
                and not getattr(cal, f.name)
            )
        ]
        assert not vazios, vazios


class TestAIdaEVoltaCompleta:
    """Todo campo preenchido, salvo e relido, volta com o mesmo valor."""

    def test_TODO_CAMPO_SOBREVIVE_AO_SALVAR_MAIS_CARREGAR(self, tmp_path):
        cal = calibracao_com_todo_campo_preenchido()
        alvo = tmp_path / "calibration.json"
        cal.salvar(alvo)
        de_volta = Calibracao.carregar(alvo)

        divergentes = []
        for campo in dataclasses.fields(Calibracao):
            antes, depois = getattr(cal, campo.name), getattr(de_volta, campo.name)
            if campo.name == "assinaturas":
                # A assinatura carrega uma matriz numpy, e comparar dataclass
                # com numpy dentro levanta em vez de responder. A forma
                # serializada e a comparacao honesta aqui.
                antes = [a.como_dict() for a in antes]
                depois = [a.como_dict() for a in depois]
            if antes != depois:
                divergentes.append(campo.name)
        assert not divergentes, (
            f"estes campos mudaram na ida e volta: {divergentes}"
        )


class TestOsValidadoresDaRenda:
    """Presente tem de estar certo; ausente e legitimo."""

    def _com_renda(self, tmp_path: Path, por_personagem) -> Path:
        dados = json.loads(FIXTURA_DE_RENDA.read_text(encoding="utf-8"))
        if por_personagem is None:
            dados.pop("renda_por_personagem", None)
        else:
            dados["renda_por_personagem"] = por_personagem
        alvo = tmp_path / "calibration.json"
        alvo.write_text(json.dumps(dados), encoding="utf-8")
        return alvo

    def test_UM_PISO_ABAIXO_DO_MINIMO_E_RECUSADO(self, tmp_path):
        por_personagem = renda_por_personagem_de_exemplo()
        por_personagem["Faerlina"]["nivel"]["piso_de_brilho"] = 0
        with pytest.raises(CalibracaoInvalida) as erro:
            Calibracao.carregar(self._com_renda(tmp_path, por_personagem))
        assert "Recalibre" in str(erro.value), "a mensagem precisa dizer o conserto"

    def test_UM_PISO_ACIMA_DO_MAXIMO_E_RECUSADO(self, tmp_path):
        por_personagem = renda_por_personagem_de_exemplo()
        por_personagem["Yazalaque"]["barra_esquerda"]["piso_de_brilho"] = 255
        with pytest.raises(CalibracaoInvalida) as erro:
            Calibracao.carregar(self._com_renda(tmp_path, por_personagem))
        assert "255" in str(erro.value)

    def test_UM_PISO_BOOLEANO_E_RECUSADO_COM_MENSAGEM_PROPRIA(self, tmp_path):
        """`bool` e subclasse de `int`, e por isso precisa de recusa PROPRIA.

        `True` passaria por `isinstance(valor, int)` e viraria piso 1 calado —
        que e o caso `0` disfarcado: a mascara fica cheia, todo pixel vira
        tinta, e o OCR le ruido com confianca.
        """
        por_personagem = renda_por_personagem_de_exemplo()
        por_personagem["Faerlina"]["barra_direita"]["piso_de_brilho"] = True
        with pytest.raises(CalibracaoInvalida) as erro:
            Calibracao.carregar(self._com_renda(tmp_path, por_personagem))
        assert "bool" in str(erro.value), (
            "a recusa precisa nomear o tipo: sem isso o usuario ve 'precisa ser "
            "um inteiro' olhando para um valor que ele considera um inteiro"
        )

    def test_UM_PISO_DO_TIPO_ERRADO_E_RECUSADO(self, tmp_path):
        por_personagem = renda_por_personagem_de_exemplo()
        por_personagem["Faerlina"]["nivel"]["piso_de_brilho"] = "200"
        with pytest.raises(CalibracaoInvalida):
            Calibracao.carregar(self._com_renda(tmp_path, por_personagem))

    def test_UM_RETANGULO_DE_LARGURA_ZERO_E_RECUSADO(self, tmp_path):
        por_personagem = renda_por_personagem_de_exemplo()
        por_personagem["Faerlina"]["nivel"]["regiao"]["largura"] = 0
        with pytest.raises(CalibracaoInvalida) as erro:
            Calibracao.carregar(self._com_renda(tmp_path, por_personagem))
        assert "largura" in str(erro.value)

    def test_UM_RETANGULO_COM_ORIGEM_NEGATIVA_PASSA(self, tmp_path):
        """Negativo e LEGITIMO: e a regra de `Regiao`, e recusar aqui mataria
        um HUD posicionado a esquerda da origem."""
        por_personagem = renda_por_personagem_de_exemplo()
        por_personagem["Faerlina"]["nivel"]["regiao"]["esquerda"] = -10
        cal = Calibracao.carregar(self._com_renda(tmp_path, por_personagem))
        assert cal.renda_do_personagem("Faerlina")["nivel"]["regiao"]["esquerda"] == -10

    def test_A_CHAVE_INTEIRAMENTE_AUSENTE_PASSA(self, tmp_path):
        """Feature nao calibrada e feature DESLIGADA, e nao arquivo invalido."""
        cal = Calibracao.carregar(self._com_renda(tmp_path, None))
        assert cal.renda_por_personagem is None
        assert cal.versao == 2


class TestOAninhadoDeRendaPorPersonagem:
    """A amarra estrutural ve a CHAVE; estes testes veem o que mora dentro."""

    def _gravar(self, tmp_path: Path, cal: Calibracao) -> Calibracao:
        alvo = tmp_path / "calibration.json"
        cal.salvar(alvo)
        return Calibracao.carregar(alvo)

    def test_DOIS_PERSONAGENS_SOBREVIVEM_COM_OS_NIVEIS_DISTINTOS(self, tmp_path):
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        de_volta = self._gravar(tmp_path, cal)
        faerlina = de_volta.renda_do_personagem("Faerlina")["nivel"]["regiao"]
        yazalaque = de_volta.renda_do_personagem("Yazalaque")["nivel"]["regiao"]
        assert (faerlina["esquerda"], faerlina["topo"]) == (246, 736)
        assert (yazalaque["esquerda"], yazalaque["topo"]) == (236, 750)
        assert faerlina != yazalaque, (
            "os dois retangulos sao DIFERENTES de proposito: um retangulo unico "
            "leria o nivel certo de uma instancia e um numero plausivel e "
            "errado da outra"
        )

    def test_UMA_SUBCHAVE_DESCONHECIDA_SOBREVIVE_A_IDA_E_VOLTA(self, tmp_path):
        """O analogo, uma camada abaixo, do defeito que a amarra pega em cima.

        O aninhado e REEMITIDO e nao reconstruido campo a campo. Se algum dia
        alguem o reconstruir, uma sub-chave que este codigo nao conhece nasce
        apagada — e o campo novo do calibrador some no dia em que for gravado.
        """
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        por_personagem = copy.deepcopy(cal.renda_por_personagem)
        por_personagem["Faerlina"]["campo_do_futuro"] = {"medido_em": "2027"}
        object.__setattr__(cal, "renda_por_personagem", por_personagem)
        de_volta = self._gravar(tmp_path, cal)
        assert de_volta.renda_do_personagem("Faerlina")["campo_do_futuro"] == {
            "medido_em": "2027"
        }

    def test_UMA_ENTRADA_INCOMPLETA_E_RECUSADA(self, tmp_path):
        """Uma entrada pela metade e PIOR que uma entrada ausente.

        A ausente desliga a feature; a pela metade faz a leitura procurar um
        campo que nao tem endereco.
        """
        dados = json.loads(FIXTURA_DE_RENDA.read_text(encoding="utf-8"))
        dados["renda_por_personagem"]["Yazalaque"].pop("barra_direita")
        alvo = tmp_path / "calibration.json"
        alvo.write_text(json.dumps(dados), encoding="utf-8")
        with pytest.raises(CalibracaoInvalida) as erro:
            Calibracao.carregar(alvo)
        assert "barra_direita" in str(erro.value)


class TestOConjuntoDeMoldesDaBarra:
    """O conjunto INCOMPLETO sobrevive inteiro, incompleto e na mesma ordem."""

    def test_UM_CONJUNTO_INCOMPLETO_VOLTA_SEM_SER_COMPLETADO(self, tmp_path):
        """Um `salvar` que "normalizasse" o conjunto inventaria moldes vazios.

        E tres moldes vazios que passam pela guarda de conjunto completo sao a
        falha ABERTA que a exigencia de conjunto existe para impedir: o conjunto
        pela metade lendo com a confianca do conjunto inteiro.
        """
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        conjunto = moldes_da_barra_de_exemplo()
        object.__setattr__(cal, "renda_moldes_da_barra", copy.deepcopy(conjunto))
        alvo = tmp_path / "calibration.json"
        cal.salvar(alvo)
        de_volta = Calibracao.carregar(alvo).renda_moldes_da_barra

        assert [m["glifo"] for m in de_volta["moldes"]] == [
            m["glifo"] for m in conjunto["moldes"]
        ], "o conjunto voltou reordenado ou completado"
        assert len(de_volta["moldes"]) == len(ROTULOS_INCOMPLETOS)
        for antes, depois in zip(conjunto["moldes"], de_volta["moldes"]):
            assert depois["molde"]["bytes"] == antes["molde"]["bytes"], (
                f"os bytes do molde {antes['glifo']!r} mudaram na ida e volta"
            )
        assert isinstance(de_volta["piso_de_leitura"], float)
        assert isinstance(de_volta["margem_de_leitura"], float)

    def test_A_GUARDA_DE_CONJUNTO_COMPLETO_REPROVA_O_CONJUNTO_RECARREGADO(
        self, tmp_path
    ):
        """A clausula que separa o ARRANQUE da LEITURA.

        O arranque confere FORMA e carrega o conjunto pela metade, porque ele e
        o estado normal do usuario entre duas rodadas do cortador. Quem confere
        COMPLETUDE e a leitura, e ela recusa nomeando os que faltam. Se um dia
        o conjunto recarregado passar nesta guarda sem o cortador ter rodado, e
        porque alguem o completou com molde vazio — e um molde vazio lendo com a
        confianca de um conjunto certo e a falha aberta.
        """
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        object.__setattr__(
            cal, "renda_moldes_da_barra", moldes_da_barra_de_exemplo()
        )
        alvo = tmp_path / "calibration.json"
        cal.salvar(alvo)
        de_volta = Calibracao.carregar(alvo).renda_moldes_da_barra

        rotulos = {m["glifo"] for m in de_volta["moldes"]}
        assert conjunto_descreve_numeros(rotulos) is False
        assert {"5", "7"}.isdisjoint(rotulos)

    def test_UM_CONJUNTO_COMPLETO_PASSA_NA_MESMA_GUARDA(self, tmp_path):
        """O controle sem o qual a asserção acima passaria com a guarda quebrada."""
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        object.__setattr__(
            cal, "renda_moldes_da_barra", moldes_da_barra_de_exemplo("0123456789,")
        )
        alvo = tmp_path / "calibration.json"
        cal.salvar(alvo)
        de_volta = Calibracao.carregar(alvo).renda_moldes_da_barra
        rotulos = {m["glifo"] for m in de_volta["moldes"]}
        assert conjunto_descreve_numeros(rotulos) is True

    def test_A_CHAVE_AUSENTE_PASSA_COM_A_VERSAO_INTACTA(self, tmp_path):
        dados = json.loads(FIXTURA_DE_RENDA.read_text(encoding="utf-8"))
        dados.pop("renda_moldes_da_barra", None)
        alvo = tmp_path / "calibration.json"
        alvo.write_text(json.dumps(dados), encoding="utf-8")
        cal = Calibracao.carregar(alvo)
        assert cal.renda_moldes_da_barra is None
        assert cal.versao == 2


class TestAPonteDeXpNoArquivo:
    """A terceira chave da renda: por personagem E POR NIVEL (REND-08, CTX-8)."""

    def _com_a_ponte(self, tmp_path: Path, ponte) -> Path:
        dados = json.loads(FIXTURA_DE_RENDA.read_text(encoding="utf-8"))
        if ponte is None:
            dados.pop("renda_ponte_de_xp", None)
        else:
            dados["renda_ponte_de_xp"] = ponte
        alvo = tmp_path / "calibration.json"
        alvo.write_text(json.dumps(dados), encoding="utf-8")
        return alvo

    def test_A_CHAVE_AUSENTE_PASSA_COM_A_VERSAO_INTACTA(self, tmp_path):
        """Ninguem e obrigado a recalibrar: a chave e opcional e a versao fica em 2."""
        cal = Calibracao.carregar(self._com_a_ponte(tmp_path, None))
        assert cal.renda_ponte_de_xp is None
        assert cal.versao == 2

    def test_DOIS_PERSONAGENS_E_DOIS_NIVEIS_SOBREVIVEM_A_IDA_E_VOLTA(self, tmp_path):
        cal = Calibracao.carregar(
            self._com_a_ponte(tmp_path, ponte_de_xp_de_exemplo())
        )
        alvo = tmp_path / "de-volta.json"
        cal.salvar(alvo)
        de_volta = Calibracao.carregar(alvo)

        assert de_volta.ponte_do_nivel("Faerlina", 66)["xp_por_ponto"] == 383_124
        assert de_volta.ponte_do_nivel("Faerlina", 67)["xp_por_ponto"] == 388_700
        assert de_volta.ponte_do_nivel("Yazalaque", 70)["xp_por_ponto"] == 410_000
        assert de_volta.renda_ponte_de_xp == ponte_de_xp_de_exemplo()

    def test_UMA_SUBCHAVE_DESCONHECIDA_SOBREVIVE_A_IDA_E_VOLTA(self, tmp_path):
        """O dict e CRU: uma sub-chave que este codigo ainda nao conhece fica.

        Se algum dia alguem reconstruir a entrada campo a campo, o campo novo
        da ferramenta de medicao nasce apagado no dia em que for gravado.
        """
        ponte = ponte_de_xp_de_exemplo()
        ponte["Faerlina"]["67"]["campo_do_futuro"] = {"n_sessoes": 3}
        cal = Calibracao.carregar(self._com_a_ponte(tmp_path, ponte))
        alvo = tmp_path / "de-volta.json"
        cal.salvar(alvo)
        de_volta = Calibracao.carregar(alvo)
        assert de_volta.ponte_do_nivel("Faerlina", 67)["campo_do_futuro"] == {
            "n_sessoes": 3
        }


class TestOValidadorDaPonteDeXp:
    """Presente tem de estar certo. E a forma inclui a PROCEDENCIA."""

    def _carregar(self, tmp_path: Path, ponte):
        dados = json.loads(FIXTURA_DE_RENDA.read_text(encoding="utf-8"))
        dados["renda_ponte_de_xp"] = ponte
        alvo = tmp_path / "calibration.json"
        alvo.write_text(json.dumps(dados), encoding="utf-8")
        return Calibracao.carregar(alvo)

    def test_O_CONTROLE_A_ENTRADA_COMPLETA_PASSA(self, tmp_path):
        """Sem este controle, um validador que recusasse TUDO passaria nos irmaos."""
        cal = self._carregar(tmp_path, ponte_de_xp_de_exemplo())
        assert cal.ponte_do_nivel("Faerlina", 67)["xp_por_ponto"] == 388_700

    @pytest.mark.parametrize(
        "valor",
        [0, -1, "388700", 388_700.0, None],
        ids=["zero", "negativo", "texto", "flutuante", "nulo"],
    )
    def test_UM_XP_POR_PONTO_INVALIDO_E_RECUSADO_NOMEANDO_PERSONAGEM_E_NIVEL(
        self, tmp_path, valor
    ):
        ponte = ponte_de_xp_de_exemplo()
        ponte["Faerlina"]["67"]["xp_por_ponto"] = valor
        with pytest.raises(CalibracaoInvalida) as erro:
            self._carregar(tmp_path, ponte)
        mensagem = str(erro.value)
        assert "Faerlina" in mensagem, "a recusa precisa dizer de QUEM e a entrada"
        assert "67" in mensagem, "a recusa precisa dizer de QUAL NIVEL e a entrada"
        assert "Recalibre" in mensagem, "a mensagem precisa carregar o conserto"

    def test_UM_XP_POR_PONTO_AUSENTE_E_RECUSADO(self, tmp_path):
        ponte = ponte_de_xp_de_exemplo()
        ponte["Faerlina"]["67"].pop("xp_por_ponto")
        with pytest.raises(CalibracaoInvalida) as erro:
            self._carregar(tmp_path, ponte)
        mensagem = str(erro.value)
        assert "xp_por_ponto" in mensagem
        assert "Faerlina" in mensagem and "67" in mensagem

    def test_UM_XP_POR_PONTO_BOOLEANO_E_RECUSADO_COM_MENSAGEM_PROPRIA(self, tmp_path):
        """`True` e um `int` de valor 1, e uma ponte de 1 XP por ponto e absurda.

        Sem recusa PROPRIA para `bool` ele passaria por `isinstance(v, int)` e
        viraria uma constante que converte 8 pontos percentuais em 8 XP — um
        numero perfeitamente formatado e a trinta milhoes de distancia do certo.
        """
        ponte = ponte_de_xp_de_exemplo()
        ponte["Faerlina"]["67"]["xp_por_ponto"] = True
        with pytest.raises(CalibracaoInvalida) as erro:
            self._carregar(tmp_path, ponte)
        assert "bool" in str(erro.value), (
            "a recusa precisa nomear o tipo: sem isso o usuario le 'precisa ser "
            "um inteiro' olhando para um valor que ele considera um inteiro"
        )

    @pytest.mark.parametrize(
        "campo", ["n_abates", "n_linhas_de_chat", "janela_em_segundos"]
    )
    def test_CADA_CAMPO_DE_PROCEDENCIA_AUSENTE_E_RECUSADO_PELO_NOME(
        self, tmp_path, campo
    ):
        """A procedencia e OBRIGATORIA, e a razao e a CTX-8.

        Uma constante medida em seis minutos e uma medida em tres horas nao
        valem o mesmo. Sem os numeros ao lado, ninguem consegue auditar depois
        qual das duas esta no arquivo.
        """
        ponte = ponte_de_xp_de_exemplo()
        ponte["Faerlina"]["67"].pop(campo)
        with pytest.raises(CalibracaoInvalida) as erro:
            self._carregar(tmp_path, ponte)
        mensagem = str(erro.value)
        assert campo in mensagem, "a recusa precisa nomear o campo que falta"
        assert "Faerlina" in mensagem and "67" in mensagem

    def test_A_DATA_DA_MEDICAO_AUSENTE_E_RECUSADA(self, tmp_path):
        """"Quando foi medida" e procedencia tanto quanto "com quantos abates"."""
        ponte = ponte_de_xp_de_exemplo()
        ponte["Faerlina"]["67"].pop("medido_em")
        with pytest.raises(CalibracaoInvalida) as erro:
            self._carregar(tmp_path, ponte)
        assert "medido_em" in str(erro.value)

    @pytest.mark.parametrize(
        "campo", ["n_abates", "n_linhas_de_chat", "janela_em_segundos"]
    )
    def test_UM_CAMPO_DE_PROCEDENCIA_NAO_POSITIVO_E_RECUSADO(self, tmp_path, campo):
        """Zero abates ou zero segundo de janela nao e procedencia: e ausencia."""
        ponte = ponte_de_xp_de_exemplo()
        ponte["Faerlina"]["67"][campo] = 0
        with pytest.raises(CalibracaoInvalida) as erro:
            self._carregar(tmp_path, ponte)
        assert campo in str(erro.value)

    def test_UMA_CHAVE_DE_NIVEL_QUE_NAO_E_NUMERO_E_RECUSADA(self, tmp_path):
        ponte = ponte_de_xp_de_exemplo()
        ponte["Faerlina"]["sessenta e sete"] = ponte["Faerlina"].pop("67")
        with pytest.raises(CalibracaoInvalida) as erro:
            self._carregar(tmp_path, ponte)
        mensagem = str(erro.value)
        assert "sessenta e sete" in mensagem
        assert "nivel" in mensagem.lower(), (
            "a mensagem precisa dizer o que se esperava naquela posicao"
        )

    def test_UM_NOME_DE_PERSONAGEM_VAZIO_E_RECUSADO(self, tmp_path):
        ponte = ponte_de_xp_de_exemplo()
        ponte[""] = ponte.pop("Yazalaque")
        with pytest.raises(CalibracaoInvalida):
            self._carregar(tmp_path, ponte)

    def test_UMA_ENTRADA_QUE_NAO_E_OBJETO_E_RECUSADA(self, tmp_path):
        ponte = ponte_de_xp_de_exemplo()
        ponte["Faerlina"]["67"] = 388_700
        with pytest.raises(CalibracaoInvalida) as erro:
            self._carregar(tmp_path, ponte)
        assert "Faerlina" in str(erro.value)

    def test_A_CHAVE_QUE_NAO_E_OBJETO_E_RECUSADA(self, tmp_path):
        with pytest.raises(CalibracaoInvalida) as erro:
            self._carregar(tmp_path, [{"Faerlina": {}}])
        assert "renda_ponte_de_xp" in str(erro.value)


class TestOAcessorDaPonteNuncaCaiParaOVizinho:
    """A proibicao de queda mora em UM lugar so, e e este acessor."""

    def _cal(self, tmp_path: Path, ponte=None) -> Calibracao:
        dados = json.loads(FIXTURA_DE_RENDA.read_text(encoding="utf-8"))
        if ponte is not None:
            dados["renda_ponte_de_xp"] = ponte
        alvo = tmp_path / "calibration.json"
        alvo.write_text(json.dumps(dados), encoding="utf-8")
        return Calibracao.carregar(alvo)

    def test_O_NIVEL_PEDIDO_E_O_NIVEL_DEVOLVIDO(self, tmp_path):
        cal = self._cal(tmp_path, ponte_de_xp_de_exemplo())
        assert cal.ponte_do_nivel("Faerlina", 66)["xp_por_ponto"] == 383_124
        assert cal.ponte_do_nivel("Faerlina", 67)["xp_por_ponto"] == 388_700

    def test_SEM_ENTRADA_PARA_O_NIVEL_ATUAL_NAO_CAI_PARA_O_ANTERIOR(self, tmp_path):
        """O defeito que a CTX-8 proibe com todas as letras.

        A constante do 66 aplicada ao 67 produz um numero com a mesma cara e
        errado. O teste afirma, na mesma funcao, que a entrada do 66 EXISTIA —
        sem isso ele passaria por vacuidade.
        """
        ponte = ponte_de_xp_de_exemplo()
        ponte["Faerlina"].pop("67")
        cal = self._cal(tmp_path, ponte)

        assert cal.ponte_do_nivel("Faerlina", 66) is not None, (
            "o vizinho tem de EXISTIR, senao a assercao de baixo e vacua"
        )
        assert cal.ponte_do_nivel("Faerlina", 67) is None

    def test_SEM_ENTRADA_PARA_O_PERSONAGEM_NAO_CAI_PARA_O_OUTRO(self, tmp_path):
        cal = self._cal(tmp_path, ponte_de_xp_de_exemplo())
        assert cal.ponte_do_nivel("Yazalaque", 70) is not None, (
            "a entrada vizinha tem de EXISTIR, senao a assercao de baixo e vacua"
        )
        assert cal.ponte_do_nivel("Yazalaque", 67) is None
        assert cal.ponte_do_nivel("Korzis", 67) is None

    def test_A_CHAVE_DE_NIVEL_INTEIRA_E_ENCONTRADA_DE_VOLTA(self, tmp_path):
        """O modo de falha classico desta forma, e ele NAO LEVANTA.

        JSON nao tem chave inteira: `{67: ...}` gravado vira `{"67": ...}`. Um
        acessor que comparasse o inteiro com a chave de texto so devolveria
        nada, e o painel diria "indisponivel" para sempre sem ninguem entender
        por que.
        """
        cal = self._cal(tmp_path)
        cal.renda_ponte_de_xp = {
            "Faerlina": {67: dict(PROCEDENCIA_DE_EXEMPLO, xp_por_ponto=388_700)}
        }

        assert cal.ponte_do_nivel("Faerlina", 67)["xp_por_ponto"] == 388_700

        alvo = tmp_path / "de-volta.json"
        cal.salvar(alvo)
        de_volta = Calibracao.carregar(alvo)
        assert list(de_volta.renda_ponte_de_xp["Faerlina"]) == ["67"], (
            "o JSON converteu a chave para TEXTO, que e o ponto deste teste"
        )
        assert de_volta.ponte_do_nivel("Faerlina", 67)["xp_por_ponto"] == 388_700

    def test_A_CHAVE_INTEIRAMENTE_AUSENTE_DEVOLVE_NADA_E_NAO_LEVANTA(self, tmp_path):
        cal = self._cal(tmp_path)
        assert cal.renda_ponte_de_xp is None
        assert cal.ponte_do_nivel("Faerlina", 67) is None

    def test_SEM_NOME_E_SEM_NIVEL_DEVOLVE_NADA(self, tmp_path):
        cal = self._cal(tmp_path, ponte_de_xp_de_exemplo())
        assert cal.ponte_do_nivel(None, 67) is None
        assert cal.ponte_do_nivel("Faerlina", None) is None
