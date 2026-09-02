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
