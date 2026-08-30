"""A ferramenta de calibracao do mercado: o que da para afirmar sem o mouse.

O fluxo e interativo por desenho (D-06) — as regioes sao marcadas com
`cv2.selectROI`. Este arquivo afirma tudo o que NAO depende da mao do usuario:

- os DOIS tripwires de escrita de imagem, o velho e o novo;
- que a mecanica de selecao e COMPARTILHADA com o calibrador atual, e nao
  copiada — inclusive que a refatoracao preservou o comportamento;
- a matriz de confusao, que e a unica parte da ferramenta que pode recusar
  sozinha um trabalho que o usuario acabou de fazer;
- carregar-mutar-regravar, que e o que sustenta "sem editar JSON a mao";
- as recusas explicadas: sem calibracao anterior, frame do modo errado, e
  janela redimensionada depois da calibracao.

O que NAO esta aqui, e nao pode estar: se os retangulos caem no lugar certo.
Isso e o portao humano da Task 2, e a imagem de conferencia existe para ele.
"""

from __future__ import annotations

import argparse
import inspect
import textwrap
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.calibrar
import l2scanner.calibrar_mercado
from l2scanner.calibracao import CalibracaoInvalida
from l2scanner.calibrar import _selecionar_regiao, calibrar_selecionando
from l2scanner.calibrar_mercado import (
    COLISAO_MAXIMA_ENTRE_TEMPLATES,
    MercadoNaoCalibravel,
    carregar_calibracao,
    conferir_o_frame,
    derivar_grade,
    desenhar_conferencia,
    escolher_frame,
    conferir_a_coluna_na_grade,
    grupos_do_cabecalho,
    ler_watchlist,
    matriz_de_confusao,
    medir_o_corte_de_brilho_do_cabecalho,
    montar_ancoras,
    sugerir_a_coluna_do_nome,
    sugerir_as_colunas,
)
from l2scanner.mercado_geometria import GradeMedida

REFERENCIA = Path(__file__).parent / "fixtures" / "calibracao_de_referencia.json"


@pytest.fixture
def calibracao(tmp_path: Path) -> Path:
    destino = tmp_path / "calibration.json"
    destino.write_text(REFERENCIA.read_text(encoding="utf-8"), encoding="utf-8")
    return destino


def _codigo_sem_prosa(fonte: str) -> str:
    """O fonte sem docstrings nem comentarios -- so o que o Python executa.

    Existe para os tripwires estruturais: eles proibem uma MECANICA, nao uma
    palavra. Varrer o texto cru fazia um docstring que explica a proibicao
    reprovar por cita-la.
    """
    import io
    import tokenize

    pedacos = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(fonte).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            pedacos.append(tok.string)
    except tokenize.TokenError:  # pragma: no cover - fonte truncado
        return fonte
    return " ".join(pedacos)


class TestOsDoisTripwiresDeEscritaDeImagem:
    """O modulo novo nao grava imagem; o velho continua gravando num lugar so.

    Replica de `test_conferencia_gravada.py::
    test_existe_um_unico_ponto_de_escrita_no_modulo`, e a razao de o modulo ser
    NOVO: se a calibracao do mercado tivesse crescido dentro de `calibrar.py`,
    qualquer gravacao dela cairia na contagem daquele teste.
    """

    def test_o_modulo_novo_nao_grava_imagem_por_conta_propria(self):
        fonte = inspect.getsource(l2scanner.calibrar_mercado)
        assert fonte.count("imwrite") == 0, (
            "calibrar_mercado gravou imagem sozinho. Toda escrita tem de passar "
            "por _gravar_conferencia, que confere o retorno e diz alto quando "
            "falha — foi o erro calado nos dois pontos que fez o calibrador "
            "anunciar uma imagem que nao existia"
        )

    def test_o_modulo_novo_IMPORTA_o_ponto_unico_de_escrita(self):
        assert hasattr(l2scanner.calibrar_mercado, "_gravar_conferencia")
        assert (
            l2scanner.calibrar_mercado._gravar_conferencia
            is l2scanner.calibrar._gravar_conferencia
        )

    def test_o_tripwire_do_modulo_VELHO_continua_verde_apos_a_extracao(self):
        total = inspect.getsource(l2scanner.calibrar).count("imwrite")
        no_auxiliar = inspect.getsource(
            l2scanner.calibrar._gravar_conferencia
        ).count("imwrite")
        assert no_auxiliar >= 1
        assert total == no_auxiliar, (
            "a extracao de _selecionar_regiao trouxe escrita de imagem junto"
        )

    def test_a_selecao_e_COMPARTILHADA_e_nao_duplicada(self):
        """O tripwire olha CODIGO, nunca prosa.

        A versao anterior varria o fonte cru e reprovava tambem quando a palavra
        aparecia num docstring explicando por que ela nao pode estar ali -- foi o
        que aconteceu ao documentar a correcao do deslocamento da grade. Um
        portao que confunde comentario com chamada ensina a nao comentar, que e
        o avesso do que este projeto quer. Continua igualmente severo com o
        defeito de verdade: `test_o_tripwire_ainda_pega_uma_chamada_de_verdade`
        prova isso por mutacao.
        """
        codigo = _codigo_sem_prosa(inspect.getsource(l2scanner.calibrar_mercado))
        assert "selectROI" not in codigo, (
            "ha uma segunda mecanica de selectROI: duas copias envelhecem "
            "separadas e a pior produz retangulo plausivel na posicao errada"
        )
        assert (
            l2scanner.calibrar_mercado._selecionar_regiao
            is l2scanner.calibrar._selecionar_regiao
        )

    def test_o_tripwire_ainda_pega_uma_chamada_de_verdade(self):
        """Sem esta prova, tornar o tripwire preciso seria so afrouxa-lo."""
        so_prosa = textwrap.dedent(
            """
            def f(x):
                "selectROI aqui e so prosa e deve passar."
                # selectROI aqui tambem
                return x
            """
        )
        assert "selectROI" not in _codigo_sem_prosa(so_prosa), (
            "prosa nao pode reprovar"
        )

        com_chamada = textwrap.dedent(
            """
            def f(img):
                "sem mencao nenhuma."
                return cv2.selectROI("janela", img)
            """
        )
        assert "selectROI" in _codigo_sem_prosa(com_chamada), (
            "uma CHAMADA de verdade tem de continuar sendo pega"
        )

class TestOAuxiliarExtraido:
    """A reescala e a parte que nao podia ser duplicada."""

    def test_devolve_a_caixa_nas_coordenadas_ORIGINAIS(self, monkeypatch):
        """Imagem larga forca escala < 1.0; a caixa volta multiplicada."""
        pixels = np.zeros((900, 3200, 3), dtype=np.uint8)
        monkeypatch.setattr(cv2, "selectROI", lambda *a, **k: (100, 50, 200, 30))
        monkeypatch.setattr(cv2, "destroyAllWindows", lambda: None)

        caixa = _selecionar_regiao(pixels, "t", "i")

        # escala = 1600/3200 = 0.5 -> tudo dobra na volta
        assert caixa == (200, 100, 400, 60)

    def test_sem_reescala_devolve_a_caixa_como_veio(self, monkeypatch):
        pixels = np.zeros((400, 800, 3), dtype=np.uint8)
        monkeypatch.setattr(cv2, "selectROI", lambda *a, **k: (10, 20, 30, 40))
        monkeypatch.setattr(cv2, "destroyAllWindows", lambda: None)

        assert _selecionar_regiao(pixels, "t", "i") == (10, 20, 30, 40)

    @pytest.mark.parametrize("caixa", [(10, 20, 0, 40), (10, 20, 30, 0)])
    def test_caixa_degenerada_devolve_None(self, monkeypatch, caixa):
        """ESC devolve (0,0,0,0): cancelar nao pode virar retangulo de area zero."""
        pixels = np.zeros((400, 800, 3), dtype=np.uint8)
        monkeypatch.setattr(cv2, "selectROI", lambda *a, **k: caixa)
        monkeypatch.setattr(cv2, "destroyAllWindows", lambda: None)

        assert _selecionar_regiao(pixels, "t", "i") is None


class TestAEquivalenciaDaRefatoracao:
    """`calibrar_selecionando` refatorada tem de fazer o que fazia antes."""

    def test_a_mesma_caixa_produz_o_mesmo_recorte_e_a_mesma_origem(
        self, monkeypatch
    ):
        pixels = np.zeros((900, 3200, 3), dtype=np.uint8)
        pixels[100:160, 200:600] = 200
        monkeypatch.setattr(cv2, "selectROI", lambda *a, **k: (100, 50, 200, 30))
        monkeypatch.setattr(cv2, "destroyAllWindows", lambda: None)

        vistos = {}

        def espiao(recorte, ox, oy):
            vistos["forma"] = recorte.shape
            vistos["origem"] = (ox, oy)
            return None

        monkeypatch.setattr(
            l2scanner.calibrar, "calibrar_automatico", espiao
        )
        calibrar_selecionando(pixels, 1000, 2000)

        # x=200 y=100 larg=400 alt=60, exatamente como antes da extracao
        assert vistos["forma"] == (60, 400, 3)
        assert vistos["origem"] == (1200, 2100)

    def test_cancelar_continua_devolvendo_None_sem_chamar_o_automatico(
        self, monkeypatch
    ):
        pixels = np.zeros((400, 800, 3), dtype=np.uint8)
        monkeypatch.setattr(cv2, "selectROI", lambda *a, **k: (0, 0, 0, 0))
        monkeypatch.setattr(cv2, "destroyAllWindows", lambda: None)

        def nunca(*a, **k):  # pragma: no cover - o teste falha se rodar
            raise AssertionError("nao pode deduzir layout de uma selecao vazia")

        monkeypatch.setattr(l2scanner.calibrar, "calibrar_automatico", nunca)
        assert calibrar_selecionando(pixels, 0, 0) is None


def molde_de_texto(texto: str, largura: int = 120, altura: int = 20) -> np.ndarray:
    imagem = np.zeros((altura, largura), dtype=np.uint8)
    cv2.putText(
        imagem, texto, (2, altura - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 255, 1
    )
    return imagem


class TestAMatrizDeConfusao:
    def test_dois_moldes_QUASE_IDENTICOS_sao_RECUSADOS_com_o_par_nomeado(self):
        """`+3 Bota X` contra `+4 Bota X`: o caso que corrompe a serie inteira."""
        moldes = {
            "+3 Bota X": molde_de_texto("+3 Bota X"),
            "+4 Bota X": molde_de_texto("+3 Bota X").copy(),
            "Chapeu Y": molde_de_texto("Chapeu Y"),
        }
        resultado = matriz_de_confusao(moldes)

        assert not resultado.aprovado
        assert set(resultado.par_colidente) == {"+3 Bota X", "+4 Bota X"}
        assert resultado.pior_score > COLISAO_MAXIMA_ENTRE_TEMPLATES
        assert resultado.limiar_sugerido is None
        texto = resultado.explicar()
        assert "+3 Bota X" in texto and "+4 Bota X" in texto
        assert "destroi a serie" in texto

    def test_moldes_BEM_SEPARADOS_sao_aprovados_com_limiar_sugerido(self):
        moldes = {
            "Dragon Belt": molde_de_texto("Dragon Belt"),
            "Zzzz": molde_de_texto("Zzzz"),
        }
        resultado = matriz_de_confusao(moldes)

        assert resultado.aprovado
        assert resultado.pior_score <= COLISAO_MAXIMA_ENTRE_TEMPLATES
        assert resultado.limiar_sugerido == pytest.approx(
            (1.0 + resultado.pior_score) / 2
        )
        assert f"{resultado.pior_score:.4f}" in resultado.explicar()

    def test_a_matriz_traz_TODO_par_uma_vez_so(self):
        moldes = {n: molde_de_texto(n) for n in ("A", "B", "C")}
        resultado = matriz_de_confusao(moldes)
        assert len(resultado.matriz) == 3
        assert ("A", "B") in resultado.matriz
        assert ("B", "A") not in resultado.matriz

    def test_com_menos_de_dois_moldes_nao_ha_o_que_confundir(self):
        assert matriz_de_confusao({}).aprovado
        assert matriz_de_confusao({"so um": molde_de_texto("so um")}).aprovado

    @pytest.mark.parametrize(
        "moldes,quantos",
        [({}, "ZERO"), ({"so um": None}, "UM")],
        ids=["zero-moldes", "um-molde"],
    )
    def test_sem_par_para_comparar_NAO_afirma_score_nem_deriva_limiar(
        self, moldes: dict, quantos: str
    ):
        """Aprovar e correto; afirmar uma medicao que nao aconteceu, nao.

        Com menos de dois moldes nao existe par nenhum. A versao anterior
        devolvia `pior_score=0.0` e `limiar_sugerido=(1.0+0.0)/2` e imprimia
        "Matriz de confusao APROVADA: o pior score entre dois itens diferentes
        e 0.0000" -- duas afirmacoes sem lastro numa frase so, e a segunda
        delas ia direto para o `calibration.json` como
        `mercado_limiar_de_template`.

        0.5 e permissivo a ponto de casar quase tudo: o pior inter-classe que
        este modulo TOLERA e 0.85. `_conferir_as_chaves_de_mercado` aceita 0.5
        sem reclamar (faixa valida `(0, 1]`), entao nada a jusante pegaria isso
        -- a Fase 2 herdaria um numero fabricado com cara de medido.
        """
        if moldes:
            moldes = {"so um": molde_de_texto("so um")}

        resultado = matriz_de_confusao(moldes)

        assert resultado.aprovado, "sem par nenhum, recusar seria pior"
        assert resultado.matriz == {}
        assert resultado.rodou is False
        assert resultado.limiar_sugerido is None, (
            f"com {quantos} molde(s) saiu um limiar derivado de zero "
            f"comparacoes: {resultado.limiar_sugerido}"
        )
        assert resultado.pior_score is None, (
            f"com {quantos} molde(s) saiu um 'pior score' de "
            f"{resultado.pior_score} sem nenhum score ter sido calculado"
        )

        texto = resultado.explicar()
        assert "NAO RODOU" in texto
        assert "APROVADA" not in texto, (
            f"a frase de aprovacao afirma um pior score medido; sem par "
            f"nenhum ela e uma mentira tranquilizadora: {texto!r}"
        )
        assert "0.0000" not in texto and "0.5000" not in texto

    def test_o_limiar_de_template_nao_e_MAIS_gravado_pelo_fluxo(self):
        """A guarda virou omissao, e a omissao e mais forte que a guarda.

        Ate 2026-08-29 este teste exigia `if resultado.limiar_sugerido is not
        None:` em volta da atribuicao, porque escrever `None` por cima de um
        limiar MEDIDO numa rodada anterior era o defeito. Com o passo da
        watchlist aposentado (LEIT-01 le o nome por OCR), `calibrar` nao toca
        mais no campo: `cal` chega a `salvar` com o valor que veio do disco.

        Nao se pode sobrescrever o que nao se atribui.
        """
        fonte = _codigo_sem_prosa(
            inspect.getsource(l2scanner.calibrar_mercado.calibrar)
        )
        assert "cal . mercado_limiar_de_template =" not in fonte
        assert "cal . mercado_templates_de_nome =" not in fonte

    def test_moldes_de_TAMANHOS_diferentes_sao_comparaveis(self):
        """Cortar ao menor comum e o que impede a matriz de aprovar por omissao.

        Sem o alinhamento, dois moldes em que nenhum domina o outro nos dois
        eixos dariam 0.0 — "nao colidem" por nao terem sido comparados.
        """
        base = molde_de_texto("Bota X", largura=140, altura=30)
        # Nenhum dos dois domina o outro nos DOIS eixos: 30x100 contra 20x140.
        moldes = {"alto": base[:30, :100].copy(), "largo": base[:20, :140].copy()}
        resultado = matriz_de_confusao(moldes)
        assert resultado.pior_score > 0.0
        assert not resultado.aprovado


class TestCarregarMutarRegravar:
    def test_mutar_so_o_mercado_preserva_todos_os_demais_campos(
        self, calibracao: Path
    ):
        antes = json.loads(calibracao.read_text(encoding="utf-8"))

        cal = carregar_calibracao(calibracao)
        cal.mercado_grade = {"layout": "negociacao", "linhas_por_pagina": 10}
        cal.mercado_limiar_de_template = 0.93
        cal.salvar(calibracao)

        depois = json.loads(calibracao.read_text(encoding="utf-8"))
        for chave, valor in antes.items():
            if chave.startswith("mercado_"):
                continue
            if isinstance(valor, dict):
                # Campos com valor padrao (os do `layout`) sao ACRESCENTADOS pelo
                # `salvar`, o que ja acontecia antes desta ferramenta existir. O
                # que nao pode e um valor MEDIDO pelo usuario mudar.
                assert valor.items() <= depois[chave].items(), (
                    f"{chave} perdeu ou alterou um valor medido"
                )
            else:
                assert depois[chave] == valor, f"{chave} mudou sem ninguem pedir"
        assert depois["mercado_grade"]["linhas_por_pagina"] == 10
        assert depois["mercado_limiar_de_template"] == 0.93

    def test_a_VERSAO_DO_ESQUEMA_nao_sobe(self, calibracao: Path):
        cal = carregar_calibracao(calibracao)
        cal.mercado_grade = {"layout": "adena"}
        cal.salvar(calibracao)
        assert json.loads(calibracao.read_text(encoding="utf-8"))["versao"] == 2
        assert carregar_calibracao(calibracao).mercado_grade == {"layout": "adena"}

    def test_sem_calibracao_anterior_a_recusa_diz_O_QUE_RODAR(self, tmp_path: Path):
        with pytest.raises(MercadoNaoCalibravel) as erro:
            carregar_calibracao(tmp_path / "nao_existe.json")
        texto = str(erro.value)
        assert "calibrar.bat" in texto
        assert not (tmp_path / "nao_existe.json").exists(), (
            "recusar nao pode criar uma calibracao pela metade"
        )


class TestAsRecusasDeGeometria:
    def test_frame_do_modo_PARTY_e_recusado_alto(self, calibracao: Path):
        cal = carregar_calibracao(calibracao)
        recorte_de_party = np.zeros((522, 174, 3), dtype=np.uint8)
        with pytest.raises(MercadoNaoCalibravel, match="modo party"):
            conferir_o_frame(cal, recorte_de_party)

    def test_frame_de_JANELA_COMPLETA_passa(self, calibracao: Path):
        cal = carregar_calibracao(calibracao)
        conferir_o_frame(cal, np.zeros((1392, 1720, 3), dtype=np.uint8))

    def test_frame_vazio_e_recusado(self, calibracao: Path):
        cal = carregar_calibracao(calibracao)
        with pytest.raises(MercadoNaoCalibravel):
            conferir_o_frame(cal, np.zeros((0, 0, 3), dtype=np.uint8))

    def test_janela_redimensionada_faz_a_LEITURA_recusar(self, calibracao: Path):
        """Pitfall 5: o molde cortado noutra escala casa baixo sem explicacao."""
        cal = carregar_calibracao(calibracao)
        cal.mercado_geometria_da_captura = {"largura": 1720, "altura": 1392}
        cal.salvar(calibracao)

        recarregada = carregar_calibracao(calibracao)
        recarregada.conferir_geometria_do_mercado(1720, 1392)  # nao levanta
        with pytest.raises(CalibracaoInvalida, match="Recalibre o mercado"):
            recarregada.conferir_geometria_do_mercado(1600, 900)

    def test_sem_carimbo_gravado_a_leitura_nao_reclama(self, calibracao: Path):
        """Instalacao que nunca calibrou o mercado sobe igual, com a feature OFF."""
        carregar_calibracao(calibracao).conferir_geometria_do_mercado(800, 600)


class TestAEscolhaDoFrame:
    def test_sem_indice_o_usuario_FOLHEIA_em_vez_de_receber_um_frame_qualquer(
        self, tmp_path: Path, monkeypatch
    ):
        """MEDIDO EM CAMPO 2026-08-28: o frame do meio veio ocluido.

        O padrao antigo era `len(quadros) // 2` -- uma escolha arbitraria que
        nao tem como saber se ali havia tooltip, marcacao de alvo ou a lista em
        rolagem por cima do painel. Calibrar sobre um frame ocluido grava
        retangulos que medem a coisa errada, e o erro so aparece muito depois
        como leitura ruim (a familia do incidente 27x).

        Agora quem escolhe e o olho do usuario. O meio continua sendo onde o
        folhear COMECA -- as gravacoes do roteiro abrem com o usuario ainda
        posicionando a tela --, mas deixou de ser a palavra final.
        """
        for i in range(5):
            (tmp_path / f"frame_{i:06d}.png").write_bytes(b"")

        visto: dict[str, object] = {}

        def falso_navegador(quadros, comeco):
            visto["quantos"] = len(quadros)
            visto["comeco"] = comeco
            return quadros[4]

        monkeypatch.setattr(
            "l2scanner.calibrar_mercado.navegar_e_escolher", falso_navegador
        )
        escolhido = escolher_frame(tmp_path, None, None)

        assert visto["comeco"] == 2, "o folhear deve COMECAR no meio"
        assert visto["quantos"] == 5, "o navegador precisa ver a gravacao inteira"
        assert escolhido.name == "frame_000004.png", (
            "a escolha do usuario tem de mandar, nao o palpite do meio"
        )

    def test_indice_explicito_nao_folheia(self, tmp_path: Path, monkeypatch):
        """`--indice` e uma escolha ja feita: abrir a janela seria atrapalhar."""
        for i in range(5):
            (tmp_path / f"frame_{i:06d}.png").write_bytes(b"")

        def nao_deveria_abrir(quadros, comeco):  # pragma: no cover
            raise AssertionError("--indice explicito nao pode abrir o navegador")

        monkeypatch.setattr(
            "l2scanner.calibrar_mercado.navegar_e_escolher", nao_deveria_abrir
        )
        assert escolher_frame(tmp_path, None, 3).name == "frame_000003.png"

    def test_indice_explicito_manda(self, tmp_path: Path, monkeypatch):
        for i in range(5):
            (tmp_path / f"frame_{i:06d}.png").write_bytes(b"")
        monkeypatch.setattr(
            "l2scanner.calibrar_mercado.navegar_e_escolher",
            lambda quadros, comeco: (_ for _ in ()).throw(
                AssertionError("nao deveria folhear com --indice")
            ),
        )
        assert escolher_frame(tmp_path, None, 0).name == "frame_000000.png"

    def test_indice_fora_da_faixa_e_recusado_dizendo_a_faixa(self, tmp_path: Path):
        for i in range(3):
            (tmp_path / f"frame_{i:06d}.png").write_bytes(b"")
        with pytest.raises(MercadoNaoCalibravel, match="0 a 2"):
            escolher_frame(tmp_path, None, 9)

    def test_pasta_sem_frames_e_recusada(self, tmp_path: Path):
        with pytest.raises(MercadoNaoCalibravel, match="record-janela"):
            escolher_frame(tmp_path, None, None)

    def test_sem_gravacao_e_sem_frame_a_recusa_diz_as_duas_flags(self):
        with pytest.raises(MercadoNaoCalibravel, match="--gravacao"):
            escolher_frame(None, None, None)


class TestADerivacaoDaGrade:
    def test_dez_linhas_de_45_px_saem_de_uma_linha_so(self):
        grade = derivar_grade(
            (100, 200, 900, 450), (100, 200, 900, 45), "negociacao", (60, 150)
        )
        assert grade["linhas_por_pagina"] == 10
        assert grade["altura_da_linha"] == 45

    def test_a_grade_e_guardada_em_DESLOCAMENTO_e_nao_em_posicao(self):
        """O painel anda 827x831 px; posicao absoluta apontaria para o vazio.

        A primeira versao gravava `origem_x`/`origem_y` crus do selectROI. As
        ancoras ja guardavam deslocamento -- a grade tinha recebido so a metade
        certa do tratamento. Encontrado quando o usuario comparou a propria tela
        ao vivo com o frame gravado e viu o painel em outro lugar.
        """
        grade = derivar_grade(
            (100, 200, 900, 450), (100, 200, 900, 45), "negociacao", (60, 150)
        )
        assert grade["dx"] == 40, "dx tem de ser 100-60, nao 100"
        assert grade["dy"] == 50, "dy tem de ser 200-150, nao 200"
        assert "origem_x" not in grade and "origem_y" not in grade, (
            "posicao absoluta nao pode voltar: uma calibracao feita com o painel "
            "num canto apontaria para o vazio depois de um arrasto"
        )

    def test_a_MESMA_grade_em_posicoes_diferentes_da_o_mesmo_deslocamento(self):
        """O que prova que a calibracao sobrevive ao painel andar."""
        num_canto = derivar_grade(
            (100, 200, 900, 450), (100, 200, 900, 45), "negociacao", (60, 150)
        )
        arrastado = derivar_grade(
            (927, 1031, 900, 450), (927, 1031, 900, 45), "negociacao", (887, 981)
        )
        assert num_canto == arrastado

    def test_a_tela_de_busca_tem_NOVE(self):
        grade = derivar_grade((0, 0, 900, 405), (0, 0, 900, 45), "busca", (0, 0))
        assert grade["linhas_por_pagina"] == 9

    def test_o_LAYOUT_e_gravado_junto(self):
        """Sao TRES conjuntos de coluna; ler a coluna errada corrompe a serie."""
        assert (
            derivar_grade((0, 0, 9, 9), (0, 0, 9, 3), "adena", (0, 0))["layout"]
            == "adena"
        )

    def test_linha_de_altura_zero_e_recusada(self):
        with pytest.raises(MercadoNaoCalibravel, match="remarque"):
            derivar_grade((0, 0, 900, 450), (0, 0, 900, 0), "negociacao", (0, 0))


class TestAsAncorasViramDESLOCAMENTO:
    def test_a_posicao_absoluta_vira_deslocamento_a_partir_da_origem(self):
        pixels = np.random.default_rng(1).integers(
            0, 255, size=(600, 800, 3), dtype=np.uint8
        )
        caixas = {
            "titulo": (300, 100, 100, 28),
            "botao_fechar": (700, 90, 60, 60),
        }
        ancoras = montar_ancoras(pixels, caixas, (300, 100))

        assert [(a.nome, a.dx, a.dy) for a in ancoras] == [
            ("titulo", 0, 0),
            ("botao_fechar", 400, -10),
        ]
        assert ancoras[0].molde.shape == (28, 100)

    def test_ancora_fora_do_frame_e_recusada_pelo_nome(self):
        pixels = np.zeros((100, 100, 3), dtype=np.uint8)
        with pytest.raises(MercadoNaoCalibravel, match="botao_fechar"):
            montar_ancoras(pixels, {"botao_fechar": (500, 500, 60, 60)}, (0, 0))


class TestAWatchlist:
    def test_le_a_lista_do_config(self, tmp_path: Path):
        arquivo = tmp_path / "config.toml"
        arquivo.write_text(
            '[mercado]\nwatchlist = ["+3 Bota X", "Dragon Belt"]\n', encoding="utf-8"
        )
        assert ler_watchlist(arquivo) == ["+3 Bota X", "Dragon Belt"]

    def test_sem_secao_de_mercado_devolve_lista_VAZIA_e_nao_erro(
        self, tmp_path: Path
    ):
        arquivo = tmp_path / "config.toml"
        arquivo.write_text("[[evento]]\nnome = 'TvT'\n", encoding="utf-8")
        assert ler_watchlist(arquivo) == []

    def test_sem_arquivo_devolve_lista_vazia(self, tmp_path: Path):
        assert ler_watchlist(tmp_path / "nao_existe.toml") == []

    def test_entradas_em_branco_sao_ignoradas(self, tmp_path: Path):
        arquivo = tmp_path / "config.toml"
        arquivo.write_text('[mercado]\nwatchlist = ["A", "  ", ""]\n', encoding="utf-8")
        assert ler_watchlist(arquivo) == ["A"]


class TestAImagemDeConferencia:
    def test_desenha_sem_tocar_o_original(self):
        pixels = np.zeros((200, 300, 3), dtype=np.uint8)
        copia = pixels.copy()
        saida = desenhar_conferencia(pixels, {"titulo": (10, 20, 100, 28)})
        assert np.array_equal(pixels, copia), "o frame de origem foi alterado"
        assert saida.any(), "nenhum retangulo foi desenhado"


class TestOTextoFinalDaConferencia:
    """O CR-02: a ferramenta so pode mandar abrir uma imagem que existe.

    Este e o FUND-01 verbatim, do outro lado da parede. A linha final era
    incondicional e o retorno de `_gravar_conferencia` era descartado -- mas
    aquela funcao devolve `None` quando nao gravou nada, e um caminho
    ALTERNATIVO (`calibracao-conferencia-HHMMSS.png`) quando o arquivo de sempre
    estava travado no visualizador de fotos, que e o caso mais comum porque a
    propria ferramenta manda o usuario abrir a imagem.

    Nos dois casos o usuario era mandado para `calibracao-conferencia.png`, que
    ou nao existe, ou E A IMAGEM DA CALIBRACAO ANTERIOR.

    Molde copiado de `test_conferencia_gravada.py::
    test_texto_final_do_solo_so_manda_conferir_quando_ha_imagem`, que ja resolvia
    isto certo em `calibrar.py`.
    """

    def test_com_imagem_manda_abrir_O_CAMINHO_QUE_FOI_GRAVADO(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ):
        # O nome ALTERNATIVO de proposito: e o caso que o codigo velho errava.
        imagem = tmp_path / "calibracao-conferencia-235959.png"
        imagem.write_bytes(b"png de mentira")

        l2scanner.calibrar_mercado._texto_final_da_conferencia(
            imagem, tmp_path / "calibration.json"
        )

        saida = capsys.readouterr().out
        assert "ABRA" in saida
        assert str(imagem) in saida, (
            "o texto nao citou o caminho REALMENTE gravado"
        )

    def test_sem_imagem_nao_cita_png_nenhum(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ):
        import re

        l2scanner.calibrar_mercado._texto_final_da_conferencia(
            None, tmp_path / "calibration.json"
        )

        saida = capsys.readouterr().out
        citados = re.findall(r"\S+\.png", saida)
        assert citados == [], (
            f"sem imagem gravada, o texto citou {citados} -- ou o arquivo nao "
            f"existe, ou e o da calibracao ANTERIOR, que e justamente o que o "
            f"usuario abriria e conferiria por engano. Mesma regra de "
            f"`calibrar._gravar_conferencia`: sem imagem, sem nome."
        )
        assert "NAO ACONTECEU" in saida

    def test_sem_imagem_admite_que_a_calibracao_JA_FOI_GRAVADA(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ):
        """`cal.salvar` roda ANTES deste texto -- calar isso e a metade cara.

        Dizer so "a conferencia nao aconteceu" deixaria o usuario achando que
        nada mudou no disco. Mudou: os retangulos que ninguem olhou estao
        gravados e o scanner vai usa-los.
        """
        arquivo = tmp_path / "calibration.json"

        l2scanner.calibrar_mercado._texto_final_da_conferencia(None, arquivo)

        saida = capsys.readouterr().out
        assert arquivo.name in saida, (
            "o texto nao diz onde a calibracao nao-conferida ficou gravada"
        )
        assert "NINGUEM" in saida

    def test_o_calibrar_nao_descarta_mais_o_retorno_da_gravacao(self):
        """O tripwire do defeito exato: a chamada tem de ser atribuida.

        `_gravar_conferencia(...)` como instrucao solta e o bug em uma linha.
        """
        fonte = inspect.getsource(l2scanner.calibrar_mercado.calibrar)
        for linha in fonte.splitlines():
            despido = linha.strip()
            if despido.startswith("_gravar_conferencia("):
                raise AssertionError(
                    f"o retorno de _gravar_conferencia foi descartado: "
                    f"{despido!r}. Ele diz QUAL imagem foi gravada, ou que "
                    f"nenhuma foi -- e sem isso a ferramenta manda abrir um "
                    f"arquivo que pode nao existir ou ser o da rodada anterior."
                )
        assert "_texto_final_da_conferencia(" in fonte


class TestRodarSemWatchlistNaoApagaOsMoldes:
    """CR-04: o unico caminho do projeto que apagava calibracao sem perguntar.

    `cal.mercado_templates_de_nome = [...]` era incondicional. Com a watchlist
    vazia isso e `[]`, e `cal.salvar` regrava o arquivo INTEIRO -- os moldes de
    uma calibracao anterior somem. O caminho e trivial: `ler_watchlist` devolve
    `[]` quando o `config.toml` nao existe (outro checkout, um worktree),
    quando o usuario comentou a watchlist para reajustar so uma ancora, ou
    quando escreveu `[mercado]` sem a chave.

    E o console afirmava o contrario -- "as ancoras e a grade ja ficam
    gravadas" descreve um comportamento ADITIVO.

    Estes testes rodam o `calibrar()` de ponta a ponta, com dubles so nas duas
    coisas que exigem mao humana ou disco: `_selecionar_regiao` e
    `_gravar_conferencia`. E o primeiro teste do projeto a exercitar essa
    funcao inteira -- ela nao tinha nenhum.
    """

    CAIXAS = [
        (300, 200, 100, 28),   # titulo
        (794, 190, 60, 60),    # botao_fechar
        (794, 865, 60, 60),    # canto_inf_dir
        (310, 260, 480, 450),  # area da lista
        (310, 260, 480, 45),   # primeira linha
        # As QUATRO COLUNAS, todas dentro da area da lista (x de 310 a 790) --
        # `conferir_a_coluna_na_grade` recusa o que cair fora.
        (320, 260, 100, 450),  # coluna do nome
        (430, 260, 60, 450),   # Quantity
        (500, 260, 80, 450),   # Total
        (600, 260, 80, 450),   # Unit price
        (310, 228, 480, 30),   # a banda do cabecalho, acima da lista
    ]

    @pytest.fixture
    def cenario(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """calibration.json + frame de janela completa + dubles instalados."""
        import argparse

        destino = tmp_path / "calibration.json"
        destino.write_text(REFERENCIA.read_text(encoding="utf-8"), encoding="utf-8")

        frame = tmp_path / "frame_000000.png"
        pixels = np.random.default_rng(7).integers(
            0, 255, (1000, 900, 3), dtype=np.uint8
        )
        assert cv2.imwrite(str(frame), pixels), "nao gravei o frame de teste"

        fila = list(self.CAIXAS)
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "_selecionar_regiao",
            lambda *a, **k: fila.pop(0),
        )
        # NUNCA deixar o teste escrever na raiz do repositorio: o proprio
        # `_gravar_conferencia` grava em RAIZ/calibracao-conferencia.png, que e
        # o arquivo que engana o usuario. Aqui ele devolve um caminho de
        # mentira, dentro do tmp_path.
        imagem = tmp_path / "conferencia.png"
        monkeypatch.setattr(
            l2scanner.calibrar_mercado, "_gravar_conferencia", lambda _img: imagem
        )

        # O FLUXO COMPLETO GANHOU UM PASSO: depois da watchlist ele oferece o
        # corte de glifos. Estes cenarios nao exercitam glifos, entao respondem
        # "terminar" na primeira volta -- sem isso o laco leria do stdin.
        monkeypatch.setattr("builtins.input", lambda *a, **k: "f")

        args = argparse.Namespace(
            calibracao=str(destino),
            gravacao=None,
            frame=str(frame),
            indice=None,
            layout="negociacao",
            so_digitos=False,
        )
        return destino, args

    def test_os_moldes_de_nome_da_rodada_anterior_SOBREVIVEM(
        self, cenario, capsys
    ):
        """Agora eles sobrevivem por OMISSAO, que e mais forte que a guarda.

        O CR-04 protegia a atribuicao com um `if`. Com o passo da watchlist
        aposentado nao ha atribuicao nenhuma: `calibrar` nao toca no campo, e
        `cal.salvar` regrava o que veio do disco.
        """
        destino, args = cenario
        anteriores = [
            {"nome": "+3 Bota X", "molde": "0a:0a:" + "00" * 100},
            {"nome": "Chapeu Y", "molde": "0a:0a:" + "ff" * 100},
        ]
        dados = json.loads(destino.read_text(encoding="utf-8"))
        dados["mercado_templates_de_nome"] = anteriores
        dados["mercado_limiar_de_template"] = 0.93
        destino.write_text(json.dumps(dados), encoding="utf-8")

        assert l2scanner.calibrar_mercado.calibrar(args) == 0

        depois = json.loads(destino.read_text(encoding="utf-8"))
        assert depois["mercado_templates_de_nome"] == anteriores, (
            "a rodada APAGOU os moldes de nome ja calibrados. Cada um custou "
            "um arrasto de mouse sobre um frame gravado."
        )
        assert depois["mercado_limiar_de_template"] == 0.93, (
            "o limiar MEDIDO numa rodada anterior foi sobrescrito"
        )
        # As ancoras, a grade e as colunas, que e o que esta rodada marcou.
        assert depois["mercado_grade"]["linhas_por_pagina"] == 10
        assert depois["mercado_ancora"]["largura"] == 100

        assert "Mantidos os 2 molde(s)" in capsys.readouterr().out, (
            "a ferramenta preservou os moldes mas nao disse ao usuario"
        )

    def test_sem_moldes_anteriores_nao_promete_nada(self, cenario, capsys):
        """O caso limpo: nao ha o que preservar, e nao ha o que anunciar."""
        destino, args = cenario

        assert l2scanner.calibrar_mercado.calibrar(args) == 0

        depois = json.loads(destino.read_text(encoding="utf-8"))
        assert depois["mercado_templates_de_nome"] is None
        assert depois["mercado_limiar_de_template"] is None
        assert "Mantidos os" not in capsys.readouterr().out

    def test_as_quatro_colunas_sao_gravadas_em_DESLOCAMENTO(self, cenario):
        """Nunca em coordenada absoluta: o painel anda 827x831 px."""
        destino, args = cenario

        assert l2scanner.calibrar_mercado.calibrar(args) == 0

        depois = json.loads(destino.read_text(encoding="utf-8"))
        # origem do painel = canto da faixa de titulo, (300, 200) nas CAIXAS.
        assert depois["mercado_coluna_do_nome"] == {"dx": 20, "largura": 100}
        assert depois["mercado_coluna_da_quantidade"] == {"dx": 130, "largura": 60}
        assert depois["mercado_coluna_do_total"] == {"dx": 200, "largura": 80}
        assert depois["mercado_coluna_do_unitario"] == {"dx": 300, "largura": 80}

    def test_uma_coluna_fora_da_grade_recusa_ANTES_de_gravar(
        self, cenario, monkeypatch: pytest.MonkeyPatch
    ):
        """T-02-02: um dx fora da grade le OUTRA coluna com confianca."""
        destino, args = cenario
        antes = destino.read_text(encoding="utf-8")

        fora = list(self.CAIXAS)
        fora[5] = (100, 260, 100, 450)  # a coluna do nome, a esquerda da lista
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "_selecionar_regiao",
            lambda *a, **k: fora.pop(0),
        )

        with pytest.raises(MercadoNaoCalibravel, match="FORA"):
            l2scanner.calibrar_mercado.calibrar(args)

        assert destino.read_text(encoding="utf-8") == antes, (
            "a recusa aconteceu DEPOIS de gravar"
        )

    def test_nenhuma_instrucao_de_preencher_watchlist_e_impressa(
        self, cenario, capsys
    ):
        """O passo morreu com a reescrita de LEIT-01 em 2026-08-29.

        Mandar o usuario escrever `[mercado] watchlist` agora e mandar ele
        configurar uma coisa que nao e mais lida por ninguem.
        """
        _destino, args = cenario

        assert l2scanner.calibrar_mercado.calibrar(args) == 0

        saida = capsys.readouterr().out
        assert "watchlist" not in saida.lower(), (
            f"a ferramenta ainda fala em watchlist:\n{saida}"
        )
        assert "OCR" in saida, (
            "o passo saiu e nada explicou o que o substituiu — a ausencia "
            "parece defeito"
        )


class TestAsRecusasExplicadasDaWatchlist:
    """WR-06: nada aqui pode virar traceback depois de 5 arrastos de mouse.

    `main` so captura `MercadoNaoCalibravel` -- qualquer outra excecao sobe
    como traceback e o `.bat` nem consegue explicar. E a leitura da watchlist
    acontecia DEPOIS das ancoras e da grade, maximizando o prejuizo.
    """

    def test_toml_invalido_recusa_explicando_em_vez_de_estourar(
        self, tmp_path: Path
    ):
        arquivo = tmp_path / "config.toml"
        arquivo.write_text("[mercado\nwatchlist = [", encoding="utf-8")

        with pytest.raises(MercadoNaoCalibravel) as erro:
            ler_watchlist(arquivo)

        assert "config.toml" in str(erro.value)
        assert "TOML" in str(erro.value)

    @pytest.mark.parametrize(
        "linha,tipo",
        [
            ('watchlist = "Bota"', "str"),
            ("watchlist = 3", "int"),
            ("watchlist = {a = 1}", "dict"),
        ],
        ids=["string", "inteiro", "tabela"],
    )
    def test_watchlist_do_tipo_errado_recusa_nomeando_o_tipo(
        self, tmp_path: Path, linha: str, tipo: str
    ):
        """`watchlist = "Bota"` ITERAVA OS CARACTERES.

        A ferramenta pedia quatro recortes -- `B`, `o`, `t`, `a` -- e montava
        uma matriz de confusao sobre eles.
        """
        arquivo = tmp_path / "config.toml"
        arquivo.write_text(f"[mercado]\n{linha}\n", encoding="utf-8")

        with pytest.raises(MercadoNaoCalibravel) as erro:
            ler_watchlist(arquivo)

        assert "LISTA" in str(erro.value)
        assert tipo in str(erro.value)

    def test_uma_lista_de_verdade_continua_passando(self, tmp_path: Path):
        arquivo = tmp_path / "config.toml"
        arquivo.write_text(
            '[mercado]\nwatchlist = ["+3 Bota X", "Chapeu Y"]\n', encoding="utf-8"
        )
        assert ler_watchlist(arquivo) == ["+3 Bota X", "Chapeu Y"]

    # O TRIPWIRE DE ORDEM ("`ler_watchlist` antes do primeiro `_marcar`") CAIU
    # COM O PROPRIO PASSO, em 2026-08-29. Ele existia para que um `config.toml`
    # quebrado fosse descoberto antes de cinco arrastos de mouse; sem chamador
    # no fluxo, nao ha ordem a prender. O que ficou no lugar e
    # `TestOPassoDaWatchlistFoiAPOSENTADO`, que afirma a AUSENCIA da chamada —
    # uma condicao mais forte, e nao mais fraca, que a de ordem.
    #
    # As recusas explicadas de `ler_watchlist` acima continuam afirmadas: a
    # funcao segue no arquivo como precedente medido.

    def test_falha_de_gravacao_vira_recusa_explicada(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """`cal.salvar` sem `try` produzia `OSError` cru.

        Pasta somente-leitura, disco cheio ou arquivo travado por antivirus.
        """
        fonte = inspect.getsource(l2scanner.calibrar_mercado.calibrar)
        assert "except OSError" in fonte, (
            "cal.salvar continua sem tratamento; um disco cheio vira traceback"
        )


class TestOAvisoDeDpi:
    """WR-07: o modulo calculava `_MODO_DPI` e nunca o conferia."""

    def test_falha_de_dpi_avisa_alto_antes_de_calibrar(
        self, monkeypatch: pytest.MonkeyPatch, capsys
    ):
        monkeypatch.setattr(
            l2scanner.calibrar_mercado, "_MODO_DPI", "FALHOU: sem shcore.dll"
        )
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "calibrar",
            lambda _args: (_ for _ in ()).throw(MercadoNaoCalibravel("parou aqui")),
        )

        assert l2scanner.calibrar_mercado.main([]) == 1

        saida = capsys.readouterr().out
        assert "consciencia de DPI" in saida
        assert "GRAVA" in saida, (
            "o aviso nao diz o que torna esta instancia pior que as outras "
            "duas: aqui as coordenadas erradas vao para o disco e ficam"
        )

    def test_dpi_ok_nao_polui_a_tela(
        self, monkeypatch: pytest.MonkeyPatch, capsys
    ):
        monkeypatch.setattr(
            l2scanner.calibrar_mercado, "_MODO_DPI", "PerMonitorAwareV2"
        )
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "calibrar",
            lambda _args: (_ for _ in ()).throw(MercadoNaoCalibravel("parou aqui")),
        )

        l2scanner.calibrar_mercado.main([])

        assert "DPI" not in capsys.readouterr().out


class TestOMoldeDaAncoraEIndexadoPorNome:
    """WR-08: `ancoras[0]` era o `titulo` por ACIDENTE de ordem.

    `caixas` preserva a ordem de insercao de `ANCORAS_SUGERIDAS`, e `titulo`
    esta primeiro. Reordenar aquela constante -- o que a docstring de
    `localizar_painel` incentiva, "a ordem certa e a mais confiavel primeiro" --
    passaria a gravar o molde de uma ancora ao lado do retangulo de OUTRA, em
    `mercado_ancora`. Erro calado.
    """

    def test_reordenar_as_ancoras_sugeridas_nao_troca_o_molde_gravado(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        import argparse

        destino = tmp_path / "calibration.json"
        destino.write_text(REFERENCIA.read_text(encoding="utf-8"), encoding="utf-8")
        frame = tmp_path / "frame_000000.png"
        pixels = np.random.default_rng(11).integers(
            0, 255, (1000, 900, 3), dtype=np.uint8
        )
        assert cv2.imwrite(str(frame), pixels)

        # A MESMA constante, com `titulo` em ULTIMO. As caixas seguem cada
        # nome, entao a calibracao correta e identica nas duas ordens.
        invertida = tuple(
            reversed(l2scanner.calibrar_mercado.ANCORAS_SUGERIDAS)
        )
        caixas_por_nome = {
            "titulo": (300, 200, 100, 28),
            "botao_fechar": (794, 190, 60, 60),
            "canto_inf_dir": (794, 865, 60, 60),
        }

        def rodar(ancoras_sugeridas):
            monkeypatch.setattr(
                l2scanner.calibrar_mercado,
                "ANCORAS_SUGERIDAS",
                ancoras_sugeridas,
            )
            # O duble responde POR NOME, e nao por posicao numa fila.
            #
            # A fila por posicao presumia que o calibrador pediria as ancoras na
            # ordem de `ANCORAS_SUGERIDAS`. Ele nao pede mais: a faixa de titulo
            # e SEMPRE a primeira, porque e dela que saem os retangulos
            # sugeridos das outras quatro regioes. Responder por nome torna o
            # teste indiferente a ordem de pergunta -- que e exatamente o que
            # ele afirma: reordenar a constante nao pode trocar o molde gravado.
            # A grade, as quatro colunas e a banda do cabecalho, na ordem em
            # que o fluxo as pede depois das ancoras.
            resto = iter(
                [
                    (310, 260, 480, 450),  # area da lista
                    (310, 260, 480, 45),   # primeira linha
                    (320, 260, 100, 450),  # coluna do nome
                    (430, 260, 60, 450),   # Quantity
                    (500, 260, 80, 450),   # Total
                    (600, 260, 80, 450),   # Unit price
                    (310, 228, 480, 30),   # cabecalho
                ]
            )

            def responder(_pixels, titulo, _instrucao, _sugestao=None):
                for nome, caixa in caixas_por_nome.items():
                    if titulo.endswith(nome):
                        return caixa
                return next(resto)

            monkeypatch.setattr(
                l2scanner.calibrar_mercado, "_selecionar_regiao", responder
            )
            monkeypatch.setattr(
                l2scanner.calibrar_mercado,
                "_gravar_conferencia",
                lambda _img: tmp_path / "conferencia.png",
            )
            destino.write_text(
                REFERENCIA.read_text(encoding="utf-8"), encoding="utf-8"
            )
            # o fluxo completo oferece o corte de glifos no fim; este cenario
            # nao exercita glifos e responde "terminar"
            monkeypatch.setattr("builtins.input", lambda *a, **k: "f")
            args = argparse.Namespace(
                calibracao=str(destino), gravacao=None, frame=str(frame),
                indice=None, layout="negociacao", so_digitos=False,
            )
            assert l2scanner.calibrar_mercado.calibrar(args) == 0
            return json.loads(destino.read_text(encoding="utf-8"))

        na_ordem = rodar(l2scanner.calibrar_mercado.ANCORAS_SUGERIDAS)
        fora_de_ordem = rodar(invertida)

        assert (
            na_ordem["mercado_molde_da_ancora"]
            == fora_de_ordem["mercado_molde_da_ancora"]
        ), (
            "reordenar ANCORAS_SUGERIDAS trocou o molde gravado em "
            "mercado_molde_da_ancora -- ele ficou ao lado do retangulo de outra "
            "ancora, e nada avisaria"
        )
        assert na_ordem["mercado_ancora"] == fora_de_ordem["mercado_ancora"]

    def test_o_comentario_nao_promete_mais_que_a_ferramenta_desenha(self):
        """A constante afirmava "a ferramenta mostra cada regiao"; ela nao mostra.

        Os `dx`/`dy` sao desempacotados e descartados, `selectROI` abre vazio, e
        so o TAMANHO sugerido chega ao usuario -- em texto.
        """
        fonte = inspect.getsource(l2scanner.calibrar_mercado)
        cabecalho = fonte[: fonte.index("ANCORAS_SUGERIDAS = (")]
        assert "a ferramenta mostra cada regiao e" not in cabecalho, (
            "o comentario voltou a afirmar um comportamento que nao existe"
        )


class TestAGradeDegeneradaNaoVira1:
    """WR-09: `max(1, galt // altura_da_linha)` disfarcava um retangulo errado.

    "A area da lista e MENOR que uma linha" so acontece se os dois retangulos
    estiverem trocados, ou se um deles sair minusculo. Isso virava
    `linhas_por_pagina: 1`, gravado com a mesma confianca de um valor correto --
    e a Fase 2 leria uma linha por pagina para sempre.
    """

    def test_linha_mais_alta_que_a_grade_e_recusada(self):
        with pytest.raises(MercadoNaoCalibravel) as erro:
            derivar_grade((0, 0, 480, 20), (0, 0, 480, 45), "negociacao", (0, 0))

        texto = str(erro.value)
        assert "20 px" in texto and "45 px" in texto, (
            "a recusa nao diz os dois numeros que o usuario precisa comparar"
        )
        assert "trocados" in texto, "a recusa nao diz o erro mais provavel"

    def test_grade_e_linha_do_mesmo_tamanho_ainda_dao_uma_linha(self):
        """O limite exato NAO e degenerado: uma lista de uma linha e legitima."""
        grade = derivar_grade((0, 0, 480, 45), (0, 0, 480, 45), "busca", (0, 0))
        assert grade["linhas_por_pagina"] == 1

    @pytest.mark.parametrize(
        "layout,esperado", [("negociacao", 10), ("adena", 10), ("busca", 9)]
    )
    def test_a_contagem_de_campo_passa_calada(
        self, layout: str, esperado: int, capsys
    ):
        """Bater com a medicao do spike nao imprime nada."""
        grade = derivar_grade(
            (0, 0, 480, 45 * esperado), (0, 0, 480, 45), layout, (0, 0)
        )
        assert grade["linhas_por_pagina"] == esperado
        assert "ATENCAO" not in capsys.readouterr().out

    def test_divergir_do_numero_MEDIDO_em_campo_avisa_alto(self, capsys):
        """9 linhas onde o campo mediu 10: 5 px de erro na primeira linha bastam.

        Nao e recusa -- a medicao veio de UMA janela, e outra resolucao muda os
        pixels. Mas sair calado deixaria a Fase 2 lendo uma linha a menos por
        pagina para sempre.
        """
        grade = derivar_grade((0, 0, 480, 450), (0, 0, 480, 50), "negociacao", (0, 0))

        assert grade["linhas_por_pagina"] == 9
        saida = capsys.readouterr().out
        assert "ATENCAO" in saida
        assert "9 linhas" in saida and "10" in saida, (
            "o aviso nao confronta o que saiu com o que foi medido"
        )
        assert "negociacao" in saida

    def test_um_layout_desconhecido_nao_inventa_expectativa(self, capsys):
        derivar_grade((0, 0, 480, 450), (0, 0, 480, 50), "inventado", (0, 0))
        assert "ATENCAO" not in capsys.readouterr().out


class TestOLacoDeCorteDeGlifos:
    """A conferencia de CONTAGEM, que e o coracao do modo de digitos.

    Ela transforma um erro de marcacao — o retangulo que cortou meio digito, ou
    que pegou o `X` de `XM Coin` junto — em recusa IMEDIATA, em vez de num molde
    errado gravado com a mesma confianca de um certo. Sem ela, um `8` cortado
    pela metade viraria o molde oficial do `8` e todo preco que o contivesse
    sairia errado, calado.

    Nada aqui abre janela: `_selecionar_regiao` e a leitura do teclado sao
    substituidas.
    """

    def _preco(self, glifos: int = 5) -> np.ndarray:
        """Um 'preco' sintetico com N glifos separados por uma coluna vazia."""
        tela = np.zeros((45, 90, 3), dtype=np.uint8)
        for i in range(glifos):
            tela[10:19, 5 + i * 5 : 9 + i * 5] = 255
        return tela

    def _rodar(
        self,
        monkeypatch,
        pixels: np.ndarray,
        respostas: list[str],
        caixas: list[tuple[int, int, int, int]] | None = None,
        ja_gravados: dict | None = None,
    ) -> dict:
        caixas = caixas or [(0, 0, pixels.shape[1], pixels.shape[0])] * 20
        entregues = iter(caixas)
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "_selecionar_regiao",
            lambda *a, **k: next(entregues),
        )
        fala = iter(respostas)
        return l2scanner.calibrar_mercado.cortar_glifos(
            pixels, ja_gravados or {}, ler=lambda *a, **k: next(fala)
        )

    def test_rotulo_do_tamanho_certo_entra_rotulado_e_na_ordem(self, monkeypatch):
        cortados = self._rodar(monkeypatch, self._preco(5), ["n", "18,90", "f"])
        assert list(cortados) == ["1", "8", ",", "9", "0"]
        for molde in cortados.values():
            assert molde.shape[0] == 9  # a faixa compartilhada

    def test_rotulo_de_tamanho_DIFERENTE_e_recusado_citando_os_DOIS_numeros(
        self, monkeypatch, capsys
    ):
        cortados = self._rodar(monkeypatch, self._preco(5), ["n", "7,50", "f"])
        assert cortados == {}, "nada pode entrar de uma marcacao recusada"

        saida = capsys.readouterr().out
        assert "5" in saida and "4" in saida, (
            "a mensagem tem de trazer quantos glifos foram vistos E quantos "
            "caracteres foram digitados — so um dos dois nao diz o que fazer"
        )

    @pytest.mark.parametrize("rotulo", ["18a90", "18 90", "", "18.90"])
    def test_rotulo_invalido_e_recusado_sem_consumir_a_marcacao(
        self, monkeypatch, rotulo, capsys
    ):
        cortados = self._rodar(monkeypatch, self._preco(5), ["n", rotulo, "f"])
        assert cortados == {}
        assert "virgula" in capsys.readouterr().out.lower()

    def test_dois_numeros_marcados_em_sequencia_ACUMULAM(self, monkeypatch):
        cortados = self._rodar(
            monkeypatch,
            self._preco(5),
            ["n", "18,90", "n", "12,34", "f"],
        )
        assert set(cortados) == {"1", "8", ",", "9", "0", "2", "3", "4"}

    def test_um_glifo_que_aparece_nos_DOIS_e_gravado_uma_vez_so(self, monkeypatch):
        cortados = self._rodar(
            monkeypatch, self._preco(4), ["n", "1234", "n", "1256", "f"]
        )
        assert sorted(cortados) == ["1", "2", "3", "4", "5", "6"]

    def test_recorte_sem_texto_pede_para_REMARCAR_em_vez_de_gravar_vazio(
        self, monkeypatch, capsys
    ):
        escuro = np.zeros((45, 90, 3), dtype=np.uint8)
        cortados = self._rodar(monkeypatch, escuro, ["n", "f"])
        assert cortados == {}
        assert "remarque" in capsys.readouterr().out.lower()

    def test_a_cobertura_NOMEIA_o_que_falta_a_cada_volta(self, monkeypatch, capsys):
        self._rodar(monkeypatch, self._preco(5), ["n", "18,90", "f"])
        saida = capsys.readouterr().out
        # `2` e `5` nao foram cortados e tem de aparecer nomeados
        assert "2" in saida and "5" in saida
        assert "falta" in saida.lower()

    def test_a_cobertura_conta_o_que_JA_ESTAVA_gravado(self, monkeypatch, capsys):
        ja = {d: np.zeros((9, 4), dtype=np.uint8) for d in "0123456789,"}
        self._rodar(monkeypatch, self._preco(5), ["f"], ja_gravados=ja)
        saida = capsys.readouterr().out.lower()
        assert "xm coin" in saida or "adena" in saida, (
            "com os digitos todos gravados, o que falta sao as palavras"
        )

    def test_a_palavra_de_sufixo_e_marcada_INTEIRA_e_a_ferramenta_PERGUNTA_qual(
        self, monkeypatch
    ):
        """Ela pergunta em vez de deduzir: deduzir erraria calado."""
        tela = np.zeros((45, 90, 3), dtype=np.uint8)
        tela[10:18, 5:60] = 150  # apagada como no jogo: so o piso do sufixo ve
        cortados = self._rodar(monkeypatch, tela, ["x", "a", "f"])
        assert set(cortados) == {"XM Coin", "Adena"}
        for molde in cortados.values():
            assert molde.shape == (8, 55)

    def test_opcao_desconhecida_nao_derruba_o_laco(self, monkeypatch):
        cortados = self._rodar(monkeypatch, self._preco(4), ["?", "n", "1234", "f"])
        assert sorted(cortados) == ["1", "2", "3", "4"]


class TestAFusaoDosGlifos:
    """Rodada nova FUNDE com o que ja estava gravado — nunca substitui.

    Precedente direto do CR-04, que consertou este mesmo defeito no caminho dos
    moldes de NOME, e pela mesma razao: cada molde custou um arrasto de mouse
    sobre um frame gravado, e este e o unico caminho do projeto capaz de apagar
    trabalho de calibracao sem perguntar.
    """

    def test_um_subconjunto_recortado_PRESERVA_os_ausentes(self):
        anteriores = {d: _glifo(d) for d in "0123456789,"}
        agora = {"8": _glifo("8", semente=99)}

        fundido = l2scanner.calibrar_mercado.fundir_glifos(anteriores, agora)
        assert set(fundido) == set(anteriores)
        assert np.array_equal(fundido["8"], agora["8"]), "o corte novo vence"
        assert np.array_equal(fundido["0"], anteriores["0"]), "o ausente fica"

    def test_rodada_que_corta_ZERO_nao_apaga_nada(self):
        anteriores = {d: _glifo(d) for d in "0123456789,"}
        fundido = l2scanner.calibrar_mercado.fundir_glifos(anteriores, {})
        assert set(fundido) == set(anteriores)

    def test_o_total_nunca_diminui(self):
        anteriores = {d: _glifo(d) for d in "0123"}
        fundido = l2scanner.calibrar_mercado.fundir_glifos(
            anteriores, {"9": _glifo("9")}
        )
        assert len(fundido) >= len(anteriores)


def _glifo(rotulo: str, semente: int = 7) -> np.ndarray:
    """Um molde 9x4 distinto por rotulo, so para as afirmacoes de fusao."""
    gerador = np.random.default_rng(abs(hash(rotulo)) % 1000 + semente)
    return (gerador.integers(0, 2, size=(9, 4)) * 255).astype(np.uint8)


def _frame_com_preco_sintetico() -> np.ndarray:
    """Uma janela com CINCO glifos DISTINTOS em (100,100), 30x15.

    Distintos de proposito: cinco blocos identicos seriam uniformes (desvio
    zero) e a matriz os classificaria como pares incalculaveis, recusando a
    rodada — o que testaria o guard, e nao a persistencia.
    """
    pixels = np.zeros((1392, 1720, 3), dtype=np.uint8)
    # NENHUM padrao preenche a faixa inteira: um glifo solido de ponta a ponta
    # tem desvio ZERO no proprio recorte e cai no guard de par incalculavel,
    # que e outro comportamento, testado noutro lugar.
    #
    # E os DEZ padroes sao distintos entre si, nao so dentro de cada preco: a
    # segunda rodada marca o preco de baixo, e se ela reaproveitasse as mesmas
    # formas com outros rotulos a matriz recusaria com razao (dois moldes
    # identicos com rotulos diferentes E uma colisao).
    primeira = (
        ((0, 7), (0, 4)),
        ((3, 9), (0, 4)),
        ((0, 5), (0, 2)),
        ((4, 9), (1, 4)),
        ((1, 8), (0, 3)),
    )
    segunda = (
        ((0, 4), (0, 4)),
        ((5, 9), (0, 4)),
        ((2, 9), (0, 2)),
        ((0, 6), (2, 4)),
        ((6, 9), (1, 3)),
    )
    for topo, padroes in ((100, primeira), (200, segunda)):
        for i, ((y0, y1), (x0, x1)) in enumerate(padroes):
            base_x = 100 + i * 5
            pixels[topo + y0 : topo + y1, base_x + x0 : base_x + x1] = 255
    return pixels


class TestAPersistenciaDosGlifos:
    """O que chega ao `calibration.json`, e o que nunca chega."""

    def _rodar(
        self,
        monkeypatch,
        tmp_path: Path,
        calibracao: Path,
        respostas: list[str],
        so_digitos: bool = True,
        caixa: tuple[int, int, int, int] = (100, 100, 30, 15),
    ):
        frame = tmp_path / "frame.png"
        pixels = _frame_com_preco_sintetico()
        cv2.imwrite(str(frame), pixels)

        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "_selecionar_regiao",
            lambda *a, **k: caixa,
        )
        self.gravacoes = []
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "_gravar_conferencia",
            lambda tela: self.gravacoes.append(tela) or (tmp_path / "conf.png"),
        )
        fala = iter(respostas)
        monkeypatch.setattr("builtins.input", lambda *a, **k: next(fala))

        args = argparse.Namespace(
            calibracao=str(calibracao),
            gravacao=None,
            frame=str(frame),
            indice=None,
            layout="adena",
            so_digitos=so_digitos,
        )
        return l2scanner.calibrar_mercado.calibrar(args)

    def test_o_modo_isolado_NAO_pede_ancora_nem_grade(
        self, monkeypatch, tmp_path: Path, calibracao: Path
    ):
        chamadas = []
        frame = tmp_path / "frame.png"
        cv2.imwrite(str(frame), _frame_com_preco_sintetico())

        def espiao(_pixels, titulo, _instrucao, _sugestao=None):
            chamadas.append(titulo)
            return (100, 100, 30, 15)

        monkeypatch.setattr(
            l2scanner.calibrar_mercado, "_selecionar_regiao", espiao
        )
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "_gravar_conferencia",
            lambda tela: tmp_path / "conf.png",
        )
        fala = iter(["n", "18,90", "f"])
        monkeypatch.setattr("builtins.input", lambda *a, **k: next(fala))

        antes = json.loads(calibracao.read_text(encoding="utf-8"))
        args = argparse.Namespace(
            calibracao=str(calibracao), gravacao=None, frame=str(frame),
            indice=None, layout="adena", so_digitos=True,
        )
        assert l2scanner.calibrar_mercado.calibrar(args) == 0

        juntos = " ".join(chamadas).lower()
        assert "ancora" not in juntos and "grade" not in juntos, chamadas
        assert "linha" not in juntos, chamadas

        depois = json.loads(calibracao.read_text(encoding="utf-8"))
        assert depois.get("mercado_ancoras") == antes.get("mercado_ancoras")
        assert depois.get("mercado_grade") == antes.get("mercado_grade")

    def test_os_glifos_cortados_chegam_ao_arquivo_com_limiar_derivado(
        self, monkeypatch, tmp_path: Path, calibracao: Path
    ):
        assert self._rodar(
            monkeypatch, tmp_path, calibracao, ["n", "18,90", "f"]
        ) == 0
        dados = json.loads(calibracao.read_text(encoding="utf-8"))
        rotulos = [i["glifo"] for i in dados["mercado_templates_de_digito"]]
        assert sorted(rotulos) == [",", "0", "1", "8", "9"]
        assert 0.0 < dados["mercado_limiar_de_glifo"] <= 1.0

    def test_uma_rodada_que_corta_ZERO_deixa_a_chave_IDENTICA(
        self, monkeypatch, tmp_path: Path, calibracao: Path
    ):
        self._rodar(monkeypatch, tmp_path, calibracao, ["n", "18,90", "f"])
        antes = json.loads(calibracao.read_text(encoding="utf-8"))

        self._rodar(monkeypatch, tmp_path, calibracao, ["f"])
        depois = json.loads(calibracao.read_text(encoding="utf-8"))
        assert (
            depois["mercado_templates_de_digito"]
            == antes["mercado_templates_de_digito"]
        )

    def test_a_rodada_seguinte_FUNDE_em_vez_de_trocar(
        self, monkeypatch, tmp_path: Path, calibracao: Path
    ):
        self._rodar(monkeypatch, tmp_path, calibracao, ["n", "18,90", "f"])
        self._rodar(
            monkeypatch, tmp_path, calibracao, ["n", "23,45", "f"],
            caixa=(100, 200, 30, 15),  # o SEGUNDO preco, com outras formas
        )

        dados = json.loads(calibracao.read_text(encoding="utf-8"))
        rotulos = {i["glifo"] for i in dados["mercado_templates_de_digito"]}
        assert {"1", "8", "9", "0"} <= rotulos, "os da 1a rodada sumiram"
        assert {"2", "3", "4", "5"} <= rotulos, "os da 2a rodada nao entraram"

    def test_a_saida_final_NOMEIA_os_glifos_que_faltaram(
        self, monkeypatch, tmp_path: Path, calibracao: Path, capsys
    ):
        self._rodar(monkeypatch, tmp_path, calibracao, ["n", "18,90", "f"])
        saida = capsys.readouterr().out
        depois_de_gravar = saida.split("gravada em")[-1]
        for faltante in ("2", "3", "4", "5", "6", "7"):
            assert faltante in depois_de_gravar, (
                f"o glifo {faltante} faltou e nao foi nomeado DEPOIS da linha "
                f"de calibracao gravada — no meio da sessao ele rola para fora "
                f"da tela"
            )

    def test_a_conferencia_visual_e_gravada_UMA_VEZ_SO(
        self, monkeypatch, tmp_path: Path, calibracao: Path
    ):
        self._rodar(monkeypatch, tmp_path, calibracao, ["n", "18,90", "f"])
        assert len(self.gravacoes) == 1, (
            "_gravar_conferencia grava num nome FIXO: a segunda chamada apaga a "
            "primeira e o usuario confere metade da calibracao achando que "
            "confere tudo"
        )
        assert self.gravacoes[0].size > 0

    def test_a_VERSAO_DO_ESQUEMA_segue_2_depois_do_corte(
        self, monkeypatch, tmp_path: Path, calibracao: Path
    ):
        self._rodar(monkeypatch, tmp_path, calibracao, ["n", "18,90", "f"])
        assert json.loads(calibracao.read_text(encoding="utf-8"))["versao"] == 2

    def test_o_corte_preserva_todo_campo_nao_relacionado_a_mercado(
        self, monkeypatch, tmp_path: Path, calibracao: Path
    ):
        antes = json.loads(calibracao.read_text(encoding="utf-8"))
        self._rodar(monkeypatch, tmp_path, calibracao, ["n", "18,90", "f"])
        depois = json.loads(calibracao.read_text(encoding="utf-8"))
        for chave, valor in antes.items():
            if chave.startswith("mercado_"):
                continue
            if isinstance(valor, dict):
                assert valor.items() <= depois[chave].items()
            else:
                assert depois[chave] == valor, f"{chave} mudou sem ninguem pedir"

    def test_colisao_entre_glifos_NAO_GRAVA_NADA_e_nomeia_o_par(
        self, monkeypatch, tmp_path: Path, calibracao: Path
    ):
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "matriz_de_confusao_de_glifos",
            lambda moldes: l2scanner.calibrar_mercado.ResultadoDaConfusao(
                aprovado=False,
                pior_score=0.99,
                par_colidente=("0", "8"),
                limiar_sugerido=None,
                matriz={("0", "8"): 0.99},
            ),
        )
        antes = calibracao.read_text(encoding="utf-8")
        with pytest.raises(MercadoNaoCalibravel):
            self._rodar(monkeypatch, tmp_path, calibracao, ["n", "18,90", "f"])
        assert calibracao.read_text(encoding="utf-8") == antes, (
            "recusar nao pode gravar nada"
        )

    def test_com_menos_de_dois_glifos_o_limiar_NAO_e_inventado(
        self, monkeypatch, tmp_path: Path, calibracao: Path
    ):
        """A licao do CR-03 aplicada a chave nova."""
        # um retangulo estreito, com UM glifo so
        self._rodar(
            monkeypatch, tmp_path, calibracao, ["n", "7", "f"],
            caixa=(100, 100, 4, 15),
        )
        dados = json.loads(calibracao.read_text(encoding="utf-8"))
        assert len(dados["mercado_templates_de_digito"]) == 1
        assert dados.get("mercado_limiar_de_glifo") is None


class TestAChaveDoLimiarDeGlifo:
    """`mercado_limiar_de_glifo`, opcional via `.get` (D-07)."""

    def test_ausente_carrega_sem_excecao(self, calibracao: Path):
        assert carregar_calibracao(calibracao).mercado_limiar_de_glifo is None

    @pytest.mark.parametrize("valor", ["0.9", True, [0.9], {}])
    def test_tipo_errado_recusa_mandando_recalibrar(self, calibracao: Path, valor):
        dados = json.loads(calibracao.read_text(encoding="utf-8"))
        dados["mercado_limiar_de_glifo"] = valor
        calibracao.write_text(json.dumps(dados), encoding="utf-8")
        with pytest.raises((CalibracaoInvalida, MercadoNaoCalibravel), match="ecalibre"):
            carregar_calibracao(calibracao)

    @pytest.mark.parametrize("valor", [0.0, -0.5, 1.5, 2])
    def test_fora_de_zero_a_um_recusa_explicando_o_risco(
        self, calibracao: Path, valor
    ):
        dados = json.loads(calibracao.read_text(encoding="utf-8"))
        dados["mercado_limiar_de_glifo"] = valor
        calibracao.write_text(json.dumps(dados), encoding="utf-8")
        with pytest.raises((CalibracaoInvalida, MercadoNaoCalibravel)):
            carregar_calibracao(calibracao)

    def test_valor_valido_faz_a_ida_e_volta(self, calibracao: Path):
        cal = carregar_calibracao(calibracao)
        cal.mercado_limiar_de_glifo = 0.8586
        cal.salvar(calibracao)
        assert carregar_calibracao(calibracao).mercado_limiar_de_glifo == 0.8586


class TestAFlagDeCorteIsolado:
    def test_a_flag_chega_a_calibrar_pelo_parser(self, monkeypatch):
        vistos = {}
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "calibrar",
            lambda args: vistos.update(vars(args)) or 0,
        )
        assert l2scanner.calibrar_mercado.main(["--frame", "x.png", "--so-digitos"]) == 0
        assert vistos["so_digitos"] is True

    def test_sem_a_flag_o_fluxo_completo_continua_sendo_o_padrao(self, monkeypatch):
        vistos = {}
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "calibrar",
            lambda args: vistos.update(vars(args)) or 0,
        )
        assert l2scanner.calibrar_mercado.main(["--frame", "x.png"]) == 0
        assert vistos["so_digitos"] is False

    def test_o_bat_cita_as_DUAS_invocacoes(self):
        bat = (
            Path(l2scanner.calibrar_mercado.__file__).parent.parent
            / "calibrar-mercado.bat"
        ).read_text(encoding="utf-8", errors="replace")
        assert "--so-digitos" in bat, (
            "o frame que calibra a grade nao tem o digito 8: sem a segunda "
            "invocacao documentada, o usuario nao sabe como completar o conjunto"
        )

class TestAContagemDeLinhasArredonda:
    """MEDIDO EM CAMPO 2026-08-29, na primeira calibracao completa por mao humana.

    O usuario desenhou a area da lista CERTA -- a conferencia visual mostra o
    retangulo cobrindo as dez linhas, com o cabecalho de fora -- mas ela saiu
    com 447 px em vez de 450, e a conta truncava para 9. Tres pixels custavam um
    anuncio inteiro por pagina, calado, la na frente na leitura.

    Nenhuma mao acerta 450 px exatos arrastando um mouse. O arredondamento
    absorve erro de MAO; a divergencia contra o layout medido continua acusando
    erro de INTERPRETACAO. Sao mecanismos diferentes para defeitos diferentes, e
    esta classe prova que consertar um nao apagou o outro.
    """

    def test_o_caso_real_do_usuario_da_DEZ(self):
        grade = derivar_grade(
            (744, 618, 943, 447), (744, 618, 943, 45), "adena", (1171, 362)
        )
        assert grade["linhas_por_pagina"] == 10, (
            "447 px cobrem dez linhas de 45 aos olhos; truncar devolvia 9"
        )

    def test_a_altura_exata_continua_dando_dez(self):
        grade = derivar_grade(
            (744, 618, 943, 450), (744, 618, 943, 45), "adena", (1171, 362)
        )
        assert grade["linhas_por_pagina"] == 10

    def test_o_cabecalho_engolido_CONTINUA_acusando_onze(self):
        """A guarda contra erro de interpretacao nao pode ter sido afrouxada."""
        grade = derivar_grade(
            (744, 590, 943, 495), (744, 590, 943, 45), "adena", (1171, 362)
        )
        assert grade["linhas_por_pagina"] == 11, (
            "arredondar nao pode esconder um cabecalho engolido -- e esse o "
            "erro que o aviso de divergencia existe para pegar"
        )

    def test_uma_grade_genuinamente_curta_continua_dando_nove(self):
        grade = derivar_grade(
            (744, 618, 943, 405), (744, 618, 943, 45), "adena", (1171, 362)
        )
        assert grade["linhas_por_pagina"] == 9


# ---------------------------------------------------------------------------
# As QUATRO COLUNAS e o MOLDE DO CABECALHO (Fase 02, plano 02-01)
# ---------------------------------------------------------------------------
#
# Tudo aqui roda sobre fixtures VERSIONADAS resgatadas de gravacoes reais, e
# nunca sobre `recordings/` — a pasta e gitignored e nao vem de clone limpo,
# entao um teste que dependesse dela ficaria verde nesta maquina e amarelo em
# toda outra. O precedente e `test_mercado_glifos.py:1-16`.
#
#     tests/fixtures/mercado/janela_negociacao_f010.png
#         a JANELA inteira (1720x1392) de
#         `recordings/20260828-060622-mercado-pagina-cheia/frame_000010.png`.
#         Grade de negociacao com dez linhas e uma tooltip cobrindo as quatro
#         primeiras — de proposito: e a linha coberta que prova que a proposta
#         sobrevive a oclusao parcial.
#     tests/fixtures/mercado/cabecalho_negociacao_goods.png
#         a banda do cabecalho (30x944) de
#         `recordings/20260828-063752-mercado-aberto/frame_000000.png`,
#         ordenada por `Goods`.
#     tests/fixtures/mercado/cabecalho_negociacao_unitprice.png
#         a banda do MESMO painel em `frame_000020` da mesma gravacao,
#         ordenada por `Unit price`. O par existe para provar que o molde casa
#         a mesma coluna com e sem a seta, que anda de celula conforme a
#         ordenacao (D-11).

FIXTURES_MERCADO = Path(__file__).parent / "fixtures" / "mercado"
JANELA_F010 = FIXTURES_MERCADO / "janela_negociacao_f010.png"
CABECALHO_GOODS = FIXTURES_MERCADO / "cabecalho_negociacao_goods.png"
CABECALHO_UNITPRICE = FIXTURES_MERCADO / "cabecalho_negociacao_unitprice.png"

# A GRADE DE `janela_negociacao_f010.png`, EM COORDENADAS DO FRAME.
#
# NAO sai de `medir_a_grade` sobre esta fixture, e a razao e o proprio material:
# a tooltip cobre as quatro primeiras linhas e quebra a alternancia de fundo de
# que aquela medicao vive — ela devolve 11 linhas de 45 px comecando na segunda.
# Estes numeros saem do caminho que a ferramenta usa de verdade: a faixa de
# titulo localizada por ancora em (1010, 212) mais o deslocamento gravado no
# `calibration.json` do usuario (dx=-428, dy=258, 942x445, 10 linhas de 45).
#
# Sao constantes de fixture, como `ALTURA_DA_LINHA = 45` em
# `test_mercado_glifos.py`: elas descrevem UM material conhecido, e o teste que
# as usa afirma relacoes, nao os numeros em si.
GRADE_F010 = GradeMedida(esquerda=582, topo=470, largura=942, passo=45, linhas=10)


def _fixture(caminho: Path) -> np.ndarray:
    pixels = cv2.imread(str(caminho))
    assert pixels is not None, f"nao decodifiquei {caminho}"
    return pixels


def _sobrevive(grupo: tuple[int, int], depois: list[tuple[int, int]]) -> bool:
    """O grupo `grupo` ainda existe em `depois`, ainda que mais estreito.

    A comparacao e por SOBREPOSICAO e nao por igualdade: o corte de brilho come
    o antialias das bordas, entao um rotulo que ia de 152 a 181 volta de 153 a
    180. Exigir a tupla identica chamaria de "sumiu" exatamente o texto que o
    corte existe para preservar.
    """
    a, b = grupo
    return any(inicio < b and a < fim for inicio, fim in depois)


def _maximos_por_grupo(
    banda: np.ndarray, grupos: list[tuple[int, int]]
) -> dict[tuple[int, int], int]:
    valor = cv2.cvtColor(banda, cv2.COLOR_BGR2HSV)[:, :, 2]
    return {(a, b): int(valor[:, a:b].max()) for a, b in grupos}


class TestAsTresFixturesDeNegociacaoExistem:
    """Sem elas os testes abaixo nao sao afirmaveis num clone limpo."""

    @pytest.mark.parametrize(
        "caminho,forma",
        [
            (JANELA_F010, (1392, 1720)),
            (CABECALHO_GOODS, (30, 944)),
            (CABECALHO_UNITPRICE, (30, 944)),
        ],
    )
    def test_a_fixture_existe_e_tem_a_forma_medida(self, caminho, forma):
        assert caminho.is_file(), f"{caminho.name} nao foi versionada"
        assert _fixture(caminho).shape[:2] == forma


class TestOCorteDeBrilhoDoCabecalho:
    """O corte e MEDIDO neste frame, nunca herdado de constante.

    A pesquisa mediu rotulos em 229, a seta de ordenacao em 181 e a borda da
    banda em 201, numa unica resolucao e numa unica pele — e por isso o numero
    mora no `calibration.json`, nao no fonte. O que o codigo carrega e o METODO:
    o maior vao entre os picos de brilho dos grupos da propria banda.
    """

    def test_o_corte_cai_ESTRITAMENTE_entre_a_seta_e_os_rotulos(self):
        banda = _fixture(CABECALHO_GOODS)
        corte = medir_o_corte_de_brilho_do_cabecalho(banda)
        assert corte is not None

        antes = _maximos_por_grupo(banda, grupos_do_cabecalho(banda, None))
        depois = grupos_do_cabecalho(banda, corte)
        sumiram = [
            pico for g, pico in antes.items() if not _sobrevive(g, depois)
        ]
        ficaram = [pico for g, pico in antes.items() if _sobrevive(g, depois)]

        assert sumiram, "o corte nao removeu grupo nenhum — nao separou nada"
        assert ficaram, "o corte removeu TUDO — a banda ficaria vazia"
        assert max(sumiram) < corte < min(ficaram), (
            f"corte={corte} nao separa: sumiram ate {max(sumiram)}, ficaram a "
            f"partir de {min(ficaram)}"
        )

    def test_a_seta_de_ordenacao_e_um_dos_grupos_que_somem(self):
        """Ela tem 3 px de largura e e o que o molde NAO pode carregar."""
        banda = _fixture(CABECALHO_GOODS)
        corte = medir_o_corte_de_brilho_do_cabecalho(banda)
        antes = grupos_do_cabecalho(banda, None)
        depois = grupos_do_cabecalho(banda, corte)
        sumiram = [g for g in antes if not _sobrevive(g, depois)]
        assert any(b - a <= 3 for a, b in sumiram), (
            f"nenhum grupo estreito sumiu; sumiram {sumiram}"
        )

    def test_uma_banda_chapada_nao_devolve_corte(self):
        """Sem dois picos nao ha vao para medir, e propor seria inventar."""
        chapada = np.full((30, 200, 3), 200, dtype=np.uint8)
        assert medir_o_corte_de_brilho_do_cabecalho(chapada) is None


class TestOMoldeDoCabecalhoCasaAsDuasORDENACOES:
    """A seta anda de celula; o molde tem de ignorar isso (D-11).

    `frame_000000` esta ordenado por `Goods` e a seta cai no grupo (198,201);
    `frame_000020` esta ordenado por `Unit price` e ela cai em (796,799). Se o
    molde carregasse a seta, ele casaria uma ordenacao e recusaria a outra — e o
    portao de layout recusaria a pagina inteira, calado.
    """

    def test_o_conjunto_de_grupos_e_IGUAL_nas_duas_ordenacoes(self):
        goods = _fixture(CABECALHO_GOODS)
        unitprice = _fixture(CABECALHO_UNITPRICE)

        crus_goods = grupos_do_cabecalho(goods, None)
        crus_unit = grupos_do_cabecalho(unitprice, None)
        assert crus_goods != crus_unit, (
            "as duas bandas ja eram iguais SEM o corte — a fixture nao prova "
            "nada sobre a seta"
        )

        corte = medir_o_corte_de_brilho_do_cabecalho(goods)
        assert grupos_do_cabecalho(goods, corte) == grupos_do_cabecalho(
            unitprice, corte
        )

    def test_o_corte_medido_nas_duas_bandas_e_o_mesmo(self):
        assert medir_o_corte_de_brilho_do_cabecalho(
            _fixture(CABECALHO_GOODS)
        ) == medir_o_corte_de_brilho_do_cabecalho(_fixture(CABECALHO_UNITPRICE))


class TestASugestaoDaColunaDoNome:
    """LEIT-05: o recorte e a COLUNA, nunca a linha inteira.

    E ele precisa ser LARGO. Medido em campo: um nome num recorte de 143 px saiu
    truncado (`Common Mafia Leader Lucia`); com 270 px saiu inteiro. Medir a
    coluna pelo TEXTO desta pagina daria 263 px — todos os dez nomes aqui sao o
    mesmo `Earth Spirit Evolution Stone`, e nomes sao alinhados a ESQUERDA e de
    comprimento variavel. Por isso o limite direito vem do rotulo `Quantity` no
    cabecalho, que e o pixel mais a esquerda que aquela coluna chega a desenhar.
    """

    def test_comeca_depois_do_icone_e_cobre_pelo_menos_270_px(self):
        pixels = _fixture(JANELA_F010)
        caixa = sugerir_a_coluna_do_nome(pixels, GRADE_F010)
        assert caixa is not None
        x, y, largura, altura = caixa

        # O ICONE VAI DE +11 A +42 e o NOME COMECA EM +48, medidos nas dez
        # linhas desta fixture. O retangulo tem de cair na terra de ninguem
        # entre os dois.
        #
        # A PONTA DE BAIXO E A QUE PEGA A REGRESSAO REAL: o icone tem miolo
        # escuro (saturacao 84-107 entre bordas de 193-255), e todo corte
        # automatico que tentei — maior vao, Otsu — pousa nesse miolo e devolve
        # ~+30, partindo o icone ao meio e deixando metade dele dentro do
        # recorte que vai para o OCR.
        assert x >= GRADE_F010.esquerda + 43, "o retangulo comecou dentro do icone"
        assert x <= GRADE_F010.esquerda + 48, "o retangulo comeu o inicio do nome"
        assert largura >= 270, (
            f"a coluna do nome saiu com {largura} px; 270 e o piso medido em "
            f"campo para um nome longo nao truncar"
        )
        assert y == GRADE_F010.topo
        assert altura == GRADE_F010.altura

    def test_nao_invade_a_coluna_da_quantidade(self):
        """A quantidade desta pagina comeca em +428 a partir da grade."""
        caixa = sugerir_a_coluna_do_nome(_fixture(JANELA_F010), GRADE_F010)
        x, _y, largura, _altura = caixa
        assert x + largura <= GRADE_F010.esquerda + 428

    def test_sem_cabecalho_legivel_devolve_None(self):
        """`None` abre a janela VAZIA. Sugerir errado e pior que nao sugerir."""
        ruido = np.random.default_rng(3).integers(
            0, 255, (1000, 900, 3), dtype=np.uint8
        )
        grade = GradeMedida(esquerda=10, topo=100, largura=800, passo=45, linhas=10)
        assert sugerir_a_coluna_do_nome(ruido, grade) is None


class TestAsColunasDeNumero:
    """Quantity, Total e Unit price viram RETANGULO CALIBRADO, nao busca.

    Em producao a coluna de numero nunca e localizada por `numeros_com_sufixo`:
    aquela funcao propoe aqui, com um humano olhando, e o que vale depois e o
    retangulo confirmado.
    """

    @pytest.fixture
    def colunas(self):
        return sugerir_as_colunas(_fixture(JANELA_F010), GRADE_F010)

    def test_propoe_as_quatro(self, colunas):
        assert set(colunas) == {"nome", "quantidade", "total", "unitario"}

    def test_nenhum_par_se_sobrepoe_em_UM_pixel(self, colunas):
        faixas = sorted((x, x + largura) for x, _y, largura, _alt in colunas.values())
        for (_a0, a1), (b0, _b1) in zip(faixas, faixas[1:]):
            assert a1 <= b0, f"as colunas se sobrepoem: {faixas}"

    def test_o_unitario_cai_a_direita_do_total(self, colunas):
        assert colunas["unitario"][0] >= colunas["total"][0] + colunas["total"][2]

    def test_cada_coluna_cabe_dentro_da_grade(self, colunas):
        for nome, (x, _y, largura, _alt) in colunas.items():
            assert x >= GRADE_F010.esquerda, nome
            assert x + largura <= GRADE_F010.esquerda + GRADE_F010.largura, nome

    def test_a_coluna_do_total_cobre_o_numero_da_pagina(self, colunas):
        """Os totais desta pagina vivem entre +548 e +579 a partir da grade."""
        x, _y, largura, _alt = colunas["total"]
        assert x <= GRADE_F010.esquerda + 548
        assert x + largura >= GRADE_F010.esquerda + 579

    def test_a_coluna_do_unitario_cobre_o_numero_da_pagina(self, colunas):
        """Os unitarios desta pagina vivem entre +820 e +851."""
        x, _y, largura, _alt = colunas["unitario"]
        assert x <= GRADE_F010.esquerda + 820
        assert x + largura >= GRADE_F010.esquerda + 851

    def test_um_frame_sem_grade_legivel_nao_propoe_nada(self):
        ruido = np.random.default_rng(11).integers(
            0, 255, (1000, 900, 3), dtype=np.uint8
        )
        grade = GradeMedida(esquerda=10, topo=100, largura=800, passo=45, linhas=10)
        assert sugerir_as_colunas(ruido, grade) == {}


class TestARecusaDeColunaForaDaGrade:
    """Um dx mentido nao quebra nada visivel: ele le OUTRA coluna (T-02-02)."""

    GRADE = (100, 200, 400, 450)

    def test_a_coluna_que_passa_da_direita_e_recusada(self):
        with pytest.raises(MercadoNaoCalibravel, match="Remarque|remarque"):
            conferir_a_coluna_na_grade("total", (450, 200, 100, 450), self.GRADE)

    def test_a_coluna_que_comeca_antes_da_grade_e_recusada(self):
        with pytest.raises(MercadoNaoCalibravel, match="Remarque|remarque"):
            conferir_a_coluna_na_grade("nome", (50, 200, 100, 450), self.GRADE)

    def test_a_coluna_dentro_da_grade_passa(self):
        conferir_a_coluna_na_grade("nome", (110, 200, 100, 450), self.GRADE)


class TestOPassoDaWatchlistFoiAPOSENTADO:
    """LEIT-01 passou a ler o nome por OCR em 2026-08-29 (quick `260829-rd9`).

    A ferramenta nao pede mais recorte por item nem manda o usuario escrever
    `[mercado] watchlist` no `config.toml`. `ler_watchlist` e
    `matriz_de_confusao` FICAM no arquivo — elas sao o precedente medido citado
    por outros textos, e apagar a funcao apagaria a medicao junto.
    """

    def test_as_duas_funcoes_continuam_existindo(self):
        assert callable(l2scanner.calibrar_mercado.ler_watchlist)
        assert callable(l2scanner.calibrar_mercado.matriz_de_confusao)

    def test_o_fluxo_principal_nao_chama_mais_ler_watchlist(self):
        fonte = inspect.getsource(l2scanner.calibrar_mercado.calibrar)
        assert "ler_watchlist" not in _codigo_sem_prosa(fonte), (
            "o passo da watchlist voltou ao fluxo principal"
        )

    def test_o_layout_negociacao_e_o_padrao_do_cli(self):
        """D-09: o v1 le SOMENTE o layout calibrado, e ele passou a ser este."""
        ajuda = " ".join(_rodar_help().split())
        assert "--layout" in ajuda
        assert "padrao: negociacao" in ajuda


def _rodar_help() -> str:
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        with pytest.raises(SystemExit):
            l2scanner.calibrar_mercado.main(["--help"])
    return buffer.getvalue()
