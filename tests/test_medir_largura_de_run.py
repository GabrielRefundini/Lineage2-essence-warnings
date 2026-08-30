"""A LARGURA DE RUN: a convencao semi-aberta, o limite derivado, a folga de cola.

Tudo aqui roda sobre fixturas VERSIONADAS de `tests/fixtures/mercado/` e sobre
populacoes CONSTRUIDAS a mao, nunca sobre `recordings/` nem sobre o
`calibration.json` da maquina - os dois sao gitignored e nao vem de clone limpo,
entao um teste que dependesse deles ficaria verde nesta maquina e amarelo em
toda outra. A varredura que PRODUZ o numero
(`tools/medir_largura_de_run.py --gravar`) e outra coisa, roda no checkout
principal, e o numero dela vive no `calibration.json`.

AS FIXTURAS DESTE ARQUIVO, COM A PROVENIENCIA DECLARADA
--------------------------------------------------------
As tres novas saem todas de `recordings/20260828-053105-mercado-aberto/`, que e
uma das 8 gravacoes NOMEADAS do censo. Cada uma e a celula INTEIRA de UMA coluna
calibrada de UMA linha da grade, recortada pelo `dx`/`largura` da calibracao de
producao - a mesma convencao que a producao usa no tick.

    glifos_colados_quantidade_f078.png   123x45, coluna Quantity de
        `frame_000078.png` LINHA 3. O `44` que sai como UM run de 12 px e hoje
        le `4`: o defeito que este plano fecha. Total `56,00` e Unit price
        `1,27` derivam a quantidade 44, entao ele tem rotulo NAO CIRCULAR.

    glifos_colados_total_f105.png        209x45, coluna Total de
        `frame_000105.png` LINHA 6. O caso que separa CONSERTO de INVENCAO: o
        run de 11 px admite `6+5` (que da `144,44`) e `7+4` (que da `149,44`), e
        os dois passam nas duas peneiras. Unit price `2,99` e Quantity `50`
        prendem o total em [149,25; 150,00): so `149,44` cabe.

    glifos_colados_total_f054.png        209x45, coluna Total de
        `frame_000054.png` LINHA 8. O `44,00` cujo run de 12 px hoje le `4,00`.

    glifos_precos_f010.png / glifos_unitario_f010.png   as fixturas de CONTROLE
        que ja existiam (ver `tests/test_medir_leitura_de_glifo.py`). Elas nao
        tem run largo nenhum, e e sobre elas que a convencao de largura e presa.

A CONVENCAO DE LARGURA E SEMI-ABERTA, E ERRAR POR UM INVALIDA TUDO
--------------------------------------------------------------------
`segmentar_glifos` guarda `(inicio, coluna)` onde `coluna` e a PRIMEIRA coluna
VAZIA. A largura e portanto `fim - inicio`, e NUNCA `fim - inicio + 1`. O script
descartavel que levantou o alarme usou a convencao inclusiva, inflou toda
largura em 1, e por isso a faixa "suspeita" dele engoliu TODO `4` legitimo - o
molde do `4` tem exatamente 6 px. `TestAConvencaoSemiAberta` prende isso contra
`glifos_unitario_f010.png`, que le `6,00` com larguras `4, 1, 4, 4`.

O ROTULO DAS COLUNAS DE MOEDA E A INVERSA DO ROTULO DA QUANTITY
-----------------------------------------------------------------
`quantidade_derivada(total, unitario)` (02-07) nao ve um pixel da coluna
Quantity. `total_no_intervalo(total, unitario, quantidade)` e a MESMA aritmetica
no outro sentido: ela nao FIXA o total, mas REJEITA um total inventado. Os dois
sao gabaritos e nao espelhos - e sem isso nao ha medicao, so eco.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from l2scanner.calibracao import Calibracao
from l2scanner.identidade import VALOR_MINIMO_DO_TEXTO
from l2scanner.mercado_leitura import (
    mascara_de_numero,
    segmentar_glifos,
    segmentar_glifos_no_brilho,
)
from l2scanner.mercado_visao import glifos_de_calibracao

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures" / "mercado"
CALIBRACAO = FIXTURES / "calibracao_de_fixture.json"


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


ferramenta = _carregar_a_ferramenta("medir_largura_de_run")

PASSO_DA_VARREDURA = ferramenta.PASSO_DA_VARREDURA
TETO_DA_FOLGA = ferramenta.TETO_DA_FOLGA
Baldes = ferramenta.Baldes
larguras_de_molde = ferramenta.larguras_de_molde
larguras_com_folga = ferramenta.larguras_com_folga
limite_de_glifo_unico = ferramenta.limite_de_glifo_unico
particionar_por_dp = ferramenta.particionar_por_dp
propor_a_folga = ferramenta.propor_a_folga
quantidade_derivada = ferramenta.quantidade_derivada
total_no_intervalo = ferramenta.total_no_intervalo


def _cal() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO)


def _moldes() -> dict:
    return glifos_de_calibracao(_cal().mercado_templates_de_digito)


def _ler(nome: str) -> np.ndarray:
    pixels = cv2.imread(str(FIXTURES / nome))
    assert pixels is not None, f"fixtura ausente: {nome}"
    return pixels


def _piso_e_margem() -> tuple[float, float]:
    cal = _cal()
    return (
        float(cal.mercado_limiar_de_leitura_de_glifo),
        float(cal.mercado_margem_de_leitura_de_glifo),
    )


class TestAConvencaoSemiAberta:
    """A largura e `fim - inicio`. Errar por um infla tudo e engole o `4`."""

    def test_o_unitario_de_controle_da_as_larguras_dos_MOLDES(self):
        faixa, runs = segmentar_glifos(_ler("glifos_unitario_f010.png"))
        assert faixa is not None
        larguras = [fim - inicio for inicio, fim in runs]
        # `6,00`: tres digitos de 4 px e uma virgula de 1 px. Sob a convencao
        # INCLUSIVA isto daria [5, 2, 5, 5], que nao casa com molde nenhum.
        assert larguras == [4, 1, 4, 4]

    def test_as_larguras_de_controle_batem_com_as_larguras_dos_moldes(self):
        moldes = _moldes()
        assert moldes["0"].shape[1] == 4
        assert moldes[","].shape[1] == 1
        assert moldes["4"].shape[1] == 6


class TestAsLargurasDosMoldes:
    def test_larguras_de_molde_ignora_os_moldes_de_PALAVRA(self):
        moldes = _moldes()
        # `Adena` tem 35 px e `XM Coin` 44: eles NAO sao glifos de um caractere
        # e nao entram na geometria de um glifo unico, pela mesma regra que
        # `pontuar_glifos` ja aplica (`len(rotulo) == 1`).
        assert larguras_de_molde(moldes) == (1, 4, 6)

    def test_limite_de_glifo_unico_e_o_MAIOR_deles(self):
        assert limite_de_glifo_unico(_moldes()) == 6

    def test_o_limite_e_DERIVADO_e_nao_uma_chave_do_calibration(self):
        dados = json.loads(CALIBRACAO.read_text(encoding="utf-8"))
        assert not [c for c in dados if "largura_maxima" in c], (
            "o limite virou chave: duas verdades para uma so geometria"
        )

    def test_sem_molde_de_um_caractere_nao_ha_limite(self):
        assert larguras_de_molde({"Adena": np.zeros((10, 35), np.uint8)}) == ()
        assert limite_de_glifo_unico({}) is None


class TestLargurasComFolga:
    def test_folga_zero_e_a_largura_dos_moldes_pura(self):
        assert larguras_com_folga((1, 4, 6), 0) == (1, 4, 6)

    def test_folga_um_acrescenta_UMA_coluna_a_cada_largura(self):
        assert larguras_com_folga((1, 4, 6), 1) == (1, 2, 4, 5, 6, 7)

    def test_folga_dois_nao_repete_largura(self):
        assert larguras_com_folga((1, 4, 6), 2) == (1, 2, 3, 4, 5, 6, 7, 8)


class TestORotuloDeIntervalo:
    """A INVERSA de `quantidade_derivada`, e o caso conferido no pixel."""

    def test_o_caso_de_f105_conferido_a_mao(self):
        # unitario 2,99 e quantidade 50 prendem o total em [149,25; 150,00).
        assert total_no_intervalo(14944, 299, 50) is True
        assert total_no_intervalo(14444, 299, 50) is False

    def test_as_bordas_do_intervalo(self):
        assert total_no_intervalo(14925, 299, 50) is True
        assert total_no_intervalo(14924, 299, 50) is False
        assert total_no_intervalo(15000, 299, 50) is False
        assert total_no_intervalo(14999, 299, 50) is True

    def test_sem_os_dois_inteiros_ele_NAO_OPINA(self):
        assert total_no_intervalo(14944, None, 50) is None
        assert total_no_intervalo(14944, 299, None) is None
        assert total_no_intervalo(None, 299, 50) is None
        assert total_no_intervalo(14944, 299, 0) is None

    def test_ele_NUNCA_levanta(self):
        assert total_no_intervalo(-1, -1, -1) is None

    def test_ele_e_consistente_com_quantidade_derivada(self):
        # O rotulo de intervalo aceita o total quando a quantidade derivada
        # daquele par aponta a quantidade: sao a mesma aritmetica nos dois
        # sentidos, e uma divergencia aqui seria duas verdades.
        assert quantidade_derivada(14944, 299) == 50
        assert total_no_intervalo(14944, 299, 50) is True


class TestAParticaoPorProgramacaoDinamica:
    """O corte de SETE-mais-quatro em f105, e a recusa sem folga."""

    def _run_largo(self, nome: str, valor_minimo: int):
        pixels = _ler(nome)
        faixa, runs = segmentar_glifos_no_brilho(pixels, valor_minimo)
        mascara = (mascara_de_numero(pixels, valor_minimo) * 255).astype(np.uint8)
        limite = limite_de_glifo_unico(_moldes())
        largos = [(a, b) for a, b in runs if b - a > limite]
        assert largos, f"{nome} deixou de ter run largo"
        return mascara, faixa, largos[0]

    def test_f105_acha_o_corte_de_SETE_mais_quatro(self):
        piso, margem = _piso_e_margem()
        mascara, faixa, (a, b) = self._run_largo(
            "glifos_colados_total_f105.png", VALOR_MINIMO_DO_TEXTO
        )
        assert b - a == 11
        achado = particionar_por_dp(
            mascara,
            faixa,
            a,
            b,
            larguras_com_folga(larguras_de_molde(_moldes()), 1),
            piso,
            margem,
            _moldes(),
        )
        assert achado is not None
        pior_score, _pior_margem, rotulos = achado
        # O corte ERRADO (`6+5`) tambem passa nas duas peneiras e produz `44`.
        # A DP escolhe pelo PIOR score, e o pior de `7+4` e ~0,79 contra ~0,47
        # do `6+5` - e por isso ela escolhe o certo sem precisar do rotulo.
        assert rotulos == ["4", "9"]
        assert pior_score > 0.6

    def test_f078_le_o_par_de_QUATROS_ja_com_a_folga_ZERO(self):
        piso, margem = _piso_e_margem()
        cal = _cal()
        mascara, faixa, (a, b) = self._run_largo(
            "glifos_colados_quantidade_f078.png",
            int(cal.mercado_limiar_de_brilho_da_quantidade),
        )
        assert b - a == 12
        achado = particionar_por_dp(
            mascara,
            faixa,
            a,
            b,
            larguras_com_folga(larguras_de_molde(_moldes()), 0),
            piso,
            margem,
            _moldes(),
        )
        assert achado is not None
        assert achado[2] == ["4", "4"]

    def test_sem_largura_que_some_a_particao_devolve_None(self):
        piso, margem = _piso_e_margem()
        mascara, faixa, (a, b) = self._run_largo(
            "glifos_colados_total_f105.png", VALOR_MINIMO_DO_TEXTO
        )
        # Nenhuma composicao de larguras {4} soma 11: a DP nao acha corte.
        assert (
            particionar_por_dp(
                mascara, faixa, a, b, (4,), piso, margem, _moldes()
            )
            is None
        )

    def test_um_piso_impossivel_derruba_TODO_corte(self):
        _piso, margem = _piso_e_margem()
        mascara, faixa, (a, b) = self._run_largo(
            "glifos_colados_total_f105.png", VALOR_MINIMO_DO_TEXTO
        )
        assert (
            particionar_por_dp(
                mascara,
                faixa,
                a,
                b,
                larguras_com_folga(larguras_de_molde(_moldes()), 1),
                0.999,
                margem,
                _moldes(),
            )
            is None
        )


def _celula(chave, coluna, rotulo, por_folga, hoje):
    """Uma celula de populacao CONSTRUIDA, no formato que `propor_a_folga` le."""
    return ferramenta.CelulaLarga(
        chave=chave,
        coluna=coluna,
        rotulo=rotulo,
        lido_hoje=hoje,
        lido_por_folga=dict(por_folga),
    )


class TestAPropostaDaFolga:
    """Propoe a folga com o maior CERTO entre as que NAO erram. Passo 1."""

    def test_o_passo_da_varredura_e_UM(self):
        assert PASSO_DA_VARREDURA == 1

    def test_propoe_a_folga_com_o_MAIOR_certo_entre_as_limpas(self):
        celulas = [
            _celula(("g", "f", 0), "quantidade", 44, {0: 44, 1: 44}, 4),
            _celula(("g", "f", 1), "total", 14944, {0: None, 1: 14944}, 1444),
        ]
        proposta = propor_a_folga(celulas, teto=1)
        assert proposta.veredito == "PROPOSTO"
        assert proposta.folga == 1
        assert proposta.baldes_da_folga.certo == 2
        assert proposta.baldes_da_folga.errado == ()

    def test_REPROVA_quando_nenhuma_folga_tem_o_balde_LE_ERRADO_vazio(self):
        celulas = [
            _celula(("g", "f", 0), "quantidade", 44, {0: 7, 1: 7}, 4),
        ]
        proposta = propor_a_folga(celulas, teto=1)
        assert proposta.veredito == "REPROVADO"
        assert proposta.folga is None
        assert proposta.causa
        assert "7" in proposta.linha_do_veredito

    def test_a_folga_proposta_tem_a_PROPRIA_linha_na_tabela(self):
        celulas = [_celula(("g", "f", 0), "quantidade", 44, {0: 44, 1: 44}, 4)]
        proposta = propor_a_folga(celulas, teto=2)
        assert proposta.folga in proposta.tabela
        assert proposta.tabela[proposta.folga].errado == ()

    def test_a_tabela_nao_tem_saltos(self):
        celulas = [_celula(("g", "f", 0), "quantidade", 44, {}, 4)]
        proposta = propor_a_folga(celulas, teto=3)
        assert sorted(proposta.tabela) == [0, 1, 2, 3]

    def test_empate_de_CERTO_escolhe_a_MENOR_folga(self):
        celulas = [_celula(("g", "f", 0), "quantidade", 44, {0: 44, 1: 44}, 4)]
        proposta = propor_a_folga(celulas, teto=1)
        assert proposta.folga == 0

    def test_uma_populacao_VAZIA_nao_propoe_nada(self):
        proposta = propor_a_folga([], teto=1)
        assert proposta.veredito == "REPROVADO"
        assert "vazia" in proposta.linha_do_veredito.lower()

    def test_a_linha_do_veredito_e_MAIUSCULA_e_diz_a_causa(self):
        celulas = [_celula(("g", "f", 0), "quantidade", 44, {0: 7}, 4)]
        proposta = propor_a_folga(celulas, teto=0)
        assert proposta.linha_do_veredito.startswith("REPROVADO")


class TestOsBaldes:
    def test_o_balde_LE_ERRADO_guarda_a_celula_e_nao_so_a_contagem(self):
        baldes = Baldes(certo=0, nao_le=0, errado=((("g", "f", 0), 44, 4),))
        assert baldes.erra is True
        assert baldes.total == 1
        assert baldes.errado[0][1] == 44

    def test_um_balde_vazio_NAO_erra(self):
        assert Baldes(certo=3, nao_le=1, errado=()).erra is False


class TestOCensoEIMPORTADO:
    def test_e_o_MESMO_OBJETO_de_medir_oclusao(self):
        # Identidade, e nao igualdade: um segundo `importlib` produziria outro
        # objeto e a afirmacao passaria sobre uma COPIA. O modulo de referencia
        # vem de `sys.modules`, que o proprio `_carregar_o_censo` registrou.
        oclusao = sys.modules["medir_oclusao"]
        assert ferramenta.GRAVACOES_DO_CENSO is oclusao.GRAVACOES_DO_CENSO
        assert ferramenta.MOTIVO_PARA_IGNORAR is oclusao.MOTIVO_PARA_IGNORAR

    def test_sao_as_OITO_gravacoes_nomeadas(self):
        assert len(ferramenta.GRAVACOES_DO_CENSO) == 8

    def test_o_fonte_nao_REDECLARA_a_lista(self):
        fonte = (RAIZ / "tools" / "medir_largura_de_run.py").read_text(
            encoding="utf-8"
        )
        assert "GRAVACOES_DO_CENSO = (" not in fonte, (
            "a lista foi COPIADA: duas varreduras passariam a medir conjuntos "
            "diferentes sem ninguem notar"
        )


class TestAParadaQuandoFaltaPastaDoCenso:
    def test_diretorio_inexistente_sai_com_DOIS(self, tmp_path, capsys):
        assert (
            ferramenta.main(
                [
                    "--gravacoes",
                    str(tmp_path / "nao-existe"),
                    "--calibracao",
                    str(CALIBRACAO),
                ]
            )
            == 2
        )

    def test_censo_incompleto_sai_com_TRES_e_NOMEIA_as_que_faltam(
        self, tmp_path, capsys
    ):
        (tmp_path / ferramenta.GRAVACOES_DO_CENSO[0]).mkdir()
        codigo = ferramenta.main(
            [
                "--gravacoes",
                str(tmp_path),
                "--calibracao",
                str(CALIBRACAO),
            ]
        )
        assert codigo == 3
        saida = capsys.readouterr().out
        for nome in ferramenta.GRAVACOES_DO_CENSO[1:]:
            assert nome in saida
        assert ferramenta.GRAVACOES_DO_CENSO[0] not in saida.split(
            "AUSENTE"
        )[-1]


class TestAGravacaoNaoPerdeOsMoldes:
    def test_load_mutate_save_preserva_TUDO_o_mais(self, tmp_path):
        destino = tmp_path / "calibration.json"
        destino.write_text(
            CALIBRACAO.read_text(encoding="utf-8"), encoding="utf-8"
        )
        antes = json.loads(destino.read_text(encoding="utf-8"))
        ferramenta.gravar(destino, 1)
        depois = json.loads(destino.read_text(encoding="utf-8"))
        assert len(depois["mercado_templates_de_digito"]) == len(
            antes["mercado_templates_de_digito"]
        )
        assert depois["mercado_ancoras"] == antes["mercado_ancoras"]
        assert depois["mercado_folga_de_cola_do_glifo"] == 1
        mudadas = {
            chave
            for chave in set(antes) | set(depois)
            if antes.get(chave) != depois.get(chave)
        }
        assert mudadas <= {"mercado_folga_de_cola_do_glifo"}

    def test_a_ferramenta_usa_os_replace(self):
        fonte = (RAIZ / "tools" / "medir_largura_de_run.py").read_text(
            encoding="utf-8"
        )
        assert "os.replace" in fonte
