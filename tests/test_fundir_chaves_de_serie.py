"""As GUARDAS da ferramenta que funde as chaves partidas pela letra de grade.

ESTA SUITE NAO TOCA O `.mercado/` DO USUARIO, E ISSO E AFIRMADO E NAO PROMETIDO
===============================================================================
`.mercado/` e dado real, acumulado, sem versao e sem desfazer. Toda fixtura mora
em `tmp_path`. E como "eu tomei cuidado" nao e uma prova, a fixtura autouse
`o_mercado_do_usuario_fica_intocado` tira um INSTANTANEO da pasta de producao
(nomes, tamanhos e `st_mtime_ns` de cada arquivo, recursivo) antes de CADA teste
e o compara depois. Se a pasta nao existe, ela afirma que continua nao
existindo. Um teste que escrevesse la falharia — na maquina do usuario, onde a
pasta existe de verdade, e nesta arvore, onde ela nao existe.

A ferramenta tambem nunca e EXECUTADA contra a pasta de producao aqui: nenhum
teste chama `main()` sem `--pasta` apontando para `tmp_path`, e ha um teste que
afirma justamente qual e o padrao do argumento, sem roda-lo.

O QUE CADA CLASSE PRENDE
------------------------
    TestOPlano                  a regra que nao pode ser afrouxada: fusao SO na
                                igualdade exata de `nome_exibido`, e recusa
                                NOMEADA quando ha zero ou duas candidatas com
                                letra de grade
    TestAsObservacoes           a duplicata da fusao vira UMA linha, com a
                                `primeira_vez` mais ANTIGA, e a ordem do arquivo
                                sobrevive
    TestOCatalogo               `avistamentos` SOMA, `primeira_vez` fica a mais
                                antiga e `ultima_vez` a mais recente
    TestOContratoDaSaida        cabecalho byte a byte e quebra de linha final
                                (D-17), afirmados ANTES de gravar
    TestODryRun                 sem `--gravar`, nem um byte nem um mtime mudam
    TestAGravacao               backup byte a byte, escrita atomica, e backup
                                que nunca e sobrescrito
    TestOArquivoDoUsuario       os numeros da simulacao: 61 -> 51, com 10
                                duplicatas reais
    TestOMercadoDeProducao      a propria guarda desta suite, e o padrao do
                                argumento
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def _carregar_a_ferramenta(nome: str):
    caminho = RAIZ / "tools" / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    assert spec and spec.loader, f"nao carreguei {caminho}"
    modulo = importlib.util.module_from_spec(spec)
    # Registrar ANTES de executar: `@dataclass` resolve as anotacoes por
    # `sys.modules[cls.__module__]`, e sem isto ele encontra None.
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


ferramenta = _carregar_a_ferramenta("fundir_chaves_de_serie")

from l2scanner.mercado_catalogo import (  # noqa: E402
    ARQUIVO_DO_CATALOGO,
    PASTA_DO_MERCADO,
)
from l2scanner.mercado_registro import (  # noqa: E402
    ARQUIVO_DE_OBSERVACOES,
    ContratoDoArquivoQuebrado,
)


# ---------------------------------------------------------------------------
# A GUARDA: nenhum teste desta suite toca a pasta de producao
# ---------------------------------------------------------------------------


def _instantaneo_do_mercado():
    """Nomes, tamanhos e mtimes de tudo sob `.mercado/`, ou `None` se ausente."""
    if not PASTA_DO_MERCADO.exists():
        return None
    itens = []
    for caminho in sorted(PASTA_DO_MERCADO.rglob("*")):
        if caminho.is_file():
            estado = caminho.stat()
            itens.append(
                (
                    str(caminho.relative_to(PASTA_DO_MERCADO)),
                    estado.st_size,
                    estado.st_mtime_ns,
                )
            )
    return itens


@pytest.fixture(autouse=True)
def o_mercado_do_usuario_fica_intocado():
    """A prova executada de que a suite nao escreve no dado real do usuario."""
    antes = _instantaneo_do_mercado()
    yield
    depois = _instantaneo_do_mercado()
    assert depois == antes, (
        "UM TESTE DESTA SUITE TOCOU " + str(PASTA_DO_MERCADO) + ". Esse arquivo "
        "e dado real do usuario, sem versao e sem desfazer. Toda fixtura tem de "
        "morar em `tmp_path`."
    )


# ---------------------------------------------------------------------------
# Montagem de fixturas, sempre em tmp_path
# ---------------------------------------------------------------------------

CABECALHO_DE_OBSERVACOES = (
    "chave_da_serie;nome_exibido;primeira_vez;total_em_centesimos;quantidade;"
    "residuo_do_cruzamento\r\n"
)
CABECALHO_DO_CATALOGO = "chave;nome_exibido;primeira_vez;ultima_vez;avistamentos\r\n"

BASE = datetime(2026, 8, 30, 14, 3, 21)


def _linha_de_observacao(chave, nome, carimbo, total, quantidade, residuo=""):
    return ";".join(
        [chave, nome, carimbo.isoformat(), str(total), str(quantidade), residuo]
    )


def escrever_observacoes(pasta: Path, linhas, cabecalho=CABECALHO_DE_OBSERVACOES):
    arquivo = pasta / ARQUIVO_DE_OBSERVACOES
    texto = cabecalho + "".join(linha + "\r\n" for linha in linhas)
    with arquivo.open("w", encoding="utf-8", newline="") as destino:
        destino.write(texto)
    return arquivo


def _linha_de_catalogo(chave, nome, primeira, ultima, avistamentos):
    return ";".join(
        [chave, nome, primeira.isoformat(), ultima.isoformat(), str(avistamentos)]
    )


def escrever_catalogo(pasta: Path, linhas, cabecalho=CABECALHO_DO_CATALOGO):
    arquivo = pasta / ARQUIVO_DO_CATALOGO
    texto = cabecalho + "".join(linha + "\r\n" for linha in linhas)
    with arquivo.open("w", encoding="utf-8", newline="") as destino:
        destino.write(texto)
    return arquivo


def ler_linhas(arquivo: Path):
    with arquivo.open("r", encoding="utf-8", newline="") as fonte:
        bruto = fonte.read()
    corpo = bruto.split("\n", 1)[1]
    return [linha for linha in corpo.replace("\r\n", "\n").split("\n") if linha]


ARMOR_VELHA = "protecting-scroll-enchant-c-grade-armor#"
ARMOR_NOVA = "protecting-scroll-enchant-c-grade-armor#C"
ARMOR_NOME = "Protecting Scroll: Enchant C-grade Armor"
WEAPON_VELHA = "scroll-enchant-d-grade-weapon#"
WEAPON_NOVA = "scroll-enchant-d-grade-weapon#D"
WEAPON_NOME = "Scroll: Enchant D-grade Weapon"


# ---------------------------------------------------------------------------


class TestOPlano:
    """A regra mecanica: igualdade EXATA de `nome_exibido`, e nada mais."""

    def test_duas_chaves_com_o_mesmo_nome_fundem_na_que_tem_letra(self):
        plano = ferramenta.planejar(
            {ARMOR_VELHA: ARMOR_NOME, ARMOR_NOVA: ARMOR_NOME}
        )
        assert plano.recusas == ()
        assert len(plano.fusoes) == 1
        assert plano.fusoes[0].destino == ARMOR_NOVA
        assert plano.fusoes[0].origens == (ARMOR_VELHA,)
        assert plano.mapa == {ARMOR_VELHA: ARMOR_NOVA}

    def test_nomes_diferentes_nao_fundem_e_a_razao_sai_por_extenso(self):
        plano = ferramenta.planejar(
            {ARMOR_VELHA: "Protecting Scroll: Enchant B-grade Armor",
             ARMOR_NOVA: ARMOR_NOME}
        )
        assert plano.fusoes == ()
        assert len(plano.recusas) == 1
        motivo = plano.recusas[0].motivo
        assert "nome_exibido" in motivo
        assert "B-grade" in motivo and "C-grade" in motivo
        assert "similaridade" in motivo

    def test_nome_que_difere_so_no_espaco_nao_funde(self):
        """A igualdade e de bytes. `strip` aqui seria a primeira frouxidao."""
        plano = ferramenta.planejar(
            {ARMOR_VELHA: ARMOR_NOME + " ", ARMOR_NOVA: ARMOR_NOME}
        )
        assert plano.fusoes == ()
        assert len(plano.recusas) == 1

    def test_nenhuma_candidata_com_letra_recusa_o_grupo_e_nomeia_o_caso(self):
        plano = ferramenta.planejar(
            {"hardins-soul-crystal#": "Hardin's Soul Crystal",
             "hardins-soul-crystal#1": "Hardin's Soul Crystal"}
        )
        assert plano.fusoes == ()
        assert len(plano.recusas) == 1
        assert "NENHUMA" in plano.recusas[0].motivo

    def test_duas_candidatas_com_letra_recusam_o_grupo_e_nomeiam_as_duas(self):
        plano = ferramenta.planejar(
            {"gemstone#": "Gemstone",
             "gemstone#B": "Gemstone",
             "gemstone#C": "Gemstone"}
        )
        assert plano.fusoes == ()
        assert len(plano.recusas) == 1
        motivo = plano.recusas[0].motivo
        assert "MAIS DE UMA" in motivo
        assert "gemstone#B" in motivo and "gemstone#C" in motivo

    def test_chave_que_so_existe_nas_observacoes_e_recusada_e_nomeada(self):
        plano = ferramenta.planejar(
            {ARMOR_NOVA: ARMOR_NOME}, chaves_observadas=[ARMOR_VELHA]
        )
        assert plano.fusoes == ()
        assert len(plano.recusas) == 1
        assert "catalogo" in plano.recusas[0].motivo

    def test_chave_sozinha_nao_produz_fusao_nem_recusa(self):
        plano = ferramenta.planejar({ARMOR_NOVA: ARMOR_NOME})
        assert plano.fusoes == () and plano.recusas == ()

    def test_chave_sem_separador_de_assinatura_fica_no_proprio_grupo(self):
        """Duas chaves estranhas nao podem cair no MESMO grupo por acidente."""
        plano = ferramenta.planejar({"solta-a": "A", "solta-b": "B"})
        assert plano.fusoes == () and plano.recusas == ()

    def test_a_letra_e_lida_da_chave_e_nao_recalculada_do_nome(self):
        assert ferramenta.tem_letra_de_grade(ARMOR_NOVA) is True
        assert ferramenta.tem_letra_de_grade(ARMOR_VELHA) is False
        assert ferramenta.tem_letra_de_grade("x#5B3") is True
        assert ferramenta.tem_letra_de_grade("x#12") is False


class TestAsObservacoes:
    def test_a_duplicata_da_fusao_vira_uma_linha_com_a_primeira_vez_mais_antiga(self):
        antiga = BASE
        recente = BASE + timedelta(days=2)
        linhas = [
            [ARMOR_VELHA, ARMOR_NOME, antiga.isoformat(), "6200", "48", "0"],
            [ARMOR_NOVA, ARMOR_NOME, recente.isoformat(), "6200", "48", ""],
        ]
        novas, relatorio = ferramenta.aplicar_nas_observacoes(
            linhas, {ARMOR_VELHA: ARMOR_NOVA}
        )
        assert len(novas) == 1
        assert relatorio.linhas_removidas == 1
        assert relatorio.linhas_reescritas == 1
        assert novas[0][0] == ARMOR_NOVA
        assert novas[0][2] == antiga.isoformat()
        # A linha sobrevivente sai INTEIRA, e nao costurada com a outra: o
        # residuo `"0"` e o da linha antiga, e nao o `""` da recente.
        assert novas[0][5] == "0"

    def test_a_sobrevivente_e_a_mais_antiga_mesmo_quando_ela_vem_depois(self):
        antiga = BASE
        recente = BASE + timedelta(days=2)
        linhas = [
            [ARMOR_NOVA, ARMOR_NOME, recente.isoformat(), "6200", "48", ""],
            [ARMOR_VELHA, ARMOR_NOME, antiga.isoformat(), "6200", "48", "7"],
        ]
        novas, _ = ferramenta.aplicar_nas_observacoes(
            linhas, {ARMOR_VELHA: ARMOR_NOVA}
        )
        assert len(novas) == 1
        assert novas[0][2] == antiga.isoformat()
        assert novas[0][5] == "7"

    def test_a_ordem_do_arquivo_sobrevive_a_fusao(self):
        linhas = [
            ["outra#", "Outra", BASE.isoformat(), "100", "1", ""],
            [ARMOR_VELHA, ARMOR_NOME, BASE.isoformat(), "6200", "48", ""],
            ["terceira#", "Terceira", BASE.isoformat(), "300", "3", ""],
        ]
        novas, _ = ferramenta.aplicar_nas_observacoes(
            linhas, {ARMOR_VELHA: ARMOR_NOVA}
        )
        assert [campos[0] for campos in novas] == [
            "outra#",
            ARMOR_NOVA,
            "terceira#",
        ]

    def test_duplicata_que_ja_existia_sob_uma_chave_so_e_preservada(self):
        """Decisao 2 do topo da ferramenta: ela so desfaz o que a fusao criou."""
        linhas = [
            [ARMOR_NOVA, ARMOR_NOME, BASE.isoformat(), "6200", "48", ""],
            [ARMOR_NOVA, ARMOR_NOME, BASE.isoformat(), "6200", "48", ""],
        ]
        novas, relatorio = ferramenta.aplicar_nas_observacoes(linhas, {})
        assert len(novas) == 2
        assert relatorio.linhas_removidas == 0
        assert relatorio.duplicatas_preexistentes == 1

    def test_linha_que_nao_valida_recusa_o_arquivo_inteiro_e_nomeia_a_linha(self):
        linhas = [
            [ARMOR_VELHA, ARMOR_NOME, BASE.isoformat(), "6200", "48", ""],
            [ARMOR_VELHA, ARMOR_NOME, "nao-e-iso", "6200", "48", ""],
        ]
        with pytest.raises(ferramenta.LinhaQueNaoValida) as erro:
            ferramenta.aplicar_nas_observacoes(linhas, {ARMOR_VELHA: ARMOR_NOVA})
        assert "linha 3" in str(erro.value)
        assert "ISO" in str(erro.value)

    def test_totais_diferentes_sob_a_mesma_chave_nao_sao_duplicata(self):
        linhas = [
            [ARMOR_VELHA, ARMOR_NOME, BASE.isoformat(), "6200", "48", ""],
            [ARMOR_NOVA, ARMOR_NOME, BASE.isoformat(), "6300", "48", ""],
        ]
        novas, relatorio = ferramenta.aplicar_nas_observacoes(
            linhas, {ARMOR_VELHA: ARMOR_NOVA}
        )
        assert len(novas) == 2
        assert relatorio.linhas_removidas == 0


class TestOCatalogo:
    def test_avistamentos_somam_e_as_pontas_do_tempo_se_esticam(self):
        linhas = [
            _linha_de_catalogo(
                ARMOR_VELHA, ARMOR_NOME, BASE, BASE + timedelta(days=1), 280
            ).split(";"),
            _linha_de_catalogo(
                ARMOR_NOVA,
                ARMOR_NOME,
                BASE + timedelta(days=2),
                BASE + timedelta(days=3),
                5,
            ).split(";"),
        ]
        novas, relatorio = ferramenta.aplicar_no_catalogo(
            linhas, {ARMOR_VELHA: ARMOR_NOVA}
        )
        assert len(novas) == 1
        assert relatorio.linhas_removidas == 1
        assert relatorio.destinos_atualizados == 1
        chave, nome, primeira, ultima, avistamentos = novas[0]
        assert chave == ARMOR_NOVA
        assert nome == ARMOR_NOME
        assert primeira == BASE.isoformat()
        assert ultima == (BASE + timedelta(days=3)).isoformat()
        assert avistamentos == "285"

    def test_a_serie_nao_envolvida_sai_com_os_campos_que_entrou(self):
        intacta = _linha_de_catalogo(
            "outra#", "Outra", BASE, BASE + timedelta(days=1), 3
        ).split(";")
        novas, _ = ferramenta.aplicar_no_catalogo([intacta], {})
        assert novas == [intacta]

    def test_linha_de_catalogo_que_nao_valida_recusa_o_arquivo_inteiro(self):
        ruim = [ARMOR_NOVA, ARMOR_NOME, BASE.isoformat(), BASE.isoformat(), "x"]
        with pytest.raises(ferramenta.LinhaQueNaoValida) as erro:
            ferramenta.aplicar_no_catalogo([ruim], {})
        assert "linha 2" in str(erro.value)


class TestOContratoDaSaida:
    def test_o_cabecalho_sai_byte_a_byte_igual_ao_que_entrou(self, tmp_path):
        escrever_observacoes(
            tmp_path,
            [
                _linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48),
                _linha_de_observacao(
                    ARMOR_NOVA, ARMOR_NOME, BASE + timedelta(days=1), 6300, 48
                ),
            ],
        )
        escrever_catalogo(
            tmp_path,
            [
                _linha_de_catalogo(ARMOR_VELHA, ARMOR_NOME, BASE, BASE, 15),
                _linha_de_catalogo(ARMOR_NOVA, ARMOR_NOME, BASE, BASE, 5),
            ],
        )
        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0

        for nome, cabecalho in (
            (ARQUIVO_DE_OBSERVACOES, CABECALHO_DE_OBSERVACOES),
            (ARQUIVO_DO_CATALOGO, CABECALHO_DO_CATALOGO),
        ):
            bruto = (tmp_path / nome).read_bytes().decode("utf-8")
            assert bruto.startswith(cabecalho), nome

    def test_o_arquivo_escrito_termina_em_quebra_de_linha(self, tmp_path):
        escrever_observacoes(
            tmp_path,
            [_linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48)],
        )
        escrever_catalogo(
            tmp_path,
            [
                _linha_de_catalogo(ARMOR_VELHA, ARMOR_NOME, BASE, BASE, 15),
                _linha_de_catalogo(ARMOR_NOVA, ARMOR_NOME, BASE, BASE, 5),
            ],
        )
        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0
        for nome in (ARQUIVO_DE_OBSERVACOES, ARQUIVO_DO_CATALOGO):
            assert (tmp_path / nome).read_bytes().endswith(b"\n"), nome

    def test_o_terminador_do_arquivo_de_entrada_e_respeitado(self, tmp_path):
        """Arquivo salvo com `\\n` volta com `\\n`, e nao com as duas convencoes."""
        escrever_observacoes(
            tmp_path,
            [
                _linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48),
                _linha_de_observacao(
                    ARMOR_NOVA, ARMOR_NOME, BASE + timedelta(days=1), 6300, 48
                ),
            ],
            cabecalho=CABECALHO_DE_OBSERVACOES.replace("\r\n", "\n"),
        )
        escrever_catalogo(
            tmp_path,
            [
                _linha_de_catalogo(ARMOR_VELHA, ARMOR_NOME, BASE, BASE, 15),
                _linha_de_catalogo(ARMOR_NOVA, ARMOR_NOME, BASE, BASE, 5),
            ],
            cabecalho=CABECALHO_DO_CATALOGO.replace("\r\n", "\n"),
        )
        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0
        bruto = (tmp_path / ARQUIVO_DE_OBSERVACOES).read_bytes()
        assert b"\r\n" not in bruto

    def test_observacoes_sem_quebra_final_recusa_tudo_e_nao_escreve(self, tmp_path):
        arquivo = escrever_observacoes(
            tmp_path,
            [_linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48)],
        )
        with arquivo.open("r", encoding="utf-8", newline="") as fonte:
            bruto = fonte.read()
        with arquivo.open("w", encoding="utf-8", newline="") as destino:
            destino.write(bruto.rstrip("\r\n"))
        antes = arquivo.read_bytes()
        escrever_catalogo(
            tmp_path,
            [
                _linha_de_catalogo(ARMOR_VELHA, ARMOR_NOME, BASE, BASE, 15),
                _linha_de_catalogo(ARMOR_NOVA, ARMOR_NOME, BASE, BASE, 5),
            ],
        )
        assert (
            ferramenta.main(["--pasta", str(tmp_path), "--gravar"])
            == ferramenta.SAIDA_CONTRATO_QUEBRADO
        )
        assert arquivo.read_bytes() == antes
        assert list(tmp_path.glob("*.bak")) == []

    def test_catalogo_sem_cabecalho_recusa_tudo_e_nao_escreve(self, tmp_path):
        obs = escrever_observacoes(
            tmp_path,
            [_linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48)],
        )
        antes = obs.read_bytes()
        escrever_catalogo(
            tmp_path,
            [_linha_de_catalogo(ARMOR_NOVA, ARMOR_NOME, BASE, BASE, 5)],
            cabecalho="",
        )
        assert (
            ferramenta.main(["--pasta", str(tmp_path), "--gravar"])
            == ferramenta.SAIDA_CONTRATO_QUEBRADO
        )
        assert obs.read_bytes() == antes
        assert list(tmp_path.glob("*.bak")) == []

    def test_uma_linha_ruim_impede_a_escrita_dos_DOIS_arquivos(self, tmp_path):
        """Decisao 3 do topo: ou os dois, ou nenhum."""
        obs = escrever_observacoes(
            tmp_path,
            [
                _linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48),
                ARMOR_NOVA + ";" + ARMOR_NOME + ";nao-e-iso;6300;48;",
            ],
        )
        cat = escrever_catalogo(
            tmp_path,
            [
                _linha_de_catalogo(ARMOR_VELHA, ARMOR_NOME, BASE, BASE, 15),
                _linha_de_catalogo(ARMOR_NOVA, ARMOR_NOME, BASE, BASE, 5),
            ],
        )
        antes_obs, antes_cat = obs.read_bytes(), cat.read_bytes()
        assert (
            ferramenta.main(["--pasta", str(tmp_path), "--gravar"])
            == ferramenta.SAIDA_CONTRATO_QUEBRADO
        )
        assert obs.read_bytes() == antes_obs
        assert cat.read_bytes() == antes_cat
        assert list(tmp_path.glob("*.bak")) == []


class TestODryRun:
    def test_sem_gravar_nem_um_byte_nem_um_mtime_mudam(self, tmp_path, capsys):
        obs = escrever_observacoes(
            tmp_path,
            [
                _linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48),
                _linha_de_observacao(
                    ARMOR_NOVA, ARMOR_NOME, BASE + timedelta(days=1), 6200, 48
                ),
            ],
        )
        cat = escrever_catalogo(
            tmp_path,
            [
                _linha_de_catalogo(ARMOR_VELHA, ARMOR_NOME, BASE, BASE, 15),
                _linha_de_catalogo(ARMOR_NOVA, ARMOR_NOME, BASE, BASE, 5),
            ],
        )
        antes = {
            caminho: (caminho.read_bytes(), caminho.stat().st_mtime_ns)
            for caminho in (obs, cat)
        }

        assert ferramenta.main(["--pasta", str(tmp_path)]) == 0

        for caminho, (bytes_antes, mtime_antes) in antes.items():
            assert caminho.read_bytes() == bytes_antes, caminho.name
            assert caminho.stat().st_mtime_ns == mtime_antes, caminho.name
        assert sorted(p.name for p in tmp_path.iterdir()) == sorted(
            [ARQUIVO_DE_OBSERVACOES, ARQUIVO_DO_CATALOGO]
        )
        saida = capsys.readouterr().out
        assert "nada gravado" in saida
        assert "--gravar" in saida

    def test_o_dry_run_ja_mostra_a_fusao_que_faria(self, tmp_path, capsys):
        escrever_observacoes(
            tmp_path,
            [_linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48)],
        )
        escrever_catalogo(
            tmp_path,
            [
                _linha_de_catalogo(ARMOR_VELHA, ARMOR_NOME, BASE, BASE, 15),
                _linha_de_catalogo(ARMOR_NOVA, ARMOR_NOME, BASE, BASE, 5),
            ],
        )
        assert ferramenta.main(["--pasta", str(tmp_path)]) == 0
        saida = capsys.readouterr().out
        assert "FUNDE" in saida
        assert ARMOR_NOVA in saida and ARMOR_VELHA in saida


class TestAGravacao:
    def test_o_backup_e_byte_a_byte_o_arquivo_de_antes(self, tmp_path):
        obs = escrever_observacoes(
            tmp_path,
            [
                _linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48),
                _linha_de_observacao(
                    ARMOR_NOVA, ARMOR_NOME, BASE + timedelta(days=1), 6200, 48
                ),
            ],
        )
        cat = escrever_catalogo(
            tmp_path,
            [
                _linha_de_catalogo(ARMOR_VELHA, ARMOR_NOME, BASE, BASE, 15),
                _linha_de_catalogo(ARMOR_NOVA, ARMOR_NOME, BASE, BASE, 5),
            ],
        )
        antes_obs, antes_cat = obs.read_bytes(), cat.read_bytes()

        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0

        backups = sorted(p.name for p in tmp_path.glob("*.antes-da-fusao-*.bak"))
        assert len(backups) == 2
        (backup_obs,) = tmp_path.glob(ARQUIVO_DE_OBSERVACOES + ".antes-da-fusao-*")
        (backup_cat,) = tmp_path.glob(ARQUIVO_DO_CATALOGO + ".antes-da-fusao-*")
        assert backup_obs.read_bytes() == antes_obs
        assert backup_cat.read_bytes() == antes_cat
        assert obs.read_bytes() != antes_obs

    def test_backup_existente_para_a_ferramenta_e_nao_e_sobrescrito(self, tmp_path):
        obs = escrever_observacoes(
            tmp_path,
            [_linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48)],
        )
        backup = ferramenta.caminho_do_backup(obs, "20260901-031500")
        backup.write_bytes(b"um backup anterior que nao pode sumir\n")
        with pytest.raises(FileExistsError):
            ferramenta.gravar(obs, "seja o que for\n", "20260901-031500")
        assert backup.read_bytes() == b"um backup anterior que nao pode sumir\n"

    def test_a_escrita_nao_deixa_temporario_para_tras(self, tmp_path):
        escrever_observacoes(
            tmp_path,
            [_linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48)],
        )
        escrever_catalogo(
            tmp_path,
            [
                _linha_de_catalogo(ARMOR_VELHA, ARMOR_NOME, BASE, BASE, 15),
                _linha_de_catalogo(ARMOR_NOVA, ARMOR_NOME, BASE, BASE, 5),
            ],
        )
        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0
        assert list(tmp_path.glob("*.tmp-*")) == []

    def test_rodar_de_novo_depois_da_fusao_nao_encontra_nada_a_fazer(self, tmp_path):
        escrever_observacoes(
            tmp_path,
            [
                _linha_de_observacao(ARMOR_VELHA, ARMOR_NOME, BASE, 6200, 48),
                _linha_de_observacao(
                    ARMOR_NOVA, ARMOR_NOME, BASE + timedelta(days=1), 6300, 48
                ),
            ],
        )
        escrever_catalogo(
            tmp_path,
            [
                _linha_de_catalogo(ARMOR_VELHA, ARMOR_NOME, BASE, BASE, 15),
                _linha_de_catalogo(ARMOR_NOVA, ARMOR_NOME, BASE, BASE, 5),
            ],
        )
        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0
        depois = (tmp_path / ARQUIVO_DE_OBSERVACOES).read_bytes()
        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0
        assert (tmp_path / ARQUIVO_DE_OBSERVACOES).read_bytes() == depois

    def test_pasta_inexistente_sai_com_codigo_proprio_e_nao_cria_nada(self, tmp_path):
        alvo = tmp_path / "nao-existe"
        assert (
            ferramenta.main(["--pasta", str(alvo), "--gravar"])
            == ferramenta.SAIDA_SEM_PASTA
        )
        assert not alvo.exists()


class TestOArquivoDoUsuario:
    """Os numeros da simulacao sobre o arquivo real: 61 -> 51, 10 duplicatas.

    A FIXTURA E EQUIVALENTE, NAO E O ARQUIVO DELE. O `.mercado/` do usuario e
    dado real e esta suite nunca o abre. O que se afirma aqui e que a ferramenta,
    sobre um arquivo com a MESMA forma (2 itens partidos, 15+5 e 5+5, com as 10
    ofertas repetidas sob as duas chaves), produz exatamente os numeros que a
    simulacao previu.
    """

    def _montar(self, pasta: Path):
        linhas = []
        # As 15 linhas da chave VELHA do armor. As 5 primeiras sao as ofertas
        # que tambem foram gravadas sob a chave nova.
        for i in range(15):
            linhas.append(
                _linha_de_observacao(
                    ARMOR_VELHA, ARMOR_NOME, BASE + timedelta(minutes=i),
                    6200 + i, 48
                )
            )
        # As 5 da chave VELHA do weapon, tambem repetidas sob a nova.
        for i in range(5):
            linhas.append(
                _linha_de_observacao(
                    WEAPON_VELHA, WEAPON_NOME, BASE + timedelta(minutes=100 + i),
                    900 + i, 12
                )
            )
        # 31 linhas de itens que a fusao nao toca.
        for i in range(31):
            linhas.append(
                _linha_de_observacao(
                    "item-" + str(i) + "#", "Item " + str(i),
                    BASE + timedelta(minutes=200 + i), 1000 + i, 1
                )
            )
        # As 5 da chave NOVA do armor: mesma serie, total e quantidade das 5
        # primeiras da velha -> 5 duplicatas reais. Carimbo MAIS RECENTE.
        for i in range(5):
            linhas.append(
                _linha_de_observacao(
                    ARMOR_NOVA, ARMOR_NOME, BASE + timedelta(days=2, minutes=i),
                    6200 + i, 48
                )
            )
        # As 5 da chave NOVA do weapon -> outras 5 duplicatas reais.
        for i in range(5):
            linhas.append(
                _linha_de_observacao(
                    WEAPON_NOVA, WEAPON_NOME,
                    BASE + timedelta(days=2, minutes=100 + i), 900 + i, 12
                )
            )
        assert len(linhas) == 61
        escrever_observacoes(pasta, linhas)
        escrever_catalogo(
            pasta,
            [
                _linha_de_catalogo(ARMOR_VELHA, ARMOR_NOME, BASE, BASE, 280),
                _linha_de_catalogo(
                    ARMOR_NOVA, ARMOR_NOME, BASE + timedelta(days=2),
                    BASE + timedelta(days=2), 5
                ),
                _linha_de_catalogo(WEAPON_VELHA, WEAPON_NOME, BASE, BASE, 40),
                _linha_de_catalogo(
                    WEAPON_NOVA, WEAPON_NOME, BASE + timedelta(days=2),
                    BASE + timedelta(days=2), 5
                ),
            ],
        )

    def test_sessenta_e_uma_linhas_viram_cinquenta_e_uma(self, tmp_path, capsys):
        self._montar(tmp_path)
        assert len(ler_linhas(tmp_path / ARQUIVO_DE_OBSERVACOES)) == 61

        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0

        depois = ler_linhas(tmp_path / ARQUIVO_DE_OBSERVACOES)
        assert len(depois) == 51
        saida = capsys.readouterr().out
        assert "duplicatas desfeitas  : 10" in saida
        assert "chaves reescritas     : 20" in saida

    def test_as_vinte_observacoes_do_armor_ficam_todas_sob_a_chave_nova(
        self, tmp_path
    ):
        self._montar(tmp_path)
        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0
        depois = ler_linhas(tmp_path / ARQUIVO_DE_OBSERVACOES)
        chaves = [linha.split(";")[0] for linha in depois]
        assert chaves.count(ARMOR_NOVA) == 15
        assert chaves.count(ARMOR_VELHA) == 0
        assert chaves.count(WEAPON_NOVA) == 5
        assert chaves.count(WEAPON_VELHA) == 0

    def test_a_sobrevivente_de_cada_duplicata_e_a_de_carimbo_mais_antigo(
        self, tmp_path
    ):
        self._montar(tmp_path)
        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0
        depois = ler_linhas(tmp_path / ARQUIVO_DE_OBSERVACOES)
        carimbos = {
            linha.split(";")[2]
            for linha in depois
            if linha.split(";")[0] == ARMOR_NOVA
        }
        recentes = {
            (BASE + timedelta(days=2, minutes=i)).isoformat() for i in range(5)
        }
        assert carimbos & recentes == set()

    def test_o_catalogo_fica_com_duas_series_e_a_soma_dos_avistamentos(
        self, tmp_path
    ):
        self._montar(tmp_path)
        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0
        linhas = ler_linhas(tmp_path / ARQUIVO_DO_CATALOGO)
        assert len(linhas) == 2
        por_chave = {linha.split(";")[0]: linha.split(";") for linha in linhas}
        assert set(por_chave) == {ARMOR_NOVA, WEAPON_NOVA}
        assert por_chave[ARMOR_NOVA][4] == "285"
        assert por_chave[WEAPON_NOVA][4] == "45"
        assert por_chave[ARMOR_NOVA][2] == BASE.isoformat()
        assert por_chave[ARMOR_NOVA][3] == (BASE + timedelta(days=2)).isoformat()

    def test_as_trinta_e_uma_linhas_alheias_saem_identicas(self, tmp_path):
        self._montar(tmp_path)
        antes = [
            linha
            for linha in ler_linhas(tmp_path / ARQUIVO_DE_OBSERVACOES)
            if linha.startswith("item-")
        ]
        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0
        depois = [
            linha
            for linha in ler_linhas(tmp_path / ARQUIVO_DE_OBSERVACOES)
            if linha.startswith("item-")
        ]
        assert depois == antes
        assert len(depois) == 31

    def test_o_arquivo_fundido_ainda_atravessa_o_portao_do_leitor(self, tmp_path):
        """A prova mais forte: o registro de producao le o que a ferramenta escreveu."""
        from l2scanner.mercado_registro import observacoes_do_arquivo

        self._montar(tmp_path)
        assert ferramenta.main(["--pasta", str(tmp_path), "--gravar"]) == 0
        lidas = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)
        assert len(lidas) == 51
        assert sum(1 for o in lidas if o.chave_da_serie == ARMOR_NOVA) == 15


class TestOMercadoDeProducao:
    def test_o_padrao_do_argumento_e_a_pasta_de_producao(self):
        """O comando do usuario e `--gravar` e mais nada; o padrao ja aponta certo.

        O analisador vem da FERRAMENTA, e nao remontado aqui: um teste que
        remontasse o `add_argument` afirmaria a si mesmo, e o padrao poderia
        mudar la sem ninguem perceber.
        """
        opcoes = ferramenta.construir_analisador().parse_args([])
        assert opcoes.pasta == str(PASTA_DO_MERCADO)
        assert opcoes.gravar is False, (
            "o padrao TEM de ser dry-run: um `--gravar` implicito reescreveria o "
            "CSV do usuario para quem so digitou o nome da ferramenta"
        )

    def test_a_guarda_desta_suite_enxerga_uma_escrita_no_mercado(self, tmp_path):
        """A fixtura que protege o `.mercado/` nao pode ser decorativa.

        Aqui a guarda e exercitada contra uma pasta de MENTIRA em `tmp_path`, com
        a mesma funcao de instantaneo. Se `_instantaneo_do_mercado` fosse cega, o
        `assert` abaixo falharia — e e ele que sustenta a promessa do topo.
        """
        falso = tmp_path / "mercado"
        falso.mkdir()
        (falso / "observacoes.csv").write_bytes(b"a\n")

        def instantaneo():
            return sorted(
                (
                    str(p.relative_to(falso)),
                    p.stat().st_size,
                    p.stat().st_mtime_ns,
                )
                for p in falso.rglob("*")
                if p.is_file()
            )

        antes = instantaneo()
        (falso / "observacoes.csv").write_bytes(b"bb\n")
        assert instantaneo() != antes

    def test_a_excecao_de_contrato_e_a_do_modulo_de_producao(self):
        """A ferramenta nao inventa uma excecao paralela para o mesmo assunto."""
        assert ferramenta.ContratoDoArquivoQuebrado is ContratoDoArquivoQuebrado


class TestOTextoQueVaiParaOConsole:
    """Todo texto de EXECUCAO e ASCII. Docstring pode ter tracinho longo; frase
    impressa nao pode.

    O console do Windows abre em cp1252, e a mesma frase acaba colada num log,
    numa mensagem de erro e num editor qualquer. A regra ja esta escrita em
    `mercado_registro.TEXTO_DO_LEIAME`; aqui ela vira teste, porque um travessao
    num motivo de recusa sai como `?` bem na hora em que o usuario precisa
    entender por que a ferramenta nao fundiu.
    """

    def test_nenhuma_string_de_execucao_da_ferramenta_sai_do_ascii(self):
        import ast

        caminho = RAIZ / "tools" / "fundir_chaves_de_serie.py"
        with caminho.open("r", encoding="utf-8", newline="") as fonte:
            arvore = ast.parse(fonte.read())

        docstrings = {
            no.body[0].value.lineno
            for no in ast.walk(arvore)
            if isinstance(
                no,
                (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            )
            and ast.get_docstring(no, clean=False) is not None
        }

        fora_do_ascii = [
            (no.lineno, no.value)
            for no in ast.walk(arvore)
            if isinstance(no, ast.Constant)
            and isinstance(no.value, str)
            and no.lineno not in docstrings
            and any(not c.isascii() for c in no.value)
        ]
        assert fora_do_ascii == [], (
            "texto de execucao fora do ASCII: o console do Windows abre em "
            "cp1252 e essas frases sairiam com `?` no lugar do caractere. "
            + repr(fora_do_ascii)
        )

    def test_o_motivo_de_uma_recusa_real_e_legivel_em_cp1252(self):
        plano = ferramenta.planejar(
            {"gemstone#": "Gemstone",
             "gemstone#B": "Gemstone",
             "gemstone#C": "Gemstone"}
        )
        (recusa,) = plano.recusas
        # `encode` estrito: se algum caractere nao couber em cp1252 isto levanta.
        recusa.motivo.encode("cp1252")
