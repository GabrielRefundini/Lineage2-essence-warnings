"""A coroa do lider quebra o reconhecimento NOS DOIS SENTIDOS.

O QUE JA ESTAVA COBERTO
-----------------------
`TestMembroQueViraLider`, em tests/test_identidade.py, cobre o sentido em que a
coroa esta NO RECORTE ao vivo e falta na assinatura: quem foi calibrado sem
coroa e depois virou lider. Aconteceu em 2026-08-25 e custou duas horas de
operacao cega.

O SENTIDO QUE FALTAVA, e que aconteceu tambem
---------------------------------------------
O inverso. A coroa esta gravada NA ASSINATURA e sumiu da tela: quem foi
calibrado ENQUANTO era lider e depois deixou de ser. Visto em campo em
2026-08-31, com uma party de quatro, todos os quatro calibrados:

    assinatura de Mostarda -> a imagem dela COM a coroa (ela era lider)
    recorte ao vivo        -> "ostarda", sem coroa (ela nao e mais lider)

Ela virou "Membro 3" no console. Welazkez teve o problema espelhado (calibrado
sem coroa, lider hoje), e os outros dois, cuja condicao de lider nao mudou,
foram reconhecidos sem tropeco. Ou seja: o discriminador do defeito e
exatamente a MUDANCA de lideranca, nos dois sentidos.

O DESENHO E O MESMO, e de proposito
-----------------------------------
Um SEGUNDO PASSE que testa UM alinhamento a mais, escolhido pela estrutura
("bloco, lacuna, bloco") de um dos lados, ancorado no outro, e cobrado com
limiar e margem mais caros. A diferenca e so de qual lado se le a lacuna:

    sentido ja coberto   lacuna no RECORTE  -> desloca o RECORTE   para a esquerda
    sentido novo         lacuna na ASSINATURA -> desloca a ASSINATURA para a esquerda

NAO e o `.max()` irrestrito que foi removido: aquele varria 25 deslocamentos e
rendia +0.000 nos casamentos certos e ate +0.373 nos errados. Aqui continua
sendo UM alinhamento por par, determinado pelos pixels.

A FIXTURE AJUDA, E OS PIXELS DA COROA SAO REAIS
-----------------------------------------------
Na fixture o Korzis E o lider, e a assinatura gravada dele TEM a coroa (lacuna
lida em 10). O que estes testes fabricam e o outro lado: o recorte dele como
ficaria DEPOIS de ele perder a lideranca. E o espelho exato do que
`assinatura_sem_coroa` fabrica no arquivo vizinho.

Medido com esses pixels, o recorte do ex-lider contra as quatro assinaturas:

    primeiro passe   0.266  0.146  0.252  0.298   <- a propria assinatura em 0.266
    sentido novo     1.000  0.000  0.000  0.000
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.identidade import (
    LIMIAR_DE_CASAMENTO,
    LIMIAR_DO_ORNAMENTO,
    Assinatura,
    _correlacionar,
    _inicio_do_nome_apos_ornamento,
    _pontuar,
    _pontuar_sem_o_ornamento_da_assinatura,
    _primeira_coluna_com_texto,
    _reancorar_a_assinatura_sem_ornamento,
    identificar_linhas,
    mascara_de_texto,
)

FIXTURES = Path(__file__).parent / "fixtures" / "identidade"


@pytest.fixture
def calibracao() -> Calibracao:
    return Calibracao.carregar(FIXTURES / "calibracao.json")


def recorte_de(mascara: np.ndarray) -> np.ndarray:
    """Um recorte BGR que produz EXATAMENTE esta mascara.

    Claro (255) onde a mascara acende, escuro (30) no resto — os dois lados
    bem longe de VALOR_MINIMO_DE_TEXTO = 180.

    Existe para os testes entrarem por `identificar_linhas`, que recebe PIXELS.
    Um teste que entrasse direto com mascaras exercitaria um caminho que
    producao nao usa, e a passagem por `mascara_de_texto` e justamente onde um
    erro de canal ou de tipo apareceria.
    """
    plano = np.where(mascara > 0, 255, 30).astype(np.uint8)
    return np.repeat(plano[:, :, None], 3, axis=2)


def sem_a_coroa(assinatura: Assinatura, margem: int = 0) -> np.ndarray:
    """A mascara do ex-lider: a mesma pessoa DEPOIS de perder a coroa.

    Tira o ornamento da assinatura real e traz o nome para `margem`, que e onde
    um nome sem coroa comeca — medido, entre a coluna 0 e a 2 conforme o nome.

    E o espelho de `TestMembroQueViraLider.assinatura_sem_coroa`: la o produto e
    a ASSINATURA sem coroa e o recorte tem a coroa; aqui o produto e o RECORTE
    sem coroa e a coroa fica na assinatura.
    """
    com_coroa = assinatura.mascara
    inicio = _inicio_do_nome_apos_ornamento(com_coroa)
    assert inicio is not None, "a assinatura da fixture tem de ter coroa"

    corpo = com_coroa[:, inicio:]
    sem_coroa = np.zeros_like(com_coroa)
    largura = min(corpo.shape[1], sem_coroa.shape[1] - margem)
    sem_coroa[:, margem : margem + largura] = corpo[:, :largura]
    return sem_coroa


class TestOSintomaEstaNaFixture:
    """Sem isto os testes abaixo poderiam estar medindo outra coisa."""

    def test_a_assinatura_do_lider_tem_a_lacuna_que_delata_a_coroa(self, calibracao):
        assinatura = calibracao.assinaturas[0]

        assert _inicio_do_nome_apos_ornamento(assinatura.mascara) is not None, (
            "a assinatura do Korzis foi gravada com ele lider; sem a coroa nela "
            "este arquivo inteiro nao esta testando o caso que diz testar"
        )

    def test_as_outras_assinaturas_nao_tem_coroa(self, calibracao):
        for assinatura in calibracao.assinaturas[1:]:
            assert (
                _inicio_do_nome_apos_ornamento(assinatura.mascara) is None
            ), f"{assinatura.nome} nao era lider e nao pode ter lacuna"

    def test_o_primeiro_passe_sozinho_nao_da_conta(self, calibracao):
        """A reproducao em numero: a propria assinatura casa 0.266.

        Nao e "perto do limiar" — esta a quase meio ponto dele. Esperar nao
        resolve: a assinatura gravada nao muda, e o membro fica "Membro N"
        atravessando ate um reinicio do scanner.
        """
        vivo = mascara_de_texto(recorte_de(sem_a_coroa(calibracao.assinaturas[0])))

        pontos = _pontuar(recorte_de(vivo), calibracao.assinaturas)

        assert pontos[0] < LIMIAR_DE_CASAMENTO, (
            f"a propria assinatura casou {pontos[0]:.3f} no alinhamento "
            f"calibrado — o cenario do defeito nao se reproduziu"
        )


class TestExLiderVoltaASerReconhecido:
    """O conserto, pelo caminho de producao."""

    def test_quem_foi_calibrado_com_coroa_e_a_perdeu_volta(self, calibracao):
        vivo = recorte_de(sem_a_coroa(calibracao.assinaturas[0]))

        res = identificar_linhas({0: vivo}, calibracao.assinaturas)

        assert res[0].nome == calibracao.assinaturas[0].nome, (
            "o membro calibrado COM coroa que deixou de ser lider tem que "
            "voltar. Sem isso ele fica 'Membro N' para sempre, e a saida real "
            "dele passa calada"
        )

    @pytest.mark.parametrize("margem", [0, 1, 2])
    def test_o_alinhamento_respeita_a_margem_do_recorte(self, calibracao, margem):
        """Vizinhos de fronteira, como no sentido ja coberto.

        Um nome sem coroa comeca na coluna 0, 1 ou 2 conforme o nome — medido na
        fixture. Ancorar na coluna 0 estaria errado por ate 2 px, e 1 px ja
        derruba a correlacao de 1.000 para 0.24. O deslocamento e medido contra
        a primeira coluna DO RECORTE.
        """
        vivo = recorte_de(sem_a_coroa(calibracao.assinaturas[0], margem))

        res = identificar_linhas({0: vivo}, calibracao.assinaturas)

        assert res[0].nome == calibracao.assinaturas[0].nome, (
            f"quebrou com o nome comecando na coluna {margem}"
        )

    def test_as_outras_linhas_continuam_como_estavam(self, calibracao):
        """Controle: o passe novo nao pode mexer em quem ja estava certo."""
        vivos = {0: recorte_de(sem_a_coroa(calibracao.assinaturas[0]))}
        for i, assinatura in enumerate(calibracao.assinaturas[1:], start=1):
            vivos[i] = recorte_de(assinatura.mascara)

        res = identificar_linhas(vivos, calibracao.assinaturas)

        assert [res[i].nome for i in range(4)] == calibracao.nomes


class TestAsTravasDoSentidoNovo:
    """As mesmas quatro travas do sentido ja coberto, exigidas de novo.

    Elas nao sao herdadas: sao codigo novo, e um passe adicional sem elas e
    exatamente o casamento deslizante que foi removido por trocar silencio por
    nome errado.
    """

    def test_ex_lider_de_fora_da_lista_nao_ganha_nome_emprestado(self, calibracao):
        """Parties de verdade tem gente que nao esta na calibracao."""
        vivo = recorte_de(sem_a_coroa(calibracao.assinaturas[0]))
        sem_o_dono = list(calibracao.assinaturas[1:])

        res = identificar_linhas({0: vivo}, sem_o_dono)

        assert res[0].nome is None, (
            f"um estranho ganhou o nome {res[0].nome!r} — trocamos um silencio "
            f"por uma mentira plausivel"
        )

    def test_assinatura_sem_coroa_nem_entra_neste_sentido(self, calibracao):
        """A trava que faz quase todo o trabalho, e de graca.

        Se NENHUMA assinatura tem lacuna, nao ha ornamento para descontar e o
        passe nem comeca. Medido em 10 assinaturas reais de 3 calibracoes: 9 sao
        bloco unico, e a unica que se parte em dois e a do lider.
        """
        vivo = mascara_de_texto(recorte_de(sem_a_coroa(calibracao.assinaturas[0])))

        assert (
            _pontuar_sem_o_ornamento_da_assinatura(vivo, calibracao.assinaturas[1:])
            is None
        )

    def test_so_desconta_o_ornamento_para_a_ESQUERDA(self, calibracao):
        """Tirar uma coroa so pode puxar o nome para tras. Nunca empurrar.

        Sem esta trava, uma assinatura cujo nome comeca ANTES do nome no recorte
        seria testada num alinhamento invertido — um alinhamento que a coroa nao
        produz, e portanto pura chance extra de erro. Mesmo raciocinio que tirou
        o casamento deslizante.
        """
        assinatura = calibracao.assinaturas[0]
        depois_da_coroa = _inicio_do_nome_apos_ornamento(assinatura.mascara)

        para_a_esquerda = _reancorar_a_assinatura_sem_ornamento(
            assinatura, depois_da_coroa - 5
        )
        na_mesma_coluna = _reancorar_a_assinatura_sem_ornamento(
            assinatura, depois_da_coroa
        )
        para_a_direita = _reancorar_a_assinatura_sem_ornamento(
            assinatura, depois_da_coroa + 3
        )

        assert para_a_esquerda is not None
        assert na_mesma_coluna is None, "deslocamento zero nao e ornamento"
        assert para_a_direita is None, "tirar a coroa nunca empurra o nome"

    def test_o_deslocamento_leva_o_nome_para_onde_o_recorte_o_mostra(
        self, calibracao
    ):
        """O alinhamento sai dos pixels, e nao de uma constante escrita a mao.

        Depois de descontada a coroa, a primeira coluna de texto da assinatura
        tem de cair exatamente na primeira coluna de texto do recorte.
        """
        assinatura = calibracao.assinaturas[0]
        for margem in (0, 1, 2):
            vivo = sem_a_coroa(assinatura, margem)
            coluna_do_recorte = _primeira_coluna_com_texto(vivo)

            molde = _reancorar_a_assinatura_sem_ornamento(
                assinatura, coluna_do_recorte
            )

            assert _primeira_coluna_com_texto(molde) == coluna_do_recorte

    def test_este_sentido_nunca_RENOMEIA_uma_linha_ja_resolvida(self, calibracao):
        """"Estritamente aditivo" tambem aqui.

        O cenario: o membro ja foi RECALIBRADO depois de perder a coroa, entao o
        primeiro passe resolve a linha dele com a assinatura nova, no alinhamento
        calibrado. A assinatura ANTIGA, com a coroa, continua por ai sob outro
        nome — e pelo sentido novo ela casaria 1.000 nessa mesma linha.

        Se o segundo passe pudesse reescrever, ele trocaria um nome CERTO por um
        errado com confianca maxima. E o defeito que este projeto trata como o
        pior de todos, e a razao de o passe so poder preencher vazio.
        """
        dono = calibracao.assinaturas[0]
        vivo = sem_a_coroa(dono)
        de_hoje = Assinatura(nome=dono.nome, mascara=vivo)
        antiga_com_coroa = Assinatura(nome="Intruso", mascara=dono.mascara)

        res = identificar_linhas(
            {0: recorte_de(vivo)}, [de_hoje, antiga_com_coroa]
        )

        assert res[0].nome == dono.nome, (
            f"a linha ja estava resolvida e virou {res[0].nome!r} — o segundo "
            f"passe so pode preencher vazio, nunca reescrever"
        )

    def test_duas_linhas_nunca_recebem_a_mesma_assinatura(self, calibracao):
        """Unicidade: duas linhas sao duas pessoas diferentes.

        Foi o mesmo nome em duas linhas que rendeu 52 eventos falsos em 25
        minutos. Aqui as duas linhas mostram o MESMO ex-lider, o que no jogo nao
        acontece — e por isso mesmo e o cenario que revela se a assinatura volta
        para a mesa depois de consumida.
        """
        vivo = recorte_de(sem_a_coroa(calibracao.assinaturas[0]))

        res = identificar_linhas({0: vivo, 1: vivo.copy()}, calibracao.assinaturas)

        nomes = [res[i].nome for i in (0, 1) if res[i].nome]
        assert len(nomes) == len(set(nomes)), (
            f"a mesma assinatura ganhou duas linhas: {nomes}"
        )

    def test_com_o_recorte_sujo_o_ex_lider_some_mas_nunca_vira_outro(
        self, calibracao
    ):
        """O modo de falha certo e o silencio, nao o nome errado."""
        limpo = recorte_de(sem_a_coroa(calibracao.assinaturas[0]))
        gerador = np.random.default_rng(17)
        esperados = (None, calibracao.assinaturas[0].nome)

        for ruido in (5, 10, 20, 30, 60):
            for _ in range(20):
                sujo = limpo.copy()
                ys = gerador.integers(0, sujo.shape[0], ruido)
                xs = gerador.integers(0, sujo.shape[1], ruido)
                sujo[ys, xs] = 255

                res = identificar_linhas({0: sujo}, calibracao.assinaturas)

                assert res[0].nome in esperados, (
                    f"com {ruido}px de ruido a linha virou {res[0].nome!r} — "
                    f"trocamos silencio por mentira"
                )

    def test_pontuacao_fraca_nao_passa_so_por_estar_sozinha(self, calibracao):
        """O limiar tem de barrar sozinho, sem depender da margem.

        Um candidato unico tem margem enorme por construcao. Se o limiar nao
        barrasse, "e o unico parecido" viraria prova suficiente.
        """
        gerador = np.random.default_rng(23)
        com_coroa = calibracao.assinaturas[0].mascara
        meio_apagado = com_coroa.copy()
        acesos = np.argwhere(meio_apagado > 0)
        escolhidos = gerador.choice(len(acesos), len(acesos) // 2, replace=False)
        for y, x in acesos[escolhidos]:
            meio_apagado[y, x] = 0

        assinaturas = [Assinatura(nome="Korzis", mascara=meio_apagado)]
        vivo = sem_a_coroa(calibracao.assinaturas[0])
        (pontuou,) = _pontuar_sem_o_ornamento_da_assinatura(vivo, assinaturas)

        assert pontuou < LIMIAR_DO_ORNAMENTO, (
            f"pontuou {pontuou:.3f}, refaca o cenario"
        )

        res = identificar_linhas({0: recorte_de(vivo)}, assinaturas)

        assert res[0].nome is None, (
            f"casou {pontuou:.3f} sendo o unico candidato — o limiar de "
            f"{LIMIAR_DO_ORNAMENTO} tem que barrar por conta propria"
        )


def _carregar(nome: str) -> dict:
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


@pytest.fixture
def assinaturas_do_incidente() -> list[Assinatura]:
    """As quatro assinaturas REAIS do usuario em 2026-09-01.

    Welazkez era LIDER quando calibrou, entao a coroa esta gravada na
    assinatura dele. Os outros tres nao eram.
    """
    dados = _carregar("incidente_2026-09-01_assinaturas.json")
    return [Assinatura.de_dict(d) for d in dados["assinaturas"]]


@pytest.fixture
def welazkez_sem_coroa() -> np.ndarray:
    """A mascara REAL do Welazkez depois que ele deixou de ser lider.

    Nao e fabricada: e o recorte que o aprendiz gravou no acervo do usuario
    (chave aee450..., confianca 0.2928) quando o reconhecimento falhou.
    """
    dados = _carregar("incidente_2026-09-01_welazkez_sem_coroa.json")
    return Assinatura.de_dict(dados).mascara


class TestACoroaRealTemLacunaMaisEstreitaQueAFixture:
    """A regressao de 2026-09-01: o sentido inverso nao dispara em campo.

    O servidor caiu, a party foi remontada, e o Welazkez virou "Membro 2"
    apesar de calibrado. Os outros tres casaram. O aprendiz entao gravou uma
    duplicata ANONIMA dele — que, quando ele deixasse a lideranca, sequestraria
    a linha e deixaria o nome orfao para sempre.

    O CONSERTO DE 2026-08-31 NAO PEGA ESTE CASO, e o motivo e um numero:

        assinatura do Korzis (fixture)   coroa, LACUNA DE 4 colunas em branco
        assinatura do Welazkez (campo)   coroa, LACUNA DE 3 colunas em branco

    `_inicio_do_nome_apos_ornamento` cobra `diff > COLUNAS_DE_LACUNA_DO_ORNAMENTO`,
    e `diff` e "colunas em branco + 1". Com a constante em 4 ele exige 4 brancos.
    A fixture tem exatamente 4 e passa raspando; a coroa real do usuario tem 3 e
    e lida como "sem ornamento". O sentido inverso nem comeca.

    A CORRELACAO PROVA QUE E A MESMA PESSOA. Deslocando a assinatura calibrada
    para a esquerda, medido contra este recorte:

         0 px -> 0.1843    12 px -> 0.2098
         2 px -> 0.2645    14 px -> 0.3245
         4 px -> 0.2124    16 px -> 0.3187
         6 px -> 0.2342    18 px -> 0.2901
         8 px -> 0.2697    19 px -> 0.9667   <<<
        10 px -> 0.2755    20 px -> 0.3015
                           24 px -> 0.3428

    E 19 e exatamente onde a lacuna manda ancorar: coroa em 2..15, brancos em
    16..18, nome a partir de 19.

    E O PICO SER AGUDO E A SEGURANCA DO CONSERTO. 0.9667 no 19 e ~0.3 em TODOS
    os 29 vizinhos medidos significa que baixar a exigencia de lacuna nao abre
    porta para mentira: um ornamento lido onde nao ha produz um alinhamento
    qualquer, e um alinhamento qualquer pontua ~0.3, recusado com folga pelo
    limiar de 0.85 do segundo passe. O que muda nao e a chance de acertar
    errado, e a chance de sequer TENTAR quando ha o que acertar.
    """

    def test_a_assinatura_real_do_welazkez_tem_a_lacuna_da_coroa(
        self, assinaturas_do_incidente
    ):
        """O discriminador, no pixel real: coroa 2..15, brancos 16..18, nome 19."""
        welazkez = assinaturas_do_incidente[0]
        assert welazkez.nome == "Welazkez"

        assert _inicio_do_nome_apos_ornamento(welazkez.mascara) == 19, (
            "a coroa real do usuario tem 3 colunas em branco, nao 4 como a da "
            "fixture. Lida como 'sem ornamento', ela desliga o sentido inverso "
            "inteiro e o membro fica 'Membro N' para sempre"
        )

    def test_as_outras_tres_assinaturas_continuam_sem_ornamento(
        self, assinaturas_do_incidente
    ):
        """A trava que faz quase todo o trabalho nao pode afrouxar junto.

        Se baixar a exigencia de lacuna passasse a ver coroa em quem nao tem, o
        segundo passe deixaria de ser a excecao rara que ele e.
        """
        for assinatura in assinaturas_do_incidente[1:]:
            assert _inicio_do_nome_apos_ornamento(assinatura.mascara) is None, (
                f"{assinatura.nome} nao era lider e nao pode ter lacuna de coroa"
            )

    def test_o_recorte_sem_coroa_nao_e_lido_como_tendo_uma(self, welazkez_sem_coroa):
        """O outro sentido nao pode se intrometer neste caso.

        Se o recorte ao vivo fosse lido como "tem ornamento", entrariamos pelo
        sentido errado e a linha ganharia um alinhamento que a coroa nunca
        produziu.
        """
        assert _inicio_do_nome_apos_ornamento(welazkez_sem_coroa) is None

    def test_o_primeiro_passe_sozinho_erra_a_pessoa(
        self, welazkez_sem_coroa, assinaturas_do_incidente
    ):
        """A reproducao em numero, e ela e pior do que "nao reconheceu".

        Medido: 0.1843 contra a PROPRIA assinatura e 0.2928 contra a Mostarda.
        No alinhamento calibrado o Welazkez se parece MENOS com ele mesmo do que
        com outra pessoa. So o limiar de 0.75 impede isso de virar alerta com o
        nome errado.
        """
        pontos = _pontuar(recorte_de(welazkez_sem_coroa), assinaturas_do_incidente)

        assert pontos[0] < LIMIAR_DE_CASAMENTO
        assert max(pontos) > pontos[0], (
            "o cenario nao se reproduziu: aqui a propria assinatura tem de ser "
            "PIOR que a de outra pessoa"
        )

    def test_o_welazkez_real_volta_a_ser_reconhecido(
        self, welazkez_sem_coroa, assinaturas_do_incidente
    ):
        """O conserto, pelo caminho de producao e com os pixels do incidente."""
        res = identificar_linhas(
            {0: recorte_de(welazkez_sem_coroa)}, assinaturas_do_incidente
        )

        assert res[0].nome == "Welazkez", (
            f"casou {res[0].nome!r} com {res[0].confianca:.4f}. Sem isto o "
            f"aprendiz grava uma duplicata ANONIMA de quem JA TEM NOME, e "
            f"quando ele deixar a lideranca a duplicata sequestra a linha: "
            f"'Membro N' para sempre e o nome orfao"
        )

    def test_o_reconhecimento_nao_e_sorte_de_alinhamento(
        self, welazkez_sem_coroa, assinaturas_do_incidente
    ):
        """O pico e agudo, e por isso um ornamento lido errado nao mente.

        Um pixel para o lado e a correlacao desaba de 0.9667 para ~0.30, muito
        abaixo do limiar de 0.85 do segundo passe. E isso que autoriza baixar a
        exigencia de lacuna sem devolver as chances extras de falso positivo que
        o `.max()` deslizante produzia.
        """
        welazkez = assinaturas_do_incidente[0].mascara
        vizinhos = []
        for k in range(0, 30):
            if k == 19:
                continue
            largura = welazkez.shape[1] - k
            deslocada = np.zeros_like(welazkez)
            deslocada[:, :largura] = welazkez[:, k:]
            vizinhos.append(_correlacionar(welazkez_sem_coroa, deslocada))

        assert max(vizinhos) < LIMIAR_DO_ORNAMENTO, (
            f"o melhor vizinho pontuou {max(vizinhos):.4f} — se um alinhamento "
            f"errado chegasse ao limiar, o argumento de seguranca deste "
            f"conserto cairia"
        )
