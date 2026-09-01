"""O acervo de assinaturas em disco, e o silencio de quem ele nao sabe nomear.

POR QUE O SILENCIO E TESTADO AQUI, NA FASE 1, E NAO NA FASE 2

O acervo so vale a pena se uma entrada SEM NOME puder existir com seguranca.
Enquanto uma entrada anonima puder virar sujeito de alerta, aprender assinaturas
automaticamente (Fase 2) seria construir em cima de um tipo que mente: o scanner
reconheceria a linha, nao saberia o nome de ninguem, e mesmo assim anunciaria
"Fulano morreu" pegando emprestado o nome da lista por POSICAO. Foi exatamente
esse o defeito encontrado em campo — `Rastreador.assinaturas_configuradas` tinha
default `False`, era atribuido so nos testes, e portanto o silencio estava
provado na suite e desligado no jogo.

A ORDEM DOS TESTES DA FATIA E DELIBERADA. A guarda contra prova vazia (a mesma
entrada, COM o arquivo irmao de nome, produz o nome na tela) vem ANTES da
afirmacao de silencio. Sem ela, "a linha nao gerou evento nenhum" passaria
igualzinho se a assinatura simplesmente nunca casasse com coisa alguma — e o
teste estaria provando que o acervo nao funciona, com cara de estar provando que
ele cala.

TODA entrada usada aqui e escrita A MAO com `json.dumps`, nunca por um caminho
de producao: esta fase LE e PROVA, e nao aprende.
"""

from __future__ import annotations

import ast
import json
import os
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.acervo import (
    AcervoDeIdentidades,
    Identidades,
    carregar_identidades,
    chave_da_assinatura,
)
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.identidade import (
    LIMIAR_DE_CASAMENTO,
    MARGEM_MINIMA_SOBRE_O_SEGUNDO,
    Assinatura,
    _pontuar_mascara,
    criar_assinatura,
    identificar_linhas,
    mascara_de_texto,
)
from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento
from l2scanner.visao import _recorte_do_nome, extrair

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "identidade"

# A linha da party window de onde sai a assinatura da fatia. Qualquer uma
# serviria; esta e a segunda, para que o rotulo esperado ("Membro 2") nao possa
# coincidir por acidente com um "Membro 1" vindo de um indice zerado.
LINHA_DA_FATIA = 1


@pytest.fixture
def calibracao() -> Calibracao:
    """A calibracao da fixture SEM as assinaturas que ela ja traz.

    O acervo tem de ser a unica fonte de identidade nestes testes: com as quatro
    assinaturas calibradas na mesa, um casamento correto nao provaria que a
    entrada em disco foi lida.
    """
    cal = Calibracao.carregar(FIXTURES / "calibracao.json")
    cal.assinaturas = []
    return cal


@pytest.fixture
def pixels() -> np.ndarray:
    px = cv2.imread(str(FIXTURES / "party_ordem_original.png"), cv2.IMREAD_COLOR)
    assert px is not None, "fixture da party nao pode ser lida"
    return px


def assinatura_da_linha(px: np.ndarray, cal: Calibracao, indice: int) -> Assinatura:
    """A assinatura ANONIMA do nome que esta naquela linha do frame real."""
    recorte = _recorte_do_nome(px, cal, indice)
    assert recorte is not None
    return criar_assinatura("", recorte)


def semear(pasta: Path, assinatura: Assinatura, nome: str | None = None) -> str:
    """Escreve uma entrada A MAO, como um humano faria, e devolve a chave.

    Deliberadamente NAO usa nenhum caminho de escrita de producao: o criterio
    desta fase e que uma entrada POSTA A MAO se comporte certo.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    chave = chave_da_assinatura(assinatura)
    corpo = assinatura.como_dict()
    corpo.pop("nome", None)
    (pasta / f"assinatura_{chave}.json").write_text(
        json.dumps(corpo), encoding="utf-8"
    )
    if nome is not None:
        (pasta / f"nome_{chave}").write_text(nome, encoding="utf-8")
    return chave


def observar_frame(px: np.ndarray, cal: Calibracao):
    return extrair(Frame(pixels=px, indice=0, saude=SaudeDoFrame.OK), cal)


def com_hp(obs, indice: int, hp: float):
    linhas = list(obs.linhas)
    linhas[indice] = replace(linhas[indice], hp=hp)
    return replace(obs, linhas=tuple(linhas))


def mortes_apos_zerar(obs, indice: int, configuradas: bool, nomes: list[str]):
    """Roda o rastreador de verdade sobre uma sequencia que confirma morte."""
    r = Rastreador(
        nomes=list(nomes),
        assinaturas_configuradas=configuradas,
        ajustes=Ajustes(confirmacoes_para_morte=2),
    )
    for i in range(15):
        r.observar(obs, -100 + i)
    eventos = []
    for i in range(6):
        eventos.extend(r.observar(com_hp(obs, indice, 0.0), 10 + i))
    return r, [e.membro for e in eventos if e.tipo is TipoDeEvento.MORREU]


# ---------------------------------------------------------------------------
# A CHAVE (D-01 e D-06)
# ---------------------------------------------------------------------------


class TestAChaveEOConteudo:
    """A chave e o hash dos PIXELS, e de mais nada.

    Ela precisa sobreviver a duas coisas que mudam o tempo todo — a posicao da
    linha e o nome que damos a pessoa — porque e ela que identifica a entrada
    entre reinicios e entre as duas instancias que o usuario roda.
    """

    def test_a_chave_nao_depende_do_nome(self, pixels, calibracao):
        """Batizar nao pode reescrever a identidade da entrada.

        Se a chave mudasse com o nome, corrigir um batismo errado (a Fase 3
        permite isso de proposito) orfanaria a assinatura e o scanner voltaria a
        nao conhecer a pessoa.
        """
        mascara = assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA).mascara
        chaves = {
            chave_da_assinatura(Assinatura(nome=n, mascara=mascara))
            for n in ("", "Kaus", "Korzis")
        }
        assert len(chaves) == 1, f"o nome vazou para a chave: {chaves}"

    def test_a_chave_nao_depende_da_posicao(self, pixels, calibracao):
        """A party window compacta as linhas; a posicao nunca foi identidade.

        Os pixels do nome da linha 1 sao copiados para a regiao da linha 0 — o
        que a party faz sozinha quando alguem sai — e a chave tem de ser a
        mesma.
        """
        original = assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)

        compactado = pixels.copy()
        origem = calibracao.regiao_do_nome(LINHA_DA_FATIA)
        destino = calibracao.regiao_do_nome(0)
        compactado[
            destino.topo : destino.topo + destino.altura,
            destino.esquerda : destino.esquerda + destino.largura,
        ] = pixels[
            origem.topo : origem.topo + origem.altura,
            origem.esquerda : origem.esquerda + origem.largura,
        ]
        movido = assinatura_da_linha(compactado, calibracao, 0)

        assert chave_da_assinatura(movido) == chave_da_assinatura(original)

    def test_as_dimensoes_entram_no_material(self):
        """Duas mascaras diferentes com os MESMOS bytes empacotados.

        `packbits` de uma 2x8 e de uma 4x4 produz byte a byte a mesma coisa.
        Sem a dimensao no material do hash, elas compartilhariam chave — e
        compartilhar chave e compartilhar NOME. Nao e uma colisao que depende de
        sorte: basta um recorte de altura diferente.
        """
        bits = np.array([1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1], np.uint8)
        larga = Assinatura(nome="", mascara=bits.reshape(2, 8))
        alta = Assinatura(nome="", mascara=bits.reshape(4, 4))

        assert larga.como_dict()["bits"] == alta.como_dict()["bits"], (
            "premissa do teste: os bytes empacotados sao identicos"
        )
        assert chave_da_assinatura(larga) != chave_da_assinatura(alta)

    def test_a_chave_e_sha256_inteiro(self, pixels, calibracao):
        """64 digitos hex, sem truncar.

        O desfecho de uma colisao aqui nao e um erro: e "Korzis morreu" quando
        morreu o Kaus, com a mensagem parecendo normal. Decisao travada pelo
        usuario em 2026-08-31.
        """
        chave = chave_da_assinatura(
            assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        assert len(chave) == 64
        assert set(chave) <= set("0123456789abcdef")


# ---------------------------------------------------------------------------
# A LEITURA DA PASTA
# ---------------------------------------------------------------------------


class TestLeituraDoAcervo:
    """A pasta e compartilhada, duravel e editada a mao. Tudo la dentro e INPUT."""

    def test_entrada_sem_irmao_de_nome_e_lida_como_anonima(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        acervo = AcervoDeIdentidades(tmp_path)

        assert acervo.chaves() == [chave]
        (lida,) = acervo.assinaturas()
        assert lida.anonima
        assert lida.nome == ""

    def test_entrada_com_irmao_de_nome_valido_produz_o_nome(
        self, tmp_path, pixels, calibracao
    ):
        semear(
            tmp_path,
            assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA),
            nome="Kaus",
        )
        (lida,) = AcervoDeIdentidades(tmp_path).assinaturas()
        assert lida.nome == "Kaus"
        assert not lida.anonima

    def test_o_nome_enfiado_dentro_do_json_e_ignorado(
        self, tmp_path, pixels, calibracao
    ):
        """O nome mora no arquivo IRMAO, e so nele (D-03).

        Alguem editando a pasta a mao pode achar natural escrever `nome` dentro
        do json da assinatura. Se isso batizasse a entrada, haveria dois lugares
        onde um nome pode morar, e a Fase 3 corrigiria so um deles.
        """
        assinatura = assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        chave = chave_da_assinatura(assinatura)
        corpo = assinatura.como_dict()
        corpo["nome"] = "Impostor"
        (tmp_path / f"assinatura_{chave}.json").write_text(
            json.dumps(corpo), encoding="utf-8"
        )

        acervo = AcervoDeIdentidades(tmp_path)
        assert acervo.chaves() == [chave], (
            "a chave recalculada tem de continuar batendo: o `nome` nao entra "
            "no material do hash"
        )
        (lida,) = acervo.assinaturas()
        assert lida.anonima

    def test_conteudo_adulterado_e_descartado(self, tmp_path, pixels, calibracao):
        """O nome do arquivo nao e uma afirmacao: e uma soma de verificacao.

        Um bit trocado no corpo faz a chave recalculada divergir do nome do
        arquivo. A entrada some — em vez de continuar respondendo pela
        identidade de outra pessoa.
        """
        assinatura = assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        chave = chave_da_assinatura(assinatura)
        corpo = assinatura.como_dict()
        corpo.pop("nome")
        virado = bytearray(bytes.fromhex(corpo["bits"]))
        virado[0] ^= 0x01
        corpo["bits"] = bytes(virado).hex()
        (tmp_path / f"assinatura_{chave}.json").write_text(
            json.dumps(corpo), encoding="utf-8"
        )

        acervo = AcervoDeIdentidades(tmp_path)
        assert acervo.chaves() == []
        assert acervo.assinaturas() == []

    @pytest.mark.parametrize(
        "conteudo",
        [
            "../../etc/passwd",
            "Kaus\nKorzis",
            "",
            "   ",
            "K",
            "A" * 40,
            "Kaus Korzis",
            "..",
        ],
        ids=[
            "travessia",
            "duas_linhas",
            "vazio",
            "so_espaco",
            "curto_demais",
            "longo_demais",
            "com_espaco",
            "pontos",
        ],
    )
    def test_nome_invalido_degrada_para_anonimo(
        self, tmp_path, pixels, calibracao, conteudo
    ):
        """O desfecho de um arquivo de nome ruim e SILENCIO, nunca um nome errado.

        Um nome faltando custa um "Membro N" no console. Um nome errado custa a
        party socorrendo a pessoa errada — a assimetria nao esta nem perto de
        ser simetrica.
        """
        semear(
            tmp_path,
            assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA),
            nome=conteudo,
        )
        (lida,) = AcervoDeIdentidades(tmp_path).assinaturas()
        assert lida.anonima, f"{conteudo!r} nao pode virar nome exibido"

    def test_nome_valido_sobrevive_a_espaco_e_quebra_de_linha_ao_redor(
        self, tmp_path, pixels, calibracao
    ):
        """Um editor de texto acrescenta `\\n` no fim; isso nao pode anonimizar."""
        semear(
            tmp_path,
            assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA),
            nome="  Kaus\n",
        )
        (lida,) = AcervoDeIdentidades(tmp_path).assinaturas()
        assert lida.nome == "Kaus"

    @pytest.mark.parametrize(
        "nome_do_arquivo",
        [
            "assinatura_naohex.json",
            "assinatura_" + "a" * 63 + ".json",
            "assinatura_" + "A" * 64 + ".json",
            "assinatura_..%2f..%2fetc%2fpasswd.json",
            "assinatura_" + "a" * 64,
            "outra_coisa.json",
        ],
    )
    def test_nome_de_arquivo_fora_do_padrao_nunca_vira_chave(
        self, tmp_path, nome_do_arquivo
    ):
        """So `assinatura_<64 hex>.json` e considerado.

        Como a chave e hex por construcao, travessia de caminho fica
        estruturalmente fora de alcance: nao existe nome aceito que contenha um
        separador.
        """
        (tmp_path / nome_do_arquivo).write_text("{}", encoding="utf-8")
        assert AcervoDeIdentidades(tmp_path).chaves() == []

    def test_lixo_na_pasta_nao_vira_excecao_no_meio_do_farm(
        self, tmp_path, pixels, calibracao
    ):
        """A pasta e compartilhada pelas duas instancias e duravel.

        Um arquivo ilegivel nao pode derrubar a leitura das entradas boas: no
        molde de `loot.registros()`, o que nao da para ler e PULADO.
        """
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        lixo = "b" * 64
        (tmp_path / f"assinatura_{lixo}.json").write_text(
            "{ isto nao e json", encoding="utf-8"
        )
        (tmp_path / f"assinatura_{'c' * 64}.json").write_text(
            json.dumps({"altura": 4}), encoding="utf-8"
        )
        (tmp_path / "leiame.txt").write_text("anotacao do usuario", encoding="utf-8")

        assert AcervoDeIdentidades(tmp_path).chaves() == [chave]

    def test_a_pasta_e_criada_no_arranque(self, tmp_path):
        pasta = tmp_path / "sub" / ".identidades"
        AcervoDeIdentidades(pasta)
        assert pasta.is_dir()

    def test_acervo_vazio_nao_levanta(self, tmp_path):
        acervo = AcervoDeIdentidades(tmp_path / ".identidades")
        assert acervo.chaves() == []
        assert acervo.assinaturas() == []


# ---------------------------------------------------------------------------
# A FUSAO E A LINHA DE ARRANQUE
# ---------------------------------------------------------------------------


class TestFusaoComACalibracao:
    def test_as_calibradas_entram_primeiro(self, tmp_path, pixels, calibracao):
        """A precedencia da calibracao e ESTRUTURAL, e nao uma condicao escrita.

        `identificar_linhas` desempata por `-j`: no empate exato vence o indice
        menor. Pondo as calibradas na frente, a regra "a calibracao ganha"
        acontece sozinha, e nao pode ser invertida por engano numa comparacao.
        """
        calibrada = Assinatura(
            nome="Korzis", mascara=np.ones((4, 4), dtype=np.uint8)
        )
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))

        identidades = carregar_identidades(
            [calibrada], AcervoDeIdentidades(tmp_path)
        )
        assert identidades.assinaturas[0] is calibrada
        assert identidades.conhecidas == 2

    def test_sem_assinatura_nenhuma_configuradas_e_falso(self, tmp_path):
        identidades = carregar_identidades([], AcervoDeIdentidades(tmp_path))
        assert identidades.configuradas is False
        assert identidades.resumo == "Identidades: nenhuma assinatura conhecida"

    def test_resumo_conta_conhecidas_e_sem_nome(self, tmp_path, pixels, calibracao):
        """A linha do arranque (OPER-01).

        O usuario precisa saber, antes de sair AFK, quantas pessoas o scanner
        reconhece e quantas dessas ainda nao tem nome — que sao exatamente as
        que vao aparecer como "Membro N" e nao vao gerar alerta em nome de
        ninguem.
        """
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, 0))
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, 1), nome="Kaus")

        identidades = carregar_identidades([], AcervoDeIdentidades(tmp_path))
        assert identidades.conhecidas == 2
        assert identidades.sem_nome == 1
        assert identidades.configuradas is True
        assert identidades.resumo == (
            "Identidades: 2 assinatura(s) conhecida(s), 1 sem nome"
        )

    def test_o_resumo_nao_tem_acento_nem_travessao(self):
        """Convencao do projeto para todo texto que o usuario le."""
        resumos = [
            Identidades().resumo,
            Identidades(
                assinaturas=[Assinatura("", np.ones((2, 2), np.uint8))]
            ).resumo,
        ]
        for texto in resumos:
            assert texto.isascii(), texto
            assert "—" not in texto and "–" not in texto


# ---------------------------------------------------------------------------
# A FATIA INTEIRA: disco -> fusao -> reconhecimento -> rastreador -> console
# ---------------------------------------------------------------------------


class TestUmaEntradaAMaoAtravessaOScanner:
    """O criterio 6, e a razao de esta fase existir antes da Fase 2.

    A guarda contra prova vazia vem PRIMEIRO de proposito: se a assinatura
    semeada nunca casasse com nada, o teste de silencio passaria sem provar
    silencio nenhum.
    """

    def test_com_nome_a_linha_e_reconhecida_e_o_alerta_sai_no_nome_dela(
        self, tmp_path, pixels, calibracao
    ):
        """GUARDA CONTRA PROVA VAZIA. Le antes do teste seguinte."""
        semear(
            tmp_path,
            assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA),
            nome="Kaus",
        )
        identidades = carregar_identidades([], AcervoDeIdentidades(tmp_path))
        calibracao.assinaturas = identidades.assinaturas

        obs = observar_frame(pixels, calibracao)
        assert obs.linhas[LINHA_DA_FATIA].nome == "Kaus", (
            "a entrada em disco tem de casar com a linha real do frame; sem "
            "isto o teste de silencio abaixo nao prova nada"
        )

        _, mortes = mortes_apos_zerar(
            obs, LINHA_DA_FATIA, identidades.configuradas, calibracao.nomes
        )
        assert mortes == ["Kaus"]

    def test_sem_nome_a_MESMA_entrada_e_reconhecida_e_CALA(
        self, tmp_path, pixels, calibracao
    ):
        """O silencio do `#linhaN`, agora para uma entrada do acervo.

        A UNICA diferenca em relacao ao teste acima e a ausencia do arquivo
        irmao `nome_<chave>`. A linha continua sendo reconhecida — a mesma
        assinatura, a mesma correlacao — e mesmo assim nenhum evento sai em nome
        dela e o console mostra "Membro 2".

        O reflexo errado aqui e deixar a linha falar, porque reconhece-la parece
        progresso. Nao e: uma entrada anonima nao tem sujeito, e um alerta sem
        sujeito so pode pegar emprestado o nome de outra pessoa.
        """
        semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        identidades = carregar_identidades([], AcervoDeIdentidades(tmp_path))
        calibracao.assinaturas = identidades.assinaturas

        obs = observar_frame(pixels, calibracao)
        linha = obs.linhas[LINHA_DA_FATIA]
        assert linha.nome == "", "a entrada anonima nao pode ganhar nome nenhum"
        assert linha.confianca_do_nome > 0.9, (
            "ela FOI reconhecida — o silencio nao pode vir de falta de casamento"
        )

        rastreador, mortes = mortes_apos_zerar(
            obs, LINHA_DA_FATIA, identidades.configuradas, calibracao.nomes
        )
        assert mortes == [], f"uma linha sem sujeito nao morre. Saiu: {mortes}"

        identidade = rastreador._identidade_por_linha[LINHA_DA_FATIA]
        assert identidade == f"#linha{LINHA_DA_FATIA}"
        assert rastreador._nome_exibido(identidade) == f"Membro {LINHA_DA_FATIA + 1}"

    def test_a_entrada_anonima_nao_entra_nos_nomes_reservados(
        self, tmp_path, pixels, calibracao
    ):
        """A string vazia nao pode virar um "nome" que reserva alguma coisa."""
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        identidades = carregar_identidades([], AcervoDeIdentidades(tmp_path))
        calibracao.assinaturas = identidades.assinaturas

        assert calibracao.nomes_com_assinatura == set()


# ---------------------------------------------------------------------------
# O PORTAO DE CLASSE: nenhum Rastreador novo nasce mudo por esquecimento
# ---------------------------------------------------------------------------


def _chamadas_de_rastreador(fonte: str, arquivo: str) -> list[tuple[str, bool]]:
    """Toda chamada `Rastreador(...)` na arvore, e se ela decide sobre a flag.

    AST e nunca `grep`: as docstrings deste projeto citam `Rastreador(...)` ao
    explicar as proprias regras, e um `grep` acusaria comentario como codigo.
    """
    achadas: list[tuple[str, bool]] = []
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Call):
            continue
        alvo = getattr(no.func, "id", None) or getattr(no.func, "attr", None)
        if alvo != "Rastreador":
            continue
        decide = any(
            k.arg == "assinaturas_configuradas" for k in no.keywords
        )
        achadas.append((f"{arquivo}:{no.lineno}", decide))
    return achadas


def _chamadas_em_producao() -> list[tuple[str, bool]]:
    achadas: list[tuple[str, bool]] = []
    for caminho in sorted((RAIZ / "l2scanner").glob("*.py")):
        achadas.extend(
            _chamadas_de_rastreador(
                caminho.read_text(encoding="utf-8"), caminho.name
            )
        )
    return achadas


class TestNenhumRastreadorNasceMudo:
    """`assinaturas_configuradas` decide entre CALAR e MENTIR.

    Um booleano com default silencioso e a pior forma possivel para uma decisao
    dessas, e o campo provou isso: ate 2026-08-31 o unico construtor de producao
    (`__main__.py`) nao passava o argumento, oito casos de
    `tests/test_identidade.py` passavam `True`, e o resultado era o silencio do
    `#linhaN` verde na suite e DESLIGADO no jogo. Uma linha sem reconhecimento
    pegava emprestado `nomes[indice]` e anunciava a morte de quem estava vivo.

    Consertar so a chamada de hoje deixaria a porta aberta: o segundo
    `Rastreador(...)` que alguem escrever amanha nasceria mudo do mesmo jeito, e
    nenhum teste reclamaria. Este portao afirma sobre o CONJUNTO INTEIRO.

    O portao NAO conserta o default. Tornar o parametro posicional obrigatorio
    quebraria os oito testes existentes, e esta fase nao reescreve teste que
    passa. Quem quiser um `Rastreador` sem o silencio ligado continua podendo —
    mas tem de escrever `False` com a propria mao, e ai a escolha aparece no
    diff de alguem em vez de acontecer por esquecimento.
    """

    def test_toda_chamada_em_producao_decide_sobre_a_flag(self):
        mudas = [local for local, decide in _chamadas_em_producao() if not decide]
        assert not mudas, (
            "estes `Rastreador(...)` nao decidem sobre `assinaturas_configuradas` "
            "e portanto nascem com o silencio DESLIGADO: " + ", ".join(mudas)
        )

    def test_o_detector_acusa_um_caso_plantado(self):
        """Guarda contra prova vazia.

        Um detector com o caminho errado, ou um `walk` que nao alcanca, ficaria
        verde para sempre — e o portao teria a mesma forma de defeito que ele
        existe para pegar.
        """
        fabricado = "from l2scanner.rastreador import Rastreador\nr = Rastreador(nomes=[])\n"
        achadas = _chamadas_de_rastreador(fabricado, "<fabricado>")
        assert achadas, "o detector nao achou nem uma chamada plantada"
        assert [local for local, decide in achadas if not decide], (
            "o detector nao acusaria um `Rastreador(nomes=[])` sem a flag"
        )

    def test_o_detector_reconhece_uma_chamada_que_decide(self):
        """A outra metade: o detector nao acusa quem cumpriu a regra."""
        fabricado = "r = Rastreador(nomes=[], assinaturas_configuradas=False)\n"
        achadas = _chamadas_de_rastreador(fabricado, "<fabricado>")
        assert achadas == [("<fabricado>:1", True)]

    def test_o_portao_nao_passa_por_vacuidade(self):
        """Um portao que nao acha nada passa sem provar nada.

        Este projeto ja pagou por um comando de verificacao que "passava sem
        rodar nada" (plano 10-02). A licao esta escrita la, e o preco dela e
        esta assercao de tres linhas.
        """
        achadas = _chamadas_em_producao()
        assert achadas, (
            "o detector nao encontrou NENHUM `Rastreador(...)` em l2scanner/ — "
            "o portao esta olhando para o lugar errado"
        )


# ---------------------------------------------------------------------------
# A ESCRITA: duas instancias disputando, e o disco que falha sem mentir
# ---------------------------------------------------------------------------


def falhar_dentro_de(pasta: Path, real):
    """Um `os.open`/`os.write` que so falha para a pasta do teste.

    Patchar a funcao inteira derrubaria a propria pytest junto. O envelope
    delega para a de verdade tudo que nao e o acervo sob teste.
    """

    def falso(alvo, *args, **kwargs):
        if str(pasta) in str(alvo):
            raise OSError("disco cheio (simulado)")
        return real(alvo, *args, **kwargs)

    return falso


def recusar_escrita(descritor, dados):
    raise OSError("disco cheio (simulado)")


class TestGravar:
    """A primitiva de escrita existe e e provada; ela NAO tem chamador no laco.

    Aprender uma assinatura sozinho e trabalho da Fase 2. Esta fase prova que a
    escrita se comporta — a corrida das duas instancias e o disco que falha —
    para que a Fase 2 possa decidir QUANDO chamar sem ter tambem de descobrir SE
    funciona.
    """

    def test_gravar_uma_assinatura_nova_devolve_criado(
        self, tmp_path, pixels, calibracao
    ):
        acervo = AcervoDeIdentidades(tmp_path)
        assinatura = assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)

        assert acervo.gravar(assinatura) == "criado"
        assert acervo.chaves() == [chave_da_assinatura(assinatura)]

    def test_gravar_de_novo_devolve_ja_existia_e_nao_duplica(
        self, tmp_path, pixels, calibracao
    ):
        acervo = AcervoDeIdentidades(tmp_path)
        assinatura = assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        acervo.gravar(assinatura)

        assert acervo.gravar(assinatura) == "ja_existia"
        assert len(acervo.chaves()) == 1

    def test_duas_instancias_na_mesma_pasta_produzem_UMA_entrada(
        self, tmp_path, pixels, calibracao
    ):
        """A premissa do projeto: Yazalaque e Faerlina rodando ao mesmo tempo.

        `O_CREAT|O_EXCL` decide a corrida no kernel. Exatamente uma cria; a
        outra recebe `"ja_existia"`, que e uma resposta verdadeira e nao um
        erro.
        """
        yazalaque = AcervoDeIdentidades(tmp_path)
        faerlina = AcervoDeIdentidades(tmp_path)
        assinatura = assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)

        desfechos = sorted(
            [yazalaque.gravar(assinatura), faerlina.gravar(assinatura)]
        )
        assert desfechos == ["criado", "ja_existia"]
        assert len(yazalaque.chaves()) == 1

    def test_assinaturas_diferentes_produzem_entradas_diferentes(
        self, tmp_path, pixels, calibracao
    ):
        acervo = AcervoDeIdentidades(tmp_path)
        acervo.gravar(assinatura_da_linha(pixels, calibracao, 0))
        acervo.gravar(assinatura_da_linha(pixels, calibracao, 1))

        assert len(acervo.chaves()) == 2

    def test_o_corpo_gravado_nao_carrega_o_nome(self, tmp_path, pixels, calibracao):
        """O nome mora no irmao (D-03).

        Se ele fosse junto, corrigir um batismo exigiria reescrever a
        assinatura — e reescrever a assinatura muda a chave, que e a unica coisa
        que nao pode mudar.
        """
        acervo = AcervoDeIdentidades(tmp_path)
        assinatura = replace(
            assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA), nome="Kaus"
        )
        acervo.gravar(assinatura)

        (arquivo,) = list(tmp_path.glob("assinatura_*.json"))
        corpo = json.loads(arquivo.read_text(encoding="utf-8"))
        assert "nome" not in corpo
        assert set(corpo) == {"altura", "largura", "bits"}

    def test_o_que_foi_gravado_e_relido_igual(self, tmp_path, pixels, calibracao):
        """Ida e volta: gravar e ler tem de concordar sobre a chave.

        Se nao concordassem, TODA entrada gravada seria descartada pela
        conferencia de chave da leitura — e o acervo pareceria funcionar
        (`"criado"` toda vez) enquanto nunca reconhecesse ninguem.
        """
        acervo = AcervoDeIdentidades(tmp_path)
        assinatura = assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        acervo.gravar(assinatura)

        (lida,) = acervo.assinaturas()
        assert np.array_equal(lida.mascara, assinatura.mascara)
        assert lida.anonima

    def test_falha_de_disco_devolve_falhou_e_nao_deixa_entrada(
        self, tmp_path, pixels, calibracao, monkeypatch
    ):
        """`falhou` e uma terceira resposta, e nao um `criado` disfarcado.

        E a distincao que permite ao chamador da Fase 2 tentar de novo em vez de
        acreditar que aprendeu. Colapsada em `criado`, a pessoa ficaria anonima
        para sempre — o batismo pergunta uma vez so — sem erro em lugar nenhum.
        """
        acervo = AcervoDeIdentidades(tmp_path)
        monkeypatch.setattr(
            "l2scanner.acervo.os.open", falhar_dentro_de(tmp_path, os.open)
        )

        desfecho = acervo.gravar(
            assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )

        assert desfecho == "falhou"
        assert desfecho not in ("criado", "ja_existia")
        assert list(tmp_path.glob("assinatura_*")) == []

    def test_falha_no_meio_da_escrita_nao_deixa_entrada_pela_metade(
        self, tmp_path, pixels, calibracao, monkeypatch
    ):
        """O descritor abriu, o corpo nao foi.

        A entrada intacta ao lado continua legivel, e a que falhou nao aparece
        em `assinaturas()` — nem como assinatura truncada com chave que bate,
        que seria a forma perigosa: uma mascara pela metade casando com a pessoa
        errada.
        """
        acervo = AcervoDeIdentidades(tmp_path)
        intacta = assinatura_da_linha(pixels, calibracao, 0)
        assert acervo.gravar(intacta) == "criado"

        monkeypatch.setattr("l2scanner.acervo.os.write", recusar_escrita)
        assert acervo.gravar(assinatura_da_linha(pixels, calibracao, 1)) == "falhou"

        assert acervo.chaves() == [chave_da_assinatura(intacta)]
        (sobrevivente,) = acervo.assinaturas()
        assert np.array_equal(sobrevivente.mascara, intacta.mascara)

    def test_uma_escrita_parcial_tambem_e_falha(
        self, tmp_path, pixels, calibracao, monkeypatch
    ):
        """`os.write` pode escrever MENOS do que pediram, sem levantar nada.

        Um corpo truncado que ninguem contou seria a unica forma de o acervo
        gravar lixo com a cara de sucesso.
        """
        acervo = AcervoDeIdentidades(tmp_path)
        monkeypatch.setattr("l2scanner.acervo.os.write", lambda fd, dados: 1)

        assert (
            acervo.gravar(assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
            == "falhou"
        )
        assert acervo.assinaturas() == []
        assert list(tmp_path.glob("assinatura_*")) == []

    def test_a_docstring_de_gravar_nomeia_os_dois_precedentes(self):
        """O projeto tem DOIS tri-estados opostos, e quem le precisa saber qual.

        Sem isso escrito, o proximo modulo duravel copia o da agenda por
        proximidade e colapsa uma falha de disco em sucesso.
        """
        doc = AcervoDeIdentidades.gravar.__doc__
        assert "RegistroDeLoot" in doc
        assert "RegistroEmDisco" in doc
        assert "criado | ja_existia | falhou" in doc


# ---------------------------------------------------------------------------
# SEM PODA, SEM RELOGIO, E ATRAVESSANDO O REINICIO
# ---------------------------------------------------------------------------


DIAS_DE_ENVELHECIMENTO = 400
SEGUNDOS_POR_DIA = 86400


class TestOAcervoNaoEnvelhece:
    """562 bytes por assinatura, e o usuario dispensou qualquer limpeza no v1.

    A ausencia de poda e uma DECISAO, e decisao que nao tem teste vira detalhe
    de implementacao que alguem "arruma" na proxima fase.
    """

    def test_entradas_de_400_dias_atras_continuam_todas_presentes(
        self, tmp_path, pixels, calibracao
    ):
        """400 dias porque o `.agenda/` poda em 3.

        A pergunta "quem e o Fulano" e sobre MESES: a pessoa que entrou na party
        no ano passado continua sendo a mesma pessoa. Se alguem acrescentar poda
        por idade um dia, e aqui que aparece.

        O tempo entra pelo ARQUIVO (`os.utime`), e nunca pelo relogio da
        maquina: o modulo nao tem relogio para adiantar.
        """
        acervo = AcervoDeIdentidades(tmp_path)
        for indice in range(4):
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        antes = acervo.chaves()
        assert len(antes) == 4, "premissa: quatro linhas, quatro assinaturas"

        antigo = os.stat(tmp_path).st_mtime - DIAS_DE_ENVELHECIMENTO * SEGUNDOS_POR_DIA
        for arquivo in tmp_path.iterdir():
            os.utime(arquivo, (antigo, antigo))

        depois = AcervoDeIdentidades(tmp_path).chaves()
        assert depois == antes
        assert len(depois) == 4

    def test_o_modulo_nao_tem_relogio_proprio(self):
        """A guarda estrutural mora em `tests/test_presenca.py`.

        Este caso existe para que quem ler `test_acervo.py` saiba ONDE ela esta:
        a poda por acidente comeca sempre por um relogio proprio, e o portao que
        impede isso e a tupla `MODULOS` de la.
        """
        from tests.test_presenca import TestSemRelogioProprio

        assert "acervo.py" in TestSemRelogioProprio.MODULOS


class TestOAcervoAtravessaOReinicio:
    def test_uma_instancia_nova_ve_o_MESMO_acervo(
        self, tmp_path, pixels, calibracao
    ):
        """Derrubar e subir o scanner nao pode regenerar nem perder nada.

        A ORDEM entra na afirmacao de proposito: ela alimenta o desempate do
        guloso de `identificar_linhas`. Duas leituras da mesma pasta em ordens
        diferentes dariam reconhecimento diferente com a tela exatamente igual —
        e um bug assim so aparece quando duas assinaturas empatam, ou seja,
        exatamente quando errar e mais caro.
        """
        antes_acervo = AcervoDeIdentidades(tmp_path)
        for indice in range(4):
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        antes = antes_acervo.assinaturas()
        chaves_antes = antes_acervo.chaves()

        del antes_acervo
        depois_acervo = AcervoDeIdentidades(tmp_path)

        assert depois_acervo.chaves() == chaves_antes
        depois = depois_acervo.assinaturas()
        assert len(depois) == len(antes)
        for a, b in zip(antes, depois):
            assert a.nome == b.nome
            assert np.array_equal(a.mascara, b.mascara)


# ---------------------------------------------------------------------------
# A FRONTEIRA DE FASE: esta fase LE, e nao APRENDE
# ---------------------------------------------------------------------------


def _retrato_da_pasta(pasta: Path) -> dict[str, bytes]:
    return {c.name: c.read_bytes() for c in sorted(pasta.iterdir())}


class TestQuemConheceOAcervoEOQueOLacoFazComEle:
    """Os dois portoes de FRONTEIRA DE FASE deste arquivo, DEPOIS da Fase 2.

    A FASE 2 CHEGOU, E OS DOIS FORAM ALTERADOS PELO MOTIVO QUE A DOCSTRING
    ANTERIOR JA MANDAVA. Ela dizia, escrita na Fase 1 para este momento: "A Fase
    2 vai APAGAR `test_o_laco_real_nao_encosta_no_acervo` e AJUSTAR
    `test_so_dois_modulos_conhecem_o_acervo`, DE PROPOSITO — aprender
    assinaturas no laco e literalmente o objetivo da Fase 2".

    O que mudou, e o que NAO mudou:

    - `l2scanner/aprendiz.py` entrou no conjunto de quem conhece o acervo. Ele e
      o consumidor novo, e o unico que escreve por inferencia.
    - `sessao.py` e `visao.py` continuam presos do lado de FORA, que era o ponto
      do portao desde sempre. O `sessao.py` fala com o `aprendiz`, e nao com o
      acervo; o `visao.py` nao fala com nenhum dos dois e continua sendo uma
      funcao pura.
    - o caso comportamental foi SUBSTITUIDO pelo oposto, e nao so removido: o
      par de casos e o que mantem a afirmacao "o laco toca o acervo do jeito
      certo" ancorada em COMPORTAMENTO, e nao em texto.

    Estes dois casos continuam afirmando uma fronteira de FASE, e nao uma
    invariante do projeto.

    A FASE 3 CHEGOU, E O CONJUNTO CRESCEU DE NOVO PELO MOTIVO QUE ESTA
    DOCSTRING JA MANDAVA. Ela dizia, escrita na Fase 2 para este momento: "A
    Fase 3 (batizar) vai acrescentar a escrita do irmao `nome_<chave>`, e o
    conjunto de quem conhece o acervo pode crescer de novo — pelo mesmo tipo de
    razao, e com a mesma exigencia de ser deliberado".

    O que mudou, e o que NAO mudou:

    - `l2scanner/batismo.py` entrou. Ele e quem ESCREVE o nome (`nomear`) e
      quem MARCA a pergunta (`marcar_pergunta`), que sao as duas capacidades
      novas do acervo nesta fase.
    - `sessao.py` e `visao.py` continuam presos do lado de FORA, que sempre foi
      o ponto do portao. A sessao fala com o `batismo`, e nao com o acervo — o
      mesmo desenho que ela ja tinha com o `aprendiz`. O portao pergunta quem
      IMPORTA, lido da arvore sintatica, e essa distincao E o desenho: a sessao
      SEGURA um `AcervoDeIdentidades` que o `__main__` construiu, e nunca
      constroi um.
    """

    def test_so_dois_modulos_conhecem_o_acervo(self):
        """Igualdade de CONJUNTOS, e nunca um `grep` negativo.

        Um `assert "acervo" not in sessao.py` passaria por engano no dia em que
        o import chegasse com outro nome. A igualdade acusa tanto quem passou a
        conhecer quanto quem deixou de conhecer.

        A pergunta e "quem IMPORTA o acervo", lida da arvore sintatica, e nao
        "quem escreve a palavra acervo": as docstrings de `identidade.py` e de
        `calibracao.py` citam o acervo em prosa ao explicar por que uma
        assinatura anonima existe, e uma busca textual acusaria justamente a
        documentacao que protege a regra — o mesmo motivo que fez
        `_modulos_importados` nascer em `tests/test_presenca.py`.

        Isso prende `sessao.py` e `visao.py` FORA, que e exatamente onde um
        aprendizado prematuro nasceria.
        """
        conhecem = {"acervo.py"}  # quem define o modulo
        for caminho in sorted((RAIZ / "l2scanner").glob("*.py")):
            arvore = ast.parse(caminho.read_text(encoding="utf-8"))
            for no in ast.walk(arvore):
                if isinstance(no, ast.ImportFrom) and no.module == "acervo":
                    conhecem.add(caminho.name)
                elif isinstance(no, ast.Import):
                    if any(a.name.split(".")[-1] == "acervo" for a in no.names):
                        conhecem.add(caminho.name)

        assert conhecem == {
            "acervo.py",
            "aprendiz.py",
            "batismo.py",
            "esquecimento.py",
            "__main__.py",
        }, (
            "o acervo e LIDO no arranque (`__main__.py`), ESCRITO por "
            "inferencia (`aprendiz.py`, Fase 2), NOMEADO pelo batismo "
            "(`batismo.py`, Fase 3) e TIRADO DE CIRCULACAO pelo esquecimento "
            "(`esquecimento.py`), e mais nada. `sessao.py` e `visao.py` "
            "continuam de FORA de proposito: a sessao fala com o aprendiz e "
            "com o batismo, e nunca com o acervo, e a visao e uma funcao pura "
            "que nao fala com nenhum dos tres. E `comandos.py` tambem continua "
            "de fora: ele fala com o `esquecimento`, e nao com o acervo, pelo "
            "mesmo desenho que ele ja tinha com o `batismo`. Achado: "
            + str(conhecem)
        )

    def test_o_laco_real_ESCREVE_no_acervo_e_escreve_uma_vez_so(
        self, tmp_path, pixels, calibracao
    ):
        """A prova COMPORTAMENTAL, virada pela Fase 2. Vale mais que a textual.

        Este caso SUBSTITUI `test_o_laco_real_nao_encosta_no_acervo`, que a
        Fase 1 escreveu ja mandando apaga-lo aqui. Aprender no laco e o objetivo
        desta fase; o que precisa continuar sendo afirmado por comportamento e
        que ele escreve DO JEITO CERTO — uma linha desconhecida, uma entrada, e
        nao uma por tick.

        A escrita chega por um caminho que nenhuma busca por texto anteciparia:
        `sessao.tick` -> `aprendiz.Aprendiz.observar` -> `acervo.gravar`. E
        justamente por isso a prova e comportamental.
        """
        from l2scanner.acervo import PREFIXO_ASSINATURA, PREFIXO_NOME
        from l2scanner.agenda import RegistroEmDisco
        from l2scanner.aprendiz import AjustesDoAprendiz, Aprendiz
        from l2scanner.sessao import Sessao

        acervo_pasta = tmp_path / ".identidades"
        # TRES das quatro linhas semeadas: a quarta e a que o laco tem de
        # aprender sozinho. Semear as quatro faria o caso passar sem que
        # NENHUMA escrita acontecesse.
        conhecidas = [i for i in range(4) if i != LINHA_DA_FATIA]
        for indice in conhecidas:
            semear(acervo_pasta, assinatura_da_linha(pixels, calibracao, indice))
        identidades = carregar_identidades([], AcervoDeIdentidades(acervo_pasta))
        calibracao.assinaturas = identidades.assinaturas
        assert len(_retrato_da_pasta(acervo_pasta)) == 3, "premissa: tres conhecidas"

        class SilencioParado:
            def ativo(self):
                return False

            def atualizar(self, agora):
                return None

        acervo = AcervoDeIdentidades(acervo_pasta)
        sessao = Sessao(
            cal=calibracao,
            rastreador=Rastreador(
                nomes=list(calibracao.nomes),
                assinaturas_configuradas=identidades.configuradas,
            ),
            eventos_agendados=[],
            registro=RegistroEmDisco(tmp_path / ".agenda"),
            silencio=SilencioParado(),
            aprendiz=Aprendiz(
                acervo, AjustesDoAprendiz(leituras_para_aprender=3)
            ),
        )
        for indice in range(20):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )

        # NAO VACUIDADE, a mesma guarda da Fase 1: o laco rodou de verdade e
        # USOU o acervo. Um tick que falhasse na analise deixaria a pasta com
        # tres entradas pelo motivo errado, e o portao passaria sem nunca ter
        # chegado perto de uma escrita.
        assert resultado.observacao is not None
        assert any(
            linha.nome == "" and linha.confianca_do_nome > 0.9
            for linha in resultado.observacao.linhas
        ), "as assinaturas do acervo tem de estar em jogo neste tick"

        depois = [
            nome
            for nome in _retrato_da_pasta(acervo_pasta)
            if nome.startswith(PREFIXO_ASSINATURA)
        ]
        # UMA entrada nova, e nao uma a cada N ticks. Vinte ticks sobre o mesmo
        # frame com N igual a tres dariam ate seis entradas para a MESMA pessoa
        # sem a insercao na lista VIVA (D-03) — o inchaco que o APRE-04 proibe.
        assert len(depois) == 4, (
            "o laco tinha de aprender a quarta linha sozinho, UMA vez so. "
            f"Achado: {depois}"
        )
        assert not [
            nome for nome in _retrato_da_pasta(acervo_pasta)
            if nome.startswith(PREFIXO_NOME)
        ], "esta fase grava ANONIMO: batizar e a Fase 3"


# ---------------------------------------------------------------------------
# A CONVIVENCIA: a calibracao e o acervo carregando a MESMA pessoa (OPER-02)
# ---------------------------------------------------------------------------

# Quantos bits da mascara sao virados para produzir a COPIA QUASE IDENTICA.
#
# Nao e um numero escolhido no olho. Medido nesta fixture, na linha 1
# (mascara 20x100 com 48 pixels de texto), virando bits deterministicos:
#
#     bits  calibrada  copia   margem   desfecho de identificar_linhas
#        1     1.0000  0.9895   0.0105  SILENCIO
#        3     1.0000  0.9694   0.0306  SILENCIO
#        8     1.0000  0.9212   0.0788  SILENCIO
#       12     1.0000  0.8879   0.1121  SILENCIO   (ainda abaixo de 0.12)
#       20     1.0000  0.8306   0.1694  "J4guar"   (a margem passou)
#       40     1.0000  0.7237   0.2763  "J4guar"
#
# 8 fica no meio da faixa perigosa: as DUAS pontuacoes bem acima de
# LIMIAR_DE_CASAMENTO (0.75) e a margem bem abaixo de
# MARGEM_MINIMA_SOBRE_O_SEGUNDO (0.12). E exatamente a forma do desfecho que a
# deduplicacao existe para impedir.
BITS_VIRADOS = 8

# A linha da fixture usada nos casos de convivencia. `J4guar` na ordem original.
LINHA_DA_CONVIVENCIA = 1


@pytest.fixture
def calibrada_de_verdade(pixels, calibracao) -> Assinatura:
    """A assinatura CALIBRADA da linha, com o nome que o usuario digitou."""
    recorte = _recorte_do_nome(pixels, calibracao, LINHA_DA_CONVIVENCIA)
    assert recorte is not None
    return criar_assinatura("J4guar", recorte)


def quase_igual(assinatura: Assinatura, nome: str = "") -> Assinatura:
    """A mesma pessoa capturada de outro frame: chave diferente, imagem igual.

    Um pixel basta para a chave mudar (D-01/D-06 usam o conteudo inteiro), e e
    por isso que a regra da CHAVE sozinha nao fecha o buraco de OPER-02.
    """
    achatada = assinatura.mascara.flatten().copy()
    alvos = np.random.RandomState(42).choice(
        achatada.size, size=BITS_VIRADOS, replace=False
    )
    achatada[alvos] ^= 1
    return Assinatura(nome=nome, mascara=achatada.reshape(assinatura.mascara.shape))


class TestOReconhecimentoDeHojeContinuaIgual:
    """Criterio 2, primeira metade: quem prefere digitar nao perde nada.

    O acervo VAZIO e o estado de todo mundo que ainda nao chegou na Fase 2. Se a
    fusao mexesse na lista calibrada, a feature cobraria um preco de quem nem a
    esta usando.
    """

    def test_com_o_acervo_vazio_a_lista_calibrada_volta_intacta(
        self, tmp_path, pixels, calibracao
    ):
        calibradas = [
            criar_assinatura(nome, _recorte_do_nome(pixels, calibracao, i))
            for i, nome in enumerate(["Korzis", "J4guar", "Kaus", "TioMad"])
        ]
        identidades = carregar_identidades(
            calibradas, AcervoDeIdentidades(tmp_path)
        )
        assert identidades.assinaturas == calibradas
        assert [a.nome for a in identidades.assinaturas] == [
            "Korzis",
            "J4guar",
            "Kaus",
            "TioMad",
        ]

    def test_com_o_acervo_vazio_o_frame_real_entrega_os_mesmos_nomes(
        self, tmp_path, pixels
    ):
        """A afirmacao que `tests/test_identidade.py` ja faz, refeita PELA FUSAO.

        Aqui a lista de assinaturas nao vem do `calibration.json` direto: ela
        passa por `carregar_identidades`. E o que prova que a fusao nao e um
        caminho paralelo com resultado proprio.
        """
        cal = Calibracao.carregar(FIXTURES / "calibracao.json")
        identidades = carregar_identidades(
            list(cal.assinaturas), AcervoDeIdentidades(tmp_path)
        )
        cal.assinaturas = identidades.assinaturas

        obs = observar_frame(pixels, cal)
        assert [linha.nome for linha in obs.linhas[:4]] == cal.nomes


class TestAMesmaPessoaNosDoisLugares:
    """Criterio 2, segunda metade: nenhuma das duas sombreia a outra.

    O PIOR DESFECHO, e ele nao e neutro: sem deduplicacao, duas assinaturas
    quase identicas pontuam ~1.000 e ~0.92 na MESMA linha, a diferenca fica
    abaixo de `MARGEM_MINIMA_SOBRE_O_SEGUNDO` (0.12) e `identificar_linhas`
    devolve `Casamento(None, ...)`. Acrescentar a pessoa ao acervo a faria PARAR
    de ser reconhecida.
    """

    def test_conteudo_identico_a_entrada_do_acervo_e_descartada(
        self, tmp_path, pixels, calibracao, calibrada_de_verdade
    ):
        """Chave igual: a entrada do acervo nao entra, e a linha fica com o nome
        CALIBRADO."""
        semear(tmp_path, calibrada_de_verdade)  # anonima, mesmo conteudo

        identidades = carregar_identidades(
            [calibrada_de_verdade], AcervoDeIdentidades(tmp_path)
        )
        assert identidades.conhecidas == 1
        assert identidades.assinaturas[0] is calibrada_de_verdade

        calibracao.assinaturas = identidades.assinaturas
        obs = observar_frame(pixels, calibracao)
        assert obs.linhas[LINHA_DA_CONVIVENCIA].nome == "J4guar"

    def test_mesmo_nome_e_conteudo_diferente_a_entrada_do_acervo_e_descartada(
        self, tmp_path, pixels, calibracao, calibrada_de_verdade
    ):
        """A REGRA DO NOME, e o caso que a regra da chave NAO cobre.

        Duas capturas da mesma pessoa em frames diferentes tem chaves
        diferentes. Sem esta regra, a linha ficaria MUDA — a pessoa deixaria de
        ser reconhecida por ter sido acrescentada ao acervo.
        """
        copia = quase_igual(calibrada_de_verdade, nome="J4guar")
        assert chave_da_assinatura(copia) != chave_da_assinatura(
            calibrada_de_verdade
        ), "premissa: a copia tem chave PROPRIA, entao a regra da chave nao pega"
        semear(tmp_path, copia, nome="J4guar")

        identidades = carregar_identidades(
            [calibrada_de_verdade], AcervoDeIdentidades(tmp_path)
        )
        assert identidades.conhecidas == 1, (
            "a copia com o mesmo nome entrou na lista; a linha vai ficar muda "
            "pela margem, que e o pior desfecho de OPER-02"
        )

        calibracao.assinaturas = identidades.assinaturas
        obs = observar_frame(pixels, calibracao)
        assert obs.linhas[LINHA_DA_CONVIVENCIA].nome == "J4guar"

    def test_pessoa_nova_entra_normalmente_e_depois_das_calibradas(
        self, tmp_path, pixels, calibracao, calibrada_de_verdade
    ):
        """Nenhuma regra pode fechar a porta para quem o acervo conhece a mais."""
        outra = assinatura_da_linha(pixels, calibracao, 3)
        semear(tmp_path, outra, nome="TioMad")

        identidades = carregar_identidades(
            [calibrada_de_verdade], AcervoDeIdentidades(tmp_path)
        )
        assert identidades.conhecidas == 2
        assert identidades.assinaturas[0] is calibrada_de_verdade
        assert identidades.assinaturas[1].nome == "TioMad"

    def test_nenhuma_calibrada_e_descartada_por_regra_nenhuma(
        self, tmp_path, pixels, calibracao
    ):
        """T-01-10: a entrada do acervo nao desaloja quem foi digitado a mao.

        As quatro calibradas continuam la, na mesma ordem, mesmo com o acervo
        carregando copias exatas de TODAS elas.
        """
        calibradas = [
            criar_assinatura(nome, _recorte_do_nome(pixels, calibracao, i))
            for i, nome in enumerate(["Korzis", "J4guar", "Kaus", "TioMad"])
        ]
        for assinatura in calibradas:
            semear(tmp_path, assinatura)

        identidades = carregar_identidades(
            calibradas, AcervoDeIdentidades(tmp_path)
        )
        assert identidades.assinaturas == calibradas

    def test_a_anonima_so_deduplica_por_chave(
        self, tmp_path, pixels, calibracao
    ):
        """Duas anonimas de conteudos diferentes CONVIVEM.

        Uma entrada sem nome nao tem o que comparar com a regra do nome. Ela so
        e descartada quando a chave dela ja veio da calibracao.
        """
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, 0))
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, 3))

        identidades = carregar_identidades([], AcervoDeIdentidades(tmp_path))
        assert identidades.conhecidas == 2
        assert identidades.sem_nome == 2

    def test_a_anonima_com_a_chave_de_uma_calibrada_e_descartada(
        self, tmp_path, calibrada_de_verdade
    ):
        """Mesmo sem nome para comparar, a chave sozinha ja fecha o caso."""
        semear(tmp_path, Assinatura("", calibrada_de_verdade.mascara))

        identidades = carregar_identidades(
            [calibrada_de_verdade], AcervoDeIdentidades(tmp_path)
        )
        assert identidades.conhecidas == 1
        assert identidades.sem_nome == 0

    def test_a_string_vazia_nao_reserva_nome_nenhum(
        self, tmp_path, pixels, calibracao, calibrada_de_verdade
    ):
        """A regra do nome nao pode casar `""` com `""` e engolir as anonimas.

        Duas entradas ANONIMAS de conteudos diferentes tem o mesmo "nome" (a
        string vazia). Se a regra do nome nao exigisse nome NAO VAZIO, a segunda
        anonima seria descartada por parecer duplicada da primeira — e o acervo
        so conseguiria guardar UMA pessoa sem nome no mundo inteiro.
        """
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, 0))
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, 2))
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, 3))

        identidades = carregar_identidades(
            [calibrada_de_verdade], AcervoDeIdentidades(tmp_path)
        )
        assert identidades.conhecidas == 4
        assert identidades.sem_nome == 3

    def test_nomes_reservados_da_lista_fundida_nao_carrega_vazio(
        self, tmp_path, pixels, calibracao, calibrada_de_verdade
    ):
        """A string vazia nao pode virar um nome que reserva alguma coisa."""
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, 0))

        identidades = carregar_identidades(
            [calibrada_de_verdade], AcervoDeIdentidades(tmp_path)
        )
        calibracao.assinaturas = identidades.assinaturas

        assert calibracao.nomes_com_assinatura == {"J4guar"}
        assert "" not in calibracao.nomes_com_assinatura
        # A linha 1 e a do `J4guar`, que TEM assinatura: uma linha nao
        # reconhecida nunca pode pegar emprestado o nome de quem a assinatura
        # nao colocou ali.
        assert calibracao.nome_da_linha(1) == "Membro 2"


class TestOResiduoAnonimoDegradaParaSilencio:
    """O caso que a deduplicacao NAO cobre, e a razao de ele ser aceitavel.

    Uma entrada ANONIMA posta a mao, parecida mas nao identica a uma calibrada,
    nao tem nome para comparar: a regra da chave nao pega (as chaves diferem) e a
    regra do nome nao se aplica (nao ha nome). As duas passam do limiar, a margem
    fica abaixo de 0.12 e a linha vira SILENCIO.

    Aceito de proposito, por dois motivos:

      - E o unico desfecho SEGURO da familia. A linha CALA em vez de mentir, que
        e a garantia que o projeto mais preza. Um nome errado manda a party
        socorrer a pessoa errada.
      - Nao e alcancavel pelo caminho normal. Esta fase nunca escreve, e a Fase 2
        so grava depois de nao casar com nada ja gravado (APRE-04). Um
        quase-duplicado anonimo so nasce de uma entrada posta a mao.
    """

    def test_as_duas_premissas_do_caso_sao_medidas_antes_do_desfecho(
        self, pixels, calibracao, calibrada_de_verdade
    ):
        """Sem estas duas medidas, o silencio poderia vir de outra causa.

        Se a copia nao passasse do limiar, a linha receberia o nome calibrado e
        o teste nao estaria provando nada sobre a margem. Se as chaves fossem
        iguais, o caso seria o da deduplicacao por chave, e nao o residuo.
        """
        copia = quase_igual(calibrada_de_verdade)
        assert copia.anonima
        assert chave_da_assinatura(copia) != chave_da_assinatura(
            calibrada_de_verdade
        )

        recorte = _recorte_do_nome(pixels, calibracao, LINHA_DA_CONVIVENCIA)
        pontos = _pontuar_mascara(
            mascara_de_texto(recorte), [calibrada_de_verdade, copia]
        )
        assert pontos[0] > LIMIAR_DE_CASAMENTO, pontos
        assert pontos[1] > LIMIAR_DE_CASAMENTO, pontos
        assert abs(pontos[0] - pontos[1]) < MARGEM_MINIMA_SOBRE_O_SEGUNDO, (
            f"as duas pontuacoes precisam EMPATAR para o caso existir: {pontos}"
        )

    def test_a_linha_CALA_e_o_nome_errado_NAO_sai(
        self, tmp_path, pixels, calibracao, calibrada_de_verdade
    ):
        copia = quase_igual(calibrada_de_verdade)
        semear(tmp_path, copia)  # anonima, posta a mao

        identidades = carregar_identidades(
            [calibrada_de_verdade], AcervoDeIdentidades(tmp_path)
        )
        assert identidades.conhecidas == 2, (
            "o residuo e justamente a entrada que NENHUMA regra descarta"
        )

        recorte = _recorte_do_nome(pixels, calibracao, LINHA_DA_CONVIVENCIA)
        casamento = identificar_linhas(
            {LINHA_DA_CONVIVENCIA: recorte}, identidades.assinaturas
        )[LINHA_DA_CONVIVENCIA]

        assert casamento.nome is None, (
            "o desfecho aceito e SILENCIO; qualquer nome aqui seria um chute"
        )
        assert casamento.nome != "J4guar"

    def test_nenhum_evento_sai_em_nome_de_quem_calou(
        self, tmp_path, pixels, calibracao, calibrada_de_verdade
    ):
        """O silencio atravessa ate o rastreador: zero alerta, rotulo generico."""
        semear(tmp_path, quase_igual(calibrada_de_verdade))
        identidades = carregar_identidades(
            [calibrada_de_verdade], AcervoDeIdentidades(tmp_path)
        )
        calibracao.assinaturas = identidades.assinaturas

        obs = observar_frame(pixels, calibracao)
        # `None` e nao `""`: a linha nao casou com NINGUEM. A string vazia seria
        # "casou com uma anonima", que e outro estado — reconhecida e sem nome.
        assert obs.linhas[LINHA_DA_CONVIVENCIA].nome is None

        _, mortes = mortes_apos_zerar(
            obs,
            LINHA_DA_CONVIVENCIA,
            identidades.configuradas,
            calibracao.nomes,
        )
        assert mortes == [], f"uma linha que calou nao morre. Saiu: {mortes}"


class TestADocstringRespondeAPergunta:
    """A pergunta que o `<phase_specific_direction>` mandou FECHAR POR ESCRITO.

    "O que acontece quando a calibracao e o acervo carregam a mesma pessoa" tem
    de estar respondido onde quem mexe na funcao le, e nao so num plano
    arquivado.
    """

    def test_as_tres_perguntas_estao_respondidas(self):
        texto = carregar_identidades.__doc__ or ""
        assert "--nomes" in texto, "falta POR QUE a calibrada vence"
        assert "-j" in texto, (
            "falta POR QUE a ordem e estrutural, e nao uma condicao"
        )
        assert "MARGEM_MINIMA_SOBRE_O_SEGUNDO" in texto and "0.12" in texto, (
            "falta o NUMERO que torna a regra do nome necessaria"
        )
        assert "anonima" in texto.lower(), (
            "falta dizer o que fica de fora e por que isso e aceitavel"
        )
