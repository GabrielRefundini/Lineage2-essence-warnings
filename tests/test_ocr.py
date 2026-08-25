"""O OCR do Windows, e a degradacao graciosa quando ele nao esta la.

ESTE ARQUIVO E A PROVA DE D-02. As bindings do WinRT sao MODULARES desde
set/2023 e simplesmente nao existem no Python que roda esta suite — so no
`.venv` do usuario. Isso nao e um problema a contornar: e o ambiente em que a
maior parte dos testes tem que valer.

O recurso de manutencao e opcional; o scanner nao e. Um `import winrt` no topo
de um modulo que o scanner sempre carrega derrubaria o produto INTEIRO para
quem nao rodou o `vigiar-party.bat` depois desta atualizacao — por causa de um
recurso que ele nem pediu.

Onde o resultado dependeria do ambiente, os testes FORCAM o estado com
`monkeypatch` em vez de torcer para a maquina estar do jeito certo.
"""

from __future__ import annotations

import numpy as np
import pytest

import l2scanner.ocr as ocr


@pytest.fixture(autouse=True)
def cache_limpo():
    """O motivo e calculado UMA vez e guardado — entao cada teste comeca zerado."""
    ocr._resetar_cache()
    yield
    ocr._resetar_cache()


def imagem():
    return np.zeros((20, 100, 3), dtype=np.uint8)


def sem_bindings(monkeypatch):
    """Forca o estado 'as bindings nao estao instaladas', em qualquer maquina."""
    monkeypatch.setattr(ocr, "_CHECADO", True)
    monkeypatch.setattr(ocr, "_MOTIVO", ocr.SEM_BINDINGS)


class TestImportarNuncaLevanta:
    def test_importar_o_modulo_funciona_com_ou_sem_as_bindings(self):
        """Sozinho, este teste ja e a prova de D-02.

        Ele passa nos DOIS ambientes: o Python da suite (sem bindings) e o
        `.venv` do usuario (com). Se o import do WinRT subisse para o topo do
        modulo, ele falharia aqui — e falharia no scanner do usuario junto.
        """
        import importlib

        importlib.reload(ocr)
        assert hasattr(ocr, "ler_texto")


class TestSemAsBindings:
    def test_ler_texto_devolve_none_e_nao_levanta(self, monkeypatch):
        sem_bindings(monkeypatch)
        assert ocr.ler_texto(imagem()) is None

    def test_o_motivo_diz_o_que_fazer(self, monkeypatch):
        """Um aviso que nao diz como consertar e ruido.

        O usuario nao e desenvolvedor: "OCR indisponivel" o deixa exatamente
        onde estava. "Rode o vigiar-party.bat" o tira de la.
        """
        sem_bindings(monkeypatch)
        motivo = ocr.motivo_indisponivel()
        assert motivo
        assert "vigiar-party.bat" in motivo or "requirements.txt" in motivo
        assert ocr.disponivel() is False


class TestEntradaDegenerada:
    @pytest.mark.parametrize(
        "entrada", [None, np.zeros((0, 0, 3), dtype=np.uint8)]
    )
    def test_nao_chega_perto_do_winrt(self, entrada, monkeypatch):
        """A guarda vem ANTES de qualquer chamada de plataforma.

        Forcamos o OCR como DISPONIVEL de proposito: sem a guarda, um recorte
        vazio viraria uma excecao la dentro do WinRT em vez de um None limpo.
        """
        monkeypatch.setattr(ocr, "_CHECADO", True)
        monkeypatch.setattr(ocr, "_MOTIVO", None)
        chamou = []
        monkeypatch.setattr(
            ocr, "_reconhecer", lambda _: chamou.append(1) or "nunca deveria"
        )

        assert ocr.ler_texto(entrada) is None
        assert chamou == []


class TestExcecaoDaPlataformaEEngolida:
    def test_ler_texto_engole_a_excecao(self, monkeypatch):
        """Esta funcao roda DENTRO do tick de captura.

        Uma excecao aqui pararia o scanner de olhar a party — e a proxima morte
        real passaria despercebida, que e o pior modo de falha do projeto.
        """
        monkeypatch.setattr(ocr, "_CHECADO", True)
        monkeypatch.setattr(ocr, "_MOTIVO", None)

        def explode(_pixels):
            raise RuntimeError("o WinRT nao esta feliz")

        monkeypatch.setattr(ocr, "_reconhecer", explode)

        assert ocr.ler_texto(imagem()) is None


class TestContratoDeTipo:
    def test_o_retorno_e_none_ou_str_no_ambiente_real(self):
        """Sem monkeypatch nenhum: vale no Python da suite E no `.venv`.

        E o teste que NAO mente sobre o que nao foi provado. A precisao do OCR
        na fonte do jogo so uma manutencao real prova — e e para isso que
        existe o `--testar-manutencao`.
        """
        resultado = ocr.ler_texto(imagem())
        assert resultado is None or isinstance(resultado, str)
