"""A calibracao de party MIRA uma janela, em vez de varrer o desktop inteiro.

O INCIDENTE QUE ESTE ARQUIVO EXISTE PARA IMPEDIR, medido em 2026-08-30: o
usuario roda DOIS clientes ao mesmo tempo — dois processos `L2.bin`, um com o
titulo `Faerlina - XM Essence` e outro com `Yazalaque - XM Essence`. O
`python -m l2scanner.calibrar --auto` capturava o DESKTOP inteiro e
`calibrar_automatico` procurava faixas vermelhas na imagem TODA, agrupando-as
por espacamento regular. Com duas party windows visiveis ele agrupa barras dos
DOIS clientes e deduz uma geometria que nao e de nenhum — e como cada passo
interno parece bem-sucedido, isso e gravado CALADO.

E a mesma familia do incidente das 27 chaves apagadas: o perigo nao e o erro
que grita, e o que se certifica sozinho.

DUAS DISCIPLINAS INEGOCIAVEIS DESTE ARQUIVO:

1. NOMES NEUTROS. As fixtures usam `Alfa` e `Beta`, nunca o roster real. Um
   teste que soubesse quem o usuario e passaria a afirmar a maquina de quem o
   roda, em vez de afirmar o codigo.

2. TODO caso que chama `main()` monkeypatcha `ARQUIVO_CALIBRACAO` para dentro
   de `tmp_path`, e falsifica `achar_janela`/`origem_da_janela`/`JanelaSource`.
   Sem os tres, a suite exigiria o jogo ABERTO para passar — e a falha
   apareceria longe da causa. Os seams sao nomeados em `l2scanner.calibrar`,
   que e ONDE OS NOMES VIVEM (eles sao importados la); patchar
   `l2scanner.captura_janela` nao alcanca nada.
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pytest

import l2scanner.calibrar
import l2scanner.config
from l2scanner.calibracao import (
    LIMIARES_HP_PADRAO,
    LIMIARES_MP_PADRAO,
    Calibracao,
    LayoutDaParty,
    descrever_geometria_da_tela,
)
from l2scanner.frames import Regiao

ALFA = "Alfa - XM Essence"
BETA = "Beta - XM Essence"

# A origem da janela mirada, em coordenadas de desktop. Escolhida diferente de
# (0,0) de proposito: e o que permite afirmar que o `(ox, oy)` que chegou ao
# resto de `main()` veio da JANELA, e nao do desktop.
ORIGEM_MIRADA = (300, 150)


@pytest.fixture(scope="module")
def geo() -> str:
    """A geometria da tela, lida UMA vez — o teste nao depende da tela."""
    return descrever_geometria_da_tela()


def _party(geo: str) -> Calibracao:
    """A calibracao que a rodada vai produzir — so campos de party."""
    return Calibracao(
        party_window=Regiao(esquerda=100, topo=200, largura=300, altura=400),
        ancora=Regiao(esquerda=0, topo=0, largura=40, altura=28),
        layout=LayoutDaParty(
            icone_x=4,
            icone_y=6,
            icone_tamanho=22,
            barra_x=30,
            barra_largura=120,
            barra_altura=8,
            hp_y=10,
            mp_y=20,
            passo=44,
            max_linhas=8,
        ),
        limiares_hp=LIMIARES_HP_PADRAO,
        limiares_mp=LIMIARES_MP_PADRAO,
        geometria_da_tela=geo,
    )


class Cenario:
    """O que o teste OBSERVOU da rodada — quem foi mirado, quem foi chamado."""

    def __init__(self) -> None:
        self.titulos_abertos: list[str] = []
        self.fechamentos = 0
        self.capturas_de_desktop = 0
        self.fallbacks = 0
        self.selecoes: list[tuple] = []
        self.alvo_do_automatico: list[tuple] = []


def _dirigir(
    monkeypatch,
    tmp_path,
    argv,
    *,
    personagem=None,
    janelas=(),
    party=None,
    contem=None,
    frame=None,
    erro_ao_abrir=None,
    alvo_calibracao=None,
) -> tuple[int, Cenario]:
    """Roda o `main()` de verdade, com o disco e as janelas presos ao teste."""
    cenario = Cenario()
    alvo = alvo_calibracao or (tmp_path / "calibration.json")

    # SEM ESTA LINHA A SUITE APAGA O calibration.json DA MAQUINA DE QUEM A
    # RODA — o incidente de 2026-08-30, reproduzido dentro do CI. NAO REMOVA.
    monkeypatch.setattr(l2scanner.calibrar, "ARQUIVO_CALIBRACAO", alvo)

    quadro_da_janela = (
        frame if frame is not None else np.zeros((400, 400, 3), dtype=np.uint8)
    )

    class _JanelaFalsa:
        """Um `JanelaSource` que REGISTRA com que titulo foi construido.

        E essa gravacao que prova qual janela foi mirada — sem ela o teste so
        conseguiria afirmar que ALGUMA janela foi lida.
        """

        def __init__(self, titulo, *args, **kwargs):
            cenario.titulos_abertos.append(titulo)
            if erro_ao_abrir is not None:
                raise erro_ao_abrir

        def capturar_completo(self):
            return quadro_da_janela

        def fechar(self):
            cenario.fechamentos += 1

    def _capturar_tela():
        cenario.capturas_de_desktop += 1
        return np.zeros((500, 500, 3), dtype=np.uint8), 0, 0

    def _automatico(pixels, ox, oy):
        cenario.alvo_do_automatico.append((pixels.shape, ox, oy))
        return party

    def _selecionando(pixels, ox, oy):
        cenario.selecoes.append((pixels.shape, ox, oy))
        return party

    def _fallback():
        cenario.fallbacks += 1
        return None

    monkeypatch.setattr(
        l2scanner.calibrar, "ler_personagem_do_jogo", lambda *a, **k: personagem
    )
    monkeypatch.setattr(
        l2scanner.calibrar, "listar_janelas_do_jogo", lambda *a, **k: list(janelas)
    )
    monkeypatch.setattr(l2scanner.calibrar, "achar_janela", lambda titulo: 4242)
    monkeypatch.setattr(
        l2scanner.calibrar, "origem_da_janela", lambda hwnd: ORIGEM_MIRADA
    )
    monkeypatch.setattr(l2scanner.calibrar, "JanelaSource", _JanelaFalsa)
    monkeypatch.setattr(l2scanner.calibrar, "capturar_tela", _capturar_tela)
    monkeypatch.setattr(l2scanner.calibrar, "calibrar_automatico", _automatico)
    monkeypatch.setattr(l2scanner.calibrar, "calibrar_selecionando", _selecionando)
    monkeypatch.setattr(l2scanner.calibrar, "_tentar_pelas_janelas_do_jogo", _fallback)
    monkeypatch.setattr(l2scanner.calibrar, "janela_que_contem", lambda *a, **k: contem)
    monkeypatch.setattr(
        l2scanner.calibrar, "achar_barra_do_proprio", lambda *a, **k: None
    )
    # `conferir_visualmente` grava PNG na RAIZ do repositorio e nada tem a
    # dizer sobre o que este arquivo afirma.
    monkeypatch.setattr(
        l2scanner.calibrar, "conferir_visualmente", lambda *a, **k: None
    )
    # O `sleep` de 0.6s existe para deixar chegar um frame de verdade; com uma
    # dupla no lugar da WGC ele so faz a suite demorar.
    monkeypatch.setattr(l2scanner.calibrar.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(sys, "argv", ["l2scanner.calibrar", *argv])

    return l2scanner.calibrar.main(), cenario


def _escrever_toml(caminho: Path, corpo: str) -> Path:
    caminho.write_text(corpo, encoding="utf-8")
    return caminho


# ---------------------------------------------------------------------------
# A chave no config.toml
# ---------------------------------------------------------------------------


class TestALeituraDaChave:
    def test_le_o_personagem_da_secao_jogo(self, tmp_path):
        caminho = _escrever_toml(
            tmp_path / "config.toml", '[jogo]\npersonagem = "Alfa"\n'
        )
        assert l2scanner.config.ler_personagem_do_jogo(caminho) == "Alfa"

    def test_secao_ausente_nao_e_erro(self, tmp_path):
        caminho = _escrever_toml(tmp_path / "config.toml", "[[evento]]\nnome = 'x'\n")
        assert l2scanner.config.ler_personagem_do_jogo(caminho) is None

    def test_arquivo_inexistente_nao_e_erro(self, tmp_path):
        ausente = tmp_path / "nao-existe.toml"
        assert l2scanner.config.ler_personagem_do_jogo(ausente) is None

    def test_espacos_em_volta_saem_e_so_espacos_e_ausencia(self, tmp_path):
        com_espacos = _escrever_toml(
            tmp_path / "a.toml", '[jogo]\npersonagem = "  Alfa  "\n'
        )
        assert l2scanner.config.ler_personagem_do_jogo(com_espacos) == "Alfa"

        vazio = _escrever_toml(tmp_path / "b.toml", '[jogo]\npersonagem = "   "\n')
        assert l2scanner.config.ler_personagem_do_jogo(vazio) is None

    def test_toml_quebrado_recusa_citando_o_arquivo(self, tmp_path):
        from l2scanner.agenda import AgendaInvalida

        caminho = _escrever_toml(tmp_path / "config.toml", "[jogo\npersonagem =")

        with pytest.raises(AgendaInvalida) as erro:
            l2scanner.config.ler_personagem_do_jogo(caminho)
        assert "config.toml" in str(erro.value)

    def test_valor_que_nao_e_texto_recusa_dizendo_o_tipo(self, tmp_path):
        from l2scanner.agenda import AgendaInvalida

        caminho = _escrever_toml(
            tmp_path / "config.toml", '[jogo]\npersonagem = ["Alfa", "Beta"]\n'
        )

        with pytest.raises(AgendaInvalida) as erro:
            l2scanner.config.ler_personagem_do_jogo(caminho)
        assert "list" in str(erro.value)

    def test_um_caminho_explicito_le_so_aquele_arquivo(self, tmp_path):
        """Sem isso, o guarda do arquivo do repositorio leria a maquina."""
        _escrever_toml(tmp_path / "config.local.toml", '[jogo]\npersonagem = "Beta"\n')
        versionado = _escrever_toml(tmp_path / "config.toml", "# nada aqui\n")

        assert l2scanner.config.ler_personagem_do_jogo(versionado) is None


# ---------------------------------------------------------------------------
# A escolha da janela — funcao PURA, testavel sem o jogo aberto
# ---------------------------------------------------------------------------


class TestAEscolhaDaJanela:
    def test_a_chave_do_config_escolhe_entre_duas_janelas(self):
        escolhida = l2scanner.calibrar.escolher_janela_do_jogo(
            [ALFA, BETA], None, "Alfa"
        )
        assert escolhida == ALFA

    def test_a_caixa_nao_decide(self):
        """D-03 — o servidor nao permite dois nicks que so diferem em caixa."""
        escolhida = l2scanner.calibrar.escolher_janela_do_jogo(
            [ALFA, BETA], None, "alfa"
        )
        assert escolhida == ALFA

    def test_sem_pedido_e_sem_personagem_nao_ha_mira_e_nao_ha_recusa(self):
        """D-06 — quem nunca configurou nada nao pode ver a ferramenta parar."""
        escolhida = l2scanner.calibrar.escolher_janela_do_jogo([ALFA, BETA], None, None)
        assert escolhida is None

    def test_o_pedido_vence_a_chave_do_config(self):
        """D-01 — `--janela` na linha de comando vence sempre."""
        escolhida = l2scanner.calibrar.escolher_janela_do_jogo(
            [ALFA, BETA], BETA, "Alfa"
        )
        assert escolhida == BETA

    def test_nenhum_personagem_escrito_no_fonte(self):
        """A prova ESTRUTURAL de D-01.

        `pedido` e `personagem` sem valor padrao significam que nao existe onde
        um nome de personagem se esconder. Uma constante magica aqui estaria
        errada para qualquer outra pessoa que usasse o projeto.
        """
        parametros = inspect.signature(
            l2scanner.calibrar.escolher_janela_do_jogo
        ).parameters
        for nome in ("pedido", "personagem"):
            assert parametros[nome].default is inspect.Parameter.empty, (
                f"`{nome}` ganhou valor padrao — e onde um nome de personagem "
                f"se esconderia."
            )


# ---------------------------------------------------------------------------
# A mira de ponta a ponta
# ---------------------------------------------------------------------------


class TestAMiraLeUmaJanelaSo:
    def test_auto_com_mira_le_so_a_janela_mirada(self, monkeypatch, tmp_path, geo):
        """O caso que prende o incidente dos dois clientes."""
        rc, cenario = _dirigir(
            monkeypatch,
            tmp_path,
            ["--auto"],
            personagem="Alfa",
            janelas=[ALFA, BETA],
            party=_party(geo),
        )

        assert rc == 0
        assert cenario.titulos_abertos == [ALFA], (
            "A janela lida nao foi a mirada — os pixels do outro cliente "
            "entraram na imagem analisada."
        )
        assert cenario.capturas_de_desktop == 0, (
            "O desktop foi capturado mesmo com mira ativa: as barras dos DOIS "
            "clientes voltaram a poder ser agrupadas."
        )
        assert cenario.fallbacks == 0, (
            "`_tentar_pelas_janelas_do_jogo` rodou com mira ativa — iterar "
            "todas as janelas contradiz a mira (D-05)."
        )
        assert cenario.fechamentos == 1

    def test_o_automatico_recebe_a_origem_da_janela_e_nao_a_do_desktop(
        self, monkeypatch, tmp_path, geo
    ):
        rc, cenario = _dirigir(
            monkeypatch,
            tmp_path,
            ["--auto"],
            personagem="Alfa",
            janelas=[ALFA, BETA],
            party=_party(geo),
        )
        assert rc == 0
        _, ox, oy = cenario.alvo_do_automatico[0]
        assert (ox, oy) == ORIGEM_MIRADA

    def test_o_console_diz_qual_janela_mirou_e_de_onde_veio_a_mira(
        self, monkeypatch, tmp_path, capsys, geo
    ):
        """Com dois clientes abertos, saber POR QUE aquela foi escolhida e o
        que permite ao usuario perceber um alvo errado ANTES de gravar."""
        rc, _ = _dirigir(
            monkeypatch,
            tmp_path,
            ["--auto"],
            personagem="Alfa",
            janelas=[ALFA, BETA],
            party=_party(geo),
        )
        saida = capsys.readouterr().out
        assert rc == 0
        assert ALFA in saida
        assert "config.toml" in saida


class TestOCampoJanelaGravado:
    def test_com_mira_o_campo_janela_e_o_alvo_e_nao_o_palpite_geometrico(
        self, monkeypatch, tmp_path, geo
    ):
        """D-09 — com os dois clientes SOBREPOSTOS, `janela_que_contem`
        devolveria o cliente de CIMA, e o scanner em producao herdaria o
        cliente errado, gravado calado.
        """
        alvo = tmp_path / "calibration.json"
        rc, _ = _dirigir(
            monkeypatch,
            tmp_path,
            ["--auto"],
            personagem="Alfa",
            janelas=[ALFA, BETA],
            party=_party(geo),
            contem=BETA,
            alvo_calibracao=alvo,
        )

        assert rc == 0
        gravado = json.loads(alvo.read_text(encoding="utf-8"))
        assert gravado["janela"] == ALFA, (
            "O palpite geometrico venceu a mira: o campo `janela` gravado "
            "aponta para o outro cliente."
        )
        assert gravado["nome_proprio"] == "Alfa"

    def test_sem_mira_janela_que_contem_continua_decidindo(
        self, monkeypatch, tmp_path, geo
    ):
        """D-09 — sem alvo declarado, o palpite geometrico e a melhor
        informacao existente e fica INTOCADO."""
        alvo = tmp_path / "calibration.json"
        rc, cenario = _dirigir(
            monkeypatch,
            tmp_path,
            ["--auto"],
            personagem=None,
            janelas=[],
            party=_party(geo),
            contem=BETA,
            alvo_calibracao=alvo,
        )

        assert rc == 0
        assert cenario.capturas_de_desktop == 1
        gravado = json.loads(alvo.read_text(encoding="utf-8"))
        assert gravado["janela"] == BETA
