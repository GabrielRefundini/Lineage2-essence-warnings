"""Tirar do acervo o que nunca deveria ter entrado.

O QUE FALTAVA, E O QUE ISSO CUSTOU

Ate aqui o acervo era de mao unica. `acervo.py` diz "NAO tem poda, de
proposito", `batismo.py` diz "nao existe comando de esquecer uma assinatura" na
propria recusa de nome ocupado, e `sessao.py` justificava o portao da cegueira
com "a gravacao e IRREVERSIVEL". Tres modulos escreveram a mesma frase, e ela
era verdade.

MEDIDO NA PASTA REAL DO USUARIO EM 2026-08-31: 11 assinaturas conhecidas, 6 sem
nome, e o arranque avisando que 7 delas foram gravadas com a regiao de nome
20x100 quando a atual e 20x110 (elas nao podem casar com nada, e aquelas
pessoas aparecem como Membro N para sempre). Renderizando as mascaras
apareceram tambem "Show Options", texto de UI e duas capturas contaminadas com
"Kills: 4 Deaths" por cima do nome.

ESQUECER E RENOMEAR, NUNCA APAGAR

A leitura do acervo so aceita `assinatura_<64 hex>.json`
(`AcervoDeIdentidades._chave_do_nome`), entao trocar o prefixo ja tira a entrada
de circulacao. Um `unlink` numa pasta sem backup, comandado pelo WhatsApp,
seria a unica operacao verdadeiramente irreversivel deste projeto, que nasceu
inteiro da premissa de preferir o desfecho recuperavel.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pytest

from l2scanner.acervo import (
    PREFIXO_ASSINATURA,
    PREFIXO_ESQUECIDA,
    PREFIXO_NOME,
    PREFIXO_NOME_ESQUECIDO,
    AcervoDeIdentidades,
    chave_da_assinatura,
    fora_de_forma,
)
from l2scanner.batismo import apelido_da_chave
from l2scanner.comandos import (
    _AJUDA,
    COMANDOS_DE_MEMBRO,
    Comando,
    comandos_novos,
    interpretar_dinamico,
)
from l2scanner.esquecimento import (
    PALAVRA_DO_LOTE,
    PedidoDeEsquecimento,
    RespostaDoEsquecimento,
    interpretar_esquecimento,
    responder_esquecimento,
)
from l2scanner.identidade import Assinatura

RAIZ = Path(__file__).resolve().parent.parent

# A forma da regiao de nome de HOJE, e a de ONTEM. Os dois pares sao os
# MEDIDOS na maquina do usuario: `nome_largura` passou de 100 para 110 e
# aposentou de uma vez as 7 assinaturas que ele ja tinha.
FORMA_DE_HOJE = (20, 110)
FORMA_DE_ONTEM = (20, 100)


def assinatura_de(semente: int, forma=FORMA_DE_HOJE, nome: str = "") -> Assinatura:
    """Uma mascara determinstica e distinta por semente.

    O conteudo importa: a chave E o sha256 do material da mascara, entao duas
    sementes diferentes tem de dar duas chaves diferentes.
    """
    mascara = np.zeros(forma, dtype=np.uint8)
    plana = mascara.reshape(-1)
    # Um padrao esparso e dependente da semente. `+ 3` para nenhuma mascara
    # sair vazia, e passo primo para sementes vizinhas nao se sombrearem.
    plana[semente + 3 :: 7] = 1
    plana[semente] = 1
    return Assinatura(nome=nome, mascara=mascara)


def semear(pasta: Path, assinatura: Assinatura, nome: str | None = None) -> str:
    """Escreve uma entrada A MAO, sem passar por caminho de escrita nenhum.

    Mesmo helper (e mesma razao) de `tests/test_acervo.py`: o criterio e que
    uma entrada POSTA A MAO se comporte certo.
    """
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


@pytest.fixture
def pasta(tmp_path) -> Path:
    """SEMPRE em `tmp_path`. A `.identidades/` do usuario tem dados reais."""
    return tmp_path / ".identidades"


@pytest.fixture
def acervo(pasta) -> AcervoDeIdentidades:
    return AcervoDeIdentidades(pasta)


# ---------------------------------------------------------------------------
# A GRAMATICA
# ---------------------------------------------------------------------------


class TestAGramatica:
    """Uma gramatica so, que valida na INTERPRETACAO e le no RESPONDER.

    Precedente exato do `interpretar_pegou` e do `interpretar_batismo`, com a
    razao ja escrita neles: duas gramaticas divergiriam no primeiro ajuste e o
    comando passaria a aceitar o que nao executa.
    """

    def test_um_apelido_hex_e_um_pedido_de_uma_entrada(self):
        assert interpretar_esquecimento("6288ee") == PedidoDeEsquecimento(
            apelido="6288ee"
        )

    def test_o_apelido_e_normalizado_para_minusculo(self):
        """As chaves do acervo sao hex MINUSCULO.

        Quem copia `6288EE` de algum lugar continua sendo atendido, e isso nao
        alarga o charset em um caractere.
        """
        assert interpretar_esquecimento("6288EE").apelido == "6288ee"

    def test_a_palavra_do_lote_e_um_pedido_de_lote(self):
        assert interpretar_esquecimento(PALAVRA_DO_LOTE) == PedidoDeEsquecimento(
            lote=True
        )

    def test_a_palavra_do_lote_nao_pode_ser_confundida_com_apelido(self):
        """Ela tem letras fora do hex, entao a separacao e ESTRUTURAL.

        Nao ha desempate a fazer entre "isto e um prefixo de chave" e "isto e a
        palavra do lote": nenhuma chave hex jamais comeca por `fora-de-forma`.
        """
        assert not set(PALAVRA_DO_LOTE) <= set("0123456789abcdef")

    def test_sem_argumento_nao_e_pedido_nenhum(self):
        """Um `/esquecer` pelado nao pode virar "esqueca alguma coisa"."""
        for argumento in (None, "", "   "):
            assert interpretar_esquecimento(argumento) is None, repr(argumento)

    def test_duas_palavras_nao_sao_pedido(self):
        """`/esquecer 6288ee TITANDER` e recusado, e nao lido pela metade."""
        assert interpretar_esquecimento("6288ee TITANDER") is None
        assert interpretar_esquecimento(f"{PALAVRA_DO_LOTE} tudo") is None

    def test_o_que_nao_e_hex_nem_a_palavra_do_lote_e_recusado(self):
        """`/esquecer linha3` e `/esquecer tudo` nao alcancam nada.

        A trava contra "esqueca a linha 3" e uma AUSENCIA, exatamente como em
        `batismo.py`: nao existe sintaxe que alcance uma posicao, entao "3" e
        so um prefixo hex que nao casa chave nenhuma, e "linha3" nem hex e.
        """
        for argumento in ("linha3", "tudo", "todas", "TITANDER", "-"):
            assert interpretar_esquecimento(argumento) is None, argumento


# ---------------------------------------------------------------------------
# O DISCO: RENOMEIA, NUNCA APAGA
# ---------------------------------------------------------------------------


class TestOAcervoRenomeiaEmVezDeApagar:
    def test_a_entrada_sai_de_circulacao(self, acervo, pasta):
        chave = semear(pasta, assinatura_de(1))
        assert acervo.chaves() == [chave], "premissa: ela estava no acervo"

        assert acervo.esquecer(chave) == "esquecida"

        assert acervo.chaves() == [], "a entrada continua sendo lida"

    def test_o_arquivo_CONTINUA_no_disco_com_outro_nome(self, acervo, pasta):
        chave = semear(pasta, assinatura_de(1))
        antes = (pasta / f"{PREFIXO_ASSINATURA}{chave}.json").read_text(
            encoding="utf-8"
        )

        acervo.esquecer(chave)

        morto = pasta / f"{PREFIXO_ESQUECIDA}{chave}.json"
        assert morto.exists(), (
            "esquecer nao pode APAGAR: um unlink comandado pelo WhatsApp numa "
            "pasta sem backup e a unica operacao irreversivel deste projeto"
        )
        assert morto.read_text(encoding="utf-8") == antes, (
            "o conteudo tem de sobreviver intacto, senao a volta a mao nao "
            "reconstroi a mesma assinatura"
        )
        assert not (pasta / f"{PREFIXO_ASSINATURA}{chave}.json").exists()

    def test_renomear_de_volta_a_mao_RESSUSCITA_a_entrada(self, acervo, pasta):
        """A promessa da resposta, provada e nao so escrita.

        A resposta diz ao usuario para renomear de volta. Se isso nao
        funcionasse, a mensagem seria a mentira mais cara do recurso: ela diria
        que ha volta onde nao ha.
        """
        chave = semear(pasta, assinatura_de(1), nome="TITANDER")
        acervo.esquecer(chave)
        assert acervo.chaves() == []

        (pasta / f"{PREFIXO_ESQUECIDA}{chave}.json").rename(
            pasta / f"{PREFIXO_ASSINATURA}{chave}.json"
        )
        (pasta / f"{PREFIXO_NOME_ESQUECIDO}{chave}").rename(
            pasta / f"{PREFIXO_NOME}{chave}"
        )

        assert acervo.chaves() == [chave]
        assert acervo.nomeados() == {chave: "TITANDER"}

    def test_o_irmao_do_nome_vai_junto(self, acervo, pasta):
        """Sem isso, aprender a MESMA mascara de novo ressuscitaria o nome.

        A chave e o hash do conteudo: um recorte identico produz a mesma chave,
        e um `nome_<chave>` deixado para tras colaria o nome antigo na entrada
        nova sem ninguem ter batizado nada.
        """
        chave = semear(pasta, assinatura_de(1), nome="TITANDER")

        acervo.esquecer(chave)

        assert not (pasta / f"{PREFIXO_NOME}{chave}").exists()
        renomeado = pasta / f"{PREFIXO_NOME_ESQUECIDO}{chave}"
        assert renomeado.exists(), "o nome tambem tem de ser recuperavel"
        assert renomeado.read_text(encoding="utf-8") == "TITANDER"

    def test_uma_entrada_sem_nome_nao_precisa_de_irmao(self, acervo, pasta):
        chave = semear(pasta, assinatura_de(1))
        assert acervo.esquecer(chave) == "esquecida"
        assert not (pasta / f"{PREFIXO_NOME_ESQUECIDO}{chave}").exists()

    def test_esquecer_o_que_nao_existe_e_AUSENTE_e_nao_falha(self, acervo, pasta):
        """Os dois desfechos precisam ser distinguiveis por quem responde.

        "ja nao estava la" e uma resposta tranquila; "nao consegui mexer no
        disco" pede que o usuario tente de novo. Colapsar os dois faria uma
        falha de disco parecer sucesso.
        """
        semear(pasta, assinatura_de(1))
        ausente = "0" * 64
        assert acervo.esquecer(ausente) == "ausente"

    def test_chave_torta_e_recusada_por_construcao(self, acervo, pasta):
        """A mesma trava estrutural do `nomear` e do `marcar_pergunta`.

        Um nome de arquivo que nao seja hex puro nunca vira caminho, entao
        travessia de diretorio e impossivel por construcao e nao por vigilancia
        de quem chama.
        """
        semear(pasta, assinatura_de(1))
        for torta in ("../../etc/passwd", "nome_x", "ABC", "", "6288ee"):
            assert acervo.esquecer(torta) == "invalido", torta

    def test_a_segunda_vez_na_MESMA_chave_e_ausente(self, acervo, pasta):
        chave = semear(pasta, assinatura_de(1))
        assert acervo.esquecer(chave) == "esquecida"
        assert acervo.esquecer(chave) == "ausente"

    def test_as_vizinhas_nao_sao_tocadas(self, acervo, pasta):
        alvo = semear(pasta, assinatura_de(1))
        vizinhas = [semear(pasta, assinatura_de(s)) for s in (2, 3, 4)]

        acervo.esquecer(alvo)

        assert acervo.chaves() == sorted(vizinhas)

    def test_o_marcador_de_pergunta_FICA(self, acervo, pasta):
        """D-04 continua valendo: uma pergunta por assinatura, para sempre.

        A entrada esquecida e, na maioria dos casos, lixo. Se a mesma mascara
        reaparecer, ela produz a MESMA chave, e apagar o marcador aqui faria o
        scanner voltar a perguntar quem e a janela do navegador. Perguntar de
        novo sobre o que o usuario acabou de mandar esquecer e o contrario do
        que ele pediu.
        """
        chave = semear(pasta, assinatura_de(1))
        assert acervo.marcar_pergunta(chave) is True

        acervo.esquecer(chave)

        assert acervo.marcar_pergunta(chave) is False, (
            "o marcador nao pode ser consumido de novo"
        )

    def test_a_simulacao_NAO_encosta_no_disco(self, tmp_path):
        """O `--dry-run` roda sobre a `.identidades/` COMPARTILHADA.

        Em `--dry-run` o despachante e de CONSOLE, real e vivo: a simulacao
        OUVE comandos de verdade. Sem este portao, um `/esquecer` digitado
        enquanto uma simulacao roda ao lado do scanner de verdade tiraria de
        circulacao a entrada do scanner de verdade. E o incidente de
        2026-08-26 19:30 (a simulacao disputando a chave do aviso de TvT),
        agora com uma operacao destrutiva no lugar do aviso.
        """
        pasta = tmp_path / ".identidades"
        chave = semear(pasta, assinatura_de(1), nome="TITANDER")
        simulado = AcervoDeIdentidades(pasta, simulando=True)

        assert simulado.esquecer(chave) == "simulado"

        assert (pasta / f"{PREFIXO_ASSINATURA}{chave}.json").exists()
        assert (pasta / f"{PREFIXO_NOME}{chave}").exists()
        assert not (pasta / f"{PREFIXO_ESQUECIDA}{chave}.json").exists()


# ---------------------------------------------------------------------------
# UMA ENTRADA, PELO APELIDO CURTO
# ---------------------------------------------------------------------------


class TestUmaEntradaPeloApelido:
    def test_o_apelido_curto_alcanca_a_entrada(self, acervo, pasta):
        chave = semear(pasta, assinatura_de(1))

        resposta = responder_esquecimento(acervo, apelido_da_chave(chave))

        assert isinstance(resposta, RespostaDoEsquecimento)
        assert acervo.chaves() == []
        assert apelido_da_chave(chave) in resposta.privado

    def test_a_resposta_diz_o_QUE_saiu_QUANTAS_ficaram_e_COMO_voltar(
        self, acervo, pasta
    ):
        """Os tres pedacos obrigatorios da confirmacao.

        Sem o "quantas ficaram" o usuario nao sabe se o lote seguinte ainda faz
        sentido; sem o "como voltar" a promessa de recuperabilidade e so uma
        frase de release note.
        """
        alvo = semear(pasta, assinatura_de(1), nome="TITANDER")
        for semente in (2, 3, 4):
            semear(pasta, assinatura_de(semente))

        resposta = responder_esquecimento(acervo, apelido_da_chave(alvo))
        texto = resposta.privado

        assert apelido_da_chave(alvo) in texto
        assert "TITANDER" in texto, "quem tinha nome merece ser citado pelo nome"
        assert "3" in texto, "a resposta tem de dizer quantas sobraram"
        assert f"{PREFIXO_ESQUECIDA}{alvo}.json" in texto, (
            "a recuperacao e manual, entao a resposta tem de dizer o NOME DO "
            "ARQUIVO. Sem ele a instrucao nao pode ser seguida"
        )
        assert f"{PREFIXO_ASSINATURA}{alvo}.json" in texto, (
            "e o nome para o qual renomear de volta"
        )

    def test_a_resposta_de_uma_entrada_NAO_ecoa_no_grupo(self, acervo, pasta):
        """O contraste com o `/batizar` e deliberado.

        O batismo ecoa porque a PERGUNTA foi publica: deixa-la pendurada no
        grupo faria o proximo party-mate tentar responder e cair no `continue`
        da autorizacao, sem resposta. Esquecer nao responde pergunta nenhuma,
        e o grupo nao tem o que fazer com a informacao de que uma assinatura
        saiu de circulacao.
        """
        chave = semear(pasta, assinatura_de(1))
        resposta = responder_esquecimento(acervo, apelido_da_chave(chave))
        assert resposta.grupo is None

    def test_um_apelido_ambiguo_e_RECUSADO_com_a_lista(self, acervo, pasta):
        """Nunca desempatar. Aqui a razao pesa mais que no batismo.

        Um desempate errado no batismo cola o nome na pessoa errada; aqui ele
        tira de circulacao a assinatura da pessoa errada, e o usuario so
        descobre quando ela virar "Membro N" no meio de um farm.
        """
        chaves = sorted(
            chave_da_assinatura(assinatura_de(s)) for s in range(1, 60)
        )
        comuns = [
            (a, b)
            for a, b in zip(chaves, chaves[1:])
            if a[:1] == b[:1]
        ]
        assert comuns, "premissa: ha duas chaves que comecam igual"
        prefixo = comuns[0][0][:1]
        for semente in range(1, 60):
            semear(pasta, assinatura_de(semente))
        quantas = len(acervo.chaves())

        resposta = responder_esquecimento(acervo, prefixo)

        assert len(acervo.chaves()) == quantas, "nada pode ter saido"
        assert "mais de uma" in resposta.privado.lower()
        assert resposta.grupo is None

    def test_um_apelido_desconhecido_nao_esquece_nada(self, acervo, pasta):
        semear(pasta, assinatura_de(1))
        resposta = responder_esquecimento(acervo, "ffffff")
        assert len(acervo.chaves()) == 1
        assert "ffffff" in resposta.privado

    def test_a_gramatica_torta_e_recusada_com_a_forma_certa(self, acervo, pasta):
        semear(pasta, assinatura_de(1))
        resposta = responder_esquecimento(acervo, "6288ee TITANDER")
        assert len(acervo.chaves()) == 1
        assert "/esquecer" in resposta.privado


# ---------------------------------------------------------------------------
# A LISTA VIVA
# ---------------------------------------------------------------------------


class TestSaiDoReconhecimentoVivo:
    """O analogo do que o `/batizar` ja faz (D-08), na direcao contraria."""

    def test_a_esquecida_sai_da_lista_viva_no_mesmo_tick(self, acervo, pasta):
        alvo = assinatura_de(1)
        outra = assinatura_de(2)
        chave = semear(pasta, alvo)
        semear(pasta, outra)
        vivas = [alvo, outra]

        responder_esquecimento(
            acervo, apelido_da_chave(chave), assinaturas_vivas=vivas
        )

        assert [chave_da_assinatura(a) for a in vivas] == [
            chave_da_assinatura(outra)
        ], (
            "sem esta remocao o disco esqueceu e a tela continua reconhecendo "
            "ate o proximo arranque, e o usuario manda o comando de novo"
        )

    def test_a_lista_viva_e_mutada_NO_LUGAR(self, acervo, pasta):
        """Quem le e o `extrair` do proximo tick, pela MESMA referencia.

        Trocar por uma lista nova aqui dentro deixaria `cal.assinaturas`
        apontando para a antiga, e o comando pareceria nao ter efeito nenhum.
        """
        alvo = assinatura_de(1)
        chave = semear(pasta, alvo)
        vivas = [alvo]
        mesma = vivas

        responder_esquecimento(
            acervo, apelido_da_chave(chave), assinaturas_vivas=vivas
        )

        assert mesma is vivas
        assert mesma == []

    def test_sem_lista_viva_nada_levanta(self, acervo, pasta):
        """O laco da agenda nao tem tela, entao nao tem lista viva (T-03-07)."""
        chave = semear(pasta, assinatura_de(1))
        resposta = responder_esquecimento(acervo, apelido_da_chave(chave))
        assert acervo.chaves() == []
        assert resposta.privado


# ---------------------------------------------------------------------------
# O LOTE
# ---------------------------------------------------------------------------


class TestOLote:
    """Sete comandos no celular e pedir para o usuario desistir.

    Mas um lote e a unica sintaxe deste projeto que atinge N entradas com uma
    frase, entao a mira dele nao pode ser "tudo": ela e exatamente o que a
    geometria de agora ja provou morto.
    """

    def _pasta_mista(self, pasta) -> tuple[list[str], list[str]]:
        """Tres fora de forma (largura 100) e duas na forma de hoje (110)."""
        mortas = [
            semear(pasta, assinatura_de(s, forma=FORMA_DE_ONTEM))
            for s in (1, 2, 3)
        ]
        vivas = [
            semear(pasta, assinatura_de(s, forma=FORMA_DE_HOJE)) for s in (4, 5)
        ]
        return mortas, vivas

    def test_o_lote_alcanca_SO_as_fora_de_forma(self, acervo, pasta):
        mortas, vivas = self._pasta_mista(pasta)

        responder_esquecimento(
            acervo, PALAVRA_DO_LOTE, forma_esperada=FORMA_DE_HOJE
        )

        assert sorted(acervo.chaves()) == sorted(vivas), (
            "o lote nao pode encostar em quem ainda casa com a geometria de "
            "agora: essas sao as pessoas que o scanner reconhece hoje"
        )
        for chave in mortas:
            assert (pasta / f"{PREFIXO_ESQUECIDA}{chave}.json").exists()

    def test_a_resposta_do_lote_diz_quantas_sairam_e_quantas_ficaram(
        self, acervo, pasta
    ):
        mortas, vivas = self._pasta_mista(pasta)

        resposta = responder_esquecimento(
            acervo, PALAVRA_DO_LOTE, forma_esperada=FORMA_DE_HOJE
        )
        texto = resposta.privado

        assert "3" in texto and "2" in texto
        for chave in mortas:
            assert apelido_da_chave(chave) in texto, (
                "cada apelido tem de aparecer: sem eles o usuario nao tem como "
                "conferir que saiu o que ele achava que ia sair"
            )
        assert PREFIXO_ESQUECIDA in texto, "a volta a mao precisa do prefixo"
        assert resposta.grupo is None

    def test_sem_nenhuma_fora_de_forma_o_lote_nao_esquece_NADA(
        self, acervo, pasta
    ):
        """A guarda que impede o lote de virar "apague tudo"."""
        vivas = [
            semear(pasta, assinatura_de(s, forma=FORMA_DE_HOJE)) for s in (1, 2)
        ]

        resposta = responder_esquecimento(
            acervo, PALAVRA_DO_LOTE, forma_esperada=FORMA_DE_HOJE
        )

        assert sorted(acervo.chaves()) == sorted(vivas)
        assert "nenhuma" in resposta.privado.lower()

    def test_sem_saber_a_forma_de_agora_o_lote_e_RECUSADO(self, acervo, pasta):
        """O laco da agenda nao tem calibracao, entao nao sabe a geometria.

        Adivinhar aqui seria o lote escolhendo sozinho o que esta morto, e a
        escolha errada tira de circulacao gente viva. A recusa diz onde o
        comando funciona, em vez de so dizer nao.
        """
        mortas, vivas = self._pasta_mista(pasta)

        resposta = responder_esquecimento(acervo, PALAVRA_DO_LOTE)

        assert sorted(acervo.chaves()) == sorted(mortas + vivas), (
            "nada pode sair quando a geometria de agora e desconhecida"
        )
        assert "nada" in resposta.privado.lower()

    def test_o_lote_tira_as_esquecidas_da_lista_viva(self, acervo, pasta):
        mortas = [assinatura_de(s, forma=FORMA_DE_ONTEM) for s in (1, 2)]
        viva = assinatura_de(4, forma=FORMA_DE_HOJE)
        for assinatura in (*mortas, viva):
            semear(pasta, assinatura)
        vivas = [*mortas, viva]

        responder_esquecimento(
            acervo,
            PALAVRA_DO_LOTE,
            assinaturas_vivas=vivas,
            forma_esperada=FORMA_DE_HOJE,
        )

        assert [chave_da_assinatura(a) for a in vivas] == [
            chave_da_assinatura(viva)
        ]

    def test_o_que_veio_do_calibration_json_e_ANUNCIADO_e_nao_calado(
        self, acervo, pasta
    ):
        """Uma fora de forma que nao esta na pasta nao sai por aqui.

        Ela mora no `calibration.json`, que este comando nao toca por desenho:
        escrever nele desfaria pelo lado de dentro a razao de a pasta ser
        propria. Calar sobre isso deixaria o usuario esperando um efeito que
        nunca vem, que e o modo de falha que este projeto mais combate.
        """
        semear(pasta, assinatura_de(1, forma=FORMA_DE_ONTEM))
        calibrada_velha = assinatura_de(9, forma=FORMA_DE_ONTEM, nome="Mostarda")
        vivas = [calibrada_velha, assinatura_de(1, forma=FORMA_DE_ONTEM)]

        resposta = responder_esquecimento(
            acervo,
            PALAVRA_DO_LOTE,
            assinaturas_vivas=vivas,
            forma_esperada=FORMA_DE_HOJE,
        )

        assert [chave_da_assinatura(a) for a in vivas] == [
            chave_da_assinatura(calibrada_velha)
        ]
        assert "calibrar" in resposta.privado.lower(), (
            "a unica saida para uma calibrada fora de forma e recalibrar, e a "
            "resposta tem de dizer isso"
        )


# ---------------------------------------------------------------------------
# O CRITERIO DE FORMA MORA NUM LUGAR SO
# ---------------------------------------------------------------------------


class TestOCriterioDeForma:
    """Duas copias do criterio divergiriam no primeiro ajuste.

    `Identidades.fora_de_forma` conta e `Identidades.aviso_de_forma` redige; o
    lote precisa da MESMA pergunta para escolher o que sai. Uma terceira copia
    aqui faria o aviso de arranque e o comando discordarem sobre quem esta
    morto, e o usuario acreditaria no aviso.
    """

    def test_forma_diferente_e_fora_de_forma(self):
        assert fora_de_forma(assinatura_de(1, forma=FORMA_DE_ONTEM), FORMA_DE_HOJE)

    def test_forma_igual_nao_e(self):
        assert not fora_de_forma(
            assinatura_de(1, forma=FORMA_DE_HOJE), FORMA_DE_HOJE
        )

    def test_a_ALTURA_conta_tanto_quanto_a_largura(self):
        """`nome_altura` tambem e calibravel.

        Olhar so um dos lados deixaria a mesma falha silenciosa entrar pelo
        outro.
        """
        assert fora_de_forma(assinatura_de(1, forma=(21, 110)), FORMA_DE_HOJE)

    def test_sem_forma_esperada_ninguem_esta_fora(self):
        """"Ninguem disse qual e a forma" nao pode acusar nada."""
        assert not fora_de_forma(assinatura_de(1, forma=FORMA_DE_ONTEM), None)

    def test_o_aviso_de_arranque_usa_o_MESMO_criterio(self):
        """Portao de AST: `Identidades` nao pode ter uma copia da comparacao.

        Lido da arvore porque o defeito e estrutural. Uma segunda comparacao de
        `mascara.shape` dentro de `acervo.py` passaria despercebida em revisao
        e so apareceria no dia em que as duas discordassem.
        """
        fonte = (RAIZ / "l2scanner" / "acervo.py").read_text(encoding="utf-8")
        arvore = ast.parse(fonte)
        classe = next(
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.ClassDef) and no.name == "Identidades"
        )
        chamadas = {
            no.func.id
            for no in ast.walk(classe)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Name)
        }
        assert "fora_de_forma" in chamadas, (
            "Identidades tem de PERGUNTAR ao criterio unico, e nao comparar "
            "shape por conta propria"
        )


# ---------------------------------------------------------------------------
# O COMANDO E DE DONO
# ---------------------------------------------------------------------------


class TestOComandoENivelDeDono:
    TELEFONE_DO_DONO = "+5544997077000"
    TELEFONE_DO_MEMBRO = "+5544912345678"

    def _mensagem(self, texto: str, telefone: str) -> dict:
        return {
            "id": 7001,
            "content": texto,
            "message_type": 0,
            "private": False,
            "sender": {"name": "Yazalaque", "phone_number": telefone},
        }

    def test_o_comando_existe_no_enum(self):
        assert Comando.ESQUECER in set(Comando)

    def test_ele_nasce_FORA_de_COMANDOS_DE_MEMBRO(self):
        """A lista e de INCLUSAO, entao ele nasce fora sozinho.

        Este caso existe porque a razao dele ficar fora e mais forte que a do
        `/batizar`: batizar corrompe um nome, esquecer tira uma pessoa inteira
        do reconhecimento. E uma razao que so vive num comentario nao sobrevive
        ao proximo ajuste.
        """
        assert Comando.ESQUECER not in COMANDOS_DE_MEMBRO

    def test_ele_tem_linha_na_ajuda(self):
        """O tripwire `set(_AJUDA) == set(Comando)` ja cobra isto.

        Repetido aqui por nome porque a ajuda desatualizada e o modo de falha
        que ensina sintaxe que nao funciona.
        """
        assert set(_AJUDA) == set(Comando)
        linha = _AJUDA[Comando.ESQUECER]
        assert linha.familia == "Identidade"
        assert "<apelido>" in linha.sintaxe

    def test_a_forma_em_LOTE_e_ANUNCIADA(self):
        """Uma forma que existe e nao e anunciada nao existe para o usuario.

        Sao 7 entradas mortas na pasta dele hoje: sem a linha na ajuda ele
        mandaria sete comandos, ou desistiria.
        """
        linha = _AJUDA[Comando.ESQUECER]
        anunciadas = (linha.sintaxe, *linha.apelidos)
        assert any(PALAVRA_DO_LOTE in forma for forma in anunciadas), (
            f"o lote nao esta anunciado em {anunciadas}"
        )

    @pytest.mark.parametrize(
        "texto",
        [
            "/esquecer 6288ee",
            "/esquecer-6288ee",
            f"/esquecer {PALAVRA_DO_LOTE}",
            f"/esquecer-{PALAVRA_DO_LOTE}",
        ],
    )
    def test_as_quatro_formas_escritas_chegam_como_ESQUECER(self, texto):
        lido = interpretar_dinamico(texto, frozenset())
        assert lido is not None, f"{texto!r} nao virou comando nenhum"
        assert lido[0] is Comando.ESQUECER

    def test_o_dono_alcanca_pelo_caminho_real(self):
        achados = comandos_novos(
            [self._mensagem("/esquecer 6288ee", self.TELEFONE_DO_DONO)],
            set(),
            [self.TELEFONE_DO_DONO],
        )
        assert [m.comando for m in achados] == [Comando.ESQUECER]

    def test_um_party_mate_NAO_alcanca(self):
        """Pelo caminho real, com o segundo nivel de autorizacao ligado."""
        from l2scanner.comandos import Membro

        achados = comandos_novos(
            [self._mensagem("/esquecer 6288ee", self.TELEFONE_DO_MEMBRO)],
            set(),
            [self.TELEFONE_DO_DONO],
            membros=(Membro(nick="Korzis", telefone=self.TELEFONE_DO_MEMBRO),),
        )
        assert achados == [], "um party-mate esqueceu uma assinatura"


# ---------------------------------------------------------------------------
# A COSTURA COM O LACO
# ---------------------------------------------------------------------------


class DespachanteQueGrava:
    """Grava `(texto, categoria, conversa_alvo)` em vez de mandar para a rede.

    Truthy de proposito: `atender_comandos` testa `if not despachante`.
    """

    def __init__(self) -> None:
        self.despachos: list[tuple[str, object, str | None]] = []

    def despachar(self, texto, categoria=None, conversa_alvo=None) -> None:
        self.despachos.append((texto, categoria, conversa_alvo))

    @property
    def alvos(self) -> list:
        return [conversa for _, _, conversa in self.despachos]

    @property
    def textos(self) -> list:
        return [texto for texto, _, _ in self.despachos]


class LeitorDeUmaMensagem:
    """Um `LeitorDeComandos` falso que devolve UMA mensagem CRUA.

    Crua (dict, como a API do Chatwoot devolve) de proposito: as travas de
    `comandos_novos` (tipo, nota privada, id repetido, vocabulario e
    autorizacao) tem de rodar de verdade, e nao ser puladas pelo teste.
    """

    ativo = True
    DONO = "+5544997077000"

    def __init__(self, texto: str) -> None:
        self.telefones = [self.DONO]
        self.membros = []
        self._mensagem = {
            "id": 8888,
            "content": texto,
            "message_type": 0,
            "private": False,
            "sender": {"name": "Yazalaque", "phone_number": self.DONO},
            "conversation_id": "1",
        }

    def ler(self, _monotonico):
        return [self._mensagem]


def pelo_whatsapp(
    texto: str,
    tmp_path,
    *,
    acervo=None,
    assinaturas_vivas=None,
    forma_esperada=None,
) -> DespachanteQueGrava:
    """Roda `atender_comandos` como o LACO roda, e devolve o que saiu.

    Os dois relogios entram separados porque eles NAO sao intercambiaveis:
    `agora` e `datetime` de parede e `monotonico` e segundos corridos. Passar
    um so para os dois ja derrubou o scanner em producao com um `TypeError`
    que a suite nao pegava, porque os testes chamavam o leitor direto.
    """
    import time
    from datetime import datetime

    from l2scanner.__main__ import atender_comandos
    from l2scanner.agenda import RegistroEmDisco

    despachante = DespachanteQueGrava()
    atender_comandos(
        LeitorDeUmaMensagem(texto),
        RegistroEmDisco(tmp_path / "agenda"),
        [],
        despachante,
        datetime(2026, 8, 31, 20, 30),
        time.monotonic(),
        acervo=acervo,
        assinaturas_vivas=assinaturas_vivas,
        forma_esperada=forma_esperada,
    )
    return despachante


class TestACosturaComOLaco:
    """O funil unico por onde TODA resposta de comando passa.

    Um erro aqui nao quebra um recurso: ele muda o destino de todos ao mesmo
    tempo, em silencio. A mensagem chega, no lugar errado.
    """

    def test_o_caminho_feliz_responde_SO_na_conversa_de_origem(
        self, tmp_path, acervo, pasta
    ):
        chave = semear(pasta, assinatura_de(1), nome="TITANDER")

        despachante = pelo_whatsapp(
            f"/esquecer {apelido_da_chave(chave)}", tmp_path, acervo=acervo
        )

        assert despachante.alvos == ["1"], (
            "esquecer nao responde pergunta publica nenhuma, entao nao ecoa "
            f"no grupo. Destinos: {despachante.alvos}"
        )
        assert acervo.chaves() == []
        assert "TITANDER" in despachante.textos[0]

    def test_a_resposta_atravessa_o_silencio(self, tmp_path, acervo, pasta):
        """Resposta de comando e `Categoria.SEMPRE`, sem excecao.

        `Categoria.NORMAL` e cortada no transporte quando ha silencio de
        TvT/Prime, e uma resposta cortada assim e indistinguivel, do lado de
        quem digitou, de o bot ter morrido.
        """
        from l2scanner.notificador import Categoria

        chave = semear(pasta, assinatura_de(1))
        despachante = pelo_whatsapp(
            f"/esquecer {apelido_da_chave(chave)}", tmp_path, acervo=acervo
        )

        assert {c for _, c, _ in despachante.despachos} == {Categoria.SEMPRE}

    def test_o_lote_atravessa_a_costura_com_a_geometria(
        self, tmp_path, acervo, pasta
    ):
        mortas = [
            semear(pasta, assinatura_de(s, forma=FORMA_DE_ONTEM)) for s in (1, 2)
        ]
        viva = semear(pasta, assinatura_de(4, forma=FORMA_DE_HOJE))

        despachante = pelo_whatsapp(
            f"/esquecer {PALAVRA_DO_LOTE}",
            tmp_path,
            acervo=acervo,
            forma_esperada=FORMA_DE_HOJE,
        )

        assert acervo.chaves() == [viva]
        assert despachante.alvos == ["1"]
        for chave in mortas:
            assert apelido_da_chave(chave) in despachante.textos[0]

    def test_sem_acervo_o_ramo_RECUSA_e_nao_levanta(self, tmp_path):
        """O laco da agenda sem acervo, e o `--dry-run` sem pasta.

        `atender_comandos` nunca levanta: vigiar a party e o trabalho, ouvir
        comando e um extra.
        """
        despachante = pelo_whatsapp("/esquecer 0123ab", tmp_path)
        assert despachante.alvos == ["1"]
        assert "identidades" in despachante.textos[0].lower()

    def test_o_LACO_PRINCIPAL_entrega_a_geometria(self):
        """Portao de AST, e ele guarda uma falha SILENCIOSA.

        Sem `forma_esperada` na chamada do laco principal, o lote responderia
        para sempre "nao sei qual e a regiao de nome de agora" no unico lugar
        em que ele deveria funcionar, e do lado do usuario isso e
        indistinguivel do comando estar quebrado. Nao ha entrada que produza
        esse defeito num teste de comportamento sem subir um laco com tela;
        o que se afirma aqui e a propriedade que impede o defeito de nascer.

        Afirma a FORMA e nao o valor: tem de ser uma EXPRESSAO, e nunca o
        literal `None`. O nome da variavel fica livre de proposito, pela mesma
        razao ja escrita no portao do `bosses`.
        """
        import inspect

        from l2scanner import __main__ as principal

        arvore = ast.parse(inspect.getsource(principal.laco_principal))
        chamadas = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and getattr(no.func, "id", None) == "atender_comandos"
        ]
        assert chamadas, "o laco principal nao chama `atender_comandos`"
        for chamada in chamadas:
            passados = {
                palavra.arg: palavra.value
                for palavra in chamada.keywords
                if palavra.arg
            }
            assert "forma_esperada" in passados, (
                "o laco principal nao entrega a regiao de nome de agora, e o "
                "lote do /esquecer nunca vai funcionar em campo"
            )
            valor = passados["forma_esperada"]
            assert not (
                isinstance(valor, ast.Constant) and valor.value is None
            ), "a geometria foi entregue como None literal"

    def test_a_prova_do_portao_pega_a_ausencia(self):
        """Guarda contra prova vazia: o detector acha o que deveria achar."""
        arvore = ast.parse("atender_comandos(leitor, acervo=acervo)\n")
        chamada = next(
            no for no in ast.walk(arvore) if isinstance(no, ast.Call)
        )
        passados = {p.arg for p in chamada.keywords if p.arg}
        assert "forma_esperada" not in passados


# ---------------------------------------------------------------------------
# O TEXTO CHEGA NO CELULAR
# ---------------------------------------------------------------------------


def _todas_as_respostas(acervo, pasta) -> list[str]:
    """Um exemplar de CADA redacao que este modulo sabe produzir."""
    chave = semear(pasta, assinatura_de(1, forma=FORMA_DE_ONTEM), nome="TITANDER")
    semear(pasta, assinatura_de(2, forma=FORMA_DE_HOJE))
    vivas = [
        assinatura_de(1, forma=FORMA_DE_ONTEM, nome="TITANDER"),
        assinatura_de(2, forma=FORMA_DE_HOJE),
    ]

    textos = [
        responder_esquecimento(acervo, None).privado,
        responder_esquecimento(acervo, "6288ee TITANDER").privado,
        responder_esquecimento(acervo, "ffffff").privado,
        responder_esquecimento(acervo, PALAVRA_DO_LOTE).privado,
        responder_esquecimento(
            acervo, PALAVRA_DO_LOTE, forma_esperada=FORMA_DE_HOJE
        ).privado,
        responder_esquecimento(
            acervo,
            apelido_da_chave(chave),
            assinaturas_vivas=vivas,
        ).privado,
        responder_esquecimento(
            acervo, PALAVRA_DO_LOTE, forma_esperada=FORMA_DE_HOJE
        ).privado,
    ]
    return textos


class TestOTextoAtravessaOCp1252:
    """O texto vai para o WhatsApp e para o console do Windows.

    Um travessao vira lixo no cp1252, e um caractere corrompido faz o usuario
    duvidar da mensagem inteira. Numa mensagem que ENSINA um nome de arquivo
    para digitar, duvidar dela e nao conseguir recuperar nada.
    """

    def test_ha_frase_suficiente_para_a_prova_valer(self, acervo, pasta):
        textos = _todas_as_respostas(acervo, pasta)
        assert len(textos) >= 6
        assert all(t.strip() for t in textos)

    def test_nenhuma_frase_tem_acento(self, acervo, pasta):
        for texto in _todas_as_respostas(acervo, pasta):
            assert texto == texto.encode("ascii", "ignore").decode("ascii"), texto

    def test_nenhuma_frase_tem_travessao(self, acervo, pasta):
        for texto in _todas_as_respostas(acervo, pasta):
            for proibido in ("—", "–"):
                assert proibido not in texto, texto
