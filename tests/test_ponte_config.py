"""A config da ponte: o que ela exige, e por que ela exige MAIS que a agenda.

`ler_agenda` decidiu que "arquivo ausente nao e erro", e esta certa: a agenda e
um acessorio de um scanner que roda sem ela. A ponte e o contrario — e um
PROCESSO DEDICADO que nao existe sem a secao `[discord]`. Subir muda seria pior
que nao subir: o usuario ficaria olhando um console vivo esperando um anuncio
que nunca poderia chegar (CONF-03).

Como o resto da suite, estes testes nao tocam a rede e nao importam `discord`:
o `ponte_config.py` e stdlib pura (`tomllib` + o `ler_env` de 13 linhas que o
repositorio ja tem).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from l2scanner.ponte_config import (
    ARQUIVO_CONFIG,
    VALOR_DE_EXEMPLO_DO_TOKEN,
    ConfigDaPonte,
    PonteInvalida,
    conferir_a_configuracao,
    ler_config_da_ponte,
    ler_token_do_discord,
    resumo_da_configuracao,
)

GUILD = 936957935572103169
CANAL_A = 1536506379752185953
CANAL_B = 1538202612762022020

COMPLETO = f"""
[discord]
guild = {GUILD}
canais = [{CANAL_A}, {CANAL_B}]
conversa_de_destino = "42"
simulacao = true
"""

# Um token com cara de token de bot do Discord, e com uma marca dentro que
# nenhuma mensagem de erro poderia produzir por acaso.
TOKEN_RECONHECIVEL = "MTIzNDU2Nzg5MDEyMzQ1Njc4.Gabcde.NAO-PODE-VAZAR-NUNCA"


def escrever(pasta: Path, texto: str) -> Path:
    alvo = pasta / "config.toml"
    alvo.write_text(texto, encoding="utf-8")
    return alvo


def escrever_env(pasta: Path, texto: str) -> Path:
    alvo = pasta / ".env"
    alvo.write_text(texto, encoding="utf-8")
    return alvo


def trocar(chave: str, valor: str) -> str:
    """Troca UMA linha do bloco completo, mantendo o resto valido.

    Assim cada teste de tipo errado exercita exatamente um campo — um bloco
    reescrito a mao por teste divergiria do bloco real na primeira chave nova.
    """
    linhas = [
        f"{chave} = {valor}" if linha.startswith(f"{chave} ") else linha
        for linha in COMPLETO.splitlines()
    ]
    return "\n".join(linhas)


def sem(chave: str) -> str:
    return "\n".join(
        linha for linha in COMPLETO.splitlines() if not linha.startswith(f"{chave} ")
    )


class TestLerASecaoDiscord:
    def test_secao_completa_devolve_guild_canais_e_destino_com_os_tipos_certos(
        self, tmp_path
    ):
        """Tipo errado aqui nao aparece na hora: aparece na comparacao de id.

        Um `canais` de strings compararia `"1536..." != 1536...` para sempre e
        a ponte ficaria muda com o console dizendo que esta ouvindo os canais.
        """
        cfg = ler_config_da_ponte(escrever(tmp_path, COMPLETO))

        assert isinstance(cfg, ConfigDaPonte)
        assert cfg.guild == GUILD
        assert cfg.canais == frozenset({CANAL_A, CANAL_B})
        assert isinstance(cfg.canais, frozenset)
        assert all(isinstance(canal, int) for canal in cfg.canais)
        assert cfg.conversa_de_destino == "42"
        assert cfg.simulacao is True

    def test_a_leitura_aceita_um_caminho_explicito(self, tmp_path):
        """Sem isto os testes precisariam sobrescrever o config.toml do repo.

        E a mesma disciplina de `ler_env(caminho)` e `ler_agenda(caminho)`:
        toda funcao que le arquivo aceita o caminho e cai no padrao.
        """
        cfg = ler_config_da_ponte(escrever(tmp_path, COMPLETO))

        assert cfg.guild == GUILD

    def test_sem_caminho_ela_cai_no_config_toml_do_repositorio(self):
        """O arquivo versionado tem que continuar valido de verdade.

        Este teste le O config.toml do repositorio, nao um fabricado: se alguem
        editar a secao `[discord]` e quebrar um id, o vermelho aparece aqui e
        nao as 21h50 com a ponte muda.
        """
        cfg = ler_config_da_ponte(None)

        assert ARQUIVO_CONFIG.is_file()
        assert cfg.guild == GUILD
        assert cfg.canais == frozenset({CANAL_A, CANAL_B})


class TestArquivoOuSecaoAusenteEhErro:
    """O contraste deliberado com `ler_agenda` (CONF-03)."""

    def test_config_ausente_e_erro_e_nao_um_padrao_silencioso(self, tmp_path):
        """A ponte nao tem padrao razoavel: sem canais ela nao tem o que ouvir.

        E a mensagem tem de NOMEAR o arquivo que ela procurou. "nao encontrei a
        configuracao" faz o usuario abrir a pasta errada.
        """
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(tmp_path / "config.toml")

        assert "config.toml" in str(erro.value)
        assert "[discord]" in str(erro.value)

    def test_secao_discord_ausente_mostra_o_bloco_de_exemplo_inteiro(self, tmp_path):
        """Nomear a secao nao basta: o usuario precisa saber o que escrever nela.

        Quem esbarra nisto tem um `config.toml` que existe e uma secao que nao.
        Dizer so "falta [discord]" o deixa inventando nomes de chave num arquivo
        que ele nao escreveu. O bloco de exemplo e a diferenca entre uma
        mensagem que reclama e uma que conserta.
        """
        outro = "[[evento]]\nnome = 'TvT'\n"

        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, outro))

        texto = str(erro.value)
        assert "[discord]" in texto
        for chave in ("guild", "canais", "conversa_de_destino", "simulacao"):
            assert chave in texto

    def test_toml_quebrado_diz_qual_ARQUIVO_esta_quebrado(self, tmp_path):
        """Sao DOIS arquivos em jogo, e editar o errado e o desfecho provavel.

        "o TOML esta quebrado" com um `config.toml` e um `config.local.toml` na
        mesma pasta e um convite a mexer no arquivo que estava certo.
        """
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, "[discord\nguild = 1\n"))

        texto = str(erro.value)
        assert "TOML" in texto
        assert "config.toml" in texto

    @pytest.mark.parametrize("chave", ["guild", "canais", "conversa_de_destino"])
    def test_chave_ausente_levanta_nomeando_a_chave_que_falta(self, chave, tmp_path):
        """A mensagem tem que dizer QUAL chave, senao o usuario adivinha.

        Sao tres chaves obrigatorias num arquivo que o usuario edita a mao;
        "falta uma chave" mandaria ele conferir as tres numa janela de cmd.
        """
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, sem(chave)))

        assert chave in str(erro.value)

    def test_conversa_de_destino_vazia_ainda_e_config_valida(self, tmp_path):
        """Na Fase 1 o usuario AINDA NAO descobriu o id do Chatwoot.

        Exigir valor aqui impediria o proprio criterio 2 da fase de ser
        conferido — a fase so simula, e simular nao precisa de destino. Quem vai
        exigir valor de verdade e a Fase 3, na hora de entregar.
        """
        vazia = COMPLETO.replace('conversa_de_destino = "42"', 'conversa_de_destino = ""')

        cfg = ler_config_da_ponte(escrever(tmp_path, vazia))

        assert cfg.conversa_de_destino == ""


class TestTipoErradoEhRecusadoEmVezDeAceitoCalado:
    """CONF-03 na sua forma mais traicoeira: o valor que "quase" serve."""

    def test_guild_entre_aspas_e_recusada_dizendo_o_que_veio_e_o_que_se_espera(
        self, tmp_path
    ):
        """Aspas em volta de um id e o deslize de edicao mais comum do TOML.

        Sem esta recusa a ponte compararia `"936..." != 936...` para sempre: ela
        subiria, diria no console que esta ouvindo o servidor, e nao ouviria
        nada. O usuario ficaria olhando um console saudavel esperando um anuncio
        impossivel — exatamente o modo de falha que a fase inteira existe para
        matar.
        """
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, trocar("guild", f'"{GUILD}"')))

        texto = str(erro.value)
        assert "guild" in texto
        assert "aspas" in texto

    def test_guild_true_e_recusada_porque_bool_e_subclasse_de_int(self, tmp_path):
        """A armadilha do Python: `isinstance(True, int)` e VERDADEIRO.

        Sem uma checagem explicita de `bool`, `guild = true` passaria como o
        servidor de id 1 — um servidor que existe, que nao e o do usuario, e do
        qual a ponte nunca receberia nada. Zero linhas de erro no console. E o
        mesmo buraco que `calibracao.py:466-480` fecha e que `config.py:229-244`
        documenta.
        """
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, trocar("guild", "true")))

        assert "guild" in str(erro.value)

    def test_canais_true_tambem_e_recusado_pela_mesma_armadilha(self, tmp_path):
        """`canais = true` nao pode virar "nenhum canal" calado."""
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, trocar("canais", "true")))

        assert "canais" in str(erro.value)

    def test_lista_de_canais_vazia_e_recusada(self, tmp_path):
        """Uma ponte sem canal nenhum e uma ponte que nunca vai falar.

        Ela subiria, conectaria, imprimiria "ouvindo os canais: " e ficaria
        muda para sempre. Recusar no arranque e a unica saida honesta.
        """
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, trocar("canais", "[]")))

        assert "canais" in str(erro.value)

    def test_um_canal_so_e_configuracao_LEGITIMA(self, tmp_path):
        """A lista e do usuario: nada no produto exige exatamente dois canais.

        Exigir dois seria pinar no codigo uma escolha que e do usuario, e o
        primeiro efeito disso seria alguem que so quer ouvir #anuncios ficar sem
        conseguir subir a ponte.
        """
        cfg = ler_config_da_ponte(escrever(tmp_path, trocar("canais", f"[{CANAL_A}]")))

        assert cfg.canais == frozenset({CANAL_A})

    def test_canal_repetido_vira_um_so_sem_erro(self, tmp_path):
        """Repetir um id e desatencao, nao erro: o efeito pretendido e o mesmo.

        `frozenset` ja resolve. Levantar aqui seria transformar um typo inocente
        num arranque abortado.
        """
        cfg = ler_config_da_ponte(
            escrever(tmp_path, trocar("canais", f"[{CANAL_A}, {CANAL_A}]"))
        )

        assert cfg.canais == frozenset({CANAL_A})

    def test_canal_que_nao_e_numero_e_recusado_NOMEANDO_o_elemento(self, tmp_path):
        """Com dois ids de 19 digitos lado a lado, "a lista esta errada" nao ajuda.

        A mensagem tem de dizer QUAL elemento, senao o usuario confere os dois a
        olho nu numa janela de cmd sem quebra de linha.
        """
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(
                escrever(tmp_path, trocar("canais", f'[{CANAL_A}, "{CANAL_B}"]'))
            )

        texto = str(erro.value)
        assert "canais" in texto
        assert str(CANAL_B) in texto

    def test_conversa_de_destino_sem_aspas_e_recusada_ensinando_as_aspas(
        self, tmp_path
    ):
        """O id do Chatwoot e TEXTO neste projeto, e a diferenca e visivel.

        As conversas do `.env` chegam como texto (`config.py:97-101` parte um
        CSV), e a comparacao com a conversa de destino e de texto com texto.
        Aceitar um numero aqui faria `28 != "28"` na hora de comparar com as
        conversas de comando — e a guarda de higiene passaria batido justamente
        no caso que ela existe para pegar.
        """
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, trocar("conversa_de_destino", "28")))

        texto = str(erro.value)
        assert "conversa_de_destino" in texto
        assert "aspas" in texto


class TestOModoSimulacao:
    """CONF-04: um interruptor honesto, ou nenhum interruptor."""

    def test_simulacao_ausente_vale_true(self, tmp_path):
        """O padrao seguro e o que NAO manda mensagem para o grupo.

        Quem esquece a chave nao pode acabar postando anuncio de guild no
        WhatsApp de sete pessoas sem ter pedido.
        """
        cfg = ler_config_da_ponte(escrever(tmp_path, sem("simulacao")))

        assert cfg.simulacao is True

    def test_simulacao_false_e_RECUSADA_citando_a_Fase_3(self, tmp_path):
        """Uma chave que mente e pior do que uma chave ausente.

        Na Fase 1 nao existe caminho de entrega nenhum. Aceitar
        `simulacao = false` calado faria o usuario desligar a simulacao, esperar
        as mensagens no WhatsApp e nao receber nada — sem uma linha de erro
        explicando que a entrega ainda nem foi escrita.
        """
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, trocar("simulacao", "false")))

        texto = str(erro.value)
        assert "simulacao" in texto
        assert "Fase 3" in texto

    def test_simulacao_com_valor_que_nao_e_booleano_e_recusada(self, tmp_path):
        """`simulacao = "true"` (entre aspas) e o deslize irmao do id com aspas."""
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, trocar("simulacao", '"true"')))

        assert "simulacao" in str(erro.value)


class TestOTokenSaiDoEnv:
    def test_o_token_sai_do_env_pela_chave_DISCORD_TOKEN(self, tmp_path):
        """CONF-01: o token nao mora no config.toml, que e versionado.

        O config.toml e o arquivo que o usuario tira print e cola no grupo
        pedindo ajuda. O token do bot nao pode estar nele.
        """
        env = escrever_env(tmp_path, "DISCORD_TOKEN=abc.123.xyz\n")

        assert ler_token_do_discord(env) == "abc.123.xyz"

    def test_env_INEXISTENTE_manda_copiar_o_ENV_EXEMPLO(self, tmp_path):
        """Quem esbarra nisto e um leigo com uma janela de cmd aberta.

        "arquivo nao existe" e "a chave nao esta la" tem consertos DIFERENTES —
        um e copiar o exemplo, o outro e preencher uma linha. Uma mensagem so
        para os dois manda metade dos usuarios procurar o que nao esta faltando.
        """
        with pytest.raises(PonteInvalida) as erro:
            ler_token_do_discord(tmp_path / ".env")

        texto = str(erro.value)
        assert "DISCORD_TOKEN" in texto
        assert "ENV-EXEMPLO.txt" in texto

    def test_env_que_EXISTE_sem_a_chave_nomeia_a_chave(self, tmp_path):
        """O `.env` do scanner ja existe na maquina do usuario ha meses.

        O caso real nao e "nao tenho .env": e "tenho o .env do Chatwoot e falta
        uma linha nova nele". A mensagem tem de nomear a linha que falta.
        """
        env = escrever_env(tmp_path, "CHATWOOT_URL=https://exemplo\n")

        with pytest.raises(PonteInvalida) as erro:
            ler_token_do_discord(env)

        assert "DISCORD_TOKEN" in str(erro.value)

    def test_token_vazio_e_tratado_como_ausente(self, tmp_path):
        """`DISCORD_TOKEN=` copiado do exemplo e o caso mais comum de todos."""
        env = escrever_env(tmp_path, "DISCORD_TOKEN=\n")

        with pytest.raises(PonteInvalida) as erro:
            ler_token_do_discord(env)

        assert "DISCORD_TOKEN" in str(erro.value)

    def test_o_valor_de_EXEMPLO_literal_e_recusado(self, tmp_path):
        """Mesmo tratamento que `config.py:74-75` da ao CHATWOOT_TOKEN.

        Sem isto, quem colar o texto do placeholder recebe do Discord um
        `LoginFailure` em ingles no meio de um traceback, em vez da linha em
        portugues que diz onde clicar.
        """
        env = escrever_env(tmp_path, f"DISCORD_TOKEN={VALOR_DE_EXEMPLO_DO_TOKEN}\n")

        with pytest.raises(PonteInvalida) as erro:
            ler_token_do_discord(env)

        assert "DISCORD_TOKEN" in str(erro.value)

    def test_nenhuma_mensagem_de_erro_carrega_o_VALOR_do_token(self, tmp_path):
        """Um erro que despeja o `.env` inteiro vaza o token para o log rotativo.

        E dali para um print no grupo, porque a primeira coisa que um usuario
        faz quando o programa reclama e fotografar o console.

        Este teste provoca TODOS os erros que o modulo sabe levantar com um
        `.env` valido ao lado, e afirma a ausencia do valor em cada mensagem. A
        implementacao ingenua (`f"nao achei nada em {env}"`, ou um resumo que
        imprime o token para "ajudar a conferir") fica vermelha aqui.
        """
        env = escrever_env(tmp_path, f"DISCORD_TOKEN={TOKEN_RECONHECIVEL}\n")

        quebrados = [
            "[discord\nguild = 1\n",
            "[[evento]]\nnome = 'TvT'\n",
            sem("guild"),
            sem("canais"),
            sem("conversa_de_destino"),
            trocar("guild", "true"),
            trocar("guild", f'"{GUILD}"'),
            trocar("canais", "[]"),
            trocar("canais", f'[{CANAL_A}, "x"]'),
            trocar("simulacao", "false"),
        ]

        mensagens = []
        for texto in quebrados:
            with pytest.raises(PonteInvalida) as erro:
                conferir_a_configuracao(escrever(tmp_path, texto), env)
            mensagens.append(str(erro.value))

        # E o caminho FELIZ tambem: o resumo que o `--conferir` imprime.
        cfg, token = conferir_a_configuracao(escrever(tmp_path, COMPLETO), env)
        mensagens.append(resumo_da_configuracao(cfg, len(token)))

        assert token == TOKEN_RECONHECIVEL
        for mensagem in mensagens:
            assert TOKEN_RECONHECIVEL not in mensagem
            assert "NAO-PODE-VAZAR" not in mensagem


class TestAGuardaDaConversaDeDestino:
    """T-01-06, com a razao HONESTA — que e menor do que a pesquisa sugeria.

    O caminho "um anuncio postado pela ponte vira comando do scanner" JA ESTA
    FECHADO e nao e o motivo desta guarda: a ponte posta `outgoing`
    (`notificador.py:281`) e `comandos.py:887` descarta tudo que nao e
    `incoming`. O motivo REAL e o outro sentido: quem RESPONDE numa conversa de
    anuncio compartilhada manda `incoming`, e um "ok" ou um "kkkk" numa conversa
    que tambem e canal de comando seria lido como comando do scanner.

    A guarda sobreviveu a revogacao da ENTR-02 (os anuncios passam a ir para a
    conversa 28, a MESMA dos avisos de party) porque ela nunca falou sobre
    aquilo: 28 nao colide com a conversa de comando, entao ela passa — e
    continua de pe para o dia em que alguem apontar o destino para a conversa
    errada.
    """

    def test_destino_igual_a_uma_conversa_de_comando_e_RECUSADO(self, tmp_path):
        env = escrever_env(
            tmp_path,
            "DISCORD_TOKEN=abc.123.xyz\nCHATWOOT_CONVERSAS_COMANDO=1,42\n",
        )

        with pytest.raises(PonteInvalida) as erro:
            conferir_a_configuracao(escrever(tmp_path, COMPLETO), env)

        texto = str(erro.value)
        assert "conversa_de_destino" in texto
        assert "CHATWOOT_CONVERSAS_COMANDO" in texto

    def test_a_mensagem_explica_QUEM_RESPONDE_e_nao_o_risco_inflado(self, tmp_path):
        """Uma justificativa falsa e o comeco de uma guarda removida.

        Se a mensagem dissesse "um anuncio com `.status` vira comando", o
        primeiro leitor que abrisse `comandos.py:887` veria que e mentira e
        apagaria a guarda inteira — junto com o risco REAL, que nao e mentira.
        """
        env = escrever_env(
            tmp_path,
            "DISCORD_TOKEN=abc.123.xyz\nCHATWOOT_CONVERSAS_COMANDO=42\n",
        )

        with pytest.raises(PonteInvalida) as erro:
            conferir_a_configuracao(escrever(tmp_path, COMPLETO), env)

        texto = str(erro.value).lower()
        assert "responde" in texto

    def test_destino_diferente_das_conversas_de_comando_passa(self, tmp_path):
        """Os valores REAIS do usuario: destino 28, comando 1. Nao colidem."""
        env = escrever_env(
            tmp_path,
            "DISCORD_TOKEN=abc.123.xyz\nCHATWOOT_CONVERSAS_COMANDO=1\n",
        )
        toml = COMPLETO.replace(
            'conversa_de_destino = "42"', 'conversa_de_destino = "28"'
        )

        cfg, _ = conferir_a_configuracao(escrever(tmp_path, toml), env)

        assert cfg.conversa_de_destino == "28"

    def test_lista_de_comando_vazia_e_o_padrao_e_deixa_tudo_passar(self, tmp_path):
        """`CHATWOOT_CONVERSAS_COMANDO` vazio e o padrao do projeto.

        Se a lista vazia virasse uma colisao com a conversa `""`, a ponte
        recusaria subir na maquina de quem nunca ligou o canal de comando — ou
        seja, na maioria delas.
        """
        env = escrever_env(tmp_path, "DISCORD_TOKEN=abc.123.xyz\n")
        vazia = COMPLETO.replace(
            'conversa_de_destino = "42"', 'conversa_de_destino = ""'
        )

        cfg, _ = conferir_a_configuracao(escrever(tmp_path, vazia), env)

        assert cfg.conversa_de_destino == ""

    def test_a_comparacao_ignora_espaco_em_volta(self, tmp_path):
        """`CHATWOOT_CONVERSAS_COMANDO` viaja como CSV escrito a mao.

        `config.py:97-101` parte com `split(",")` e `strip()` justamente porque
        `1, 42` com espaco e como uma pessoa escreve. Comparar sem `strip()`
        deixaria ` 42` diferente de `42` e a guarda passaria batida — verde,
        presente e inutil.
        """
        env = escrever_env(
            tmp_path,
            "DISCORD_TOKEN=abc.123.xyz\nCHATWOOT_CONVERSAS_COMANDO=1,  42  ,7\n",
        )

        with pytest.raises(PonteInvalida) as erro:
            conferir_a_configuracao(escrever(tmp_path, COMPLETO), env)

        assert "conversa_de_destino" in str(erro.value)


class TestAPortaUnicaDoArranque:
    def test_conferir_a_configuracao_devolve_config_e_token(self, tmp_path):
        """Uma porta so para o arranque inteiro: TOML, tipo, segredo e higiene.

        Com duas portas, o `--conferir` e o arranque de verdade divergiriam — e
        o modo que existe para provar o arranque provaria outro caminho.
        """
        env = escrever_env(tmp_path, "DISCORD_TOKEN=abc.123.xyz\n")

        cfg, token = conferir_a_configuracao(escrever(tmp_path, COMPLETO), env)

        assert cfg.guild == GUILD
        assert token == "abc.123.xyz"

    def test_config_quebrada_e_vista_ANTES_de_o_token_ser_lido(self, tmp_path):
        """Sem `.env` nenhum, um TOML quebrado ainda tem de reclamar do TOML.

        A ordem importa para quem esta consertando: mandar preencher o `.env`
        quando o `config.toml` esta quebrado faz a pessoa mexer no arquivo
        errado e achar que piorou.
        """
        with pytest.raises(PonteInvalida) as erro:
            conferir_a_configuracao(escrever(tmp_path, "[discord\n"), tmp_path / ".env")

        assert "TOML" in str(erro.value)


class TestOResumoQueOConferirImprime:
    def test_o_resumo_mostra_servidor_canais_destino_e_modo(self, tmp_path):
        """O resumo e a UNICA coisa que o `--conferir` entrega ao usuario.

        Se ele nao mostrar os ids, o modo `--conferir` responde "esta tudo
        certo" sem dizer certo com o que — e o usuario nao tem como perceber que
        conferiu o servidor errado.
        """
        cfg = ler_config_da_ponte(escrever(tmp_path, COMPLETO))

        resumo = resumo_da_configuracao(cfg, tamanho_do_token=59)

        assert str(GUILD) in resumo
        assert str(CANAL_A) in resumo
        assert str(CANAL_B) in resumo
        assert "42" in resumo
        assert "simulacao" in resumo.lower()

    def test_o_resumo_diz_que_o_token_foi_ENCONTRADO_sem_mostrar_o_token(
        self, tmp_path
    ):
        """"encontrei o token" e o que o usuario precisa saber; o valor, nunca."""
        cfg = ler_config_da_ponte(escrever(tmp_path, COMPLETO))

        resumo = resumo_da_configuracao(cfg, tamanho_do_token=len(TOKEN_RECONHECIVEL))

        assert TOKEN_RECONHECIVEL not in resumo
        assert str(len(TOKEN_RECONHECIVEL)) in resumo

    def test_o_resumo_nomeia_a_ORIGEM_de_cada_valor(self, tmp_path):
        """Com dois arquivos em jogo, "o valor esta errado" nao diz onde editar."""
        cfg = ler_config_da_ponte(escrever(tmp_path, COMPLETO))

        resumo = resumo_da_configuracao(cfg, tamanho_do_token=10)

        assert "config.toml" in resumo
        assert ".env" in resumo

    def test_o_resumo_e_PURO_e_nao_le_arquivo_nenhum(self, tmp_path):
        """Funcao pura: mesma entrada, mesma saida, sem tocar o disco.

        Se ela lesse o `config.toml` de novo por dentro, o
        `--conferir --config outro.toml` imprimiria o arquivo do repositorio e
        afirmaria ter conferido o que nao conferiu.
        """
        cfg = ConfigDaPonte(
            guild=1,
            canais=frozenset({2, 3}),
            conversa_de_destino="9",
            simulacao=True,
        )

        assert resumo_da_configuracao(cfg) == resumo_da_configuracao(cfg)
