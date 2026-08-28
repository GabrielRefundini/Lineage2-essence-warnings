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
    ConfigDaPonte,
    PonteInvalida,
    ler_config_da_ponte,
    ler_token_do_discord,
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


def escrever(pasta: Path, texto: str) -> Path:
    alvo = pasta / "config.toml"
    alvo.write_text(texto, encoding="utf-8")
    return alvo


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
        """A ponte nao tem padrao razoavel: sem canais ela nao tem o que ouvir."""
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(tmp_path / "nao-existe.toml")

        assert "config.toml" in str(erro.value)

    def test_secao_discord_ausente_e_erro_e_a_mensagem_nomeia_a_secao(self, tmp_path):
        """"nao encontrei a configuracao" nao ajuda ninguem a consertar nada."""
        outro = "[[evento]]\nnome = 'TvT'\n"

        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, outro))

        assert "[discord]" in str(erro.value)

    def test_toml_quebrado_diz_que_e_toml_quebrado(self, tmp_path):
        """Erro de digitacao no arquivo nao pode virar KeyError sem contexto."""
        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, "[discord\nguild = 1\n"))

        assert "TOML" in str(erro.value)

    @pytest.mark.parametrize(
        "chave", ["guild", "canais", "conversa_de_destino", "simulacao"]
    )
    def test_chave_ausente_levanta_nomeando_a_chave_que_falta(self, chave, tmp_path):
        """A mensagem tem que dizer QUAL chave, senao o usuario adivinha.

        Sao quatro chaves e um arquivo que o usuario edita a mao; "falta uma
        chave" mandaria ele conferir as quatro numa janela de cmd.
        """
        linhas = [linha for linha in COMPLETO.splitlines() if not linha.startswith(chave)]

        with pytest.raises(PonteInvalida) as erro:
            ler_config_da_ponte(escrever(tmp_path, "\n".join(linhas)))

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


class TestOTokenSaiDoEnv:
    def test_o_token_sai_do_env_pela_chave_DISCORD_TOKEN(self, tmp_path):
        """CONF-01: o token nao mora no config.toml, que e versionado.

        O config.toml e o arquivo que o usuario tira print e cola no grupo
        pedindo ajuda. O token do bot nao pode estar nele.
        """
        env = tmp_path / ".env"
        env.write_text("DISCORD_TOKEN=abc.123.xyz\n", encoding="utf-8")

        assert ler_token_do_discord(env) == "abc.123.xyz"

    def test_env_ausente_diz_o_conserto_e_nao_so_o_problema(self, tmp_path):
        """Quem esbarra nisto e um leigo com uma janela de cmd aberta."""
        with pytest.raises(PonteInvalida) as erro:
            ler_token_do_discord(tmp_path / ".env")

        texto = str(erro.value)
        assert "DISCORD_TOKEN" in texto
        assert "ENV-EXEMPLO.txt" in texto

    def test_token_vazio_e_tratado_como_ausente(self, tmp_path):
        """`DISCORD_TOKEN=` copiado do exemplo e o caso mais comum de todos."""
        env = tmp_path / ".env"
        env.write_text("DISCORD_TOKEN=\n", encoding="utf-8")

        with pytest.raises(PonteInvalida) as erro:
            ler_token_do_discord(env)

        assert "DISCORD_TOKEN" in str(erro.value)

    def test_nenhuma_mensagem_de_erro_carrega_o_VALOR_do_token(self, tmp_path):
        """Um erro que despeja o `.env` inteiro vaza o token para o log rotativo.

        E dali para um print no grupo, porque a primeira coisa que um usuario
        faz quando o programa reclama e fotografar o console. Por isso o `.env`
        deste teste tem uma chave com cara de token que a funcao NAO procura: a
        implementacao ingenua (`f"nao achei nada em {env}"`) fica vermelha aqui.
        """
        segredo = "MTIzNDU2Nzg5MDEyMzQ1Njc4.Gabcde.NAO-PODE-VAZAR"
        env = tmp_path / ".env"
        env.write_text(f"DISCORD_TOKEN_ANTIGO={segredo}\n", encoding="utf-8")

        with pytest.raises(PonteInvalida) as erro:
            ler_token_do_discord(env)

        assert segredo not in str(erro.value)
        assert "DISCORD_TOKEN" in str(erro.value)
