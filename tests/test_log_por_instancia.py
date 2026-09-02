"""Um arquivo de log por instancia, e a suite fora do log de producao.

O DEFEITO DE CAMPO, COM O TRACEBACK QUE O USUARIO COLOU
=======================================================
O usuario roda DUAS instancias do scanner (Yazalaque e Faerlina) lado a lado,
por desenho e desde a Fase 1 - e a razao inteira de AGEN-07 existir. As duas
apontavam o MESMO `RotatingFileHandler` para `logs/scanner.log`. No Windows,
`os.rename` de um arquivo que outro processo mantem ABERTO falha, entao a
rotacao morria assim:

    --- Logging error ---
    Traceback (most recent call last):
      File "...\\logging\\handlers.py", line 74, in emit
        self.doRollover()
      File "...\\logging\\handlers.py", line 179, in doRollover
        self.rotate(self.baseFilename, dfn)
      File "...\\logging\\handlers.py", line 115, in rotate
        os.rename(source, dest)
    PermissionError: [WinError 32] O arquivo ja esta sendo usado por outro
    processo: 'logs\\scanner.log' -> 'logs\\scanner.log.1'
    Message: '\\n%s'
    Arguments: ('[vigiando]',)

E nao acontecia uma vez: acontecia A CADA LINHA logada depois de o arquivo
passar do limite, porque `BaseRotatingHandler.emit` chama `shouldRollover` toda
vez e o arquivo nunca encolhia. O console do usuario ficava inundado, e o
`[vigiando]` que ele deveria estar lendo se perdia no meio dos tracebacks. Pior:
o registro daquela linha era PERDIDO - `emit` cai no `handleError` e nunca chega
ao `FileHandler.emit`.

O CUSTO MEDIDO DA SUITE ESCREVENDO NO LOG DE PRODUCAO
======================================================
Um log sem dono fez a pericia perseguir defeito inexistente DUAS vezes num
unico dia (2026-09-02):

  1. `Presenca: 2 party-mate(s) ... (Korzis, J4guar)` mais
     `CHATWOOT_TELEFONES_COMANDO vazio, qualquer remetente alcanca TODO comando`
     quase viraram um relato de "ha um scanner sem contencao de seguranca em
     campo". Era saida da SUITE DE TESTES, escrevendo no mesmo
     `logs/scanner.log`.
  2. `Aprendi uma assinatura nova ... confianca 0.7492` quase virou uma acusacao
     de que o aprendiz gravava duplicata em campo. O `0.7492` era a fixture de
     `tests/test_aprendiz.py`.

E na mesma noite, investigando a party sumindo de verdade, nao houve como
distinguir se os blocos `[vigiando]` VAZIOS eram da instancia do Yazalaque
(defeito) ou da Faerlina, que nao esta em party nenhuma (normal). A pericia
parou ali.

MEDIDO NESTA ARVORE, antes do conserto: uma rodada completa da suite criava
`logs/scanner.log` com 654.907 bytes MAIS um `logs/scanner.log.1` de 2.000.709
bytes. Ou seja, a suite nao so sujava o log de campo: ela ROTACIONAVA, e cada
rodada empurrava duas horas de farm real para fora da janela de tres backups.

As tres portas por onde a suite entrava, achadas instrumentando o construtor do
`RotatingFileHandler` e nomeando o teste corrente:

    tests/test_aprendiz.py::TestARecusaAcontecENoARRANQUE
        ::test_main_chamada_de_verdade_devolve_2_com_o_jogo_fechado
    tests/test_aprendiz.py::TestARecusaAcontecENoARRANQUE
        ::test_um_config_bom_nao_impede_o_arranque
    tests/test_bosses.py::TestOArranque
        ::test_um_bloco_torto_derruba_o_arranque_com_codigo_2

Sao TRES construtores e 2,6 MB de saida porque o manipulador ficava INSTALADO
no logger `l2scanner` depois que o teste terminava: as outras ~5300 linhas de
teste que logam por ele iam junto para o arquivo de producao.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pytest

from l2scanner.raiz import RAIZ
from l2scanner.registro_de_log import (
    ARQUIVO_PADRAO,
    ArquivoRotativoTolerante,
    montar_arquivo_rotativo,
    nome_da_instancia,
    nome_do_arquivo_de_log,
)


def _calibracao(pasta: Path, **campos) -> Path:
    alvo = pasta / "calibration.json"
    alvo.write_text(json.dumps(campos), encoding="utf-8")
    return alvo


class TestONomeSaiDoPersonagem:
    """O criterio de nome, e as tres alternativas recusadas com a razao.

    RECUSADO: O PID. Um `scanner-24316.log` nasce a cada arranque, entao
    `backupCount=3` passa a cobrir tres arquivos de nada e `scanner.log.1` para
    de significar "a hora anterior". E ninguem procurando "o log do Yazalaque"
    reconhece um numero de processo - que muda toda vez que ele fecha o jogo.

    RECUSADO: O TITULO INTEIRO DA JANELA. `Yazalaque - XM Essence.log` poe
    espaco e hifen-com-espacos no nome do arquivo, e a metade ` - XM Essence` e
    IDENTICA nas duas instancias: ela nao carrega informacao nenhuma que
    distinga uma da outra. Titulo de janela tambem aceita `:` e `?`, que o
    Windows recusa em nome de arquivo.

    ESCOLHIDO: O NOME DO PERSONAGEM. Sobrevive a reinicio (mesmo personagem =
    mesmo arquivo = a rotacao volta a acumular historia de verdade), e legivel
    para um humano procurando "o log do Yazalaque", e e exatamente o campo que
    o usuario ja digita para separar as duas instancias.
    """

    def test_o_titulo_da_janela_vira_o_nome_do_personagem(self):
        assert nome_da_instancia("Yazalaque - XM Essence") == "Yazalaque"
        assert nome_do_arquivo_de_log("Yazalaque - XM Essence") == (
            "scanner-Yazalaque.log"
        )

    def test_as_duas_instancias_nunca_compartilham_o_arquivo(self):
        """O defeito inteiro em uma assercao."""
        um = nome_do_arquivo_de_log("Yazalaque - XM Essence")
        outro = nome_do_arquivo_de_log("Faerlina - XM Essence")

        assert um != outro, "duas instancias no mesmo arquivo e o WinError 32"

    def test_o_nome_sobrevive_a_reinicio(self):
        """A recusa do PID, medida em vez de afirmada.

        Duas chamadas no mesmo processo ja seriam iguais com PID. O que este
        caso prende e que o PID nao aparece NO NOME - e por isso o proximo
        arranque, com outro PID, cai no MESMO arquivo e continua a rotacao.
        """
        nome = nome_do_arquivo_de_log("Yazalaque - XM Essence")

        assert str(os.getpid()) not in nome
        assert nome == nome_do_arquivo_de_log("Yazalaque - XM Essence")

    def test_janela_AUTO_cai_na_calibracao_em_disco(self, tmp_path):
        """`vigiar-party.bat` passa `--janela` SEM valor, que vira "AUTO".

        Esse e o arranque mais comum do usuario, entao um criterio que so
        funcionasse com o titulo explicito deixaria a instancia principal sem
        nome - e as duas de volta no mesmo arquivo.
        """
        alvo = _calibracao(tmp_path, nome_proprio="Yazalaque")

        assert nome_do_arquivo_de_log("AUTO", alvo) == "scanner-Yazalaque.log"

    def test_sem_janela_nenhuma_a_calibracao_ainda_decide(self, tmp_path):
        """O caminho `mss`, sem `--janela` nenhum, tambem tem dono."""
        alvo = _calibracao(tmp_path, nome_proprio="Faerlina")

        assert nome_do_arquivo_de_log(None, alvo) == "scanner-Faerlina.log"

    def test_a_calibracao_sem_nome_proprio_cai_no_titulo_gravado(self, tmp_path):
        """`calibrar.py:1544` deriva um do outro; aqui a ordem e a mesma."""
        alvo = _calibracao(tmp_path, janela="Faerlina - XM Essence")

        assert nome_do_arquivo_de_log("AUTO", alvo) == "scanner-Faerlina.log"

    def test_sem_nada_para_ir_o_nome_continua_o_de_hoje(self, tmp_path):
        """Sem regressao para quem roda UMA instancia e nunca calibrou nome.

        `scanner.log` continua sendo o arquivo, entao o historico de campo que
        ja esta em `logs/scanner.log`, `.1` e `.3` continua sendo lido e
        continuado - nao ha migracao, nao ha renomeacao, nao ha perda.
        """
        assert nome_do_arquivo_de_log(None, tmp_path / "nao-existe.json") == (
            ARQUIVO_PADRAO
        )
        assert ARQUIVO_PADRAO == "scanner.log"

    def test_calibracao_ilegivel_nao_levanta(self, tmp_path):
        """Decidir o nome do log nunca pode derrubar o arranque.

        `Calibracao.carregar` recusa arquivo torto com codigo 2 e uma mensagem
        - e ESSA mensagem precisa de um manipulador de log ja instalado para
        chegar ao usuario. Se a espiada aqui levantasse, a recusa sairia como
        traceback cru, que e o desfecho que `CalibracaoInvalida` existe para
        evitar.
        """
        torto = tmp_path / "calibration.json"
        torto.write_text("{ isto nao e json", encoding="utf-8")

        assert nome_do_arquivo_de_log("AUTO", torto) == ARQUIVO_PADRAO

    def test_calibracao_que_nao_e_dicionario_nao_levanta(self, tmp_path):
        lista = tmp_path / "calibration.json"
        lista.write_text("[1, 2, 3]", encoding="utf-8")

        assert nome_do_arquivo_de_log("AUTO", lista) == ARQUIVO_PADRAO

    @pytest.mark.parametrize(
        "titulo",
        [
            'Ya:za?la*que - XM Essence',
            "..\\..\\Yazalaque - XM Essence",
            "Yaza/laque - XM Essence",
        ],
    )
    def test_caractere_proibido_pelo_windows_nao_chega_ao_nome(self, titulo):
        """Titulo de janela e texto de TERCEIRO: o jogo escreve o que quiser.

        Sem peneira, um `:` levanta `OSError` na abertura do arquivo e o
        scanner nao sobe; um `..\\` escreveria FORA de `logs/`.
        """
        nome = nome_do_arquivo_de_log(titulo)

        assert not (set(nome) & set(':?*/\\<>|"')), nome
        assert nome.startswith("scanner-") and nome.endswith(".log")

    def test_titulo_so_de_lixo_cai_no_padrao(self):
        """Peneirar tudo nao pode deixar um `scanner-.log` orfao."""
        assert nome_do_arquivo_de_log("??? - XM Essence") == ARQUIVO_PADRAO

    def test_nome_absurdamente_longo_e_cortado(self):
        nome = nome_do_arquivo_de_log("Y" * 500 + " - XM Essence")

        assert len(nome) < 100, "nome de arquivo tem limite no Windows"


class TestARotacaoQueFalhaNaoInunda:
    """O desfecho escolhido para o `PermissionError` de rotacao, e por que.

    ESCOLHIDO: DESISTIR DA ROTACAO, CONTINUAR ESCREVENDO, AVISAR UMA VEZ.

    As alternativas, e por que cada uma e pior:

      - Deixar o traceback sair (hoje): inunda o console a cada linha logada e
        PERDE o registro, porque `emit` desvia para `handleError` antes de
        chegar ao `FileHandler.emit`. Perder a linha `[vigiando]` de um farm de
        tres horas e o oposto do que o arquivo de log existe para fazer.
      - Calar o erro sem avisar: o arquivo cresce sem teto e ninguem sabe.
        Silencio treina o usuario a confiar num sinal que nao significa mais
        nada, que e a mesma doutrina que `avisar_falha` ja segue na entrega.
      - Derrubar o scanner: um problema de LOG nao pode matar a vigilancia da
        party. O log e o acessorio; o alerta de morte e o produto.

    Com um arquivo por instancia isto vira raro, mas nao impossivel: o usuario
    pode subir dois scanners do MESMO personagem por engano, e ai os dois
    apontam para o mesmo caminho de novo.
    """

    def _handler(self, tmp_path, **kw):
        return ArquivoRotativoTolerante(
            tmp_path / "scanner.log", maxBytes=100, backupCount=3,
            encoding="utf-8", **kw
        )

    def _log(self, handler, quantas):
        registro = logging.getLogger("teste-da-rotacao")
        registro.handlers[:] = [handler]
        registro.propagate = False
        registro.setLevel(logging.INFO)
        for i in range(quantas):
            registro.info("linha %d com corpo suficiente para passar do limite", i)
        handler.flush()

    def test_a_rotacao_normal_continua_funcionando(self, tmp_path):
        """Guarda contra prova vazia: sem isto, tudo abaixo passaria por
        rotacao nunca acontecer."""
        handler = self._handler(tmp_path)
        try:
            self._log(handler, 20)
        finally:
            handler.close()

        assert (tmp_path / "scanner.log.1").exists(), "a rotacao tem de rotacionar"
        assert not handler.rotacao_desistiu

    def test_a_linha_nao_e_perdida_quando_a_rotacao_falha(
        self, tmp_path, monkeypatch, capsys
    ):
        """O que o stdlib faz de pior: alem de gritar, ele ENGOLE o registro."""
        monkeypatch.setattr(
            os, "rename", lambda *_a, **_k: (_ for _ in ()).throw(
                PermissionError(32, "usado por outro processo")
            )
        )
        handler = self._handler(tmp_path)
        try:
            self._log(handler, 20)
        finally:
            handler.close()

        escrito = (tmp_path / "scanner.log").read_text(encoding="utf-8")
        for i in range(20):
            assert f"linha {i} " in escrito, f"a linha {i} sumiu na rotacao falha"

    def test_avisa_uma_vez_so_e_nao_por_linha(self, tmp_path, monkeypatch, capsys):
        """O sintoma inteiro: um traceback POR LINHA logada, para sempre."""
        monkeypatch.setattr(
            os, "rename", lambda *_a, **_k: (_ for _ in ()).throw(
                PermissionError(32, "usado por outro processo")
            )
        )
        handler = self._handler(tmp_path)
        try:
            self._log(handler, 50)
        finally:
            handler.close()

        erro = capsys.readouterr().err
        assert erro.count("rotacionar") == 1, erro
        assert "Traceback" not in erro
        assert "--- Logging error ---" not in erro

    def test_para_de_tentar_rotacionar(self, tmp_path, monkeypatch):
        """A desistencia e ESTRUTURAL, e nao um contador de avisos.

        `maxBytes = 0` faz `shouldRollover` do stdlib devolver `False` para
        sempre - entao `doRollover` nao e chamado de novo nem uma vez, e nao ha
        50 tentativas silenciosas de renomear a cada tick de 1 Hz.
        """
        monkeypatch.setattr(
            os, "rename", lambda *_a, **_k: (_ for _ in ()).throw(
                PermissionError(32, "usado por outro processo")
            )
        )
        handler = self._handler(tmp_path)
        try:
            self._log(handler, 20)

            assert handler.rotacao_desistiu
            assert handler.maxBytes == 0
        finally:
            handler.close()

    def test_o_aviso_diz_o_conserto_e_nao_so_o_erro(
        self, tmp_path, monkeypatch, capsys
    ):
        """Uma mensagem que nao diz o que fazer e so um susto."""
        monkeypatch.setattr(
            os, "rename", lambda *_a, **_k: (_ for _ in ()).throw(
                PermissionError(32, "usado por outro processo")
            )
        )
        handler = self._handler(tmp_path)
        try:
            self._log(handler, 20)
        finally:
            handler.close()

        erro = capsys.readouterr().err
        assert "--janela" in erro, "o conserto e dar um nome proprio a instancia"
        assert "scanner.log" in erro, "qual arquivo, e nao 'um arquivo'"

    def test_o_aviso_tambem_fica_no_proprio_log(self, tmp_path, monkeypatch, capsys):
        """A pericia acontece DEPOIS, lendo o arquivo - nao no console vivo.

        Um log que parou de rotacionar e um log que pode ter engolido o resto
        da sessao. Quem abrir o arquivo seis meses depois precisa ver isso ali,
        e nao num console que ja fechou.
        """
        monkeypatch.setattr(
            os, "rename", lambda *_a, **_k: (_ for _ in ()).throw(
                PermissionError(32, "usado por outro processo")
            )
        )
        handler = self._handler(tmp_path)
        try:
            self._log(handler, 20)
        finally:
            handler.close()

        escrito = (tmp_path / "scanner.log").read_text(encoding="utf-8")
        assert escrito.count("rotacionar") == 1, escrito[-2000:]

    def test_qualquer_OSError_de_rotacao_e_tratado(self, tmp_path, monkeypatch):
        """Disco cheio e antivirus travando o arquivo caem no mesmo lugar.

        `PermissionError` e so o caso do Windows com duas instancias. Prender
        so ele deixaria `OSError` cru voltando a inundar o console.
        """
        monkeypatch.setattr(
            os, "rename", lambda *_a, **_k: (_ for _ in ()).throw(
                OSError(28, "disco cheio")
            )
        )
        handler = self._handler(tmp_path)
        try:
            self._log(handler, 20)

            assert handler.rotacao_desistiu
        finally:
            handler.close()


class TestMontarOArquivoRotativo:
    def test_o_caminho_sai_do_personagem(self, tmp_path):
        handler = montar_arquivo_rotativo(
            tmp_path, janela="Yazalaque - XM Essence"
        )
        try:
            assert Path(handler.baseFilename).name == "scanner-Yazalaque.log"
        finally:
            handler.close()

    def test_e_o_handler_tolerante_e_nao_o_cru_do_stdlib(self, tmp_path):
        """Sem isto, o conserto da rotacao valeria so para quem o construir a
        mao - e o arranque de producao voltaria ao WinError 32."""
        handler = montar_arquivo_rotativo(tmp_path)
        try:
            assert isinstance(handler, ArquivoRotativoTolerante)
        finally:
            handler.close()


class TestOLogAntigoNaoEPerdido:
    """`logs/scanner.log`, `.1` e `.3` ja foram evidencia varias vezes.

    O conserto nao pode apagar, renomear nem sobrescrever nenhum deles. O nome
    novo NASCE ao lado; nao ha migracao.
    """

    def test_configurar_log_nao_toca_no_que_ja_existe(self, tmp_path, monkeypatch):
        from l2scanner import __main__ as principal

        pasta = tmp_path / "logs"
        pasta.mkdir()
        velhos = {}
        for nome in ("scanner.log", "scanner.log.1", "scanner.log.3"):
            (pasta / nome).write_text(f"historico de campo de {nome}", encoding="utf-8")
            velhos[nome] = (pasta / nome).read_bytes()

        monkeypatch.setattr(principal, "PASTA_LOGS", pasta)
        monkeypatch.setattr(principal, "ARQUIVO_CALIBRACAO", tmp_path / "cal.json")
        (tmp_path / "cal.json").write_text(
            json.dumps({"nome_proprio": "Yazalaque"}), encoding="utf-8"
        )

        anteriores = list(principal.log.handlers)
        nivel = principal.log.level
        try:
            principal.configurar_log(False, janela="AUTO")

            for nome, conteudo in velhos.items():
                assert (pasta / nome).exists(), f"{nome} sumiu"
                assert (pasta / nome).read_bytes() == conteudo, f"{nome} mudou"
            assert (pasta / "scanner-Yazalaque.log").exists()
        finally:
            for manipulador in list(principal.log.handlers):
                if manipulador not in anteriores:
                    manipulador.close()
            principal.log.handlers[:] = anteriores
            principal.log.setLevel(nivel)


class TestConfigurarLogUsaAInstancia:
    def test_o_arquivo_do_arranque_e_o_do_personagem(self, tmp_path, monkeypatch):
        from logging.handlers import RotatingFileHandler

        from l2scanner import __main__ as principal

        monkeypatch.setattr(principal, "PASTA_LOGS", tmp_path / "logs")
        monkeypatch.setattr(principal, "ARQUIVO_CALIBRACAO", tmp_path / "cal.json")

        anteriores = list(principal.log.handlers)
        nivel = principal.log.level
        try:
            principal.configurar_log(False, janela="Faerlina - XM Essence")
            arquivos = [
                h for h in principal.log.handlers
                if isinstance(h, RotatingFileHandler)
            ]

            assert arquivos, "sem arquivo, um farm de tres horas morre calado"
            assert Path(arquivos[-1].baseFilename).name == "scanner-Faerlina.log"
        finally:
            for manipulador in list(principal.log.handlers):
                if manipulador not in anteriores:
                    manipulador.close()
            principal.log.handlers[:] = anteriores
            principal.log.setLevel(nivel)

    def test_o_main_entrega_a_janela_ao_configurar_log(self):
        """O elo. Sem ele o arranque real continuaria caindo em `scanner.log`.

        Portao de FONTE porque `main()` chama `configurar_log` antes de
        qualquer coisa observavel, e um teste de comportamento aqui exigiria
        rodar o arranque inteiro so para ler um nome de arquivo.
        """
        from l2scanner import __main__ as principal

        fonte = Path(principal.__file__).read_text(encoding="utf-8")

        assert "configurar_log(args.verboso, janela=args.janela)" in fonte


class TestASuiteNaoEscreveNoLogDeProducao:
    """O portao que fecha as duas cacas de fantasma da docstring do modulo."""

    def test_a_pasta_de_log_do_arranque_esta_fora_da_arvore(self):
        """Durante a suite, `PASTA_LOGS` NAO aponta para `<repo>/logs`.

        Esta e a afirmacao direta: nao importa qual teste chame `main()` de
        verdade, o destino nao e o log de campo.
        """
        from l2scanner import __main__ as principal

        assert not str(Path(principal.PASTA_LOGS).resolve()).startswith(
            str((RAIZ / "logs").resolve())
        ), principal.PASTA_LOGS

    def test_o_portao_recusa_um_manipulador_no_log_de_producao(self, tmp_path):
        """E o portao FALHA ALTO, em vez de depender de alguem lembrar."""
        with pytest.raises(AssertionError, match="log de producao"):
            logging.FileHandler(RAIZ / "logs" / "scanner.log", delay=True)

    def test_o_portao_tambem_pega_o_rotativo(self):
        from logging.handlers import RotatingFileHandler

        with pytest.raises(AssertionError, match="log de producao"):
            RotatingFileHandler(RAIZ / "logs" / "scanner-Yazalaque.log", delay=True)

    def test_o_portao_deixa_passar_o_tmp_path(self, tmp_path):
        """Guarda contra portao que recusa tudo: os testes de log acima
        precisam continuar podendo escrever em `tmp_path`."""
        handler = logging.FileHandler(tmp_path / "scanner.log")
        handler.close()
