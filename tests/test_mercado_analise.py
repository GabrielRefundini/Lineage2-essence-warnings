"""A leitura tipada do `observacoes.csv` e a estatistica honesta sobre ela.

NADA AQUI TOCA A `.mercado/` REAL, e nada aqui monta frame. Os arquivos nascem
em `tmp_path` e a analise recebe listas montadas a mao — e o que permite a suite
inteira rodar no Python global, sem WinRT e sem material gravado.

O FATO QUE GOVERNA TODOS ESTES TESTES
======================================
Uma linha do CSV NAO e "o preco as 14:32": e "esta oferta especifica — este
item, este total, esta quantidade — foi vista pela PRIMEIRA vez as 14:32". A
chave de dedup da Fase 3 e `(chave_da_serie, total_em_centesimos, quantidade)`,
SEM tempo (`mercado_registro.py:149-166`). Logo nao existe serie temporal de
preco: existe uma sequencia de OFERTAS DISTINTAS ordenada pela primeira vez que
cada uma apareceu. Toda a aritmetica exercitada aqui respeita isso.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pytest

from l2scanner.mercado_catalogo import SEPARADOR
from l2scanner.mercado_registro import (
    ARQUIVO_DE_OBSERVACOES,
    COLUNAS,
    ContratoDoArquivoQuebrado,
    ObservacaoLida,
    observacoes_do_arquivo,
)

LOGGER = "l2scanner.mercado_registro"

# Ingenuos, hora local, sem `tzinfo` — e o que `Relogio.agora()` devolve
# (`l2scanner/relogio.py:156-163`) e o que `campos_da_observacao` escreve com
# `.isoformat()`. Cobrar fuso aqui cobraria um formato que a producao nunca
# produz.
AGORA = datetime(2026, 8, 30, 21, 15, 0)


# ===========================================================================
# TASK 1 — `observacoes_do_arquivo`, pelo portao de contrato que ja existe
# ===========================================================================


def _linha_crua(
    *,
    chave: str = "common-aztac#0",
    nome: str = "Common Aztac",
    carimbo: datetime = AGORA,
    total: int = 6200,
    quantidade: int = 48,
    residuo: str = "0",
) -> str:
    return SEPARADOR.join(
        (chave, nome, carimbo.isoformat(), str(total), str(quantidade), residuo)
    )


def _fabricar(pasta: Path, *linhas: str, terminador: str = "\r\n") -> Path:
    """Escreve um CSV com cabecalho e as linhas dadas. Bytes exatos.

    O terminador e `\\r\\n` porque e o que `csv.writer` com `newline=""` emite
    no Windows, que e o arquivo que a producao produz.
    """
    alvo = pasta / ARQUIVO_DE_OBSERVACOES
    corpo = terminador.join((SEPARADOR.join(COLUNAS), *linhas)) + terminador
    alvo.write_bytes(corpo.encode("utf-8"))
    return alvo


class TestAsLinhasParseadasVoltamTIPADAS:
    """Tres linhas boas viram tres registros, com os tipos que a analise usa."""

    def test_tres_linhas_boas_devolvem_TRES_registros(self, tmp_path):
        _fabricar(
            tmp_path,
            _linha_crua(total=6200, quantidade=48),
            _linha_crua(total=4500, quantidade=100),
            _linha_crua(total=1000, quantidade=1),
        )
        itens = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)
        assert len(itens) == 3

    def test_os_numeros_voltam_INTEIROS_e_o_carimbo_volta_DATETIME(self, tmp_path):
        """O tipo e o contrato: a analise faz `Fraction(total, quantidade)`, e
        `Fraction` de string nao e a mesma coisa que `Fraction` de inteiro."""
        _fabricar(tmp_path, _linha_crua())
        itens = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)
        assert type(itens[0].total_em_centesimos) is int
        assert type(itens[0].quantidade) is int
        assert type(itens[0].primeira_vez) is datetime

    def test_os_campos_de_texto_voltam_INTEIROS_de_conteudo(self, tmp_path):
        _fabricar(tmp_path, _linha_crua(chave="k#1", nome="Common Aztac"))
        (item,) = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)
        assert item.chave_da_serie == "k#1"
        assert item.nome_exibido == "Common Aztac"
        assert item.primeira_vez == AGORA

    def test_o_registro_e_FROZEN(self, tmp_path):
        """Ninguem reescreve uma observacao lida do disco depois de le-la."""
        _fabricar(tmp_path, _linha_crua())
        (item,) = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)
        with pytest.raises(Exception):
            item.total_em_centesimos = 1  # type: ignore[misc]


class TestOPortaoDeContratoEOMESMO:
    """Uma verdade so sobre o que o arquivo e — nunca um parser novo.

    Duas implementacoes divergentes de leitura do mesmo arquivo reintroduziriam
    exatamente a truncagem parseavel que a Fase 3 gastou um plano inteiro para
    pegar: `80` virando `8` passa na contagem de campos e na validacao por tipo,
    e SO o terminador a pega.
    """

    def test_sem_quebra_de_linha_final_LEVANTA(self, tmp_path):
        alvo = _fabricar(tmp_path, _linha_crua())
        bruto = alvo.read_bytes()
        assert bruto.endswith(b"\n")
        alvo.write_bytes(bruto[:-1])
        with pytest.raises(ContratoDoArquivoQuebrado):
            observacoes_do_arquivo(alvo)

    def test_o_ultimo_byte_cortado_deixa_seis_campos_PARSEAVEIS_e_ainda_LEVANTA(
        self, tmp_path
    ):
        """O corte medido: `...;48;80\\r\\n` truncado vira `...;48;8` — seis
        campos, todos validos, residuo de 8 onde o disco dizia 80."""
        alvo = _fabricar(tmp_path, _linha_crua(residuo="80"))
        alvo.write_bytes(alvo.read_bytes()[:-3])  # tira `0\r\n`
        with pytest.raises(ContratoDoArquivoQuebrado):
            observacoes_do_arquivo(alvo)

    def test_cabecalho_divergente_LEVANTA(self, tmp_path):
        alvo = _fabricar(tmp_path, _linha_crua())
        texto = alvo.read_text(encoding="utf-8")
        trocado = texto.replace("total_em_centesimos", "total", 1)
        alvo.write_bytes(trocado.encode("utf-8"))
        with pytest.raises(ContratoDoArquivoQuebrado):
            observacoes_do_arquivo(alvo)

    def test_arquivo_AUSENTE_devolve_lista_vazia_sem_levantar(self, tmp_path):
        """A `.mercado/` nasce vazia e a analise tem de dizer 'sem evidencia',
        nao explodir."""
        assert observacoes_do_arquivo(tmp_path / "nao-existe.csv") == []

    def test_a_leitura_NAO_CRIA_o_arquivo_ausente(self, tmp_path):
        alvo = tmp_path / "nao-existe.csv"
        observacoes_do_arquivo(alvo)
        assert not alvo.exists()

    def test_arquivo_de_ZERO_BYTES_devolve_lista_vazia(self, tmp_path):
        alvo = tmp_path / ARQUIVO_DE_OBSERVACOES
        alvo.write_bytes(b"")
        assert observacoes_do_arquivo(alvo) == []

    def test_so_o_cabecalho_devolve_lista_vazia(self, tmp_path):
        alvo = _fabricar(tmp_path)
        assert observacoes_do_arquivo(alvo) == []


class TestUmaLinhaRuimCaiSOZINHA:
    """Passado o portao, linha ruim nunca condena o arquivo (D-14)."""

    def test_contagem_de_campos_errada_e_DESCARTADA_e_as_demais_continuam(
        self, tmp_path, caplog
    ):
        alvo = _fabricar(
            tmp_path,
            _linha_crua(total=6200),
            "so;tres;campos",
            _linha_crua(total=4500),
        )
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            itens = observacoes_do_arquivo(alvo)
        assert len(itens) == 2
        assert [i.total_em_centesimos for i in itens] == [6200, 4500]

    def test_o_aviso_NOMEIA_o_numero_da_linha(self, tmp_path, caplog):
        """A forense deste projeto acontece depois do farm, com o log na mao:
        'linha descartada' sem o numero nao conserta nada."""
        alvo = _fabricar(
            tmp_path,
            _linha_crua(),
            "so;tres;campos",
        )
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            observacoes_do_arquivo(alvo)
        avisos = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert avisos, "a linha ruim tem de produzir aviso"
        assert any("3" in r.getMessage() for r in avisos), [
            r.getMessage() for r in avisos
        ]

    def test_carimbo_que_nao_e_ISO_tambem_CAI_sozinho(self, tmp_path, caplog):
        alvo = _fabricar(
            tmp_path,
            SEPARADOR.join(("k#1", "Nome", "ontem de tarde", "6200", "48", "")),
            _linha_crua(),
        )
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            itens = observacoes_do_arquivo(alvo)
        assert len(itens) == 1


class TestOResiduoQueNaoColapsa:
    """`None` e `0` sao fatos DIFERENTES e nao podem colapsar (D-01).

    `None` e "alguma das tres celulas nao leu, entao nao houve conferencia" e
    `0` e "conferi a aritmetica e ela bateu na casa do centesimo".
    """

    def test_vazio_volta_None_e_zero_volta_zero(self, tmp_path):
        alvo = _fabricar(
            tmp_path,
            _linha_crua(total=6200, residuo=""),
            _linha_crua(total=4500, residuo="0"),
        )
        vazio, zero = observacoes_do_arquivo(alvo)
        assert vazio.residuo_do_cruzamento is None
        assert zero.residuo_do_cruzamento == 0

    def test_um_residuo_medido_sobrevive_a_leitura(self, tmp_path):
        alvo = _fabricar(tmp_path, _linha_crua(residuo="80"))
        (item,) = observacoes_do_arquivo(alvo)
        assert item.residuo_do_cruzamento == 80


class TestAExtracaoEREFACTOR_PURO:
    """Os metodos do registro e a leitura nova chamam a MESMA funcao."""

    def test_o_registro_delega_o_terminador_a_funcao_de_modulo(self):
        import inspect

        from l2scanner import mercado_registro

        fonte = inspect.getsource(
            mercado_registro.RegistroDeObservacoes._conferir_o_terminador
        )
        assert "conferir_o_terminador(" in fonte

    def test_o_registro_delega_o_cabecalho_a_funcao_de_modulo(self):
        import inspect

        from l2scanner import mercado_registro

        fonte = inspect.getsource(
            mercado_registro.RegistroDeObservacoes._conferir_o_cabecalho
        )
        assert "conferir_o_cabecalho(" in fonte

    def test_a_leitura_nova_NAO_abre_o_arquivo_para_escrita(self):
        import inspect

        from l2scanner import mercado_registro

        fonte = inspect.getsource(mercado_registro.observacoes_do_arquivo)
        assert '"w"' not in fonte and '"a"' not in fonte
        assert "mkdir" not in fonte

    def test_ObservacaoLida_carrega_exatamente_as_COLUNAS(self):
        import dataclasses

        campos = tuple(f.name for f in dataclasses.fields(ObservacaoLida))
        assert campos == COLUNAS
