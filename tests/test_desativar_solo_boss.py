"""Desligar e religar TODOS os avisos do Solo Boss, sem editar arquivo nenhum.

O QUE ESTE ARQUIVO PROVA, e por que cada prova existe:

1. **NAO HA COMO CALAR METADE.** O usuario decidiu que e tudo ou nada, e a
   razao e de produto: a chamada de 1h50 sem o lembrete de 10 minutos convida
   a party para um boss que ninguem lembra de ir; o lembrete sem a chamada
   avisa uma party que nunca foi consultada. Meia-mudez e pior que qualquer um
   dos dois extremos, entao o gate e por EVENTO e nao por tipo de aviso.

2. **O DESLIGAMENTO SOBREVIVE AO `vigiar-party.bat`.** Decisao explicita do
   usuario, contra a alternativa em memoria e contra a expiracao automatica.
   Aqui isso e um `RegistroEmDisco` NOVO lendo a mesma pasta — que e
   exatamente o que um restart faz.

3. **A PODA NAO PODE COMER O DESLIGAMENTO.** `agenda.podar` apaga marcador com
   mais de 3 dias e roda no construtor, ou seja, a cada arranque. Um marcador
   que expirasse sozinho religaria o boss sem ninguem mandar — o oposto da
   decisao 2.

4. **O `/status` CONTA.** Um off-switch persistido que o `/status` nao mostra
   e estado escondido: o usuario esquece que desligou e perde o boss achando
   que o bot esta vigiando.

5. **DISCO ESTRAGADO FAZ O AVISO SAIR, nunca sumir.** E a lei ja escrita no
   `RegistroEmDisco.marcar`: preferir o aviso duplicado ao aviso perdido. A
   party ignora uma repeticao; ela nao adivinha um boss que ninguem anunciou.

Nenhum relogio e monkeypatchado aqui — o tempo entra por parametro, como manda
`relogio.py:83` e como o resto da agenda ja faz.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from l2scanner.agenda import (
    PREFIXO_EVENTO_CALADO,
    EventoAgendado,
    RegistroEmDisco,
    TipoDeAviso,
    apelido_do_evento,
    avisos_devidos,
    nomes_dos_eventos,
    responder_silenciamento,
)
from l2scanner.config import ler_agenda

RAIZ = Path(__file__).resolve().parent.parent

# Uma segunda-feira, o mesmo dia conhecido do `test_agenda.py`.
SEGUNDA = datetime(2026, 8, 24)
assert SEGUNDA.weekday() == 0

# O Solo Boss como o `config.toml` do repositorio o descreve: 12 horarios
# pares, chamada 1h50 antes, lembrete 10 minutos antes, e NUNCA no horario.
SOLO_BOSS = EventoAgendado(
    nome="Solo Boss",
    horarios=((20, 0),),
    avisar_minutos_antes=10,
    avisar_no_horario=False,
    chamar_minutos_antes=110,
)
TVT = EventoAgendado(nome="TvT", horarios=((21, 50),), avisar_minutos_antes=10)

# Os dois instantes em que o Solo Boss das 20:00 fala.
CHAMADA = datetime(2026, 8, 24, 18, 10)  # 110 minutos antes
LEMBRETE = datetime(2026, 8, 24, 19, 50)  # 10 minutos antes

SLUG = "solo-boss"


def _tipos(agora, eventos, calados=frozenset()):
    return [
        a.tipo
        for a in avisos_devidos(agora, eventos, set(), eventos_calados=calados)
    ]


class TestOGateCalaOsDoisAvisos:
    """A decisao "tudo ou nada", provada nos dois instantes que ela cobre."""

    def test_ligado_o_boss_chama_e_lembra_como_sempre(self):
        assert _tipos(CHAMADA, [SOLO_BOSS]) == [TipoDeAviso.CHAMADA]
        assert _tipos(LEMBRETE, [SOLO_BOSS]) == [TipoDeAviso.ANTES]

    def test_calado_a_CHAMADA_nao_sai(self):
        assert _tipos(CHAMADA, [SOLO_BOSS], frozenset({SLUG})) == []

    def test_calado_o_LEMBRETE_nao_sai(self):
        assert _tipos(LEMBRETE, [SOLO_BOSS], frozenset({SLUG})) == []

    def test_calado_nem_o_aviso_de_AGORA_escapa(self):
        """O terceiro tipo, que o config do usuario nem usa.

        `avisar_no_horario = false` ja o mantem quieto no Solo Boss real, entao
        ele nunca apareceria nesta prova por acidente. Ligar o campo aqui e o
        que mostra que o gate e por EVENTO e nao uma lista de dois tipos que o
        proximo `TipoDeAviso` do projeto ia furar em silencio.
        """
        falante = EventoAgendado(
            nome="Solo Boss", horarios=((20, 0),), avisar_no_horario=True
        )
        assert _tipos(datetime(2026, 8, 24, 20, 0), [falante]) == [TipoDeAviso.AGORA]
        assert _tipos(
            datetime(2026, 8, 24, 20, 0), [falante], frozenset({SLUG})
        ) == []

    def test_o_outro_evento_continua_falando(self):
        """Calar o boss nao pode calar o TvT — sao dois eventos, nao um modo."""
        agora = datetime(2026, 8, 24, 21, 40)
        assert _tipos(agora, [SOLO_BOSS, TVT], frozenset({SLUG})) == [
            TipoDeAviso.ANTES
        ]

    def test_sem_o_parametro_tudo_fica_byte_a_byte_como_estava(self):
        """O default vazio e o que mantem os 1444 testes de hoje valendo."""
        assert [a.tipo for a in avisos_devidos(CHAMADA, [SOLO_BOSS], set())] == [
            TipoDeAviso.CHAMADA
        ]


class TestNaAgendaRealDoRepositorio:
    """A mesma varredura de dia do `test_agenda.py`, com o boss desligado.

    Os numeros sao ESCRITOS A MAO a partir da tabela que
    `test_o_volume_diario_total_e_o_esperado` ja documenta, e nunca colhidos da
    execucao — um alarme calibrado pela saida que ele vigia so afirma que o
    codigo faz o que o codigo faz.

        TvT               10   5 horarios x (ANTES + AGORA)
        Prime              2   1 horario  x (ANTES + AGORA), so seg-qui
        Solo Boss ANTES   12   -> 0 com o comando dado
        Solo Boss CHAMADA 12   -> 0 com o comando dado
        --------------------------------------------------
        total             36   -> 12
    """

    @pytest.fixture
    def agenda(self):
        return ler_agenda(RAIZ / "config.toml")

    def _varrer_um_dia(self, agenda, dia, calados=frozenset()):
        enviados: set[str] = set()
        saidas = []
        instante = dia
        for _ in range(24 * 60):
            for aviso in avisos_devidos(
                instante, agenda, enviados, eventos_calados=calados
            ):
                enviados.add(aviso.chave)
                saidas.append((aviso.evento, aviso.tipo))
            instante += timedelta(minutes=1)
        return saidas

    def test_o_dia_inteiro_perde_as_24_mensagens_do_boss_e_so_elas(self, agenda):
        saidas = self._varrer_um_dia(agenda, SEGUNDA, frozenset({SLUG}))
        assert [s for s in saidas if s[0] == "Solo Boss"] == []
        assert len(saidas) == 12, "TvT (10) + Prime (2), e nada mais"

    def test_com_o_boss_ligado_o_dia_continua_valendo_36(self, agenda):
        assert len(self._varrer_um_dia(agenda, SEGUNDA)) == 36


class TestOEstadoEmDisco:
    """Onde o desligamento mora, e o que ele tem que aguentar."""

    def test_desativar_e_ler_de_volta(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        assert registro.calar_evento("Solo Boss") == "calado"
        assert registro.eventos_calados() == frozenset({SLUG})

    def test_reiniciar_o_scanner_NAO_religa(self, tmp_path):
        """A decisao 1 do usuario, e o `vigiar-party.bat` e literalmente isto.

        O objeto novo nao herda nada do anterior — ele so tem a pasta. Se o
        estado morasse em memoria, esta linha voltaria vazia.
        """
        RegistroEmDisco(tmp_path).calar_evento("Solo Boss")

        depois_do_restart = RegistroEmDisco(tmp_path)

        assert depois_do_restart.eventos_calados() == frozenset({SLUG})

    def test_a_poda_nao_expira_o_desligamento(self, tmp_path):
        """Marcador sem data, de PROPOSITO — o usuario recusou expiracao.

        `podar` roda no construtor, ou seja, a cada arranque do scanner. Se
        este marcador entrasse em `_PREFIXOS_CONHECIDOS` e ganhasse data, o
        boss religaria sozinho depois de tres dias e ninguem saberia por que.
        """
        registro = RegistroEmDisco(tmp_path)
        registro.calar_evento("Solo Boss")

        assert registro.podar(hoje=date(2030, 1, 1)) >= 0
        assert registro.eventos_calados() == frozenset({SLUG})
        assert RegistroEmDisco(tmp_path).eventos_calados() == frozenset({SLUG})

    def test_desativar_duas_vezes_diz_que_ja_estava(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        assert registro.calar_evento("Solo Boss") == "calado"
        assert registro.calar_evento("Solo Boss") == "ja_estava"

    def test_ativar_diz_se_havia_o_que_religar(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        assert registro.voltar_a_avisar("Solo Boss") == "ja_estava"
        registro.calar_evento("Solo Boss")
        assert registro.voltar_a_avisar("Solo Boss") == "religado"
        assert registro.eventos_calados() == frozenset()

    def test_a_escrita_que_falha_NAO_vira_sucesso(self, tmp_path):
        """O tri-estado do `entrar`, e nao o `bool` do `marcar`.

        `marcar` colapsa `OSError` em True porque, para um ANUNCIO, o
        duplicado e melhor que o perdido. Aqui a regra e a inversa: dizer
        "desativei" sobre uma escrita que o disco recusou faria o usuario parar
        de esperar avisos que vao continuar chegando — e no dia em que ele
        quisesse religar, nao haveria nada para religar.

        A pasta e apagada de verdade, sem monkeypatch: e o que acontece quando
        alguem limpa `.agenda/` com o scanner aberto.
        """
        registro = RegistroEmDisco(tmp_path / "agenda")
        (tmp_path / "agenda").rmdir()

        assert registro.calar_evento("Solo Boss") == "falhou"

    def test_duas_instancias_competindo_so_uma_desativa(self, tmp_path):
        """O usuario roda Yazalaque e Faerlina lado a lado, na MESMA pasta.

        E a mesma atomicidade do `O_CREAT|O_EXCL` que ja impede o aviso de TvT
        de sair em dobro. Sem ela, as duas anunciariam no grupo que
        desativaram — e o grupo leria a mesma coisa duas vezes.
        """
        yazalaque = RegistroEmDisco(tmp_path)
        faerlina = RegistroEmDisco(tmp_path)

        resultados = [
            yazalaque.calar_evento("Solo Boss"),
            faerlina.calar_evento("Solo Boss"),
        ]

        assert resultados.count("calado") == 1
        assert resultados.count("ja_estava") == 1
        assert faerlina.eventos_calados() == frozenset({SLUG})

    def test_cada_evento_cala_sozinho(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.calar_evento("Solo Boss")
        assert registro.eventos_calados() == frozenset({SLUG})
        assert _tipos(datetime(2026, 8, 24, 21, 40), [TVT], registro.eventos_calados()) == [
            TipoDeAviso.ANTES
        ]

    def test_o_marcador_nao_atrapalha_o_resto_da_pasta(self, tmp_path):
        """A pasta e compartilhada com avisos, cancelamentos e presenca."""
        registro = RegistroEmDisco(tmp_path)
        registro.calar_evento("Solo Boss")
        registro.marcar("2026-08-24_solo-boss-2000_antes")

        assert registro.cancelados() == set()
        assert registro.presentes("2026-08-24_solo-boss-2000") == frozenset()
        assert registro.eventos_calados() == frozenset({SLUG})


class TestDiscoEstragado:
    """Leitura defensiva: a pasta e duravel, compartilhada e nao e nossa."""

    def test_nome_truncado_e_ignorado_sem_derrubar_nada(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        (tmp_path / PREFIXO_EVENTO_CALADO).write_text("", encoding="utf-8")

        assert registro.eventos_calados() == frozenset()

    def test_lixo_na_pasta_nao_derruba_a_leitura(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.calar_evento("Solo Boss")
        (tmp_path / "arquivo_qualquer.txt").write_text("lixo", encoding="utf-8")
        (tmp_path / "evento_calado").write_text("sem underline final", "utf-8")
        os.mkdir(tmp_path / (PREFIXO_EVENTO_CALADO + "uma-pasta"))

        # A pasta com nome de marcador CONTA: `enviados()` lista nomes, nao
        # arquivos, e um diretorio criado a mao ali e indistinguivel de um
        # marcador. Nao levantar e o requisito; o conteudo e consequencia.
        assert SLUG in registro.eventos_calados()

    def test_a_pasta_sumindo_faz_o_aviso_SAIR(self, tmp_path):
        """A direcao da falha, e ela nao e simetrica.

        Disco ilegivel = nenhum evento calado = o boss e anunciado. E a lei
        escrita no `marcar`: preferir o duplicado ao perdido. A direcao oposta
        — assumir "calado" quando nao da para ler — silenciaria o boss por
        causa de um disco travado, que e a falha que ninguem percebe.

        Sem monkeypatch: a pasta e apagada de verdade debaixo do registro, que
        e o que acontece quando o usuario limpa `.agenda/` com o scanner
        aberto.
        """
        registro = RegistroEmDisco(tmp_path / "agenda")
        registro.calar_evento("Solo Boss")
        for caminho in (tmp_path / "agenda").iterdir():
            caminho.unlink()
        (tmp_path / "agenda").rmdir()

        assert registro.eventos_calados() == frozenset()
        assert _tipos(CHAMADA, [SOLO_BOSS], registro.eventos_calados()) == [
            TipoDeAviso.CHAMADA
        ]


class TestARespostaDoComando:
    """O texto que chega no celular — e o que ele nao pode deixar de dizer."""

    def _registro(self, tmp_path):
        return RegistroEmDisco(tmp_path)

    def test_desativar_nomeia_OS_DOIS_avisos_com_os_minutos_do_config(
        self, tmp_path
    ):
        """Os numeros saem do `EventoAgendado`, nunca de um literal.

        Um texto que dissesse "110" a mao passaria a mentir no dia em que o
        usuario editasse `chamar_minutos_antes` — e mentir sobre o que foi
        desligado e pior que nao explicar.
        """
        resposta = responder_silenciamento(
            self._registro(tmp_path), [SOLO_BOSS], "Solo Boss", True, "Yazalaque"
        )

        assert "110" in resposta
        assert "10 minutos" in resposta
        assert "Yazalaque" in resposta
        # O SEGUNDO "nem" — e ele nao e enfeite. Sem esta asercao a frase saiu
        # "nem a chamada de 110 minutos antes, o lembrete de 10 minutos antes",
        # que se le como se so a chamada tivesse sido desligada. Numa
        # funcionalidade cuja regra e "tudo ou nada", a frase que sugere metade
        # e um defeito de produto, nao de redacao.
        assert "nem a chamada de 110" in resposta
        assert "nem o lembrete de 10 minutos" in resposta

    def test_desativar_diz_que_sobrevive_ao_restart(self, tmp_path):
        """Decisao 1 do usuario dita EM VOZ ALTA, e nao so implementada.

        Quem desliga precisa saber que reiniciar nao religa; senao ele reinicia
        "para garantir" e continua sem os avisos sem entender por que.
        """
        resposta = responder_silenciamento(
            self._registro(tmp_path), [SOLO_BOSS], "Solo Boss", True, "Yazalaque"
        )
        assert "reinici" in resposta.lower()

    def test_desativar_ensina_como_religar(self, tmp_path):
        resposta = responder_silenciamento(
            self._registro(tmp_path), [SOLO_BOSS], "Solo Boss", True, "Yazalaque"
        )
        assert "/ativarsoloboss" in resposta

    def test_desativar_duas_vezes_nao_finge_que_acabou_de_desligar(self, tmp_path):
        registro = self._registro(tmp_path)
        responder_silenciamento(registro, [SOLO_BOSS], "Solo Boss", True, "quem")
        segunda = responder_silenciamento(
            registro, [SOLO_BOSS], "Solo Boss", True, "quem"
        )
        assert "ja estava" in segunda.lower()

    def test_ativar_volta_a_prometer_os_dois_avisos(self, tmp_path):
        registro = self._registro(tmp_path)
        registro.calar_evento("Solo Boss")

        resposta = responder_silenciamento(
            registro, [SOLO_BOSS], "Solo Boss", False, "Yazalaque"
        )

        assert registro.eventos_calados() == frozenset()
        assert "110" in resposta and "10 minutos" in resposta
        # "A e B", e nao "nem A, nem B": e a mesma lista com a conjuncao da
        # outra direcao. Uma frase so para os dois sentidos leria errado num
        # deles, sempre.
        assert "antes e o lembrete" in resposta

    def test_um_evento_que_so_faz_UM_aviso_nao_ganha_conjuncao_solta(
        self, tmp_path
    ):
        """Lista de uma parte so nao pode sair com um "nem" pendurado.

        Nao e um evento hipotetico: basta o usuario apagar a linha
        `chamar_minutos_antes` do `config.toml`, que o proprio arquivo convida
        a apagar ("se nao valer a pena, apague a linha e nada mais muda").
        """
        so_lembrete = EventoAgendado(
            nome="Solo Boss",
            horarios=((20, 0),),
            avisar_minutos_antes=10,
            avisar_no_horario=False,
        )
        resposta = responder_silenciamento(
            self._registro(tmp_path), [so_lembrete], "Solo Boss", True, "quem"
        )

        assert "nem o lembrete de 10 minutos antes." in resposta
        assert "chamada" not in resposta

    def test_ativar_o_que_nunca_foi_desativado_diz_a_verdade(self, tmp_path):
        resposta = responder_silenciamento(
            self._registro(tmp_path), [SOLO_BOSS], "Solo Boss", False, "quem"
        )
        assert "ja estava" in resposta.lower()

    def test_religar_que_falha_diz_que_o_boss_CONTINUA_calado(self, tmp_path):
        """A direcao PERIGOSA da falha, e por isso ela e dita em voz alta.

        `sair` (a saida da lista de presenca) trata `OSError` como "voce nao
        estava la". Aqui isso seria o pior desfecho possivel: o marcador
        continuaria em disco, o boss continuaria calado, e a unica pessoa capaz
        de perceber teria acabado de ler "voltei a avisar". Um boss perdido em
        silencio e exatamente o que esta funcionalidade nao pode produzir.

        O marcador e substituido por um DIRETORIO de mesmo nome — `unlink`
        recusa apagar diretorio nos dois sistemas. Sem monkeypatch.
        """
        registro = self._registro(tmp_path)
        os.mkdir(tmp_path / (PREFIXO_EVENTO_CALADO + SLUG))

        resposta = responder_silenciamento(
            registro, [SOLO_BOSS], "Solo Boss", False, "Yazalaque"
        )

        assert "CONTINUAM" in resposta
        assert registro.eventos_calados() == frozenset({SLUG})

    def test_evento_fora_da_agenda_NAO_cria_marcador_nenhum(self, tmp_path):
        """O modo de falha silencioso que este ramo fecha.

        Se o usuario renomear o bloco `[[evento]]` no `config.toml`, o comando
        gravaria um marcador que nao casa evento nenhum: ele responderia
        "desativado", nada seria calado, e o `/status` — que so conhece os
        eventos da agenda — tambem nao teria o que mostrar. Duas superficies
        mentindo juntas.
        """
        registro = self._registro(tmp_path)

        resposta = responder_silenciamento(
            registro, [TVT], "Solo Boss", True, "quem"
        )

        assert registro.eventos_calados() == frozenset()
        assert "Solo Boss" in resposta
        assert "agenda" in resposta.lower()


class TestOStatusRevela:
    """Decisao 2 do usuario, e ela e inegociavel.

    O `_obedecer_status` e a unica coisa entre o usuario que esqueceu que
    desligou e um boss perdido em silencio.
    """

    def _status(self, tmp_path, calar):
        from l2scanner.__main__ import _obedecer_status

        registro = RegistroEmDisco(tmp_path)
        if calar:
            registro.calar_evento("Solo Boss")
        return _obedecer_status(
            registro, [SOLO_BOSS, TVT], datetime(2026, 8, 24, 12, 0)
        )

    def test_com_o_boss_calado_o_status_diz_o_nome_e_a_palavra(self, tmp_path):
        resposta = self._status(tmp_path, calar=True)
        assert "Solo Boss" in resposta
        assert "desativad" in resposta.lower()

    def test_com_tudo_ligado_o_status_nao_inventa_nada(self, tmp_path):
        resposta = self._status(tmp_path, calar=False)
        assert "desativad" not in resposta.lower()

    def test_o_status_sobrevive_ao_restart_junto_com_o_estado(self, tmp_path):
        """As duas decisoes do usuario na mesma prova, que e onde elas vivem.

        Persistir sem contar e estado escondido; contar sem persistir e uma
        promessa que o proximo arranque quebra.
        """
        RegistroEmDisco(tmp_path).calar_evento("Solo Boss")
        assert "Solo Boss" in self._status(tmp_path, calar=False)

    def test_nomes_dos_eventos_devolve_o_nome_COMO_CONFIGURADO(self):
        """O disco guarda `solo-boss`; o usuario escreveu `Solo Boss`.

        Mesma disciplina do D-10 na lista de presenca: o slug e detalhe de
        armazenamento e nunca pode vazar para a tela de ninguem.
        """
        assert nomes_dos_eventos([SOLO_BOSS, TVT], frozenset({SLUG})) == ["Solo Boss"]
        assert nomes_dos_eventos([SOLO_BOSS], frozenset()) == []
        assert nomes_dos_eventos([TVT], frozenset({SLUG})) == []


class TestApelidoDoEvento:
    """O slug e UM so — o da chave de aviso, o da ocorrencia e o do marcador.

    Duas implementacoes divergiriam no primeiro ajuste e o gate passaria a
    procurar um apelido que a agenda nunca escreve. Em silencio, que e o pior
    modo de falha desta funcionalidade.
    """

    def test_o_espaco_e_a_caixa_somem(self):
        assert apelido_do_evento("Solo Boss") == "solo-boss"

    def test_a_chave_do_aviso_usa_o_mesmo_apelido(self):
        from l2scanner.agenda import Aviso

        aviso = Aviso(
            evento="Solo Boss",
            tipo=TipoDeAviso.CHAMADA,
            alvo=datetime(2026, 8, 24, 20, 0),
            devido_em=CHAMADA,
        )
        assert apelido_do_evento("Solo Boss") in aviso.chave

    def test_a_chave_da_ocorrencia_usa_o_mesmo_apelido(self):
        from l2scanner.agenda import chave_da_ocorrencia

        chave = chave_da_ocorrencia("Solo Boss", datetime(2026, 8, 24, 20, 0))
        assert chave.startswith("2026-08-24_" + apelido_do_evento("Solo Boss"))


class TestOsDoisLacosObedecem:
    """Sao DOIS lacos, e calar so um e a definicao de meia-mudez.

    O usuario roda `vigiar-party.bat` (o laco principal, via `Sessao`) e
    `avisos-tvt.bat` (`--so-agenda`). Os dois leem a MESMA pasta `.agenda/` e
    falam no MESMO grupo. Uma supressao aplicada so de um lado faria o boss
    ficar quieto num modo e falante no outro — e o usuario descobriria isso na
    forma de um aviso que ele desligou chegando no celular.
    """

    def _sessao(self, tmp_path, eventos, registro):
        from l2scanner.sessao import Sessao

        class SemSilencio:
            def ativo(self):
                return False

            def atualizar(self, agora):
                return None

        return Sessao(
            cal=None,
            rastreador=None,
            eventos_agendados=eventos,
            registro=registro,
            silencio=SemSilencio(),
        )

    def _avisos_do_tick(self, tmp_path, calar):
        from l2scanner.sessao import ResultadoDoTick

        registro = RegistroEmDisco(tmp_path)
        if calar:
            registro.calar_evento("Solo Boss")
        sessao = self._sessao(tmp_path, [SOLO_BOSS], registro)
        resultado = ResultadoDoTick()
        sessao._processar_agenda(CHAMADA, resultado)
        return resultado.avisos

    def test_o_laco_principal_cala_o_boss(self, tmp_path):
        assert self._avisos_do_tick(tmp_path, calar=False), "o boss deveria chamar"
        assert self._avisos_do_tick(tmp_path / "outra", calar=True) == []

    def test_o_laco_da_agenda_le_os_eventos_calados(self):
        """Tripwire de fonte, o mesmo idioma do teste do relogio monotonico.

        `laco_da_agenda` e um `while True` com rede e sono dentro; le-lo e a
        forma que este repositorio ja usa para provar que uma chamada carrega
        o argumento certo.
        """
        import inspect
        import re

        from l2scanner import __main__ as principal

        fonte = inspect.getsource(principal.laco_da_agenda)
        corpo = fonte[fonte.index("avisos_devidos(") :]
        chamada = re.match(r"avisos_devidos\((.*?)\n\s*\)", corpo, re.S)
        assert chamada, "laco_da_agenda nao chama avisos_devidos em varias linhas"
        assert "eventos_calados" in chamada.group(1), (
            "o laco --so-agenda ignora o desligamento do Solo Boss: o boss "
            "ficaria quieto no vigiar-party.bat e falante no avisos-tvt.bat"
        )


class TestNaCostura:
    """Os dois comandos pelo caminho REAL, de ponta a ponta.

    Um parser paralelo montado aqui provaria que o teste concorda consigo
    mesmo. Isto entra por `atender_comandos` com as cinco travas ligadas.
    """

    TELEFONE = "+5544997077000"

    def _atender(self, tmp_path, texto, registro=None, conversa="1"):
        import time

        from l2scanner.__main__ import atender_comandos
        from l2scanner.notificador import Despachante, NotificadorEmMemoria

        class LeitorFalso:
            ativo = True
            telefones = [TestNaCostura.TELEFONE]
            membros: list = []

            def ler(self, _):
                return [
                    {
                        "id": 909,
                        "content": texto,
                        "message_type": 0,
                        "private": False,
                        "sender": {
                            "name": "Yazalaque",
                            "phone_number": TestNaCostura.TELEFONE,
                        },
                        "conversation_id": conversa,
                    }
                ]

        notificador = NotificadorEmMemoria()
        despachante = Despachante(notificador)
        registro = registro if registro is not None else RegistroEmDisco(tmp_path)
        atender_comandos(
            LeitorFalso(),
            registro,
            [SOLO_BOSS, TVT],
            despachante,
            datetime(2026, 8, 24, 12, 0),
            time.monotonic(),
        )
        despachante.iniciar()
        despachante.encerrar()
        return registro, notificador

    def test_desativarsoloboss_cala_o_evento_de_verdade(self, tmp_path):
        registro, _ = self._atender(tmp_path, "/desativarsoloboss")
        assert registro.eventos_calados() == frozenset({SLUG})

    def test_e_o_gate_morde_no_mesmo_registro(self, tmp_path):
        registro, _ = self._atender(tmp_path, "/desativarsoloboss")
        assert _tipos(CHAMADA, [SOLO_BOSS], registro.eventos_calados()) == []
        assert _tipos(LEMBRETE, [SOLO_BOSS], registro.eventos_calados()) == []

    def test_ativarsoloboss_religa_os_dois(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.calar_evento("Solo Boss")

        self._atender(tmp_path, "/ativarsoloboss", registro=registro)

        assert registro.eventos_calados() == frozenset()
        assert _tipos(CHAMADA, [SOLO_BOSS], registro.eventos_calados()) == [
            TipoDeAviso.CHAMADA
        ]
        assert _tipos(LEMBRETE, [SOLO_BOSS], registro.eventos_calados()) == [
            TipoDeAviso.ANTES
        ]

    def test_o_GRUPO_e_avisado_de_que_o_boss_calou(self, tmp_path):
        """Mesmo racional do `.cancelar` e do `.solo`: muda o que TODO MUNDO
        recebe daqui pra frente. Calar 12 chamadas por dia da party inteira em
        segredo e a versao coletiva do estado escondido."""
        _, notificador = self._atender(tmp_path, "/desativarsoloboss")
        alvos = [alvo for _, alvo in notificador.destinos]
        assert "1" in alvos, "quem pediu nao recebeu confirmacao"
        assert None in alvos, "o grupo nao ficou sabendo que o boss calou"

    def test_o_GRUPO_e_avisado_de_que_o_boss_voltou(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.calar_evento("Solo Boss")
        _, notificador = self._atender(
            tmp_path, "/ativarsoloboss", registro=registro
        )
        assert None in [alvo for _, alvo in notificador.destinos]
