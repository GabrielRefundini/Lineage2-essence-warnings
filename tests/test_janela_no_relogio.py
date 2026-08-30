"""A janela de respawn valendo com o jogo FECHADO — provada no LACO.

POR QUE ESTE ARQUIVO EXISTE SEPARADO DE `tests/test_respawn.py`. Aquele afirma
funcoes PURAS: dado um instante, uma ancora e uma regra, qual aviso vence. Este
afirma que o LACO AS ALCANCA — que o `--so-agenda`, rodando de verdade, chega
ate elas e transforma um arquivo vazio em disco numa mensagem no grupo.

E a distincao que mais custou caro neste repositorio: codigo com teste verde que
o laco nunca chama. Foi assim que o nivel de membro do plano 10-01 nasceu
inalcancavel (`Membro`, `nick_do_membro` e os blocos `[[membro]]` existiam,
tinham teste unitario verde, e `autorizado_para` recusava todo mundo), e foi
assim que o elo do `.pegou` ficou pendurado. Uma funcao pura verde nao prova
nada sobre o modo do usuario.

E O `--so-agenda` E JUSTAMENTE O MODO DE MENOR COBERTURA DO PROJETO — 19-20% —
e foi onde o incidente de 2026-08-26 19:30 aconteceu. Ele tambem e o modo que
faz JANE-05 valer: quem mais precisa saber que a janela do boss abriu e
exatamente quem NAO esta com o jogo aberto.

TUDO AQUI RODA COM O JOGO FECHADO E SEM REDE (OPER-03): o relogio e parado, a
agenda e injetada, o despachante grava em memoria e `time.sleep` levanta
`KeyboardInterrupt` para o laco dar exatamente uma volta.
"""

from __future__ import annotations

import argparse
import ast
import logging
from datetime import datetime
from pathlib import Path

import pytest

from l2scanner.agenda import EventoAgendado
from l2scanner.bosses import Boss
from l2scanner.notificador import Categoria

RAIZ = Path(__file__).resolve().parent.parent

# Os bosses sao CONSTRUIDOS AQUI e nunca lidos do `config.toml` do repositorio:
# aquele arquivo e do usuario e ele o edita, e um teste ancorado nas horas de la
# fica vermelho no dia em que ele trocar 6 por 5, sem defeito nenhum.
NORTH = Boss(nome="Tiat North", respawn_horas_min=6, respawn_horas_max=8)
SOUTH = Boss(nome="Tiat South", respawn_horas_min=6, respawn_horas_max=8)

NASCIMENTO = datetime(2026, 8, 30, 14, 30)

# O NOME DO ARQUIVO DA ANCORA, ESCRITO A MAO E NAO GERADO.
#
# A forma esta registrada em `02-01-SUMMARY.md` e e uma porta de mao unica:
# depois do primeiro arquivo gravado em `.agenda/`, muda-la faz o marcador
# antigo deixar de casar e um aviso ja enviado sair de novo no grupo. Semear
# chamando `chave_do_nascimento` deixaria este teste VERDE PARA SEMPRE, porque
# ele passaria a comparar o produtor consigo mesmo. Escrito a mao, uma mudanca
# de formato fica VERMELHA aqui, que e onde ela precisa aparecer.
ANCORA_EM_DISCO = "nascimento_2026-08-30_tiat-north-1430_chat"
AVISO_DE_ABERTURA = "2026-08-30_tiat-north-1430_abre"
AVISO_DE_LIMITE = "2026-08-30_tiat-north-1430_limite"


def _fonte(arquivo: str) -> str:
    return (RAIZ / "l2scanner" / arquivo).read_text(encoding="utf-8")


def _funcao(arquivo: str, nome: str) -> ast.FunctionDef:
    """A definicao de uma funcao, por AST e nunca por busca textual.

    A razao ja foi escrita tres vezes neste projeto e vale de novo aqui: as
    docstrings desta fase CITAM os nomes proibidos de proposito, para explicar
    por escrito o que a regra proibe. Um `grep` acusaria justamente a
    documentacao que protege a regra.

    Aceita tambem metodos (`Classe.metodo`), pela mesma varredura.
    """
    arvore = ast.parse(_fonte(arquivo))
    curto = nome.rsplit(".", 1)[-1]
    return next(
        no
        for no in ast.walk(arvore)
        if isinstance(no, ast.FunctionDef) and no.name == curto
    )


def _funcao_do_main(nome: str) -> ast.FunctionDef:
    return _funcao("__main__.py", nome)


def _chamadas(no: ast.AST, alvo: str) -> list[ast.Call]:
    """Toda chamada a `alvo` na subarvore, seja `alvo(...)` ou `x.alvo(...)`."""
    return [
        filho
        for filho in ast.walk(no)
        if isinstance(filho, ast.Call)
        and (
            getattr(filho.func, "id", None) == alvo
            or getattr(filho.func, "attr", None) == alvo
        )
    ]


def _chama(no: ast.AST, alvo: str) -> bool:
    return bool(_chamadas(no, alvo))


class RelogioParado:
    """O relogio de verdade pergunta a hora ao Chatwoot. Este nao pergunta nada.

    Sem ele o teste dependeria do `.env` do usuario e da rede — as duas coisas
    que OPER-03 proibe.
    """

    def __init__(self, quando: datetime) -> None:
        self._quando = quando

    def agora(self) -> datetime:
        return self._quando


class DespachanteQueGrava:
    """Grava `(texto, categoria)` em memoria, no molde do falso de
    `tests/test_presenca.py`.

    As afirmacoes ficam sobre ESTRUTURA — quantos despachos, com qual categoria
    — e nao sobre o texto do log, que e frouxo e muda com a redacao.
    """

    def __init__(self) -> None:
        self.despachos: list[tuple[str, object, object]] = []

    def iniciar(self) -> None:  # pragma: no cover - o laco chama, nada faz
        pass

    def encerrar(self) -> None:  # pragma: no cover - idem
        pass

    def despachar(self, texto, categoria=None, conversa_alvo=None) -> None:
        self.despachos.append((texto, categoria, conversa_alvo))

    @property
    def textos(self) -> list[str]:
        return [texto for texto, _, _ in self.despachos]


def uma_volta_do_laco_da_agenda(
    monkeypatch,
    tmp_path,
    quando: datetime,
    *,
    eventos=(),
    bosses=(),
    dry_run=False,
    despachante=None,
):
    """Uma unica volta do `laco_da_agenda`, com o relogio parado.

    Reusa a FORMA de `tests/test_agenda.py::TestSimulacaoNoLacoDaAgenda._tick`,
    acrescentando a troca de `ler_bosses` e um despachante que grava. Devolve
    `(codigo, pasta, despachante)`.
    """
    from l2scanner import __main__ as principal

    if despachante is None:
        despachante = DespachanteQueGrava()

    pasta = tmp_path / ".agenda"
    monkeypatch.setattr(principal, "PASTA_AGENDA", pasta)
    monkeypatch.setattr(principal, "PASTA_LOOT", tmp_path / ".loot")
    monkeypatch.setattr(principal, "ler_agenda", lambda *a, **k: list(eventos))
    monkeypatch.setattr(principal, "ler_bosses", lambda *a, **k: list(bosses))
    monkeypatch.setattr(
        principal, "montar_relogio", lambda *a, **k: RelogioParado(quando)
    )
    monkeypatch.setattr(principal, "montar_despachante", lambda *a, **k: despachante)
    # Os dois montadores leem o `.env`. Aqui o que esta em julgamento e o disco
    # e o despacho, nao a entrega.
    monkeypatch.setattr(principal, "montar_leitor_de_comandos", lambda *a, **k: None)

    def uma_volta_so(_segundos):
        # O laco so sai por KeyboardInterrupt, e ele ja trata e devolve 0.
        raise KeyboardInterrupt

    monkeypatch.setattr(principal.time, "sleep", uma_volta_so)

    args = argparse.Namespace(dry_run=dry_run, intervalo=0)
    return principal.laco_da_agenda(args), pasta, despachante


def semear_ancora(pasta) -> None:
    """Escreve o marcador VAZIO da ancora direto na pasta.

    O arquivo e vazio de proposito: e a mesma propriedade que faz a criacao
    atomica (`O_CREAT|O_EXCL`) ser a decisao de despacho inteira.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / ANCORA_EM_DISCO).touch()


class TestAJanelaComOJogoFechado:
    """JANE-02 e JANE-05 no laco do relogio: a fatia inteira, sem tela.

    O usuario com o jogo fechado, o PC ligado e `run-agenda.bat` rodando recebe
    no WhatsApp que a janela do Tiat abriu, seis horas depois de um nascimento
    que ele talvez nem tenha visto.
    """

    def test_no_instante_da_abertura_sai_exatamente_um_despacho(
        self, monkeypatch, tmp_path
    ):
        pasta = tmp_path / ".agenda"
        semear_ancora(pasta)

        codigo, _, despachante = uma_volta_do_laco_da_agenda(
            monkeypatch, tmp_path, NASCIMENTO.replace(hour=20, minute=30),
            bosses=[NORTH],
        )

        assert codigo == 0
        assert len(despachante.despachos) == 1, despachante.textos
        texto, categoria, _ = despachante.despachos[0]
        assert "Tiat North" in texto
        assert "14:30" in texto, "a mensagem nao cita o nascimento que a ancorou"
        # D-23: o aviso atravessa o silencio do Prime. Um boss nascendo durante
        # o Prime e exatamente a informacao que ninguem quer perder.
        assert categoria is Categoria.SEMPRE

    def test_no_instante_do_limite_sai_o_outro_despacho(self, monkeypatch, tmp_path):
        """`respawn_horas_max = 8`: 14:30 + 8h = 22:30."""
        pasta = tmp_path / ".agenda"
        semear_ancora(pasta)

        _, _, despachante = uma_volta_do_laco_da_agenda(
            monkeypatch, tmp_path, NASCIMENTO.replace(hour=22, minute=30),
            bosses=[NORTH],
        )

        assert len(despachante.despachos) == 1, despachante.textos
        assert "limite otimista" in despachante.textos[0]

    def test_a_mensagem_do_limite_e_diferente_da_da_abertura(
        self, monkeypatch, tmp_path
    ):
        """Duas mensagens iguais para dois fatos diferentes seria o mesmo que
        uma so."""
        abertura = tmp_path / "abre"
        limite = tmp_path / "limite"
        semear_ancora(abertura / ".agenda")
        semear_ancora(limite / ".agenda")

        _, _, um = uma_volta_do_laco_da_agenda(
            monkeypatch, abertura, NASCIMENTO.replace(hour=20, minute=30),
            bosses=[NORTH],
        )
        _, _, outro = uma_volta_do_laco_da_agenda(
            monkeypatch, limite, NASCIMENTO.replace(hour=22, minute=30),
            bosses=[NORTH],
        )

        assert um.textos and outro.textos
        assert um.textos[0] != outro.textos[0]

    def test_um_minuto_antes_da_abertura_o_laco_fica_mudo(
        self, monkeypatch, tmp_path
    ):
        """Antes de `min` o boss NAO nasce. Um aviso antecipado treinaria a
        party a ir cedo e a nao achar nada."""
        semear_ancora(tmp_path / ".agenda")

        _, _, despachante = uma_volta_do_laco_da_agenda(
            monkeypatch, tmp_path, NASCIMENTO.replace(hour=20, minute=29),
            bosses=[NORTH],
        )

        assert despachante.despachos == []

    def test_tres_horas_depois_do_vencimento_o_aviso_nao_ressuscita(
        self, monkeypatch, tmp_path
    ):
        """D-22 afirmado no LACO, e nao so na funcao pura.

        Um aviso vencido as 20:30 chegando quando o usuario sobe o scanner as
        23:30 seria pior que nenhum: ele diria "a janela abriu" sobre um fato
        de tres horas atras, e a party sairia atras de um boss que ja pode ter
        nascido e morrido.
        """
        semear_ancora(tmp_path / ".agenda")

        _, _, despachante = uma_volta_do_laco_da_agenda(
            monkeypatch, tmp_path, NASCIMENTO.replace(hour=23, minute=30),
            bosses=[NORTH],
        )

        assert despachante.despachos == []

    def test_uma_segunda_volta_sobre_a_mesma_pasta_nao_repete(
        self, monkeypatch, tmp_path
    ):
        """JANE-06 no laco: o `marcar` E a decisao de despachar (D-21).

        A segunda volta esta DENTRO da tolerancia de cinco minutos (20:31), que
        e onde a repeticao aconteceria se a decisao nao fosse o marcador.
        """
        pasta = tmp_path / ".agenda"
        semear_ancora(pasta)

        uma_volta_do_laco_da_agenda(
            monkeypatch, tmp_path, NASCIMENTO.replace(hour=20, minute=30),
            bosses=[NORTH],
        )
        _, _, segundo = uma_volta_do_laco_da_agenda(
            monkeypatch, tmp_path, NASCIMENTO.replace(hour=20, minute=31),
            bosses=[NORTH],
        )

        assert segundo.despachos == []
        aberturas = [c for c in pasta.iterdir() if c.name == AVISO_DE_ABERTURA]
        assert len(aberturas) == 1
        assert not (pasta / AVISO_DE_LIMITE).exists()

    def test_um_boss_sem_ancora_nao_produz_nada(self, monkeypatch, tmp_path):
        """Guarda contra prova vazia pelo outro lado: sem ancora nao ha
        previsao, e o silencio aqui e a resposta correta."""
        _, pasta, despachante = uma_volta_do_laco_da_agenda(
            monkeypatch, tmp_path, NASCIMENTO.replace(hour=20, minute=30),
            bosses=[NORTH],
        )

        assert despachante.despachos == []


class TestOModoDeSimulacaoNaJanela:
    """JANE-06 / D-21: o `--dry-run` mostra e NAO queima o marcador.

    E o incidente de 2026-08-26 19:30 aplicado ao namespace novo. A guarda ja
    mora no lugar certo (`RegistroEmDisco(..., simulando=args.dry_run)` no
    arranque do laco), e o shell novo nao conhece `dry_run` e nao pode conhecer
    — mas isso so vale se o laco realmente ALCANCAR o aviso de janela.
    """

    def test_em_simulacao_o_texto_sai_e_a_pasta_nao_e_criada(
        self, monkeypatch, tmp_path, caplog
    ):
        """A `.agenda/` e semeada em OUTRA pasta e a real nem existe.

        Como o `--dry-run` nao pode escrever, a unica forma de ele ter uma
        ancora para ler e ela ja estar la. Aqui a ancora e semeada na pasta que
        o laco vai usar, e a afirmacao passa a ser sobre o AVISO nao ter sido
        gravado.
        """
        pasta = tmp_path / ".agenda"
        semear_ancora(pasta)

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            _, _, despachante = uma_volta_do_laco_da_agenda(
                monkeypatch, tmp_path, NASCIMENTO.replace(hour=20, minute=30),
                bosses=[NORTH], dry_run=True,
            )

        assert "Tiat North" in caplog.text, "a simulacao nao mostrou nada"
        assert not (pasta / AVISO_DE_ABERTURA).exists(), (
            "o --dry-run queimou o marcador da janela: o aviso de verdade "
            "nunca sairia"
        )

    def test_em_simulacao_uma_pasta_inexistente_continua_inexistente(
        self, monkeypatch, tmp_path
    ):
        """Sem ancora nao ha aviso, e o disco tem que continuar intocado."""
        _, pasta, _ = uma_volta_do_laco_da_agenda(
            monkeypatch, tmp_path, NASCIMENTO.replace(hour=20, minute=30),
            bosses=[NORTH], dry_run=True,
        )

        assert not pasta.exists(), "a simulacao criou a .agenda/ compartilhada"


class TestOArranqueComBossESemEvento:
    """T-02-14: quem so vigia boss e o publico INTEIRO de JANE-05.

    Ate a Fase 2 o `--so-agenda` recusava subir sem nenhum `[[evento]]`, e a
    partir daqui isso esta errado: um usuario que so configurou `[[boss]]`
    ficaria sem o unico modo que entrega a janela com o jogo fechado.
    """

    def test_com_boss_e_sem_evento_o_laco_sobe(self, monkeypatch, tmp_path):
        codigo, _, _ = uma_volta_do_laco_da_agenda(
            monkeypatch, tmp_path, NASCIMENTO.replace(hour=20, minute=30),
            eventos=[], bosses=[NORTH, SOUTH],
        )

        assert codigo == 0, (
            "quem so configurou [[boss]] ficou sem o modo do relogio"
        )

    def test_sem_evento_e_sem_boss_o_laco_continua_recusando(
        self, monkeypatch, tmp_path, caplog
    ):
        """Guarda contra prova vazia: a recusa nao foi apagada, foi
        estreitada."""
        with caplog.at_level(logging.ERROR, logger="l2scanner"):
            codigo, _, _ = uma_volta_do_laco_da_agenda(
                monkeypatch, tmp_path, NASCIMENTO, eventos=[], bosses=[],
            )

        assert codigo == 2

    def test_a_recusa_cita_as_DUAS_portas_de_entrada(
        self, monkeypatch, tmp_path, caplog
    ):
        """Uma mensagem que so fala de `[[evento]]` mandaria o usuario
        configurar a coisa errada."""
        with caplog.at_level(logging.ERROR, logger="l2scanner"):
            uma_volta_do_laco_da_agenda(
                monkeypatch, tmp_path, NASCIMENTO, eventos=[], bosses=[],
            )

        assert "[[evento]]" in caplog.text
        assert "[[boss]]" in caplog.text

    def test_com_evento_e_sem_boss_nada_mudou(self, monkeypatch, tmp_path):
        """O caminho que ja existia desde a Fase 6 continua igual."""
        codigo, _, despachante = uma_volta_do_laco_da_agenda(
            monkeypatch, tmp_path, NASCIMENTO,
            eventos=[EventoAgendado(nome="TvT", horarios=((19, 30),))],
            bosses=[],
        )

        assert codigo == 0
        assert despachante.despachos == []


class TestOShellDoSoAgenda:
    """`_avisar_janelas_de_respawn` sozinho, sem o laco em volta.

    O molde e `_fechar_listas_de_presenca`: loga SEMPRE, despacha se houver
    para onde.
    """

    def _registro(self, tmp_path, com_ancora=True):
        from l2scanner.agenda import RegistroEmDisco

        pasta = tmp_path / ".agenda"
        if com_ancora:
            semear_ancora(pasta)
        return RegistroEmDisco(pasta)

    def test_sem_despachante_a_mensagem_ainda_aparece_no_log(
        self, tmp_path, caplog
    ):
        """Quem roda sem `.env` e sem `--dry-run` nao pode perder a mensagem.

        E a mesma separacao que o laco ja faz com o encerramento de silencio e
        com a lista fechada.
        """
        from l2scanner.__main__ import _avisar_janelas_de_respawn

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            avisos = _avisar_janelas_de_respawn(
                self._registro(tmp_path),
                [NORTH],
                NASCIMENTO.replace(hour=20, minute=30),
                None,
            )

        assert len(avisos) == 1
        assert "Tiat North" in caplog.text

    def test_devolve_os_avisos_para_o_chamador_afirmar(self, tmp_path):
        from l2scanner.__main__ import _avisar_janelas_de_respawn
        from l2scanner.respawn import TipoDeJanela

        avisos = _avisar_janelas_de_respawn(
            self._registro(tmp_path),
            [NORTH],
            NASCIMENTO.replace(hour=20, minute=30),
            DespachanteQueGrava(),
        )

        assert [a.tipo for a in avisos] == [TipoDeJanela.ABRE]
        assert avisos[0].boss == "Tiat North"

    def test_sem_janela_devida_nao_loga_nem_despacha(self, tmp_path, caplog):
        from l2scanner.__main__ import _avisar_janelas_de_respawn

        despachante = DespachanteQueGrava()
        with caplog.at_level(logging.INFO, logger="l2scanner"):
            avisos = _avisar_janelas_de_respawn(
                self._registro(tmp_path, com_ancora=False),
                [NORTH],
                NASCIMENTO.replace(hour=20, minute=30),
                despachante,
            )

        assert avisos == []
        assert despachante.despachos == []
        assert not [r for r in caplog.records if "Tiat North" in r.getMessage()]


class TestAPrevisaoNoArranque:
    """OPER-02 chegando ao console dos DOIS lacos.

    Quem sobe o scanner ve, na primeira tela, quais bosses estao sendo vigiados
    e quando a janela de cada um abre — e ve escrito, sem previsao inventada, de
    quais deles o scanner ainda nao viu nascimento nenhum.
    """

    def _registro(self, tmp_path, com_ancora=True):
        from l2scanner.agenda import RegistroEmDisco

        pasta = tmp_path / ".agenda"
        if com_ancora:
            semear_ancora(pasta)
        return RegistroEmDisco(pasta)

    def test_o_shell_loga_uma_linha_por_boss(self, tmp_path, caplog):
        from l2scanner.__main__ import _anunciar_previsao_de_janelas

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            _anunciar_previsao_de_janelas(
                self._registro(tmp_path), [NORTH, SOUTH], NASCIMENTO
            )

        mensagens = [r.getMessage() for r in caplog.records]
        assert any("Tiat North" in m for m in mensagens)
        assert any("Tiat South" in m for m in mensagens)

    def test_o_shell_nao_diz_nada_sem_boss_configurado(self, tmp_path, caplog):
        """`montar_vigia_de_bosses` ja diz que a vigilancia esta desligada, e
        com o texto que ensina a ligar. Repetir treinaria o usuario a
        ignorar."""
        from l2scanner.__main__ import _anunciar_previsao_de_janelas

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            _anunciar_previsao_de_janelas(
                self._registro(tmp_path, com_ancora=False), [], NASCIMENTO
            )

        assert caplog.records == []

    def test_o_laco_da_agenda_emite_as_duas_linhas_no_arranque(
        self, monkeypatch, tmp_path, caplog
    ):
        """As duas linhas, e ANTES de qualquer despacho.

        A previsao e a primeira tela: ela existe para o usuario saber o que
        esperar antes de o scanner comecar a falar.
        """
        semear_ancora(tmp_path / ".agenda")

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            _, _, despachante = uma_volta_do_laco_da_agenda(
                monkeypatch, tmp_path, NASCIMENTO.replace(hour=20, minute=30),
                bosses=[NORTH, SOUTH],
            )

        mensagens = [r.getMessage() for r in caplog.records]
        com_ancora = next(
            i for i, m in enumerate(mensagens)
            if "Tiat North" in m and "30/08 20:30" in m
        )
        sem_ancora = next(
            i for i, m in enumerate(mensagens)
            if "Tiat South" in m and "nascimento" in m
        )
        assert not any(c.isdigit() for c in mensagens[sem_ancora]), (
            "a linha de quem nao tem ancora inventou uma previsao"
        )

        assert len(despachante.despachos) == 1
        # A frase do WhatsApp, e nao "a janela abriu": a linha de previsao
        # tambem contem esse pedaco, e casar por ele acharia a propria previsao.
        despachada = next(
            i for i, m in enumerate(mensagens)
            if "Antes de agora ele nao nascia" in m
        )
        assert com_ancora < despachada and sem_ancora < despachada, (
            "a previsao do arranque saiu depois do primeiro aviso"
        )

    def test_o_laco_da_agenda_repete_a_previsao_de_hora_em_hora(self):
        """Lido por AST, no molde do proprio `_anunciar_proximo` ao lado.

        O `--so-agenda` roda por DIAS, e um scanner que nao diz quando vai
        falar de novo e indistinguivel de um travado. Repetir so o proximo
        evento deixaria de fora justamente a informacao deste workstream.
        """
        laco = _funcao_do_main("laco_da_agenda")
        blocos_horarios = [
            no
            for no in ast.walk(laco)
            if isinstance(no, ast.If)
            and _chama(no, "_anunciar_proximo")
        ]
        assert blocos_horarios, "o bloco horario sumiu do laco_da_agenda"
        assert any(
            _chama(bloco, "_anunciar_previsao_de_janelas")
            for bloco in blocos_horarios
        ), (
            "a previsao de janela nao e repetida de hora em hora: depois de um "
            "dia rodando, o console nao diz mais nada sobre os bosses"
        )

    def test_o_laco_principal_anuncia_a_previsao_FORA_de_qualquer_condicao(self):
        """Deliberadamente fora de `montar_vigia_de_bosses`, e por que.

        A previsao depende SO da ancora em disco e do relogio, entao ela tem que
        sair mesmo com o vigia desligado por falta de calibracao ou de OCR.
        Amarra-la ao vigia faria uma calibracao quebrada APAGAR, em silencio, a
        previsao de uma ancora que continua correta em disco — que e a mesma
        razao pela qual `Sessao` recebe `regras_de_respawn` separado de
        `bosses`.

        Afirmado por AST sobre a POSICAO da chamada: ela e uma instrucao do
        corpo do `laco_principal`, e nao um ramo de `if`. Rodar uma volta do
        laco principal exigiria calibracao, captura e um frame — e um teste que
        precisa do jogo aberto nao prova OPER-03.
        """
        laco = _funcao_do_main("laco_principal")

        assert _chama(laco, "_anunciar_previsao_de_janelas"), (
            "laco_principal nunca anuncia a previsao de janela"
        )
        condicionais = [
            no for no in ast.walk(laco)
            if isinstance(no, (ast.If, ast.Try))
            and _chama(no, "_anunciar_previsao_de_janelas")
        ]
        assert condicionais == [], (
            "a previsao de janela do laco principal esta dentro de uma "
            "condicao: uma calibracao quebrada apagaria a previsao de uma "
            "ancora que continua correta em disco"
        )
