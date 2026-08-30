"""O que a conferencia PROVA com o jogo fechado, sem rede e sem motor de OCR.

A ferramenta que estes testes cobrem existe por um buraco NOMEADO: o
`--replay` do scanner nao confronta a frase do anuncio, porque
`ReplaySource.capturar` (`l2scanner/frames.py`) monta o `Frame` SEM `extras` —
entao `frame.extras.get("tiat_chat")` e sempre `None` num replay e o vigia
nunca recebe pixel nenhum do chat. Reproduzir uma gravacao nao mede o
reconhecimento; ele so parece medido.

POR QUE O LEITOR DE OCR E INJETADO, E NAO MOCKADO NO MODULO
------------------------------------------------------------
As bindings WinRT do Windows nao estao instaladas no ambiente onde esta suite
roda (sao a causa dos skips do baseline). Um teste que chamasse `l2scanner.ocr`
de verdade ficaria verde numa maquina e amarelo em outra, e a regra desta suite
e rodar com o jogo FECHADO e sem rede.

Entao `main` recebe um `MotorDeOcr` por parametro e os testes entregam um que
devolve texto fixo. O que se prova aqui e a MECANICA DE VEREDITO — o pedaco que
decide — e nao a qualidade do motor, que so pixel real mede e que e justamente
o que o `<human-check>` do plano pede ao usuario.

O CONJUNTO DE ENTRADA E TEXTO, DE PROPOSITO
--------------------------------------------
Os PNGs criados aqui sao retangulos pretos de 120x40. Eles existem so para a
ferramenta ter um arquivo para abrir e um recorte para fazer; o texto vem do
motor injetado. Gravar uma fixture de chat renderizado faria o teste depender
da fonte do jogo, que nao esta no repositorio.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parent.parent


def _carregar_a_ferramenta(nome: str):
    """`tools/` nao e pacote, entao o import vem do caminho do arquivo."""
    caminho = RAIZ / "tools" / (nome + ".py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    assert spec and spec.loader, f"nao carreguei {caminho}"
    modulo = importlib.util.module_from_spec(spec)
    # Registrar ANTES de executar: `@dataclass` resolve as anotacoes por
    # `sys.modules[cls.__module__]`, e sem isto ele encontra None.
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


ferramenta = _carregar_a_ferramenta("conferir_anuncio_de_boss")


# A frase REAL, medida do print do usuario em 2026-08-30. O ROADMAP supunha
# `[Lv. 80]`; o print mostra 60.
ANUNCIO = "Tiat North [Lv. 60] has spawned!"

# A mesma frase como o OCR a degrada, com UMA troca que a tabela de folga NAO
# cobre: o `t` de `North` lido como `l`. `T1at` e `N0r` sao trocas que a folga
# JA aceita, e estao aqui de proposito — a pista tem de apontar o `t`, e nao o
# `1` nem o `0`.
QUASE = "T1at N0rlh [Lv. 60] has spawned!"

CONFIG_COM_DOIS_BOSSES = """
[[boss]]
nome = "Tiat North"
respawn_horas_min = 6
respawn_horas_max = 8

[[boss]]
nome = "Tiat South"
respawn_horas_min = 6
respawn_horas_max = 8
"""


def motor_falso(deteccao, conferencia=None, disponivel=True, motivo=None):
    """Um `MotorDeOcr` que devolve texto fixo, uma string por escala."""
    if conferencia is None:
        conferencia = deteccao
    return ferramenta.MotorDeOcr(
        disponivel=lambda: disponivel,
        motivo=lambda: motivo,
        escalas=(
            ("deteccao", lambda pixels: deteccao),
            ("conferencia", lambda pixels: conferencia),
        ),
    )


def png(caminho: Path) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(caminho), np.zeros((40, 120, 3), dtype=np.uint8))
    return caminho


@pytest.fixture
def cenario(tmp_path):
    """Um PNG, um config.toml com dois bosses, e o recorte da imagem inteira."""
    imagem = png(tmp_path / "print.png")
    config = tmp_path / "config.toml"
    config.write_text(CONFIG_COM_DOIS_BOSSES, encoding="utf-8")
    return imagem, config


def argv(alvo, config, *extras):
    return [
        str(alvo),
        "--config",
        str(config),
        "--recorte",
        "0",
        "0",
        "120",
        "40",
        *extras,
    ]


def vereditos_por_boss(varredura, escala="deteccao"):
    """`{nome: (casou_anuncio, casou_nome)}` da primeira imagem, numa escala."""
    leitura = varredura.imagens[0]
    (da_escala,) = [e for e in leitura.escalas if e.escala == escala]
    return {
        v.boss: (v.casou_anuncio, v.casou_nome) for v in da_escala.vereditos
    }


# ---------------------------------------------------------------------------
# O veredito: a metade que decide
# ---------------------------------------------------------------------------


class TestOVeredito:
    def test_o_anuncio_casa_o_boss_da_frase_e_nao_o_outro(self, cenario):
        imagem, config = cenario
        codigo = ferramenta.main(
            argv(imagem, config), motor=motor_falso(ANUNCIO)
        )
        assert codigo == 0
        varredura = ferramenta.ULTIMA_VARREDURA
        assert vereditos_por_boss(varredura) == {
            "Tiat North": (True, True),
            "Tiat South": (False, False),
        }

    def test_so_o_nome_casa_o_alvo_e_nunca_o_anuncio(self, cenario):
        """O recorte do ALVO nao tem frase nenhuma — so o nome do mob."""
        imagem, config = cenario
        codigo = ferramenta.main(
            argv(imagem, config), motor=motor_falso("Tiat South")
        )
        assert codigo == 0
        assert vereditos_por_boss(ferramenta.ULTIMA_VARREDURA) == {
            "Tiat North": (False, False),
            "Tiat South": (False, True),
        }

    def test_texto_sem_boss_nenhum_nao_casa_e_a_varredura_completou(
        self, cenario
    ):
        """Ausencia de casamento e RESULTADO, e por isso o codigo e 0."""
        imagem, config = cenario
        codigo = ferramenta.main(
            argv(imagem, config),
            motor=motor_falso("SaBaoCruCru : VAGA DD AOE FILD PRA XP !!"),
        )
        assert codigo == 0
        assert ferramenta.ULTIMA_VARREDURA.casamentos_de_anuncio == 0
        assert ferramenta.ULTIMA_VARREDURA.casamentos_de_nome == 0

    def test_a_frase_e_conferida_linha_a_linha_e_nunca_no_blob(self, cenario):
        """A MESMA convencao de `VigiaDeBosses.avaliar` (T-01-02).

        Sobre o blob, o `\\s+` da parte fixa costuraria o fim da linha de um
        jogador com o comeco da linha de outro e produziria um casamento que
        nenhuma linha real contem. Duas linhas de jogadores diferentes, cada
        uma com metade da frase, tem de dar NAO.
        """
        imagem, config = cenario
        costura = "Fulano : Tiat North\nCicrano : [Lv. 60] has spawned!"
        ferramenta.main(argv(imagem, config), motor=motor_falso(costura))
        assert (
            vereditos_por_boss(ferramenta.ULTIMA_VARREDURA)["Tiat North"][0]
            is False
        )


# ---------------------------------------------------------------------------
# O texto CRU: a metade que informa
# ---------------------------------------------------------------------------


class TestOTextoCru:
    def test_as_duas_escalas_aparecem_na_saida_com_o_texto_de_cada_uma(
        self, cenario, capsys
    ):
        """A divergencia entre as escalas E informacao, e por isso as duas saem.

        Se a de conferencia le e a de deteccao nao, a correcao nao e afrouxar o
        padrao: e o scanner ler o recorte do chat na escala maior.
        """
        imagem, config = cenario
        ferramenta.main(
            argv(imagem, config),
            motor=motor_falso("lixo ilegivel", conferencia=ANUNCIO),
        )
        saida = capsys.readouterr().out
        assert "deteccao" in saida
        assert "conferencia" in saida
        assert "lixo ilegivel" in saida
        assert "has spawned" in saida

    def test_caractere_invisivel_aparece_na_saida(self, cenario, capsys):
        """Um espaco a mais e exatamente o que derruba um casamento.

        O texto sai como REPRESENTACAO e nunca solto: solto, o espaco final e o
        caractere de controle ficam invisiveis justamente no relatorio que
        existe para mostra-los.
        """
        imagem, config = cenario
        ferramenta.main(
            argv(imagem, config), motor=motor_falso("Tiat North \t")
        )
        saida = capsys.readouterr().out
        assert repr("Tiat North \t") in saida

    def test_o_texto_cru_sai_ANTES_do_veredito(self, cenario, capsys):
        """Mesmo quando tudo da NAO, colar a saida continua sendo informacao.

        A comparacao comeca no bloco da LEITURA e nao no topo da saida: o
        cabecalho ja nomeia os bosses lidos do config e ja cita o arquivo, e
        medir a partir do topo estaria medindo o cabecalho.
        """
        imagem, config = cenario
        ferramenta.main(argv(imagem, config), motor=motor_falso("nada aqui"))
        saida = capsys.readouterr().out
        bloco = saida[saida.index("[deteccao] texto cru") :]
        assert bloco.index("nada aqui") < bloco.index("veredito:")
        assert bloco.index("nada aqui") < bloco.index("Tiat North")


# ---------------------------------------------------------------------------
# A pista: o que transforma um NAO numa acao
# ---------------------------------------------------------------------------


class TestAPistaDeDivergencia:
    def test_a_pista_aponta_o_caractere_que_o_ocr_perdeu(self, cenario, capsys):
        imagem, config = cenario
        ferramenta.main(argv(imagem, config), motor=motor_falso(QUASE))
        saida = capsys.readouterr().out
        assert (
            vereditos_por_boss(ferramenta.ULTIMA_VARREDURA)["Tiat North"][0]
            is False
        )
        assert "PISTA" in saida
        # O caractere MEDIDO, e nao "algo perto": esperado `t`, lido `l`.
        assert repr("t") in saida
        assert repr("l") in saida

    def test_a_pista_nao_acusa_troca_que_a_folga_JA_aceita(
        self, cenario, capsys
    ):
        """`T1a7 Nor7h` casa; sem casamento nao ha pista, e nem deveria haver.

        Apontar o `1` ou o `7` mandaria alguem afrouxar uma tolerancia que ja
        existe — que e o comeco do caminho que devolve o padrao ao curinga.
        """
        imagem, config = cenario
        ferramenta.main(
            argv(imagem, config),
            motor=motor_falso("T1a7 Nor7h [Lv. 8O] has spawned!"),
        )
        saida = capsys.readouterr().out
        assert (
            vereditos_por_boss(ferramenta.ULTIMA_VARREDURA)["Tiat North"][0]
            is True
        )
        assert "PISTA" not in saida

    def test_sem_nada_parecido_nao_ha_pista(self, cenario, capsys):
        imagem, config = cenario
        ferramenta.main(
            argv(imagem, config),
            motor=motor_falso("Laurinhaa : alguma pt com vaga plains DD AEO"),
        )
        assert "PISTA" not in capsys.readouterr().out

    @pytest.mark.parametrize(
        "linha",
        [
            # Os trechos que MAIS dispararam PISTA na varredura de 2.110 frames
            # de chat real, todos em 0,60 exatos. Nenhum parece `Tiat North`.
            "Wait for the animation for Transformation to finish",
            "You cannot attack that target. The target is invalid",
            "MST : Team: Normal mode party recruiting",
            "Fulano : ele tei mato tudo sozinho",
        ],
    )
    def test_o_ruido_de_chat_real_medido_nao_produz_pista(
        self, cenario, capsys, linha
    ):
        """O corte de 0,6 foi REFUTADO em campo, e este teste prende o novo.

        Em 0,6 a varredura de 2.110 frames cuspiu 320 linhas PISTA com ZERO
        near-miss de verdade no meio. Uma pista que dispara 320 vezes enterra a
        unica que importa no dia em que o usuario colar o print do spawn.
        """
        imagem, config = cenario
        ferramenta.main(argv(imagem, config), motor=motor_falso(linha))
        assert "PISTA" not in capsys.readouterr().out

    @pytest.mark.parametrize(
        "trecho,perdido",
        [
            ("T1at N0rlh", ("t", "l")),  # 0,700 — o pior do lote medido
            ("Tiat Nortb", ("h", "b")),  # 0,900
            ("Tiat Nonth", ("r", "n")),  # 0,900
        ],
    )
    def test_o_near_miss_de_verdade_continua_produzindo_pista(
        self, cenario, capsys, trecho, perdido
    ):
        """O outro lado do corte: subir o piso nao pode calar o caso util.

        `T1at N0rlh` esta em 0,700 e e o pior near-miss medido — se ele parar
        de dar pista, o piso subiu demais e o relatorio perdeu a razao de
        existir.
        """
        imagem, config = cenario
        esperado, lido = perdido
        ferramenta.main(
            argv(imagem, config),
            motor=motor_falso(f"{trecho} [Lv. 60] has spawned!"),
        )
        saida = capsys.readouterr().out
        assert "PISTA" in saida
        assert repr(esperado) in saida
        assert repr(lido) in saida


# ---------------------------------------------------------------------------
# As recusas: quando a ferramenta NAO CONSEGUIU medir
# ---------------------------------------------------------------------------


class TestQuandoNaoDaParaMedir:
    def test_ocr_indisponivel_devolve_1_e_imprime_o_motivo(
        self, cenario, capsys
    ):
        """Zero casamentos SILENCIOSO levaria a afrouxar um padrao certo.

        E a mitigacao de T-04-02: o motor ausente nao pode ser confundido com
        "nenhum boss apareceu".
        """
        imagem, config = cenario
        codigo = ferramenta.main(
            argv(imagem, config),
            motor=motor_falso(
                ANUNCIO,
                disponivel=False,
                motivo="As bibliotecas de OCR do Windows nao estao instaladas",
            ),
        )
        assert codigo == 1
        saida = capsys.readouterr().out
        assert "As bibliotecas de OCR do Windows nao estao instaladas" in saida
        assert "casamento" not in saida.lower()

    def test_pasta_sem_imagem_nenhuma_devolve_1(self, tmp_path, capsys):
        config = tmp_path / "config.toml"
        config.write_text(CONFIG_COM_DOIS_BOSSES, encoding="utf-8")
        vazia = tmp_path / "vazia"
        vazia.mkdir()
        codigo = ferramenta.main(
            argv(vazia, config), motor=motor_falso(ANUNCIO)
        )
        assert codigo == 1
        assert "nenhuma imagem" in capsys.readouterr().out.lower()

    def test_sem_calibracao_e_sem_recorte_devolve_1_dizendo_onde_olhar(
        self, cenario, capsys
    ):
        """Nao saber onde olhar nao pode virar uma varredura de zero."""
        imagem, config = cenario
        codigo = ferramenta.main(
            [
                str(imagem),
                "--config",
                str(config),
                "--calibracao",
                str(imagem.parent / "nao-existe.json"),
            ],
            motor=motor_falso(ANUNCIO),
        )
        assert codigo == 1
        saida = capsys.readouterr().out.lower()
        assert "--recorte" in saida

    def test_recorte_que_nao_cabe_em_imagem_NENHUMA_devolve_1(
        self, cenario, capsys
    ):
        """Zero leituras nao pode virar zero casamentos (T-04-02)."""
        imagem, config = cenario
        codigo = ferramenta.main(
            [
                str(imagem),
                "--config",
                str(config),
                "--recorte",
                "0",
                "0",
                "9000",
                "9000",
            ],
            motor=motor_falso(ANUNCIO),
        )
        saida = capsys.readouterr().out
        assert codigo == 1
        assert "nao medi nada" in saida.lower()

    def test_uma_imagem_que_nao_cabe_e_PULADA_e_nao_derruba_a_varredura(
        self, tmp_path, capsys
    ):
        """MEDIDO contra o `recordings/` real: ele mistura frame de janela
        inteira (1720x1392) com recorte de party window (172x522) de outro
        recurso. Abortar no primeiro recorte que nao coubesse jogaria fora dois
        mil frames bons por causa de um arquivo que nem era chat.
        """
        config = tmp_path / "config.toml"
        config.write_text(CONFIG_COM_DOIS_BOSSES, encoding="utf-8")
        pasta = tmp_path / "misturada"
        png(pasta / "frame_000000.png")  # 120x40, cabe
        cv2.imwrite(
            str(pasta / "frame_000001.png"),
            np.zeros((10, 10, 3), dtype=np.uint8),  # nao cabe
        )
        png(pasta / "frame_000002.png")

        codigo = ferramenta.main(
            argv(pasta, config), motor=motor_falso(ANUNCIO)
        )
        saida = capsys.readouterr().out
        assert codigo == 0
        assert "frame_000001.png" in saida
        assert "PULADA" in saida
        # As duas que cabem foram medidas; a que nao cabe nao virou leitura.
        assert len(ferramenta.ULTIMA_VARREDURA.imagens) == 2


# ---------------------------------------------------------------------------
# A pasta de gravacao
# ---------------------------------------------------------------------------


class TestAPastaDeGravacao:
    def test_uma_linha_por_frame_e_um_resumo_ao_final(self, tmp_path, capsys):
        config = tmp_path / "config.toml"
        config.write_text(CONFIG_COM_DOIS_BOSSES, encoding="utf-8")
        pasta = tmp_path / "20260830-000000-spawn"
        for i in range(3):
            png(pasta / f"frame_{i:06d}.png")

        codigo = ferramenta.main(
            argv(pasta, config), motor=motor_falso(ANUNCIO)
        )
        assert codigo == 0
        saida = capsys.readouterr().out
        for i in range(3):
            assert f"frame_{i:06d}.png" in saida
        assert "RESUMO" in saida
        varredura = ferramenta.ULTIMA_VARREDURA
        assert len(varredura.imagens) == 3
        # Duas escalas por frame, e as duas leram a frase.
        assert varredura.casamentos_de_anuncio == 6

    def test_uma_pasta_DE_gravacoes_e_varrida_um_nivel_abaixo(self, tmp_path):
        """`recordings/` e uma pasta de PASTAS, e o plano aponta a ferramenta
        para ela. Parar no nivel zero devolveria "nenhuma imagem" com dois mil
        frames em disco.
        """
        config = tmp_path / "config.toml"
        config.write_text(CONFIG_COM_DOIS_BOSSES, encoding="utf-8")
        raiz = tmp_path / "recordings"
        png(raiz / "sessao-a" / "frame_000000.png")
        png(raiz / "sessao-b" / "frame_000000.png")

        codigo = ferramenta.main(argv(raiz, config), motor=motor_falso("nada"))
        assert codigo == 0
        assert len(ferramenta.ULTIMA_VARREDURA.imagens) == 2

    def test_os_frames_das_subpastas_ganham_dos_PNGs_avulsos_da_raiz(
        self, tmp_path
    ):
        """MEDIDO contra o `recordings/` real: 12 PNGs avulsos na raiz e 2.110
        frames nas subpastas. Com `*.png` da raiz ganhando, apontar a
        ferramenta para `recordings` mediria os 12 avulsos e nunca desceria —
        uma varredura que parece completa e cobre 0,5% do material.
        """
        config = tmp_path / "config.toml"
        config.write_text(CONFIG_COM_DOIS_BOSSES, encoding="utf-8")
        raiz = tmp_path / "recordings"
        png(raiz / "agora_janela.png")
        png(raiz / "base_party.png")
        png(raiz / "sessao-a" / "frame_000000.png")
        png(raiz / "sessao-a" / "frame_000001.png")
        png(raiz / "sessao-b" / "frame_000000.png")

        codigo = ferramenta.main(argv(raiz, config), motor=motor_falso("nada"))
        assert codigo == 0
        lidos = [i.arquivo.name for i in ferramenta.ULTIMA_VARREDURA.imagens]
        assert len(lidos) == 3
        assert "agora_janela.png" not in lidos


# ---------------------------------------------------------------------------
# O tripwire de T-04-03
# ---------------------------------------------------------------------------


def test_a_ferramenta_nao_escreve_expressao_regular_propria():
    """Os dois padroes vem de `l2scanner.bosses`, e isso e uma MITIGACAO.

    T-04-03: o `nome` do `[[boss]]` e texto escrito a mao que vira fonte de
    regex. `padrao_do_anuncio` monta com `re.escape` caractere a caractere; uma
    regex local repetiria a construcao sem a garantia e faria a ferramenta
    MEDIR com uma convencao e o scanner DECIDIR com outra.

    A prova e sobre a ARVORE e nao sobre o texto do arquivo. Um `assert
    "re.compile" not in fonte` acusaria a propria docstring que EXPLICA a
    mitigacao — e o conserto seria apagar a explicacao, que e o ativo. Pela
    arvore, `import re` e `from re import ...` sao impossiveis sob qualquer
    apelido, inclusive `import re as _r`, que um scan de substring deixaria
    passar.
    """
    fonte = (RAIZ / "tools" / "conferir_anuncio_de_boss.py").read_text(
        encoding="utf-8"
    )
    importados = set()
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Import):
            importados.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom):
            importados.add(no.module or "")
    assert "re" not in importados, f"a ferramenta importou re: {importados}"
    assert getattr(ferramenta, "re", None) is None

    assert "padrao_do_anuncio" in fonte
    assert "padrao_do_nome" in fonte
