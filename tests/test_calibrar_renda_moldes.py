"""O cortador dos moldes da fonte da BARRA, preso sem janela e sem disco real.

Tudo aqui roda sobre mascaras SINTETICAS montadas a mao com as larguras que a
medicao de campo produziu, na convencao EXCLUSIVA de `larguras_de_molde` (M-P).
Nada aqui abre janela do OpenCV, le OCR, ou toca `recordings/` — a pasta e
gitignored e nao vem de clone limpo, entao um teste que dependesse dela ficaria
verde nesta maquina e amarelo em toda outra
(`tests/test_mercado_glifos.py:4-8`).

O QUE ESTA SUITE **NAO** PROVA, E ESTA E A FRASE MAIS IMPORTANTE DO ARQUIVO
==========================================================================
Ela fica verde **sem que `tests/fixtures/renda/moldes_da_barra.json` exista**.
Ela prende a FERRAMENTA; quem fecha o LEIT-09 e a RODADA — um humano olhando
cada recorte ampliado e confirmando o rotulo. Por isso a rodada e um
`checkpoint:human-action` e nao uma tarefa `auto`: um portao cuja unica prova
nao toca o artefato que ele existe para produzir e um portao que passa por
engano, e o desfecho seria a adena RECUSADA com a suite toda verde.

Um rotulo confirmado errado nao produz meia leitura: produz a leitura errada
com a confianca da certa. Esta medido na docstring de
`conjunto_descreve_numeros` — um `8` sem molde de `8` casa com `0` a 0,7826
contra piso 0,4698, e a folga de 0,1628 sobre o segundo colocado significa que
nem a margem pega.
"""

from __future__ import annotations

import ast
import json
import pathlib

import numpy as np
import pytest

import l2scanner.calibrar_renda_moldes as cortador
from l2scanner.calibracao import Calibracao
from l2scanner.mercado_leitura import conjunto_descreve_numeros
from l2scanner.mercado_visao import glifos_de_calibracao

PISO_SINTETICO = 128
ALTURA_DA_IMAGEM = 30
TOPO_DO_DIGITO, BASE_DO_DIGITO = 12, 22  # altura 10 — a fonte da barra (M-K)
TOPO_DA_VIRGULA = 20
TOPO_DO_ICONE = 5


# ---------------------------------------------------------------------------
# As oficinas: recortes sinteticos com a geometria medida
# ---------------------------------------------------------------------------


def imagem_de_blocos(blocos, altura=ALTURA_DA_IMAGEM) -> np.ndarray:
    largura = sum(b[0] for b in blocos) + (len(blocos) - 1) + 2
    imagem = np.zeros((altura, largura, 3), dtype=np.uint8)
    x = 1
    for largura_do_bloco, topo, base in blocos:
        imagem[topo:base, x : x + largura_do_bloco] = 255
        x += largura_do_bloco + 1
    return imagem


def icone(largura=14):
    return (largura, TOPO_DO_ICONE, BASE_DO_DIGITO)


def digito(largura=4, *, topo=TOPO_DO_DIGITO):
    return (largura, topo, BASE_DO_DIGITO)


def virgula():
    return (1, TOPO_DA_VIRGULA, BASE_DO_DIGITO)


def campo_com_n_glifos(quantos: int, *, topo=TOPO_DO_DIGITO) -> np.ndarray:
    """Um recorte no formato da adena: icone, `quantos` glifos, icone."""
    blocos = [icone(14)] + [digito(topo=topo) for _ in range(quantos)] + [icone(15)]
    return imagem_de_blocos(blocos)


def recorte(pixels, *, frame="frame_000000.png", campo="adena", piso=PISO_SINTETICO):
    return cortador.RecorteDaBarra(
        frame=frame, campo=campo, pixels=pixels, piso_de_brilho=piso
    )


def leitor(respostas):
    """Um `input` de mentira: devolve as respostas em ordem."""
    fila = list(respostas)

    def ler(_pergunta=""):
        return fila.pop(0) if fila else "f"

    return ler


def moldes_de_altura(altura: int, rotulos: str) -> dict[str, np.ndarray]:
    return {
        rotulo: np.full((altura, 4), 255, dtype=np.uint8) for rotulo in rotulos
    }


# ---------------------------------------------------------------------------
# A GUARDA DE ALTURA, NOS DOIS SENTIDOS
# ---------------------------------------------------------------------------


def test_a_guarda_de_altura_PULA_o_recorte_de_geometria_errada():
    """M-I virado teste, com o numero do M-K.

    Os 13 moldes de `mercado_templates_de_digito` sao 4x9; a fonte da barra e
    5x10 na convencao inclusiva do documento e 4x9-ish contra 10 de altura
    aqui. Um recorte cuja faixa peneirada tem altura 9 num conjunto de altura
    10 foi cortado de outro lugar.
    """
    problema = cortador.conferir_a_altura((0, 9), moldes_de_altura(10, "013"))

    assert problema is not None
    assert "9" in problema and "10" in problema


def test_a_guarda_de_altura_ACEITA_a_geometria_certa():
    """O controle obrigatorio. Sem ele, um cortador que RECUSA TUDO passaria
    verde — e esse e exatamente o desfecho que uma guarda escrita contra a
    altura contaminada do M-I teria produzido: uma ferramenta que roda, sai com
    codigo 0 e nunca corta nada."""
    assert cortador.conferir_a_altura((0, 10), moldes_de_altura(10, "013")) is None


def test_sem_molde_gravado_nao_ha_altura_com_que_comparar():
    """Na primeira rodada o conjunto e vazio: a guarda nao tem contra o que
    comparar e nao pode inventar uma altura."""
    assert cortador.conferir_a_altura((0, 10), {}) is None


def test_a_altura_comparada_e_a_PENEIRADA_e_nao_a_faixa_bruta():
    """A ordem e o achado inteiro: foi o icone DENTRO do recorte que produziu a
    altura contaminada do M-I sobre uma fonte de altura 10. Medir antes do
    descarte e reproduzir o defeito por dentro da ferramenta que existe para
    nao reproduzi-lo."""
    pixels = campo_com_n_glifos(4)
    saida = cortador.glifos_do_recorte(
        pixels, piso_de_brilho=PISO_SINTETICO, moldes=moldes_de_altura(10, "0134")
    )

    assert not isinstance(saida, cortador.RecusaDeForma)
    _mascara, glifos = saida
    assert glifos.faixa[1] - glifos.faixa[0] == 10
    assert cortador.conferir_a_altura(glifos.faixa, moldes_de_altura(10, "0")) is None


def test_um_recorte_de_altura_errada_e_pulado_COM_O_FRAME_NOMEADO():
    pixels = campo_com_n_glifos(3, topo=TOPO_DO_DIGITO + 1)  # altura 9
    rodada = cortador.propor_e_confirmar(
        [recorte(pixels, frame="frame_000007.png")],
        moldes_de_altura(10, "0123456789,"),
        ler=leitor(["f"]),
    )

    assert rodada.cortados == {}
    assert len(rodada.pulos) == 1
    assert rodada.pulos[0].frame == "frame_000007.png"
    assert "9" in rodada.pulos[0].detalhe and "10" in rodada.pulos[0].detalhe


# ---------------------------------------------------------------------------
# O RUN DE 141 PX
# ---------------------------------------------------------------------------


def test_o_run_de_141_px_e_PULADO_com_a_largura_e_a_causa_nomeadas():
    """M-L: a barra verde de progresso entra na mascara e cola o campo inteiro.
    141 px em glifos desta fonte dariam vinte e oito digitos que nunca
    estiveram na tela."""
    pixels = imagem_de_blocos([(141, TOPO_DO_DIGITO, BASE_DO_DIGITO)])
    rodada = cortador.propor_e_confirmar(
        [recorte(pixels, frame="frame_exp.png", campo="exp")],
        moldes_de_altura(10, "0123456789,"),
        ler=leitor(["f"]),
    )

    assert rodada.cortados == {}
    assert len(rodada.pulos) == 1
    pulo = rodada.pulos[0]
    assert pulo.motivo == cortador.MOTIVO_DO_RUN_ANORMAL
    assert "141" in pulo.detalhe
    assert "VERDE" in pulo.detalhe or "verde" in pulo.detalhe
    assert "M-L" in pulo.detalhe


def test_a_sugestao_do_recorte_apertado_viaja_com_a_recusa_do_run_colado():
    pixels = imagem_de_blocos([(141, TOPO_DO_DIGITO, BASE_DO_DIGITO)])
    rodada = cortador.propor_e_confirmar(
        [recorte(pixels, campo="exp")],
        moldes_de_altura(10, "0123456789,"),
        ler=leitor(["f"]),
    )
    conserto = cortador.conserto_do_run_colado()
    assert "1366:1386" in conserto
    assert rodada.pulos[0].motivo == cortador.MOTIVO_DO_RUN_ANORMAL


# ---------------------------------------------------------------------------
# A PENEIRA E IMPORTADA, E NAO COPIADA
# ---------------------------------------------------------------------------


def test_o_cortador_NAO_define_uma_segunda_peneira():
    fonte = pathlib.Path(cortador.__file__).read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    definidas = [
        no.name
        for no in ast.walk(arvore)
        if isinstance(no, ast.FunctionDef) and no.name == "_glifos_do_numero"
    ]
    assert definidas == []
    assert "_glifos_do_numero" in fonte


def test_a_peneira_do_cortador_E_a_do_modulo_puro():
    from l2scanner.renda_leitura import _glifos_do_numero

    assert cortador._glifos_do_numero is _glifos_do_numero


def test_o_numero_da_altura_contaminada_so_aparece_como_REFUTACAO():
    """Criterio do plano: onde `17` aparecer no fonte do cortador, ele aparece
    como refutacao com o M-K citado — nunca como altura de glifo desta barra."""
    fonte = pathlib.Path(cortador.__file__).read_text(encoding="utf-8")
    suspeitas = [
        linha
        for linha in fonte.splitlines()
        if "17" in linha and "M-K" not in linha and "refutad" not in linha
    ]
    assert suspeitas == []


def test_a_chave_do_mercado_nao_e_nomeada_no_fonte():
    fonte = pathlib.Path(cortador.__file__).read_text(encoding="utf-8")
    assert "mercado_templates_de_digito" not in fonte


# ---------------------------------------------------------------------------
# A COLHEITA E DE QUALQUER CAMPO DA BARRA
# ---------------------------------------------------------------------------


def test_os_quatro_campos_da_barra_sao_aceitos():
    assert set(cortador.CAMPOS_DA_BARRA) == {"adena", "lcoin", "bonus", "exp"}


@pytest.mark.parametrize("campo", ["adena", "lcoin", "bonus", "exp"])
def test_a_ferramenta_propoe_em_QUALQUER_campo(campo):
    """A colheita nao e restrita a adena: o `5` e o `7` estao noutros campos da
    MESMA barra (M-L), e o bloqueio "esperar o farm" caiu com o `--campo`."""
    pixels = campo_com_n_glifos(3)
    rodada = cortador.propor_e_confirmar(
        [recorte(pixels, campo=campo)],
        {},
        ler=leitor(["123", "f"]),
    )
    assert set(rodada.cortados) == {"1", "2", "3"}
    assert rodada.pulos == []


def test_onde_procurar_nomeia_o_CAMPO_e_nao_manda_esperar_o_farm():
    """O conserto MUDOU com o M-L: ele deixou de ser "farmar ate o digito
    aparecer" e passou a ser "varrer outro campo da barra"."""
    dicas = " ".join(cortador.onde_procurar(["5", "7"]))
    assert "5" in dicas and "7" in dicas
    assert "bonus" in dicas or "lcoin" in dicas
    assert "farm" not in dicas.lower()


# ---------------------------------------------------------------------------
# A MAQUINA PROPOE, O HUMANO CONFIRMA -- E NADA GRAVA SEM CONFIRMACAO
# ---------------------------------------------------------------------------


def test_a_primeira_rodada_NAO_propoe_e_diz_isso():
    """Sem molde nenhum gravado nao ha proposta: o humano digita o numero
    inteiro, e e assim que o primeiro molde nasce certo."""
    pixels = campo_com_n_glifos(3)
    rodada = cortador.propor_e_confirmar(
        [recorte(pixels)], {}, ler=leitor(["123", "f"])
    )

    assert rodada.propostas == [None]
    assert set(rodada.cortados) == {"1", "2", "3"}


def test_o_que_o_humano_digita_SEMPRE_vence():
    pixels = campo_com_n_glifos(2)
    rodada = cortador.propor_e_confirmar(
        [recorte(pixels)], {}, ler=leitor(["47", "f"])
    )
    assert set(rodada.cortados) == {"4", "7"}


def test_um_rotulo_com_contagem_errada_NAO_grava():
    """A conferencia de contagem transforma um recorte que cortou meio digito
    em recusa imediata, em vez de num molde errado gravado com a confianca de
    um certo."""
    pixels = campo_com_n_glifos(3)
    rodada = cortador.propor_e_confirmar(
        [recorte(pixels)], {}, ler=leitor(["12", "f"])
    )
    assert rodada.cortados == {}


def test_uma_rodada_so_propor_nao_pede_nada_e_nao_corta_nada():
    pixels = campo_com_n_glifos(3)
    rodada = cortador.propor_e_confirmar(
        [recorte(pixels)],
        moldes_de_altura(10, "0123456789,"),
        ler=None,
        so_propor=True,
    )
    assert rodada.cortados == {}
    assert len(rodada.propostas) == 1


# ---------------------------------------------------------------------------
# O CONJUNTO INCOMPLETO: GRAVADO E ANUNCIADO, NUNCA COMPLETADO
# ---------------------------------------------------------------------------


def test_a_cobertura_da_barra_sao_os_ONZE_e_nao_os_treze_do_mercado():
    """`Adena` e `XM Coin` sao palavras de sufixo da GRADE do mercado. Elas nao
    existem nesta fonte, e conta-las como faltantes mandaria o usuario procurar
    para sempre por algo que nao esta na barra."""
    existem, faltam = cortador.cobertura_da_barra(set("0123456789,"))
    assert len(existem) == 11
    assert faltam == []
    assert "Adena" not in existem and "XM Coin" not in existem


def test_o_conjunto_INCOMPLETO_e_gravado_e_os_faltantes_saem_POR_NOME(
    tmp_path, monkeypatch
):
    caminho = tmp_path / "calibration.json"
    _semear(caminho)
    monkeypatch.setattr(cortador, "ARQUIVO_CALIBRACAO", caminho)

    oito = moldes_de_altura(10, "01234689")
    gravados = cortador.gravar_os_moldes(
        oito, piso_de_leitura=0.47, margem_de_leitura=0.037
    )

    # A GRAVACAO ACONTECEU -- travar ate os onze fecharem jogaria fora moldes
    # ja conferidos por um humano por causa de uma rodada interrompida.
    assert len(gravados["moldes"]) == 8
    depois = json.loads(caminho.read_text(encoding="utf-8"))
    assert len(depois["renda_moldes_da_barra"]["moldes"]) == 8

    # E `conjunto_descreve_numeros` sobre ele devolve False -- isso NAO e um
    # erro: e o LEIT-09 funcionando.
    reconstituidos = glifos_de_calibracao(depois["renda_moldes_da_barra"]["moldes"])
    assert conjunto_descreve_numeros(reconstituidos) is False

    saida = "\n".join(cortador.anunciar_a_cobertura(oito))
    assert "5" in saida and "7" in saida and "," in saida
    assert "RECUSAR" in saida or "recusar" in saida


def test_nenhum_molde_alem_dos_confirmados_e_gravado(tmp_path, monkeypatch):
    """O controle negativo da proibicao: a ferramenta nunca inventa molde vazio
    para completar o conjunto, e nunca copia molde de outra fonte."""
    caminho = tmp_path / "calibration.json"
    _semear(caminho)
    monkeypatch.setattr(cortador, "ARQUIVO_CALIBRACAO", caminho)

    oito = moldes_de_altura(10, "01234689")
    cortador.gravar_os_moldes(oito, piso_de_leitura=0.47, margem_de_leitura=0.037)

    depois = json.loads(caminho.read_text(encoding="utf-8"))
    rotulos = {m["glifo"] for m in depois["renda_moldes_da_barra"]["moldes"]}
    assert rotulos == set("01234689")


# ---------------------------------------------------------------------------
# UMA CHAVE DE TOPO MUDA. TODAS AS OUTRAS FICAM IDENTICAS.
# ---------------------------------------------------------------------------


def _semear(caminho: pathlib.Path) -> dict:
    """Um `calibration.json` valido, com a chave do mercado POVOADA."""
    referencia = json.loads(
        pathlib.Path("tests/fixtures/renda/calibracao_de_fixture.json").read_text(
            encoding="utf-8"
        )
    )
    referencia["mercado_templates_de_digito"] = [
        {
            "glifo": rotulo,
            "altura": 9,
            "largura": 4,
            "molde": {
                "altura": 9,
                "largura": 4,
                "bytes": (np.full((9, 4), 255, np.uint8).tobytes().hex()),
            },
        }
        for rotulo in "0123456789,"
    ] + [
        {
            "glifo": palavra,
            "altura": 9,
            "largura": 35,
            "molde": {
                "altura": 9,
                "largura": 35,
                "bytes": (np.full((9, 35), 255, np.uint8).tobytes().hex()),
            },
        }
        for palavra in ("Adena", "XM Coin")
    ]
    caminho.write_text(json.dumps(referencia, indent=1), encoding="utf-8")
    return referencia


def test_a_chave_do_mercado_volta_IDENTICA_depois_da_rodada(tmp_path, monkeypatch):
    caminho = tmp_path / "calibration.json"
    antes = _semear(caminho)
    assert len(antes["mercado_templates_de_digito"]) == 13  # contados ANTES
    monkeypatch.setattr(cortador, "ARQUIVO_CALIBRACAO", caminho)

    cortador.gravar_os_moldes(
        moldes_de_altura(10, "0123456789,"),
        piso_de_leitura=0.47,
        margem_de_leitura=0.037,
    )

    depois = json.loads(caminho.read_text(encoding="utf-8"))
    assert depois["mercado_templates_de_digito"] == antes["mercado_templates_de_digito"]
    assert len(depois["mercado_templates_de_digito"]) == 13


def test_toda_outra_chave_de_topo_volta_IDENTICA(tmp_path, monkeypatch):
    caminho = tmp_path / "calibration.json"
    antes = _semear(caminho)
    monkeypatch.setattr(cortador, "ARQUIVO_CALIBRACAO", caminho)

    cortador.gravar_os_moldes(
        moldes_de_altura(10, "0123456789,"),
        piso_de_leitura=0.47,
        margem_de_leitura=0.037,
    )

    depois = json.loads(caminho.read_text(encoding="utf-8"))
    mudadas = [c for c in set(antes) | set(depois) if antes.get(c) != depois.get(c)]
    assert mudadas == ["renda_moldes_da_barra"]

    # O CONTROLE POSITIVO: a rodada escreveu ALGUMA COISA. Sem ele, uma
    # ferramenta que nao gravasse nada passaria neste teste com folga.
    assert depois["renda_moldes_da_barra"]["moldes"]
    assert antes.get("renda_moldes_da_barra") is None


def test_o_conjunto_gravado_volta_por_glifos_de_calibracao(tmp_path, monkeypatch):
    caminho = tmp_path / "calibration.json"
    _semear(caminho)
    monkeypatch.setattr(cortador, "ARQUIVO_CALIBRACAO", caminho)

    cortador.gravar_os_moldes(
        moldes_de_altura(10, "0123456789,"),
        piso_de_leitura=0.47,
        margem_de_leitura=0.037,
    )

    depois = json.loads(caminho.read_text(encoding="utf-8"))
    reconstituidos = glifos_de_calibracao(depois["renda_moldes_da_barra"]["moldes"])
    assert conjunto_descreve_numeros(reconstituidos) is True
    assert {m.shape[0] for m in reconstituidos.values()} == {10}

    # E o arquivo continua carregando pelo arranque, que confere FORMA.
    Calibracao.carregar(caminho)


# ---------------------------------------------------------------------------
# `--propor` NAO ESCREVE
# ---------------------------------------------------------------------------


def test_propor_nao_escreve_no_disco(tmp_path, monkeypatch):
    caminho = tmp_path / "calibration.json"
    _semear(caminho)
    conteudo_antes = json.loads(caminho.read_text(encoding="utf-8"))
    monkeypatch.setattr(cortador, "ARQUIVO_CALIBRACAO", caminho)

    pasta = tmp_path / "gravacao"
    pasta.mkdir()
    import cv2

    cv2.imwrite(str(pasta / "frame_000000.png"), campo_com_n_glifos(3))

    codigo = cortador.main(
        [
            "--gravacoes",
            str(pasta),
            "--campo",
            "adena",
            "--recorte",
            "inteiro",
            "--piso",
            str(PISO_SINTETICO),
            "--propor",
        ]
    )

    assert codigo == 0
    assert json.loads(caminho.read_text(encoding="utf-8")) == conteudo_antes


# ---------------------------------------------------------------------------
# A MATRIZ DE CONFUSAO ANTES DE GRAVAR
# ---------------------------------------------------------------------------


def test_rotulos_inseparaveis_NAO_gravam_e_o_par_sai_nomeado():
    """Precedente literal de `_conferir_os_glifos`: "nada foi gravado: os
    glifos precisam ser separaveis primeiro" — a mensagem diz ao usuario que o
    estado anterior esta intacto."""
    identicos = {
        "0": np.full((10, 4), 255, np.uint8),
        "8": np.full((10, 4), 255, np.uint8),
    }
    with pytest.raises(cortador.RendaNaoCalibravel) as erro:
        cortador.conferir_os_moldes(identicos)
    mensagem = str(erro.value)
    assert "nada foi gravado" in mensagem
    assert "0" in mensagem and "8" in mensagem


# ---------------------------------------------------------------------------
# A FIXTURA DE MOLDES NAO NASCE AQUI
# ---------------------------------------------------------------------------


def test_a_fixtura_de_moldes_NAO_e_produzida_por_codigo():
    """Criterio, e nao pendencia. A fixtura so pode nascer de uma rodada em que
    um humano confirmou cada rotulo olhando o recorte ampliado — a Tarefa 3.
    Uma fixtura que aparecesse por codigo de teste seria a falha aberta do
    LEIT-09 entrando pela suite.

    Este teste vira o seu proprio contrario no dia em que a rodada humana
    acontecer, e ai ele deve ser SUBSTITUIDO pelas asserções do `01-04` sobre a
    fixtura real — nao apagado.
    """
    fonte = pathlib.Path(cortador.__file__).read_text(encoding="utf-8")
    assert "moldes_da_barra.json" not in fonte
    meu = pathlib.Path(__file__).read_text(encoding="utf-8")
    assert "fixtures/renda/moldes" not in meu
