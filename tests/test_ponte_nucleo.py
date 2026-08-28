"""O miolo da ponte: quem passa, quem nao passa, e por que.

Toda esta suite roda em milissegundos e SEM REDE porque o nucleo nao conhece o
Discord: ele recebe uma `MensagemRecebida` ja normalizada e devolve um
`Resultado`, no espirito de `Sessao.tick(frame, momento)`. Nao ha `asyncio`,
nao ha `pytest-asyncio` (que nao esta instalado) e, principalmente, NAO HA
`import discord` — nem aqui nem em nada que este arquivo importe.

Esse ultimo ponto e estrutural, e medido: o `pytest` deste repositorio roda no
Python GLOBAL (3.12.10, com pytest e cv2), enquanto o `discord` foi instalado no
`.venv` de producao, que NAO tem pytest. Um teste que importasse `discord`,
direta ou transitivamente, morreria na COLETA e levaria a suite inteira junto.
Por isso o `ponte_nucleo.py` nao tem uma linha de terceiro, e por isso existe
`test_importar_o_nucleo_nao_puxa_o_discord` la embaixo.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from l2scanner.ponte_nucleo import (
    ClienteDiscordEmMemoria,
    Decisao,
    MensagemRecebida,
    NucleoDaPonte,
    mensagem_de_teste,
)

# Os ids reais da fase, para que o teste falhe se alguem trocar o alvo sem
# querer. Sao ids publicos de canal, nao segredo — o segredo e so o token.
GUILD = 936957935572103169
CANAL_A = 1536506379752185953
CANAL_B = 1538202612762022020
CANAIS = frozenset({CANAL_A, CANAL_B})

# Um canal qualquer do MESMO servidor que nao esta na lista.
CANAL_DE_FORA = 1111111111111111111
# Uma thread. Id de thread e id de canal vivem no mesmo espaco de numeros,
# entao um id de thread simplesmente nao casa com a lista — sem codigo extra.
THREAD = 1222222222222222222

EU = 5000000000000000001  # o id da propria ponte
OUTRO_BOT = 6000000000000000002
UM_WEBHOOK = 7000000000000000003


def nucleo(id_da_ponte: int | None = EU) -> NucleoDaPonte:
    return NucleoDaPonte(guild=GUILD, canais=CANAIS, id_da_ponte=id_da_ponte)


class TestSoOsDoisCanais:
    """PONTE-02: a lista de canais e a PRIMEIRA trava, antes de tudo."""

    def test_mensagem_de_canal_fora_da_lista_e_ignorada_e_o_motivo_e_o_canal(self):
        """Sem esta trava a ponte repete o servidor inteiro no WhatsApp.

        O motivo precisa vir na decisao, e nao so um "nao passou": quando o
        usuario reclamar de que a mensagem dele nao apareceu, a diferenca entre
        IGNORADA_CANAL e IGNORADA_PROPRIA e a diferenca entre "voce postou no
        canal errado" e "o bot esta se ouvindo".
        """
        resultado = nucleo().receber(mensagem_de_teste(canal=CANAL_DE_FORA))

        assert resultado.decisao is Decisao.IGNORADA_CANAL

    @pytest.mark.parametrize("canal", sorted(CANAIS))
    def test_mensagem_em_cada_um_dos_dois_canais_configurados_e_aceita(self, canal):
        """Os DOIS. Um teste com um canal so deixaria o segundo sem cobertura."""
        resultado = nucleo().receber(mensagem_de_teste(canal=canal))

        assert resultado.decisao is Decisao.ACEITA

    def test_id_de_thread_nao_passa_sem_uma_linha_a_mais_de_codigo(self):
        """Thread e canal dividem o espaco de ids, entao o frozenset ja resolve.

        O teste existe para travar essa propriedade: se alguem trocar a
        comparacao por "o canal pai esta na lista?", threads passam a vazar e o
        anuncio vira conversa de thread repetida no WhatsApp.
        """
        resultado = nucleo().receber(mensagem_de_teste(canal=THREAD))

        assert resultado.decisao is Decisao.IGNORADA_CANAL


class TestOFiltroEhSoODoProprioId:
    """PONTE-04: descartar `author.bot` seria descartar o caso principal."""

    def test_mensagem_da_propria_ponte_e_ignorada(self):
        """Sem isto, a Fase 3 vira laco: a ponte entrega, se ve, entrega de novo."""
        resultado = nucleo().receber(mensagem_de_teste(canal=CANAL_A, autor=EU))

        assert resultado.decisao is Decisao.IGNORADA_PROPRIA

    def test_mensagem_de_OUTRO_bot_no_canal_alvo_e_aceita(self):
        """ESTE E O CASO PRINCIPAL: anuncio de guild costuma vir de bot.

        `if message.author.bot: return` e o recorte mais copiado de tutorial de
        bot do Discord. Aqui ele apagaria justamente a mensagem que a ponte
        existe para repetir — e apagaria calado, que e o pior jeito.
        """
        resultado = nucleo().receber(
            mensagem_de_teste(canal=CANAL_A, autor=OUTRO_BOT, autor_nome="AnuncioBot")
        )

        assert resultado.decisao is Decisao.ACEITA

    def test_mensagem_de_webhook_no_canal_alvo_e_aceita(self):
        """O autor de um webhook e o id DO WEBHOOK, nunca o id da ponte.

        Muitos servidores publicam anuncio por webhook. Se a trava fosse "veio
        de coisa automatica, descarta", o servidor inteiro de anuncios sumiria.
        """
        resultado = nucleo().receber(
            mensagem_de_teste(canal=CANAL_B, autor=UM_WEBHOOK, autor_nome="Avisos")
        )

        assert resultado.decisao is Decisao.ACEITA


class TestOIdDaPonteChegaDepoisDaConexao:
    """PONTE-04: `None` e um estado de PRE-CONEXAO, com dono e com teste."""

    def test_nucleo_sem_id_da_ponte_nao_descarta_ninguem_por_autoria(self):
        """`None` aqui e DOCUMENTADO, nao esquecimento.

        O `main` monta o nucleo ANTES do `run`, e nesse instante o cliente
        ainda nao sabe quem ele e. Afirmar isso de proposito impede que o
        proximo leitor trate o estado como bug e "conserte" para um id falso.
        """
        seco = nucleo(id_da_ponte=None)

        resultado = seco.receber(mensagem_de_teste(canal=CANAL_A, autor=EU))

        assert resultado.decisao is Decisao.ACEITA

    def test_depois_de_definir_id_da_ponte_o_MESMO_nucleo_passa_a_descartar(self):
        """A prova de que a trava existe em PRODUCAO, e nao so no teste.

        Sem `definir_id_da_ponte` no `on_ready`, o unico id que o construtor
        recebe e `None` e o filtro do proprio id NUNCA dispara no processo de
        verdade — enquanto todo teste que passa o id na mao continua verde.
        Verde no CI, morto na maquina do usuario, e o sintoma so apareceria na
        Fase 3, como laco de entrega.
        """
        vivo = nucleo(id_da_ponte=None)
        minha = mensagem_de_teste(canal=CANAL_A, autor=EU)

        assert vivo.receber(minha).decisao is Decisao.ACEITA

        vivo.definir_id_da_ponte(EU)

        assert vivo.receber(minha).decisao is Decisao.IGNORADA_PROPRIA

    def test_definir_id_da_ponte_duas_vezes_com_o_mesmo_id_nao_muda_nada(self):
        """O `on_ready` roda de novo a cada IDENTIFY: a chamada e idempotente.

        Uma reconexao no meio do farm nao pode mudar quem a ponte descarta.
        """
        vivo = nucleo(id_da_ponte=None)
        vivo.definir_id_da_ponte(EU)
        vivo.definir_id_da_ponte(EU)

        resultado = vivo.receber(mensagem_de_teste(canal=CANAL_A, autor=EU))

        assert resultado.decisao is Decisao.IGNORADA_PROPRIA


class TestNaoExisteOutroFiltro:
    """PONTE-03: nada de cargo, nada de mencao, nada de "so quem eu conheco"."""

    def test_mensagem_de_alguem_sem_cargo_nenhum_e_aceita(self):
        """Membro novo de guild costuma nao ter cargo, e e quem mais avisa coisa."""
        resultado = nucleo().receber(
            mensagem_de_teste(canal=CANAL_A, autor_nome="RecemChegado")
        )

        assert resultado.decisao is Decisao.ACEITA

    def test_mensagem_que_menciona_everyone_e_aceita(self):
        """`@everyone` e o formato tipico do anuncio — filtrar seria filtrar o alvo."""
        resultado = nucleo().receber(
            mensagem_de_teste(canal=CANAL_A, texto="@everyone TvT em 10 minutos")
        )

        assert resultado.decisao is Decisao.ACEITA

    def test_mensagem_que_nao_menciona_ninguem_e_aceita(self):
        """A armadilha do portao humano vive aqui.

        Testar o criterio 2 da fase MENCIONANDO o bot da um falso verde: uma
        mensagem que menciona o bot chega com texto mesmo com a intent
        DESLIGADA. Por isso a ponte nao pode ter filtro de mencao nenhum — se
        tivesse, o unico teste manual que funcionaria seria justamente o que
        mente.
        """
        resultado = nucleo().receber(
            mensagem_de_teste(canal=CANAL_A, texto="teste da ponte 1")
        )

        assert resultado.decisao is Decisao.ACEITA


class TestALinhaDoConsole:
    def test_a_decisao_aceita_ja_carrega_o_texto_pronto_para_o_console(self):
        """A beirada async nao remonta nada; ela so imprime o que o nucleo deu.

        Se a montagem da linha morasse no `on_message`, ela seria a unica parte
        do caminho sem teste — e e exatamente a parte que o usuario LE.
        """
        resultado = nucleo().receber(
            mensagem_de_teste(canal=CANAL_A, autor_nome="Korzis", texto="subiu evento")
        )

        assert str(CANAL_A) in resultado.linha
        assert "Korzis" in resultado.linha
        assert "subiu evento" in resultado.linha

    def test_a_linha_carrega_o_texto_CRU_ate_o_ultimo_caractere(self):
        """Fase 1 nao formata nada. Truncar aqui esconderia o que se quer provar.

        O objetivo da fase e ver o texto DE VERDADE. Uma linha cortada nao
        distingue "chegou inteiro" de "chegou pela metade".
        """
        texto = "linha comprida de teste, com numero 12345 e pontuacao no fim."
        resultado = nucleo().receber(mensagem_de_teste(canal=CANAL_A, texto=texto))

        assert resultado.linha.endswith(texto)

    def test_mensagem_ignorada_nao_produz_linha_de_console(self):
        """Imprimir o que foi recusado transformaria o console no servidor inteiro."""
        resultado = nucleo().receber(mensagem_de_teste(canal=CANAL_DE_FORA))

        assert resultado.linha == ""


class TestClienteDiscordEmMemoria:
    """O duble que substitui o cliente do Discord inteiro. Sem rede, sem asyncio."""

    def test_uma_lista_de_mensagens_fabricadas_produz_as_decisoes_esperadas(self):
        """A fatia de recebimento inteira, exercitada sem sair da maquina.

        Sem este duble, provar "bot passa, webhook passa, canal de fora nao
        passa" exigiria um servidor Discord de verdade e um humano postando —
        ou seja, nao seria provado nunca.
        """
        cliente = ClienteDiscordEmMemoria(nucleo())

        cliente.entregar_todas(
            [
                mensagem_de_teste(id=1, canal=CANAL_A, autor_nome="Korzis", texto="oi"),
                mensagem_de_teste(id=2, canal=CANAL_DE_FORA, texto="outro canal"),
                mensagem_de_teste(id=3, canal=CANAL_B, autor=OUTRO_BOT, texto="anuncio"),
                mensagem_de_teste(id=4, canal=CANAL_A, autor=EU, texto="eco meu"),
            ]
        )

        assert [r.decisao for r in cliente.resultados] == [
            Decisao.ACEITA,
            Decisao.IGNORADA_CANAL,
            Decisao.ACEITA,
            Decisao.IGNORADA_PROPRIA,
        ]

    def test_o_duble_acumula_so_as_linhas_aceitas(self):
        """`linhas` e o que o console teria mostrado — nem mais, nem menos."""
        cliente = ClienteDiscordEmMemoria(nucleo())

        cliente.entregar_todas(
            [
                mensagem_de_teste(id=1, canal=CANAL_A, texto="entra"),
                mensagem_de_teste(id=2, canal=CANAL_DE_FORA, texto="fica de fora"),
            ]
        )

        assert len(cliente.linhas) == 1
        assert "entra" in cliente.linhas[0]
        assert "fica de fora" not in cliente.linhas[0]

    def test_o_duble_guarda_as_mensagens_que_recebeu(self):
        """Para o teste poder perguntar "o que foi bombeado?" sem espiar o nucleo."""
        cliente = ClienteDiscordEmMemoria(nucleo())
        uma = mensagem_de_teste(canal=CANAL_A)

        cliente.entregar(uma)

        assert cliente.mensagens == [uma]


class TestAFormaNormalizadaDaMensagem:
    def test_a_mensagem_carrega_os_campos_que_a_fase_2_vai_precisar(self):
        """Anexo, embed, figurinha, componente, enquete, encaminhamento, sistema.

        Eles nascem aqui, todos `False` por padrao, porque a FORM-04 (postagem
        so-com-imagem nao pode sumir calada) precisa saber que havia algo na
        mensagem quando o texto vem vazio. Acrescentar campo depois obrigaria a
        mexer no normalizador e no nucleo ao mesmo tempo.
        """
        crua = mensagem_de_teste(canal=CANAL_A, tem_anexo=True)

        assert crua.tem_anexo is True
        assert crua.tem_embed is False
        assert crua.tem_figurinha is False
        assert crua.tem_componente is False
        assert crua.tem_enquete is False
        assert crua.e_encaminhamento is False
        assert crua.e_mensagem_de_sistema is False

    def test_a_mensagem_e_congelada(self):
        """O nucleo nao pode reescrever o que recebeu; o duble reusa a instancia."""
        crua = mensagem_de_teste(canal=CANAL_A)

        with pytest.raises(Exception):
            crua.texto = "outra coisa"  # type: ignore[misc]

    def test_a_fabrica_de_teste_mora_no_codigo_de_producao(self):
        """Uma so fabrica para os dois lados, como `NotificadorEmMemoria`.

        Duas fabricas divergem: a do teste ganha um campo, a de producao nao, e
        o duble passa a exercitar uma mensagem que nao existe.
        """
        assert isinstance(mensagem_de_teste(), MensagemRecebida)


class TestADivisaoEmTresModulos:
    def test_importar_o_nucleo_nao_puxa_o_discord(self):
        """A trava que mantem a suite inteira viva.

        MEDIDO: o pytest roda no Python GLOBAL, que NAO tem `discord`; o
        `discord` esta no `.venv` de producao, que NAO tem pytest. Se
        `ponte_nucleo` ou `ponte_config` passarem a importar `discord` (mesmo
        transitivamente), a suite morre na COLETA — todos os arquivos, nao so
        estes. O subprocesso e de proposito: dentro do processo do pytest, um
        outro teste ja poderia ter importado `discord` e mascarado a regressao.
        """
        codigo = (
            "import sys;"
            "import l2scanner.ponte_nucleo, l2scanner.ponte_config;"
            "assert 'discord' not in sys.modules, sorted(sys.modules);"
            "print('limpo')"
        )
        saida = subprocess.run(
            [sys.executable, "-c", codigo],
            capture_output=True,
            text=True,
        )

        assert saida.returncode == 0, saida.stderr
        assert "limpo" in saida.stdout
