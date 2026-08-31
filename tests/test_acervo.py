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
from l2scanner.identidade import Assinatura, criar_assinatura
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
