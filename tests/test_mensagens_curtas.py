"""O ORCAMENTO DE CARACTERES DAS MENSAGENS QUE O USUARIO LE.

O PEDIDO, textual: "estamos mandando textos muito grandes, vamos ser mais
sucintos nas mensagens, leitura rapida, por exemplo texto do tiat podemos
reduzir muito somente para informacoes realmente necessarias".

O PRINCIPIO QUE ESTE ARQUIVO GUARDA. A mensagem carrega O QUE O USUARIO
PRECISA FAZER OU SABER PARA AGIR. O RACIOCINIO (por que o numero e aquele,
qual medicao o sustenta, que incidente ele evita) mora na DOCSTRING da funcao
que a produz, e nao no celular de quem esta no meio de um farm.

POR QUE UM PORTAO DE COMPRIMENTO, e nao so uma reescrita. Toda mensagem deste
projeto ficou longa do mesmo jeito: uma frase de justificativa acrescentada de
cada vez, cada uma defensavel sozinha. Sem um numero que recuse a soma, a
proxima justificativa entra e o texto volta a 349 caracteres em seis meses. Um
portao aqui e a unica coisa que torna o encurtamento uma propriedade do
projeto, em vez de uma limpeza que expira.

O ORCAMENTO SAI DA FREQUENCIA, e nao do gosto de quem escreve:

- RECORRENTE (chega toda hora, todo dia): tem de caber numa olhada. O corte e
  `ORCAMENTO_RECORRENTE`. Sao os alertas de party e as linhas de previsao do
  `/tiat`, que o usuario le no celular no meio do jogo.
- DE GRUPO (chega a TODO MUNDO, varias vezes por dia): `ORCAMENTO_DO_BOSS`.
  Sao as quatro frases de janela de boss. Em 2026-09-02 este teto era 180, com
  a razao escrita aqui: "elas carregam nome, duracao, um horario completo e a
  ressalva da ancora; nao cabem em 160 sem perder um desses quatro". Em
  2026-09-03 ele virou 80, e as quatro passam com folga — a duracao ("8h") era
  a regra do servidor, identica em toda mensagem, e a razao de ela poder sair
  esta em `respawn.texto_da_janela`. O TETO E O MENOR DOS TRES de proposito:
  estas frases vao para o grupo, entao cada caractere e pago pelo numero de
  pessoas VEZES o numero de ocorrencias.
- RARO E ACIONAVEL (uma vez por incidente, e o usuario tem de FAZER algo):
  `ORCAMENTO_RARO`. Pode ser mais longo, mas nao pode ter paragrafo de
  justificativa.

O QUE ESTE PORTAO NAO MEDE. Ele nao afirma que a mensagem esta certa: os
testes de cada modulo continuam fazendo isso, e continuam sendo o portao que
protege a informacao ACIONAVEL (o comando a digitar, o arquivo a abrir, o
numero a conferir). Este aqui so recusa a volta da justificativa.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from l2scanner.aprendiz import (
    RetratoDaContaminacao,
    RetratoDasRecusas,
    resumo_da_contaminacao,
    resumo_das_recusas,
)
from l2scanner.esquecimento import _linha_da_volta, _recusa_da_simulacao
from l2scanner.notificador import formatar
from l2scanner.rastreador import Evento, TipoDeEvento
from l2scanner.respawn import (
    Ancora,
    AvisoDeJanela,
    Boss,
    OrigemDoAviso,
    TipoDeJanela,
    linhas_de_previsao,
    texto_da_janela,
)

# Uma olhada no celular, sem rolar a tela.
ORCAMENTO_RECORRENTE = 160

# Nome do boss, o estado, o que fazer com ele, e de onde veio o numero.
# Mensagem de GRUPO: o custo de cada caractere e multiplicado pelo numero de
# pessoas que a recebem. Era 180 ate 2026-09-03 (ver a docstring de modulo).
ORCAMENTO_DO_BOSS = 80

# Raro e acionavel: cabe uma instrucao, nao cabe um paragrafo de por que.
ORCAMENTO_RARO = 320


def _quanto(texto: str) -> str:
    return f"{len(texto)} caracteres, o teto e: {texto}"


# ---------------------------------------------------------------------------
# RECORRENTE: o que chega no celular durante o farm.
# ---------------------------------------------------------------------------

NASCIMENTO = datetime(2026, 8, 30, 14, 30)
ABRE_EM = datetime(2026, 8, 30, 20, 30)
NORTH = Boss(nome="Tiat North", respawn_horas_min=6, respawn_horas_max=8)
SOUTH = Boss(nome="Tiat South", respawn_horas_min=6, respawn_horas_max=8)


def _ancora(origem=OrigemDoAviso.CHAT):
    return {"tiat-north": Ancora(boss="tiat-north", instante=NASCIMENTO, origem=origem)}


class TestAsLinhasDoTiat:
    """A resposta do `/tiat` e a que o usuario nomeou por escrito.

    Ela sai UMA LINHA POR BOSS: com dois bosses no `config.toml` a resposta
    inteira e a soma, e um excesso de 190 caracteres por linha vira uma
    mensagem de quase 400 no celular. O portao mede a LINHA porque e ela que
    multiplica.
    """

    @pytest.mark.parametrize(
        "origem", [OrigemDoAviso.CHAT, OrigemDoAviso.ALVO, OrigemDoAviso.CHAT_E_ALVO]
    )
    def test_a_linha_com_ancora_cabe_numa_olhada(self, origem):
        linha = linhas_de_previsao(ABRE_EM, [NORTH], _ancora(origem))[0]
        assert len(linha) <= ORCAMENTO_RECORRENTE, _quanto(linha)

    def test_a_linha_sem_ancora_cabe_numa_olhada(self):
        linha = linhas_de_previsao(ABRE_EM, [SOUTH], {})[0]
        assert len(linha) <= ORCAMENTO_RECORRENTE, _quanto(linha)

    def test_a_resposta_de_dois_bosses_ainda_cabe_numa_tela(self):
        """O caso real do usuario: Tiat North e Tiat South no mesmo config."""
        resposta = "\n".join(linhas_de_previsao(ABRE_EM, [NORTH, SOUTH], _ancora()))
        assert len(resposta) <= 2 * ORCAMENTO_RECORRENTE, _quanto(resposta)


# A ancora que cruzou a meia-noite: nascimento as 23:00 e a janela vencendo as
# 07:00 do dia seguinte. E o PIOR CASO do orcamento, porque e o unico em que a
# citacao curta carrega a data (mais 6 caracteres) — e com respawn de 8h ele
# acontece em cerca de um terco das mensagens, nao e um canto raro.
NASCIMENTO_DE_ONTEM = datetime(2026, 8, 29, 23, 0)
VENCE_DE_MANHA = datetime(2026, 8, 30, 7, 0)


class TestAsQuatroFrasesDeJanela:
    """As frases que o grupo recebe quando a janela abre e quando o limite passa."""

    @pytest.mark.parametrize("origem", [OrigemDoAviso.CHAT, OrigemDoAviso.ALVO])
    @pytest.mark.parametrize(
        "tipo,horas", [(TipoDeJanela.ABRE, 6), (TipoDeJanela.LIMITE, 8)]
    )
    @pytest.mark.parametrize(
        "instante,alvo",
        [
            (NASCIMENTO, ABRE_EM),
            (NASCIMENTO_DE_ONTEM, VENCE_DE_MANHA),
        ],
        ids=["ancora-de-hoje", "ancora-de-ontem"],
    )
    def test_cabe_no_orcamento_do_boss(self, tipo, horas, origem, instante, alvo):
        """As OITO: a matriz das quatro frases vezes os dois dias da ancora.

        Medir so a ancora do mesmo dia deixaria o portao cego justamente no
        caso mais longo, e o teto de 80 foi escolhido depois de medir ESTE.
        """
        texto = texto_da_janela(
            AvisoDeJanela(
                boss="Tiat North",
                tipo=tipo,
                ancora=Ancora(boss="tiat-north", instante=instante, origem=origem),
                alvo=alvo,
                horas=horas,
            )
        )
        assert len(texto) <= ORCAMENTO_DO_BOSS, _quanto(texto)

    def test_a_data_aparece_QUANDO_a_ancora_nao_e_de_hoje(self):
        """E some quando e. A conta so e conferivel se o horario for datavel.

        Sem esta distincao ha dois defeitos possiveis, um em cada direcao: uma
        ancora das 23:00 lida as 07:00 sem data vira um horario no FUTURO, e a
        data em toda mensagem faz dois tercos delas pagarem 6 caracteres para
        dizer "hoje".
        """
        def frase(instante, alvo):
            return texto_da_janela(
                AvisoDeJanela(
                    boss="Tiat North",
                    tipo=TipoDeJanela.ABRE,
                    ancora=Ancora(
                        boss="tiat-north",
                        instante=instante,
                        origem=OrigemDoAviso.CHAT,
                    ),
                    alvo=alvo,
                    horas=6,
                )
            )

        de_hoje = frase(NASCIMENTO, ABRE_EM)
        de_ontem = frase(NASCIMENTO_DE_ONTEM, VENCE_DE_MANHA)

        assert "14:30" in de_hoje and "30/08" not in de_hoje, de_hoje
        assert "29/08 23:00" in de_ontem, de_ontem


class TestOsAlertasDeParty:
    """Morte, saida, cegueira: o que chega mais vezes que qualquer outra coisa."""

    def _evento(self, tipo, **campos):
        campos.setdefault("membro", "Yazalaque")
        campos.setdefault("momento", 1787600000.0)
        return Evento(tipo=tipo, **campos)

    @pytest.mark.parametrize("tipo", list(TipoDeEvento))
    def test_todo_alerta_cabe_numa_olhada(self, tipo):
        texto = formatar(
            self._evento(tipo, segundos_no_estado=420.0, detalhe="tela de login")
        )
        assert len(texto) <= ORCAMENTO_RECORRENTE, _quanto(texto)


# ---------------------------------------------------------------------------
# RARO E ACIONAVEL: uma vez por incidente, e o usuario tem o que fazer.
# ---------------------------------------------------------------------------


class TestOsAvisosDeAprendizado:
    """As duas linhas do `scanner.log` que explicavam por que nao aprenderam.

    A recusa por contaminacao tinha 940 caracteres e terminava dizendo "NAO HA
    O QUE CONFIGURAR". Se nao ha o que fazer, nao precisa de 940 caracteres.
    """

    def test_a_contaminacao_com_dado_cabe_no_orcamento_raro(self):
        texto = resumo_da_contaminacao(
            RetratoDaContaminacao(
                recusas=7, menor=290, maior=843, teto=210, celulas=1200
            )
        )
        assert len(texto) <= ORCAMENTO_RARO, _quanto(texto)

    def test_a_contaminacao_sem_dado_cabe_numa_olhada(self):
        texto = resumo_da_contaminacao(RetratoDaContaminacao())
        assert len(texto) <= ORCAMENTO_RECORRENTE, _quanto(texto)

    @pytest.mark.parametrize(
        "retrato",
        [
            RetratoDasRecusas(recusas=104),
            RetratoDasRecusas(
                recusas=104,
                menor=3,
                maior=25,
                mediana=5.5,
                medidas=90,
                abaixo_do_teto=84,
                sugestao=6,
                regime="cintilacao",
            ),
            RetratoDasRecusas(
                recusas=6,
                menor=40,
                maior=1067,
                mediana=298.5,
                medidas=6,
                abaixo_do_teto=1,
                sugestao=None,
                regime="turbulencia",
            ),
        ],
        ids=["sem-distancia", "cintilacao", "turbulencia"],
    )
    def test_a_instabilidade_cabe_no_orcamento_raro(self, retrato):
        texto = resumo_das_recusas(retrato, tolerado=4)
        assert len(texto) <= ORCAMENTO_RARO, _quanto(texto)


class TestAsRespostasDoEsquecimento:
    def test_a_linha_da_volta_de_uma_chave_cabe_no_orcamento_raro(self):
        texto = _linha_da_volta(["a1b2c3d4"], com_nome=True)
        assert len(texto) <= ORCAMENTO_RARO, _quanto(texto)

    def test_a_linha_da_volta_de_um_lote_cabe_no_orcamento_raro(self):
        texto = _linha_da_volta(["a1b2c3d4", "e5f6a7b8"], com_nome=False)
        assert len(texto) <= ORCAMENTO_RARO, _quanto(texto)

    def test_a_recusa_da_simulacao_cabe_numa_olhada(self):
        assert len(_recusa_da_simulacao()) <= ORCAMENTO_RECORRENTE, _quanto(
            _recusa_da_simulacao()
        )


# ---------------------------------------------------------------------------
# OS INVARIANTES DE SEMPRE, sobre os textos JA ENCURTADOS.
#
# Encurtar nao pode virar afirmar, e nao pode introduzir um caractere que o
# cp1252 do caminho do WhatsApp nao carrega. Os dois portoes ja existem por
# familia de mensagem; aqui eles pegam o conjunto todo de uma vez, que e o
# unico jeito de um texto novo nascer coberto.
# ---------------------------------------------------------------------------


def todos_os_textos_encurtados() -> list[str]:
    textos: list[str] = []
    for origem in (OrigemDoAviso.CHAT, OrigemDoAviso.ALVO):
        textos.extend(linhas_de_previsao(ABRE_EM, [NORTH, SOUTH], _ancora(origem)))
        for tipo, horas in ((TipoDeJanela.ABRE, 6), (TipoDeJanela.LIMITE, 8)):
            textos.append(
                texto_da_janela(
                    AvisoDeJanela(
                        boss="Tiat North",
                        tipo=tipo,
                        ancora=Ancora(
                            boss="tiat-north", instante=NASCIMENTO, origem=origem
                        ),
                        alvo=ABRE_EM,
                        horas=horas,
                    )
                )
            )
    for tipo in TipoDeEvento:
        textos.append(
            formatar(
                Evento(
                    tipo=tipo,
                    momento=1787600000.0,
                    membro="Yazalaque",
                    segundos_no_estado=420.0,
                    detalhe="tela de login",
                )
            )
        )
    textos.append(
        resumo_da_contaminacao(
            RetratoDaContaminacao(
                recusas=7, menor=290, maior=843, teto=210, celulas=1200
            )
        )
    )
    textos.append(resumo_da_contaminacao(RetratoDaContaminacao()))
    textos.append(
        resumo_das_recusas(
            RetratoDasRecusas(
                recusas=104,
                menor=3,
                maior=25,
                mediana=5.5,
                medidas=90,
                abaixo_do_teto=84,
                sugestao=6,
                regime="cintilacao",
            ),
            tolerado=4,
        )
    )
    textos.append(_linha_da_volta(["a1b2c3d4"], com_nome=True))
    textos.append(_recusa_da_simulacao())
    return textos


@pytest.mark.parametrize("texto", todos_os_textos_encurtados())
def test_nenhum_texto_encurtado_tem_travessao(texto):
    """O caminho do WhatsApp passa por `cp1252`: um travessao vira `?`."""
    assert "—" not in texto, texto
    assert "–" not in texto, texto


@pytest.mark.parametrize("texto", todos_os_textos_encurtados())
def test_nenhum_texto_encurtado_saiu_do_ascii(texto):
    texto.encode("ascii")


@pytest.mark.parametrize("texto", todos_os_textos_encurtados())
def test_encurtar_nao_virou_afirmar(texto):
    """A redacao HEDGED sobrevive ao corte.

    "HP zerado, possivel morte" nao pode virar "morreu" no caminho de deixar a
    mensagem curta: a economia de caracteres seria paga com a unica coisa que
    o projeto inteiro protege, que e nao afirmar o que o scanner nao viu.
    """
    minusculo = texto.lower()
    for afirmacao in ("morreu na pt", "confirmado", "com certeza", "garantido"):
        assert afirmacao not in minusculo, f"{afirmacao!r} em: {texto}"


def test_a_prova_nao_e_vazia():
    """Guarda contra portao morto: a lista tem que ter texto de verdade."""
    textos = todos_os_textos_encurtados()
    assert len(textos) > 20
    assert all(texto.strip() for texto in textos)
