"""As chaves de mercado entram no calibration.json SEM invalidar o que existe.

A doutrina esta escrita em `calibracao.py:196-206` e vale literalmente aqui: o
`carregar` recusa qualquer versao diferente de `VERSAO_DO_ESQUEMA`, entao subir
para 3 por causa de campos OPCIONAIS obrigaria o usuario a recalibrar a mao um
arquivo que continua correto. As quatro chaves novas seguem o trilho do
`banner_manutencao` — campo `| None = None`, serializacao condicional no
`salvar`, `.get` no `carregar` — e este arquivo e o que prende isso.

O teste que mais importa e o do arquivo ANTIGO: `calibracao_de_referencia.json`
foi gravado antes desta funcionalidade existir e nao tem nenhuma chave de
mercado. Ele precisa carregar sem excecao e sem uma linha de migracao.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from l2scanner.calibracao import VERSAO_DO_ESQUEMA, Calibracao, CalibracaoInvalida
from l2scanner.frames import Regiao

FIXTURES = Path(__file__).parent / "fixtures"
REFERENCIA = FIXTURES / "calibracao_de_referencia.json"

# Um molde minusculo, so para o round-trip: 2x3 bytes crus em hex.
MOLDE_DE_BRINQUEDO = {"altura": 2, "largura": 3, "bytes": "0102030405f0"}

ANCORA_DE_BRINQUEDO = Regiao(esquerda=912, topo=350, largura=100, altura=28)
GEOMETRIA_DE_BRINQUEDO = {"janela_largura": 1720, "janela_altura": 1392}


@pytest.fixture
def cal_sem_mercado() -> Calibracao:
    return Calibracao.carregar(REFERENCIA)


class TestACalibracaoAntigaContinuaValendo:
    def test_a_versao_do_esquema_segue_em_2(self):
        """Subir a versao invalidaria a calibracao medida a mao do usuario.

        Se este teste cair, alguem trocou um campo opcional por uma migracao
        obrigatoria — e a conta dessa troca e o usuario recalibrar tudo.
        """
        assert VERSAO_DO_ESQUEMA == 2

    def test_um_arquivo_gravado_antes_desta_funcionalidade_carrega(self):
        """`calibracao_de_referencia.json` nao tem NENHUMA chave de mercado."""
        dados = json.loads(REFERENCIA.read_text(encoding="utf-8"))
        assert not [c for c in dados if c.startswith("mercado_")], (
            "a fixture de referencia ganhou chaves de mercado e deixou de "
            "provar o que ela existe para provar"
        )
        cal = Calibracao.carregar(REFERENCIA)  # nao pode levantar
        assert cal.versao == 2

    def test_sem_as_chaves_novas_os_quatro_campos_voltam_None(self, cal_sem_mercado):
        assert cal_sem_mercado.mercado_ancora is None
        assert cal_sem_mercado.mercado_molde_da_ancora is None
        assert cal_sem_mercado.mercado_limiar_da_ancora is None
        assert cal_sem_mercado.mercado_geometria_da_captura is None

    def test_salvar_e_recarregar_sem_mercado_nao_inventa_chave(
        self, cal_sem_mercado, tmp_path
    ):
        destino = tmp_path / "calibration.json"
        cal_sem_mercado.salvar(destino)
        devolvida = Calibracao.carregar(destino)
        assert devolvida.mercado_ancora is None
        assert devolvida.mercado_molde_da_ancora is None
        assert devolvida.mercado_limiar_da_ancora is None
        assert devolvida.mercado_geometria_da_captura is None


class TestORoundTripDasChavesNovas:
    def test_as_quatro_chaves_voltam_identicas(self, cal_sem_mercado, tmp_path):
        cal_sem_mercado.mercado_ancora = ANCORA_DE_BRINQUEDO
        cal_sem_mercado.mercado_molde_da_ancora = MOLDE_DE_BRINQUEDO
        cal_sem_mercado.mercado_limiar_da_ancora = 0.73
        cal_sem_mercado.mercado_geometria_da_captura = GEOMETRIA_DE_BRINQUEDO

        destino = tmp_path / "calibration.json"
        cal_sem_mercado.salvar(destino)
        devolvida = Calibracao.carregar(destino)

        assert devolvida.mercado_ancora == ANCORA_DE_BRINQUEDO
        assert devolvida.mercado_limiar_da_ancora == 0.73
        assert devolvida.mercado_geometria_da_captura == GEOMETRIA_DE_BRINQUEDO

    def test_o_molde_volta_byte_a_byte(self, cal_sem_mercado, tmp_path):
        """O hex e o dado; um round-trip que perde um byte perde a ancora."""
        cal_sem_mercado.mercado_molde_da_ancora = MOLDE_DE_BRINQUEDO
        destino = tmp_path / "calibration.json"
        cal_sem_mercado.salvar(destino)
        devolvida = Calibracao.carregar(destino)

        assert devolvida.mercado_molde_da_ancora == MOLDE_DE_BRINQUEDO
        assert devolvida.mercado_molde_da_ancora["bytes"] == "0102030405f0"

    def test_a_versao_gravada_continua_2_com_as_chaves_preenchidas(
        self, cal_sem_mercado, tmp_path
    ):
        cal_sem_mercado.mercado_ancora = ANCORA_DE_BRINQUEDO
        cal_sem_mercado.mercado_limiar_da_ancora = 0.73
        destino = tmp_path / "calibration.json"
        cal_sem_mercado.salvar(destino)

        dados = json.loads(destino.read_text(encoding="utf-8"))
        assert dados["versao"] == 2
        assert dados["mercado_ancora"] == ANCORA_DE_BRINQUEDO.como_dict()
        assert dados["mercado_limiar_da_ancora"] == 0.73

    def test_um_scanner_ANTIGO_recusaria_alto_e_nao_calado(self, tmp_path):
        """A recusa de versao continua sendo a defesa de entrada (T-02-02).

        Nao e sobre as chaves novas: e a garantia de que o trilho escolhido
        (campo opcional, versao congelada) nao afrouxou o portao que ja existia.
        """
        dados = json.loads(REFERENCIA.read_text(encoding="utf-8"))
        dados["versao"] = 3
        destino = tmp_path / "futuro.json"
        destino.write_text(json.dumps(dados), encoding="utf-8")

        with pytest.raises(CalibracaoInvalida, match="v3"):
            Calibracao.carregar(destino)


class TestAsChavesDeMercadoSaoENTRADA_NAO_CONFIAVEL:
    """O `calibration.json` e um arquivo que o proprio modulo chama de editavel.

    As tres chaves de mercado saiam de `dados.get(...)` direto para dentro da
    `Calibracao`, sem uma checagem de tipo ou de faixa. O `molde_de_hex` ja
    tratava o dict como entrada nao confiavel (`mercado_visao.py:151-159`) e a
    versao ja tinha portao (`T-02-02`); o LIMIAR nao tinha nada.

    A validacao mora no `carregar`, ao lado do portao de versao, porque e la
    que a mensagem ainda pode dizer "recalibre" com o usuario olhando para o
    console — e nao no meio do farm, as duas da manha, dentro de
    `mercado_aberto`.
    """

    def _com(self, tmp_path: Path, **chaves) -> Path:
        dados = json.loads(REFERENCIA.read_text(encoding="utf-8"))
        dados.update(chaves)
        destino = tmp_path / "mexido.json"
        destino.write_text(json.dumps(dados), encoding="utf-8")
        return destino

    @pytest.mark.parametrize("limiar", [0, 0.0, -1, -0.5, 1.5, 2])
    def test_limiar_fora_de_0_a_1_e_recusado_no_arranque(self, tmp_path, limiar):
        """Limiar <= 0 faz `mercado_aberto` devolver True para TODO recorte.

        O detector deixaria de detectar e passaria a afirmar — fail-open no
        modulo cujo charter inteiro e "um sinal de mercado nunca pode virar um
        segundo detector de morte".
        """
        caminho = self._com(tmp_path, mercado_limiar_da_ancora=limiar)
        with pytest.raises(CalibracaoInvalida, match="limiar|Recalibre"):
            Calibracao.carregar(caminho)

    @pytest.mark.parametrize("limiar", ["0.73", True, False, None, [], {}])
    def test_limiar_que_nao_e_numero_e_recusado_no_arranque(self, tmp_path, limiar):
        """`"0.73"` — numero entre aspas — e o deslize de edicao mais comum.

        Sem portao ele virava `TypeError: '>=' not supported between 'float'
        and 'str'` la dentro de `mercado_visao.mercado_aberto`, no meio do
        farm. `None` e o caso legitimo de "nao calibrado" e passa; os outros
        nao.
        """
        if limiar is None:
            Calibracao.carregar(self._com(tmp_path, mercado_limiar_da_ancora=None))
            return
        caminho = self._com(tmp_path, mercado_limiar_da_ancora=limiar)
        with pytest.raises(CalibracaoInvalida, match="limiar|numero|Recalibre"):
            Calibracao.carregar(caminho)

    @pytest.mark.parametrize("limiar", [0.73, 1, 1.0, 0.0001])
    def test_limiar_valido_passa(self, tmp_path, limiar):
        """Sem isto, recusar tudo deixaria os testes acima verdes."""
        cal = Calibracao.carregar(
            self._com(tmp_path, mercado_limiar_da_ancora=limiar)
        )
        assert cal.mercado_limiar_da_ancora == limiar

    @pytest.mark.parametrize("molde", [[1, 2, 3], "abc", 7, 0.5])
    def test_molde_que_nao_e_objeto_e_recusado_no_arranque(self, tmp_path, molde):
        """`[1, 2, 3]` virava `TypeError: list indices must be integers`."""
        caminho = self._com(tmp_path, mercado_molde_da_ancora=molde)
        with pytest.raises(CalibracaoInvalida, match="molde|Recalibre"):
            Calibracao.carregar(caminho)

    @pytest.mark.parametrize("geometria", [[1720, 1392], "1720x1392", 3])
    def test_geometria_que_nao_e_objeto_e_recusada_no_arranque(
        self, tmp_path, geometria
    ):
        caminho = self._com(tmp_path, mercado_geometria_da_captura=geometria)
        with pytest.raises(CalibracaoInvalida, match="geometria|Recalibre"):
            Calibracao.carregar(caminho)

    @pytest.mark.parametrize(
        "ancora",
        [
            {"esquerda": 912, "topo": 350, "largura": 0, "altura": 28},
            {"esquerda": 912, "topo": 350, "largura": 100, "altura": 0},
            {"esquerda": 912, "topo": 350, "largura": -100, "altura": -28},
        ],
    )
    def test_ancora_com_dimensao_nao_positiva_e_recusada(self, tmp_path, ancora):
        """Par do WR-04: este retangulo e a conferencia da forma do molde.

        `Regiao.de_dict` aceita largura e altura <= 0 (e faz bem: `esquerda` e
        `topo` PRECISAM aceitar negativo, por causa de monitor a esquerda do
        principal). Mas uma ancora de area zero ou negativa nao recorta nada, e
        e justamente a forma esperada contra a qual o molde e conferido.
        """
        caminho = self._com(tmp_path, mercado_ancora=ancora)
        with pytest.raises(CalibracaoInvalida, match="ancora|Recalibre"):
            Calibracao.carregar(caminho)

    def test_uma_calibracao_sem_nenhuma_chave_de_mercado_continua_carregando(self):
        """O teste que mais importa deste arquivo nao pode ter sido quebrado."""
        cal = Calibracao.carregar(REFERENCIA)
        assert cal.mercado_ancora is None
        assert cal.mercado_molde_da_ancora is None
        assert cal.mercado_limiar_da_ancora is None
        assert cal.mercado_geometria_da_captura is None


class TestAEscritaAtomicaDoCalibrationJson:
    """WR-12: um JSON truncado aqui derruba a calibracao de PARTY junto.

    `Calibracao.salvar` fazia `caminho.write_text(...)` direto sobre o arquivo
    final. Uma interrupcao no meio -- Ctrl-C impaciente, disco cheio, antivirus
    segurando o handle -- deixa um JSON truncado, e a proxima carga levanta
    "esta corrompido: recalibre" para o SCANNER INTEIRO. O que se perde e a
    party window, os limiares HSV afinados a mao contra o Gamma da tela do
    usuario, o `hp_proprio` e as assinaturas de nome.

    O risco ja existia; esta fase mudou o PERFIL dele. O calibration.json era
    escrito uma vez, na calibracao inicial; agora ha um segundo escritor que o
    usuario roda repetidamente.
    """

    def _referencia(self, destino: Path):
        from l2scanner.calibracao import Calibracao

        origem = Path(__file__).parent / "fixtures" / "calibracao_de_referencia.json"
        destino.write_text(origem.read_text(encoding="utf-8"), encoding="utf-8")
        return Calibracao.carregar(destino)

    def test_uma_escrita_interrompida_preserva_o_arquivo_ANTERIOR(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        import json as _json
        import os

        destino = tmp_path / "calibration.json"
        cal = self._referencia(destino)
        antes = destino.read_text(encoding="utf-8")

        def morrer(_origem, _destino):
            raise KeyboardInterrupt("o usuario perdeu a paciencia")

        monkeypatch.setattr(os, "replace", morrer)

        with pytest.raises(KeyboardInterrupt):
            cal.salvar(destino)

        assert destino.read_text(encoding="utf-8") == antes, (
            "a calibracao anterior foi danificada por uma escrita interrompida"
        )
        # O que importa e o arquivo carregar; o temporario e detrito visivel.
        _json.loads(destino.read_text(encoding="utf-8"))

    def test_uma_escrita_normal_nao_deixa_temporario_para_tras(
        self, tmp_path: Path
    ):
        destino = tmp_path / "calibration.json"
        cal = self._referencia(destino)

        cal.salvar(destino)

        sobrando = [p.name for p in tmp_path.iterdir() if p.name != destino.name]
        assert sobrando == [], f"a gravacao deixou lixo na pasta: {sobrando}"

    def test_o_conteudo_gravado_continua_o_mesmo(self, tmp_path: Path):
        """A troca de mecanica nao pode mudar o que sai no arquivo."""
        import json as _json

        from l2scanner.calibracao import Calibracao

        destino = tmp_path / "calibration.json"
        cal = self._referencia(destino)
        cal.salvar(destino)

        recarregada = Calibracao.carregar(destino)
        assert recarregada.party_window == cal.party_window
        assert recarregada.limiares_hp == cal.limiares_hp
        assert _json.loads(destino.read_text(encoding="utf-8"))["versao"] == (
            _json.loads(
                (
                    Path(__file__).parent
                    / "fixtures"
                    / "calibracao_de_referencia.json"
                ).read_text(encoding="utf-8")
            )["versao"]
        )
