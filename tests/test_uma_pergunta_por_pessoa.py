"""UMA PERGUNTA = UMA PESSOA = UMA IMAGEM (conserto de campo do OCRN-03).

O QUE A VERIFICACAO EM CAMPO DE 01/09/2026 PROVOU, E O QUE ELA REFUTOU

O envio foi feito DE VERDADE, pelo caminho de producao
(`NotificadorChatwoot.enviar` com `anexos=`), para o grupo de WhatsApp do
usuario. Tres coisas ficaram CONFIRMADAS e continuam valendo:

- o Chatwoot ACEITA o `multipart/form-data` montado a mao com a stdlib;
- o provedor de WhatsApp ENTREGA imagem em grupo;
- a recompressao do WhatsApp NAO destroi a legibilidade: o nome saiu nitido
  com `AMPLIACAO = 6` e `INTER_NEAREST`.

E duas decisoes do desenho anterior foram REFUTADAS pela realidade. Estas duas
sao o motivo de este arquivo existir:

1. **"Uma mensagem, N anexos" NAO FUNCIONA.** Dois anexos foram mandados numa
   mensagem so; CHEGOU UM. O Chatwoot aceitou os dois (o POST nao deu erro) e a
   ponte de WhatsApp entregou so o primeiro. Nenhum teste offline pegaria isso:
   e comportamento do PROVEDOR, do outro lado do socket que esta suite nunca
   abre. O que a suite consegue guardar e o DESENHO que sobrevive a essa
   propriedade — uma pessoa por mensagem —, e e isso que os casos abaixo
   afirmam.

2. **A etiqueta dentro da imagem foi CORTADA pelo preview.** O PNG gerado
   estava correto (conferido no arquivo: o apelido aparece nitido a esquerda),
   mas a imagem tinha 836x138 — proporcao ~6:1 — e o WhatsApp corta as laterais
   no preview da bolha. O apelido estava colado na esquerda e sumiu da tela. A
   protecao existia no arquivo e NAO existia no olho do usuario, que e o pior
   tipo de protecao: ela era justamente o cinto de seguranca contra a ordem se
   perder.

   MEDIDO no mesmo dia: uma imagem de proporcao **1.60:1** nao sofreu o corte.
   O alvo escolhido e **3:2 (1.50:1)**, do lado seguro do ponto medido, com o
   apelido ACIMA do nome em vez de ao lado.

OS IDIOMAS SAO COPIADOS, E NAO IMPORTADOS, pela razao que
`tests/test_janela_sob_demanda.py` ja escreve: importar entre arquivos de teste
cria dependencia entre eles.

Nenhum caso aqui abre socket, e nenhum encosta em `config.toml`,
`calibration.json` ou `.identidades/` do repositorio. Tudo roda em `tmp_path`.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.acervo import (
    PREFIXO_ASSINATURA,
    PREFIXO_NOME,
    PREFIXO_PERGUNTA,
    AcervoDeIdentidades,
    carregar_identidades,
    chave_da_assinatura,
)
from l2scanner.agenda import RegistroEmDisco
from l2scanner.aprendiz import AjustesDoAprendiz, Aprendiz
from l2scanner.batismo import (
    INTERVALO_ENTRE_PERGUNTAS,
    Pendente,
    apelido_da_chave,
    montar_pergunta_com_imagens,
    pendentes_do_acervo,
    pode_perguntar,
)
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.identidade import Assinatura, criar_assinatura
from l2scanner.rastreador import Rastreador
from l2scanner.retrato import AMPLIACAO, MARGEM, MOLDURA, PROPORCAO_DA_BOLHA
from l2scanner.sessao import Sessao
from l2scanner.visao import _recorte_do_nome

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "identidade"

# A borda que nao e pixel do jogo: a margem branca mais a moldura cinza.
BORDA = MARGEM + MOLDURA


# ---------------------------------------------------------------------------
# Fixtures e falsos, copiados de `test_batismo.py` e `test_a_pergunta_leva_a_imagem.py`
# ---------------------------------------------------------------------------


@pytest.fixture
def calibracao() -> Calibracao:
    cal = Calibracao.carregar(FIXTURES / "calibracao.json")
    cal.assinaturas = []
    return cal


@pytest.fixture
def pixels() -> np.ndarray:
    px = cv2.imread(str(FIXTURES / "party_ordem_original.png"), cv2.IMREAD_COLOR)
    assert px is not None, "fixture da party nao pode ser lida"
    return px


def mascara_com_texto(semente: int, altura: int = 20, largura: int = 110):
    """Uma mascara 0/1 com a forma de um nome: um bloco de colunas acesas.

    NAO E RUIDO ALEATORIO, pela razao que `test_a_pergunta_leva_a_imagem.py` ja
    escreve: as colunas acesas sao conhecidas, entao a afirmacao e sobre pixels
    nomeados.
    """
    mascara = np.zeros((altura, largura), dtype=np.uint8)
    mascara[4 : altura - 4, semente % 5 + 2 :: 5] = 1
    mascara[2, 4 + semente] = 1
    return mascara


def assinatura_fabricada(semente: int) -> Assinatura:
    return Assinatura(nome="", mascara=mascara_com_texto(semente))


def assinatura_da_linha(px: np.ndarray, cal: Calibracao, indice: int) -> Assinatura:
    recorte = _recorte_do_nome(px, cal, indice)
    assert recorte is not None
    return criar_assinatura("", recorte)


def semear(pasta: Path, assinatura: Assinatura, nome: str | None = None) -> str:
    """Escreve uma entrada A MAO, como um humano faria, e devolve a chave."""
    pasta.mkdir(parents=True, exist_ok=True)
    chave = chave_da_assinatura(assinatura)
    corpo = assinatura.como_dict()
    corpo.pop("nome", None)
    (pasta / f"{PREFIXO_ASSINATURA}{chave}.json").write_text(
        json.dumps(corpo), encoding="utf-8"
    )
    if nome is not None:
        (pasta / f"{PREFIXO_NOME}{chave}").write_text(nome, encoding="utf-8")
    return chave


def marcadores_da_pasta(pasta: Path) -> list[str]:
    """Os apelidos das chaves que ja tem `perguntado_<chave>` em disco."""
    return sorted(
        apelido_da_chave(c.name[len(PREFIXO_PERGUNTA) :])
        for c in pasta.iterdir()
        if c.name.startswith(PREFIXO_PERGUNTA)
    )


def apelidos_listados(texto: str) -> list[str]:
    """Os apelidos que a mensagem cita, um por linha indentada."""
    return [
        linha.strip().split(" ")[0]
        for linha in texto.splitlines()
        if linha.startswith("  ")
    ]


class DespachanteQueGrava:
    """Grava `(texto, categoria, conversa_alvo)` em vez de mandar para a rede.

    Truthy de proposito: `Sessao._despachar` testa `if self.despachante`.
    """

    def __init__(self) -> None:
        self.despachos: list[tuple[str, object, str | None]] = []
        self.anexados: list[tuple[str, ...]] = []
        self.reservas: list[str | None] = []

    def despachar(
        self,
        texto,
        categoria=None,
        conversa_alvo=None,
        anexos=None,
        texto_sem_anexos=None,
    ) -> None:
        self.despachos.append((texto, categoria, conversa_alvo))
        self.anexados.append(tuple(a.nome_do_arquivo for a in anexos or ()))
        self.reservas.append(texto_sem_anexos)

    @property
    def perguntas(self) -> list[str]:
        """So os despachos que sao a PERGUNTA do batismo."""
        return [texto for texto, _, _ in self.despachos if "/batizar" in texto]

    @property
    def imagens_das_perguntas(self) -> list[tuple[str, ...]]:
        return [
            anexos
            for (texto, _, _), anexos in zip(self.despachos, self.anexados)
            if "/batizar" in texto
        ]


class SilencioParado:
    def ativo(self):
        return False

    def atualizar(self, agora):
        return None


def carregar_na_calibracao(cal, pasta: Path):
    identidades = carregar_identidades([], AcervoDeIdentidades(pasta))
    cal.assinaturas = identidades.assinaturas
    return identidades


def montar_sessao(
    tmp_path,
    calibracao,
    *,
    acervo,
    despachante=None,
    identidades=None,
    pendentes_de_batismo=(),
    momento_da_ultima_pergunta=None,
) -> Sessao:
    return Sessao(
        cal=calibracao,
        rastreador=Rastreador(
            nomes=list(calibracao.nomes),
            assinaturas_configuradas=(
                identidades.configuradas if identidades is not None else False
            ),
        ),
        eventos_agendados=[],
        registro=RegistroEmDisco(tmp_path / "agenda"),
        silencio=SilencioParado(),
        despachante=despachante,
        aprendiz=Aprendiz(acervo, AjustesDoAprendiz(leituras_para_aprender=3)),
        acervo=acervo,
        pendentes_de_batismo=pendentes_de_batismo,
        momento_da_ultima_pergunta=momento_da_ultima_pergunta,
    )


def rodar(sessao, pixels, inicio: int, fim: int, base: int = 1_700_000_000):
    """Ticks de UM em UM segundo, que e a cadencia real do scanner (~1 Hz)."""
    for indice in range(inicio, fim):
        sessao.tick(
            Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
            momento=base + indice,
        )


# ---------------------------------------------------------------------------
# 1. UMA PERGUNTA LEVA UMA PESSOA SO
# ---------------------------------------------------------------------------


class TestUmaPerguntaLevaUmaPessoaSo:
    """O conserto do achado 1: o provedor entrega UM anexo por mensagem.

    Uma mensagem com tres anexos chega com UM. Entao a mensagem passa a ter
    UMA pessoa, e as outras esperam a proxima rodada.
    """

    def test_tres_anonimas_produzem_UMA_pessoa_e_UMA_imagem(self, tmp_path):
        for semente in range(3):
            semear(tmp_path, assinatura_fabricada(semente))
        acervo = AcervoDeIdentidades(tmp_path, simulando=False)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        assert pergunta is not None
        assert len(pergunta.imagens) == 1, (
            "mais de um anexo numa mensagem so: MEDIDO em campo em 01/09/2026, "
            f"o provedor entrega UM. Saiu: {pergunta.imagens}"
        )
        assert len(apelidos_listados(pergunta.texto)) == 1, (
            f"a mensagem cita mais de uma pessoa:\n{pergunta.texto}"
        )

    def test_a_imagem_e_a_da_pessoa_CITADA(self, tmp_path):
        """A legenda e o conteudo tem de ser da MESMA pessoa.

        Com um anexo so o risco de trocar some por construcao — e este caso e
        o que impede alguem de reintroduzir a troca escolhendo a imagem por
        outro criterio que nao a pessoa perguntada.
        """
        for semente in range(3):
            semear(tmp_path, assinatura_fabricada(semente))
        acervo = AcervoDeIdentidades(tmp_path, simulando=False)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        (apelido,) = apelidos_listados(pergunta.texto)
        assert [a.nome_do_arquivo for a in pergunta.imagens] == [f"{apelido}.png"]

    def test_as_outras_saem_nas_RODADAS_SEGUINTES_e_nenhuma_se_perde(
        self, tmp_path
    ):
        """O defeito mais caro possivel aqui e uma pessoa nunca ser perguntada.

        Tres chamadas seguidas tem de cobrir as tres pendentes, sem repetir
        nenhuma e sem pular nenhuma. A quarta nao pergunta mais nada.
        """
        chaves = {
            apelido_da_chave(semear(tmp_path, assinatura_fabricada(s)))
            for s in range(3)
        }
        acervo = AcervoDeIdentidades(tmp_path, simulando=False)

        perguntadas = []
        for _ in range(3):
            pergunta = montar_pergunta_com_imagens(
                acervo, pendentes_do_acervo(acervo)
            )
            assert pergunta is not None, (
                f"uma das tres nunca foi perguntada. Ja sairam: {perguntadas}"
            )
            perguntadas.extend(apelidos_listados(pergunta.texto))

        assert sorted(perguntadas) == sorted(chaves), (
            f"as tres rodadas nao cobriram as tres pendentes: {perguntadas}"
        )
        assert montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo)) is None


# ---------------------------------------------------------------------------
# 2. O MARCADOR SO E QUEIMADO DE QUEM FOI PERGUNTADO
# ---------------------------------------------------------------------------


class TestOMarcadorSoQueimaDeQuemFoiPerguntado:
    """O defeito mais caro possivel deste conserto, dito em voz alta.

    `perguntado_<chave>` e de MAO UNICA: nao ha comando de esquecer no v1, e
    nenhum codigo apaga esse arquivo. Se a redacao passar a citar UMA pessoa
    mas o marcador continuar sendo queimado das N, as outras N-1 ficam
    "Membro N" PARA SEMPRE — perguntadas segundo o disco, e nunca perguntadas
    segundo o WhatsApp do usuario. E uma perda silenciosa e permanente.
    """

    def test_tres_pendentes_queimam_UM_marcador_so(self, tmp_path):
        for semente in range(3):
            semear(tmp_path, assinatura_fabricada(semente))
        acervo = AcervoDeIdentidades(tmp_path, simulando=False)

        montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        assert len(marcadores_da_pasta(tmp_path)) == 1, (
            "o marcador foi queimado de quem nao foi perguntado: essas pessoas "
            f"ficam anonimas para sempre. {marcadores_da_pasta(tmp_path)}"
        )

    def test_o_marcador_que_existe_e_o_DA_PESSOA_CITADA(self, tmp_path):
        """Guarda contra o conserto preguicoso.

        Queimar o marcador de uma e perguntar por OUTRA cumpriria a contagem
        do caso acima e produziria o mesmo desfecho permanente.
        """
        for semente in range(3):
            semear(tmp_path, assinatura_fabricada(semente))
        acervo = AcervoDeIdentidades(tmp_path, simulando=False)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        assert marcadores_da_pasta(tmp_path) == apelidos_listados(pergunta.texto)

    def test_quem_ficou_para_a_proxima_rodada_CONTINUA_perguntavel(self, tmp_path):
        chaves = [semear(tmp_path, assinatura_fabricada(s)) for s in range(3)]
        acervo = AcervoDeIdentidades(tmp_path, simulando=False)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))
        (perguntado,) = apelidos_listados(pergunta.texto)

        for chave in chaves:
            if apelido_da_chave(chave) == perguntado:
                continue
            sozinha = montar_pergunta_com_imagens(acervo, [Pendente(chave=chave)])
            assert sozinha is not None, (
                f"{apelido_da_chave(chave)} nao foi perguntada e ja esta com o "
                "marcador queimado: ela nunca mais sera perguntada"
            )


# ---------------------------------------------------------------------------
# 3. O ESPACAMENTO ENTRE PERGUNTAS
# ---------------------------------------------------------------------------


class TestOEspacamentoEntrePerguntas:
    """Duas pessoas aprendidas em ticks proximos nao viram duas bolhas seguidas.

    O TEMPO ENTRA POR PARAMETRO. `batismo.py` esta no portao AST de
    `tests/test_presenca.py`, ao lado de `acervo.py` e `aprendiz.py`, e a
    razao escrita la vale inteira aqui: um relogio proprio neste modulo seria
    lido como conveniencia e reabriria por dentro a porta que D-04 fecha por
    construcao.
    """

    def test_a_primeira_pergunta_nao_espera_nada(self):
        assert pode_perguntar(1_700_000_000.0, None) is True

    def test_dentro_do_intervalo_nao_pergunta(self):
        antes = 1_700_000_000.0
        assert pode_perguntar(antes + INTERVALO_ENTRE_PERGUNTAS - 1, antes) is False

    def test_no_intervalo_EXATO_ja_pergunta(self):
        antes = 1_700_000_000.0
        assert pode_perguntar(antes + INTERVALO_ENTRE_PERGUNTAS, antes) is True

    def test_um_relogio_que_anda_PARA_TRAS_nao_bloqueia_para_sempre(self):
        """A degradacao e para o lado de PERGUNTAR, e nao para o de calar.

        Um replay reiniciado, ou um `momento` que volta, deixaria a diferenca
        negativa para sempre — e uma pessoa que nunca e perguntada fica anonima
        para sempre. Errar aqui custa uma bolha a mais; errar para o outro lado
        custa a pessoa.
        """
        antes = 1_700_000_000.0
        assert pode_perguntar(antes - 5_000, antes) is True

    def test_o_intervalo_e_de_pelo_menos_meio_minuto(self):
        """Uma constante que virasse 1s reabriria a enxurrada sem quebrar nada.

        O numero escolhido e 60s: e o tempo de o usuario ler UMA pergunta e
        responder antes de a proxima chegar, num grupo cujo dono ja desligou
        `avisar_no_horario` do Solo Boss por VOLUME.
        """
        assert INTERVALO_ENTRE_PERGUNTAS >= 30.0

    def test_a_funcao_e_PURA_e_nao_tem_relogio_por_dentro(self):
        """Duas chamadas com os mesmos argumentos dao a mesma resposta.

        Um `time.monotonic()` escondido dentro dela faria a segunda chamada
        divergir da primeira sem nada mudar por fora.
        """
        antes = 1_700_000_000.0
        agora = antes + INTERVALO_ENTRE_PERGUNTAS / 2
        assert pode_perguntar(agora, antes) == pode_perguntar(agora, antes)


class TestOPortaoDeRelogioAlcancaOModuloNovo:
    def test_batismo_continua_sem_now_de_datetime(self):
        """Guarda: o espacamento nao pode ter entrado como relogio proprio."""
        fonte = (RAIZ / "l2scanner" / "batismo.py").read_text(encoding="utf-8")
        achados = [
            no.attr
            for no in ast.walk(ast.parse(fonte))
            if isinstance(no, ast.Attribute)
            and no.attr in {"now", "utcnow", "monotonic", "time"}
        ]
        assert achados == [], f"batismo.py ganhou relogio proprio: {achados}"


# ---------------------------------------------------------------------------
# 4. A SESSAO: duas pessoas no mesmo tick, duas rodadas
# ---------------------------------------------------------------------------


class TestDuasPessoasNoMesmoTickNaoViramDuasBolhas:
    DESCONHECIDAS = (1, 3)

    def _sessao_com_duas_desconhecidas(self, tmp_path, pixels, calibracao):
        for indice in range(4):
            if indice not in self.DESCONHECIDAS:
                semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path, simulando=False),
            despachante=despachante,
            identidades=identidades,
        )
        return sessao, despachante

    def test_no_mesmo_tick_sai_UMA_pergunta_com_UM_anexo(
        self, tmp_path, pixels, calibracao
    ):
        sessao, despachante = self._sessao_com_duas_desconhecidas(
            tmp_path, pixels, calibracao
        )

        rodar(sessao, pixels, 0, 10)

        assert len(despachante.perguntas) == 1, (
            "duas bolhas seguidas no WhatsApp: MEDIDO em campo, so a primeira "
            f"imagem chega. {despachante.perguntas}"
        )
        assert despachante.imagens_das_perguntas == [
            despachante.imagens_das_perguntas[0]
        ]
        assert len(despachante.imagens_das_perguntas[0]) == 1

    def test_a_segunda_sai_depois_do_INTERVALO_e_com_a_imagem_dela(
        self, tmp_path, pixels, calibracao
    ):
        sessao, despachante = self._sessao_com_duas_desconhecidas(
            tmp_path, pixels, calibracao
        )

        rodar(sessao, pixels, 0, 10)
        assert len(despachante.perguntas) == 1, "premissa: a primeira ja saiu"

        rodar(sessao, pixels, 10, 10 + int(INTERVALO_ENTRE_PERGUNTAS) + 5)

        assert len(despachante.perguntas) == 2, (
            "a segunda pessoa nunca foi perguntada depois do intervalo: ela "
            f"fica Membro N para sempre. {despachante.perguntas}"
        )
        primeira, segunda = (
            apelidos_listados(p)[0] for p in despachante.perguntas
        )
        assert primeira != segunda, "a mesma pessoa foi perguntada duas vezes"
        assert despachante.imagens_das_perguntas[1] == (f"{segunda}.png",)

    def test_a_segunda_nao_tem_o_marcador_queimado_ENQUANTO_ESPERA(
        self, tmp_path, pixels, calibracao
    ):
        sessao, despachante = self._sessao_com_duas_desconhecidas(
            tmp_path, pixels, calibracao
        )

        rodar(sessao, pixels, 0, 10)

        assert len(despachante.perguntas) == 1, "premissa: uma pergunta so saiu"
        assert marcadores_da_pasta(tmp_path) == apelidos_listados(
            despachante.perguntas[0]
        ), (
            "quem esta na fila esperando ja teve o marcador queimado: a "
            "pergunta dela nunca vai sair"
        )

    def test_a_cadencia_NAO_cresce_com_os_ticks(
        self, tmp_path, pixels, calibracao
    ):
        """Duas pendentes produzem DUAS perguntas, e nunca uma por tick."""
        sessao, despachante = self._sessao_com_duas_desconhecidas(
            tmp_path, pixels, calibracao
        )

        rodar(sessao, pixels, 0, 400)

        assert len(despachante.perguntas) == 2, (
            f"a pergunta virou enxurrada: {len(despachante.perguntas)} bolhas"
        )


class TestAsPendentesDoArranqueTerminamNaSessao:
    """As entradas que JA estao no disco sao as unicas do acervo real.

    O arranque pergunta UMA. As outras nao podem esperar o proximo reinicio do
    scanner: elas entram na sessao e saem uma por intervalo.
    """

    def test_a_sessao_pergunta_as_que_o_arranque_deixou(
        self, tmp_path, pixels, calibracao
    ):
        for indice in range(4):
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        acervo = AcervoDeIdentidades(tmp_path, simulando=False)
        pendentes = pendentes_do_acervo(acervo)
        assert len(pendentes) == 4, "premissa: quatro anonimas no disco"

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=acervo,
            despachante=despachante,
            identidades=identidades,
            pendentes_de_batismo=pendentes,
        )

        rodar(sessao, pixels, 0, 4 * int(INTERVALO_ENTRE_PERGUNTAS) + 10)

        saidos = [apelidos_listados(p)[0] for p in despachante.perguntas]
        assert sorted(saidos) == sorted(
            apelido_da_chave(p.chave) for p in pendentes
        ), f"a sessao nao drenou a fila do arranque: {saidos}"

    def test_o_momento_da_ULTIMA_pergunta_do_arranque_e_respeitado(
        self, tmp_path, pixels, calibracao
    ):
        """O arranque acabou de mandar uma. A sessao nao pode mandar outra ja.

        Sem este elo, o usuario recebe duas bolhas no mesmo segundo em que o
        scanner sobe — que e exatamente a rajada que este conserto desfaz.
        """
        for indice in range(4):
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        acervo = AcervoDeIdentidades(tmp_path, simulando=False)
        pendentes = pendentes_do_acervo(acervo)

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=acervo,
            despachante=despachante,
            identidades=identidades,
            pendentes_de_batismo=pendentes,
            momento_da_ultima_pergunta=1_700_000_000.0,
        )

        rodar(sessao, pixels, 0, int(INTERVALO_ENTRE_PERGUNTAS) - 5)

        assert despachante.perguntas == [], (
            "a sessao perguntou dentro do intervalo que o arranque abriu"
        )


class TestOArranqueEntregaAFilaParaASessao:
    """O elo estrutural, no molde dos portoes que este projeto ja tem.

    Um caso de comportamento sobre o `laco_principal` exigiria subir o programa
    inteiro. O que esta em jogo e uma LIGACAO que pode sumir num refactor sem
    nenhum teste ficar vermelho — e o precedente ja custou uma fase inteira
    desligada em campo com a suite verde.
    """

    @staticmethod
    def _sessoes(fonte: str) -> list[ast.Call]:
        return [
            no
            for no in ast.walk(ast.parse(fonte))
            if isinstance(no, ast.Call)
            and (getattr(no.func, "id", None) or getattr(no.func, "attr", None))
            == "Sessao"
        ]

    def test_o_laco_principal_passa_a_fila_e_o_momento(self):
        fonte = (RAIZ / "l2scanner" / "__main__.py").read_text(encoding="utf-8")
        chamadas = self._sessoes(fonte)
        assert chamadas, "nenhuma `Sessao(...)` em __main__.py"
        for chamada in chamadas:
            passados = {p.arg for p in chamada.keywords}
            assert "pendentes_de_batismo" in passados, (
                "as anonimas que o arranque nao perguntou ficam esperando o "
                "proximo reinicio do scanner"
            )
            assert "momento_da_ultima_pergunta" in passados, (
                "a sessao nao sabe que o arranque acabou de perguntar, e manda "
                "a segunda bolha no mesmo segundo"
            )

    def test_o_portao_acusaria_a_fila_arrancada(self):
        """Guarda contra prova vazia."""
        fonte = (RAIZ / "l2scanner" / "__main__.py").read_text(encoding="utf-8")
        envenenado = fonte.replace("pendentes_de_batismo=", "_arrancado=")
        assert envenenado != fonte, "a mutacao plantada nao pegou"
        for chamada in self._sessoes(envenenado):
            if "pendentes_de_batismo" not in {p.arg for p in chamada.keywords}:
                return
        raise AssertionError("o portao nao acusaria a fila arrancada")


# ---------------------------------------------------------------------------
# 5. O TEXTO PARA DE FALAR DE ORDEM E DE LISTA
# ---------------------------------------------------------------------------


class TestOTextoNaoFalaMaisDeOrdemNemDeLista:
    """Com UMA pessoa por mensagem, ordem e lista deixaram de existir.

    As frases antigas — "na mesma ordem desta lista", "as outras N ficaram sem
    imagem" — descreviam um envelope que o provedor nunca entregou. Manter
    qualquer uma delas seria descrever para o usuario uma mensagem que ele nao
    recebeu, que e a mentira plausivel que este projeto combate.
    """

    @pytest.fixture
    def pergunta(self, tmp_path):
        for semente in range(5):
            semear(tmp_path, assinatura_fabricada(semente))
        acervo = AcervoDeIdentidades(tmp_path, simulando=False)
        return montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

    @pytest.mark.parametrize(
        "proibida",
        [
            "mesma ordem",
            "lista acima",
            "ficaram sem imagem",
            "ficou sem imagem",
            "cada uma",
            "primeiras",
        ],
    )
    def test_a_frase_de_ordem_ou_de_lista_saiu(self, pergunta, proibida):
        for texto in (pergunta.texto, pergunta.texto_sem_imagens):
            assert proibida not in texto.lower(), f"{proibida!r} em:\n{texto}"

    def test_o_cabecalho_fala_de_UMA_pessoa_no_SINGULAR(self, pergunta):
        assert "Aprendi 1 pessoa que ainda esta sem nome" in pergunta.texto
        assert "pessoas" not in pergunta.texto, pergunta.texto
        assert "estao sem nome" not in pergunta.texto, pergunta.texto

    def test_a_reserva_continua_sem_prometer_imagem(self, pergunta):
        """O texto que sai quando o anexo falha nao pode prometer imagem."""
        assert "imagem" not in pergunta.texto_sem_imagens.lower()
        assert "/batizar" in pergunta.texto_sem_imagens
        assert apelidos_listados(pergunta.texto_sem_imagens) == apelidos_listados(
            pergunta.texto
        )

    def test_o_texto_com_imagem_AVISA_que_ela_veio_junto(self, pergunta):
        assert "imagem" in pergunta.texto.lower()

    def test_continua_sem_travessao_e_cabendo_no_cp1252(self, pergunta):
        for texto in (pergunta.texto, pergunta.texto_sem_imagens):
            assert "—" not in texto, f"travessao em: {texto!r}"
            assert "–" not in texto, f"meia risca em: {texto!r}"
            texto.encode("cp1252")

    def test_a_saida_da_pergunta_absurda_continua_escrita(self, pergunta):
        """T-02-07: um recorte contaminado pode ter virado entrada.

        Ignorar so e seguro porque D-04 garante que a pergunta nao volta, e
        dizer isso com todas as letras e o que transforma "o bot esta pedindo
        uma coisa sem sentido" em "e so nao responder".
        """
        assert "nao pergunto de novo" in pergunta.texto


# ---------------------------------------------------------------------------
# 6. A IMAGEM SOBREVIVE AO CORTE DO PREVIEW
# ---------------------------------------------------------------------------


def desenhar(mascara, apelido: str = "0dcf6f") -> np.ndarray:
    from l2scanner.retrato import png_do_nome

    img = cv2.imdecode(
        np.frombuffer(png_do_nome(mascara, apelido), np.uint8),
        cv2.IMREAD_GRAYSCALE,
    )
    assert img is not None, "o PNG nao abre"
    return img


class TestAEtiquetaSobreviveAoCorteDoPreview:
    """O conserto do achado 2, e ele e sobre o OLHO do usuario.

    A etiqueta existia no ARQUIVO e nao existia na TELA: 836x138 (~6:1) e o
    WhatsApp corta as laterais no preview da bolha. O apelido estava colado na
    esquerda e sumiu — e ele e o cinto de seguranca contra a ordem se perder.
    """

    def test_a_proporcao_final_fica_em_3_por_2(self):
        img = desenhar(mascara_com_texto(1))
        altura, largura = img.shape

        assert largura / altura == pytest.approx(PROPORCAO_DA_BOLHA, abs=0.02), (
            f"{largura}x{altura} da {largura / altura:.2f}:1. MEDIDO em campo: "
            "6:1 e cortado no preview, 1.60:1 nao e"
        )

    def test_a_imagem_LARGA_que_foi_cortada_em_campo_nao_volta(self):
        """A afirmacao que pega a regressao inteira, com o numero de campo.

        836x138 sao ~6.06:1. Qualquer coisa acima de 2:1 ja esta a caminho
        daquele desfecho.
        """
        for semente in (0, 3, 7):
            img = desenhar(mascara_com_texto(semente))
            altura, largura = img.shape
            assert largura / altura < 2.0, f"{largura}x{altura}"

    def test_o_apelido_fica_ACIMA_do_nome_e_nao_ao_LADO(self):
        """Dois PNGs da MESMA mascara com apelidos diferentes.

        A area do nome (a faixa de baixo) tem de ser IDENTICA nos dois, e o que
        esta acima dela tem de diferir. Foi o apelido AO LADO que o corte
        lateral comeu.
        """
        mascara = mascara_com_texto(2)
        alta = mascara.shape[0] * AMPLIACAO

        uma = desenhar(mascara, "0dcf6f")
        outra = desenhar(mascara, "15caec")

        assert uma.shape == outra.shape
        nome_de_uma = uma[-(alta + BORDA) : -BORDA, BORDA:-BORDA]
        nome_da_outra = outra[-(alta + BORDA) : -BORDA, BORDA:-BORDA]
        assert np.array_equal(nome_de_uma, nome_da_outra), (
            "a faixa de baixo mudou com o apelido: o nome nao esta la embaixo"
        )
        assert not np.array_equal(uma[: -(alta + BORDA)], outra[: -(alta + BORDA)]), (
            "o apelido nao esta ACIMA do nome"
        )

    def test_a_largura_da_imagem_e_a_do_nome_e_nao_a_do_nome_MAIS_a_faixa(self):
        mascara = mascara_com_texto(4)
        img = desenhar(mascara)

        assert img.shape[1] == mascara.shape[1] * AMPLIACAO + 2 * BORDA, (
            "sobrou faixa lateral: era ela que empurrava a proporcao para 6:1"
        )

    def test_o_nome_continua_sem_meio_tom(self):
        """`INTER_NEAREST` foi CONFIRMADO em campo e nao pode se perder.

        A recompressao do WhatsApp nao destruiu a legibilidade justamente
        porque cada pixel do jogo continua sendo um quadrado. Cinza inventado
        nessa escala e o que transforma um `l` num `I`.
        """
        mascara = mascara_com_texto(5)
        img = desenhar(mascara)
        alta = mascara.shape[0] * AMPLIACAO

        area = img[-(alta + BORDA) : -BORDA, BORDA:-BORDA]
        tons = set(np.unique(area).tolist())
        assert tons <= {0, 255}, f"a ampliacao suavizou: {sorted(tons)}"

    def test_a_ampliacao_confirmada_em_campo_continua_em_6(self):
        assert AMPLIACAO == 6, (
            "6x foi CONFIRMADO em campo em 01/09/2026: o nome saiu nitido "
            "depois da recompressao do WhatsApp"
        )

    def test_o_acervo_real_do_usuario_desenha_na_proporcao_nova(self):
        """A prova de campo, e ela e read-only.

        PULA quando a pasta nao existe (outra maquina, CI): um teste que exige
        o disco de uma pessoa e um teste que quebra na maquina de todo mundo.
        """
        pasta = RAIZ / ".identidades"
        arquivos = sorted(pasta.glob("*assinatura_*.json")) if pasta.exists() else []
        if not arquivos:
            pytest.skip("acervo real ausente nesta maquina")

        for arquivo in arquivos:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            dados.setdefault("nome", "")
            img = desenhar(Assinatura.de_dict(dados).mascara, "abcdef")
            altura, largura = img.shape
            assert largura / altura == pytest.approx(
                PROPORCAO_DA_BOLHA, abs=0.05
            ), f"{arquivo.name}: {largura}x{altura}"
