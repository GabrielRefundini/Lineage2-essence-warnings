"""Regressao do bug "a party estavel entra e sai em looping".

O SINTOMA: com 5 pessoas fixas na party, o scanner anunciou 52 eventos de
ENTROU/SAIU em 25 minutos. Nenhum deles aconteceu de verdade.

Os frames em fixtures/party_estavel_com_vazamento/ foram capturados ao vivo com
a party PARADA, e sao a unica entrada da suite que contem as condicoes reais que
quebravam o reconhecimento:

    limpo.png            mascara do nome com  93 px, Korzis casa a 0.976
    vazamento_leve.png   mascara com 184 px,        Korzis cai para 0.538
    vazamento_forte.png  mascara com 251 px,        Korzis cai para 0.433
    linha_fantasma.png   uma linha de chat passa no teste de icone

O teste que devia ter pego isto ja existia (`test_ninguem_aparece_duplicado`) e
tinha o oraculo certo. O que faltava era ENTRADA ADVERSARIAL: ele rodava contra
um frame limpo, onde a propriedade vale trivialmente.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.rastreador import Rastreador, TipoDeEvento
from l2scanner.visao import EstadoDaLinha, LeituraDeLinha, Observacao, extrair

FIXTURES = Path(__file__).parent / "fixtures" / "party_estavel_com_vazamento"

TODOS_OS_FRAMES = ("limpo", "vazamento_leve", "vazamento_forte", "linha_fantasma")


@pytest.fixture
def calibracao() -> Calibracao:
    return Calibracao.carregar(FIXTURES / "calibracao.json")


def carregar(rotulo: str) -> Frame:
    pixels = cv2.imread(str(FIXTURES / f"{rotulo}.png"), cv2.IMREAD_COLOR)
    assert pixels is not None, f"fixture {rotulo}.png nao pode ser lida"
    return Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK)


class TestLinhaFantasmaNaoCegaOScanner:
    """Correcao D.

    A regiao capturada e mais alta que a party window de proposito, para caber
    uma party cheia. O excedente cai sobre o chat e o minimapa.

    Uma linha de chat com contraste alto passava no teste do icone de classe.
    Ai `_bordas_da_barra_intactas` rodava sobre esse lixo, falhava, e executava
    `ui_visivel = False` para o FRAME INTEIRO. `_truncar_no_primeiro_vao`
    descartava a linha logo depois — tarde demais, a cegueira ja tinha
    acontecido e nada a desfazia.

    Custo real: cada frame assim levava o rastreador para CEGO e depois para
    REAQUISICAO, com 3 s de tolerancia em que nenhum estado avanca. O usuario
    via "[reajustando]" e todos os membros com "?".
    """

    def test_linha_de_chat_depois_do_vao_nao_derruba_a_visibilidade(self, calibracao):
        obs = extrair(carregar("linha_fantasma"), calibracao)
        assert obs.ui_visivel, (
            "uma linha DEPOIS do primeiro vao nao existe para a party window; "
            "deixa-la cegar o scanner troca 4 membros visiveis por 4 pontos de "
            "interrogacao"
        )

    def test_a_party_continua_com_quatro_membros(self, calibracao):
        obs = extrair(carregar("linha_fantasma"), calibracao)
        assert obs.membros_presentes == 4

    @pytest.mark.parametrize("rotulo", TODOS_OS_FRAMES)
    def test_nenhum_frame_da_party_parada_fica_cego(self, rotulo, calibracao):
        assert extrair(carregar(rotulo), calibracao).ui_visivel

    @pytest.mark.parametrize("rotulo", TODOS_OS_FRAMES)
    def test_nao_ha_vao_no_meio_da_lista(self, rotulo, calibracao):
        """A party window nunca tem buraco: ocupadas primeiro, vazias depois."""
        obs = extrair(carregar(rotulo), calibracao)
        estados = [l.estado is EstadoDaLinha.COM_MEMBRO for l in obs.linhas]
        assert estados == sorted(estados, reverse=True), (
            f"lista com vao no meio: {estados}"
        )


class TestSaidaRealVoltaASerDetectada:
    """Correcao E.

    A guarda anterior congelava a saida de TODOS sempre que QUALQUER linha
    ocupada estivesse sem identidade. Parecia conservadora e era: com dois
    membros da party sem assinatura gravada — o estado normal de quem acabou de
    calibrar — a condicao valia em 100% dos frames e a deteccao de saida ficava
    completamente desligada. Silenciosamente: o scanner nao reclamava, so nunca
    avisava.

    O discriminador certo nao e "alguma linha esta sem nome", e sim "a party
    window ENCOLHEU". Quando alguem sai de verdade as linhas compactam e sobra
    uma linha a menos. Quando o reconhecimento falha, a linha continua la.
    """

    NOMES = ["Kaus", "Korzis"]

    def montar(self, nomes_por_linha):
        """Uma observacao com uma linha por nome; None = nao reconhecida."""
        linhas = [
            LeituraDeLinha(
                indice=i,
                estado=EstadoDaLinha.COM_MEMBRO,
                hp=1.0,
                mp=1.0,
                nome=nome,
                confianca_do_nome=1.0 if nome else 0.0,
            )
            for i, nome in enumerate(nomes_por_linha)
        ]
        return Observacao(indice_do_frame=0, ui_visivel=True, linhas=tuple(linhas))

    def aquecer(self, rastreador, obs, ate=15):
        for t in range(ate):
            rastreador.observar(obs, float(t))
        return float(ate)

    def test_saida_real_dispara_mesmo_com_linhas_nao_reconhecidas(self):
        """O caso que estava quebrado: 2 membros sem assinatura na party."""
        r = Rastreador(nomes=self.NOMES)
        completa = self.montar(["Kaus", "Korzis", None, None])
        t = self.aquecer(r, completa)

        # Kaus sai: a linha some e as de baixo compactam.
        depois = self.montar(["Korzis", None, None])
        eventos = []
        for i in range(20):
            eventos += r.observar(depois, t + i)

        saidas = [e for e in eventos if e.tipo is TipoDeEvento.SAIU]
        assert saidas, (
            "Kaus saiu de verdade e nenhum SAIU foi emitido — a guarda de "
            "reconhecimento estava desligando a deteccao inteira"
        )
        assert [e.membro for e in saidas] == ["Kaus"]

    def test_falha_de_reconhecimento_nao_vira_saida(self):
        """O outro lado: a linha continua la, so nao sabemos de quem e."""
        r = Rastreador(nomes=self.NOMES)
        completa = self.montar(["Kaus", "Korzis", None, None])
        t = self.aquecer(r, completa)

        # O reconhecimento do Korzis pisca, mas a party continua com 4 linhas.
        piscada = self.montar(["Kaus", None, None, None])
        eventos = []
        for i in range(20):
            eventos += r.observar(piscada, t + i)

        assert not [e for e in eventos if e.tipo is TipoDeEvento.SAIU], (
            "a party window nao encolheu, entao ninguem saiu: anunciar saida "
            "aqui e o falso alarme que o usuario reportou"
        )

    def test_nome_roubado_por_outra_assinatura_nao_vira_saida(self):
        """O bug exato do relato: Korzis casou na linha do Kaus.

        Observado em logs/scanner.log 17:21:09 — "Korzis, Korzis, TioMad,
        J4guar" com o Kaus sumido, entre "KAUS SAIU" e "KAUS ENTROU".
        """
        r = Rastreador(nomes=self.NOMES)
        completa = self.montar(["Kaus", "Korzis", None, None])
        t = self.aquecer(r, completa)

        roubada = self.montar(["Korzis", "Korzis", None, None])
        eventos = []
        for i in range(20):
            eventos += r.observar(roubada, t + i)

        assert not eventos, (
            f"a party continua com 4 linhas; nada aconteceu de verdade. "
            f"Eventos indevidos: {[(e.tipo.value, e.membro) for e in eventos]}"
        )


class TestUnicidadeDaAssinatura:
    """Correcao A.

    Duas linhas sao duas pessoas. Isso e uma restricao do DOMINIO, e restricao
    de dominio pertence ao algoritmo — nao a um teste que torce para ela nao ser
    violada.

    Decidindo linha a linha, nada impedia a mesma assinatura de ganhar duas
    linhas. Aconteceu 8 vezes numa sessao de 25 minutos com a party parada
    (logs/scanner.log), e cada vez o membro roubado sumia do conjunto de
    identidades e virava um "saiu da party" que nunca aconteceu.
    """

    @pytest.mark.parametrize("rotulo", TODOS_OS_FRAMES)
    def test_nenhuma_assinatura_em_duas_linhas(self, rotulo, calibracao):
        obs = extrair(carregar(rotulo), calibracao)
        reconhecidos = [l.nome for l in obs.linhas if l.nome]
        assert len(reconhecidos) == len(set(reconhecidos)), (
            f"{rotulo}: a mesma assinatura foi atribuida a duas linhas — "
            f"{reconhecidos}"
        )

    @pytest.mark.parametrize("rotulo", TODOS_OS_FRAMES)
    def test_membro_sem_assinatura_nunca_vira_membro_calibrado(
        self, rotulo, calibracao
    ):
        """As linhas 2 e 3 sao membros da party sem assinatura gravada.

        Elas tem de continuar anonimas. Herdar o nome de um membro calibrado
        seria a pior falha possivel do produto: um alerta com o nome errado
        manda a party socorrer a pessoa errada, e ninguem desconfia porque a
        mensagem parece perfeitamente normal.
        """
        obs = extrair(carregar(rotulo), calibracao)
        nao_calibradas = [l.nome for l in obs.linhas if l.indice in (2, 3)]
        assert nao_calibradas == [None, None], (
            f"{rotulo}: linha sem assinatura recebeu nome {nao_calibradas}"
        )

    def test_o_frame_de_vazamento_nao_inventa_identidade(self, calibracao):
        """O gatilho de tudo: algo claro vaza na regiao do nome.

        A mascara do Korzis triplica (93 -> 251 px) e a correlacao correta
        despenca de 0.976 para 0.433. O certo e admitir "nao sei" — nunca
        deixar outra assinatura ocupar a vaga.
        """
        obs = extrair(carregar("vazamento_forte"), calibracao)
        nomes = [l.nome for l in obs.linhas if l.estado is EstadoDaLinha.COM_MEMBRO]
        assert nomes.count("Kaus") <= 1
        assert nomes.count("Korzis") <= 1
        assert nomes[0] == "Kaus", "o membro nao afetado tem de continuar reconhecido"
