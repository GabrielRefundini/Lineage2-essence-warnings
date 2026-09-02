"""As partes PURAS da bancada da renda, exercitadas SEM disco e SEM OCR.

NENHUM TESTE DESTE ARQUIVO ABRE A PASTA DE GRAVACOES, e a razao esta escrita em
`tests/test_mercado_glifos.py:4-8`: aquela pasta e gitignored e nao vem de clone
limpo, entao um teste apoiado nela ficaria verde nesta maquina e amarelo em
qualquer outra. A varredura que PRODUZ os numeros
(`tools/medir_a_renda.py --relatorio 1|2`) e outra coisa: ela e ferramenta, roda
no checkout principal, e o resultado dela vive em `01-MEDICOES.md`.

O NOME DAQUELA PASTA NAO APARECE NEM POR ESCRITO NESTE ARQUIVO, e isso e
deliberado: um criterio de aceitacao grepa o nome dela aqui, e um criterio que
aceitasse mencao em comentario deixaria de pegar a abertura de verdade no dia em
que ela entrasse comentada e fosse descomentada. E a mesma disciplina que
`l2scanner/renda_leitura.py` aplica as chamadas de janela do OpenCV.

O que este arquivo prende sao as decisoes que a bancada toma ANTES de tocar um
pixel: o passo da grade, a peneira de dono do frame, a peneira de forma, a
gramatica de inteiro, a leitura do desfecho de producao, o resumo da banda com a
LARGURA, a marca de FRAGIL, e a contagem do censo com denominador. Todas com
dados montados a mao.

Rodar (o `.venv` de producao NAO tem pytest; o Python global NAO tem as bindings
de OCR -- e por isso a ponte):

    PYTHONPATH=".;<repo>/.venv/Lib/site-packages" python -m pytest \\
        tests/test_medir_a_renda.py -q
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from l2scanner.renda_leitura import (
    MOTIVO_DA_DISCORDANCIA,
    MOTIVO_DO_CAMPO_VAZIO,
    RecusaDaRenda,
    ValorDaRenda,
    _cruzar_as_escalas,
)

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


ferramenta = _carregar_a_ferramenta("medir_a_renda")


class TestOPassoDaGradeAndaDeCincoEmCinco:
    """O passo de 10 nao e uma escolha de desempenho: e um defeito medido."""

    def test_o_passo_de_fabrica_e_5(self):
        assert ferramenta.PASSO_DA_GRADE == 5, (
            "A GRADE ANDA DE 5 EM 5. O passo de 10 do M-E PULOU o piso 155 e "
            "concluiu que a Yazalaque nao lia a adena. Medido de 5 em 5 (M-G): "
            "o piso 150 devolve 106.020, que e gramaticalmente valido e errado "
            "por seis ordens de grandeza, e o piso 155 devolve 1.696.020, que e "
            "a verdade de campo. Um passo grosso nao erra para o lado seguro."
        )

    def test_a_grade_visita_o_155(self):
        assert 155 in ferramenta.grade_de_pisos(100, 250, ferramenta.PASSO_DA_GRADE)

    def test_uma_grade_de_10_em_10_pularia_o_155(self):
        # O controle NEGATIVO do teste acima: sem ele, "155 esta na grade" seria
        # uma afirmacao sobre aritmetica e nao sobre o defeito.
        assert 155 not in tuple(range(100, 251, 10))

    def test_o_passo_de_10_e_RECUSADO_com_o_numero_na_mensagem(self):
        with pytest.raises(ValueError) as erro:
            ferramenta.conferir_o_passo(10)
        mensagem = str(erro.value)
        assert "155" in mensagem
        assert "106.020" in mensagem
        assert "1.696.020" in mensagem

    def test_passo_zero_ou_negativo_recusa(self):
        for passo in (0, -5):
            with pytest.raises(ValueError):
                ferramenta.conferir_o_passo(passo)

    def test_a_grade_e_inclusiva_nos_dois_extremos(self):
        grade = ferramenta.grade_de_pisos(150, 160, 5)
        assert grade == (150, 155, 160)

    def test_grade_invertida_recusa(self):
        with pytest.raises(ValueError):
            ferramenta.grade_de_pisos(200, 100, 5)


class TestDeQuemEEstaTela:
    """`None` nunca significa "use o vizinho" -- M-F custou 349 e 112."""

    PERSONAGENS = ("Faerlina", "Yazalaque")

    def test_o_nome_no_arquivo_decide_e_ele_e_insensivel_a_caixa(self):
        assert (
            ferramenta.personagem_do_arquivo(
                "frame_000000_faerlina.png", self.PERSONAGENS
            )
            == "Faerlina"
        )
        assert (
            ferramenta.personagem_do_arquivo("frame_yazalaque.png", self.PERSONAGENS)
            == "Yazalaque"
        )

    def test_frame_sem_dono_devolve_nada_e_nunca_o_primeiro_da_lista(self):
        assert ferramenta.personagem_do_arquivo("frame_000078.png", self.PERSONAGENS) is None

    def test_frame_com_DOIS_donos_e_ambiguidade_e_ela_pula(self):
        assert (
            ferramenta.personagem_do_arquivo(
                "faerlina_e_yazalaque.png", self.PERSONAGENS
            )
            is None
        )

    def test_sem_personagem_calibrado_nada_tem_dono(self):
        assert ferramenta.personagem_do_arquivo("frame_faerlina.png", ()) is None


class TestAFormaDoFrame:
    def test_a_forma_carimbada_bate(self):
        assert ferramenta.frame_tem_a_forma(
            (1392, 1720, 3), {"largura": 1720, "altura": 1392}
        )

    def test_um_recorte_parcial_no_meio_do_lote_e_pego(self):
        assert not ferramenta.frame_tem_a_forma(
            (600, 800, 3), {"largura": 1720, "altura": 1392}
        )

    def test_sem_carimbo_nao_ha_o_que_conferir(self):
        # O carimbo e opcional no esquema; recusar por ausencia desligaria a
        # bancada em toda calibracao antiga.
        assert ferramenta.frame_tem_a_forma((10, 10, 3), None)
        assert ferramenta.frame_tem_a_forma((10, 10, 3), {})
        assert ferramenta.frame_tem_a_forma((10, 10, 3), {"largura": 1720})


class TestAGramaticaDeInteiro:
    """A gramatica do nivel e da adena: a do mercado, e isso e dito em voz alta."""

    def test_o_separador_e_CLASSE_e_nao_caractere(self):
        # Medido nesta arvore, no MESMO recorte da adena da Faerlina: piso 155
        # devolve virgula, piso 160 devolve ponto.
        assert ferramenta.inteiro_do_texto("13,160,684") == 13160684
        assert ferramenta.inteiro_do_texto("13,160.684") == 13160684

    def test_os_dois_numeros_que_o_M_G_mediu_continuam_gramaticalmente_validos(self):
        # Eles NAO deixaram de passar: a adena saiu do OCR por causa disso.
        assert ferramenta.inteiro_do_texto("106.020") == 106020
        assert ferramenta.inteiro_do_texto("91") == 91

    def test_ambiguidade_recusa_em_vez_de_escolher_o_primeiro(self):
        assert ferramenta.inteiro_do_texto("8+1") is None
        assert ferramenta.candidatos_inteiros("8+1") == {8, 1}

    def test_o_MESMO_valor_repetido_nao_e_ambiguidade(self):
        assert ferramenta.inteiro_do_texto("67 67") == 67

    def test_texto_vazio_e_ausente_abstem(self):
        assert ferramenta.inteiro_do_texto("") is None
        assert ferramenta.inteiro_do_texto(None) is None

    def test_o_EXP_usa_a_gramatica_DE_PRODUCAO_e_nao_a_de_inteiro(self):
        assert (
            ferramenta.valor_do_campo("EXP 8.0012% t 592% 76", "barra_esquerda")
            == 80012
        )
        # A mesma cadeia lida como INTEIRO seria ambigua e abstem -- que e a
        # prova de que os dois campos NAO compartilham gramatica.
        assert ferramenta.valor_do_campo("EXP 8.0012% t 592% 76", "nivel") is None

    def test_o_nivel_e_a_adena_usam_a_gramatica_de_inteiro(self):
        assert ferramenta.valor_do_campo("67", "nivel") == 67
        assert ferramenta.valor_do_campo("13,160,684", "barra_direita") == 13160684


class TestOsQuatroDesfechosSaemDaDecisaoDeProducao:
    """A ferramenta LE `_cruzar_as_escalas`; ela nao escreve uma segunda particao."""

    def test_duas_validas_e_iguais(self):
        resultado = _cruzar_as_escalas("nivel", [("69", 69), ("69", 69)])
        assert isinstance(resultado, ValorDaRenda)
        assert (
            ferramenta.desfecho_do_cruzamento(resultado)
            == ferramenta.ACEITA_DUAS_ESCALAS
        )

    def test_uma_valida_e_uma_abstencao_e_o_caso_comum(self):
        resultado = _cruzar_as_escalas("nivel", [("", None), ("67", 67)])
        assert isinstance(resultado, ValorDaRenda)
        assert (
            ferramenta.desfecho_do_cruzamento(resultado) == ferramenta.ACEITA_UMA_ESCALA
        )

    def test_zero_validas_e_recusa_por_ilegibilidade(self):
        resultado = _cruzar_as_escalas("nivel", [("", None), ("", None)])
        assert isinstance(resultado, RecusaDaRenda)
        assert resultado.motivo == MOTIVO_DO_CAMPO_VAZIO
        assert ferramenta.desfecho_do_cruzamento(resultado) == ferramenta.RECUSA_ILEGIVEL

    def test_duas_validas_e_DIFERENTES_e_o_caso_que_este_censo_existe_para_contar(self):
        resultado = _cruzar_as_escalas("nivel", [("67", 67), ("69", 69)])
        assert isinstance(resultado, RecusaDaRenda)
        assert resultado.motivo == MOTIVO_DA_DISCORDANCIA
        assert (
            ferramenta.desfecho_do_cruzamento(resultado)
            == ferramenta.RECUSA_DISCORDANCIA
        )

    def test_a_bancada_NAO_adivinha_desfecho_de_um_tipo_que_nao_conhece(self):
        with pytest.raises(TypeError):
            ferramenta.desfecho_do_cruzamento("aceita, acho")

    def test_os_quatro_sao_QUATRO(self):
        assert len(ferramenta.OS_QUATRO_DESFECHOS) == 4
        assert len(set(ferramenta.OS_QUATRO_DESFECHOS)) == 4


class TestABandaUtilEALarguraDela:
    """A largura conta PISOS DA GRADE, inclusiva -- a convencao esta declarada."""

    def test_a_banda_180_a_190_com_passo_5_tem_largura_3(self):
        banda = ferramenta.resumir_a_banda([180, 185, 190], 5)
        assert (banda.inicio, banda.fim) == (180, 190)
        assert banda.largura == 3, (
            "a convencao desta bancada e CONTAGEM DE PISOS DA GRADE, inclusiva "
            "nos dois extremos -- a mesma de `largura_da_banda` no "
            "calibration.json. Ela NAO e a de `larguras_de_molde`, que mede run "
            "de glifo por `fim - inicio` (M-P)."
        )

    def test_o_vao_em_niveis_de_V_e_EXCLUSIVO_e_sai_ao_lado(self):
        banda = ferramenta.resumir_a_banda([180, 185, 190], 5)
        assert banda.vao_em_v == 10
        # Os dois numeros descrevem a MESMA banda e diferem por definicao. E
        # exatamente esta diferenca de um passo que o M-P registrou como
        # armadilha.
        assert banda.largura != banda.vao_em_v

    def test_so_a_MAIOR_corrida_contigua_conta(self):
        banda = ferramenta.resumir_a_banda([110, 150, 155, 160], 5)
        assert (banda.inicio, banda.fim) == (150, 160)
        assert banda.largura == 3

    def test_um_piso_solto_e_banda_de_largura_1(self):
        banda = ferramenta.resumir_a_banda([150], 5)
        assert (banda.inicio, banda.fim, banda.largura) == (150, 150, 1)

    def test_nenhum_piso_bom_e_ausencia_de_banda_e_nao_banda_fragil(self):
        banda = ferramenta.resumir_a_banda([], 5)
        assert banda.inicio is None
        assert banda.largura == 0
        assert banda.fragil is False


class TestABandaFragil:
    """A adena da Faerlina foi medida com banda de largura 1: sorte, nao margem."""

    def test_largura_1_e_2_sao_FRAGEIS(self):
        assert ferramenta.marcar_fragil(1)
        assert ferramenta.marcar_fragil(2)

    def test_largura_3_em_diante_nao_e(self):
        assert not ferramenta.marcar_fragil(3)
        assert not ferramenta.marcar_fragil(9)

    def test_largura_0_nao_e_fragil_porque_nao_e_banda(self):
        assert not ferramenta.marcar_fragil(0)

    def test_a_banda_de_largura_1_sai_MARCADA_pelo_resumo(self):
        banda = ferramenta.resumir_a_banda([150], 5)
        assert banda.fragil is True

    def test_a_razao_da_fragilidade_vai_ESCRITA_e_nao_so_sinalizada(self):
        razao = ferramenta.RAZAO_DA_BANDA_FRAGIL
        assert "semitransparente" in razao
        assert "cenario" in razao


class TestOCensoTemDenominador:
    def test_a_contagem_sai_com_n_e_com_os_quatro(self):
        contagem = ferramenta.contar_o_censo(
            [
                ferramenta.ACEITA_UMA_ESCALA,
                ferramenta.ACEITA_UMA_ESCALA,
                ferramenta.ACEITA_DUAS_ESCALAS,
                ferramenta.RECUSA_ILEGIVEL,
                ferramenta.RECUSA_DISCORDANCIA,
            ]
        )
        assert contagem["n"] == 5
        assert contagem[ferramenta.ACEITA_UMA_ESCALA] == 2
        assert contagem[ferramenta.ACEITA_DUAS_ESCALAS] == 1
        assert contagem[ferramenta.RECUSA_ILEGIVEL] == 1
        assert contagem[ferramenta.RECUSA_DISCORDANCIA] == 1

    def test_populacao_vazia_da_n_igual_a_zero_e_nao_um_dicionario_vazio(self):
        contagem = ferramenta.contar_o_censo([])
        assert contagem["n"] == 0
        for nome in ferramenta.OS_QUATRO_DESFECHOS:
            assert contagem[nome] == 0

    def test_um_desfecho_fora_dos_quatro_LEVANTA_em_vez_de_sumir(self):
        with pytest.raises(ValueError):
            ferramenta.contar_o_censo(["ACEITA-TALVEZ"])

    def test_denominador_zero_nao_vira_zero_por_cento(self):
        assert ferramenta.por_cento(0, 0) == "-"
        assert ferramenta.por_cento(1, 4) == "25.0%"


class TestAComparacaoContraATabelaDeCampo:
    """Uma reproducao que so pode concordar nao prova nada."""

    def test_bate_quando_os_extremos_coincidem(self):
        banda = ferramenta.resumir_a_banda([190, 195, 200, 205, 210, 215, 220], 5)
        assert ferramenta.banda_bate_com_o_campo(banda, ((190, 220),)) == "BATE"

    def test_DISCORDA_e_um_resultado_valido_e_nao_um_erro(self):
        banda = ferramenta.resumir_a_banda([190, 195, 200, 205, 210, 215], 5)
        assert ferramenta.banda_bate_com_o_campo(banda, ((190, 220),)) == "DISCORDA"

    def test_banda_vazia_contra_tabela_existente_DISCORDA(self):
        banda = ferramenta.resumir_a_banda([], 5)
        assert ferramenta.banda_bate_com_o_campo(banda, ((150, 150),)) == "DISCORDA"

    def test_sem_tabela_o_veredicto_diz_isso_em_vez_de_inventar(self):
        banda = ferramenta.resumir_a_banda([150, 155], 5)
        assert ferramenta.banda_bate_com_o_campo(banda, ()) == "SEM-TABELA"

    def test_a_adena_da_Yazalaque_no_M_E_nao_e_contigua(self):
        # 110 e 150, com vazio entre eles. Encodar como UM intervalo teria
        # inventado uma banda de 9 pisos que o campo nunca mediu.
        assert ferramenta.BANDA_DE_CAMPO[("Yazalaque", "barra_direita")] == (
            (110, 110),
            (150, 150),
        )


class TestAProcedenciaEAAdenaComoCaminhoAbandonado:
    def test_toda_verdade_de_campo_tem_gravacao_E_arquivo_na_chave(self):
        assert ferramenta.VERDADE_DE_CAMPO, "sem gabarito nao ha o que medir"
        for chave in ferramenta.VERDADE_DE_CAMPO:
            gravacao, arquivo = chave
            assert gravacao.startswith("2026"), gravacao
            assert arquivo.endswith(".png"), arquivo

    def test_a_verdade_de_campo_dos_dois_frames_de_00h45(self):
        de_00h45 = ferramenta.VERDADE_DE_CAMPO[
            ("20260902-004500-renda-duas-instancias", "frame_000000_faerlina.png")
        ]
        assert de_00h45["nivel"] == 67
        assert de_00h45["barra_direita"] == 13160684
        # O EXP viaja em DECIMOS DE MILESIMO, e nunca em float.
        assert de_00h45["barra_esquerda"] == 80012

    def test_a_ausencia_de_gabarito_e_ausencia_e_nunca_erro(self):
        de_09h30 = ferramenta.VERDADE_DE_CAMPO[
            ("20260902-093000-renda-segundo-cenario", "frame_faerlina.png")
        ]
        assert "barra_direita" in de_09h30
        assert "nivel" not in de_09h30

    def test_a_adena_carrega_o_rotulo_de_caminho_abandonado_com_o_LEIT_09(self):
        rotulo = ferramenta.ROTULO_DE_CAMINHO_ABANDONADO
        assert "LEIT-09" in rotulo
        assert "denominador" in rotulo

    def test_os_apelidos_desfazem_a_mentira_dos_nomes_das_regioes(self):
        assert ferramenta.APELIDO_DA_REGIAO["barra_esquerda"] == "EXP"
        assert ferramenta.APELIDO_DA_REGIAO["barra_direita"] == "ADENA"


class TestALeituraCarregaOVeredictoSemInventarErro:
    def _leitura(self, **kwargs):
        base = dict(
            gravacao="20260902-004500-renda-duas-instancias",
            frame="frame_000000_faerlina.png",
            personagem="Faerlina",
            regiao="nivel",
            piso=190,
            texto_2x="",
            texto_3x="67",
            valor_2x=None,
            valor_3x=67,
            desfecho=ferramenta.ACEITA_UMA_ESCALA,
            valor=67,
            verdade=67,
            candidatos_2x=0,
            candidatos_3x=1,
        )
        base.update(kwargs)
        return ferramenta.Leitura(**base)

    def test_aceita_e_certa(self):
        leitura = self._leitura()
        assert leitura.aceita is True
        assert leitura.certa is True
        assert leitura.escala_que_sustentou == "3x"

    def test_aceita_e_ERRADA_quando_o_valor_diverge_da_verdade(self):
        # Medido nesta arvore: no piso 185 a regiao do nivel da FAERLINA le
        # `69` na 3x, que e o nivel da YAZALAQUE. Aceito, e errado.
        leitura = self._leitura(piso=185, texto_3x="69", valor_3x=69, valor=69)
        assert leitura.aceita is True
        assert leitura.certa is False

    def test_sem_verdade_de_campo_a_leitura_NAO_e_errada_e_sim_nao_mensuravel(self):
        leitura = self._leitura(verdade=None)
        assert leitura.aceita is True
        assert leitura.certa is None

    def test_recusa_nao_tem_veredicto_de_acerto(self):
        leitura = self._leitura(
            desfecho=ferramenta.RECUSA_DISCORDANCIA, valor=None, valor_2x=69
        )
        assert leitura.aceita is False
        assert leitura.certa is None
        assert leitura.escala_que_sustentou is None
