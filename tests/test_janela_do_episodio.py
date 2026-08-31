"""O incidente de 2026-08-31: a janela anti-repeticao comendo um nascimento.

O QUE ACONTECEU. As ~13:58 de 31/08 o servidor anunciou `Tiat North [Lv. 60]
has spawned!` no chat do jogo. O scanner VIU: `.agenda/` tem nove ancoras
daquele nascimento, das 14:12 as 14:19. Nenhuma mensagem saiu no WhatsApp, e o
log repetiu, deteccao apos deteccao:

    14:12:57 INFO  Tiat North calado: este nascimento ja foi anunciado neste
                   episodio (origem desta deteccao: chat)

O MESMO silencio comeu o `Tiat North` das 07:16 e, pela mesma conta, teria
comido qualquer nascimento que caisse a menos de 7h55 do anterior.

A CADEIA. `inicio_do_episodio` derivava a janela anti-repeticao do MESMO numero
que serve a previsao: `respawn_horas_min - 5min`. Com `respawn_horas_min = 8`
no `config.toml`, a janela virou 7h55. O nascimento das 14:12 estava a 7.83h do
das 06:22, ou seja DENTRO dela: a chave do anuncio saiu com a hora da manha, o
marcador ja existia, e o `O_CREAT|O_EXCL` calou.

O DEFEITO NAO ERA O NUMERO, ERA O ACOPLAMENTO. Oito estava errado (a regra do
servidor e 6 horas mais 0 a 2 aleatorias, contadas da MORTE) e o numero ja foi
corrigido. Mas errar aquele numero so podia custar uma PREVISAO ATRASADA; ele
nao podia ter o poder de APAGAR um aviso. Este arquivo prova que nao tem mais.

AS DETECCOES DAQUI SAO DADO DE CAMPO, e nao um roteiro inventado: cada instante
abaixo foi copiado a mao de um nome de arquivo real de `.agenda/` em
2026-08-31. E o que permite afirmar, com os numeros que produziram o defeito,
que o desfecho mudou.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from datetime import datetime, timedelta

import pytest

from l2scanner.agenda import PREFIXO_ANUNCIO, RegistroEmDisco
from l2scanner.bosses import BossInvalido, OrigemDoAviso
from l2scanner.config import ler_bosses, ler_janela_do_episodio
from l2scanner.respawn import (
    JANELA_DO_EPISODIO,
    Ancora,
    anunciar_nascimento,
    chave_do_anuncio,
    chave_do_nascimento,
    inicio_do_episodio,
)

CHAT = OrigemDoAviso.CHAT
ALVO = OrigemDoAviso.ALVO
AMBOS = OrigemDoAviso.CHAT_E_ALVO


def _em(dia: int, hora: int, minuto: int) -> datetime:
    """Um instante de agosto de 2026, do jeito que `.agenda/` o guardou."""
    return datetime(2026, 8, dia, hora, minuto)


# AS DETECCOES REAIS, EM ORDEM, COPIADAS DE `.agenda/`.
#
# Um par por arquivo `nascimento_<data>_<apelido>-<HHMM>_<origem>`. Os grupos
# separados por linha em branco sao os nascimentos: as deteccoes de um mesmo
# nascimento se juntam em MINUTOS, e o proximo nascimento so vem horas depois.
DETECCOES_DO_NORTH = (
    (_em(30, 22, 17), CHAT),
    (_em(30, 22, 20), ALVO),
    (_em(30, 22, 21), ALVO),
    (_em(30, 22, 22), ALVO),
    (_em(30, 22, 23), ALVO),
    (_em(30, 22, 24), ALVO),
    (_em(30, 22, 25), ALVO),
    (_em(30, 22, 26), ALVO),
    (_em(30, 22, 29), ALVO),

    (_em(31, 6, 22), CHAT),
    (_em(31, 6, 24), ALVO),
    (_em(31, 6, 25), ALVO),
    (_em(31, 6, 26), ALVO),

    # A ANCORA ISOLADA, e ela nao e um nascimento: 54 minutos depois da das
    # 06:22, com UMA deteccao e vinda do chat. E quase certamente a mesma linha
    # do servidor relida na tela. Ela nao causou o incidente e nao esta
    # escondida daqui.
    (_em(31, 7, 16), CHAT),

    (_em(31, 14, 12), CHAT),
    (_em(31, 14, 13), CHAT),
    (_em(31, 14, 14), ALVO),
    (_em(31, 14, 14), AMBOS),
    (_em(31, 14, 15), ALVO),
    (_em(31, 14, 16), ALVO),
    (_em(31, 14, 17), ALVO),
    (_em(31, 14, 18), ALVO),
    (_em(31, 14, 19), ALVO),
)

DETECCOES_DO_SOUTH = (
    (_em(30, 21, 59), CHAT),
    (_em(30, 22, 1), ALVO),
    (_em(30, 22, 2), ALVO),
    (_em(30, 22, 4), ALVO),
    (_em(30, 22, 5), ALVO),
    (_em(30, 22, 6), ALVO),

    (_em(31, 4, 7), CHAT),
    (_em(31, 4, 9), CHAT),

    (_em(31, 12, 13), CHAT),
    (_em(31, 12, 14), AMBOS),
    (_em(31, 12, 15), AMBOS),
)

# OS AGRUPAMENTOS MEDIDOS: o primeiro instante de cada nascimento, quantas
# deteccoes ele rendeu e o vao entre a primeira e a ultima. Sao os cinco
# agrupamentos que o defeito de spam de campo produziria de novo se a janela
# encolhesse demais.
GRUPOS_MEDIDOS = (
    ("Tiat North", _em(30, 22, 17), 9, timedelta(minutes=12)),
    ("Tiat South", _em(30, 21, 59), 6, timedelta(minutes=7)),
    ("Tiat North", _em(31, 6, 22), 4, timedelta(minutes=4)),
    ("Tiat South", _em(31, 12, 13), 3, timedelta(minutes=2)),
    ("Tiat South", _em(31, 4, 7), 2, timedelta(minutes=2)),
)

# O MAIOR VAO MEDIDO entre a primeira e a ultima deteccao de UM nascimento.
MAIOR_VAO_MEDIDO = timedelta(minutes=12)

# A JANELA QUE O CODIGO ANTIGO PRODUZIA com o `config.toml` do dia do
# incidente: 8h de `respawn_horas_min` menos a margem de 5 minutos. Escrita a
# mao para o teste do "antes" nao depender de nenhuma constante que este
# conserto acabou de apagar.
#
# O `[[boss]]` com aquelas 8 horas ERRADAS continua no sistema, e o teste que o
# demonstra com o scanner inteiro em pe mora em
# `tests/test_sessao.py::TestOIncidenteDe31DeAgostoComOConfigErrado` — aqui so
# existe a metade pura, que nao tem tick.
JANELA_ANTIGA_COM_O_CONFIG_ERRADO = timedelta(hours=8) - timedelta(minutes=5)


def _ancoras(deteccoes, apelido="tiat-north", ate=None):
    """As ancoras ate um instante, como `ancoras_do_boss` as devolveria."""
    return [
        Ancora(boss=apelido, instante=instante, origem=origem)
        for instante, origem in deteccoes
        if ate is None or instante <= ate
    ]


class TestAMedicaoQueDerivaODefault:
    """O default nao e um numero redondo: e uma medida com folga declarada.

    Se alguem encolher a janela abaixo do maior vao medido em campo, o defeito
    de spam volta pelo caminho que ja andou uma vez. Se alguem a esticar ate a
    ordem de grandeza do respawn, volta o incidente. Os dois lados ficam
    afirmados aqui, e nao so no comentario da constante.
    """

    def test_a_janela_cobre_o_maior_vao_medido_em_campo(self):
        assert JANELA_DO_EPISODIO > MAIOR_VAO_MEDIDO

    def test_a_folga_sobre_a_medida_e_de_pelo_menos_o_dobro(self):
        """12 minutos medidos, 25 de janela: o dobro da medida mais um minuto
        para o truncamento de segundo do nome de arquivo `<HHMM>`."""
        assert JANELA_DO_EPISODIO >= MAIOR_VAO_MEDIDO * 2

    def test_a_janela_e_MUITO_menor_que_qualquer_respawn_plausivel(self):
        """O teto do arranque existe para isto; aqui fica dito que o default
        passa nele com folga de ordem de grandeza, inclusive contra o config
        ERRADO de 8 horas."""
        assert JANELA_DO_EPISODIO < timedelta(hours=1)


class TestOIncidenteDe31DeAgosto:
    """A regressao, com os numeros do relatorio e o config ERRADO no lugar."""

    def setup_method(self):
        self.ancoras = _ancoras(DETECCOES_DO_NORTH, ate=_em(31, 14, 12))

    def test_a_janela_derivada_do_respawn_errado_e_o_que_CALAVA(self):
        """O 'antes', afirmado para o conserto nao virar coincidencia.

        Com a janela de 7h55 que `respawn_horas_min = 8` produzia, o episodio
        das 14:12 comecava as 06:22: chave da manha, marcador ja em disco,
        silencio.
        """
        assert (
            inicio_do_episodio(
                self.ancoras,
                agora=_em(31, 14, 12),
                janela=JANELA_ANTIGA_COM_O_CONFIG_ERRADO,
            )
            == _em(31, 6, 22)
        )

    def test_o_nascimento_das_1412_abre_EPISODIO_PROPRIO(self):
        assert (
            inicio_do_episodio(self.ancoras, agora=_em(31, 14, 12))
            == _em(31, 14, 12)
        )

    def test_a_chave_do_anuncio_das_1412_nao_e_a_da_manha(self):
        """A chave E a decisao: iguais, o `O_CREAT|O_EXCL` cala."""
        manha = chave_do_anuncio("tiat-north", _em(31, 6, 22))
        tarde = chave_do_anuncio(
            "tiat-north",
            inicio_do_episodio(self.ancoras, agora=_em(31, 14, 12)),
        )

        assert tarde != manha
        assert tarde == "2026-08-31_tiat-north-1412"

    def test_o_nascimento_SAI_mesmo_com_o_respawn_horas_min_errado(
        self, tmp_path
    ):
        """O coracao do conserto, ponta a ponta e em disco.

        As deteccoes reais sao reproduzidas na ordem, cada uma gravando a
        ancora e pedindo o anuncio, exatamente como o tick faz. O
        `respawn_horas_min` nao chega mais ate aqui por assinatura, e e por
        isso que o valor dele deixou de poder decidir este desfecho.
        """
        registro = RegistroEmDisco(tmp_path / "agenda")
        saiu = False
        for instante, origem in DETECCOES_DO_NORTH:
            registro.registrar_nascimento(
                chave_do_nascimento("Tiat North", instante, origem)
            )
            anunciou = anunciar_nascimento(registro, "Tiat North", instante)
            if instante == _em(31, 14, 12):
                saiu = anunciou

        assert saiu, "o nascimento das 14:12 de 31/08 foi calado de novo"


class TestONaoRetornoDoSpam:
    """O defeito ANTERIOR, ja consertado, que este conserto nao pode reabrir.

    Em 2026-08-30 UM nascimento rendeu SEIS mensagens no WhatsApp, porque cada
    remarcacao de alvo era tratada como nascimento novo. Os agrupamentos
    medidos em campo (9, 6, 4, 3 e 2 deteccoes) tem de continuar rendendo UMA
    mensagem cada.
    """

    @pytest.mark.parametrize(
        ("boss", "primeira", "deteccoes", "vao"), GRUPOS_MEDIDOS
    )
    def test_um_agrupamento_medido_rende_UMA_chave_de_anuncio(
        self, boss, primeira, deteccoes, vao
    ):
        do_boss = (
            DETECCOES_DO_NORTH if boss == "Tiat North" else DETECCOES_DO_SOUTH
        )
        apelido = "tiat-north" if boss == "Tiat North" else "tiat-south"
        grupo = [
            (instante, origem)
            for instante, origem in do_boss
            if primeira <= instante <= primeira + vao
        ]
        assert len(grupo) == deteccoes

        chaves = {
            chave_do_anuncio(
                apelido,
                inicio_do_episodio(
                    _ancoras(do_boss, apelido=apelido, ate=instante),
                    agora=instante,
                ),
            )
            for instante, _origem in grupo
        }

        assert chaves == {chave_do_anuncio(apelido, primeira)}

    @pytest.mark.parametrize(
        ("boss", "deteccoes", "mensagens"),
        [
            # QUATRO E NAO TRES, e a quarta e a ancora isolada das 07:16: fora
            # da janela de 25 minutos ela abre episodio proprio e rende UMA
            # mensagem repetida. E o lado ACEITO do erro, afirmado e nao
            # consertado, e e barato: o usuario le e ignora em dois segundos.
            ("Tiat North", DETECCOES_DO_NORTH, 4),
            ("Tiat South", DETECCOES_DO_SOUTH, 3),
        ],
    )
    def test_o_replay_das_deteccoes_reais_rende_uma_mensagem_por_nascimento(
        self, boss, deteccoes, mensagens, tmp_path
    ):
        pasta = tmp_path / "agenda"
        registro = RegistroEmDisco(pasta)

        anunciados = []
        for instante, origem in deteccoes:
            registro.registrar_nascimento(
                chave_do_nascimento(boss, instante, origem)
            )
            if anunciar_nascimento(registro, boss, instante):
                anunciados.append(instante)

        assert len(anunciados) == mensagens
        marcadores = [
            c for c in pasta.iterdir() if c.name.startswith(PREFIXO_ANUNCIO)
        ]
        assert len(marcadores) == mensagens

    def test_o_replay_do_north_anuncia_os_TRES_nascimentos_e_a_releitura(
        self, tmp_path
    ):
        """Os instantes exatos, para a contagem nao esconder QUAL saiu."""
        registro = RegistroEmDisco(tmp_path / "agenda")

        anunciados = []
        for instante, origem in DETECCOES_DO_NORTH:
            registro.registrar_nascimento(
                chave_do_nascimento("Tiat North", instante, origem)
            )
            if anunciar_nascimento(registro, "Tiat North", instante):
                anunciados.append(instante)

        assert anunciados == [
            _em(30, 22, 17),
            _em(31, 6, 22),
            _em(31, 7, 16),
            _em(31, 14, 12),
        ]


class TestAJanelaNaoSaiMaisDoRespawnHorasMin:
    """O acoplamento, proibido por ESTRUTURA e nao por politica.

    Um teste de comportamento fica verde nos dois formatos no dia em que
    alguem "simplificar" a janela de volta para `respawn_horas_min - margem`
    com um default que por acaso funciona. Este portao nao.
    """

    @staticmethod
    def _nomes_do_corpo(funcao) -> set[str]:
        """Todo nome CITADO no codigo, sem a docstring.

        A docstring PRECISA citar `horas_min`: e la que a premissa quebrada
        esta explicada, com a data em que ela custou dois avisos. O portao le a
        arvore, e uma docstring e uma constante.
        """
        arvore = ast.parse(textwrap.dedent(inspect.getsource(funcao)))
        nomes = {no.id for no in ast.walk(arvore) if isinstance(no, ast.Name)}
        nomes |= {
            no.attr for no in ast.walk(arvore) if isinstance(no, ast.Attribute)
        }
        for no in ast.walk(arvore):
            if isinstance(no, ast.arg):
                nomes.add(no.arg)
        return nomes

    @pytest.mark.parametrize(
        "funcao", [inicio_do_episodio, anunciar_nascimento]
    )
    def test_o_calculo_do_episodio_nao_cita_as_horas_de_respawn(self, funcao):
        nomes = self._nomes_do_corpo(funcao)

        assert "horas_min" not in nomes
        assert "respawn_horas_min" not in nomes


class TestOTetoQueFalhaSeguro:
    """O arranque RECUSA a configuracao que produziu o incidente.

    Uma janela anti-repeticao maior ou igual ao menor `respawn_horas_min` e
    exatamente o estado de 31/08: ela engole o nascimento SEGUINTE. Recusa no
    arranque, com o usuario olhando o console, e nao um aviso no log que
    ninguem le as 3h da manha.
    """

    BOSSES = (
        '[[boss]]\nnome = "Tiat North"\n'
        "respawn_horas_min = 6\nrespawn_horas_max = 10\n\n"
        '[[boss]]\nnome = "Tiat South"\n'
        "respawn_horas_min = 8\nrespawn_horas_max = 10\n"
    )

    def _ler(self, tmp_path, corpo):
        caminho = tmp_path / "config.toml"
        caminho.write_text(corpo, encoding="utf-8")
        return ler_janela_do_episodio(ler_bosses(caminho), caminho)

    def test_sem_a_secao_vale_o_default_medido(self, tmp_path):
        assert self._ler(tmp_path, self.BOSSES) == JANELA_DO_EPISODIO

    def test_arquivo_ausente_nao_e_erro(self, tmp_path):
        assert (
            ler_janela_do_episodio([], tmp_path / "nao_existe.toml")
            == JANELA_DO_EPISODIO
        )

    def test_o_valor_escrito_manda(self, tmp_path):
        corpo = self.BOSSES + "\n[episodio]\nminutos = 40\n"

        assert self._ler(tmp_path, corpo) == timedelta(minutes=40)

    def test_uma_janela_MAIOR_que_o_menor_respawn_derruba_o_arranque(
        self, tmp_path
    ):
        corpo = self.BOSSES + "\n[episodio]\nminutos = 480\n"

        with pytest.raises(BossInvalido):
            self._ler(tmp_path, corpo)

    def test_uma_janela_IGUAL_ao_menor_respawn_tambem_e_recusada(
        self, tmp_path
    ):
        """A borda e o caso real: com 6 horas de janela e 6 de respawn, dois
        nascimentos no minimo do servidor caem no mesmo episodio e o segundo
        some."""
        corpo = self.BOSSES + "\n[episodio]\nminutos = 360\n"

        with pytest.raises(BossInvalido):
            self._ler(tmp_path, corpo)

    def test_a_recusa_cita_o_boss_do_MENOR_respawn_e_os_dois_numeros(
        self, tmp_path
    ):
        """'Errado' sem dizer ONDE faz o usuario conferir bloco por bloco."""
        corpo = self.BOSSES + "\n[episodio]\nminutos = 400\n"

        with pytest.raises(BossInvalido) as erro:
            self._ler(tmp_path, corpo)

        texto = str(erro.value)
        assert "Tiat North" in texto
        assert "400" in texto
        assert "360" in texto

    def test_a_recusa_nao_tem_travessao(self, tmp_path):
        """O console do Windows ja entregou travessao como lixo neste projeto,
        e num texto de erro um caractere corrompido faz o usuario duvidar da
        mensagem inteira."""
        corpo = self.BOSSES + "\n[episodio]\nminutos = 480\n"

        with pytest.raises(BossInvalido) as erro:
            self._ler(tmp_path, corpo)

        assert "—" not in str(erro.value)

    def test_sem_boss_nenhum_nao_ha_teto_a_conferir(self, tmp_path):
        """Mesma regra do resto do arquivo: quem nao configurou `[[boss]]` nao
        pode ver o programa quebrar por causa de um recurso que nao pediu."""
        corpo = "[episodio]\nminutos = 480\n"

        assert self._ler(tmp_path, corpo) == timedelta(minutes=480)

    @pytest.mark.parametrize("valor", ["0", "-5"])
    def test_uma_janela_de_zero_ou_negativa_e_recusada(self, valor, tmp_path):
        """Zero reabre o spam: cada deteccao vira episodio proprio, e foi assim
        que UM nascimento rendeu SEIS mensagens em 30/08."""
        corpo = self.BOSSES + f"\n[episodio]\nminutos = {valor}\n"

        with pytest.raises(BossInvalido):
            self._ler(tmp_path, corpo)

    @pytest.mark.parametrize("valor", ["true", '"25"'])
    def test_um_valor_que_nao_e_numero_de_minutos_e_recusado(
        self, valor, tmp_path
    ):
        """`true` recusado EXPLICITAMENTE porque `isinstance(True, int)` e
        verdadeiro em Python: sem a linha, ele passaria como um minuto."""
        corpo = self.BOSSES + f"\n[episodio]\nminutos = {valor}\n"

        with pytest.raises(BossInvalido):
            self._ler(tmp_path, corpo)
