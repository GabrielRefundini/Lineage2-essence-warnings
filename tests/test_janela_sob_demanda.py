"""O comando que RESPONDE a janela de respawn, em vez de so anuncia-la sozinho.

O pedido do usuario, nas palavras dele: "eu preciso de um comando para checar a
janela do tiat, se alguem mandar por exemplo /tiat no privado do bot ele avisar
o horario do ultimo e prox tiat (e janela random explicitamente)".

O TRABALHO PESADO JA ESTAVA FEITO. `respawn.linhas_de_previsao` e pura, ja
diz uma linha por boss, ja cita a ancora com horario e ja se cala quando nao viu
nascimento nenhum. Este arquivo prova o que faltava: um caminho de ENTRADA ate
aquele texto, com as travas de autorizacao ligadas, nos DOIS lacos, sem eco no
grupo.

O NOME DO COMANDO E GENERICO E O DO APELIDO NAO E, e a assimetria e o ponto.
O workstream inteiro foi construido sobre os blocos `[[boss]]` do config.toml,
justamente porque o usuario disse desde o inicio que no futuro o mesmo codigo
serve para outro mob. Um membro de enum chamado `TIAT` seria o unico lugar do
sistema preso a um boss especifico. Mas a mao que digita no meio do farm digita
`/tiat`, e ela tem que funcionar — entao a forma escrita e concreta e o simbolo
e generico, que e exatamente o que o `_VOCABULARIO` existe para permitir
(`scanner` -> `STATUS` e o precedente).
"""

from __future__ import annotations

import ast
import inspect
import time
from datetime import datetime

import pytest

from l2scanner.agenda import RegistroEmDisco
from l2scanner.bosses import Boss, OrigemDoAviso
from l2scanner.comandos import (
    COMANDOS_DE_MEMBRO,
    Comando,
    Membro,
    interpretar,
    texto_de_ajuda,
)
from l2scanner.respawn import chave_do_nascimento

# Os dois Tiats como o `config.toml` do usuario os tem HOJE: 8h fixas mais ate
# 2h de sorteio. Construidos aqui e nunca lidos daquele arquivo, pela razao ja
# escrita em `tests/test_respawn.py` — ele e do usuario e ele o edita.
SOUTH = Boss(nome="Tiat South", respawn_horas_min=8, respawn_horas_max=10)
NORTH = Boss(nome="Tiat North", respawn_horas_min=8, respawn_horas_max=10)

# Os nascimentos medidos em campo em 2026-08-30.
NASCEU_SOUTH = datetime(2026, 8, 30, 21, 59)
NASCEU_NORTH = datetime(2026, 8, 30, 22, 29)
AGORA = datetime(2026, 8, 31, 3, 0)

# O telefone de DONO, o mesmo que o resto da suite usa.
DONO = "+5544997077000"
# O de MEMBRO nao pode colidir com o de dono nos 8 digitos finais, que sao os
# unicos comparados: 97077000 contra 12345678.
MEMBRO = "+5544912345678"
MEMBROS = (Membro(nick="Korzis", telefone=MEMBRO),)


class DespachanteQueGrava:
    """Grava `(texto, categoria, conversa_alvo)` em vez de mandar para a rede.

    Copia deliberada do falso de `tests/test_presenca.py`: importa-lo criaria
    uma dependencia entre arquivos de teste, e o que esta em jogo aqui e o
    DESTINO, que e o terceiro argumento da chamada. Truthy de proposito —
    `atender_comandos` testa `if not despachante`.
    """

    def __init__(self) -> None:
        self.despachos: list[tuple[str, object, str | None]] = []

    def despachar(self, texto, categoria=None, conversa_alvo=None) -> None:
        self.despachos.append((texto, categoria, conversa_alvo))

    @property
    def alvos(self) -> list:
        """So os destinos, na ordem em que sairam. `None` e o grupo."""
        return [conversa for _, _, conversa in self.despachos]

    @property
    def textos(self) -> list:
        return [texto for texto, _, _ in self.despachos]


class LeitorDeUmaMensagem:
    """Um `LeitorDeComandos` falso que devolve UMA mensagem crua.

    A mensagem e CRUA (dict, como a API do Chatwoot devolve) de proposito: as
    travas de `comandos_novos` — tipo, nota privada, id repetido, vocabulario e
    autorizacao — tem de rodar de verdade. Montar `MensagemDeComando` a mao
    pularia justamente a costura, que e onde os erros deste projeto moram.
    """

    ativo = True

    def __init__(self, texto: str, *, telefone: str = DONO, conversa="1") -> None:
        self.telefones = [DONO]
        self.membros = list(MEMBROS)
        self._mensagem = {
            "id": 7777,
            "content": texto,
            "message_type": 0,
            "private": False,
            "sender": {"name": "Ze do Zap", "phone_number": telefone},
            "conversation_id": conversa,
        }

    def ler(self, _monotonico):
        return [self._mensagem]


def registro_com_os_dois_tiats(tmp_path) -> RegistroEmDisco:
    registro = RegistroEmDisco(tmp_path / "agenda")
    registro.registrar_nascimento(
        chave_do_nascimento("Tiat South", NASCEU_SOUTH, OrigemDoAviso.CHAT)
    )
    registro.registrar_nascimento(
        chave_do_nascimento("Tiat North", NASCEU_NORTH, OrigemDoAviso.CHAT)
    )
    return registro


def perguntar(
    texto: str,
    tmp_path,
    *,
    telefone: str = DONO,
    bosses=(SOUTH, NORTH),
    registro=None,
    conversa="1",
) -> DespachanteQueGrava:
    """Roda `atender_comandos` como o LACO roda, e devolve o que saiu.

    `agora` e `datetime` e `monotonico` e float: os dois relogios de
    `atender_comandos` nao sao intercambiaveis, e passar um so foi o crash de
    producao de 2026-08-24.
    """
    from l2scanner.__main__ import atender_comandos

    despachante = DespachanteQueGrava()
    atender_comandos(
        LeitorDeUmaMensagem(texto, telefone=telefone, conversa=conversa),
        registro if registro is not None else registro_com_os_dois_tiats(tmp_path),
        [],
        despachante,
        AGORA,
        time.monotonic(),
        bosses=bosses,
    )
    return despachante


class TestOComandoNasceGenerico:
    """O simbolo nao pode ser `TIAT`, e a razao nao e estetica.

    Todo o resto do workstream le os blocos `[[boss]]` do config.toml e nunca
    cita um boss pelo nome no fonte. Um membro de enum chamado `TIAT` seria o
    unico lugar do sistema onde trocar de mob exigiria editar codigo — e o
    usuario disse desde o inicio que quer usar o mesmo codigo para outro boss.
    """

    def test_existe_um_comando_de_janela_no_enum(self):
        assert hasattr(Comando, "JANELA")

    def test_NAO_existe_um_comando_chamado_TIAT(self):
        assert not hasattr(Comando, "TIAT"), (
            "o enum ficou preso a um boss especifico; o resto do workstream le "
            "o [[boss]] do config.toml e este simbolo passaria a ser a unica "
            "excecao"
        )

    @pytest.mark.parametrize(
        "escrita", ["/tiat", "/janela", "/janelas", "/boss", "/bosses", "/respawn"]
    )
    def test_todas_as_formas_escritas_caem_no_mesmo_comando(self, escrita):
        """`/tiat` TEM de funcionar: e a forma que a mao digita no farm.

        As genericas existem para o dia em que o boss vigiado for outro, e a
        lista e curta pela razao ja escrita no topo do `_VOCABULARIO` — cada
        palavra registrada la e um personagem que deixa de ser consultavel por
        `/<nick>`.
        """
        assert interpretar(escrita) is Comando.JANELA


class TestQualquerPartyMateAlcanca:
    """O comando entra em `COMANDOS_DE_MEMBRO`, e a justificativa e curta.

    A doutrina daquele frozenset e lista de INCLUSAO: cada entrada nova precisa
    dizer por que merece estar la. Esta merece porque a informacao que ela
    devolve JA E ANUNCIADA ao grupo pelo proprio bot quando a janela vence —
    entao o comando nao revela nada que o party-mate nao fosse receber sozinho.
    Ele so responde sob demanda o que ja sai por conta propria.
    """

    def test_a_janela_e_alcancavel_por_membro(self):
        assert Comando.JANELA in COMANDOS_DE_MEMBRO

    def test_o_telefone_de_membro_recebe_a_resposta(self, tmp_path):
        despachante = perguntar("/tiat", tmp_path, telefone=MEMBRO)

        assert despachante.alvos == ["1"], (
            "um telefone declarado em [[membro]] nao alcancou a janela"
        )
        assert "Tiat South" in despachante.textos[0]


class TestAAjudaAnunciaOComando:
    """O tripwire `set(_AJUDA) == set(Comando)` ja quebra a suite sem a linha.

    Estes testes provam a outra metade: que a linha ANUNCIA a forma que o
    usuario vai digitar. Uma entrada tecnicamente presente mas escrita so na
    forma generica deixaria `/tiat` invisivel — e comando nao anunciado, neste
    projeto, e comando que morre no `continue` do laco de autorizacao, sem
    resposta de recusa nenhuma.
    """

    def test_a_ajuda_ensina_a_forma_que_o_usuario_digita(self):
        assert "/tiat" in texto_de_ajuda()

    def test_a_ajuda_tambem_menciona_a_forma_generica(self):
        assert "/janela" in texto_de_ajuda()


class TestOTextoDaResposta:
    """O que chega no celular de quem perguntou."""

    def test_responde_sobre_TODOS_os_bosses_vigiados_na_ordem_do_config(
        self, tmp_path
    ):
        """Sem filtro por argumento: `/tiat` e uma pergunta, nao uma consulta.

        A ordem e a do `config.toml` porque uma ordem que muda entre respostas
        faria o usuario reler a lista inteira toda vez — a mesma razao ja
        escrita em `linhas_de_previsao`.
        """
        texto = perguntar("/tiat", tmp_path).textos[0]

        assert texto.index("Tiat South") < texto.index("Tiat North")

    def test_cita_o_ULTIMO_nascimento_com_horario(self, tmp_path):
        texto = perguntar("/tiat", tmp_path).textos[0]

        assert "21:59 de 30/08" in texto, "nao citou o nascimento do South"
        assert "22:29 de 30/08" in texto, "nao citou o nascimento do North"
        assert "servidor" in texto

    def test_diz_quando_a_janela_abre_e_quando_o_limite_passa(self, tmp_path):
        texto = perguntar("/tiat", tmp_path).textos[0]

        assert "31/08 05:59" in texto and "31/08 07:59" in texto
        assert "31/08 06:29" in texto and "31/08 08:29" in texto

    def test_diz_a_janela_ALEATORIA_por_extenso(self, tmp_path):
        """O acrescimo que o usuario pediu com todas as letras.

        Sem esta frase a resposta entrega dois horarios e nenhuma explicacao
        para eles serem dois.
        """
        texto = perguntar("/tiat", tmp_path).textos[0]

        assert "8h fixas" in texto
        assert "2h aleatorias" in texto

    def test_sem_ancora_nenhuma_NAO_inventa_horario(self, tmp_path):
        """T-02-13 atravessa ate o WhatsApp.

        Um horario inventado aqui e a mesma familia de defeito que a poda de
        tres dias existe para impedir — uma afirmacao sobre o futuro que
        ninguem tem como conferir — so que agora no celular da party inteira.
        """
        texto = perguntar(
            "/tiat", tmp_path, registro=RegistroEmDisco(tmp_path / "vazia")
        ).textos[0]

        assert "nascimento" in texto
        assert not any(c.isdigit() for c in texto), (
            f"a resposta sem ancora inventou um numero: {texto}"
        )

    def test_sem_boss_nenhum_no_config_a_resposta_diz_isso(self, tmp_path):
        """E nao uma resposta VAZIA.

        `linhas_de_previsao` devolve lista vazia sem boss, e com razao — quem
        imprime no console e um laco. Aqui a lista vazia viraria uma mensagem
        em branco no WhatsApp, que do lado de quem perguntou e indistinguivel
        do bot ter caido.
        """
        texto = perguntar("/tiat", tmp_path, bosses=()).textos[0]

        assert texto.strip()
        assert "boss" in texto.lower()


class TestNaoEcoaNoGrupo:
    """`avisar_o_grupo = False`, e a flag e SETADA e nao herdada.

    O comentario de `__main__.py` avisa por escrito que um ramo que devolve
    `str` sem setar a flag herda EM SILENCIO o valor do comando ANTERIOR da
    mesma volta do laco, e o efeito e resposta privada vazando para o grupo.
    Este e um ramo que devolve `str`.
    """

    def test_a_resposta_vai_SO_para_quem_perguntou(self, tmp_path):
        despachante = perguntar("/tiat", tmp_path)

        assert despachante.alvos == ["1"], (
            "a janela ecoou no grupo: e pergunta pessoal, igual ao /status, e "
            "ecoar seria ruido para quem nao perguntou"
        )

    def test_a_flag_e_SETADA_no_ramo_e_nao_herdada(self):
        """Portao de estrutura, e nao de comportamento.

        O teste acima passaria por acidente se o comando anterior da volta
        tivesse deixado `False` na variavel. Este le o fonte e exige a
        atribuicao dentro do proprio ramo, que e a unica coisa que impede a
        heranca silenciosa de voltar num refactor.
        """
        from l2scanner import __main__ as principal

        arvore = ast.parse(inspect.getsource(principal.atender_comandos))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.If):
                continue
            fonte_do_teste = ast.dump(no.test)
            if "JANELA" not in fonte_do_teste:
                continue
            atribuicoes = [
                alvo.id
                for filho in no.body
                if isinstance(filho, ast.Assign)
                for alvo in filho.targets
                if isinstance(alvo, ast.Name)
            ]
            assert "avisar_o_grupo" in atribuicoes, (
                "o ramo da JANELA nao seta avisar_o_grupo: ele herdaria em "
                "silencio o valor do comando anterior"
            )
            return
        raise AssertionError("nao ha ramo para Comando.JANELA em atender_comandos")


class TestFuncionaNosDoisLacos:
    """A familia de defeito que este projeto ja pagou DUAS vezes.

    Logica certa, ligada num caminho so. `atender_comandos` e chamada pelo laco
    da agenda (`--so-agenda`) e pelo laco principal, e o usuario roda os dois.
    Um `bosses=` esquecido de um lado nao quebra nada de forma visivel: o
    comando simplesmente responde "nao ha boss vigiado" naquele modo, e do lado
    de quem perguntou isso e indistinguivel de config errado.

    LE O FONTE, e nao o comportamento, pela mesma razao de
    `test_os_dois_lacos_passam_time_monotonic`: os lacos tem `while True` e
    captura de tela dentro, e nao ha como roda-los num teste.
    """

    def _chamada(self, nome_do_laco) -> ast.Call:
        from l2scanner import __main__ as principal

        arvore = ast.parse(inspect.getsource(getattr(principal, nome_do_laco)))
        for no in ast.walk(arvore):
            if (
                isinstance(no, ast.Call)
                and isinstance(no.func, ast.Name)
                and no.func.id == "atender_comandos"
            ):
                return no
        raise AssertionError(f"{nome_do_laco} nao chama atender_comandos")

    @pytest.mark.parametrize("laco", ["laco_principal", "laco_da_agenda"])
    def test_os_dois_lacos_passam_a_lista_de_bosses(self, laco):
        chamada = self._chamada(laco)
        nomeados = {palavra.arg for palavra in chamada.keywords}

        assert "bosses" in nomeados, (
            f"{laco} nao passa `bosses` para atender_comandos: o /tiat "
            f"responderia 'nao ha boss vigiado' neste modo"
        )

    @pytest.mark.parametrize("laco", ["laco_principal", "laco_da_agenda"])
    def test_o_que_e_passado_e_a_VARIAVEL_do_laco_e_nao_um_vazio(self, laco):
        """Guarda contra o conserto preguicoso.

        `bosses=()` satisfaria o teste acima e deixaria o defeito inteiro de
        pe: a chamada existe, o comando responde, e a resposta e sempre "nao ha
        boss vigiado". Os dois lacos leem a lista de `ler_bosses()` com nomes
        DIFERENTES (`bosses` na agenda, `regras_de_respawn` no principal), e e
        por isso que este teste afirma a forma e nao o nome.
        """
        chamada = self._chamada(laco)
        passado = next(p.value for p in chamada.keywords if p.arg == "bosses")

        assert isinstance(passado, ast.Name), (
            f"{laco} passa um literal para `bosses` em vez da lista lida do "
            f"config.toml"
        )
