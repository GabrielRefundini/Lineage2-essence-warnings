"""A PERGUNTA DO BATISMO SO VAI PARA O PRIVADO DO DONO.

POR QUE ELA SAI DO GRUPO (pedido do usuario em 2026-09-04)

Tres razoes que ja estavam no codigo, so nao estavam ligadas uma na outra:

- `/batizar` esta FORA de `COMANDOS_DE_MEMBRO`. So o dono alcanca o comando,
  porque nome errado e corrupcao duravel num acervo que nunca e podado. Entao
  a pergunta no grupo pede uma acao que 4 a 8 pessoas NAO PODEM executar;
- ela e a mensagem mais pesada do canal: e a unica do produto que leva imagem;
- e o grupo de WhatsApp e o ativo mais fragil do produto, o mesmo que
  `notificador.formatar_grupo` ja protege de rajada.

O DESTINO E O MECANISMO QUE JA EXISTE, e nao um segundo. `conversa_alvo` do
`NotificadorChatwoot.enviar` ja significa "so para esta conversa" desde
CORR-03, e e por ele que `.status` responde onde perguntaram. A conversa e a
PRIMEIRA de `CHATWOOT_CONVERSAS_COMANDO`, que e a definicao operacional de
"o privado do dono" que este projeto tem: e de la que o `/batizar` pode chegar.

E SEM PRIVADO CONFIGURADO NAO SE PERGUNTA. Nao e timidez: e a trava de D-05
estendida. Sem `CHATWOOT_CONVERSAS_COMANDO` nao existe caminho de volta para o
`/batizar`, entao a pergunta seria ruido puro no grupo — e ela QUEIMA o
marcador `perguntado_<chave>`, que e para sempre. Calar preserva a unica
pergunta que cada assinatura tem para o dia em que o dono configurar o canal.

Nenhum caso aqui abre socket, e nenhum encosta em `config.toml`,
`calibration.json` ou `.identidades/` do repositorio. Tudo roda em `tmp_path`.
Os idiomas sao COPIADOS de `test_uma_pergunta_por_pessoa.py`, e nao importados,
pela razao que aquele arquivo ja escreve: importar entre arquivos de teste cria
dependencia entre eles.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.acervo import (
    PREFIXO_ASSINATURA,
    PREFIXO_PERGUNTA,
    AcervoDeIdentidades,
    chave_da_assinatura,
)
from l2scanner.agenda import RegistroEmDisco
from l2scanner.aprendiz import AjustesDoAprendiz, Aprendiz
from l2scanner.batismo import pendentes_do_acervo
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.identidade import Assinatura
from l2scanner.notificador import ConfigChatwoot, conversa_do_dono
from l2scanner.rastreador import Rastreador
from l2scanner.sessao import Sessao

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "identidade"


# ---------------------------------------------------------------------------
# Fixtures e falsos
# ---------------------------------------------------------------------------


@pytest.fixture
def calibracao() -> Calibracao:
    cal = Calibracao.carregar(FIXTURES / "calibracao.json")
    cal.assinaturas = []
    return cal


@pytest.fixture
def pixels() -> np.ndarray:
    px = cv2.imread(str(FIXTURES / "party_ordem_original.png"), cv2.IMREAD_COLOR)
    assert px is not None, "fixture da party nao pode ser lida"
    return px


class DespachanteQueGrava:
    """Grava `(texto, categoria, conversa_alvo)` em vez de mandar para a rede.

    Truthy de proposito: `Sessao._despachar` testa `if self.despachante`.
    """

    def __init__(self) -> None:
        self.despachos: list[tuple[str, object, str | None]] = []

    def despachar(
        self,
        texto,
        categoria=None,
        conversa_alvo=None,
        anexos=None,
        texto_sem_anexos=None,
    ) -> None:
        self.despachos.append((texto, categoria, conversa_alvo))

    @property
    def perguntas(self) -> list[tuple[str, str | None]]:
        """So a PERGUNTA do batismo, com o destino dela."""
        return [
            (texto, alvo) for texto, _, alvo in self.despachos if "/batizar" in texto
        ]


class SilencioParado:
    def ativo(self):
        return False

    def atualizar(self, agora):
        return None


def mascara_com_texto(semente: int, altura: int = 20, largura: int = 110):
    """Uma mascara 0/1 com a forma de um nome: colunas acesas conhecidas."""
    mascara = np.zeros((altura, largura), dtype=np.uint8)
    mascara[4 : altura - 4, semente % 5 + 2 :: 5] = 1
    mascara[2, 4 + semente] = 1
    return mascara


def semear(pasta: Path, semente: int) -> str:
    """Escreve uma entrada anonima A MAO, e devolve a chave."""
    pasta.mkdir(parents=True, exist_ok=True)
    assinatura = Assinatura(nome="", mascara=mascara_com_texto(semente))
    chave = chave_da_assinatura(assinatura)
    corpo = assinatura.como_dict()
    corpo.pop("nome", None)
    (pasta / f"{PREFIXO_ASSINATURA}{chave}.json").write_text(
        json.dumps(corpo), encoding="utf-8"
    )
    return chave


def marcadores_da_pasta(pasta: Path) -> list[str]:
    return sorted(
        c.name for c in pasta.iterdir() if c.name.startswith(PREFIXO_PERGUNTA)
    )


def montar_sessao(tmp_path, calibracao, *, acervo, despachante, dono) -> Sessao:
    return Sessao(
        cal=calibracao,
        rastreador=Rastreador(
            nomes=list(calibracao.nomes), assinaturas_configuradas=False
        ),
        eventos_agendados=[],
        registro=RegistroEmDisco(tmp_path / "agenda"),
        silencio=SilencioParado(),
        despachante=despachante,
        aprendiz=Aprendiz(acervo, AjustesDoAprendiz(leituras_para_aprender=3)),
        acervo=acervo,
        pendentes_de_batismo=pendentes_do_acervo(acervo),
        conversa_do_dono=dono,
    )


def um_tick(sessao, pixels, momento: float = 1_700_000_000.0) -> None:
    sessao.tick(
        Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK), momento=momento
    )


# ---------------------------------------------------------------------------
# 1. QUAL CONVERSA E "O PRIVADO DO DONO"
# ---------------------------------------------------------------------------


def config_com(comando: list[str]) -> ConfigChatwoot:
    return ConfigChatwoot(
        url="https://exemplo",
        conta="1",
        token="t",
        conversas=["31"],
        conversas_de_comando=comando,
    )


class TestQualConversaEODono:
    def test_e_a_conversa_de_COMANDO_e_nao_a_de_aviso(self):
        """A de aviso e o grupo. A pergunta nao pode cair nela."""
        assert conversa_do_dono(config_com(["1"])) == "1"

    def test_com_varias_e_a_PRIMEIRA(self):
        """Todas sao canais de comando do dono; a imagem sai UMA vez so.

        Mandar para as N repetiria a mensagem mais pesada do produto em cada
        uma delas, e o marcador de D-04 e queimado uma vez.
        """
        assert conversa_do_dono(config_com(["7", "1", "9"])) == "7"

    def test_sem_conversa_de_comando_nao_ha_privado(self):
        """`None` e a resposta honesta: nao existe volta para o `/batizar`."""
        assert conversa_do_dono(config_com([])) is None

    def test_a_de_aviso_nunca_serve_de_reserva(self):
        """Cair no grupo por falta de privado seria desfazer o pedido inteiro."""
        config = config_com([])
        assert conversa_do_dono(config) not in config.conversas


# ---------------------------------------------------------------------------
# 2. A SESSAO MANDA A PERGUNTA PARA O PRIVADO
# ---------------------------------------------------------------------------


class TestASessaoMandaParaOPrivado:
    def test_a_pergunta_sai_com_a_conversa_do_dono_no_alvo(
        self, tmp_path, calibracao, pixels
    ):
        acervo = AcervoDeIdentidades(tmp_path / "ident")
        semear(tmp_path / "ident", 1)
        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path, calibracao, acervo=acervo, despachante=despachante, dono="1"
        )

        um_tick(sessao, pixels)

        assert despachante.perguntas, "a pergunta do batismo nao saiu"
        _, alvo = despachante.perguntas[0]
        assert alvo == "1", (
            f"a pergunta saiu para {alvo!r}. `None` significa as conversas de "
            f"AVISO, que e o grupo"
        )

    def test_sem_privado_nao_pergunta_e_nao_queima_o_marcador(
        self, tmp_path, calibracao, pixels
    ):
        """A trava de D-05 estendida: sem destino, a pergunta ESPERA.

        Queimar o marcador aqui deixaria a pessoa anonima para sempre, porque
        `perguntado_<chave>` nao tem desfazer e nao ha comando de esquecer no
        v1 para ele.
        """
        pasta = tmp_path / "ident"
        acervo = AcervoDeIdentidades(pasta)
        semear(pasta, 2)
        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path, calibracao, acervo=acervo, despachante=despachante, dono=None
        )

        um_tick(sessao, pixels)

        assert despachante.perguntas == []
        assert marcadores_da_pasta(pasta) == [], (
            "sem destino a pergunta nao saiu, mas o marcador foi queimado: a "
            "pessoa ficaria anonima para sempre"
        )


# ---------------------------------------------------------------------------
# 3. OS DOIS GATILHOS. Portao de estrutura, no molde do de
#    `test_a_pergunta_leva_a_imagem.py`: o do arranque exigiria subir o
#    programa inteiro, e o que esta em jogo e uma ligacao que some num refactor
#    sem nenhum teste ficar vermelho.
# ---------------------------------------------------------------------------


def _chamadas_de_despacho_da_pergunta(fonte: str) -> list[ast.Call]:
    achadas = []
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Call):
            continue
        alvo = getattr(no.func, "id", None) or getattr(no.func, "attr", None)
        if alvo not in {"despachar", "_despachar"}:
            continue
        primeiro = no.args[0] if no.args else None
        if isinstance(primeiro, ast.Attribute) and (
            getattr(primeiro.value, "id", None) == "pergunta"
        ):
            achadas.append(no)
    return achadas


class TestOPrivadoChegaNosDoisGatilhos:
    ARQUIVOS = ("sessao.py", "__main__.py")

    @pytest.mark.parametrize("arquivo", ARQUIVOS)
    def test_o_despacho_da_pergunta_leva_conversa_alvo(self, arquivo):
        fonte = (RAIZ / "l2scanner" / arquivo).read_text(encoding="utf-8")
        chamadas = _chamadas_de_despacho_da_pergunta(fonte)
        assert chamadas, f"{arquivo}: nenhum despacho de `pergunta.<campo>`"
        for chamada in chamadas:
            passados = {palavra.arg for palavra in chamada.keywords}
            assert "conversa_alvo" in passados, (
                f"{arquivo}:{chamada.lineno}: a pergunta sai sem destino, e "
                f"sem destino ela vai para as conversas de AVISO — o grupo"
            )

    @pytest.mark.parametrize("arquivo", ARQUIVOS)
    def test_o_portao_acusaria_o_alvo_arrancado(self, arquivo):
        """Guarda contra prova vazia, POR ARQUIVO."""
        fonte = (RAIZ / "l2scanner" / arquivo).read_text(encoding="utf-8")
        envenenado = fonte.replace("conversa_alvo=", "_arrancado=")
        assert envenenado != fonte, "a mutacao plantada nao pegou"
        for chamada in _chamadas_de_despacho_da_pergunta(envenenado):
            if "conversa_alvo" not in {p.arg for p in chamada.keywords}:
                return
        raise AssertionError(
            f"o portao nao acusaria um despacho de {arquivo} sem `conversa_alvo=`"
        )

    def test_o_laco_principal_passa_a_conversa_do_dono_para_a_sessao(self):
        """Sem esta ligacao a `Sessao` cala para sempre: `dono=None`."""
        fonte = (RAIZ / "l2scanner" / "__main__.py").read_text(encoding="utf-8")
        for no in ast.walk(ast.parse(fonte)):
            if isinstance(no, ast.Call) and getattr(no.func, "id", None) == "Sessao":
                if "conversa_do_dono" in {p.arg for p in no.keywords}:
                    return
        raise AssertionError(
            "`laco_principal` monta a Sessao sem `conversa_do_dono=`: a "
            "pergunta do tick ficaria sem destino e nao sairia nunca"
        )
