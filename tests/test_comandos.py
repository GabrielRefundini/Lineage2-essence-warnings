"""O scanner passa a OUVIR. Abrir a volta e abrir superficie de ataque.

O Chatwoot do usuario NAO e dedicado a este projeto: medido, a conta tem 22
conversas e 11 com mensagens de entrada, de CLIENTES REAIS. Uma delas, do Joao
Pedro, diz literalmente "Quero cancelar".

Um leitor ingenuo obedeceria a ele. Por isso a maior parte destes testes e
sobre o que o scanner se RECUSA a fazer.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from l2scanner.agenda import AgendaInvalida
from l2scanner.comandos import (
    _AJUDA,
    COMANDOS_DE_MEMBRO,
    ORIGEM_DONO,
    ORIGEM_MEMBRO,
    Comando,
    ConfiguracaoPerigosa,
    LeitorDeComandos,
    Membro,
    _mesma_pessoa,
    autorizado_para,
    chave_da_mensagem,
    colisoes_de_telefone,
    comandos_novos,
    interpretar,
    interpretar_dinamico,
    texto_de_ajuda,
)
from l2scanner import comandos, config
from l2scanner.config import ler_membros
from l2scanner.loot import apelido

# A ordem de exibicao combinada: do que se usa no meio do farm para o meta.
#
# "Presenca" entra ANTES de "Loot do Solo Boss" porque essa e a ordem do ciclo
# do boss: primeiro a party diz quem vai, so depois se decide de quem e o loot.
#
# "Identidade" entra DEPOIS de "Loot do Solo Boss" e ANTES de "Ajuda": ela e a
# familia mais nova e a menos usada no meio do farm — o batismo acontece uma
# vez por pessoa, para sempre — entao ela nao pode empurrar para baixo o que se
# digita todo dia.
_FAMILIAS_ESPERADAS = (
    "Vigilancia",
    "Silencio",
    "Presenca",
    "Loot do Solo Boss",
    "Identidade",
    "Ajuda",
)

# O apelido de assinatura que as provas derivadas da tabela `_AJUDA` usam para
# substituir o `<apelido>` anunciado pelo `/batizar`.
#
# ELE E HEX E NAO UM NOME, e isso e o ponto: `<apelido>` e `<nick>` sao dois
# placeholders com CHARSETS diferentes, e substituir os dois pela mesma coisa
# faria as provas de ponta a ponta lerem uma sintaxe que o parser recusa — ou
# seja, elas passariam por acidente, sem nunca chegar ao comando.
_APELIDO_DE_EXEMPLO = "0123ab"



def _tem_borda(texto: str) -> bool:
    """Alguma linha e uma borda de moldura — feita so de asteriscos?

    E como se afirma "isto NAO passou por `console.moldurar`" sem depender do
    tamanho da borda, que muda com o comprimento do texto.
    """
    return any(
        despido and set(despido) == {"*"}
        for despido in (linha.strip() for linha in texto.splitlines())
    )


def msg(id_, texto, tipo=0, autor="Yazalaque", private=False):
    return {
        "id": id_,
        "content": texto,
        "message_type": tipo,
        "private": private,
        "sender": {"name": autor},
    }


class TestInterpretar:
    def test_o_comando_com_prefixo_e_reconhecido(self):
        assert interpretar(".cancelar") is Comando.CANCELAR_SILENCIO

    def test_a_barra_e_o_prefixo_oficial(self):
        """A barra segue a convencao do proprio jogo (`/target`, `/invite`).

        A mao que joga ja digita barra. Este teste e a fatia vertical: se ele
        passa, `PREFIXO` virou a barra e os DOIS leitores do parser
        (`interpretar` e `interpretar_dinamico`) foram pelo mesmo caminho.
        """
        assert comandos.PREFIXO == "/"
        assert interpretar("/cancelar") is Comando.CANCELAR_SILENCIO
        assert interpretar("/join") is Comando.JOIN
        assert interpretar("/status") is Comando.STATUS
        # A forma de duas palavras vale na barra igual valia no legado.
        assert interpretar("/cancelar silencio") is Comando.CANCELAR_SILENCIO

    def test_a_forma_antiga_continua_reconhecida(self):
        """O legado nao foi cortado, e o motivo esta na constante do prefixo.

        Comando nao reconhecido morre EM SILENCIO — nao existe resposta de
        recusa. Num corte seco, os party-mates ja treinados no ponto nao
        receberiam NADA e concluiriam que o bot caiu.
        """
        assert "." in comandos.PREFIXOS
        assert interpretar(".join") is Comando.JOIN
        assert interpretar(".cancelar silencio") is Comando.CANCELAR_SILENCIO

    def test_sem_prefixo_nenhum_continua_sendo_nada(self):
        """Alargar o vocabulario de prefixos nao afrouxa a trava do prefixo."""
        for texto in ("join", "cancelar", "status", "leave"):
            assert interpretar(texto) is None, texto

    def test_aceita_as_formas_que_a_pessoa_lembra(self):
        for forma in (".cancelar", ".cancelar silencio", ".silencio", ".voltar"):
            assert interpretar(forma) is Comando.CANCELAR_SILENCIO, forma

    def test_ignora_maiuscula_e_espaco_sobrando(self):
        assert interpretar("  .CANCELAR  ") is Comando.CANCELAR_SILENCIO

    def test_SEM_prefixo_nao_e_comando(self):
        """A trava central: conversar sobre a acao nao e pedir a acao."""
        for texto in (
            "cancelar",
            "vamos cancelar o silencio?",
            "quero cancelar",
            "Quero cancelar",  # a mensagem real do Joao Pedro, cliente
            "alguem cancela isso",
        ):
            assert interpretar(texto) is None, texto

    def test_texto_vazio_ou_ausente(self):
        assert interpretar(None) is None
        assert interpretar("") is None
        assert interpretar("   ") is None

    def test_prefixo_com_palavra_desconhecida_nao_faz_nada(self):
        assert interpretar(".exportar tudo") is None
        assert interpretar(".rm -rf") is None

    def test_o_vocabulario_e_fechado(self):
        """Cada item e algo que qualquer um autorizado pode mandar o bot fazer.

        A lista curta nao e falta de imaginacao — e o limite do estrago
        possivel. Quando ela crescer, e para crescer de proposito.
        """
        assert set(Comando) == {
            Comando.CANCELAR_SILENCIO,
            Comando.STATUS,
            Comando.SOLO,
            Comando.PARTY,
            # Entrar e sair da lista de presenca do proximo Solo Boss.
            # Crescimento de proposito, e de uma natureza que a lista nunca
            # tinha tido: foram os PRIMEIROS comandos alcancaveis por um
            # SEGUNDO nivel de autorizacao — o `[[membro]]` do config.toml. A
            # `JANELA`, mais abaixo, e o terceiro e entrou por outro argumento.
            # Todos os demais continuam so para o nivel de dono. Ver
            # `TestFronteiraDeAutorizacao`.
            Comando.JOIN,
            Comando.LEAVE,
            # O controle de loot do Solo Boss. Crescimento DE PROPOSITO:
            # designar quem pega o proximo, e consultar quanto um nick pegou.
            Comando.LOOT_DESIGNAR,
            Comando.LOOT_CONSULTA,
            # E desmarcar. O unico DESTRUTIVO da lista — entrou de proposito,
            # porque sem ele o proximo boss nao tinha como voltar a ser de
            # ninguem sem editar arquivo e reiniciar o scanner.
            Comando.LOOT_CANCELAR,
            # E corrigir um loot JA CONSUMADO. Tambem de proposito: reescreve
            # HISTORICO, que nunca e podado. O contrapeso e a mira fixa no
            # registro mais recente — nao ha sintaxe para atingir a
            # estatistica antiga.
            Comando.LOOT_CORRIGIR,
            # E registrar o loot de um boss que ja passou, mesmo sem nunca ter
            # havido designacao — o caso que o `.corrigir` nao alcanca, porque
            # ele so troca o dono de um registro que ja existe. E o de MAIOR
            # alcance da lista: ele tem sintaxe para enderecar o passado. O
            # contrapeso e outro, e proprio dele — o horario tem que encaixar
            # numa ocorrencia real do Solo Boss, e a resposta sempre diz o dia.
            Comando.LOOT_ATRIBUIR,
            # E a ajuda. Ela nao muda estado nenhum — o estrago possivel dela
            # e outro: a lista de comandos e um mapa da superficie de ataque.
            # Por isso ela sai pelas MESMAS cinco travas dos outros e so na
            # conversa de origem, sem eco no grupo. Ver `TestAjuda`.
            Comando.AJUDA,
            # E desligar/religar TODOS os avisos do Solo Boss. Crescimento DE
            # PROPOSITO, e de uma natureza nova: e o primeiro par que muda o
            # que o GRUPO INTEIRO recebe por tempo indeterminado, e o efeito
            # dele e a AUSENCIA de mensagem — indistinguivel, de fora, do bot
            # ter caido. Os dois contrapesos: o `/status` conta que esta
            # desligado, e nenhum dos dois e alcancavel por `[[membro]]`.
            #
            # SAO DOIS, E NAO UM COM ARGUMENTO: um `/avisos <evento> off`
            # alcancaria TvT e Prime, que ninguem pediu. O armazenamento e o
            # gate ja sao genericos por evento; a SUPERFICIE nao e.
            Comando.DESATIVAR_SOLO_BOSS,
            Comando.ATIVAR_SOLO_BOSS,
            # E desligar/religar so a LISTA DE PRESENCA do Solo Boss. Mesma
            # natureza do par acima — muda o que o GRUPO INTEIRO recebe por
            # tempo indeterminado —, com um recorte mais fino: cai a chamada
            # "Quem vai?", o /entrar, o /sair, o fechamento da lista e a
            # designacao de loot, e o lembrete de 10 minutos CONTINUA saindo.
            #
            # SAO QUATRO E NAO DOIS, e o par novo nao e redundante com o de
            # cima: nenhuma das duas chaves contem a outra. O
            # /desativarsoloboss cala mais avisos; este alcanca superficies que
            # aquele nao toca. Um comando so, fundindo as duas, esconderia
            # metade do estado e deixaria o usuario sem saber qual religa o
            # que.
            Comando.DESATIVAR_LISTA,
            Comando.ATIVAR_LISTA,
            # E a janela de respawn dos bosses vigiados, sob demanda.
            # Crescimento DE PROPOSITO, e o de menor estrago possivel da lista:
            # e o primeiro comando de MEMBRO que nao escreve nada — nao muda
            # estado, nao fala do remetente, nao muda o que o grupo recebe. O
            # que ele revela, o proprio bot ja anuncia ao grupo por conta
            # propria quando cada janela vence; ele so adianta, sob demanda, um
            # texto que ja e publico para essa mesma plateia.
            #
            # O SIMBOLO E GENERICO E A FORMA ESCRITA E QUE E `/tiat`. O
            # workstream inteiro le os blocos `[[boss]]` do config.toml, e um
            # membro chamado `TIAT` seria o unico ponto do sistema onde trocar
            # de boss exigiria editar codigo. Ver `_VOCABULARIO`, onde `tiat`
            # mora ao lado de `janela`, `boss` e `respawn`.
            Comando.JANELA,
            # E dar NOME a uma assinatura que o scanner aprendeu sozinho.
            # Crescimento DE PROPOSITO, e o TERCEIRO comando que escreve estado
            # duravel que nunca e podado, depois de `LOOT_CORRIGIR` e
            # `LOOT_ATRIBUIR`.
            #
            # O dano de um nome errado e da MESMA familia deles: corrupcao
            # duravel e dificil de notar, num acervo sem comando de esquecer e
            # sem backup, e o sintoma nao e um erro — e a party socorrendo a
            # pessoa errada. Por isso ele nasce FORA de `COMANDOS_DE_MEMBRO`
            # (decisao 2 do ROADMAP), e nasce sozinho: o conjunto e LISTA DE
            # INCLUSAO, entao ninguem precisou lembrar de exclui-lo.
            #
            # O ALVO E A CHAVE DE CONTEUDO, E NUNCA UMA LINHA (D-03). Nao ha
            # sintaxe que alcance uma posicao: `/batizar 3 Mostarda` e recusado
            # como apelido desconhecido, porque "3" e so um prefixo hex que nao
            # casa chave nenhuma.
            Comando.BATIZAR,
        }

    def test_as_formas_do_desligamento_do_boss(self):
        """As duas formas de cada um, e nenhuma a mais.

        Cada palavra registrada no `_VOCABULARIO` e um personagem que deixa de
        ser consultavel por `/<nick>` — o preco ja documentado ali. Por isso
        sao duas por comando: a completa, que a ajuda anuncia, e a curta, que a
        mao digita no meio de um farm.
        """
        for forma in ("/desativarsoloboss", "/desativar-solo-boss", "/desativarboss"):
            assert interpretar(forma) is Comando.DESATIVAR_SOLO_BOSS, forma
        for forma in ("/ativarsoloboss", "/ativar-solo-boss", "/ativarboss"):
            assert interpretar(forma) is Comando.ATIVAR_SOLO_BOSS, forma

    def test_desativar_SOZINHO_nao_desliga_nada(self):
        """A mesma disciplina do D-02 no `.loot`: comando sem argumento nao
        pode mexer em estado duravel. Quem digita `/desativar` no meio de um
        farm nao disse O QUE desativar, e adivinhar seria calar o boss por
        conta propria."""
        assert interpretar("/desativar") is None
        assert interpretar("/ativar") is None

    def test_as_formas_do_modo_solo(self):
        for forma in (".solo", ".soloplay", ".SOLO"):
            assert interpretar(forma) is Comando.SOLO, forma
        for forma in (".party", ".pt", ".grupo"):
            assert interpretar(forma) is Comando.PARTY, forma

    def test_falar_de_solo_sem_ponto_nao_liga_nada(self):
        for texto in ("vou jogar solo", "solo", "party amanha"):
            assert interpretar(texto) is None, texto


class TestAjuda:
    """A ajuda que nao pode envelhecer.

    O projeto ganhou CINCO comandos em UM dia (`.loot-`, `.<nick>`,
    `.loot-cancelar`, `.corrigir`, `.pegou`). Uma ajuda escrita a mao estaria
    desatualizada antes do fim da semana — e ajuda desatualizada e PIOR que
    ajuda nenhuma, porque ensina sintaxe que NAO FUNCIONA e faz quem digitou
    concluir que o bot esta quebrado.

    Por isso o texto e DERIVADO da tabela `_AJUDA`, e por isso o tripwire
    abaixo existe: sem ele a tabela seria so mais um literal para esquecer.
    """

    # O telefone da allowlist. O round-trip precisa atravessar as CINCO travas
    # reais, e a quinta delas e esta — um round-trip que desligasse a allowlist
    # estaria provando um caminho que nao existe em producao.
    TELEFONE = "+5544997077000"

    def _mensagem(self, texto: str) -> dict:
        return {
            "id": 4242,
            "content": texto,
            "message_type": 0,
            "private": False,
            "sender": {"name": "Yazalaque", "phone_number": self.TELEFONE},
        }

    def test_todo_comando_tem_linha_na_tabela_de_ajuda(self):
        """O TRIPWIRE. Comando novo sem ajuda QUEBRA a suite, de proposito.

        Chaveado pelo ENUM e nao pelo `_VOCABULARIO` porque os comandos
        dinamicos (`.loot-<nick>`, `.<nick>`, `.corrigir-<nick>`, `.pegou`)
        nao moram no vocabulario — eles vivem em `interpretar_dinamico`, e um
        tripwire contra o vocabulario nao os enxergaria.
        """
        faltando = set(Comando) - set(_AJUDA)
        assert not faltando, (
            "comando novo sem entrada na tabela de ajuda: "
            + ", ".join(sorted(c.name for c in faltando))
        )
        sobrando = set(_AJUDA) - set(Comando)
        assert not sobrando, (
            "a tabela de ajuda documenta comando que nao existe mais: "
            + ", ".join(sorted(c.name for c in sobrando))
        )

    def test_toda_sintaxe_anunciada_usa_o_prefixo_OFICIAL(self):
        """O SEGUNDO TRIPWIRE: a tabela so pode anunciar o prefixo oficial.

        Os dois prefixos sao ACEITOS, mas so um e ANUNCIADO. Sem esta prova, a
        proxima linha de ajuda nasceria no prefixo legado por copiar a de cima,
        e a tabela viraria uma mistura dos dois — que e como o usuario aprende
        a sintaxe errada.

        Derivado de `comandos.PREFIXO` e nunca de um literal: assim a prova
        acompanha a constante em vez de ter que ser reescrita junto com ela.
        """
        for comando, linha in _AJUDA.items():
            assert linha.sintaxe.startswith(comandos.PREFIXO), (
                f"{comando.name} anuncia {linha.sintaxe!r}, que nao comeca "
                f"pelo prefixo oficial {comandos.PREFIXO!r}"
            )
            for forma in linha.apelidos:
                assert forma.startswith(comandos.PREFIXO), (
                    f"{comando.name} anuncia o apelido {forma!r}, que nao "
                    f"comeca pelo prefixo oficial {comandos.PREFIXO!r}"
                )

    def test_o_texto_entregue_nao_anuncia_o_prefixo_legado(self):
        """O que chega no celular fala SO a barra.

        O tripwire acima olha a tabela; este olha o texto montado, que e o que
        o usuario le — inclusive o cabecalho, que nao vem de nenhuma linha.
        """
        texto = texto_de_ajuda()
        for comando, linha in _AJUDA.items():
            legado = "." + linha.sintaxe[len(comandos.PREFIXO) :]
            assert legado not in texto, (
                f"o texto da ajuda ainda anuncia {legado!r} ({comando.name})"
            )
        assert "ponto" not in texto.lower()

    def test_toda_sintaxe_anunciada_volta_como_o_comando_certo(self):
        """A ajuda nao tem como ensinar sintaxe que nao funciona.

        Cada sintaxe da tabela e passada pelo CAMINHO REAL de leitura
        (`comandos_novos` -> `interpretar` -> `interpretar_dinamico`), com as
        cinco travas ligadas. Um parser paralelo montado aqui no teste provaria
        a coisa errada: provaria que o teste concorda consigo mesmo.

        SAO TRES MARCADORES, E O TERCEIRO NASCEU COM O BATISMO. `<nick>` e
        `<hora>` ja estavam aqui — o segundo entrou junto com o `.pegou` —, e
        `<apelido>` entrou junto com o `/batizar`, pela mesma razao.

        ACRESCENTAR UMA SUBSTITUICAO NAO E AFROUXAR O CASO, e a proxima pessoa
        a ler o diff vai desconfiar que e. O caso continua rodando o caminho
        real com as cinco travas ligadas e continua afirmando que a sintaxe
        anunciada volta como o comando certo; o que mudou e que a TABELA passou
        a ter um marcador a mais. A alternativa seria anunciar uma sintaxe sem
        marcador, o que ensinaria uma forma que nao existe — exatamente o que
        este tripwire impede. E cada marcador tem CHARSET proprio: substituir
        `<apelido>` por um nick faria o parser recusar por charset, e o caso
        passaria a afirmar que ninguem alcanca o comando, com cara de prova.
        """
        conhecidos = frozenset({apelido("J4guar")})
        for esperado, linha in _AJUDA.items():
            texto = (
                linha.sintaxe.replace("<nick>", "J4guar")
                .replace("<hora>", "18:00")
                .replace("<apelido>", _APELIDO_DE_EXEMPLO)
            )
            achados = comandos_novos(
                [self._mensagem(texto)],
                set(),
                [self.TELEFONE],
                nicks_conhecidos=conhecidos,
            )
            assert [m.comando for m in achados] == [esperado], (
                f"a ajuda anuncia {texto!r} para {esperado.name}, mas o "
                f"caminho real devolveu {[m.comando for m in achados]}"
            )

    def test_a_presenca_anuncia_o_vocabulario_PORTUGUES(self):
        """A decisao do usuario, escrita como PROVA e nao como comentario.

        Os outros tripwires desta classe sao DERIVADOS da tabela de proposito:
        eles perguntam "a sintaxe anunciada comeca pelo prefixo oficial?" e
        "ela volta como o comando certo?", e as duas respostas continuam sim
        se alguem inverter o vocabulario de volta para o ingles no proximo
        ajuste de texto. Esta e a unica prova que quebra nesse caso.

        A segunda metade importa tanto quanto a primeira: a forma inglesa tem
        que continuar ANUNCIADA entre os apelidos. Sem esta asercao,
        "inverter" viraria "apagar" sem alarme nenhum, e quem decorou o nome
        antigo descobriria por acidente que ele sumiu da vitrine.
        """
        entrar = _AJUDA[Comando.JOIN]
        sair = _AJUDA[Comando.LEAVE]
        assert entrar.sintaxe == comandos.PREFIXO + "entrar", entrar.sintaxe
        assert sair.sintaxe == comandos.PREFIXO + "sair", sair.sintaxe
        assert comandos.PREFIXO + "join" in entrar.apelidos, entrar.apelidos
        assert comandos.PREFIXO + "leave" in sair.apelidos, sair.apelidos

    @pytest.mark.parametrize("prefixo", comandos.PREFIXOS)
    def test_os_quatro_nomes_da_presenca_seguem_valendo(self, prefixo):
        """Os quatro nomes convivem, e nenhum deles pode cair em silencio.

        Comando nao reconhecido e DESCARTADO no `continue` do laco de
        autorizacao — nao existe resposta de recusa. Quem digitasse o nome
        demovido receberia NADA, e do lado dele isso e indistinguivel de o bot
        ter caido. Por isso a democao e de VITRINE, nunca de vocabulario.

        Pelo CAMINHO REAL (`comandos_novos`, cinco travas ligadas) e
        parametrizado sobre `comandos.PREFIXOS`, nunca escrito duas vezes: um
        terceiro prefixo, se um dia existir, ja nasce provado aqui.
        """
        conhecidos = frozenset({apelido("J4guar")})
        for nome, esperado in (
            ("entrar", Comando.JOIN),
            ("join", Comando.JOIN),
            ("sair", Comando.LEAVE),
            ("leave", Comando.LEAVE),
        ):
            texto = prefixo + nome
            achados = comandos_novos(
                [self._mensagem(texto)],
                set(),
                [self.TELEFONE],
                nicks_conhecidos=conhecidos,
            )
            assert [m.comando for m in achados] == [esperado], (
                f"{texto!r} devia voltar como {esperado.name}, mas o caminho "
                f"real devolveu {[m.comando for m in achados]}"
            )

    def test_todo_apelido_anunciado_volta_como_o_comando_certo(self):
        """A tabela nao tem dois niveis de veracidade — mas tinha dois niveis
        de prova.

        O teste vizinho percorre SO o campo `sintaxe`. Um apelido anunciado
        que nao funciona ensina sintaxe morta exatamente como uma sintaxe
        anunciada que nao funciona; e no instante em que uma forma e DEMOVIDA
        a apelido, ela sairia da cobertura ponta-a-ponta em silencio. Mesmo
        caminho real do vizinho, mesmas cinco travas.
        """
        conhecidos = frozenset({apelido("J4guar")})
        for esperado, linha in _AJUDA.items():
            for forma in linha.apelidos:
                texto = (
                    forma.replace("<nick>", "J4guar")
                    .replace("<hora>", "18:00")
                    .replace("<apelido>", _APELIDO_DE_EXEMPLO)
                )
                achados = comandos_novos(
                    [self._mensagem(texto)],
                    set(),
                    [self.TELEFONE],
                    nicks_conhecidos=conhecidos,
                )
                assert [m.comando for m in achados] == [esperado], (
                    f"a ajuda anuncia o apelido {texto!r} para "
                    f"{esperado.name}, mas o caminho real devolveu "
                    f"{[m.comando for m in achados]}"
                )

    def test_o_texto_cita_todas_as_sintaxes(self):
        """Pega o caso em que uma familia inteira deixa de ser emitida.

        O tripwire acima garante que a LINHA existe na tabela; so este garante
        que ela chegou no texto.
        """
        texto = texto_de_ajuda()
        for comando, linha in _AJUDA.items():
            assert linha.sintaxe in texto, (
                f"{comando.name} tem linha na tabela mas sumiu do texto"
            )

    def test_as_familias_saem_na_ordem_combinada(self):
        """Vigilancia, silencio, loot, ajuda — do mais usado ao meta."""
        texto = texto_de_ajuda()
        posicoes = [texto.index(f) for f in _FAMILIAS_ESPERADAS]
        assert posicoes == sorted(posicoes), (
            f"as familias sairam fora de ordem: {_FAMILIAS_ESPERADAS}"
        )

    def test_as_formas_escritas_da_ajuda(self):
        for forma in (".help", ".ajuda", ".comandos", ".HELP", ".?"):
            assert interpretar(forma) is Comando.AJUDA, forma

    def test_ajuda_sem_ponto_NAO_e_comando(self):
        """A ajuda nao escapa da regra do prefixo so por ser inofensiva."""
        for texto in ("help", "ajuda", "me ajuda ai", "quais os comandos"):
            assert interpretar(texto) is None, texto

    def test_a_ajuda_nao_sai_moldurada(self):
        """Guarda de D-04 no proprio produtor do texto.

        `moldurar` tem largura casada com a linha mais longa; com onze linhas
        a borda viraria uma parede de asteriscos no celular.
        """
        for linha in texto_de_ajuda().splitlines():
            despido = linha.strip()
            assert not (despido and set(despido) == {"*"}), (
                f"a ajuda saiu moldurada: {linha!r}"
            )


class TestInterpretarDinamico:
    """Os comandos com argumento: `.loot-<nick>` e `.<nick>`.

    Superficie dinamica e superficie de ataque. Por isso o desenho e todo
    restricao: nick com charset fechado, consulta so de nick conhecido, o
    vocabulario fixo com precedencia e `.offline` excluido por nome.
    """

    def test_loot_com_hifen_designa(self):
        assert interpretar_dinamico(".loot-j4guar", frozenset()) == (
            Comando.LOOT_DESIGNAR,
            "j4guar",
        )

    def test_o_comando_e_case_insensitive_mas_o_nick_e_preservado(self):
        """`.LOOT-J4guar` designa "J4guar", nao "j4guar" — a resposta vai
        mostrar o nick como a pessoa o escreveu."""
        assert interpretar_dinamico(".LOOT-J4guar", frozenset()) == (
            Comando.LOOT_DESIGNAR,
            "J4guar",
        )

    def test_loot_em_duas_palavras_tambem_designa(self):
        assert interpretar_dinamico(".loot j4guar", frozenset()) == (
            Comando.LOOT_DESIGNAR,
            "j4guar",
        )

    def test_loot_com_hifen_e_nada_depois_CANCELA(self):
        """`.loot-` apaga a designacao — a sintaxe que o usuario escolheu.

        Antes isto morria em silencio no `_NICK_VALIDO.fullmatch("")`, e nao
        havia como deixar o proximo boss sem dono sem editar arquivo.
        """
        assert interpretar_dinamico(".loot-", frozenset()) == (
            Comando.LOOT_CANCELAR,
            "",
        )

    def test_loot_SOZINHO_continua_sendo_nada(self):
        """A trava de D-02: comando sem argumento nao pode ser destrutivo.

        Quem digita `.loot` no meio de um farm quase sempre esta PERGUNTANDO
        "quem pega o loot?", nao mandando apagar. Um `.loot` que apagasse em
        silencio seria a pior armadilha possivel nesta superficie.
        """
        assert interpretar_dinamico(".loot", frozenset()) is None

    def test_o_nick_normal_nao_virou_cancelamento(self):
        """A regressao que o ramo novo poderia causar: o cancelamento entra
        ANTES do `_NICK_VALIDO`, e um nick comum tem que passar ileso."""
        assert interpretar_dinamico(".loot-J4guar", frozenset()) == (
            Comando.LOOT_DESIGNAR,
            "J4guar",
        )

    def test_as_palavras_reservadas_tambem_cancelam(self):
        """Quem nao lembra que o hifen sozinho basta escreve por extenso.

        O preco esta pago e documentado: um personagem chamado "Cancelar" nao
        pode ser designado. Barato perto de `.loot-cancelar` designar um
        personagem que nao existe e deixar a party sem jeito de desmarcar.
        """
        for texto in (
            ".loot-cancelar",
            ".loot-ninguem",
            ".loot-nenhum",
            ".loot-limpar",
            ".LOOT-CANCELAR",  # o comando e case-insensitive
        ):
            assert interpretar_dinamico(texto, frozenset()) == (
                Comando.LOOT_CANCELAR,
                "",
            ), texto

    def test_a_palavra_reservada_vale_em_duas_palavras(self):
        """`.loot cancelar` cancela — a alternativa seria DESIGNAR um
        personagem inexistente chamado "cancelar", exatamente o acidente que
        as palavras reservadas existem para evitar."""
        assert interpretar_dinamico(".loot cancelar", frozenset()) == (
            Comando.LOOT_CANCELAR,
            "",
        )

    def test_nick_de_um_caractere_nao_designa(self):
        """`.loot-a` e quase sempre um dedo escorregado, nao uma designacao."""
        assert interpretar_dinamico(".loot-a", frozenset()) is None

    def test_nick_com_caractere_fora_do_charset_nao_designa(self):
        for texto in (".loot-j4;rm", ".loot-j4_guar", ".loot-nick!"):
            assert interpretar_dinamico(texto, frozenset()) is None, texto

    def test_consulta_so_de_nick_conhecido(self):
        """O portao central: sem ele o scanner responderia lixo a qualquer
        `.palavra` do grupo."""
        conhecidos = frozenset({"j4guar"})
        assert interpretar_dinamico(".j4guar", conhecidos) == (
            Comando.LOOT_CONSULTA,
            "j4guar",
        )
        assert interpretar_dinamico(".kaus", conhecidos) is None

    def test_consulta_atravessa_maiusculas(self):
        assert interpretar_dinamico(".J4GUAR", frozenset({"j4guar"})) == (
            Comando.LOOT_CONSULTA,
            "J4GUAR",
        )

    def test_offline_NUNCA_e_comando(self):
        """`.offline` e convencao humana do grupo — quem digita esta avisando
        gente, nao o bot. Nem estando no conjunto de nicks ele vira consulta."""
        assert interpretar_dinamico(".offline", frozenset({"offline"})) is None

    def test_o_vocabulario_fixo_tem_precedencia(self):
        """Um nick homonimo de comando jamais sombreia o comando."""
        for palavra in ("status", "cancelar", "solo", "party", "pt", "grupo"):
            conhecidos = frozenset({palavra})
            assert interpretar_dinamico(f".{palavra}", conhecidos) is None, palavra

    def test_corrigir_com_hifen_corrige(self):
        assert interpretar_dinamico(".corrigir-kaus", frozenset()) == (
            Comando.LOOT_CORRIGIR,
            "kaus",
        )

    def test_corrigir_em_duas_palavras_faz_a_MESMA_coisa(self):
        """A porta dos fundos que o `.loot cancelar` ja abriu uma vez.

        Tratar so o ramo do hifen deixaria `.corrigir kaus` morrer em silencio
        — e quem digitou acharia que corrigiu. Foi exatamente esse o bug da
        tarefa anterior, onde `.loot cancelar` DESIGNAVA um personagem
        chamado "cancelar".
        """
        assert interpretar_dinamico(".corrigir kaus", frozenset()) == (
            Comando.LOOT_CORRIGIR,
            "kaus",
        )

    def test_corrigir_e_case_insensitive_mas_o_nick_e_preservado(self):
        assert interpretar_dinamico(".CORRIGIR-Kaus", frozenset()) == (
            Comando.LOOT_CORRIGIR,
            "Kaus",
        )

    def test_corrigir_SOZINHO_nao_faz_nada(self):
        """Comando sem argumento nao pode reescrever historico.

        E o `return None` explicito do ramo tambem e o que impede `.corrigir`
        de escorregar para o ramo de consulta logo abaixo, onde
        `_NICK_VALIDO` casa a palavra "corrigir" como se fosse um nick.
        """
        assert interpretar_dinamico(".corrigir", frozenset()) is None

    def test_corrigir_nao_vira_consulta_nem_com_nick_homonimo(self):
        """A prova direta de que a porta fica fechada: mesmo existindo um
        personagem chamado "Corrigir", o comando nao vira consulta dele."""
        assert interpretar_dinamico(".corrigir", frozenset({"corrigir"})) is None

    def test_nick_invalido_nao_corrige(self):
        """O mesmo `_NICK_VALIDO` dos outros comandos, sem excecao."""
        for texto in (".corrigir-a", ".corrigir-j4;rm", ".corrigir a", ".corrigir-"):
            assert interpretar_dinamico(texto, frozenset()) is None, texto

    def test_pegou_em_duas_palavras_registra(self):
        """`.pegou <hora> <nick>`: a forma enderecada, que alcanca um boss
        que ja passou mesmo sem nunca ter havido designacao."""
        assert interpretar_dinamico(".pegou 18:00 Korzis", frozenset()) == (
            Comando.LOOT_ATRIBUIR,
            "18:00 Korzis",
        )

    def test_pegou_SOZINHO_nao_faz_nada(self):
        """Comando sem argumento nao reescreve historico — a mesma trava do
        `.loot` e do `.corrigir`."""
        assert interpretar_dinamico(".pegou", frozenset()) is None

    def test_pegou_nao_vira_consulta_nem_com_nick_homonimo(self):
        """A prova direta de que o `return None` do ramo fecha a porta.

        Sem ele o fluxo cairia no ramo de consulta logo abaixo, onde
        `_NICK_VALIDO` casa a palavra "pegou": um personagem chamado "Pegou"
        transformaria o comando numa consulta dele. Foi exatamente esse erro
        que fez `.loot cancelar` DESIGNAR um personagem chamado "cancelar".
        """
        assert interpretar_dinamico(".pegou", frozenset({"pegou"})) is None

    def test_pegou_com_hifen_faz_a_MESMA_coisa(self):
        """A mao do usuario ja aprendeu `.loot-` e `.corrigir-`.

        Tratar so uma das duas formas foi exatamente o erro que fez
        `.loot cancelar` DESIGNAR um personagem chamado "cancelar": a forma
        de duas palavras nunca e opcional num comando que mexe em estado
        duravel, e a de hifen tambem nao.
        """
        assert interpretar_dinamico(".pegou-18:00 Korzis", frozenset()) == (
            Comando.LOOT_ATRIBUIR,
            "18:00 Korzis",
        )

    def test_pegou_com_hifen_e_data_carrega_as_tres_partes(self):
        assert interpretar_dinamico(".pegou-24/08 18:00 Korzis", frozenset()) == (
            Comando.LOOT_ATRIBUIR,
            "24/08 18:00 Korzis",
        )

    def test_pegou_e_case_insensitive_mas_o_nick_e_preservado(self):
        assert interpretar_dinamico(".PEGOU 18:00 Korzis", frozenset()) == (
            Comando.LOOT_ATRIBUIR,
            "18:00 Korzis",
        )

    def test_as_formas_que_NAO_registram(self):
        """O portao e `interpretar_pegou`: o parser so reconhece o comando
        quando a gramatica aceita o argumento inteiro. Aceitar aqui o que o
        responder nao sabe executar seria o pior desfecho possivel."""
        for texto in (
            ".pegou 18:00",  # sem nick
            ".pegou Korzis",  # sem hora
            ".pegou 18:00 a",  # nick curto demais
            ".pegou 18:00 j4;rm",  # fora do charset
            ".pegou 25:00 Korzis",  # hora que nao existe
            ".pegou 18:70 Korzis",  # minuto que nao existe
            ".pegou-",
            ".pegou 18:00 20:00 Korzis",  # duas horas, nenhum sentido
        ):
            assert interpretar_dinamico(texto, frozenset()) is None, texto

    def test_o_pegou_nao_deslocou_os_ramos_de_loot_nem_de_corrigir(self):
        """Regressao: o ramo novo entrou entre o `.corrigir` e a consulta, e
        nenhum dos ramos existentes pode ter mudado de comportamento."""
        assert interpretar_dinamico(".loot-j4guar", frozenset()) == (
            Comando.LOOT_DESIGNAR,
            "j4guar",
        )
        assert interpretar_dinamico(".loot", frozenset()) is None
        assert interpretar_dinamico(".loot cancelar", frozenset()) == (
            Comando.LOOT_CANCELAR,
            "",
        )
        assert interpretar_dinamico(".corrigir-kaus", frozenset()) == (
            Comando.LOOT_CORRIGIR,
            "kaus",
        )
        assert interpretar_dinamico(".corrigir kaus", frozenset()) == (
            Comando.LOOT_CORRIGIR,
            "kaus",
        )
        assert interpretar_dinamico(".corrigir", frozenset()) is None
        assert interpretar_dinamico(".j4guar", frozenset({"j4guar"})) == (
            Comando.LOOT_CONSULTA,
            "j4guar",
        )

    def test_o_comando_novo_nao_deslocou_os_ramos_de_loot(self):
        """Regressao: `.corrigir` entrou entre o ramo do `.loot` e o da
        consulta, e nenhum dos dois pode ter mudado de comportamento."""
        assert interpretar_dinamico(".loot-j4guar", frozenset()) == (
            Comando.LOOT_DESIGNAR,
            "j4guar",
        )
        assert interpretar_dinamico(".loot-", frozenset()) == (
            Comando.LOOT_CANCELAR,
            "",
        )
        assert interpretar_dinamico(".loot", frozenset()) is None

    def test_sem_prefixo_nao_e_nada(self):
        assert interpretar_dinamico("j4guar", frozenset({"j4guar"})) is None
        assert interpretar_dinamico("loot j4guar", frozenset()) is None

    def test_texto_vazio_ou_ausente(self):
        assert interpretar_dinamico(None, frozenset()) is None
        assert interpretar_dinamico("", frozenset()) is None
        assert interpretar_dinamico("   ", frozenset()) is None


class TestOsDoisPrefixos:
    """A barra e o oficial; o ponto e legado ACEITO e jamais anunciado.

    Os dois convivem por um motivo mecanico, nao por gosto: comando nao
    reconhecido morre EM SILENCIO, no `continue` do laco de autorizacao de
    `comandos_novos`. Nao existe resposta de recusa. Num corte seco os cinco
    party-mates ja treinados no ponto digitariam `.join`, nao receberiam NADA,
    e concluiriam que o bot caiu — que e o pior modo de falha possivel para
    uma mudanca cosmetica.

    A prova aqui e de PARIDADE (as duas formas devolvem o MESMO `Comando`) e
    nao de igualdade de texto, porque as duas coisas sao deliberadamente
    diferentes: o parser aceita duas formas, a superficie de texto anuncia
    UMA. E a paridade e parametrizada sobre `comandos.PREFIXOS` em vez de
    escrita duas vezes, para que um terceiro prefixo, se um dia existir, ja
    nasca provado.
    """

    TELEFONE = "+5544997077000"

    # Amostra representativa: as duas familias do vocabulario fixo que a party
    # usa no meio do farm, a forma de DUAS palavras (que tem caminho proprio em
    # `interpretar`) e o `?`, que atravessa os dois `replace` do miolo.
    FORMAS = [
        ("cancelar", Comando.CANCELAR_SILENCIO),
        ("cancelar silencio", Comando.CANCELAR_SILENCIO),
        ("status", Comando.STATUS),
        ("solo", Comando.SOLO),
        ("party", Comando.PARTY),
        ("join", Comando.JOIN),
        ("entrar", Comando.JOIN),
        ("leave", Comando.LEAVE),
        ("sair", Comando.LEAVE),
        ("help", Comando.AJUDA),
        ("?", Comando.AJUDA),
    ]

    def _mensagem(self, id_: int, texto: str) -> dict:
        return {
            "id": id_,
            "content": texto,
            "message_type": 0,
            "private": False,
            "sender": {"name": "Yazalaque", "phone_number": self.TELEFONE},
        }

    @pytest.mark.parametrize("prefixo", comandos.PREFIXOS)
    @pytest.mark.parametrize("forma,esperado", FORMAS)
    def test_o_vocabulario_fixo_tem_PARIDADE_entre_os_prefixos(
        self, prefixo, forma, esperado
    ):
        assert interpretar(prefixo + forma) is esperado

    @pytest.mark.parametrize("prefixo", comandos.PREFIXOS)
    def test_a_palavra_humana_e_recusada_nos_DOIS(self, prefixo):
        """D-05: a exclusao do `offline` e AGNOSTICA de prefixo, de proposito.

        Ela existe porque a palavra e convencao HUMANA do grupo — quem digita
        esta avisando GENTE, nao o bot — e nao pode virar consulta de nick.
        Com a barra o risco praticamente some, mas torna-la especifica de
        prefixo criaria uma divergencia de comportamento entre duas formas que
        devem ser a MESMA coisa, que e o oposto de "os dois valem".
        """
        conhecidos = frozenset({apelido("Offline")})
        assert interpretar(prefixo + "offline") is None
        assert interpretar_dinamico(prefixo + "offline", conhecidos) is None

    @pytest.mark.parametrize("prefixo", comandos.PREFIXOS)
    def test_a_consulta_por_nick_vale_nos_DOIS(self, prefixo):
        """D-06, e ela nao foi escolha solta: e FORCADA pela tabela de ajuda.

        A `_AJUDA` passou a anunciar `/<nick>`, e
        `test_toda_sintaxe_anunciada_volta_como_o_comando_certo` roda a tabela
        INTEIRA pelo caminho real. Anunciar a barra sem aceita-la quebraria a
        suite — este teste so torna a consequencia visivel onde se procura.
        """
        conhecidos = frozenset({apelido("J4guar")})
        assert interpretar_dinamico(prefixo + "J4guar", conhecidos) == (
            Comando.LOOT_CONSULTA,
            "J4guar",
        )

    @pytest.mark.parametrize("prefixo", comandos.PREFIXOS)
    def test_palavra_do_vocabulario_NAO_vira_consulta_em_nenhum_prefixo(
        self, prefixo
    ):
        """O outro lado da fronteira de D-06.

        Sem isto, um personagem homonimo de comando SOMBREARIA o comando: um
        char chamado "Status" faria `/status` responder estatistica de loot em
        vez de dizer se o scanner esta vigiando.
        """
        conhecidos = frozenset({apelido("status"), apelido("join")})
        assert interpretar_dinamico(prefixo + "status", conhecidos) is None
        assert interpretar_dinamico(prefixo + "join", conhecidos) is None

    def test_a_superficie_dinamica_inteira_na_barra(self):
        """Caso a caso, porque cada ramo tem uma armadilha propria.

        Em especial o cancelamento por palavra reservada em DUAS palavras: foi
        exatamente essa forma que, tratada so com hifen, fez o scanner DESIGNAR
        um personagem inexistente chamado "cancelar" numa tarefa anterior deste
        projeto. A forma de duas palavras nunca e opcional num comando que mexe
        em estado duravel.
        """
        conhecidos = frozenset({apelido("J4guar")})
        assert interpretar_dinamico("/loot-J4guar", conhecidos) == (
            Comando.LOOT_DESIGNAR,
            "J4guar",
        )
        assert interpretar_dinamico("/loot J4guar", conhecidos) == (
            Comando.LOOT_DESIGNAR,
            "J4guar",
        )
        assert interpretar_dinamico("/loot-", conhecidos) == (
            Comando.LOOT_CANCELAR,
            "",
        )
        assert interpretar_dinamico("/loot-cancelar", conhecidos) == (
            Comando.LOOT_CANCELAR,
            "",
        )
        assert interpretar_dinamico("/loot cancelar", conhecidos) == (
            Comando.LOOT_CANCELAR,
            "",
        )
        assert interpretar_dinamico("/corrigir-J4guar", conhecidos) == (
            Comando.LOOT_CORRIGIR,
            "J4guar",
        )
        assert interpretar_dinamico("/corrigir J4guar", conhecidos) == (
            Comando.LOOT_CORRIGIR,
            "J4guar",
        )
        assert interpretar_dinamico("/pegou 18:00 J4guar", conhecidos) == (
            Comando.LOOT_ATRIBUIR,
            "18:00 J4guar",
        )

    def test_o_loot_SOZINHO_continua_sendo_nada_na_barra(self):
        """D-02 do codigo, e o prefixo novo nao pode ter afrouxado isso.

        Comando sem argumento nao pode ser destrutivo: quem digita `/loot` no
        meio de um farm quase sempre esta PERGUNTANDO de quem e a vez.
        """
        assert interpretar_dinamico("/loot", frozenset({apelido("J4guar")})) is None
        assert interpretar("/loot") is None

    @pytest.mark.parametrize("prefixo", comandos.PREFIXOS)
    def test_o_prefixo_solto_antes_da_palavra_vale_nos_DOIS(self, prefixo):
        """Comportamento que ja existia, medido aqui para nao divergir depois.

        `interpretar` junta as DUAS primeiras palavras para aceitar
        `/cancelar silencio`, e o efeito colateral e que o prefixo separado da
        palavra por um espaco tambem casa. Isso vale identico nos dois
        prefixos, e e exatamente o tipo de detalhe que uma segunda copia do
        `startswith` faria divergir sem ninguem notar.
        """
        assert interpretar(prefixo + " join") is Comando.JOIN

    @pytest.mark.parametrize(
        "texto", ["//join", "/./join", "/", ".", "/nao-existe", "/rm -rf"]
    )
    def test_prefixo_duplicado_ou_sozinho_nao_e_comando(self, texto):
        """Um prefixo a mais nao vira comando, e um prefixo so tambem nao.

        `sem_prefixo` devolve string VAZIA para o prefixo sozinho — e um caso
        legitimo que morre adiante por nao casar vocabulario nem nick. Este
        teste e quem garante que "morre adiante" continua verdade.
        """
        assert interpretar(texto) is None, texto
        assert interpretar_dinamico(texto, frozenset({apelido("J4guar")})) is None

    def test_a_forma_antiga_atravessa_o_caminho_REAL_ponta_a_ponta(self):
        """A promessa feita aos party-mates e sobre o caminho INTEIRO.

        Prova so no `interpretar` nao bastaria: o que decide se o comando vira
        acao e `comandos_novos`, com as cinco travas ligadas. E e la, no
        `continue` da autorizacao, que mora o descarte silencioso que motivou
        manter a forma antiga viva.
        """
        achados = comandos_novos(
            [self._mensagem(31, ".join"), self._mensagem(32, ".leave")],
            set(),
            [self.TELEFONE],
        )
        assert [m.comando for m in achados] == [Comando.JOIN, Comando.LEAVE]


class TestComandosDinamicosNasTravas:
    """As travas antigas valem INTEGRALMENTE para os comandos novos.

    `.loot-<nick>` muda estado compartilhado; se um estranho pudesse mandar,
    ele controlaria de quem e a vez do loot da party inteira.
    """

    def test_loot_designar_atravessa_com_argumento(self):
        achados = comandos_novos(
            [msg(1, ".loot-j4guar")], set(), nicks_conhecidos=frozenset()
        )
        assert len(achados) == 1
        assert achados[0].comando is Comando.LOOT_DESIGNAR
        assert achados[0].argumento == "j4guar"

    def test_consulta_atravessa_com_argumento(self):
        achados = comandos_novos(
            [msg(2, ".j4guar")], set(), nicks_conhecidos=frozenset({"j4guar"})
        )
        assert len(achados) == 1
        assert achados[0].comando is Comando.LOOT_CONSULTA
        assert achados[0].argumento == "j4guar"

    def test_nick_desconhecido_morre_em_silencio(self):
        assert comandos_novos([msg(3, ".kaus")], set()) == []

    def test_telefone_nao_autorizado_e_descartado(self):
        """A trava de allowlist vale para o comando novo."""
        meus = ["+5544997077000"]
        de_outro = [msg(4, ".loot-j4guar", autor="Hiago")]
        de_outro[0]["sender"]["phone_number"] = "+48608297919"
        assert comandos_novos(de_outro, set(), meus) == []

    def test_comando_fixo_continua_sem_argumento(self):
        """`.status` com "status" nos nicks conhecidos continua STATUS."""
        achados = comandos_novos(
            [msg(5, ".status")], set(), nicks_conhecidos=frozenset({"status"})
        )
        assert len(achados) == 1
        assert achados[0].comando is Comando.STATUS
        assert achados[0].argumento is None


class TestOQueOScannerSeRecusaAObedecer:
    def test_nunca_obedece_as_proprias_mensagens(self):
        """Um comando ecoado viraria laco infinito."""
        saindo = [msg(1, ".cancelar", tipo=1)]
        assert comandos_novos(saindo, set()) == []

    def test_nunca_obedece_nota_privada_de_agente(self):
        assert comandos_novos([msg(1, ".cancelar", private=True)], set()) == []

    def test_nao_obedece_a_mesma_mensagem_duas_vezes(self):
        mensagens = [msg(42, ".cancelar")]
        primeiro = comandos_novos(mensagens, set())
        assert len(primeiro) == 1

        ja = {chave_da_mensagem(42)}
        assert comandos_novos(mensagens, ja) == []

    def test_mensagem_sem_id_e_descartada(self):
        assert comandos_novos([{"content": ".cancelar", "message_type": 0}], set()) == []

    def test_conversa_de_cliente_nao_dispara_nada(self):
        """O cenario real medido no Chatwoot do usuario."""
        conversa_real = [
            msg(1, "Ola, gostaria de automatizar meu fluxo de trabalho"),
            msg(2, "Quero cancelar"),
            msg(3, "nao"),
            msg(4, "John Snow 31/02/2001"),
        ]
        assert comandos_novos(conversa_real, set()) == []


class TestComandosNovos:
    def test_devolve_o_comando_com_autor(self):
        achados = comandos_novos([msg(7, ".cancelar", autor="Kaus")], set())
        assert len(achados) == 1
        assert achados[0].comando is Comando.CANCELAR_SILENCIO
        assert achados[0].autor == "Kaus"
        assert achados[0].id == 7

    def test_vem_em_ordem_de_id(self):
        fora_de_ordem = [msg(9, ".status"), msg(3, ".cancelar"), msg(5, ".voltar")]
        assert [m.id for m in comandos_novos(fora_de_ordem, set())] == [3, 5, 9]

    def test_mistura_real_so_deixa_passar_o_comando(self):
        lote = [
            msg(1, "Scanner ativo", tipo=1),
            msg(2, "boa noite pessoal"),
            msg(3, ".cancelar", autor="Yazalaque"),
            msg(4, "vou dormir"),
        ]
        achados = comandos_novos(lote, set())
        assert [m.id for m in achados] == [3]


class TestLeitorDeComandos:
    def _leitor(self, conversas=("13",), intervalo=20.0):
        return LeitorDeComandos(
            url="https://exemplo.invalido",
            conta="1",
            token="x",
            conversas=list(conversas),
            segundos_entre_leituras=intervalo,
        )

    def test_sem_conversa_configurada_fica_inativo(self):
        leitor = self._leitor(conversas=())
        assert not leitor.ativo
        assert leitor.ler(0.0) == []

    def test_respeita_a_cadencia(self):
        """A 1 Hz seriam 86 mil requisicoes por dia, por instancia."""
        leitor = self._leitor(intervalo=20.0)
        assert leitor.vencido(0.0)
        leitor.ler(0.0)
        assert not leitor.vencido(5.0)
        assert not leitor.vencido(19.9)
        assert leitor.vencido(20.0)

    def test_falha_de_rede_NAO_derruba_o_scanner(self):
        """Ouvir comando e extra; vigiar a party e o trabalho.

        O host nao existe, entao a chamada falha de verdade — nao ha mock aqui.
        """
        leitor = self._leitor()
        assert leitor.ler(0.0) == []
        assert leitor.falhas == 1

    def test_as_falhas_sao_contadas_para_o_resumo(self):
        leitor = self._leitor(intervalo=0.0)
        for t in range(3):
            leitor.ler(float(t))
        assert leitor.falhas == 3


class TestTelefoneEquivalente:
    """O nono digito brasileiro, e por que comparacao exata falharia.

    O usuario se identifica como +5544997077000. O Chatwoot registra o dono do
    grupo dele como 554497077000 — SEM o 9. Mesma pessoa, duas formas, as duas
    circulando na base do WhatsApp.

    Comparacao exata falharia em SILENCIO: o comando seria ignorado sem erro
    nenhum. Para uma trava de seguranca, esse e o pior modo de falha — parece
    que nao funciona, e ninguem sabe por que.
    """

    def test_o_caso_real_do_usuario(self):
        from l2scanner.comandos import telefone_equivalente

        assert telefone_equivalente("+5544997077000", "554497077000")

    def test_atravessa_formatacao(self):
        from l2scanner.comandos import telefone_equivalente

        for outro in (
            "+55 44 99707-7000",
            "(44) 99707-7000",
            "5544997077000",
            "44997077000",
        ):
            assert telefone_equivalente("+5544997077000", outro), outro

    def test_numero_de_outra_pessoa_nao_casa(self):
        from l2scanner.comandos import telefone_equivalente

        assert not telefone_equivalente("+5544997077000", "+48608297919")

    def test_vazio_nunca_casa(self):
        from l2scanner.comandos import telefone_equivalente

        assert not telefone_equivalente("+5544997077000", "")
        assert not telefone_equivalente(None, "+5544997077000")
        assert not telefone_equivalente(None, None)

    def test_numero_curto_exige_igualdade_completa(self):
        """Sem isso, um sufixo pequeno casaria com meio mundo."""
        from l2scanner.comandos import telefone_equivalente

        assert telefone_equivalente("123", "123")
        assert not telefone_equivalente("123", "456")


class TestSoOMeuNumeroMandaNoScanner:
    def test_com_allowlist_so_o_dono_passa(self):
        meus = ["+5544997077000"]
        do_dono = [msg(1, ".cancelar", autor="Yazalaque")]
        do_dono[0]["sender"]["phone_number"] = "554497077000"  # sem o 9
        assert len(comandos_novos(do_dono, set(), meus)) == 1

    def test_com_allowlist_um_estranho_e_ignorado(self):
        meus = ["+5544997077000"]
        de_outro = [msg(2, ".cancelar", autor="Hiago")]
        de_outro[0]["sender"]["phone_number"] = "+48608297919"
        assert comandos_novos(de_outro, set(), meus) == []

    def test_remetente_sem_telefone_e_ignorado_quando_ha_allowlist(self):
        """Sem numero nao da para afirmar que e voce."""
        assert comandos_novos([msg(3, ".cancelar")], set(), ["+5544997077000"]) == []

    def test_sem_allowlist_qualquer_um_passa(self):
        """Compatibilidade. O aviso de arranque torna isso visivel."""
        assert len(comandos_novos([msg(4, ".cancelar")], set(), [])) == 1

    def test_num_grupo_a_allowlist_de_conversa_nao_bastaria(self):
        """O cenario que motivou a trava.

        Num grupo, permitir a CONVERSA libera todo mundo que escreve nela. Só
        o telefone separa o dono dos outros doze membros.
        """
        meus = ["+5544997077000"]
        grupo = [
            dict(msg(10, ".cancelar", autor="Kaus"), sender={"name": "Kaus", "phone_number": "+5511999998888"}),
            dict(msg(11, ".cancelar", autor="Yazalaque"), sender={"name": "Yazalaque", "phone_number": "+5544997077000"}),
        ]
        achados = comandos_novos(grupo, set(), meus)
        assert [m.id for m in achados] == [11]


class TestEtiquetaComoInterruptor:
    def test_etiqueta_sozinha_ja_deixa_o_leitor_ativo(self):
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://x.invalido", conta="1", token="t",
            conversas=[], etiqueta="scanner",
        )
        assert leitor.ativo

    def test_sem_conversa_e_sem_etiqueta_fica_inativo(self):
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://x.invalido", conta="1", token="t", conversas=[],
        )
        assert not leitor.ativo

    def test_aberto_a_qualquer_um_quando_nao_ha_telefone(self):
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://x.invalido", conta="1", token="t", conversas=["13"],
        )
        assert leitor.aberto_a_qualquer_um

    def test_com_telefone_deixa_de_estar_aberto(self):
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://x.invalido", conta="1", token="t",
            conversas=["13"], telefones=["+5544997077000"],
        )
        assert not leitor.aberto_a_qualquer_um

    def test_falha_ao_listar_etiquetas_ouve_MENOS_nunca_mais(self):
        """Uma falha de rede nao pode abrir canal nenhum."""
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://host.que.nao.existe.invalido", conta="1", token="t",
            conversas=[], etiqueta="scanner", segundos_entre_leituras=0.0,
        )
        assert leitor.ler(0.0) == []
        assert leitor.falhas >= 1


class TestAtenderComandosNaCostura:
    """O crash real de 2026-08-24 22:59, em producao.

        TypeError: '>=' not supported between 'timedelta' and 'float'

    `atender_comandos` recebia UM parametro `agora` e o usava para DOIS
    relogios incompativeis: o `datetime` de parede que a agenda entende, e os
    segundos corridos que o limitador de taxa do leitor entende.

    Os testes existentes nao pegaram porque chamavam `LeitorDeComandos.ler()`
    direto, sempre com float. O erro so existia na COSTURA — e a costura
    (`__main__.py`, 20% de cobertura) e onde TODOS os erros de integracao deste
    projeto moraram: os tres do code review, o `destacar` com um argumento, e
    este.

    Por isso estes testes chamam a funcao do jeito que o LACO chama, com os
    tipos de verdade.
    """

    def _pecas(self, tmp_path):
        from datetime import datetime

        from l2scanner.agenda import EventoAgendado, RegistroEmDisco
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://host.que.nao.existe.invalido",
            conta="1",
            token="t",
            conversas=["1"],
            segundos_entre_leituras=0.0,
        )
        registro = RegistroEmDisco(tmp_path)
        eventos = [
            EventoAgendado(
                nome="Prime",
                horarios=((20, 0),),
                silenciar_minutos=120,
            )
        ]
        return leitor, registro, eventos, datetime(2026, 8, 24, 20, 30)

    def test_chamada_como_o_laco_chama_nao_levanta(self, tmp_path):
        """A reproducao exata do crash."""
        import time

        from l2scanner.__main__ import atender_comandos

        leitor, registro, eventos, agora = self._pecas(tmp_path)
        atender_comandos(leitor, registro, eventos, None, agora, time.monotonic())

    def test_o_relogio_de_parede_e_datetime_e_o_da_cadencia_e_float(self, tmp_path):
        """Trocar os dois de lugar tem que quebrar, e quebrar visivelmente.

        Se um dia alguem 'simplificar' juntando os parametros, este teste diz
        por que eles sao dois.
        """
        import pytest as _pytest

        from l2scanner.__main__ import atender_comandos

        leitor, registro, eventos, agora = self._pecas(tmp_path)
        # A PRIMEIRA chamada passa: `_ultima_leitura` e None e a comparacao nem
        # acontece. O crash de producao so apareceu no SEGUNDO tick — mais um
        # motivo de ter escapado, porque um teste de uma chamada so nao pega.
        atender_comandos(leitor, registro, eventos, None, agora, agora)
        with _pytest.raises(TypeError):
            atender_comandos(leitor, registro, eventos, None, agora, agora)

    def test_leitor_ausente_nao_faz_nada(self, tmp_path):
        import time

        from l2scanner.__main__ import atender_comandos

        _, registro, eventos, agora = self._pecas(tmp_path)
        atender_comandos(None, registro, eventos, None, agora, time.monotonic())

    def test_os_dois_lacos_passam_time_monotonic(self):
        """A trava contra a regressao voltar por um refactor.

        Le a fonte dos dois lacos e exige que a chamada carregue o segundo
        relogio. Foi assim que travamos o `destacar` e a ordem da agenda.
        """
        import inspect
        import re

        from l2scanner import __main__ as principal

        for nome in ("laco_principal", "laco_da_agenda"):
            fonte = inspect.getsource(getattr(principal, nome))
            # Casa ate o fecha-parenteses da PROPRIA chamada. Um `.*?` simples
            # para dentro de `time.monotonic()` e mede o argumento pela metade.
            corpo = fonte[fonte.index("atender_comandos(") :]
            chamada = re.match(r"atender_comandos\((.*?)\n\s*\)", corpo, re.S)
            assert chamada, f"{nome} nao chama atender_comandos"
            assert "time.monotonic()" in chamada.group(1), (
                f"{nome} nao passa o relogio monotonico para a cadencia"
            )


class TestRespondeOndePerguntaram:
    """Medido ao vivo: pergunta as 23:04:42 na conversa 1 (privado), resposta
    as 23:04:52 na conversa 13 (grupo). Funcionou — no lugar errado, e o
    usuario concluiu que nao tinha funcionado.

    O `Despachante` so sabia mandar para os destinos de AVISO. Ninguem
    respondia onde a pergunta chegou.
    """

    def _atender(self, tmp_path, texto, conversa="1"):
        import time
        from datetime import datetime

        from l2scanner.__main__ import atender_comandos
        from l2scanner.agenda import EventoAgendado, RegistroEmDisco
        from l2scanner.notificador import Despachante, NotificadorEmMemoria

        class LeitorFalso:
            ativo = True
            telefones: list[str] = []
            # `atender_comandos` le `membros` do leitor desde o plano 10-03b —
            # e o elo que liga os blocos `[[membro]]` do config.toml ao caminho
            # real. Vazio aqui porque estes testes sao sobre o nivel de DONO.
            membros: list = []

            def ler(self, _):
                return [
                    {
                        "id": 4242,
                        "content": texto,
                        "message_type": 0,
                        "private": False,
                        "sender": {"name": "Yazalaque"},
                        "conversation_id": conversa,
                    }
                ]

        notificador = NotificadorEmMemoria()
        despachante = Despachante(notificador)
        eventos = [
            EventoAgendado(nome="Prime", horarios=((20, 0),), silenciar_minutos=120)
        ]
        atender_comandos(
            LeitorFalso(),
            RegistroEmDisco(tmp_path),
            eventos,
            despachante,
            datetime(2026, 8, 24, 20, 30),
            time.monotonic(),
        )
        despachante.iniciar()
        despachante.encerrar()
        return notificador.destinos

    def test_status_responde_no_privado_e_NAO_no_grupo(self, tmp_path):
        destinos = self._atender(tmp_path, ".status", conversa="1")
        assert destinos, "nao respondeu nada"
        alvos = [alvo for _, alvo in destinos]
        assert alvos == ["1"], (
            f"status deveria responder so na conversa 1; foi para {alvos}"
        )

    def test_cancelar_responde_no_privado_E_avisa_o_grupo(self, tmp_path):
        """Cancelar muda o que o GRUPO recebe — todo mundo tinha parado de ser
        avisado por causa daquele silencio."""
        destinos = self._atender(tmp_path, ".cancelar", conversa="1")
        alvos = [alvo for _, alvo in destinos]
        assert "1" in alvos, "quem pediu nao recebeu confirmacao"
        assert None in alvos, "o grupo nao foi avisado de que o silencio caiu"

    def test_sem_origem_conhecida_cai_no_grupo(self, tmp_path):
        """Compatibilidade: melhor responder em algum lugar do que em nenhum."""
        destinos = self._atender(tmp_path, ".status", conversa=None)
        assert [alvo for _, alvo in destinos] == [None]


class TestLootNaCostura:
    """Os dois comandos de loot pelo caminho que o LACO usa.

    Sem eco no grupo, de proposito: a designacao vai aparecer no aviso de
    antecedencia que ja existe ("Loot: X"), e ecoar agora seria dizer a mesma
    coisa duas vezes. A consulta e pergunta pessoal, mesmo racional do
    `.status`.
    """

    def _atender(self, tmp_path, texto, loot):
        import time
        from datetime import datetime

        from l2scanner.__main__ import atender_comandos
        from l2scanner.agenda import EventoAgendado, RegistroEmDisco
        from l2scanner.notificador import Despachante, NotificadorEmMemoria

        class LeitorFalso:
            ativo = True
            telefones: list[str] = []
            # `atender_comandos` le `membros` do leitor desde o plano 10-03b —
            # e o elo que liga os blocos `[[membro]]` do config.toml ao caminho
            # real. Vazio aqui porque estes testes sao sobre o nivel de DONO.
            membros: list = []

            def ler(self, _):
                return [
                    {
                        "id": 999,
                        "content": texto,
                        "message_type": 0,
                        "private": False,
                        "sender": {"name": "Yazalaque"},
                        "conversation_id": "1",
                    }
                ]

        notificador = NotificadorEmMemoria()
        despachante = Despachante(notificador)
        eventos = [
            EventoAgendado(
                nome="Solo Boss",
                horarios=tuple((h, 0) for h in range(0, 24, 2)),
                avisar_no_horario=False,
            )
        ]
        atender_comandos(
            LeitorFalso(),
            RegistroEmDisco(tmp_path / "agenda"),
            eventos,
            despachante,
            datetime(2026, 8, 25, 9, 5),
            time.monotonic(),
            loot=loot,
        )
        despachante.iniciar()
        despachante.encerrar()
        return notificador.destinos

    def test_designar_responde_so_no_privado_e_grava(self, tmp_path):
        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        destinos = self._atender(tmp_path, ".loot-j4guar", loot)

        assert [alvo for _, alvo in destinos] == ["1"], (
            "a confirmacao tinha que sair SO na conversa de origem"
        )
        assert "J4guar" in destinos[0][0]
        assert loot.designacao() is not None

    def test_consultar_responde_so_no_privado(self, tmp_path):
        from datetime import datetime

        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        loot.registrar("j4guar", datetime(2026, 8, 25, 8, 0))
        destinos = self._atender(tmp_path, ".j4guar", loot)

        assert [alvo for _, alvo in destinos] == ["1"]
        assert "pegou 1 loot" in destinos[0][0]

    def test_sem_registro_de_loot_avisa_que_nao_da(self, tmp_path):
        """Mesmo padrao do _obedecer_modo sem rastreador: responder que nao
        da e melhor que calar — calar parece quebrado."""
        destinos = self._atender(tmp_path, ".loot-j4guar", None)

        # Sem `loot` nao ha nicks conhecidos, mas `.loot-<nick>` nao depende
        # do portao — o comando existe e a resposta explica a limitacao.
        assert destinos, "o comando morreu em silencio"
        assert "Nao consigo mexer no loot agora." in destinos[0][0]

    def test_cancelar_apaga_de_verdade_e_responde_so_no_privado(self, tmp_path):
        """A costura inteira do `.loot-`: parser, dispatch, disco e resposta.

        Sem eco no grupo, mesmo racional do designar: o grupo vai perceber
        pelo proprio aviso de antecedencia, que passa a sair sem "Loot:".
        """
        from datetime import datetime

        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        loot.designar("J4guar", datetime(2026, 8, 25, 10, 0), datetime(2026, 8, 25, 9))

        destinos = self._atender(tmp_path, ".loot-", loot)

        assert loot.designacao() is None, "o comando nao apagou nada"
        assert [alvo for _, alvo in destinos] == ["1"], (
            "a confirmacao tinha que sair SO na conversa de origem"
        )
        assert "J4guar" in destinos[0][0]

    def test_corrigir_atravessa_parser_dispatch_e_disco(self, tmp_path):
        """A costura inteira do `.corrigir-<nick>`: o loot troca de dono.

        Sem eco no grupo: corrigir historico e conserto de contabilidade entre
        quem sabe o que aconteceu, e anunciar que o loot mudou de dono
        convidaria justamente a discussao que o registro existe para encerrar.
        """
        from datetime import datetime

        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        loot.registrar("tiomad", datetime(2026, 8, 25, 8, 0))

        destinos = self._atender(tmp_path, ".corrigir-kaus", loot)

        assert [alvo for _, alvo in destinos] == ["1"], (
            "a confirmacao tinha que sair SO na conversa de origem"
        )
        assert "Kaus" in destinos[0][0]
        assert loot.resumo("kaus")[0] == 1, "a correcao nao chegou no disco"

    def test_pegou_atravessa_parser_dispatch_e_disco(self, tmp_path):
        """A costura inteira do `.pegou <hora> <nick>`: o registro NASCE.

        O helper roda com `agora = 2026-08-25 09:05`, entao o boss das 08:00
        ja passou e a pasta de loot esta vazia — nenhuma designacao, nenhum
        `pegou_*`. E o caso que o usuario relatou: o scanner estava fora do
        ar quando o boss passou, e agora alguem precisa dizer quem pegou.

        Sem eco no grupo, mesmo racional do `.corrigir`: registrar loot de
        boss passado e conserto de contabilidade entre quem ja sabe o que
        aconteceu.
        """
        from datetime import datetime

        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")

        destinos = self._atender(tmp_path, ".pegou 08:00 Korzis", loot)

        assert [alvo for _, alvo in destinos] == ["1"], (
            "a confirmacao tinha que sair SO na conversa de origem"
        )
        assert "Korzis" in destinos[0][0]
        assert loot.resumo("Korzis") == (1, datetime(2026, 8, 25, 8, 0)), (
            "o registro nao nasceu no horario do boss"
        )

    def test_cancelar_sem_nada_marcado_nao_levanta_e_responde(self, tmp_path):
        """O comando nao pode morrer calado: quem mandou merece saber que nao
        havia nada marcado, em vez de ficar na duvida se funcionou."""
        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        destinos = self._atender(tmp_path, ".loot-", loot)

        assert destinos, "o cancelamento morreu em silencio"
        assert "Nao havia loot marcado" in destinos[0][0]

    def test_cancelar_sem_registro_de_loot_avisa_que_nao_da(self, tmp_path):
        destinos = self._atender(tmp_path, ".loot-", None)

        assert destinos, "o comando morreu em silencio"
        assert "Nao consigo mexer no loot agora." in destinos[0][0]


class TestAjudaNaCostura:
    """O `.help` pelo caminho que o LACO usa, e nos DOIS destinos.

    A ajuda nao ganha portao proprio nem etiqueta nova: ela atravessa as cinco
    travas que todo comando ja atravessa. E ela nao e moldurada em lugar
    nenhum — nem no celular nem no console —, porque `moldurar` casa a largura
    da borda com a linha mais longa e o texto tem dezenove linhas.
    """

    TELEFONE = "+5544997077000"

    def _atender(self, tmp_path, texto, conversa="1", telefones=(), do_numero=None):
        import time
        from datetime import datetime

        from l2scanner.__main__ import atender_comandos
        from l2scanner.agenda import EventoAgendado, RegistroEmDisco
        from l2scanner.notificador import Despachante, NotificadorEmMemoria

        remetente = {"name": "Yazalaque"}
        if do_numero:
            remetente["phone_number"] = do_numero

        class LeitorFalso:
            ativo = True
            telefones: list[str] = []
            # `atender_comandos` le `membros` do leitor desde o plano 10-03b —
            # e o elo que liga os blocos `[[membro]]` do config.toml ao caminho
            # real. Vazio aqui porque estes testes sao sobre o nivel de DONO.
            membros: list = []

            def ler(self, _):
                return [
                    {
                        "id": 5150,
                        "content": texto,
                        "message_type": 0,
                        "private": False,
                        "sender": remetente,
                        "conversation_id": conversa,
                    }
                ]

        leitor = LeitorFalso()
        leitor.telefones = list(telefones)

        notificador = NotificadorEmMemoria()
        despachante = Despachante(notificador)
        eventos = [
            EventoAgendado(nome="Prime", horarios=((20, 0),), silenciar_minutos=120)
        ]
        atender_comandos(
            leitor,
            RegistroEmDisco(tmp_path),
            eventos,
            despachante,
            datetime(2026, 8, 25, 20, 30),
            time.monotonic(),
        )
        despachante.iniciar()
        despachante.encerrar()
        return notificador.destinos

    def test_responde_SO_na_conversa_de_origem(self, tmp_path):
        """Pergunta pessoal, mesmo racional ja escrito no ramo do `.status`.

        Ecoar a lista inteira no grupo seria ruido para quem nao perguntou.
        """
        destinos = self._atender(tmp_path, ".help")
        assert destinos, "nao respondeu nada"
        assert [alvo for _, alvo in destinos] == ["1"], (
            "a ajuda vazou para o grupo"
        )

    def test_o_que_e_despachado_e_a_tabela_INTEIRA(self, tmp_path):
        """A costura entrega o produto de `texto_de_ajuda()`, nao um resumo."""
        (despachado, _), = self._atender(tmp_path, ".help")
        for comando, linha in _AJUDA.items():
            assert linha.sintaxe in despachado, (
                f"{comando.name} nao chegou no WhatsApp"
            )

    def test_a_ajuda_chega_no_celular_SEM_moldura(self, tmp_path):
        """D-04: dezenove linhas dentro de uma moldura quebram feio na tela."""
        (despachado, _), = self._atender(tmp_path, ".help")
        assert not _tem_borda(despachado), (
            f"a ajuda saiu moldurada no WhatsApp:\n{despachado}"
        )

    def test_a_ajuda_no_LOG_tambem_sai_sem_moldura(self, tmp_path, caplog):
        """O segundo destino, e o que estava DEFEITUOSO.

        `atender_comandos` registrava `destacar(resposta)`, e `destacar` chama
        `moldurar`, cuja largura e `max(LARGURA, len(miolo) + len(carimbo))`
        sobre a string INTEIRA — com as quebras de linha dentro. Uma resposta
        de varias linhas saia no console e no `scanner.log` com uma borda de
        centenas de asteriscos.
        """
        with caplog.at_level(logging.INFO, logger="l2scanner"):
            self._atender(tmp_path, ".help")
        registrado = "\n".join(r.getMessage() for r in caplog.records)
        # A canaria e DERIVADA da tabela: ela afirma a sintaxe OFICIAL, e um
        # literal aqui envelheceria junto com o prefixo (foi o que aconteceu
        # quando o oficial virou a barra). O comando ENVIADO continua na forma
        # antiga de proposito — e cobertura do legado ponta-a-ponta.
        assert _AJUDA[Comando.STATUS].sintaxe in registrado, (
            "a resposta nem chegou no log"
        )
        assert not _tem_borda(registrado), (
            f"a ajuda saiu moldurada no console:\n{registrado}"
        )

    def test_telefone_FORA_da_allowlist_e_ignorado(self, tmp_path):
        """D-07: a ajuda nao tem portao proprio — usa os cinco que ja existem.

        A lista de comandos e um mapa da superficie de ataque; quem nao passa
        na allowlist nunca a recebe, exatamente como em qualquer outro comando.
        """
        destinos = self._atender(
            tmp_path,
            ".help",
            telefones=[self.TELEFONE],
            do_numero="+48608297919",
        )
        assert destinos == [], "um estranho recebeu a lista de comandos"

    def test_o_dono_na_allowlist_continua_recebendo(self, tmp_path):
        """O contraponto do teste acima: a trava trava o estranho, nao todos."""
        destinos = self._atender(
            tmp_path,
            ".help",
            telefones=[self.TELEFONE],
            do_numero="554497077000",  # o mesmo numero, sem o nono digito
        )
        assert [alvo for _, alvo in destinos] == ["1"]


class TestFronteiraDeAutorizacao:
    """Os dois niveis, provados nos DOIS sentidos.

    Antes desta fase a autorizacao era global e binaria: um telefone na
    allowlist podia TUDO, inclusive `.corrigir` e `.pegou`, que reescrevem a
    estatistica do `.loot/` — pasta que nunca e podada e nao tem backup. Por os
    telefones dos quatro a oito party-mates naquela lista, so para que
    pudessem dar `.join`, teria dado a todos eles esse poder.

    Entao a fronteira precisa de prova nas duas direcoes: o que o membro
    ALCANCA e, muito mais importante, o que ele NAO alcanca. E a segunda
    metade e DERIVADA do enum, nao digitada — ver os dois tripwires abaixo.
    """

    # O telefone de dono e o mesmo que os testes existentes ja usam.
    DONO = "+5544997077000"
    # O de membro NAO pode colidir com o de dono nos 8 digitos finais, que sao
    # os unicos comparados: 97077000 contra 12345678.
    MEMBRO = "+5544912345678"
    NICK = "Korzis"

    MEMBROS = (Membro(nick="Korzis", telefone="+5544912345678"),)
    # Um nick conhecido para os comandos dinamicos poderem ser interpretados.
    CONHECIDOS = frozenset({apelido("J4guar")})

    def _de(self, telefone: str | None, texto: str, id_: int = 9001) -> dict:
        remetente: dict = {"name": "Ze do Zap"}
        if telefone is not None:
            remetente["phone_number"] = telefone
        return {
            "id": id_,
            "content": texto,
            "message_type": 0,
            "private": False,
            "sender": remetente,
        }

    def _sintaxe(self, comando: Comando) -> str:
        """A sintaxe que a PROPRIA ajuda anuncia para o comando.

        Sai da tabela `_AJUDA` e nao de um literal aqui: assim a prova usa
        exatamente o que o bot ensina, e nao uma segunda opiniao do teste.

        O `<apelido>` entrou junto com o `/batizar`. Sem ele a sintaxe montada
        aqui seria `/batizar <apelido> J4guar`, que o parser recusa por
        charset: o teste da fronteira continuaria VERDE afirmando que o
        party-mate nao alcanca o comando, quando na verdade ninguem alcancaria
        — uma prova vazia com cara de fronteira.
        """
        return (
            _AJUDA[comando]
            .sintaxe.replace("<nick>", "J4guar")
            .replace("<hora>", "18:00")
            .replace("<apelido>", _APELIDO_DE_EXEMPLO)
        )

    def _achados(self, telefone: str | None, comando: Comando, **extra):
        return comandos_novos(
            [self._de(telefone, self._sintaxe(comando))],
            set(),
            extra.pop("telefones", [self.DONO]),
            nicks_conhecidos=self.CONHECIDOS,
            membros=extra.pop("membros", self.MEMBROS),
        )

    def test_o_membro_e_RECUSADO_em_tudo_que_nao_e_dele(self):
        """O TRIPWIRE DA FRONTEIRA. A lista de recusa e DERIVADA do enum.

        `set(Comando) - COMANDOS_DE_MEMBRO`, nunca digitada. Escrita a mao,
        o proximo comando destrutivo do projeto nasceria alcancavel por
        qualquer party-mate e o teste continuaria verde — ninguem descobriria
        ate alguem apagar a estatistica de um boss pelo WhatsApp.

        Derivada, um `Comando` novo entra nesta prova sozinho e so sai dela
        quando alguem decidir, por escrito, que ele e de membro.
        """
        recusados = set(Comando) - COMANDOS_DE_MEMBRO
        # Guarda contra a prova VAZIA: se alguem alargar COMANDOS_DE_MEMBRO ate
        # engolir o enum, o laco abaixo nao roda e o teste passa sem provar
        # nada. Os dois comandos nomeados aqui sao os que reescrevem historico.
        assert {Comando.LOOT_CORRIGIR, Comando.LOOT_ATRIBUIR} <= recusados, (
            "COMANDOS_DE_MEMBRO cresceu ate alcancar comando que reescreve a "
            "estatistica permanente do .loot/ — isso nunca pode ser de membro"
        )

        for comando in sorted(recusados, key=lambda c: c.name):
            achados = self._achados(self.MEMBRO, comando)
            assert achados == [], (
                f"um telefone que so esta em [[membro]] alcancou "
                f"{comando.name} pela sintaxe {self._sintaxe(comando)!r} — a "
                f"fronteira vazou"
            )

    def test_o_party_mate_NAO_cala_o_boss_da_party_inteira(self):
        """A fronteira dita por extenso para o par que nasceu agora.

        O teste derivado logo acima ja recusa os dois — ele recusa tudo que
        nao esta em `COMANDOS_DE_MEMBRO`. Esta prova existe porque a razao
        deste par ficar de fora e DIFERENTE da dos outros, e uma razao que so
        vive num comentario nao sobrevive ao proximo ajuste.

        `/entrar` mexe numa linha da lista de UMA ocorrencia, e quem digitou ve
        o efeito. `/desativarsoloboss` apaga 12 chamadas por dia da party
        INTEIRA, por tempo indeterminado, e o efeito dele e a AUSENCIA de
        mensagem — do lado dos outros quatro a oito party-mates, calar o bot e
        indistinguivel do bot ter caido. Nao e um `/entrar` maior; e outra
        categoria de estrago.
        """
        assert Comando.DESATIVAR_SOLO_BOSS not in COMANDOS_DE_MEMBRO
        assert Comando.ATIVAR_SOLO_BOSS not in COMANDOS_DE_MEMBRO
        for comando in (Comando.DESATIVAR_SOLO_BOSS, Comando.ATIVAR_SOLO_BOSS):
            assert self._achados(self.MEMBRO, comando) == [], (
                f"um telefone de [[membro]] alcancou {comando.name}"
            )

    def test_o_membro_ALCANCA_o_que_e_dele_e_chega_com_o_nick(self):
        for comando in sorted(COMANDOS_DE_MEMBRO, key=lambda c: c.name):
            achados = self._achados(self.MEMBRO, comando)
            assert [m.comando for m in achados] == [comando], (
                f"o telefone de membro nao alcancou {comando.name} pela "
                f"sintaxe {self._sintaxe(comando)!r}"
            )
            assert achados[0].nick == self.NICK, (
                "o nick tem que vir do mapa [[membro]], nunca do sender.name"
            )

    def test_o_DONO_continua_alcancando_TODO_comando(self):
        """A aditividade, dita por extenso.

        `test_toda_sintaxe_anunciada_volta_como_o_comando_certo` ja prova isto
        rodando a tabela de ajuda inteira, mas prova sem `membros` configurado.
        Este roda a mesma tabela COM o segundo nivel ligado: o dono nao pode
        perder nada por causa de gente que foi ACRESCENTADA depois dele.
        """
        for comando in sorted(Comando, key=lambda c: c.name):
            achados = self._achados(self.DONO, comando)
            assert [m.comando for m in achados] == [comando], (
                f"o telefone de dono deixou de alcancar {comando.name} depois "
                f"que o nivel de membro passou a existir — o nivel novo e "
                f"ADITIVO, nunca exclusivo"
            )

    def test_o_dono_que_nao_e_membro_chega_sem_nick(self):
        """None, e nao um nick inventado do `sender.name`.

        Quem consome decide o que fazer com isso; o que nao pode acontecer e o
        nome do contato do WhatsApp virar nick de personagem por omissao.
        """
        achados = self._achados(self.DONO, Comando.JOIN)
        assert achados[0].nick is None

    def test_allowlist_VAZIA_continua_aceitando_qualquer_um(self):
        """Compatibilidade: quem configurou comandos so por conversa.

        O nivel de membro nao pode ter FECHADO nada que estava aberto. Quem
        nunca preencheu CHATWOOT_TELEFONES_COMANDO continua exatamente como
        estava — e o aviso de arranque continua sendo quem torna isso visivel.
        """
        for comando in sorted(Comando, key=lambda c: c.name):
            achados = comandos_novos(
                [self._de("+5511900000000", self._sintaxe(comando))],
                set(),
                [],
                nicks_conhecidos=self.CONHECIDOS,
                membros=self.MEMBROS,
            )
            assert [m.comando for m in achados] == [comando], comando.name

    def test_telefone_de_lugar_nenhum_nao_alcanca_nada(self):
        """Nem dono, nem membro, com a allowlist preenchida: zero comandos.

        E o Joao Pedro do "Quero cancelar": um cliente real numa das 22
        conversas da conta, que nao pode virar operador do scanner.
        """
        for comando in sorted(Comando, key=lambda c: c.name):
            assert self._achados("+5511988887777", comando) == [], comando.name

    def test_remetente_SEM_telefone_e_recusado(self):
        """A API nem sempre traz `phone_number`. Ausencia nunca e permissao."""
        for comando in sorted(Comando, key=lambda c: c.name):
            assert self._achados(None, comando) == [], comando.name

    def test_o_nono_digito_nao_transforma_a_pessoa_em_outra(self):
        """A base do WhatsApp carrega as duas formas do mesmo numero.

        Medido nesta conta: o usuario se identifica como +5544997077000 e o
        Chatwoot registra o dono do grupo como 554497077000, sem o 9. Se o
        nivel de membro comparasse exato, o `.join` sumiria em silencio — o
        pior modo de falha possivel, porque quem digitou nao recebe erro
        nenhum e conclui que o bot esta quebrado.
        """
        membros = (Membro(nick="Kaus", telefone="+5544997077001"),)
        achados = comandos_novos(
            [self._de("554497077001", ".join")],
            set(),
            [self.DONO],
            membros=membros,
        )
        assert [m.comando for m in achados] == [Comando.JOIN]
        assert achados[0].nick == "Kaus"

    def test_o_ECO_DO_BOT_nao_vira_comando(self):
        """TRAVA 3 contra a fase que faz o bot ESCREVER no grupo.

        Ate agora o bot so falava sobre mortes e horarios. Desta fase em
        diante ele passa a escrever confirmacoes que se parecem com comandos,
        e um eco obedecido viraria laco infinito. O controle logo abaixo prova
        que a recusa vem do `message_type`, e nao de o texto ser inerte.
        """
        eco = self._de(self.DONO, ".join")
        eco["message_type"] = 1  # outgoing: o proprio bot
        assert comandos_novos([eco], set(), [self.DONO], membros=self.MEMBROS) == []

        entrando = self._de(self.DONO, ".join")
        assert len(
            comandos_novos([entrando], set(), [self.DONO], membros=self.MEMBROS)
        ) == 1, "o controle falhou: o texto sozinho ja nao era comando"

    def test_a_redacao_da_confirmacao_de_grupo_e_inerte(self):
        """E inerte por DUAS razoes independentes, e as duas valem.

        Como saida do bot, a TRAVA 3 a recusa. Como entrada, a TRAVA 2 a
        recusa de novo: `interpretar` so olha a PRIMEIRA palavra, e a
        confirmacao comeca pelo nick. Nenhuma das duas depende da outra.
        """
        texto = "Korzis entrou na lista do Solo Boss das 20:00. Mande .join tambem."

        saindo = self._de(self.DONO, texto)
        saindo["message_type"] = 1
        assert comandos_novos([saindo], set(), [self.DONO], membros=self.MEMBROS) == []

        voltando = self._de(self.DONO, texto)
        assert comandos_novos([voltando], set(), [self.DONO], membros=self.MEMBROS) == []


class TestMembroNoConfigToml:
    """O `[[membro]]` sai de um arquivo TOML e chega na decisao de autorizacao.

    A fatia vertical inteira, ponta a ponta: bloco no arquivo -> `ler_membros`
    -> `comandos_novos`. Sem isto provado de uma ponta a outra, cada metade
    poderia estar certa sozinha e a costura errada — que e onde os erros deste
    projeto moram.
    """

    TELEFONE_DE_MEMBRO = "+5544912345678"

    def _arquivo(self, tmp_path, texto: str):
        caminho = tmp_path / "config.toml"
        caminho.write_text(texto, encoding="utf-8")
        return caminho

    def test_arquivo_ausente_nao_e_erro(self, tmp_path):
        """Quem nunca declarou membro nenhum continua subindo o scanner."""
        assert ler_membros(tmp_path / "nao-existe.toml") == []

    def test_dois_blocos_viram_dois_membros_na_ordem_do_arquivo(self, tmp_path):
        caminho = self._arquivo(
            tmp_path,
            '[[membro]]\nnick = "Korzis"\ntelefone = "+5544911112222"\n\n'
            '[[membro]]\nnick = "J4guar"\ntelefone = "+5544933334444"\n',
        )
        membros = ler_membros(caminho)
        assert [m.nick for m in membros] == ["Korzis", "J4guar"]
        assert membros[0].telefone == "+5544911112222"

    def test_membro_sem_telefone_derruba_no_arranque_citando_o_nick(self, tmp_path):
        """A mensagem cita o NICK, nunca o indice do bloco.

        Um telefone faltando nao produz erro nenhum no meio do farm — produz
        um `.join` que some em silencio. Por isso o erro tem que ser de
        ARRANQUE, com o usuario olhando para o console.
        """
        caminho = self._arquivo(tmp_path, '[[membro]]\nnick = "Korzis"\n')
        with pytest.raises(AgendaInvalida) as erro:
            ler_membros(caminho)
        assert "Korzis" in str(erro.value)

    def test_nick_fora_do_charset_do_jogo_e_recusado(self, tmp_path):
        """Mesmo `NICK_VALIDO` do `loot.py`: um charset so para os dois lados.

        Um nick aceito aqui e recusado no `.loot-<nick>` faria o registro de
        presenca e o de loot falarem de pessoas diferentes.
        """
        caminho = self._arquivo(
            tmp_path,
            '[[membro]]\nnick = "Tio Mad"\ntelefone = "+5544911112222"\n',
        )
        with pytest.raises(AgendaInvalida):
            ler_membros(caminho)

    def test_membro_que_nao_e_bloco_diz_QUAL_ARQUIVO_esta_errado(self, tmp_path):
        """WR-04: `membro = "Kaus"` no lugar de `[[membro]]`.

        E o erro exato que um nao-desenvolvedor comete, e ele produzia
        `AttributeError: 'str' object has no attribute 'get'` — um traceback
        que nao diz uma palavra sobre o config.toml, o oposto do contrato
        escrito na docstring de `ler_membros`.
        """
        caminho = self._arquivo(tmp_path, 'membro = "isto nao e uma lista"\n')
        with pytest.raises(AgendaInvalida) as erro:
            ler_membros(caminho)
        assert "[[membro]]" in str(erro.value)

    def test_lista_de_valores_crus_tambem_e_erro_de_config_e_nao_AttributeError(
        self, tmp_path
    ):
        caminho = self._arquivo(tmp_path, "membro = [1, 2]\n")
        with pytest.raises(AgendaInvalida) as erro:
            ler_membros(caminho)
        assert "[[membro]] #1" in str(erro.value)

    def test_dois_membros_com_o_mesmo_nick_sao_recusados(self, tmp_path):
        """WR-05: dois blocos com o mesmo nick dividem a MESMA vaga em disco.

        A lista e indexada por `apelido(nick)`: o segundo a mandar `.join`
        receberia "voce ja esta na lista" sem nunca ter entrado, e o `.leave`
        de um tiraria o outro.
        """
        caminho = self._arquivo(
            tmp_path,
            '[[membro]]\nnick = "Kaus"\ntelefone = "+5544999998888"\n\n'
            '[[membro]]\nnick = "Kaus"\ntelefone = "+5544977776666"\n',
        )
        with pytest.raises(AgendaInvalida) as erro:
            ler_membros(caminho)
        assert "Kaus" in str(erro.value)

    def test_a_colisao_de_nick_e_pelo_SLUG_e_nao_pelo_texto(self, tmp_path):
        """`Kaus` e `kaus` sao dois blocos no TOML e um arquivo so em disco."""
        caminho = self._arquivo(
            tmp_path,
            '[[membro]]\nnick = "Kaus"\ntelefone = "+5544999998888"\n\n'
            '[[membro]]\nnick = "kaus"\ntelefone = "+5544977776666"\n',
        )
        with pytest.raises(AgendaInvalida):
            ler_membros(caminho)

    def test_telefone_mais_curto_que_o_corte_de_comparacao_e_recusado(self, tmp_path):
        """CR-01: um numero mais curto que os 8 digitos comparados casa demais."""
        caminho = self._arquivo(
            tmp_path, '[[membro]]\nnick = "Kaus"\ntelefone = "8888"\n'
        )
        with pytest.raises(AgendaInvalida) as erro:
            ler_membros(caminho)
        assert "Kaus" in str(erro.value)

    def test_o_config_toml_do_REPOSITORIO_nao_carrega_telefone_de_ninguem(self):
        """O arquivo versionado leva so exemplo COMENTADO.

        Telefone de party-mate nao e segredo, mas tambem nao e do repositorio:
        quem preenche e o usuario, na maquina dele.
        """
        raiz = Path(__file__).resolve().parent.parent
        assert ler_membros(raiz / "config.toml") == []

    def _do_membro(self, id_, texto: str) -> dict:
        return {
            "id": id_,
            "content": texto,
            "message_type": 0,
            "private": False,
            # O `name` e propositalmente DIFERENTE do nick configurado: e assim
            # que se ve se o nick veio do mapa ou do WhatsApp.
            "sender": {"name": "Ze do Zap", "phone_number": self.TELEFONE_DE_MEMBRO},
        }

    def test_o_telefone_do_arquivo_atravessa_o_join(self, tmp_path):
        caminho = self._arquivo(
            tmp_path,
            f'[[membro]]\nnick = "Korzis"\ntelefone = "{self.TELEFONE_DE_MEMBRO}"\n',
        )
        achados = comandos_novos(
            [self._do_membro(1, ".join")],
            set(),
            ["+5544997077000"],
            membros=ler_membros(caminho),
        )
        assert [m.comando for m in achados] == [Comando.JOIN]
        assert achados[0].nick == "Korzis", (
            "o nick tem que sair do mapa [[membro]], nunca do sender.name"
        )

    def test_o_mesmo_telefone_PARA_no_corrigir(self, tmp_path):
        """O ponto inteiro da fase: presenca nao da comando destrutivo."""
        caminho = self._arquivo(
            tmp_path,
            f'[[membro]]\nnick = "Korzis"\ntelefone = "{self.TELEFONE_DE_MEMBRO}"\n',
        )
        assert (
            comandos_novos(
                [self._do_membro(2, ".corrigir-Kaus")],
                set(),
                ["+5544997077000"],
                nicks_conhecidos=frozenset({apelido("Kaus")}),
                membros=ler_membros(caminho),
            )
            == []
        )

    def test_telefone_desconhecido_nao_alcanca_nem_o_join(self, tmp_path):
        caminho = self._arquivo(
            tmp_path,
            f'[[membro]]\nnick = "Korzis"\ntelefone = "{self.TELEFONE_DE_MEMBRO}"\n',
        )
        de_fora = {
            "id": 3,
            "content": ".join",
            "message_type": 0,
            "private": False,
            "sender": {"name": "Joao Pedro", "phone_number": "+5511988887777"},
        }
        assert (
            comandos_novos(
                [de_fora], set(), ["+5544997077000"], membros=ler_membros(caminho)
            )
            == []
        )


class TestMembrosNoArquivoLocal:
    """Os telefones saem do arquivo versionado e vao para o `config.local.toml`.

    Por que nao foi so por o `config.toml` no .gitignore: o
    `TestAgendaRealDoUsuario` le o arquivo DO REPOSITORIO para afirmar os
    horarios de TvT, Prime e Solo Boss. Fora do git, aquele guarda passaria a
    vigiar um exemplo que ninguem edita — continuaria verde e pararia de
    guardar, que e pior do que nao existir, porque parece protecao.

    A saida e um SEGUNDO arquivo, ignorado pelo git, carregando so os
    `[[membro]]`. A agenda e do PROJETO e fica versionada; telefone de
    party-mate e da MAQUINA e nao fica — e telefone de OUTRA PESSOA, e o que
    entra em historico de git nao sai mais nem apagando depois.
    """

    KORZIS = '[[membro]]\nnick = "Korzis"\ntelefone = "+5544911112222"\n'
    J4GUAR = '[[membro]]\nnick = "J4guar"\ntelefone = "+5544933334444"\n'

    def _arquivos(self, tmp_path, versionado: str | None, local: str | None):
        """Escreve so o que foi pedido: `None` significa arquivo AUSENTE.

        Os quatro estados desta classe sao exatamente as quatro combinacoes de
        presenca dos dois arquivos, e cada uma precisa de resposta definida —
        inclusive a de nenhum dos dois, que e a maquina recem-clonada.
        """
        caminho = tmp_path / "config.toml"
        caminho_local = tmp_path / "config.local.toml"
        if versionado is not None:
            caminho.write_text(versionado, encoding="utf-8")
        if local is not None:
            caminho_local.write_text(local, encoding="utf-8")
        return caminho, caminho_local

    def test_so_o_versionado_le_do_versionado(self, tmp_path):
        """Quem nunca criou o arquivo local ve o comportamento de sempre."""
        caminho, caminho_local = self._arquivos(tmp_path, self.KORZIS, None)
        assert [m.nick for m in ler_membros(caminho, caminho_local)] == ["Korzis"]

    def test_so_o_local_le_do_local(self, tmp_path):
        """O caso normal depois desta mudanca: os telefones so moram la."""
        caminho, caminho_local = self._arquivos(tmp_path, None, self.J4GUAR)
        membros = ler_membros(caminho, caminho_local)
        assert [m.nick for m in membros] == ["J4guar"]
        assert membros[0].telefone == "+5544933334444"

    def test_os_dois_o_local_vence_e_NAO_soma(self, tmp_path):
        """Um ou outro, nunca a soma.

        Somar faria um nick apagado do `config.toml` reaparecer pelo local sem
        ninguem entender por que, e poria a validacao de nick repetido para
        decidir qual dos dois arquivos ganha — decisao que nao tem resposta
        obvia e que ninguem quer descobrir as 2h da manha.
        """
        caminho, caminho_local = self._arquivos(tmp_path, self.KORZIS, self.J4GUAR)
        assert [m.nick for m in ler_membros(caminho, caminho_local)] == ["J4guar"]

    def test_os_dois_o_arranque_AVISA_nomeando_os_dois_arquivos(self, tmp_path, caplog):
        """Um bloco que nao faz nada e invisivel; sem aviso, e uma armadilha.

        O usuario que editou o `config.toml` e nao viu efeito nenhum precisa
        ler no console qual arquivo venceu — senao ele reedita o mesmo bloco
        morto a noite inteira.
        """
        caminho, caminho_local = self._arquivos(tmp_path, self.KORZIS, self.J4GUAR)
        with caplog.at_level(logging.WARNING, logger="l2scanner"):
            ler_membros(caminho, caminho_local)
        assert "config.toml" in caplog.text, "o arquivo ignorado nao foi nomeado"
        assert "config.local.toml" in caplog.text, "o vencedor nao foi nomeado"
        assert any(r.levelno >= logging.WARNING for r in caplog.records), (
            "o aviso saiu baixo demais para alguem notar no arranque"
        )

    def test_nenhum_dos_dois_e_lista_vazia_sem_excecao(self, tmp_path):
        """Maquina recem-clonada sobe o scanner igual sempre subiu."""
        caminho, caminho_local = self._arquivos(tmp_path, None, None)
        assert ler_membros(caminho, caminho_local) == []

    def test_so_o_versionado_NAO_avisa(self, tmp_path, caplog):
        """Aviso sem conflito e aviso que se aprende a ignorar — e no dia em
        que houver conflito de verdade ninguem le."""
        caminho, caminho_local = self._arquivos(tmp_path, self.KORZIS, None)
        with caplog.at_level(logging.WARNING, logger="l2scanner"):
            ler_membros(caminho, caminho_local)
        assert caplog.text == ""

    def test_a_validacao_vale_igual_vinda_do_local(self, tmp_path):
        """A regra e escrita UMA vez: nick repetido derruba venha de onde vier.

        Um segundo caminho de leitura com validacao propria e como a regra
        morre: ela continua no arquivo antigo e some no novo, que e justamente
        o que todo mundo passa a usar.
        """
        caminho, caminho_local = self._arquivos(
            tmp_path,
            None,
            '[[membro]]\nnick = "Kaus"\ntelefone = "+5544911112222"\n'
            '[[membro]]\nnick = "kaus"\ntelefone = "+5544933334444"\n',
        )
        with pytest.raises(AgendaInvalida) as erro:
            ler_membros(caminho, caminho_local)
        assert "Kaus" in str(erro.value)

    def test_telefone_curto_no_local_tambem_derruba_no_arranque(self, tmp_path):
        caminho, caminho_local = self._arquivos(
            tmp_path, None, '[[membro]]\nnick = "Kaus"\ntelefone = "8888"\n'
        )
        with pytest.raises(AgendaInvalida) as erro:
            ler_membros(caminho, caminho_local)
        assert "Kaus" in str(erro.value)

    def test_o_caminho_local_PADRAO_e_o_que_o_arranque_usa(self, tmp_path, monkeypatch):
        """A ligacao que o `__main__` de fato exercita: `ler_membros()` pelado.

        Sem este teste a precedencia poderia estar inteira e correta na forma
        com argumento e MORTA em producao, que chama a funcao sem nenhum.
        """
        caminho, caminho_local = self._arquivos(tmp_path, self.KORZIS, self.J4GUAR)
        monkeypatch.setattr(config, "ARQUIVO_CONFIG", caminho)
        monkeypatch.setattr(config, "ARQUIVO_CONFIG_LOCAL", caminho_local)
        assert [m.nick for m in ler_membros()] == ["J4guar"]

    def test_um_caminho_explicito_sozinho_le_SO_aquele_arquivo(self, tmp_path):
        """Passar um caminho e pedir aquele arquivo, nao a vizinhanca dele.

        E disso que depende o
        `test_o_config_toml_do_REPOSITORIO_nao_carrega_telefone_de_ninguem`:
        ele afirma que o arquivo VERSIONADO nao leva telefone. Se um caminho
        explicito arrastasse junto o `config.local.toml` ao lado, aquele guarda
        passaria a ler a maquina de quem roda o teste — e acusaria o arquivo
        errado, ou ficaria verde por acidente.
        """
        caminho, _ = self._arquivos(tmp_path, self.KORZIS, self.J4GUAR)
        assert [m.nick for m in ler_membros(caminho)] == ["Korzis"]

    def test_o_EXEMPLO_do_repositorio_tambem_nao_carrega_telefone_de_ninguem(self):
        """O modelo versionado e o novo lugar onde um telefone pode vazar.

        O `config.local.exemplo.toml` existe para ser COPIADO. Ele e rastreado
        pelo git, e um dedo errado que salve o modelo no lugar da copia poe o
        numero de um party-mate no repositorio pela porta que acabou de ser
        fechada — com o agravante de que ninguem vai olhar de novo para um
        arquivo chamado "exemplo".

        Mesmo guarda que o `test_o_config_toml_do_REPOSITORIO_...` faz do outro
        lado, no arquivo que agora nao deve mais receber `[[membro]]` nenhum.
        """
        raiz = Path(__file__).resolve().parent.parent
        modelo = raiz / "config.local.exemplo.toml"
        assert modelo.exists(), (
            "o modelo sumiu — sem ele o README manda copiar um arquivo que nao "
            "existe, e o usuario escreve os telefones no config.toml de novo"
        )
        assert ler_membros(modelo) == []


class TestColisaoDeTelefone:
    """A colisao de 8 digitos deixa de ser invisivel.

    O comentario do `DIGITOS_FINAIS_DO_TELEFONE` aceitou a colisao por escrito,
    e aceitou para um tamanho: "numa allowlist de duas a cinco pessoas isso e
    aceitavel". O `[[membro]]` acrescenta de quatro a oito telefones a mesma
    superficie, e o par dono-contra-membro e uma escalada de privilegio que
    acontece EM SILENCIO — `autorizado_para` pergunta pelo nivel de dono
    primeiro, e aquele party-mate passa a alcancar `.corrigir` e `.pegou`.
    """

    def test_dono_contra_membro_e_o_par_perigoso(self):
        pares = colisoes_de_telefone(
            ["+5544997077000"],
            (Membro(nick="Korzis", telefone="+5511997077000"),),
        )
        assert pares == [
            ("+5544997077000", "+5511997077000", ORIGEM_DONO, ORIGEM_MEMBRO)
        ], (
            "DDDs diferentes com os mesmos 8 digitos finais: e exatamente o "
            "caso em que o membro herda o poder do dono sem ninguem ver"
        )
        assert pares[0].escala_privilegio is True

    def test_membro_contra_membro_tambem_aparece(self):
        """Nao escala privilegio, mas credita o `.join` de um ao nick do outro."""
        pares = colisoes_de_telefone(
            [],
            (
                Membro(nick="Korzis", telefone="+5544912345678"),
                Membro(nick="J4guar", telefone="+5511912345678"),
            ),
        )
        assert pares == [
            ("+5544912345678", "+5511912345678", ORIGEM_MEMBRO, ORIGEM_MEMBRO)
        ]
        assert pares[0].escala_privilegio is False

    def test_dono_contra_dono_tambem_aparece(self):
        pares = colisoes_de_telefone(["+5544912345678", "+5511912345678"])
        assert pares == [
            ("+5544912345678", "+5511912345678", ORIGEM_DONO, ORIGEM_DONO)
        ]
        assert pares[0].escala_privilegio is False

    def test_o_nono_digito_NAO_e_colisao(self):
        """E a mesma pessoa escrita de dois jeitos — redundancia, nao ambiguidade.

        A base do WhatsApp carrega as duas formas do mesmo numero, entao esta e
        a configuracao mais provavel do mundo. Gritar aqui treinaria o usuario
        a ignorar o aviso, que e o unico jeito de estragar um aviso.
        """
        assert colisoes_de_telefone(["+5544997077000", "554497077000"]) == []
        assert (
            colisoes_de_telefone(
                ["+5544997077000"],
                (Membro(nick="Yaza", telefone="554497077000"),),
            )
            == []
        )

    def test_sem_membro_nenhum_e_sem_colisao_a_lista_e_vazia(self):
        """O arranque de quem nao mexeu em nada continua exatamente como era."""
        assert colisoes_de_telefone([]) == []
        assert colisoes_de_telefone(["+5544997077000", "+5511988887777"]) == []

    def test_os_pares_saem_como_foram_CONFIGURADOS(self):
        """Nao normalizados: o usuario tem que achar as duas linhas no arquivo."""
        pares = colisoes_de_telefone(
            ["+55 (44) 99707-7000"],
            (Membro(nick="Korzis", telefone="+5511997077000"),),
        )
        assert pares == [
            ("+55 (44) 99707-7000", "+5511997077000", ORIGEM_DONO, ORIGEM_MEMBRO)
        ]


class TestOSufixoNaoProvaIdentidade:
    """CR-01: a supressao por sufixo calava o par que ESCALA privilegio.

    `_mesma_pessoa` existe para nao gritar quando o usuario escreveu o proprio
    numero de duas maneiras. Enquanto ela aceitou "um e sufixo do outro", ela
    tambem calou o par dono contra membro sempre que o lado do dono estava
    escrito curto — e um numero curto e sufixo de meio mundo.

    O probe do code review, na integra: com `CHATWOOT_TELEFONES_COMANDO`
    valendo `99998888` e o `[[membro]]` Korzis em `+5544999998888`, o Korzis
    alcancava `.corrigir` e `.pegou` — que reescrevem o `.loot/`, pasta sem
    poda e sem backup — e o arranque nao dizia UMA palavra.
    """

    DONO_CURTO = ["99998888"]
    KORZIS = Membro(nick="Korzis", telefone="+5544999998888")

    def test_o_probe_do_review_agora_e_uma_colisao_visivel(self):
        pares = colisoes_de_telefone(self.DONO_CURTO, (self.KORZIS,))
        assert pares, (
            "silencio aqui e a escalada de privilegio do CR-01: o par existe, "
            "autoriza, e nao aparece em lugar nenhum"
        )
        assert pares[0].escala_privilegio is True
        assert pares[0].origem_do_primeiro == ORIGEM_DONO
        assert pares[0].origem_do_segundo == ORIGEM_MEMBRO

    def test_e_o_par_realmente_autorizava_o_membro_no_comando_de_loot(self):
        """A outra metade do probe: sem a colisao visivel, isto passa calado."""
        assert (
            autorizado_para(
                Comando.LOOT_CORRIGIR,
                {"phone_number": "+5544999998888"},
                self.DONO_CURTO,
                (self.KORZIS,),
            )
            is True
        ), "se um dia isto virar False a colisao deixa de ser perigosa; ate la, e"

    def test_o_mesmo_numero_com_e_sem_o_nono_digito_continua_calado(self):
        """A supressao legitima nao pode ter sido jogada fora junto."""
        assert _mesma_pessoa("+5544997077000", "554497077000") is True
        assert _mesma_pessoa("+5544997077000", "+5544997077000") is True

    def test_o_mesmo_numero_com_e_sem_o_codigo_de_pais_tambem(self):
        """A outra metade do ruido que o review mediu.

        Isto passou a importar quando o par dono contra membro deixou de ser
        aviso e virou recusa de arranque: quem escreveu o proprio numero das
        duas maneiras nao pode ficar sem scanner por redundancia.
        """
        assert _mesma_pessoa("5544999998888", "44999998888") is True
        assert (
            colisoes_de_telefone(
                ["+5544999998888"],
                (Membro(nick="Yaza", telefone="44999998888"),),
            )
            == []
        )

    def test_sufixo_NAO_e_mais_prova_de_identidade(self):
        assert _mesma_pessoa("99998888", "+5544999998888") is False
        assert _mesma_pessoa("97077000", "+5544997077000") is False


class TestUmaPerguntaSoSobreQuemEEsteTelefone:
    """WR-11: a trava e o nick vinham de duas varreduras independentes.

    Toda mensagem autorizada varria `membros` duas vezes — uma para decidir se
    o remetente e membro, outra para descobrir o nick dele. Alem do trabalho
    repetido, eram DOIS pontos de decisao sobre a mesma pergunta. O dia em que
    um deles ganhasse um filtro ("membro desativado") e o outro nao, uma
    mensagem AUTORIZADA entraria na lista com `nick=None` e o bot responderia
    "nao sei que nick por na lista" a alguem corretamente configurado.
    """

    MEMBRO = Membro(nick="Korzis", telefone="+5544998001122")

    def _mensagem(self):
        return {
            "id": 77,
            "message_type": 0,
            "content": ".join",
            "conversation_id": 1,
            "sender": {"name": "Korzis WhatsApp", "phone_number": "+5544998001122"},
        }

    def test_a_trava_e_o_nick_saem_do_mesmo_membro(self, monkeypatch):
        """A resolucao acontece UMA vez por mensagem, e as duas derivam dela."""
        from l2scanner import comandos as modulo

        chamadas = []
        original = modulo.membro_do_remetente

        def contando(remetente, membros):
            chamadas.append(remetente.get("phone_number"))
            return original(remetente, membros)

        monkeypatch.setattr(modulo, "membro_do_remetente", contando)

        achados = modulo.comandos_novos(
            [self._mensagem()], set(), ["+5544997077000"], membros=[self.MEMBRO]
        )

        assert [m.nick for m in achados] == ["Korzis"]
        assert len(chamadas) == 1, (
            "a mesma pergunta foi feita duas vezes por dois caminhos "
            f"independentes: {chamadas}"
        )

    def test_um_filtro_novo_nao_pode_autorizar_com_nick_None(self, monkeypatch):
        """A prova de que o defeito virou impossivel, e nao so improvavel.

        Simula o filtro futuro que WR-11 descreve: `membro_do_remetente` passa
        a recusar este party-mate. As duas respostas tem que mudar JUNTAS — a
        mensagem nao pode ser autorizada e chegar sem nick.
        """
        from l2scanner import comandos as modulo

        monkeypatch.setattr(modulo, "membro_do_remetente", lambda *_: None)

        achados = modulo.comandos_novos(
            [self._mensagem()], set(), ["+5544997077000"], membros=[self.MEMBRO]
        )

        assert achados == [], (
            "o filtro pegou so um dos dois caminhos: a mensagem foi autorizada "
            "e entraria na lista com nick=None"
        )

    def test_autorizado_para_sem_o_parametro_continua_se_virando_sozinho(self):
        """Todo teste unitario chama assim; o sentinela nao pode ter quebrado."""
        remetente = {"phone_number": "+5544998001122"}
        assert (
            autorizado_para(Comando.JOIN, remetente, ["+5544997077000"], [self.MEMBRO])
            is True
        )
        assert (
            autorizado_para(Comando.JOIN, remetente, ["+5544997077000"], [])
            is False
        )

    def test_membro_None_explicito_e_diferente_de_nao_resolvido(self):
        """O sentinela distingue "procurei e nao era" de "procure voce".

        Um `None` default colapsaria os dois e faria a trava recusar todo
        party-mate em silencio.
        """
        remetente = {"phone_number": "+5544998001122"}
        assert (
            autorizado_para(
                Comando.JOIN, remetente, ["+5544997077000"], membro=None
            )
            is False
        )
        assert (
            autorizado_para(
                Comando.JOIN, remetente, ["+5544997077000"], membro=self.MEMBRO
            )
            is True
        )


class TestArranqueComMembros:
    """O que o console diz sobre o nivel novo, no arranque.

    Mesmo precedente do aviso COMANDOS ABERTOS que ja estava ali: um estado de
    permissao nao pode ser descoberto por acidente.
    """

    def _args(self):
        import argparse

        return argparse.Namespace(dry_run=False)

    def _config(self, telefones):
        from l2scanner.notificador import ConfigChatwoot

        return ConfigChatwoot(
            url="https://chat.exemplo",
            conta="1",
            token="t",
            conversas=["1"],
            conversas_de_comando=["7"],
            telefones_de_comando=telefones,
            etiqueta_de_comando="",
        )

    def _montar(self, monkeypatch, telefones, membros, caplog):
        from l2scanner import __main__ as principal

        monkeypatch.setattr(principal, "config_do_chatwoot", lambda: self._config(telefones))
        monkeypatch.setattr(principal, "ler_membros", lambda: list(membros))
        with caplog.at_level(logging.INFO):
            return principal.montar_leitor_de_comandos(self._args())

    def test_os_membros_lidos_chegam_no_leitor(self, monkeypatch, caplog):
        membros = [Membro(nick="Korzis", telefone="+5544912345678")]
        leitor = self._montar(monkeypatch, ["+5544997077000"], membros, caplog)
        assert leitor.membros == membros, (
            "o [[membro]] lido do arquivo tem que chegar no leitor, senao a "
            "fronteira existe no papel e nao no scanner"
        )

    def test_o_arranque_diz_quantos_podem_dar_join(self, monkeypatch, caplog):
        membros = [
            Membro(nick="Korzis", telefone="+5544912345678"),
            Membro(nick="J4guar", telefone="+5544933334444"),
        ]
        self._montar(monkeypatch, ["+5544997077000"], membros, caplog)
        assert "Korzis" in caplog.text and "J4guar" in caplog.text
        assert "/entrar" in caplog.text

    def test_a_colisao_dono_contra_membro_RECUSA_A_SUBIR(self, monkeypatch, caplog):
        """CR-01: avisar nao e mitigar uma escalada de privilegio.

        Este teste ja existia e afirmava o contrario — `leitor is not None`,
        com a justificativa de que "entre dois membros ela nao escala
        privilegio nenhum". A justificativa esta certa e o caso estava errado:
        o par usado e dono contra membro, que e exatamente o que escala. Quem
        roda com o console rolando nunca ia ver o warning, e o Korzis alcancava
        `.corrigir` e `.pegou` no `.loot/`, pasta sem poda e sem backup.

        A recusa e o desfecho certo: um scanner que nao liga ate o numero ser
        desambiguado custa alguns minutos; a escalada custa meses de
        estatistica, em silencio.
        """
        membros = [Membro(nick="Korzis", telefone="+5511997077000")]
        with pytest.raises(ConfiguracaoPerigosa) as erro:
            self._montar(monkeypatch, ["+5544997077000"], membros, caplog)

        texto = str(erro.value)
        assert "+5544997077000" in texto and "+5511997077000" in texto, (
            "a recusa precisa nomear as duas linhas, senao o usuario nao sabe "
            "o que consertar"
        )
        assert "/corrigir" in texto, (
            "a recusa precisa dizer a CONSEQUENCIA, nao so que os numeros sao "
            "parecidos"
        )

    def test_o_probe_do_review_derruba_o_arranque(self, monkeypatch, caplog):
        """O probe do CR-01 na integra, pelo caminho real do arranque."""
        membros = [Membro(nick="Korzis", telefone="+5544999998888")]
        with pytest.raises(ConfiguracaoPerigosa):
            self._montar(monkeypatch, ["99998888"], membros, caplog)

    def test_a_colisao_entre_dois_MEMBROS_avisa_e_deixa_subir(
        self, monkeypatch, caplog
    ):
        """A proporcao que a justificativa do teste antigo descrevia.

        Aqui ninguem ganha comando novo — o dano e um `.join` creditado ao nick
        errado — e recusar a subir deixaria o usuario sem vigia por um erro de
        digitacao.
        """
        membros = [
            Membro(nick="Korzis", telefone="+5544997077000"),
            Membro(nick="J4guar", telefone="+5511997077000"),
        ]
        leitor = self._montar(monkeypatch, ["+5544912345678"], membros, caplog)
        avisos = [r for r in caplog.records if r.levelno >= logging.WARNING]
        texto = "\n".join(r.getMessage() for r in avisos)
        assert "TELEFONES AMBIGUOS" in texto
        assert leitor is not None

    def test_telefone_de_dono_curto_demais_derruba_o_arranque(
        self, monkeypatch, caplog
    ):
        """Uma allowlist mais frouxa que a comparacao que a alimenta nao e allowlist.

        `99998888` tem exatamente os 8 digitos comparados e passa neste corte —
        quem pega esse caso e a recusa por colisao, dois testes acima. Aqui o
        alvo e o numero que nem chega ao corte.
        """
        with pytest.raises(ConfiguracaoPerigosa) as erro:
            self._montar(monkeypatch, ["7000"], [], caplog)
        assert "7000" in str(erro.value)

    def test_sem_allowlist_de_dono_o_arranque_NAO_promete_contencao(
        self, monkeypatch, caplog
    ):
        """WR-03: `autor_autorizado` devolve True para todo mundo com a lista vazia.

        Nesse estado "Nenhum deles alcanca comando de loot" e falso exatamente
        quando importa — e essa e a frase que da confianca ao usuario.
        """
        membros = [Membro(nick="Korzis", telefone="+5544912345678")]
        self._montar(monkeypatch, [], membros, caplog)
        assert "Nenhum deles alcanca comando de loot" not in caplog.text
        avisos = [r for r in caplog.records if r.levelno >= logging.WARNING]
        texto = "\n".join(r.getMessage() for r in avisos)
        assert "/corrigir" in texto and "CHATWOOT_TELEFONES_COMANDO" in texto

    def test_com_allowlist_de_dono_a_promessa_continua_sendo_feita(
        self, monkeypatch, caplog
    ):
        membros = [Membro(nick="Korzis", telefone="+5544912345678")]
        self._montar(monkeypatch, ["+5544997077000"], membros, caplog)
        assert "Nenhum deles alcanca comando de loot" in caplog.text

    def test_sem_membro_o_arranque_loga_exatamente_como_antes(
        self, monkeypatch, caplog
    ):
        self._montar(monkeypatch, ["+5544997077000"], [], caplog)
        assert "Presenca:" not in caplog.text
        assert "TELEFONES AMBIGUOS" not in caplog.text


class TestMolduraDoConsole:
    """A regra da moldura no console, como funcao pura.

    Uma regra so para os dois destinos, e nao um caso especial para o `.help`:
    qualquer resposta de varias linhas que aparecer depois ja nasce certa.
    """

    def test_resposta_de_uma_linha_continua_moldurada(self):
        from l2scanner.__main__ import _para_o_console

        saida = _para_o_console("KORZIS MORREU")
        assert _tem_borda(saida), (
            "a moldura do console sumiu para o caso de uma linha — ela existe "
            "para o evento nao se perder no meio do log"
        )

    def test_resposta_de_varias_linhas_sai_CRUA(self):
        from l2scanner.__main__ import _para_o_console

        texto = "primeira linha\nsegunda linha\nterceira"
        assert _para_o_console(texto) == texto

    def test_a_conta_de_moldurar_e_o_motivo(self):
        """Nao e questao de gosto: e a largura que explode.

        `moldurar` faz `max(LARGURA, len(miolo) + len(carimbo))` sobre a
        string inteira. Este teste mede o estrago que o desvio evita.
        """
        from l2scanner.console import LARGURA, moldurar

        emoldurado = moldurar(texto_de_ajuda(), "20:30")
        mais_larga = max(len(linha) for linha in emoldurado.splitlines())
        assert mais_larga > 5 * LARGURA
