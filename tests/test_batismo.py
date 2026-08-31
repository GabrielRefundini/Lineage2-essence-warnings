"""O batismo: o scanner PERGUNTA quem e, e o usuario RESPONDE do celular.

A DESCOBERTA QUE DEFINE ESTA FASE, DITA EM VOZ ALTA

O acervo real do usuario tem AGORA duas entradas anonimas (`15caecfa...`, 161
pixels de texto; `f19e3c92...`, 79 pixels), aprendidas em campo pela Fase 2 em
31/08/2026. E o caminho do APRENDIZADO nunca vai perguntar sobre elas:

1. no arranque, `carregar_identidades` funde calibradas e acervo, e as duas
   entram em `cal.assinaturas`;
2. no proximo `extrair`, a linha de cada uma casa ~1.000 contra ela mesma;
3. `Casamento.nome` de uma entrada anonima e a string VAZIA, e nao `None`;
4. `sessao._candidatas_para_aprender` exige `linha.nome is None`;
5. elas nunca sao candidatas, o `Aprendiz` nunca as ve, e nenhum `Aprendizado`
   nasce.

Um gatilho preso apenas ao evento "gravei uma assinatura nova" faria a feature
funcionar perfeitamente na suite e NAO PERGUNTAR NADA no unico acervo real que
existe. Por isso ha DOIS gatilhos — o aprendizado e a varredura de arranque — e
UM marcador so (`perguntado_<chave>`, `O_CREAT|O_EXCL`). D-04 diz "uma pergunta
por assinatura", por ASSINATURA e nao por evento de aprendizado.

`TestOGatilhoDoAprendizadoNaoAlcancaOQueJaEstaNoDisco` e a prova de que a
varredura nao e redundancia. Sem ela, as duas pessoas ficam "Membro N" para
sempre.

OS IDIOMAS SAO COPIADOS, E NAO IMPORTADOS

As fixtures vem de `tests/test_acervo.py` e os falsos de despacho e leitura de
`tests/test_janela_sob_demanda.py`, copiados pela razao que aquele arquivo ja
escreve: importar entre arquivos de teste cria dependencia entre eles, e o que
esta em jogo aqui e a COSTURA, que e onde os erros deste projeto moram.

Todo caso roda dentro de `tmp_path`, com o jogo fechado e sem rede.
"""

from __future__ import annotations

import ast
import json
import os
import time
from dataclasses import replace
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
    DIGITOS_DO_APELIDO,
    Pendente,
    apelido_da_chave,
    apelidos_para_escolher,
    interpretar_batismo,
    montar_pergunta,
    pendentes_do_acervo,
    resolver,
    responder_batismo,
)
from l2scanner.calibracao import Calibracao
from l2scanner.comandos import (
    COMANDOS_DE_MEMBRO,
    _AJUDA,
    Comando,
    Membro,
    interpretar_dinamico,
)
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.identidade import (
    LIMIAR_DE_CASAMENTO,
    Assinatura,
    _pontuar_mascara,
    criar_assinatura,
    mascara_de_texto,
)
from l2scanner.notificador import Categoria
from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento
from l2scanner.sessao import Sessao
from l2scanner.visao import _recorte_do_nome, extrair

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "identidade"

# A linha da party window que fica DESCONHECIDA nos casos do aprendizado: as
# outras tres sao semeadas no acervo. A segunda, e nao a primeira, para que o
# rotulo esperado ("Membro 2") nao possa coincidir por acidente com um
# "Membro 1" vindo de um indice zerado.
LINHA_DA_FATIA = 1

# O telefone de DONO, o mesmo que o resto da suite usa.
DONO = "+5544997077000"
# O de MEMBRO nao pode colidir com o de dono nos 8 digitos finais, que sao os
# unicos comparados.
TELEFONE_DE_MEMBRO = "+5544912345678"
MEMBROS = (Membro(nick="Korzis", telefone=TELEFONE_DE_MEMBRO),)


# ---------------------------------------------------------------------------
# Fixtures e falsos, copiados dos dois arquivos que ja os tem
# ---------------------------------------------------------------------------


@pytest.fixture
def calibracao() -> Calibracao:
    """A calibracao da fixture SEM as assinaturas que ela ja traz.

    O acervo tem de ser a unica fonte de identidade nestes testes: com as
    quatro assinaturas calibradas na mesa, um casamento correto nao provaria
    que a entrada em disco foi lida.
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


def observar_frame(px: np.ndarray, cal: Calibracao):
    return extrair(Frame(pixels=px, indice=0, saude=SaudeDoFrame.OK), cal)


def retrato_da_pasta(pasta: Path) -> dict[str, bytes]:
    """Todo ARQUIVO da pasta com o conteudo, para comparar antes e depois.

    So arquivos: varios casos apontam o acervo para o proprio `tmp_path`, e a
    `.agenda/` da `Sessao` nasce ao lado. Um retrato que tentasse ler a pasta
    irma estaria medindo o cenario do teste, e nao o acervo.
    """
    if not pasta.exists():
        return {}
    return {
        c.name: c.read_bytes() for c in sorted(pasta.iterdir()) if c.is_file()
    }


class DespachanteQueGrava:
    """Grava `(texto, categoria, conversa_alvo)` em vez de mandar para a rede.

    Truthy de proposito: `atender_comandos` e `Sessao._despachar` testam
    `if not despachante` e `if self.despachante`.
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

    @property
    def perguntas(self) -> list:
        """So os despachos que sao a PERGUNTA do batismo.

        Filtrado pela sintaxe que a pergunta ensina, e nao pela contagem total:
        um caso que contasse todos os despachos quebraria no dia em que a
        sessao passasse a falar de outra coisa no mesmo tick, e estaria
        medindo a coisa errada.
        """
        return [texto for texto, _, _ in self.despachos if "/batizar" in texto]


class LeitorDeUmaMensagem:
    """Um `LeitorDeComandos` falso que devolve UMA mensagem crua.

    A mensagem e CRUA (dict, como a API do Chatwoot devolve) de proposito: as
    travas de `comandos_novos` — tipo, nota privada, id repetido, vocabulario e
    autorizacao — tem de rodar de verdade.
    """

    ativo = True

    def __init__(
        self,
        texto: str,
        *,
        telefone: str = DONO,
        conversa="1",
        identificador: int = 7777,
    ) -> None:
        self.telefones = [DONO]
        self.membros = list(MEMBROS)
        self._mensagem = {
            "id": identificador,
            "content": texto,
            "message_type": 0,
            "private": False,
            "sender": {"name": "Ze do Zap", "phone_number": telefone},
            "conversation_id": conversa,
        }

    def ler(self, _monotonico):
        return [self._mensagem]


def responder_pelo_whatsapp(
    texto: str,
    tmp_path,
    *,
    acervo=None,
    assinaturas_vivas=None,
    rastreador=None,
    telefone: str = DONO,
    conversa="1",
    identificador: int = 7777,
    registro=None,
) -> DespachanteQueGrava:
    """Roda `atender_comandos` como o LACO roda, e devolve o que saiu.

    Adaptado do helper `perguntar` de `tests/test_janela_sob_demanda.py` para
    passar `acervo=` e `assinaturas_vivas=`, que sao os parametros novos desta
    fase. `agora` e `datetime` e `monotonico` e float: os dois relogios de
    `atender_comandos` nao sao intercambiaveis.
    """
    from datetime import datetime

    from l2scanner.__main__ import atender_comandos

    despachante = DespachanteQueGrava()
    atender_comandos(
        LeitorDeUmaMensagem(
            texto,
            telefone=telefone,
            conversa=conversa,
            identificador=identificador,
        ),
        registro if registro is not None else RegistroEmDisco(tmp_path / "agenda"),
        [],
        despachante,
        datetime(2026, 8, 31, 20, 30),
        time.monotonic(),
        rastreador,
        acervo=acervo,
        assinaturas_vivas=assinaturas_vivas,
    )
    return despachante


class SilencioParado:
    def ativo(self):
        return False

    def atualizar(self, agora):
        return None


def montar_sessao(
    tmp_path,
    calibracao,
    *,
    acervo,
    despachante=None,
    leituras_para_aprender: int = 3,
    identidades=None,
    rastreador=None,
) -> Sessao:
    """Uma `Sessao` de verdade, com o aprendiz e o acervo ligados."""
    return Sessao(
        cal=calibracao,
        rastreador=rastreador
        or Rastreador(
            nomes=list(calibracao.nomes),
            assinaturas_configuradas=(
                identidades.configuradas if identidades is not None else False
            ),
        ),
        eventos_agendados=[],
        registro=RegistroEmDisco(tmp_path / "agenda"),
        silencio=SilencioParado(),
        despachante=despachante,
        aprendiz=Aprendiz(
            acervo, AjustesDoAprendiz(leituras_para_aprender=leituras_para_aprender)
        ),
        acervo=acervo,
    )


def semear_tres_das_quatro(pasta: Path, px, cal) -> list[str]:
    """Semeia todas as linhas MENOS `LINHA_DA_FATIA`, que fica desconhecida.

    Semear as quatro faria o caso do aprendizado passar sem que NENHUMA
    escrita acontecesse.
    """
    return [
        semear(pasta, assinatura_da_linha(px, cal, indice))
        for indice in range(4)
        if indice != LINHA_DA_FATIA
    ]


def carregar_na_calibracao(cal, pasta: Path):
    identidades = carregar_identidades([], AcervoDeIdentidades(pasta))
    cal.assinaturas = identidades.assinaturas
    return identidades


# ---------------------------------------------------------------------------
# A GUARDA CONTRA PROVA VAZIA, PRIMEIRO
# ---------------------------------------------------------------------------


class TestAGuardaContraProvaVazia:
    """Antes de qualquer coisa: a entrada anonima E reconhecida, e CALA.

    Sem esta afirmacao inicial, "depois do batismo o nome apareceu" passaria
    igualzinho num cenario onde a assinatura nunca casou com nada — e o caso
    estaria provando que o acervo nao funciona, com cara de estar provando que
    o batismo funciona.
    """

    def test_a_entrada_anonima_e_reconhecida_com_nome_VAZIO(
        self, tmp_path, pixels, calibracao
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        carregar_na_calibracao(calibracao, tmp_path)

        linha = observar_frame(pixels, calibracao).linhas[LINHA_DA_FATIA]

        assert linha.confianca_do_nome > 0.9, (
            "ela FOI reconhecida — sem isso o resto do arquivo nao prova nada"
        )
        assert linha.nome == "", (
            "uma entrada anonima tem nome VAZIO, e nao None: e exatamente por "
            "isso que o gatilho do aprendizado nunca a alcanca"
        )

    def test_o_rotulo_exibido_e_Membro_N(self, tmp_path, pixels, calibracao):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        obs = observar_frame(pixels, calibracao)
        rastreador = Rastreador(
            nomes=list(calibracao.nomes),
            assinaturas_configuradas=identidades.configuradas,
        )
        for i in range(15):
            rastreador.observar(obs, -100 + i)

        identidade = rastreador._identidade_por_linha[LINHA_DA_FATIA]
        assert identidade == f"#linha{LINHA_DA_FATIA}"
        assert (
            rastreador._nome_exibido(identidade) == f"Membro {LINHA_DA_FATIA + 1}"
        )


# ---------------------------------------------------------------------------
# A DESCOBERTA: o gatilho do aprendizado nao alcanca o que ja esta no disco
# ---------------------------------------------------------------------------


class TestOGatilhoDoAprendizadoNaoAlcancaOQueJaEstaNoDisco:
    """A prova de que a varredura de arranque NAO e redundancia.

    Este e o caso mais importante do arquivo. Ele afirma o que o acervo real do
    usuario faria hoje: as duas entradas ja gravadas entram na lista viva, sao
    reconhecidas com nome VAZIO, e o `Aprendiz` nunca as ve.

    Quem as alcanca e a varredura de arranque (Tarefa 3), que e a dona do
    marcador. Esta classe prova apenas que ela e NECESSARIA.
    """

    def test_cinquenta_ticks_com_tudo_ja_no_acervo_nao_aprendem_NADA(
        self, tmp_path, pixels, calibracao
    ):
        for indice in range(4):
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        assert len(identidades.assinaturas) == 4, "premissa: as quatro no acervo"
        assert identidades.sem_nome == 4, "premissa: as quatro sem nome"

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )

        for indice in range(50):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            assert resultado.aprendizados == [], (
                f"tick {indice}: uma entrada ja gravada virou candidata de "
                "novo. Se isso acontecer, o acervo incha com uma entrada nova "
                "a cada N ticks para a MESMA pessoa (APRE-04)"
            )

        assert despachante.perguntas == [], (
            "o gatilho do APRENDIZADO nao pode perguntar por elas: elas nunca "
            "produzem Aprendizado. Quem pergunta e a varredura de arranque"
        )

    def test_e_o_disco_continua_intacto_depois_dos_cinquenta_ticks(
        self, tmp_path, pixels, calibracao
    ):
        """Nenhuma entrada nova, e nenhum marcador queimado pelo caminho."""
        for indice in range(4):
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        antes = retrato_da_pasta(tmp_path)

        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=DespachanteQueGrava(),
            identidades=identidades,
        )
        for indice in range(50):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )

        assert retrato_da_pasta(tmp_path) == antes


# ---------------------------------------------------------------------------
# O GATILHO DO APRENDIZADO: pergunta UMA vez, citando a linha
# ---------------------------------------------------------------------------


class TestOAprendizadoPergunta:
    def test_a_enesima_leitura_grava_UMA_entrada_e_manda_UMA_pergunta(
        self, tmp_path, pixels, calibracao
    ):
        conhecidas = semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        assert len(conhecidas) == 3, "premissa: tres conhecidas, uma nao"

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )

        aprendidas = []
        for indice in range(10):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            aprendidas.extend(resultado.aprendizados)

        assert len(aprendidas) == 1, (
            f"uma linha desconhecida, uma entrada. Saiu: {aprendidas}"
        )
        assert len(despachante.perguntas) == 1, (
            f"uma entrada nova, uma pergunta. Saiu: {despachante.perguntas}"
        )

    def test_a_pergunta_cita_o_apelido_e_a_linha_em_BASE_1(
        self, tmp_path, pixels, calibracao
    ):
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )
        aprendidas = []
        for indice in range(10):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            aprendidas.extend(resultado.aprendizados)

        pergunta = despachante.perguntas[0]
        apelido = apelido_da_chave(aprendidas[0].chave)
        assert apelido in pergunta, (
            f"a pergunta nao cita o apelido {apelido!r} da chave gravada; sem "
            f"ele nao ha o que responder.\n{pergunta}"
        )
        assert f"linha {LINHA_DA_FATIA + 1}" in pergunta, (
            "a posicao e citada em BASE 1, como o usuario a ve na tela "
            f"(criterio 1 do ROADMAP).\n{pergunta}"
        )
        assert "/batizar" in pergunta, "a pergunta ensina a sintaxe da resposta"

    def test_a_pergunta_sai_com_Categoria_SEMPRE(
        self, tmp_path, pixels, calibracao
    ):
        """O marcador de D-04 e de MAO UNICA.

        `Categoria.NORMAL` e CORTADA no transporte durante o silencio de
        TvT/Prime, e a mensagem cortada nem entra no outbox — a pergunta seria
        queimada e nunca enviada, sistematicamente, justamente durante o evento
        em que a party mais muda de gente.
        """
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )
        for indice in range(10):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )

        categorias = {
            categoria
            for texto, categoria, _ in despachante.despachos
            if "/batizar" in texto
        }
        assert categorias == {Categoria.SEMPRE}, (
            "a pergunta tem de atravessar o silencio: uma pergunta silenciada "
            f"e uma pergunta perdida PARA SEMPRE. Saiu: {categorias}"
        )


class TestAPerguntaNaoSeRepete:
    def test_mais_vinte_ticks_identicos_nao_perguntam_de_novo(
        self, tmp_path, pixels, calibracao
    ):
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )
        for indice in range(10):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
        depois_da_primeira = len(despachante.perguntas)
        assert depois_da_primeira == 1, "premissa: uma pergunta ja saiu"

        for indice in range(10, 30):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )

        assert len(despachante.perguntas) == depois_da_primeira, (
            "a pergunta repetiu num tick seguinte. O usuario ja reclamou de "
            "spam neste projeto uma vez"
        )

    def test_uma_sessao_NOVA_sobre_a_MESMA_pasta_tambem_nao_pergunta(
        self, tmp_path, pixels, calibracao
    ):
        """O marcador esta em DISCO, e nao em memoria.

        Sem isso, reiniciar o scanner refaria todas as perguntas ja feitas — e
        o usuario reinicia o scanner o tempo todo.
        """
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        primeira = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=primeira,
            identidades=identidades,
        )
        for indice in range(10):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
        assert len(primeira.perguntas) == 1, "premissa: a primeira perguntou"

        # O reinicio: calibracao recarregada do disco, sessao nova, acervo novo
        # sobre a MESMA pasta.
        cal2 = Calibracao.carregar(FIXTURES / "calibracao.json")
        cal2.assinaturas = []
        identidades2 = carregar_na_calibracao(cal2, tmp_path)
        segunda = DespachanteQueGrava()
        sessao2 = montar_sessao(
            tmp_path,
            cal2,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=segunda,
            identidades=identidades2,
        )
        for indice in range(10):
            sessao2.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )

        assert segunda.perguntas == [], (
            "depois de reiniciar, a pergunta saiu de novo: o marcador nao "
            "esta em disco"
        )


class TestSemDespachanteNadaEMarcado:
    """D-05 estendido: nao queimar o marcador quando nao ha para onde mandar.

    Quem roda sem `.env` e sem `--dry-run` — o caminho que `montar_despachante`
    documenta como "o scanner continua util no console" — simplesmente ainda
    nao perguntou, e vai perguntar no dia em que configurar a entrega. Queimar
    o marcador aqui deixaria a pessoa como "Membro N" ate alguem apagar um
    arquivo a mao.
    """

    def test_sem_despachante_o_marcador_nao_aparece_na_pasta(
        self, tmp_path, pixels, calibracao
    ):
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=None,
            identidades=identidades,
        )
        aprendidas = []
        for indice in range(10):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            aprendidas.extend(resultado.aprendizados)

        assert len(aprendidas) == 1, "premissa: a entrada foi gravada mesmo assim"
        marcadores = [
            c.name for c in tmp_path.iterdir() if c.name.startswith("perguntado_")
        ]
        assert marcadores == [], (
            "a pergunta foi QUEIMADA sem sair: o marcador e para sempre, e a "
            f"pessoa ficaria Membro N ate alguem apagar um arquivo. {marcadores}"
        )


# ---------------------------------------------------------------------------
# O COMANDO: existe, e ele e de DONO
# ---------------------------------------------------------------------------


class TestOComandoEDeDono:
    def test_o_comando_existe_no_enum(self):
        assert hasattr(Comando, "BATIZAR")

    def test_o_tripwire_da_ajuda_segue_verde(self):
        assert set(_AJUDA) == set(Comando)

    def test_o_comando_tem_linha_na_ajuda(self):
        linha = _AJUDA[Comando.BATIZAR]
        assert linha.sintaxe.startswith("/batizar")
        assert "apelido" in linha.descricao.lower(), (
            "a descricao precisa dizer de onde vem o apelido: e a unica coisa "
            "nao obvia do comando"
        )

    def test_o_batismo_NAO_e_comando_de_membro(self):
        """Decisao 2 do ROADMAP, ja travada.

        Um nome errado e corrupcao duravel e dificil de notar num acervo que
        nunca e podado e nao tem comando de esquecer — a mesma familia de
        `/corrigir` e `/pegou`. E `COMANDOS_DE_MEMBRO` e LISTA DE INCLUSAO
        justamente para que um comando destrutivo novo NASCA fora do alcance.
        """
        assert Comando.BATIZAR not in COMANDOS_DE_MEMBRO


class TestOCaminhoRealDeLeituraEntregaOComando:
    @pytest.mark.parametrize(
        "texto",
        [
            "/batizar 15caec Mostarda",
            "/batizar-15caec Mostarda",
            ".batizar 15caec Mostarda",
            "/nomear 15caec Mostarda",
        ],
    )
    def test_as_quatro_formas_escritas(self, texto):
        assert interpretar_dinamico(texto, frozenset()) == (
            Comando.BATIZAR,
            "15caec Mostarda",
        ), texto

    def test_a_palavra_sozinha_nao_vira_consulta_de_nick(self):
        """O `return None` dos ramos NAO e redundancia.

        Sem ele o fluxo cai no ramo de consulta logo abaixo, onde
        `_NICK_VALIDO` casa as palavras "batizar" e "nomear", e um personagem
        homonimo transformaria o comando numa consulta dele.
        """
        conhecidos = frozenset({"batizar", "nomear"})
        assert interpretar_dinamico("/batizar", conhecidos) is None
        assert interpretar_dinamico("/nomear", conhecidos) is None


# ---------------------------------------------------------------------------
# A RESPOSTA BATIZA A ASSINATURA CERTA
# ---------------------------------------------------------------------------


class TestARespostaBatizaAAssinaturaCerta:
    def test_o_arquivo_de_nome_nasce_com_o_nick_exato(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        apelido = apelido_da_chave(chave)

        responder_pelo_whatsapp(
            f"/batizar {apelido} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        )

        alvo = tmp_path / f"{PREFIXO_NOME}{chave}"
        assert alvo.exists(), "o irmao nome_<chave> nao foi criado"
        assert alvo.read_text(encoding="utf-8") == "Mostarda"

    def test_a_assinatura_NAO_e_tocada_e_por_isso_a_chave_nao_muda(
        self, tmp_path, pixels, calibracao
    ):
        """D-06, afirmado byte a byte."""
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        arquivo = tmp_path / f"{PREFIXO_ASSINATURA}{chave}.json"
        antes = arquivo.read_bytes()

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        )

        assert arquivo.read_bytes() == antes, (
            "batizar tocou a assinatura. Se ela muda, a chave muda, e o pino "
            "de D-01 deixa de apontar para lugar nenhum"
        )
        assert AcervoDeIdentidades(tmp_path).chaves() == [chave]

    def test_a_resposta_confirma_no_privado_E_no_grupo(
        self, tmp_path, pixels, calibracao
    ):
        """A PERGUNTA foi publica, entao a resposta fecha o circuito no grupo.

        Uma resposta so no privado deixaria a pergunta pendurada no grupo para
        sempre, e o proximo party-mate que tentasse responder cairia no
        `continue` da autorizacao, sem resposta nenhuma.
        """
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )

        despachante = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        )

        assert despachante.alvos == ["1", None], (
            f"a confirmacao tinha que ir para a origem E para o grupo; "
            f"os destinos foram {despachante.alvos}"
        )
        assert "Mostarda" in despachante.textos[0]
        assert "Mostarda" in despachante.textos[1]

    def test_sem_acervo_o_ramo_recusa_e_NAO_ecoa_no_grupo(self, tmp_path):
        """O laco que nao tem acervo responde, e responde so a quem digitou."""
        despachante = responder_pelo_whatsapp(
            "/batizar 15caec Mostarda", tmp_path, acervo=None
        )

        assert despachante.alvos == ["1"]
        assert "identidades" in despachante.textos[0].lower()


class TestONomePassaAValerSemReiniciar:
    """D-08, nas TRES metades. A leitura ingenua e uma linha, e ela nao basta."""

    def _cenario(self, tmp_path, pixels, calibracao):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        rastreador = Rastreador(
            nomes=list(calibracao.nomes),
            assinaturas_configuradas=identidades.configuradas,
        )
        return chave, rastreador

    def test_a_lista_viva_ganha_o_nome(self, tmp_path, pixels, calibracao):
        chave, rastreador = self._cenario(tmp_path, pixels, calibracao)
        antes = [
            a.nome for a in calibracao.assinaturas if chave_da_assinatura(a) == chave
        ]
        assert antes == [""], "premissa: a assinatura viva esta anonima"

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
            rastreador=rastreador,
        )

        depois = [
            a.nome for a in calibracao.assinaturas if chave_da_assinatura(a) == chave
        ]
        assert depois == ["Mostarda"], (
            "a lista viva nao recebeu o nome: a tela continuaria dizendo "
            "Membro N ate o proximo arranque, e o usuario batizaria de novo "
            "achando que falhou"
        )

    def test_o_snapshot_de_nomes_reservados_ganha_o_nome(
        self, tmp_path, pixels, calibracao
    ):
        chave, rastreador = self._cenario(tmp_path, pixels, calibracao)

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
            rastreador=rastreador,
        )

        assert "Mostarda" in rastreador.nomes_reservados

    def test_o_proximo_extrair_sobre_o_MESMO_frame_ja_diz_o_nome(
        self, tmp_path, pixels, calibracao
    ):
        chave, rastreador = self._cenario(tmp_path, pixels, calibracao)

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
            rastreador=rastreador,
        )

        linha = observar_frame(pixels, calibracao).linhas[LINHA_DA_FATIA]
        assert linha.nome == "Mostarda", (
            "o nome tinha que valer no MESMO tick, sem reiniciar nada"
        )


class TestOTerceiroElo:
    """O elo que quase ninguem escreve, e ele e a metade do criterio 2.

    `nomes_reservados` e um SNAPSHOT do arranque, tirado de
    `cal.nomes_com_assinatura`. Ele existe para que um nome que JA TEM
    assinatura visual nunca seja emprestado por POSICAO.
    """

    def test_antes_o_nick_e_emprestado_por_posicao_e_depois_nao(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        # O caso real: o nick esta em `cal.nomes` (o usuario digitou a lista)
        # e NUNCA foi calibrado, entao ele nao esta em `nomes_reservados`.
        outra_linha = 3
        nomes = list(calibracao.nomes)
        nomes[outra_linha] = "Mostarda"
        rastreador = Rastreador(
            nomes=nomes,
            nomes_reservados=set(calibracao.nomes_com_assinatura),
            assinaturas_configuradas=identidades.configuradas,
        )
        assert rastreador.nome_de(outra_linha) == "Mostarda", (
            "premissa: hoje o nick e emprestado por POSICAO para uma linha "
            "que nao e dele"
        )

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
            rastreador=rastreador,
        )

        assert rastreador.nome_de(outra_linha) == f"Membro {outra_linha + 1}", (
            "sem `nomes_reservados.add(nick)` a tela mostra DOIS Mostarda, e "
            "um deles e mentira. E exatamente a familia de defeito que a Fase "
            "1 gastou uma onda inteira consertando, chegando pela porta nova "
            "desta fase"
        )


# ---------------------------------------------------------------------------
# A ESCRITA DO NOME E DEFENSIVA NA ORIGEM
# ---------------------------------------------------------------------------


class TestAEscritaDoNomeEDefensiva:
    """`CHAVE_VALIDA` no ESCRITOR, e nao so na leitura.

    A string vem de uma mensagem de WhatsApp. A validacao aqui e ESTRUTURAL e
    nao redundante: e o que torna travessia de caminho impossivel POR
    CONSTRUCAO, o mesmo argumento que a Fase 1 ja escreveu para o lado da
    leitura. Duas travas na mesma porta e o desenho.
    """

    CHAVE_BOA = "a" * 64

    @pytest.mark.parametrize(
        "chave",
        [
            "",
            "nao-e-hex",
            "A" * 64,  # hex maiusculo nao e a lingua do acervo
            "a" * 63,
            "a" * 65,
            "../" + "a" * 61,
            "a" * 32 + os.sep + "a" * 31,
        ],
    )
    def test_uma_chave_que_nao_e_64_hex_e_invalida_e_nao_escreve_nada(
        self, tmp_path, chave
    ):
        acervo = AcervoDeIdentidades(tmp_path)
        antes = retrato_da_pasta(tmp_path)

        assert acervo.nomear(chave, "Mostarda") == "invalido"
        assert retrato_da_pasta(tmp_path) == antes, (
            "uma chave invalida escreveu arquivo; e por aqui que a travessia "
            "de caminho entraria"
        )

    @pytest.mark.parametrize(
        "nome", ["", "x", "a" * 17, "Mos tarda", "Mostarda\n", "Mos-tarda", "../x"]
    )
    def test_um_nome_fora_do_charset_e_invalido_e_nao_escreve_nada(
        self, tmp_path, nome
    ):
        acervo = AcervoDeIdentidades(tmp_path)
        antes = retrato_da_pasta(tmp_path)

        assert acervo.nomear(self.CHAVE_BOA, nome) == "invalido"
        assert retrato_da_pasta(tmp_path) == antes

    def test_nada_e_escrito_FORA_da_pasta(self, tmp_path):
        """A prova de que a travessia nao acontece, e nao so que ela e recusada."""
        pasta = tmp_path / "identidades"
        vizinha = tmp_path / "vizinha"
        vizinha.mkdir()
        acervo = AcervoDeIdentidades(pasta)

        for chave in ("../vizinha/" + "a" * 52, ".." + os.sep + "a" * 62):
            assert acervo.nomear(chave, "Mostarda") == "invalido"

        assert list(vizinha.iterdir()) == []
        assert retrato_da_pasta(pasta) == {}

    def test_um_nome_valido_grava_e_a_leitura_ja_o_ve(
        self, tmp_path, pixels, calibracao
    ):
        """Guarda contra prova vazia: a escrita FUNCIONA quando deve."""
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        acervo = AcervoDeIdentidades(tmp_path)

        assert acervo.nomear(chave, "Mostarda") == "nomeado"
        assert acervo.nomeados() == {chave: "Mostarda"}
        assert acervo.anonimas() == []
        assert [a.nome for a in acervo.assinaturas()] == ["Mostarda"]

    def test_nomear_de_novo_TROCA_o_conteudo_e_nao_duplica(
        self, tmp_path, pixels, calibracao
    ):
        """D-06: a correcao do BATI-05 e a MESMA operacao do batismo."""
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        acervo = AcervoDeIdentidades(tmp_path)
        acervo.nomear(chave, "Kaus")

        assert acervo.nomear(chave, "Mostarda") == "nomeado"
        assert acervo.nomeados() == {chave: "Mostarda"}
        arquivos = sorted(c.name for c in tmp_path.iterdir())
        assert len(arquivos) == 2, f"sobrou temporario na pasta: {arquivos}"


class TestAnonimasEONomeados:
    def test_anonimas_devolve_so_quem_nao_tem_nome_na_ordem_de_chaves(
        self, tmp_path, pixels, calibracao
    ):
        chaves = [
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, i))
            for i in range(4)
        ]
        acervo = AcervoDeIdentidades(tmp_path)
        acervo.nomear(chaves[0], "Mostarda")

        assert acervo.anonimas() == [c for c in acervo.chaves() if c != chaves[0]]
        assert acervo.nomeados() == {chaves[0]: "Mostarda"}

    def test_pendentes_do_acervo_nascem_SEM_posicao(
        self, tmp_path, pixels, calibracao
    ):
        """A varredura de arranque nao tem posicao nenhuma para citar.

        Aquela entrada foi aprendida numa sessao anterior, possivelmente por
        outra instancia, e nenhuma posicao de agora corresponde a ela.
        Inventar uma seria a primeira mentira do caminho, no recurso inteiro
        que existe para nao mentir.
        """
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, 0))
        pendentes = pendentes_do_acervo(AcervoDeIdentidades(tmp_path))

        assert [p.indice for p in pendentes] == [None]
        assert isinstance(pendentes[0], Pendente)


# ---------------------------------------------------------------------------
# O MODULO NAO CONHECE O MUNDO, E NAO TEM RELOGIO
# ---------------------------------------------------------------------------


class TestOBatismoNaoConheceOMundo:
    """Igualdade de CONJUNTOS sobre os irmaos importados, e nunca um grep.

    A ausencia de `loot` e deliberada e tem precedente escrito: `acervo.py` ja
    se recusou a importar `loot.NICK_VALIDO` porque `loot` importa `agenda`, e
    arrastar essa cadeia para um modulo que precisa NAO ter relogio nenhum
    trocaria uma linha de regex por um acoplamento que o portao AST depois
    teria de raciocinar sobre.
    """

    PROIBIDOS = frozenset(
        {"visao", "sessao", "rastreador", "calibracao", "loot", "agenda", "presenca"}
    )

    @staticmethod
    def _irmaos_importados(caminho: Path) -> set[str]:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        achados: set[str] = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.ImportFrom) and no.level:
                if no.module:
                    achados.add(no.module.split(".")[0])
            elif isinstance(no, ast.Import):
                for alias in no.names:
                    achados.add(alias.name.split(".")[-1])
        return achados

    def test_o_conjunto_de_irmaos_importados(self):
        achados = self._irmaos_importados(RAIZ / "l2scanner" / "batismo.py")
        vazados = achados & self.PROIBIDOS
        assert vazados == set(), (
            f"batismo.py passou a conhecer {sorted(vazados)}. Ele fala "
            "`AcervoDeIdentidades`, `Assinatura` e stdlib, e so"
        )

    def test_a_prova_pega_um_import_proibido_enfiado(self):
        """Guarda contra prova vazia: o detector acha o que deveria achar."""
        import tempfile

        fonte = (RAIZ / "l2scanner" / "batismo.py").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as pasta:
            envenenado = Path(pasta) / "batismo.py"
            envenenado.write_text(fonte + "\nfrom .agenda import x\n", encoding="utf-8")
            assert "agenda" in self._irmaos_importados(envenenado)


class TestBatismoNaoTemRelogioProprio:
    """A guarda estrutural mora em `tests/test_presenca.py`.

    Este caso existe para que quem ler `test_batismo.py` saiba ONDE ela esta:
    um `datetime.now()` que aparecesse no batismo para "so perguntar de novo
    depois de 24 horas" reabriria, por dentro, a repeticao que D-04 fecha por
    construcao.
    """

    def test_o_modulo_esta_na_tupla_do_portao(self):
        from tests.test_presenca import TestSemRelogioProprio

        assert "batismo.py" in TestSemRelogioProprio.MODULOS


class TestOApelidoTemSeisDigitos:
    def test_o_apelido_e_o_prefixo_da_chave(self):
        chave = "15caecfa21ad274e57604cab1f5c44b51b10cff23368245de568c47d513b651c"
        assert apelido_da_chave(chave) == chave[:DIGITOS_DO_APELIDO]
        assert apelido_da_chave(chave) == "15caec"

    def test_as_duas_entradas_REAIS_do_usuario_nao_colidem(self):
        """Medido no acervo real do usuario em 31/08/2026.

        As duas diferem no PRIMEIRO digito, entao ate um apelido de 1 digito
        bastaria. Os seis sao folga para o dia em que a pasta tiver dezenas.
        """
        uma = "15caecfa21ad274e57604cab1f5c44b51b10cff23368245de568c47d513b651c"
        outra = "f19e3c9255f748cd5b4517d9cad268c46f1186d3db75a7154ec79ff1fa96d548"
        assert apelido_da_chave(uma) != apelido_da_chave(outra)


class TestRespondeSemLista:
    """Os dois parametros opcionais sao `None` no laco da agenda.

    La nao existe nem lista viva nem rastreador, porque nao existe tela. O
    disco JA FOI ESCRITO nesse caso: o nome vale a partir do proximo arranque
    do scanner. Ver T-03-07.
    """

    def test_o_disco_e_escrito_mesmo_sem_lista_viva_nem_rastreador(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        acervo = AcervoDeIdentidades(tmp_path)

        resposta = responder_batismo(
            acervo, f"{apelido_da_chave(chave)} Mostarda"
        )

        assert acervo.nomeados() == {chave: "Mostarda"}
        assert "Mostarda" in resposta.privado
        assert resposta.grupo is not None
        assert resposta.grupo != resposta.privado, (
            "o grupo recebe uma redacao CURTA e diferente"
        )


class TestSemTravessaoNoQueOUsuarioLe:
    """cp1252: o travessao vira `?` no console e quebra no WhatsApp.

    Afirmado sobre os textos que este modulo PRODUZ, e nao sobre o fonte: uma
    busca no fonte acusaria a prosa das docstrings, que e livre.
    """

    def test_nem_a_pergunta_nem_as_recusas_tem_travessao(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        acervo = AcervoDeIdentidades(tmp_path)
        apelido = apelido_da_chave(chave)

        textos = [
            montar_pergunta(acervo, pendentes_do_acervo(acervo)),
            responder_batismo(acervo, "").privado,
            responder_batismo(acervo, "zzz Mostarda").privado,
            responder_batismo(acervo, "ffffff Mostarda").privado,
            responder_batismo(acervo, f"{apelido} Mostarda").privado,
        ]
        for texto in textos:
            assert texto is not None
            assert "—" not in texto, f"travessao em: {texto!r}"
            assert "–" not in texto, f"meia risca em: {texto!r}"
            texto.encode("cp1252")


# ---------------------------------------------------------------------------
# TAREFA 2: o PINO, provado contra uma party que se reorganizou
# ---------------------------------------------------------------------------


# Onde mora a entrada B do cenario de reorganizacao.
#
# A entrada A mora em `LINHA_DA_FATIA`, e e ELA que a pergunta cita. Depois da
# reorganizacao as duas trocam de lugar: B passa a ocupar a linha que a
# pergunta citou, e A vai parar aqui.
LINHA_DA_OUTRA = 3


def party_reorganizada(px: np.ndarray, cal: Calibracao, um: int, outro: int):
    """O MESMO frame com os recortes de NOME de duas linhas TROCADOS.

    A reorganizacao e MONTADA e nao suposta: os blocos de pixel do nome trocam
    de lugar de verdade, entao o `extrair` seguinte le a pessoa de `um` na
    posicao de `outro` exatamente como leria se a party window tivesse
    compactado em jogo.

    So o recorte do NOME troca, e nao a linha inteira, porque e o recorte do
    nome que carrega a identidade: HP e MP nao entram na assinatura.
    """
    novo = px.copy()
    a = cal.regiao_do_nome(um)
    b = cal.regiao_do_nome(outro)
    assert (a.altura, a.largura) == (b.altura, b.largura)

    fatia_a = (
        slice(a.topo, a.topo + a.altura),
        slice(a.esquerda, a.esquerda + a.largura),
    )
    fatia_b = (
        slice(b.topo, b.topo + b.altura),
        slice(b.esquerda, b.esquerda + b.largura),
    )
    novo[fatia_a] = px[fatia_b].copy()
    novo[fatia_b] = px[fatia_a].copy()
    return novo


def chave_vista_na_linha(px: np.ndarray, cal: Calibracao, indice: int) -> str:
    """De quem e a assinatura que esta NESTA linha, agora, neste frame.

    Derivada do MATERIAL (a chave e o sha256 do conteudo da mascara), e nao do
    reconhecedor: e assim que o teste consegue afirmar quem esta na linha
    citada ANTES de afirmar o desfecho do batismo.
    """
    return chave_da_assinatura(assinatura_da_linha(px, cal, indice))


def prefixos_presentes(pasta: Path) -> set[str]:
    """Os prefixos de arquivo que existem na pasta, por igualdade de conjuntos.

    Nao e um grep negativo por "indice" ou "mapa": um grep negativo passaria
    por engano no dia em que um segundo estado nascesse com outro nome. Um
    arquivo que nao case nenhum dos tres prefixos entra no conjunto com o nome
    INTEIRO, entao a igualdade acusa e ainda diz qual e.
    """
    conhecidos = (PREFIXO_ASSINATURA, PREFIXO_NOME, PREFIXO_PERGUNTA)
    achados = set()
    for arquivo in pasta.iterdir():
        if not arquivo.is_file():
            continue
        for prefixo in conhecidos:
            if arquivo.name.startswith(prefixo):
                achados.add(prefixo)
                break
        else:
            achados.add(arquivo.name)
    return achados


class TestOPinoAtravessaAReorganizacaoDaParty:
    """A PROVA CENTRAL DO BATI-03, e ela e comportamental.

    A sequencia e a real: a pergunta sai citando uma linha, o usuario volta ao
    jogo, a party se reorganiza, e a resposta chega minutos depois. Se o alvo
    fosse a linha, o nome iria para a pessoa errada em SILENCIO, com a mensagem
    parecendo perfeitamente normal.
    """

    def _cenario(self, tmp_path, pixels, calibracao):
        """Duas entradas anonimas: A na linha da fatia, B na outra linha."""
        chave_a = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        chave_b = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_OUTRA)
        )
        carregar_na_calibracao(calibracao, tmp_path)
        return chave_a, chave_b

    def test_a_pergunta_cita_a_linha_e_a_resposta_vai_para_a_CHAVE(
        self, tmp_path, pixels, calibracao
    ):
        chave_a, chave_b = self._cenario(tmp_path, pixels, calibracao)
        acervo = AcervoDeIdentidades(tmp_path)

        # (1) a pergunta sai citando a linha onde A foi vista.
        pergunta = montar_pergunta(
            acervo, [Pendente(chave=chave_a, indice=LINHA_DA_FATIA)]
        )
        assert f"linha {LINHA_DA_FATIA + 1}" in pergunta

        # (2) a party se REORGANIZA: agora quem esta na linha citada e B.
        reorganizado = party_reorganizada(
            pixels, calibracao, LINHA_DA_FATIA, LINHA_DA_OUTRA
        )
        assert (
            chave_vista_na_linha(reorganizado, calibracao, LINHA_DA_FATIA) == chave_b
        ), (
            "premissa do caso: a entrada B tem de estar MESMO na linha citada "
            "na segunda observacao. Um caso que reorganizasse 'mais ou menos' "
            "e depois afirmasse o desfecho estaria provando outra coisa"
        )

        # (3) a resposta chega, apontando para o apelido de A.
        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_a)} Mostarda",
            tmp_path,
            acervo=acervo,
            assinaturas_vivas=calibracao.assinaturas,
        )

        # A AFIRMACAO E SOBRE O NOME DO ARQUIVO NO ACERVO, e nunca sobre "a
        # linha N ficou com o nome": um caso escrito sobre a linha passaria por
        # ACIDENTE quando a reorganizacao devolvesse a pessoa a mesma posicao.
        assert (tmp_path / f"{PREFIXO_NOME}{chave_a}").read_text(
            encoding="utf-8"
        ) == "Mostarda"
        assert not (tmp_path / f"{PREFIXO_NOME}{chave_b}").exists(), (
            "o nome foi para a entrada que estava na LINHA citada, e nao para "
            "a que a pergunta PINOU. Resolver por posicao batiza a pessoa "
            "errada em silencio, e a mensagem parece perfeitamente normal"
        )

    def test_a_linha_citada_continua_SEM_NOME_depois_do_batismo(
        self, tmp_path, pixels, calibracao
    ):
        """O outro lado da mesma prova, agora na TELA."""
        chave_a, _ = self._cenario(tmp_path, pixels, calibracao)
        reorganizado = party_reorganizada(
            pixels, calibracao, LINHA_DA_FATIA, LINHA_DA_OUTRA
        )

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_a)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
        )

        linhas = observar_frame(reorganizado, calibracao).linhas
        assert linhas[LINHA_DA_FATIA].nome == "", (
            "quem esta AGORA na linha citada ganhou o nome: o alvo virou a "
            "posicao em algum lugar do caminho"
        )
        assert linhas[LINHA_DA_OUTRA].nome == "Mostarda", (
            "e a pessoa certa aparece com o nome onde quer que ela esteja "
            "agora — e o que 'a assinatura diz onde a pessoa esta' significa"
        )


class TestNaoExisteSintaxeQueAlcanceUmaLinha:
    """D-03 nao precisou de trava: ele e uma AUSENCIA.

    `/batizar 3` cai em "apelido desconhecido" porque "3" e so um prefixo hex
    que nao casa chave nenhuma. Ninguem deve "consertar" isso acrescentando um
    ramo que aceite numero de linha.
    """

    @pytest.mark.parametrize(
        "argumento", ["3 Mostarda", "linha3 Mostarda", "#linha3 Mostarda"]
    )
    def test_nenhuma_das_tres_formas_escreve_coisa_alguma(
        self, tmp_path, pixels, calibracao, argumento
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path)
        antes = retrato_da_pasta(tmp_path)

        resposta = responder_batismo(acervo, argumento)

        assert resposta.grupo is None, "uma recusa nao ecoa no grupo"
        assert retrato_da_pasta(tmp_path) == antes, f"{argumento!r} mexeu na pasta"

    def test_um_numero_de_linha_cai_em_apelido_DESCONHECIDO(
        self, tmp_path, pixels, calibracao
    ):
        """O "3" e hex valido; ele so nao aponta para nada."""
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path)

        privado = responder_batismo(acervo, "3 Mostarda").privado

        assert "nao e numero de linha" in privado, (
            "a recusa precisa DIZER que apelido nao e numero de linha: '3' e "
            "exatamente o que um usuario distraido digitaria pensando na "
            f"terceira linha.\n{privado}"
        )

    @pytest.mark.parametrize("argumento", ["linha3 Mostarda", "#linha3 Mostarda"])
    def test_o_que_nao_e_hex_cai_em_MALFORMADO(
        self, tmp_path, pixels, calibracao, argumento
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path)

        privado = responder_batismo(acervo, argumento).privado

        assert "Nao entendi" in privado
        assert "PRIMEIRO" in privado, (
            "o erro humano mais provavel e inverter os dois argumentos, entao "
            f"a recusa tem de dizer qual e qual.\n{privado}"
        )


def par_de_assinaturas_com_prefixo_COMUM(px, cal):
    """Duas assinaturas REAIS cujas chaves comecam igual, e o tamanho do comum.

    QUAL DAS DUAS ESTRATEGIAS DO PLANO FOI USADA, E POR QUE. O plano oferecia
    chamar `resolver` direto com chaves fabricadas — e isso e feito, no
    `TestResolverJamaisDesempata`, porque `resolver` e uma funcao PURA e
    testa-la direto e o caminho certo para o combinatorio, exatamente como a
    Fase 2 alimentou o `Aprendiz` direto com `Candidata`.

    Mas o criterio de aceite tambem pede que a PASTA fique inalterada numa
    recusa ambigua, e isso exige duas entradas de verdade no acervo — o
    `_ler` recalcula a chave a partir do conteudo e descarta o que nao bate,
    entao nao ha como enfiar uma chave inventada la dentro. Por isso este
    helper: ele PROCURA, de forma deterministica, um par que colida.

    A busca vira um bit da mascara de um recorte real por vez e agrupa as
    chaves pelos tres primeiros digitos. Com algumas centenas de variantes o
    par existe com folga (o aniversario sobre 4096 baldes), e a ordem da
    varredura e fixa, entao o par encontrado e sempre o mesmo.
    """
    base = assinatura_da_linha(px, cal, LINHA_DA_FATIA).mascara
    plano = base.flatten()
    baldes: dict[str, tuple[str, Assinatura]] = {}

    for celula in range(min(600, plano.size)):
        virado = plano.copy()
        virado[celula] = 0 if virado[celula] else 1
        assinatura = Assinatura(nome="", mascara=virado.reshape(base.shape))
        chave = chave_da_assinatura(assinatura)
        balde = chave[:3]
        if balde in baldes:
            outra_chave, outra = baldes[balde]
            comum = 0
            while chave[comum] == outra_chave[comum]:
                comum += 1
            return outra, assinatura, comum
        baldes[balde] = (chave, assinatura)

    raise AssertionError(
        "nenhum par de chaves com prefixo comum foi encontrado em 600 "
        "variantes; a busca precisa de mais amostras"
    )


class TestUmPrefixoAmbiguoERecusadoENuncaDesempatado:
    """D-02. O desempate silencioso e a mentira plausivel de sempre.

    Duas assinaturas que comecam igual sao DUAS PESSOAS. Escolher uma delas
    por ordem, por data ou por qualquer outro criterio produz uma mensagem que
    parece normal e batiza a pessoa errada.
    """

    def _acervo_com_o_par(self, tmp_path, pixels, calibracao):
        uma, outra, comum = par_de_assinaturas_com_prefixo_COMUM(
            pixels, calibracao
        )
        acervo = AcervoDeIdentidades(tmp_path)
        assert acervo.gravar(uma) == "criado"
        assert acervo.gravar(outra) == "criado"
        return acervo, chave_da_assinatura(uma), chave_da_assinatura(outra), comum

    def test_a_recusa_cita_TODOS_os_candidatos_e_a_pasta_fica_inalterada(
        self, tmp_path, pixels, calibracao
    ):
        acervo, uma, outra, comum = self._acervo_com_o_par(
            tmp_path, pixels, calibracao
        )
        antes = retrato_da_pasta(tmp_path)

        resposta = responder_batismo(acervo, f"{uma[:comum]} Mostarda")

        candidatos = apelidos_para_escolher((uma, outra))
        for candidato in candidatos:
            assert candidato in resposta.privado, (
                f"a recusa nao cita {candidato!r}. Sem a lista o usuario nao "
                f"tem como agir.\n{resposta.privado}"
            )
        assert "mais digitos" in resposta.privado, (
            "a recusa precisa dizer O QUE FAZER: uma recusa que so diz 'nao' "
            "manda o usuario tentar de novo do mesmo jeito"
        )
        assert retrato_da_pasta(tmp_path) == antes, (
            "um prefixo ambiguo escreveu alguma coisa: em algum lugar do "
            "caminho houve um desempate"
        )

    def test_com_um_digito_a_mais_a_MESMA_chamada_resolve(
        self, tmp_path, pixels, calibracao
    ):
        """A guarda que prova que a recusa era sobre AMBIGUIDADE.

        Sem este caso irmao, a recusa acima passaria igualzinho se o comando
        estivesse simplesmente quebrado.
        """
        acervo, uma, _, comum = self._acervo_com_o_par(tmp_path, pixels, calibracao)

        resposta = responder_batismo(acervo, f"{uma[: comum + 1]} Mostarda")

        assert acervo.nomeados() == {uma: "Mostarda"}, resposta.privado


class TestUmPrefixoDesconhecidoERecusadoDizendoOQueExiste:
    def test_a_recusa_lista_os_apelidos_que_estao_sem_nome(
        self, tmp_path, pixels, calibracao
    ):
        chaves = [
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, i))
            for i in range(3)
        ]
        acervo = AcervoDeIdentidades(tmp_path)
        acervo.nomear(chaves[0], "Titander")

        privado = responder_batismo(acervo, "ffffff Mostarda").privado

        assert "ffffff" in privado, "a recusa diz qual apelido nao existe"
        for chave in chaves[1:]:
            assert apelido_da_chave(chave) in privado, (
                "a recusa lista os apelidos que estao SEM NOME agora; sem "
                f"isso o usuario nao tem como agir.\n{privado}"
            )
        assert apelido_da_chave(chaves[0]) not in privado, (
            "quem ja tem nome nao esta esperando batismo, e listar essa "
            "entrada convidaria um rebatismo que ninguem pediu"
        )


class TestOApelidoEDerivadoENadaEGuardado:
    """D-02: nao existe indice, nao existe mapa. So os tres irmaos."""

    def test_depois_de_uma_pergunta_e_um_batismo_so_ha_os_tres_prefixos(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        acervo = AcervoDeIdentidades(tmp_path)

        montar_pergunta(acervo, pendentes_do_acervo(acervo))
        responder_batismo(acervo, f"{apelido_da_chave(chave)} Mostarda")

        assert prefixos_presentes(tmp_path) == {
            PREFIXO_ASSINATURA,
            PREFIXO_NOME,
            PREFIXO_PERGUNTA,
        }


class TestOPinoAtravessaOReinicio:
    """A pergunta sai numa instancia; o comando e obedecido por OUTRA.

    O apelido continua resolvendo para a mesma chave porque ele e DERIVADO do
    conteudo, e o conteudo nao mudou.
    """

    def test_o_apelido_resolve_igual_numa_instancia_nova(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        quem_perguntou = AcervoDeIdentidades(tmp_path)
        pergunta = montar_pergunta(
            quem_perguntou, pendentes_do_acervo(quem_perguntou)
        )
        apelido = apelido_da_chave(chave)
        assert apelido in pergunta

        # O reinicio, ou a outra instancia do usuario: objeto novo, mesma pasta.
        quem_respondeu = AcervoDeIdentidades(tmp_path)
        responder_batismo(quem_respondeu, f"{apelido} Mostarda")

        assert quem_respondeu.nomeados() == {chave: "Mostarda"}


class TestResolverJamaisDesempata:
    """A funcao PURA, alimentada direto com chaves fabricadas.

    E o caminho certo para o combinatorio, exatamente como a Fase 2 alimentou o
    `Aprendiz` direto com `Candidata`: aqui nao ha disco, nao ha frame e nao ha
    nada a montar, so a pergunta "a que chave este prefixo aponta".
    """

    UMA = "15caecfa" + "0" * 56
    OUTRA = "15caec00" + "1" * 56
    TERCEIRA = "f19e3c92" + "2" * 56
    TODAS = (UMA, OUTRA, TERCEIRA)

    def test_um_so_candidato_resolve(self):
        achado = resolver("f19e", self.TODAS)
        assert (achado.motivo, achado.chave) == ("ok", self.TERCEIRA)

    def test_dois_candidatos_RECUSAM_com_os_dois_na_lista(self):
        achado = resolver("15caec", self.TODAS)
        assert achado.motivo == "ambiguo"
        assert achado.chave is None, "jamais um desempate"
        assert set(achado.candidatos) == {self.UMA, self.OUTRA}

    def test_o_digito_que_separa_resolve(self):
        assert resolver("15caecf", self.TODAS).chave == self.UMA
        assert resolver("15caec0", self.TODAS).chave == self.OUTRA

    def test_nenhum_candidato_e_desconhecido(self):
        achado = resolver("3", self.TODAS)
        assert (achado.motivo, achado.chave) == ("desconhecido", None)

    @pytest.mark.parametrize(
        "prefixo", ["", "linha3", "#linha3", "15CAEC", "15caecg", "a" * 65]
    )
    def test_o_que_nao_e_hex_e_malformado(self, prefixo):
        achado = resolver(prefixo, self.TODAS)
        assert (achado.motivo, achado.chave) == ("malformado", None)

    def test_a_chave_inteira_tambem_e_um_prefixo_valido(self):
        assert resolver(self.UMA, self.TODAS).chave == self.UMA

    def test_apelidos_para_escolher_ESTICA_quando_seis_digitos_empatam(self):
        """A recusa ambigua nao pode virar um beco.

        Duas chaves que compartilham os seis primeiros digitos produziriam uma
        lista com o MESMO apelido duas vezes, e o "mande mais digitos" nao
        teria como ser seguido.
        """
        escolhas = apelidos_para_escolher((self.UMA, self.OUTRA))
        assert len(set(escolhas)) == 2, escolhas
        for escolha, chave in zip(escolhas, (self.UMA, self.OUTRA)):
            assert chave.startswith(escolha)
            assert resolver(escolha, self.TODAS).chave == chave


class TestAGramaticaEUmaSo:
    """`interpretar_batismo` valida na leitura e le no responder.

    Duas gramaticas divergiriam no primeiro ajuste e o comando passaria a
    aceitar o que nao executa.
    """

    INVALIDOS = [
        None,
        "",
        "   ",
        "15caec",  # uma palavra so
        "Mostarda",
        "15caec Mostarda demais",  # tres palavras
        "zzzzzz Mostarda",  # fora do hex
        "15caec M",  # nick de 1 caractere
        "15caec " + "M" * 17,  # nick de 17
        "15caec Mos-tarda",  # fora do charset de nick
        "Mostarda 15caec",  # os dois invertidos
    ]

    @pytest.mark.parametrize("argumento", INVALIDOS)
    def test_a_interpretacao_recusa(self, argumento):
        assert interpretar_batismo(argumento) is None, argumento

    @pytest.mark.parametrize("argumento", INVALIDOS)
    def test_e_o_responder_recusa_O_MESMO_conjunto(
        self, tmp_path, pixels, calibracao, argumento
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path)
        antes = retrato_da_pasta(tmp_path)

        resposta = responder_batismo(acervo, argumento)

        assert "Nao entendi" in resposta.privado, argumento
        assert retrato_da_pasta(tmp_path) == antes, (
            f"{argumento!r} foi recusado pela interpretacao e ESCREVEU pelo "
            "responder: as duas gramaticas divergiram"
        )

    def test_o_apelido_em_maiusculo_e_aceito_e_normalizado(self):
        """Copiar `15CAEC` de algum lugar continua funcionando.

        Isso nao alarga o charset nem um caractere: o `fullmatch` roda sobre a
        forma ja minuscula, e `15CAECG` continua recusado.
        """
        assert interpretar_batismo("15CAEC Mostarda") == ("15caec", "Mostarda")
        assert interpretar_batismo("15CAECG Mostarda") is None

    def test_o_nick_e_preservado_como_digitado(self):
        assert interpretar_batismo("15caec MoStArDa") == ("15caec", "MoStArDa")


# ---------------------------------------------------------------------------
# TAREFA 3: a pergunta que nao vira spam, e o marcador que nao e queimado a toa
# ---------------------------------------------------------------------------


class TestUmaPerguntaPorAssinaturaParaSempre:
    """D-04. O marcador E a decisao, e nunca uma checagem anterior."""

    CHAVE = "a" * 64

    def test_a_primeira_chamada_marca_e_as_seguintes_nao(self, tmp_path):
        acervo = AcervoDeIdentidades(tmp_path)

        assert acervo.marcar_pergunta(self.CHAVE) is True
        assert acervo.marcar_pergunta(self.CHAVE) is False
        assert acervo.marcar_pergunta(self.CHAVE) is False

    def test_uma_instancia_NOVA_sobre_a_mesma_pasta_tambem_nao_marca(
        self, tmp_path
    ):
        assert AcervoDeIdentidades(tmp_path).marcar_pergunta(self.CHAVE) is True
        assert AcervoDeIdentidades(tmp_path).marcar_pergunta(self.CHAVE) is False

    def test_duas_instancias_disputando_produzem_UMA_pergunta(
        self, tmp_path, pixels, calibracao
    ):
        """A premissa do projeto: Yazalaque e Faerlina rodando ao mesmo tempo.

        As duas veem partys DIFERENTES (cada cliente mostra os OUTROS
        membros), entao as duas vao aprender e as duas vao querer perguntar. O
        `O_CREAT|O_EXCL` decide a corrida no kernel.
        """
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        yazalaque = AcervoDeIdentidades(tmp_path)
        faerlina = AcervoDeIdentidades(tmp_path)

        desfechos = [
            yazalaque.marcar_pergunta(chave),
            faerlina.marcar_pergunta(chave),
        ]
        assert sorted(desfechos) == [False, True]

    def test_montar_pergunta_produz_texto_num_e_None_no_outro(
        self, tmp_path, pixels, calibracao
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        yazalaque = AcervoDeIdentidades(tmp_path)
        faerlina = AcervoDeIdentidades(tmp_path)

        primeira = montar_pergunta(yazalaque, pendentes_do_acervo(yazalaque))
        segunda = montar_pergunta(faerlina, pendentes_do_acervo(faerlina))

        assert primeira is not None
        assert segunda is None, (
            "as duas instancias mandaram a mesma pergunta para o mesmo grupo"
        )

    def test_uma_chave_que_nao_e_64_hex_nunca_marca(self, tmp_path):
        acervo = AcervoDeIdentidades(tmp_path)
        antes = retrato_da_pasta(tmp_path)

        for chave in ("", "3", "linha3", "../" + "a" * 61):
            assert acervo.marcar_pergunta(chave) is False, chave

        assert retrato_da_pasta(tmp_path) == antes


class TestFalhaDeDiscoNaoManda:
    """D-05, e ela e o CONTRARIO da agenda. As duas razoes, lado a lado.

    `agenda.RegistroEmDisco.marcar` colapsa `OSError` em True porque aviso
    duplicado vence aviso perdido: a party ignora uma repeticao, mas nao
    adivinha um TvT que ninguem anunciou.

    Aqui e ao contrario. Uma pergunta perdida custa uma pessoa que continua
    como "Membro 4" ate o proximo arranque, e o proximo arranque tenta de novo.
    Uma pergunta REPETIDA repete A CADA TICK, para sempre, porque o marcador
    nunca chega ao disco.
    """

    def _quebrar_o_marcador(self, monkeypatch, pasta: Path):
        """`os.open` que so falha para o marcador desta pasta.

        Patchar a funcao inteira derrubaria a propria pytest junto, e um caso
        que dependesse de permissao real de sistema de arquivos nao rodaria
        igual em duas maquinas. Mesmo idioma de `falhar_dentro_de` na Fase 1.
        """
        real = os.open

        def falso(alvo, *args, **kwargs):
            if str(pasta) in str(alvo) and PREFIXO_PERGUNTA in str(alvo):
                raise OSError("disco cheio (simulado)")
            return real(alvo, *args, **kwargs)

        monkeypatch.setattr(os, "open", falso)

    def test_marcar_devolve_FALSE_quando_o_disco_falha(
        self, tmp_path, monkeypatch
    ):
        acervo = AcervoDeIdentidades(tmp_path)
        self._quebrar_o_marcador(monkeypatch, tmp_path)

        assert acervo.marcar_pergunta("a" * 64) is False, (
            "colapsar OSError em True aqui produziria a mensagem no grupo A "
            "CADA TICK, para sempre, porque o marcador nunca chega ao disco. "
            "Na agenda o colapso e para True pela razao OPOSTA: la aviso "
            "duplicado vence aviso perdido"
        )

    def test_montar_pergunta_devolve_None_quando_o_disco_falha(
        self, tmp_path, pixels, calibracao, monkeypatch
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path)
        self._quebrar_o_marcador(monkeypatch, tmp_path)

        assert montar_pergunta(acervo, pendentes_do_acervo(acervo)) is None

    def test_a_agenda_continua_fazendo_o_CONTRARIO(self, tmp_path, monkeypatch):
        """O par que torna a assimetria visivel, e nao so afirmada aqui."""
        registro = RegistroEmDisco(tmp_path / "agenda")
        real = os.open

        def falso(alvo, *args, **kwargs):
            if str(tmp_path / "agenda") in str(alvo):
                raise OSError("disco cheio (simulado)")
            return real(alvo, *args, **kwargs)

        monkeypatch.setattr(os, "open", falso)

        assert registro.marcar("qualquer-chave") is True, (
            "a agenda manda assim mesmo, e e por isso que o acervo NAO manda: "
            "os dois tri-estados sao opostos de proposito"
        )


class TestODryRunNaoQueimaOMarcador:
    """O incidente de 2026-08-26 19:30, agora numa pasta mais cara.

    Em `--dry-run` o `montar_despachante` devolve um `Despachante` de CONSOLE,
    real e vivo — entao a simulacao PERGUNTA de verdade. Sem `simulando`, ela
    gravaria `perguntado_<chave>` na `.identidades/` COMPARTILHADA e apagaria
    PARA SEMPRE a pergunta do scanner de verdade.
    """

    def test_simulando_marca_sem_encostar_no_disco(
        self, tmp_path, pixels, calibracao
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path, simulando=True)
        antes = retrato_da_pasta(tmp_path)

        pergunta = montar_pergunta(acervo, pendentes_do_acervo(acervo))

        assert pergunta is not None, (
            "o TEXTO e o produto inteiro do modo simulacao: sem ele nao ha o "
            "que imprimir no console"
        )
        assert retrato_da_pasta(tmp_path) == antes, (
            "a simulacao queimou o marcador da instancia real. E a forma "
            "exata do incidente de 2026-08-26 19:30, numa pasta que nao tem "
            "desfazer e nao tem comando de esquecer"
        )

    def test_simulando_pode_perguntar_a_vontade(self, tmp_path):
        acervo = AcervoDeIdentidades(tmp_path, simulando=True)
        chave = "a" * 64

        assert acervo.marcar_pergunta(chave) is True
        assert acervo.marcar_pergunta(chave) is True

    def test_o_scanner_de_verdade_continua_com_a_pergunta_dele(
        self, tmp_path, pixels, calibracao
    ):
        """A guarda que prova que o `simulando` protegeu alguma coisa."""
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        simulacao = AcervoDeIdentidades(tmp_path, simulando=True)
        montar_pergunta(simulacao, pendentes_do_acervo(simulacao))

        real = AcervoDeIdentidades(tmp_path)
        assert montar_pergunta(real, pendentes_do_acervo(real)) is not None


class TestAPerguntaNaoViraEnxurrada:
    """T-03-06. O usuario ja desligou `avisar_no_horario` do Solo Boss por
    volume, e uma pergunta por tick seria muito pior que doze por dia."""

    def test_trezentos_ticks_produzem_UMA_pergunta(
        self, tmp_path, pixels, calibracao
    ):
        """A afirmacao e que o numero NAO CRESCE com o numero de ticks.

        Herdado do molde da Fase 2 (o caso de 300 recusas): um numero magico de
        mensagens estaria medindo a fixture, e nao a cadencia.
        """
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )
        marcos = {}
        for indice in range(300):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            if indice in (9, 99, 299):
                marcos[indice] = len(despachante.perguntas)

        assert marcos == {9: 1, 99: 1, 299: 1}, (
            f"a contagem de perguntas cresceu com os ticks: {marcos}"
        )

    def test_uma_sessao_que_nao_aprende_nada_produz_ZERO_perguntas(
        self, tmp_path, pixels, calibracao
    ):
        for indice in range(4):
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )
        for indice in range(30):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )

        assert despachante.perguntas == []

    def test_duas_assinaturas_no_MESMO_tick_produzem_UM_despacho(
        self, tmp_path, pixels, calibracao
    ):
        """UMA MENSAGEM PARA N ENTRADAS, e isso e decisao de produto.

        E ha um segundo ganho, que e o que torna a divida T-02-18 legivel:
        quando a mesma pessoa foi aprendida duas vezes, as duas entradas
        aparecem como duas linhas da MESMA mensagem, uma embaixo da outra, em
        vez de duas perguntas soltas que o usuario le como dois desconhecidos.
        """
        desconhecidas = (1, 3)
        for indice in range(4):
            if indice not in desconhecidas:
                semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )
        aprendidas = []
        for indice in range(10):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            aprendidas.extend(resultado.aprendizados)

        assert len(aprendidas) == 2, "premissa: duas entradas nasceram"
        assert len(despachante.perguntas) == 1, (
            f"duas bolhas no WhatsApp em vez de uma: {despachante.perguntas}"
        )
        pergunta = despachante.perguntas[0]
        for aprendizado in aprendidas:
            assert apelido_da_chave(aprendizado.chave) in pergunta


class TestAPerguntaAtravessaOSilencioNoTRANSPORTE:
    """Um `Despachante` DE VERDADE, porque o corte mora dentro do `despachar`.

    Um despachante falso que so grava tuplas nunca exercitaria o corte, e o
    caso estaria afirmando a categoria contra si mesmo.
    """

    def _despachante_em_silencio(self, tmp_path):
        from l2scanner.notificador import Despachante

        class NotificadorMudo:
            def enviar(self, texto):
                return None

        despachante = Despachante(
            NotificadorMudo(), arquivo_outbox=tmp_path / "outbox.jsonl"
        )
        despachante.em_silencio = lambda: True
        return despachante

    def test_a_pergunta_passa_e_um_evento_NORMAL_e_cortado(self, tmp_path):
        """O par que prova que a categoria e deliberada, e nao um default.

        O outbox e a prova publica: a mensagem SILENCIADA nao entra nele, e a
        que atravessa entra.
        """
        despachante = self._despachante_em_silencio(tmp_path)

        despachante.despachar("Mostarda morreu", Categoria.NORMAL)
        despachante.despachar("Aprendi 1 pessoa: 15caec", Categoria.SEMPRE)

        assert despachante.silenciados == 1, (
            "o evento NORMAL tinha que ser cortado; sem isso o caso nao prova "
            "que havia silencio nenhum"
        )
        entregues = [
            json.loads(linha)["texto"]
            for linha in (tmp_path / "outbox.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        assert entregues == ["Aprendi 1 pessoa: 15caec"], (
            "a pergunta foi cortada pelo silencio de TvT. O marcador de D-04 e "
            "de MAO UNICA: uma pergunta silenciada e uma pergunta perdida para "
            "sempre, e TvT e justamente quando a party muda de gente"
        )


class TestAVarreduraDeArranque:
    """O caso que DEFINE a fase: as entradas que ja estao no disco.

    Elas nunca produzem `Aprendizado` (ver
    `TestOGatilhoDoAprendizadoNaoAlcancaOQueJaEstaNoDisco`), entao este e o
    unico caminho que as alcanca.
    """

    def _duas_anonimas(self, tmp_path, pixels, calibracao):
        return [
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
            for indice in (LINHA_DA_FATIA, LINHA_DA_OUTRA)
        ]

    def test_duas_entradas_anonimas_produzem_UMA_mensagem_com_os_dois_apelidos(
        self, tmp_path, pixels, calibracao
    ):
        chaves = self._duas_anonimas(tmp_path, pixels, calibracao)
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta(acervo, pendentes_do_acervo(acervo))

        assert pergunta is not None
        for chave in chaves:
            assert apelido_da_chave(chave) in pergunta, pergunta
        assert "/batizar" in pergunta, "a mensagem ensina a sintaxe da resposta"
        assert pergunta.count("Aprendi") == 1, (
            f"duas mensagens coladas em vez de uma:\n{pergunta}"
        )

    def test_o_plural_da_frase_esta_certo_nas_DUAS_formas(
        self, tmp_path, pixels, calibracao
    ):
        """O texto vai para o WhatsApp de quatro a oito pessoas.

        Uma regra de plural por concatenacao acerta o substantivo e erra o
        verbo ("esta" + "s" da "estas"), e o erro so aparece no dia em que
        houver duas assinaturas esperando — que e justamente o dia do acervo
        real do usuario.
        """
        uma = semear(tmp_path, assinatura_da_linha(pixels, calibracao, 0))
        acervo = AcervoDeIdentidades(tmp_path)

        singular = montar_pergunta(acervo, [Pendente(chave=uma)])
        assert "Aprendi 1 pessoa que ainda esta sem nome" in singular, singular

        outra = semear(tmp_path, assinatura_da_linha(pixels, calibracao, 1))
        mais = semear(tmp_path, assinatura_da_linha(pixels, calibracao, 2))
        plural = montar_pergunta(
            acervo, [Pendente(chave=outra), Pendente(chave=mais)]
        )
        assert "Aprendi 2 pessoas que ainda estao sem nome" in plural, plural
        assert "estas" not in plural, plural

    def test_a_varredura_NAO_cita_posicao_nenhuma(
        self, tmp_path, pixels, calibracao
    ):
        """O desvio deliberado do criterio 1, e ele e deliberado.

        Aquelas entradas foram aprendidas numa sessao anterior, possivelmente
        por outra instancia, e nenhuma posicao de AGORA corresponde a elas.
        Inventar uma seria a primeira mentira do caminho, no recurso inteiro
        que existe para nao mentir. Quem cumpre o criterio 1 ao pe da letra e o
        gatilho do APRENDIZADO, que cita.
        """
        self._duas_anonimas(tmp_path, pixels, calibracao)
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta(acervo, pendentes_do_acervo(acervo))

        assert "linha" not in pergunta.lower(), (
            f"a varredura inventou uma posicao:\n{pergunta}"
        )

    def test_rodar_o_arranque_de_novo_nao_produz_mensagem_nenhuma(
        self, tmp_path, pixels, calibracao
    ):
        self._duas_anonimas(tmp_path, pixels, calibracao)
        primeiro = AcervoDeIdentidades(tmp_path)
        assert montar_pergunta(primeiro, pendentes_do_acervo(primeiro)) is not None

        segundo = AcervoDeIdentidades(tmp_path)
        assert montar_pergunta(segundo, pendentes_do_acervo(segundo)) is None

    def test_quem_ja_tem_nome_nunca_entra_na_varredura(
        self, tmp_path, pixels, calibracao
    ):
        chaves = self._duas_anonimas(tmp_path, pixels, calibracao)
        acervo = AcervoDeIdentidades(tmp_path)
        acervo.nomear(chaves[0], "Titander")

        pergunta = montar_pergunta(acervo, pendentes_do_acervo(acervo))

        assert apelido_da_chave(chaves[0]) not in pergunta
        assert apelido_da_chave(chaves[1]) in pergunta

    def test_o_arranque_e_o_tick_dividem_o_MESMO_marcador(
        self, tmp_path, pixels, calibracao
    ):
        """Dois gatilhos, um marcador. D-04 e por ASSINATURA, e nao por evento.

        A sequencia e a de um dia de uso: o scanner sobe e pergunta pelas que
        ja estavam no disco; durante o farm ele aprende mais uma e pergunta por
        ela; e o arranque do dia seguinte nao repete nenhuma das duas.
        """
        semeadas = semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        # (1) O ARRANQUE pergunta pelas tres que ja estavam no disco.
        acervo = AcervoDeIdentidades(tmp_path)
        do_arranque = montar_pergunta(acervo, pendentes_do_acervo(acervo))
        assert do_arranque is not None
        for chave in semeadas:
            assert apelido_da_chave(chave) in do_arranque

        # (2) O TICK aprende a quarta e pergunta SO por ela.
        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=acervo,
            despachante=despachante,
            identidades=identidades,
        )
        aprendidas = []
        for indice in range(10):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            aprendidas.extend(resultado.aprendizados)

        assert len(despachante.perguntas) == 1, "premissa: o tick perguntou"
        do_tick = despachante.perguntas[0]
        assert apelido_da_chave(aprendidas[0].chave) in do_tick
        for chave in semeadas:
            assert apelido_da_chave(chave) not in do_tick, (
                "o tick repetiu uma pergunta que o ARRANQUE ja tinha feito: os "
                "dois gatilhos nao estao dividindo o mesmo marcador"
            )

        # (3) O ARRANQUE SEGUINTE nao repete nenhuma das duas.
        novo = AcervoDeIdentidades(tmp_path)
        assert montar_pergunta(novo, pendentes_do_acervo(novo)) is None, (
            "o arranque seguinte repetiu o que o tick ja perguntou"
        )

    def test_sem_nada_anonimo_o_arranque_nao_manda_mensagem_nenhuma(
        self, tmp_path, pixels, calibracao
    ):
        """Quem so tem gente batizada nao recebe pergunta no arranque.

        E a guarda contra a varredura virar uma linha de ruido por reinicio
        para quem ja respondeu tudo.
        """
        chaves = self._duas_anonimas(tmp_path, pixels, calibracao)
        acervo = AcervoDeIdentidades(tmp_path)
        for chave, nome in zip(chaves, ("Mostarda", "Titander")):
            assert acervo.nomear(chave, nome) == "nomeado"

        assert pendentes_do_acervo(acervo) == []
        assert montar_pergunta(acervo, pendentes_do_acervo(acervo)) is None


class TestDepoisDeUmDryRunODiscoMostraAAssimetria:
    """As duas metades juntas, e elas parecem contraditorias ate serem lidas.

    `gravar` NAO e simulado: a entrada que a simulacao escreve e byte a byte a
    que o scanner de verdade escreveria, e o `O_EXCL` faz a segunda receber
    `ja_existia`. O MARCADOR e simulado, porque ele e um recurso de uma vez so
    e consumi-lo nao tem desfazer.
    """

    def _sessao_simulada(self, tmp_path, pixels, calibracao):
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path, simulando=True),
            despachante=despachante,
            identidades=identidades,
        )
        aprendidas = []
        for indice in range(10):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            aprendidas.extend(resultado.aprendizados)
        return aprendidas, despachante

    def test_a_assinatura_FICA_e_o_marcador_NAO(
        self, tmp_path, pixels, calibracao
    ):
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        aprendidas, despachante = self._sessao_simulada(
            tmp_path, pixels, calibracao
        )

        assert len(aprendidas) == 1, "premissa: a simulacao aprendeu alguem"
        chave = aprendidas[0].chave
        assert (tmp_path / f"{PREFIXO_ASSINATURA}{chave}.json").exists(), (
            "o gravar NAO e simulado, e prometer que nada e escrito na "
            ".identidades/ seria mentira"
        )
        assert not (tmp_path / f"{PREFIXO_PERGUNTA}{chave}").exists(), (
            "a simulacao queimou o marcador do scanner de verdade"
        )
        assert len(despachante.perguntas) == 1, (
            "e a simulacao IMPRIME a pergunta: e o produto inteiro do modo"
        )

    def test_na_sequencia_dry_run_e_depois_real_a_varredura_e_quem_salva(
        self, tmp_path, pixels, calibracao
    ):
        """O efeito colateral CONHECIDO e COBERTO, e nao um bug a consertar.

        Uma entrada criada por um `--dry-run` existe em disco de verdade.
        Quando o scanner real aprender a mesma pessoa, `gravar` devolve
        `ja_existia`, e o gatilho do aprendizado so pergunta em `criado` —
        entao ele NAO pergunta naquele tick. Quem salva a pergunta e a
        varredura do proximo arranque.

        Ninguem deve "consertar" isso fazendo `ja_existia` perguntar tambem.
        """
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        self._sessao_simulada(tmp_path, pixels, calibracao)

        # Agora o scanner DE VERDADE, sobre a mesma pasta e o mesmo frame.
        cal2 = Calibracao.carregar(FIXTURES / "calibracao.json")
        cal2.assinaturas = []
        identidades2 = carregar_na_calibracao(cal2, tmp_path)
        despachante = DespachanteQueGrava()
        acervo = AcervoDeIdentidades(tmp_path)
        sessao = montar_sessao(
            tmp_path,
            cal2,
            acervo=acervo,
            despachante=despachante,
            identidades=identidades2,
        )
        aprendidas = []
        for indice in range(10):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            aprendidas.extend(resultado.aprendizados)

        assert [a.desfecho for a in aprendidas] == [], (
            "a entrada ja estava em disco pelo dry-run, entao ela nem chega a "
            "ser candidata: a lista viva do arranque ja a carregava"
        )
        assert despachante.perguntas == [], (
            "o tick nao pergunta neste caso, e isso e o esperado"
        )

        # E a varredura do arranque seguinte e quem pergunta.
        seguinte = AcervoDeIdentidades(tmp_path)
        pergunta = montar_pergunta(seguinte, pendentes_do_acervo(seguinte))
        assert pergunta is not None, (
            "a varredura de arranque e a rede que pega toda pergunta que nao "
            "saiu, e ela nao se importa com qual processo gravou a entrada"
        )


class TestSemDespachanteONemOArranqueNemOTickMarcam:
    def test_o_arranque_sem_despachante_nao_marca(
        self, tmp_path, pixels, calibracao
    ):
        """A trava e o `if despachante is not None` do laco, e nao o acervo.

        `montar_pergunta` MARCA. Chama-la sem despachante queimaria o marcador
        de uma pergunta que nao vai para lugar nenhum, e o marcador e para
        sempre.
        """
        import inspect

        from l2scanner import __main__ as principal

        fonte = inspect.getsource(principal.laco_principal)
        arvore = ast.parse(fonte)
        chamadas = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name)
            and no.func.id == "montar_pergunta"
        ]
        assert chamadas, "laco_principal nao varre o acervo no arranque"

        guardas = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.If)
            and any(
                isinstance(dentro, ast.Call)
                and isinstance(dentro.func, ast.Name)
                and dentro.func.id == "montar_pergunta"
                for dentro in ast.walk(no)
            )
            and "despachante" in ast.dump(no.test)
        ]
        assert guardas, (
            "a varredura de arranque nao esta atras de um `if despachante`: "
            "ela queimaria o marcador de uma pergunta que nao vai para lugar "
            "nenhum, e quem roda sem .env ficaria com a pessoa como Membro N "
            "ate alguem apagar um arquivo a mao"
        )


class TestOsDoisLacosPassamOAcervo:
    """A familia de defeito que este projeto ja pagou DUAS vezes.

    O marcador `comando_<id>` da `.agenda/` e COMPARTILHADO: exatamente uma
    instancia obedece cada comando. Se o laco da agenda receber a mensagem
    primeiro e nao tiver acervo, ele consome o marcador, responde "nao consigo
    mexer nas identidades agora" e o batismo do usuario e PERDIDO.

    LE O FONTE, e nao o comportamento, pela mesma razao do portao irmao em
    `tests/test_janela_sob_demanda.py`: os lacos tem `while True` e captura de
    tela dentro.
    """

    def _chamada(self, nome_do_laco) -> ast.Call:
        import inspect

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
    def test_os_dois_passam_acervo(self, laco):
        nomeados = {palavra.arg for palavra in self._chamada(laco).keywords}
        assert "acervo" in nomeados, (
            f"{laco} nao passa `acervo` para atender_comandos: se ele obedecer "
            "o comando primeiro, o batismo do usuario e consumido e perdido"
        )

    @pytest.mark.parametrize("laco", ["laco_principal", "laco_da_agenda"])
    def test_o_que_e_passado_e_a_VARIAVEL_e_nao_um_None(self, laco):
        """Guarda contra o conserto preguicoso.

        `acervo=None` satisfaria o teste acima e deixaria o defeito inteiro de
        pe: a chamada existe, o comando responde, e a resposta e sempre "nao
        consigo mexer nas identidades agora".
        """
        chamada = self._chamada(laco)
        passado = next(p.value for p in chamada.keywords if p.arg == "acervo")
        assert isinstance(passado, ast.Name), (
            f"{laco} passa um literal para `acervo` em vez do acervo de verdade"
        )

    def test_o_laco_principal_passa_tambem_a_lista_viva(self):
        """So o principal: no laco da agenda nao existe tela."""
        chamada = self._chamada("laco_principal")
        nomeados = {palavra.arg for palavra in chamada.keywords}
        assert "assinaturas_vivas" in nomeados, (
            "sem a lista viva o nome so vale no proximo arranque, e o usuario "
            "batiza de novo achando que falhou (D-08)"
        )


class TestOsDoisAcervosNascemComSimulando:
    """O `--dry-run` alcanca os DOIS lacos, entao os dois construtores pagam."""

    @pytest.mark.parametrize("laco", ["laco_principal", "laco_da_agenda"])
    def test_o_acervo_e_construido_com_simulando(self, laco):
        import inspect

        from l2scanner import __main__ as principal

        arvore = ast.parse(inspect.getsource(getattr(principal, laco)))
        construcoes = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name)
            and no.func.id == "AcervoDeIdentidades"
        ]
        assert construcoes, f"{laco} nao constroi AcervoDeIdentidades"
        for construcao in construcoes:
            nomeados = {palavra.arg for palavra in construcao.keywords}
            assert "simulando" in nomeados, (
                f"o AcervoDeIdentidades de {laco} nasce sem `simulando`: um "
                "--dry-run ao lado do scanner de verdade queimaria as "
                "perguntas dele para sempre"
            )


class TestAFraseDoDryRunEVERDADE:
    """Ela ja foi consertada uma vez neste projeto. Nao piorar de novo.

    A tentacao e escrever que nada e gravado tambem na `.identidades/`, e isso
    e FALSO: o `Aprendiz` roda em `--dry-run` e `acervo.gravar` escreve
    `assinatura_*` na pasta compartilhada. Aquela frase reintroduziria
    exatamente a promessa mentirosa que este bloco existe para consertar.
    """

    def _frase(self, caplog):
        import argparse
        import logging

        from l2scanner.__main__ import montar_despachante

        args = argparse.Namespace(dry_run=True)
        with caplog.at_level(logging.INFO, logger="l2scanner"):
            montar_despachante(args)
        return "\n".join(r.getMessage() for r in caplog.records)

    def test_a_frase_fala_de_PERGUNTA(self, caplog):
        frase = self._frase(caplog)
        assert "pergunta" in frase.lower(), (
            f"o --dry-run nao conta o que o `simulando` do acervo garante:\n{frase}"
        )

    def test_a_frase_NAO_promete_que_nada_e_gravado_na_identidades(self, caplog):
        frase = self._frase(caplog).lower()
        for mentira in (
            "nada e gravado em .identidades",
            "nada e gravado na .identidades",
            "nada e escrito em .identidades",
        ):
            assert mentira not in frase, (
                f"a frase promete o que nao cumpre: o gravar NAO e simulado.\n{frase}"
            )


# ---------------------------------------------------------------------------
# BATI-04: O NOME QUE JA E DE OUTRA PESSOA
# ---------------------------------------------------------------------------

# A linha da fixture que vira a entrada A destes casos. A entrada B continua
# sendo `LINHA_DA_FATIA`, que e a que o resto do arquivo ja usa.
#
# DUAS LINHAS DO MESMO FRAME REAL, e nao duas assinaturas fabricadas: o que
# BATI-04 decide e sobre o NOME, mas o alvo continua sendo resolvido pelo
# apelido, e um apelido so e realista se a chave vier de um recorte de verdade.
LINHA_DE_A = 0


def duas_entradas(tmp_path, pixels, calibracao, nome_de_a=None):
    """As entradas A e B semeadas A MAO, e a garantia de que os apelidos diferem.

    O par e semeado sem passar por caminho de escrita de producao nenhum, no
    idioma de `semear`: o cenario de partida do BATI-04 nao pode depender da
    feature que ele testa.

    A AFIRMACAO DOS APELIDOS DISTINTOS NAO E ENFEITE. Se os seis digitos
    empatassem, `resolver` devolveria `ambiguo` e todo caso desta secao passaria
    a provar a recusa ERRADA, com cara de estar provando BATI-04.
    """
    chave_a = semear(
        tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DE_A), nome_de_a
    )
    chave_b = semear(
        tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
    )
    assert apelido_da_chave(chave_a) != apelido_da_chave(chave_b), (
        "os apelidos de A e B empataram nos seis digitos: estes casos "
        "passariam a exercitar a recusa AMBIGUA e nao a de nome duplicado"
    )
    return chave_a, chave_b


class TestONomeQueJaEDeOutraPessoa:
    """BATI-04 e D-07: um nome e um recurso EXCLUSIVO a partir desta fase.

    Dar um nome a uma entrada TIRA esse nome de todas as outras. Sem esta
    recusa, duas assinaturas de pessoas DIFERENTES sairiam com o mesmo nome em
    dois alertas, e nao haveria como saber qual e qual — a mentira plausivel de
    sempre, chegando pela porta nova do batismo.
    """

    def test_batizar_B_com_o_nome_de_A_e_RECUSADO_e_nada_e_escrito(
        self, tmp_path, pixels, calibracao
    ):
        """As TRES afirmacoes, e nao so a recusa.

        Um caso que afirmasse apenas o texto deixaria passar uma implementacao
        que recusa por fora e escreve por dentro.
        """
        chave_a, chave_b = duas_entradas(
            tmp_path, pixels, calibracao, nome_de_a="Mostarda"
        )
        antes = retrato_da_pasta(tmp_path)

        despachante = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_b)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        )

        assert not (tmp_path / f"{PREFIXO_NOME}{chave_b}").exists(), (
            "a recusa escreveu o nome mesmo assim: as duas entradas ficariam "
            "chamadas Mostarda e os alertas viravam ambiguos"
        )
        assert (tmp_path / f"{PREFIXO_NOME}{chave_a}").read_text(
            encoding="utf-8"
        ) == "Mostarda", "a entrada que JA tinha o nome nao pode ser tocada"
        assert retrato_da_pasta(tmp_path) == antes, (
            "a pasta mudou numa recusa. Nada, byte a byte, pode mudar quando "
            "o batismo e recusado"
        )
        assert apelido_da_chave(chave_a) in despachante.textos[0]

    def test_a_recusa_diz_QUAL_entrada_tem_o_nome_e_COMO_liberar(
        self, tmp_path, pixels, calibracao
    ):
        """A SAIDA DE T-02-07 mora aqui, e em nenhum outro lugar.

        Um recorte contaminado (algo claro por cima do nome) pontua 0.0 contra
        tudo, passa no veto de D-02 e pode ter sido aprendido. Se o usuario
        responder a pergunta dele com `Mostarda`, o nome fica QUEIMADO: quando
        a Mostarda de verdade for aprendida, o batismo dela cai exatamente
        nesta recusa.

        Nao ha comando de esquecer no v1 (adiado na Fase 1, e em Deferred Ideas
        do CONTEXT), entao a unica saida e batizar a entrada de lixo com outro
        nome. Esta mensagem e o unico lugar onde o usuario vai procurar por ela;
        uma recusa que so dissesse "esse nome ja e de outra" seria um beco.
        """
        chave_a, chave_b = duas_entradas(
            tmp_path, pixels, calibracao, nome_de_a="Mostarda"
        )

        texto = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_b)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        ).textos[0]

        assert apelido_da_chave(chave_a) in texto, (
            "sem o apelido da entrada DONA o usuario nao tem sobre o que agir"
        )
        assert "/batizar" in texto, (
            "a recusa tem de ensinar a saida com o unico comando que existe"
        )
        assert "com outro nome" in texto, (
            "a saida e batizar a OUTRA entrada com outro nome; sem essa frase "
            "a recusa e um beco sem saida num acervo sem comando de esquecer"
        )
        assert "Nada mudou" in texto

    def test_a_recusa_carrega_a_leitura_de_T0218(
        self, tmp_path, pixels, calibracao
    ):
        """A divida T-02-18 vira LEGIVEL, e nao resolvida.

        Medido na Fase 2: 42 celulas de drift dao 0.7531 e nada nasce; 43 dao
        0.7492 e uma SEGUNDA entrada da mesma pessoa nasce. Quando isso
        acontece, o usuario tenta dar o mesmo nome as duas e cai aqui. Sem a
        frase que diz que a segunda ficar sem nome NAO FAZ MAL, ele conclui que
        o scanner esta quebrado e fica tentando.
        """
        _, chave_b = duas_entradas(
            tmp_path, pixels, calibracao, nome_de_a="Mostarda"
        )

        texto = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_b)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        ).textos[0]

        assert "aprendi o rosto dela duas vezes" in texto, (
            "a recusa tem de dizer em voz alta o que provavelmente aconteceu"
        )
        assert "nunca vira sujeito de alerta" in texto, (
            "e tem de dizer que a segunda sem nome nao faz mal: assinatura "
            "anonima e reconhecida e nunca vira sujeito de alerta (APRE-03)"
        )

    def test_a_recusa_NAO_ecoa_no_grupo(self, tmp_path, pixels, calibracao):
        """As recusas sao entre quem digitou e o scanner."""
        _, chave_b = duas_entradas(
            tmp_path, pixels, calibracao, nome_de_a="Mostarda"
        )

        despachante = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_b)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        )

        assert despachante.alvos == ["1"], (
            f"a recusa vazou para o grupo: {despachante.alvos}"
        )

    def test_a_comparacao_IGNORA_a_caixa(self, tmp_path, pixels, calibracao):
        """`mostarda` contra `Mostarda` tambem e recusado.

        POR QUE SER MAIS ESTRITO AQUI NAO CONTRADIZ `carregar_identidades`, que
        compara nomes por igualdade EXATA: la a pergunta e "esta entrada do
        acervo duplica uma CALIBRADA?", e um erro para o lado frouxo custa
        silencio. Aqui a pergunta e "este nome ja esta ocupado?", e um erro para
        o lado frouxo custa duas entradas chamadas `Mostarda` e `mostarda` —
        que qualquer humano lendo um alerta le como a MESMA pessoa. A regra
        estrita e um subconjunto da frouxa: ela so RECUSA mais, e recusar mais
        nao pode produzir um nome errado.
        """
        chave_a, chave_b = duas_entradas(
            tmp_path, pixels, calibracao, nome_de_a="Mostarda"
        )
        antes = retrato_da_pasta(tmp_path)

        texto = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_b)} mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        ).textos[0]

        assert not (tmp_path / f"{PREFIXO_NOME}{chave_b}").exists(), (
            "duas entradas chamadas Mostarda e mostarda produziriam dois "
            "alertas com nomes que so diferem na caixa, e um humano lendo o "
            "grupo nao tem como saber que sao pessoas diferentes"
        )
        assert apelido_da_chave(chave_a) in texto
        assert retrato_da_pasta(tmp_path) == antes

    def test_a_recusa_cita_o_nome_COMO_ESTA_GRAVADO_e_nao_como_foi_digitado(
        self, tmp_path, pixels, calibracao
    ):
        """A recusa nao pode descrever um estado que nao existe.

        Quem digita `mostarda` recebe uma recusa sobre a entrada que se chama
        `Mostarda`. Dizer "o nome mostarda ja e da assinatura 0dcf6f" seria
        falso sobre o disco, e mandaria o usuario procurar por uma grafia que
        nao esta la — no recurso inteiro que existe para nao mentir.

        E a razao da recusa precisa aparecer, porque sem ela o usuario le duas
        strings diferentes e conclui que o scanner esta quebrado.
        """
        chave_a, chave_b = duas_entradas(
            tmp_path, pixels, calibracao, nome_de_a="Mostarda"
        )

        texto = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_b)} mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        ).textos[0]

        assert "o nome Mostarda ja e" in texto, (
            f"a recusa citou a grafia DIGITADA e nao a GRAVADA: {texto}"
        )
        assert "a caixa nao conta" in texto, (
            "a recusa mostra duas grafias diferentes e nao diz por que elas "
            "sao o mesmo nome"
        )

    def test_rebatizar_a_PROPRIA_entrada_em_outra_caixa_e_ACEITO(
        self, tmp_path, pixels, calibracao
    ):
        """A excecao de D-07 e o PROPRIO alvo, e sem ela nada se corrige.

        A entrada X batizada `kaus` recusada como duplicata DELA MESMA deixaria
        a correcao de caixa impossivel — e correcao de caixa e exatamente o
        conserto mais provavel depois de um batismo digitado no celular.
        """
        chave_a, _ = duas_entradas(tmp_path, pixels, calibracao, nome_de_a="kaus")

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_a)} Kaus",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        )

        assert (tmp_path / f"{PREFIXO_NOME}{chave_a}").read_text(
            encoding="utf-8"
        ) == "Kaus", (
            "a entrada foi recusada como duplicata dela mesma: a correcao de "
            "caixa ficou impossivel (D-07)"
        )


# ---------------------------------------------------------------------------
# BATI-05: O BATISMO ERRADO SE CONSERTA PELA MESMA PORTA
# ---------------------------------------------------------------------------


class TestOBatismoErradoSeConsertaPelaMesmaPorta:
    """BATI-05 e D-06: corrigir e a MESMA operacao, e nao um caminho segundo.

    Um segundo comando `/corrigir-<apelido> <nick>` teria a MESMA
    implementacao com outro nome, e os dois divergiriam na primeira vez que
    alguem mexesse num deles sem lembrar do outro — a forma de defeito que este
    projeto ja nomeou em `autorizado_para`, em `telefone_equivalente` e em
    `membro_do_remetente`.

    O que muda entre batizar e corrigir nao e a operacao, e a RESPOSTA.
    """

    def test_corrigir_grava_o_nome_novo_e_a_assinatura_fica_INTACTA(
        self, tmp_path, pixels, calibracao
    ):
        chave_a, _ = duas_entradas(
            tmp_path, pixels, calibracao, nome_de_a="Mostarda"
        )
        assinatura = tmp_path / f"{PREFIXO_ASSINATURA}{chave_a}.json"
        antes = assinatura.read_bytes()
        quantas_antes = len(AcervoDeIdentidades(tmp_path).chaves())

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_a)} Titander",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        )

        assert (tmp_path / f"{PREFIXO_NOME}{chave_a}").read_text(
            encoding="utf-8"
        ) == "Titander"
        assert assinatura.read_bytes() == antes, (
            "a correcao tocou a assinatura. Se ela muda, a chave muda, e o "
            "acervo passa a ter DUAS entradas para a mesma pessoa (D-06)"
        )
        assert len(AcervoDeIdentidades(tmp_path).chaves()) == quantas_antes, (
            "o numero de entradas mudou numa correcao: uma entrada por pessoa "
            "e o criterio 5 inteiro"
        )

    def test_a_resposta_da_correcao_cita_o_nome_ANTIGO_e_o_NOVO(
        self, tmp_path, pixels, calibracao
    ):
        """Sem o antigo, quem digitou nao confere que corrigiu a entrada certa.

        O mesmo raciocinio ja escrito no `.pegou`, cuja resposta sempre diz o
        DIA de volta para quem digitou conferir na hora que acertou o boss.
        """
        chave_a, _ = duas_entradas(
            tmp_path, pixels, calibracao, nome_de_a="Mostarda"
        )

        texto = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_a)} Titander",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        ).textos[0]

        assert "Mostarda" in texto, "a resposta nao diz o que a entrada ERA"
        assert "Titander" in texto
        assert "livre" in texto, (
            "a resposta tem de dizer que o nome antigo ficou LIVRE: e a "
            "informacao que fecha a saida de T-02-07"
        )

    def test_o_nome_antigo_e_LIBERADO_e_serve_para_a_outra_entrada(
        self, tmp_path, pixels, calibracao
    ):
        """O criterio 5 inteiro, numa sequencia so.

        Se o nome nao fosse liberado, a terceira chamada seria recusada — e o
        usuario que errou uma vez ficaria com o nome queimado para sempre.
        """
        chave_a, chave_b = duas_entradas(
            tmp_path, pixels, calibracao, nome_de_a="Mostarda"
        )
        acervo = AcervoDeIdentidades(tmp_path)

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_a)} Titander",
            tmp_path,
            acervo=acervo,
        )
        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_b)} Mostarda",
            tmp_path,
            acervo=acervo,
            identificador=7778,
        )

        nomeados = AcervoDeIdentidades(tmp_path).nomeados()
        assert nomeados == {chave_a: "Titander", chave_b: "Mostarda"}, (
            "no fim tem de haver DUAS entradas, uma Titander e uma Mostarda: "
            f"uma entrada por pessoa. Achado: {nomeados}"
        )


class TestACorrecaoValeNoMesmoTickNasDuasDirecoes:
    """D-08 na correcao: o nome NOVO entra e o ANTIGO tem de SAIR da lista viva.

    A metade que quase ninguem escreve e a segunda. Uma implementacao que
    fizesse `append` em vez de substituir deixaria as duas convivendo, e duas
    assinaturas quase iguais se sombreiam pela MARGEM: a pessoa pararia de ser
    reconhecida, em silencio, que e a pior familia de defeito deste workstream.
    """

    def _cenario(self, tmp_path, pixels, calibracao):
        chave_a, _ = duas_entradas(
            tmp_path, pixels, calibracao, nome_de_a="Mostarda"
        )
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        vivos = [
            a.nome
            for a in calibracao.assinaturas
            if chave_da_assinatura(a) == chave_a
        ]
        assert vivos == ["Mostarda"], (
            f"premissa: a lista viva comeca com Mostarda. Achado: {vivos}"
        )
        rastreador = Rastreador(
            nomes=list(calibracao.nomes),
            nomes_reservados={"Mostarda"},
            assinaturas_configuradas=identidades.configuradas,
        )
        return chave_a, rastreador

    def test_a_lista_viva_troca_NO_LUGAR_e_o_nome_antigo_some(
        self, tmp_path, pixels, calibracao
    ):
        chave_a, rastreador = self._cenario(tmp_path, pixels, calibracao)

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_a)} Titander",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
            rastreador=rastreador,
        )

        com_a_chave = [
            a.nome
            for a in calibracao.assinaturas
            if chave_da_assinatura(a) == chave_a
        ]
        assert com_a_chave == ["Titander"], (
            "a troca tem de ser NO LUGAR: um append deixaria duas assinaturas "
            "quase iguais convivendo, elas se sombreariam pela margem e a "
            f"pessoa pararia de ser reconhecida em silencio. Achado: "
            f"{com_a_chave}"
        )
        assert not [a for a in calibracao.assinaturas if a.nome == "Mostarda"], (
            "o nome ANTIGO continua na lista viva: o proximo extrair ainda "
            "casaria a linha como Mostarda, e D-08 morreria pela metade"
        )

    def test_nomes_reservados_ganha_o_NOVO_e_NAO_perde_o_antigo(
        self, tmp_path, pixels, calibracao
    ):
        """A permanencia do antigo e DELIBERADA, e nao esquecimento.

        `nomes_reservados` e um conservador: ele so diz "este nome nao serve de
        rotulo por POSICAO", e nunca "esta pessoa esta aqui". Tirar `Mostarda`
        de la faria aquele nome voltar a ser emprestado por posicao para
        qualquer linha nao reconhecida — e um nome que ja pertenceu a uma
        assinatura nunca deveria voltar a ser um palpite posicional. Errar para
        o lado do silencio e a regra do projeto.
        """
        chave_a, rastreador = self._cenario(tmp_path, pixels, calibracao)

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_a)} Titander",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
            rastreador=rastreador,
        )

        assert "Titander" in rastreador.nomes_reservados
        assert "Mostarda" in rastreador.nomes_reservados, (
            "o nome antigo foi tirado do conservador e voltou a ser um palpite "
            "posicional: qualquer linha nao reconhecida pode sair como "
            "Mostarda de novo"
        )


class TestAGravacaoQueFalhaNaoMente:
    """`falhou` nao atualiza a tela, e a resposta nao promete nada.

    Um `falhou` que mexesse na lista viva faria a tela mostrar um nome que o
    disco nao tem, e ele sumiria no proximo arranque sem explicacao nenhuma.
    """

    def test_com_falhou_a_resposta_nao_promete_e_os_vivos_ficam_intactos(
        self, tmp_path, pixels, calibracao, monkeypatch
    ):
        chave_a, _ = duas_entradas(
            tmp_path, pixels, calibracao, nome_de_a="Mostarda"
        )
        carregar_na_calibracao(calibracao, tmp_path)
        rastreador = Rastreador(
            nomes=list(calibracao.nomes),
            nomes_reservados={"Mostarda"},
            assinaturas_configuradas=True,
        )
        acervo = AcervoDeIdentidades(tmp_path)
        monkeypatch.setattr(acervo, "nomear", lambda chave, nome: "falhou")

        texto = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_a)} Titander",
            tmp_path,
            acervo=acervo,
            assinaturas_vivas=calibracao.assinaturas,
            rastreador=rastreador,
        ).textos[0]

        assert "Titander" not in texto, (
            f"a resposta prometeu um nome que o disco nao tem: {texto}"
        )
        assert "Nada mudou" in texto
        assert [
            a.nome
            for a in calibracao.assinaturas
            if chave_da_assinatura(a) == chave_a
        ] == ["Mostarda"], "a lista viva foi atualizada num `falhou`"
        assert "Titander" not in rastreador.nomes_reservados


# ---------------------------------------------------------------------------
# CRITERIO 6: QUEM PODE BATIZAR, PELO CAMINHO REAL, NOS DOIS TELEFONES
# ---------------------------------------------------------------------------


class TestQuemPodeBatizar:
    """A trava de autorizacao mora na COSTURA, e e la que ela e provada.

    Os casos rodam por `comandos_novos` com as CINCO travas ligadas (tipo, nota
    privada, id repetido, vocabulario e autorizacao), e nao por
    `autorizado_para` isolado: a funcao sozinha ja tem teste unitario em
    `tests/test_comandos.py`, e o que faltava era a prova de que ela esta
    LIGADA no caminho que o usuario percorre.
    """

    def test_o_DONO_batiza_e_o_nome_e_gravado(self, tmp_path, pixels, calibracao):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )

        despachante = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            telefone=DONO,
        )

        assert (tmp_path / f"{PREFIXO_NOME}{chave}").read_text(
            encoding="utf-8"
        ) == "Mostarda"
        assert despachante.despachos, "o dono nao recebeu confirmacao nenhuma"

    def test_o_MEMBRO_nao_obedece_nao_escreve_e_nao_despacha(
        self, tmp_path, pixels, calibracao
    ):
        """A afirmacao e TRIPLA, e as tres sao necessarias.

        Afirmar so "nada foi obedecido" deixaria passar uma implementacao que
        recusa no lugar errado e escreve antes; afirmar so o disco deixaria
        passar uma que escreve nada e responde alguma coisa ao party-mate.

        E A RECUSA E SILENCIOSA: comando nao autorizado morre no `continue` do
        laco de `comandos_novos`, sem resposta de recusa nenhuma. Do lado de
        quem tentou responder, isso e indistinguivel do bot ter caido — e e
        exatamente por isso que o texto da pergunta (03-01) precisa dizer, em
        uma linha, que so quem calibrou o scanner consegue responder.
        """
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        antes = retrato_da_pasta(tmp_path)

        despachante = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            telefone=TELEFONE_DE_MEMBRO,
        )

        assert not (tmp_path / f"{PREFIXO_NOME}{chave}").exists(), (
            "um party-mate batizou alguem: nome errado e corrupcao duravel "
            "num acervo que nunca e podado e nao tem comando de esquecer"
        )
        assert retrato_da_pasta(tmp_path) == antes
        assert despachante.despachos == [], (
            "a recusa do membro tem de ser SILENCIOSA: ela morre no `continue` "
            f"da autorizacao. Saiu: {despachante.despachos}"
        )

    def test_o_BATIZAR_esta_na_lista_de_recusa_DERIVADA(self):
        """A prova cresceu sozinha, e este caso so a torna legivel.

        `tests/test_comandos.py::TestFronteiraDeAutorizacao` deriva a lista de
        recusa de `set(Comando) - COMANDOS_DE_MEMBRO`, entao o comando novo
        entrou nela sem uma linha de teste nova. Afirmar isso aqui em voz alta
        e o que faz a decisao aparecer para quem le ESTE arquivo.
        """
        assert Comando.BATIZAR in set(Comando) - COMANDOS_DE_MEMBRO

    def test_o_dono_alcanca_SEM_estar_declarado_membro(
        self, tmp_path, pixels, calibracao
    ):
        """O nivel de dono e ADITIVO, no mesmo registro de `autorizado_para`.

        O dono do scanner nao pode deixar de alcancar um comando so porque
        aquele comando ganhou um segundo publico. A premissa e afirmada antes
        do desfecho: se o DONO passasse a estar em `MEMBROS`, este caso viraria
        uma tautologia sem ninguem perceber.
        """
        assert DONO not in [m.telefone for m in MEMBROS], (
            "premissa: o telefone de dono NAO esta declarado em [[membro]]"
        )
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            telefone=DONO,
        )

        assert (tmp_path / f"{PREFIXO_NOME}{chave}").exists()


class TestAAjudaEnsinaUmaSintaxeQueFUNCIONA:
    """A ajuda nao tem como ensinar sintaxe que nao existe.

    O tripwire de `tests/test_comandos.py` roda a tabela `_AJUDA` INTEIRA pelo
    caminho real de leitura, substituindo os marcadores. Aqui a mesma sintaxe
    anunciada e rodada com um APELIDO DE VERDADE, contra um acervo de verdade,
    e a prova termina no disco: nao basta o parser aceitar, o batismo tem de
    acontecer.
    """

    def _sintaxe(self, forma: str, apelido: str) -> str:
        return forma.replace("<apelido>", apelido).replace("<nick>", "Mostarda")

    def test_a_sintaxe_anunciada_batiza_de_verdade(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )

        responder_pelo_whatsapp(
            self._sintaxe(_AJUDA[Comando.BATIZAR].sintaxe, apelido_da_chave(chave)),
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        )

        assert (tmp_path / f"{PREFIXO_NOME}{chave}").read_text(
            encoding="utf-8"
        ) == "Mostarda", (
            "a sintaxe que a ajuda ANUNCIA nao batizou ninguem: a ajuda estaria "
            "ensinando uma forma que nao funciona"
        )

    def test_os_apelidos_anunciados_tambem_batizam(
        self, tmp_path, pixels, calibracao
    ):
        """`/nomear` e SINONIMO exato, e a ajuda o anuncia. Ele tem de valer."""
        for indice, forma in enumerate(_AJUDA[Comando.BATIZAR].apelidos):
            pasta = tmp_path / f"acervo{indice}"
            chave = semear(
                pasta, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
            )

            responder_pelo_whatsapp(
                self._sintaxe(forma, apelido_da_chave(chave)),
                pasta,
                acervo=AcervoDeIdentidades(pasta),
                identificador=8100 + indice,
            )

            assert (pasta / f"{PREFIXO_NOME}{chave}").exists(), (
                f"a ajuda anuncia {forma!r} e ele nao batiza ninguem"
            )


# ---------------------------------------------------------------------------
# AS DUAS DIVIDAS HERDADAS DA FASE 2, AFIRMADAS E NAO ESCONDIDAS
# ---------------------------------------------------------------------------


def recorte_contaminado(px: np.ndarray, cal: Calibracao, indice: int) -> np.ndarray:
    """O MESMO frame com uma chapa CLARA por cima do nome daquela linha.

    E a forma de T-02-07 escrita como pixel: "algo claro por cima do nome".
    A mascara resultante acende a regiao inteira, entao o recorte pontua 0.0
    contra todo mundo — passa no veto de D-02 (que so veta ACIMA do limiar) e
    pode virar entrada.
    """
    regiao = cal.regiao_do_nome(indice)
    copia = px.copy()
    copia[
        regiao.topo : regiao.topo + regiao.altura,
        regiao.esquerda : regiao.esquerda + regiao.largura,
    ] = (240, 240, 240)
    return copia


def virar_celulas_no_frame(
    px: np.ndarray, cal: Calibracao, indice: int, quantas: int, semente: int = 42
) -> np.ndarray:
    """O MESMO frame com N celulas da mascara daquele nome viradas.

    COPIADO de `tests/test_aprendiz.py`, e nao importado, pela razao que o topo
    deste arquivo ja escreve. A virada e por BRILHO porque a mascara e so um
    piso de brilho: branco puro acende a celula, preto puro a apaga. Isso torna
    a perturbacao EXATA — o numero de celulas pedido e o numero de celulas
    viradas —, e deterministica via `RandomState`. Um caso que perturbasse "um
    pouco" provaria outra coisa a cada rodada.
    """
    regiao = cal.regiao_do_nome(indice)
    mascara = mascara_de_texto(_recorte_do_nome(px, cal, indice))
    alvos = np.random.RandomState(semente).choice(
        mascara.size, size=quantas, replace=False
    )
    copia = px.copy()
    for plano in alvos:
        y, x = divmod(int(plano), mascara.shape[1])
        copia[regiao.topo + y, regiao.esquerda + x] = (
            (0, 0, 0) if mascara[y, x] else (255, 255, 255)
        )
    return copia


def correlacao_contra(px, cal, indice, assinaturas) -> float:
    """A melhor pontuacao CRUA daquela linha contra aquelas assinaturas.

    Existe para a premissa ser MEDIDA antes do desfecho: afirmar "nasceu uma
    segunda entrada" sem antes afirmar POR QUE deixaria o caso passar por
    qualquer motivo, inclusive o errado.
    """
    return max(
        _pontuar_mascara(
            mascara_de_texto(_recorte_do_nome(px, cal, indice)), list(assinaturas)
        )
    )


class TestADividaT0207AFirmadaEAceita:
    """T-02-07: um nome dado a uma entrada de LIXO queima o nome.

    A Fase 2 aceitou, com as tres consequencias escritas, que um recorte
    contaminado pontua 0.0 contra tudo, passa no veto de D-02 e pode ser
    aprendido (`02-01-PLAN.md`, a decisao do veto de D-02). A terceira
    consequencia escrita era ESTA fase: a entrada gera uma pergunta pedindo ao
    usuario que batize uma janela de navegador.

    ELA FOI PAGA EM DOIS LUGARES, e nenhum deles finge que a divida sumiu:

    1. o texto da pergunta (03-01) diz que, se aquilo nao for gente, e so nao
       responder — e ignorar so e seguro porque D-04 garante que a pergunta
       nao volta;
    2. a recusa de BATI-04 (Tarefa 1) diz QUAL entrada tem o nome e COMO
       liberar, que e a saida para quem RESPONDEU.

    NAO "CONSERTE" ESTE CASO ACRESCENTANDO UM COMANDO DE ESQUECER. Ele foi
    adiado na Fase 1, com o numero na mao, e esta em Deferred Ideas do
    `03-CONTEXT.md`. A historia abaixo mostra que a saida existe SEM ele, com o
    unico comando que ha.
    """

    def test_a_historia_inteira_em_cinco_passos(
        self, tmp_path, pixels, calibracao
    ):
        contaminado = recorte_contaminado(pixels, calibracao, LINHA_DE_A)
        chave_lixo = semear(
            tmp_path, assinatura_da_linha(contaminado, calibracao, LINHA_DE_A)
        )
        real = assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        assert correlacao_contra(
            contaminado, calibracao, LINHA_DE_A, [real]
        ) == 0.0, (
            "premissa de T-02-07: um recorte contaminado pontua 0.0 contra "
            "tudo, e e por isso que o veto de D-02 nao o alcanca"
        )
        acervo = AcervoDeIdentidades(tmp_path)

        # 1. o usuario responde a pergunta absurda e QUEIMA o nome
        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_lixo)} Mostarda",
            tmp_path,
            acervo=acervo,
            identificador=8201,
        )
        assert acervo.nomeados() == {chave_lixo: "Mostarda"}

        # 2. a pessoa de verdade e aprendida depois
        chave_real = semear(tmp_path, real)
        assert apelido_da_chave(chave_real) != apelido_da_chave(chave_lixo)

        # 3. o batismo dela e RECUSADO, e a recusa cita a entrada de lixo
        texto = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_real)} Mostarda",
            tmp_path,
            acervo=acervo,
            identificador=8202,
        ).textos[0]
        assert apelido_da_chave(chave_lixo) in texto, (
            "sem o apelido da entrada de lixo o usuario nao tem como agir: a "
            "recusa vira um beco sem saida"
        )
        assert acervo.nomeados() == {chave_lixo: "Mostarda"}

        # 4. batizar a entrada de lixo com OUTRO nome libera `Mostarda`
        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_lixo)} Lixo",
            tmp_path,
            acervo=acervo,
            identificador=8203,
        )
        assert acervo.nomeados() == {chave_lixo: "Lixo"}

        # 5. e agora a pessoa de verdade passa
        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_real)} Mostarda",
            tmp_path,
            acervo=acervo,
            identificador=8204,
        )
        assert acervo.nomeados() == {chave_lixo: "Lixo", chave_real: "Mostarda"}, (
            "a saida de T-02-07 deixou de funcionar: sem ela um nome queimado "
            "por engano fica queimado para sempre, porque nao ha comando de "
            "esquecer no v1"
        )

    def test_o_dano_RESIDUAL_e_afirmado_e_declarado_aceito(
        self, tmp_path, pixels, calibracao
    ):
        """A entrada de lixo conta em `Identidades.conhecidas` para SEMPRE.

        Isto e conhecido e aceito, e nao um defeito a consertar aqui: consertar
        exigiria o comando de esquecer, que foi adiado. O preco e uma linha de
        arranque que diz um numero maior do que o de gente de verdade.
        """
        contaminado = recorte_contaminado(pixels, calibracao, LINHA_DE_A)
        semear(tmp_path, assinatura_da_linha(contaminado, calibracao, LINHA_DE_A))
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))

        identidades = carregar_identidades([], AcervoDeIdentidades(tmp_path))

        assert identidades.conhecidas == 2, (
            "uma das duas e lixo, e mesmo assim ela conta: o acervo nao tem "
            "poda nem comando de esquecer, e a contagem do arranque nao "
            "distingue gente de janela de navegador"
        )


class TestADividaT0218AFirmadaEAceita:
    """T-02-18: a mesma pessoa pode ter DUAS entradas, e ser perguntada duas vezes.

    MEDIDO NA FASE 2, mascara de 2000 celulas com 60 pixels de texto, nick
    `TioMad`: 42 celulas de drift dao correlacao 0.7531 (acima de 0.75, nada
    nasce) e 43 dao 0.7492 (abaixo, uma SEGUNDA entrada da mesma pessoa nasce).
    Uma unica celula separa as duas metades, e 43 celulas sao 2,15% da mascara
    mas 71,7% do SINAL DE TEXTO daquele nick. Num nick curto a fronteira chega
    muito antes, e o modelo de drift usado ACENDE celulas, entao a tabela e um
    limite OTIMISTA.

    NESTA FIXTURE, MEDIDO AQUI: a mascara tem 2000 celulas e 48 pixels de
    texto, e a fronteira fica em 34 celulas (0.7515, acima) contra 35 (0.7467,
    abaixo). Sao 1,75% da mascara e 72,9% do sinal de texto — a mesma leitura,
    com o numero desta maquina e nao com o da Fase 2 repetido.

    NAO HA CONSERTO HONESTO SEM MEDIDA DE CAMPO DO DRIFT ENTRE SESSOES, e ela
    nao existe: as duas capturas de party window versionadas sao BYTE A BYTE
    identicas, entao compara-las mede uma imagem consigo mesma. Esta fase nao
    fecha essa porta e nao finge que fecha; ela troca o silencio por
    LEGIBILIDADE em dois pontos, que sao os dois casos abaixo.

    NAO "CONSERTE" ESTE CASO. O comportamento e conhecido e aceito; se ele
    comecou a falhar, alguem MUDOU o codigo.
    """

    # As duas margens, MEDIDAS nesta fixture. Ver a docstring acima.
    CELULAS_ACIMA = 34
    CELULAS_ABAIXO = 35

    def _duas_da_mesma_pessoa(self, tmp_path, pixels, calibracao):
        primeira = assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        volta = virar_celulas_no_frame(
            pixels, calibracao, LINHA_DA_FATIA, self.CELULAS_ABAIXO
        )
        segunda = assinatura_da_linha(volta, calibracao, LINHA_DA_FATIA)
        chave_um = semear(tmp_path, primeira)
        chave_dois = semear(tmp_path, segunda)
        assert chave_um != chave_dois, (
            "premissa: sao DUAS entradas. Uma celula ja bastaria para a chave "
            "mudar, e e por isso que a dedupe da Fase 2 nao e por chave"
        )
        assert apelido_da_chave(chave_um) != apelido_da_chave(chave_dois)
        return chave_um, chave_dois, primeira, volta

    def test_a_fronteira_MEDIDA_e_a_razao_de_a_segunda_entrada_nascer(
        self, tmp_path, pixels, calibracao
    ):
        """A correlacao e afirmada ANTES do desfecho, nas DUAS margens."""
        primeira = assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)

        acima = correlacao_contra(
            virar_celulas_no_frame(
                pixels, calibracao, LINHA_DA_FATIA, self.CELULAS_ACIMA
            ),
            calibracao,
            LINHA_DA_FATIA,
            [primeira],
        )
        abaixo = correlacao_contra(
            virar_celulas_no_frame(
                pixels, calibracao, LINHA_DA_FATIA, self.CELULAS_ABAIXO
            ),
            calibracao,
            LINHA_DA_FATIA,
            [primeira],
        )

        assert acima >= LIMIAR_DE_CASAMENTO > abaixo, (
            f"a fronteira MEDIDA mudou: {self.CELULAS_ACIMA} celulas deram "
            f"{acima:.4f} e {self.CELULAS_ABAIXO} deram {abaixo:.4f}. Isto nao "
            "e um teste a afrouxar; e o numero que o SUMMARY registra"
        )
        assert acima == pytest.approx(0.7515, abs=1e-3), acima
        assert abaixo == pytest.approx(0.7467, abs=1e-3), abaixo
        # 35 celulas sao 1,75% da mascara e 72,9% do sinal de texto: a fracao
        # que importa e a do SINAL, e nao a da mascara.
        assert self.CELULAS_ABAIXO / primeira.mascara.size < 0.03
        assert self.CELULAS_ABAIXO / int(primeira.mascara.sum()) > 0.7

    def test_as_duas_entradas_saem_como_DUAS_LINHAS_da_MESMA_pergunta(
        self, tmp_path, pixels, calibracao
    ):
        """A primeira metade da legibilidade.

        Duas perguntas soltas seriam lidas como dois desconhecidos diferentes.
        Uma mensagem com as duas linhas, uma embaixo da outra, e o que da ao
        usuario a chance de perceber que pode ser a mesma pessoa.
        """
        chave_um, chave_dois, _, _ = self._duas_da_mesma_pessoa(
            tmp_path, pixels, calibracao
        )
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta(acervo, pendentes_do_acervo(acervo))

        assert pergunta is not None
        assert "Aprendi 2 pessoas" in pergunta, pergunta
        assert apelido_da_chave(chave_um) in pergunta
        assert apelido_da_chave(chave_dois) in pergunta
        assert montar_pergunta(acervo, pendentes_do_acervo(acervo)) is None, (
            "a segunda varredura nao pode perguntar de novo (D-04)"
        )

    def test_a_segunda_e_recusada_e_a_recusa_diz_que_isso_nao_faz_mal(
        self, tmp_path, pixels, calibracao
    ):
        """A segunda metade da legibilidade, e ela e o produto desta fase.

        Sem a frase, o usuario que tenta dar o mesmo nome as duas conclui que o
        scanner esta quebrado e fica tentando. Com ela, ele sabe que deixar a
        segunda sem nome nao custa nada: assinatura sem nome e reconhecida do
        mesmo jeito e nunca vira sujeito de alerta (APRE-03).
        """
        chave_um, chave_dois, _, _ = self._duas_da_mesma_pessoa(
            tmp_path, pixels, calibracao
        )
        acervo = AcervoDeIdentidades(tmp_path)

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_um)} Mostarda",
            tmp_path,
            acervo=acervo,
            identificador=8301,
        )
        texto = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_dois)} Mostarda",
            tmp_path,
            acervo=acervo,
            identificador=8302,
        ).textos[0]

        assert acervo.nomeados() == {chave_um: "Mostarda"}
        assert "aprendi o rosto dela duas vezes" in texto
        assert "nunca vira sujeito de alerta" in texto, (
            "a recusa nao diz que a segunda ficar sem nome nao faz mal, e essa "
            "frase e a unica mitigacao que T-02-18 tem nesta fase"
        )


# ---------------------------------------------------------------------------
# T-03-07: A INSTANCIA QUE NAO OBEDECEU O COMANDO CALA
# ---------------------------------------------------------------------------


def com_hp(obs, indice: int, hp: float):
    linhas = list(obs.linhas)
    linhas[indice] = replace(linhas[indice], hp=hp)
    return replace(obs, linhas=tuple(linhas))


def mortes_apos_zerar(obs, indice: int, configuradas: bool, nomes: list[str]):
    """Roda o rastreador de verdade sobre uma sequencia que confirma morte.

    COPIADO de `tests/test_acervo.py`, e nao importado, pela razao que o topo
    deste arquivo escreve. Ele existe aqui para a metade COMPORTAMENTAL de
    T-03-07: "continua anonima" sozinho seria uma afirmacao sobre um campo, e
    nao sobre o que o usuario ve.
    """
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


class TestAInstanciaQueNaoObedeceuContinuaAnonimaECALA:
    """T-03-07, aceito, e afirmado por COMPORTAMENTO e nao por leitura de campo.

    O usuario roda DUAS instancias sobre a MESMA pasta. O marcador
    `comando_<id>` da `.agenda/` e compartilhado, entao exatamente UMA delas
    obedece cada comando — e a outra fica com a assinatura ANONIMA na lista
    viva ate o proximo arranque.

    A DEGRADACAO E SEGURA, e e por isso que o preco e aceito: anonima CALA. A
    linha continua sendo reconhecida, o rotulo continua `Membro N`, e ela nunca
    vira sujeito de alerta nenhum (APRE-03). O disco JA tem o nome; o que falta
    e so a instancia que nao obedeceu reler a pasta, e ela le de novo no
    proximo arranque.
    """

    def test_a_segunda_lista_viva_continua_anonima_e_produz_ZERO_eventos(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        # As DUAS instancias: duas cargas independentes sobre a MESMA pasta.
        primeira = carregar_identidades([], AcervoDeIdentidades(tmp_path))
        segunda = carregar_identidades([], AcervoDeIdentidades(tmp_path))
        calibracao.assinaturas = segunda.assinaturas
        assert [a.nome for a in primeira.assinaturas] == [""], "premissa"

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=primeira.assinaturas,
            rastreador=Rastreador(
                nomes=list(calibracao.nomes),
                assinaturas_configuradas=primeira.configuradas,
            ),
        )

        assert [a.nome for a in primeira.assinaturas] == ["Mostarda"], (
            "premissa: a instancia que OBEDECEU ficou com o nome no mesmo tick"
        )
        assert [a.nome for a in segunda.assinaturas] == [""], (
            "a segunda instancia nao pode ter recebido o nome: elas nao "
            "compartilham lista viva, e o marcador comando_<id> garante que "
            "so uma obedeceu"
        )

        obs = observar_frame(pixels, calibracao)
        linha = obs.linhas[LINHA_DA_FATIA]
        assert linha.confianca_do_nome > 0.9, (
            "ela continua RECONHECIDA na segunda instancia: o que falta e o "
            "nome, e nao o reconhecimento"
        )
        assert linha.nome == ""

        rastreador, mortes = mortes_apos_zerar(
            obs, LINHA_DA_FATIA, segunda.configuradas, list(calibracao.nomes)
        )
        assert mortes == [], (
            "a instancia que nao obedeceu ANUNCIOU alguem: anonima tem de "
            "CALAR, nunca mentir. Este e o preco aceito do marcador "
            "compartilhado, e o nome chega no proximo arranque"
        )
        identidade = rastreador._identidade_por_linha[LINHA_DA_FATIA]
        assert (
            rastreador._nome_exibido(identidade)
            == f"Membro {LINHA_DA_FATIA + 1}"
        )

    def test_e_o_DISCO_ja_tem_o_nome_para_o_proximo_arranque(
        self, tmp_path, pixels, calibracao
    ):
        """A outra metade: o nome nao se perdeu, so ainda nao foi lido."""
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        primeira = carregar_identidades([], AcervoDeIdentidades(tmp_path))

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=primeira.assinaturas,
        )

        arranque_seguinte = carregar_identidades([], AcervoDeIdentidades(tmp_path))
        assert [a.nome for a in arranque_seguinte.assinaturas] == ["Mostarda"], (
            "no proximo arranque a segunda instancia le a MESMA pasta e "
            "encontra o nome: e por isso que a degradacao e temporaria"
        )


# ---------------------------------------------------------------------------
# AS CINCO LIGACOES NOVAS QUE PODERIAM SUMIR EM SILENCIO
# ---------------------------------------------------------------------------

ELO_SESSAO_ACERVO = "a Sessao de producao recebe o acervo"
ELO_COMANDOS_ACERVO = "atender_comandos recebe o acervo"
ELO_COMANDOS_LISTA_VIVA = "atender_comandos recebe a lista viva"
ELO_VARREDURA = "o arranque varre o acervo e pergunta"
ELO_SIMULANDO = "toda construcao do acervo decide sobre simulando"

ELOS_DO_BATISMO = (
    ELO_SESSAO_ACERVO,
    ELO_COMANDOS_ACERVO,
    ELO_COMANDOS_LISTA_VIVA,
    ELO_VARREDURA,
    ELO_SIMULANDO,
)


def _alvo_da_chamada(no: ast.Call) -> str | None:
    return getattr(no.func, "id", None) or getattr(no.func, "attr", None)


def _acervos_ligados(arvore: ast.Module) -> set[str]:
    """Os nomes locais que recebem o resultado de `AcervoDeIdentidades(...)`.

    Sem isso, `acervo=None` satisfaria "passou o argumento" e deixaria o
    defeito inteiro de pe: a chamada existe, o comando responde, e a resposta
    e sempre "nao consigo mexer nas identidades agora".
    """
    ligados: set[str] = set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Assign) or not isinstance(no.value, ast.Call):
            continue
        if _alvo_da_chamada(no.value) != "AcervoDeIdentidades":
            continue
        ligados |= {t.id for t in no.targets if isinstance(t, ast.Name)}
    return ligados


def _passado(no: ast.Call, nome: str) -> ast.expr | None:
    return next((k.value for k in no.keywords if k.arg == nome), None)


def _elos_do_batismo(
    fonte: str, arquivo: str
) -> tuple[dict[str, list[str]], list[str]]:
    """Devolve (o que foi ACHADO por elo, as QUEIXAS) lendo a arvore sintatica.

    AST E NUNCA `grep`, pela mesma razao dos dois portoes irmaos: as docstrings
    deste projeto citam `acervo=`, `assinaturas_vivas=` e `simulando=` EM PROSA
    ao explicar por que os elos existem, e uma busca textual acusaria justamente
    a explicacao que sobrou depois de a linha sumir.

    O IRMAO DE `tests/test_aprendiz.py` NAO FOI FUNDIDO COM ESTE de proposito:
    os dois portoes guardam fases diferentes, e uma queixa de uma apareceria no
    relatorio da outra.
    """
    arvore = ast.parse(fonte)
    achados: dict[str, list[str]] = {elo: [] for elo in ELOS_DO_BATISMO}
    queixas: list[str] = []
    acervos = _acervos_ligados(arvore)
    chamadas_de_comando: list[str] = []

    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        local = f"{arquivo}:{no.lineno}"
        alvo = _alvo_da_chamada(no)

        if alvo == "AcervoDeIdentidades":
            # O MOLDE AQUI E O DO `Rastreador`, E NAO O DOS ELOS, e a forma e
            # outra de proposito: a pergunta nao e "esta ligacao existe", e sim
            # "toda chamada DECIDE sobre um argumento cujo default e
            # silencioso". A resposta certa pode ser `False`, entao o portao
            # exige a DECISAO e nunca um valor.
            if not any(k.arg == "simulando" for k in no.keywords):
                queixas.append(
                    f"{local}: este `AcervoDeIdentidades(...)` nao decide sobre "
                    "`simulando`. O default e False, que e o valor "
                    "silenciosamente perigoso: um --dry-run que esqueca de "
                    "passar queima o marcador de pergunta da instancia REAL, e "
                    "o marcador nao tem desfazer"
                )
            else:
                achados[ELO_SIMULANDO].append(local)

        elif alvo == "Sessao":
            passado = _passado(no, "acervo")
            if passado is None:
                queixas.append(
                    f"{local}: esta `Sessao(...)` nao passa `acervo=`, entao o "
                    "aprendizado nunca pergunta quem e a pessoa nova e a fase "
                    "nasce muda em campo com a suite inteira verde"
                )
            elif not (isinstance(passado, ast.Name) and passado.id in acervos):
                queixas.append(
                    f"{local}: o `acervo=` desta `Sessao(...)` nao e um nome "
                    "vindo de um `AcervoDeIdentidades(...)` deste modulo. "
                    "`None` aqui desliga a pergunta inteira sem quebrar teste "
                    "nenhum"
                )
            else:
                achados[ELO_SESSAO_ACERVO].append(local)

        elif alvo == "atender_comandos":
            chamadas_de_comando.append(local)
            passado = _passado(no, "acervo")
            if passado is None:
                queixas.append(
                    f"{local}: este `atender_comandos(...)` nao passa "
                    "`acervo=`. O marcador `comando_<id>` e COMPARTILHADO: se "
                    "este laco receber a mensagem primeiro, ele consome o "
                    "marcador, responde 'nao consigo mexer nas identidades "
                    "agora' e o batismo do usuario e PERDIDO"
                )
            elif not (isinstance(passado, ast.Name) and passado.id in acervos):
                queixas.append(
                    f"{local}: o `acervo=` deste `atender_comandos(...)` nao e "
                    "um nome vindo de um `AcervoDeIdentidades(...)`: a chamada "
                    "existe e a resposta e sempre a recusa"
                )
            else:
                achados[ELO_COMANDOS_ACERVO].append(local)

            viva = _passado(no, "assinaturas_vivas")
            if viva is not None and not isinstance(viva, ast.Constant):
                achados[ELO_COMANDOS_LISTA_VIVA].append(local)

    # A LISTA VIVA E UM ELO DE PRESENCA, e nao uma exigencia por chamada: o
    # laco da agenda passa `None` com razao, porque la nao existe tela. O que
    # nao pode e NENHUM dos lacos passar — ai D-08 morre em silencio e o nome
    # so vale depois de reiniciar.
    if chamadas_de_comando and not achados[ELO_COMANDOS_LISTA_VIVA]:
        queixas.append(
            f"{arquivo}: nenhuma das {len(chamadas_de_comando)} chamadas de "
            "`atender_comandos(...)` passa `assinaturas_vivas=`. Sem ela o "
            "nome so vale depois de reiniciar, e o usuario batiza de novo "
            "achando que falhou (D-08)"
        )

    for no in ast.walk(arvore):
        if not isinstance(no, ast.FunctionDef) or no.name != "laco_principal":
            continue
        varreduras = [
            f"{arquivo}:{filho.lineno}"
            for filho in ast.walk(no)
            if isinstance(filho, ast.Call)
            and _alvo_da_chamada(filho) == "montar_pergunta"
        ]
        if varreduras:
            achados[ELO_VARREDURA].extend(varreduras)
        else:
            queixas.append(
                f"{arquivo}:{no.lineno}: `laco_principal` nao chama "
                "`montar_pergunta(...)`. Sem a varredura de arranque, as "
                "entradas que JA estao no disco nunca sao perguntadas — e elas "
                "sao as unicas que existem no acervo real do usuario"
            )

    return achados, queixas


def _elos_do_batismo_em_producao() -> tuple[dict[str, list[str]], list[str]]:
    achados: dict[str, list[str]] = {elo: [] for elo in ELOS_DO_BATISMO}
    queixas: list[str] = []
    for caminho in sorted((RAIZ / "l2scanner").glob("*.py")):
        parcial, reclamou = _elos_do_batismo(
            caminho.read_text(encoding="utf-8"), caminho.name
        )
        for elo, locais in parcial.items():
            achados[elo].extend(locais)
        queixas.extend(reclamou)
    return achados, queixas


# O fonte fabricado que CUMPRE as cinco regras, no formato dos lacos REAIS.
#
# Ele precisa ter os DOIS lacos, com as DUAS chamadas de `atender_comandos`,
# para que a mutacao "so um dos lacos passa o acervo" seja plantavel. O
# precedente e `TestFuncionaNosDoisLacos` de
# `tests/test_janela_sob_demanda.py`: logica certa ligada num caminho so e a
# familia de defeito que este projeto pagou duas vezes, e o usuario roda os
# dois lacos.
FONTE_QUE_CUMPRE = '''
def laco_principal(args, cal):
    acervo = AcervoDeIdentidades(PASTA_IDENTIDADES, simulando=args.dry_run)
    identidades = carregar_identidades(list(cal.assinaturas), acervo)
    cal.assinaturas = identidades.assinaturas
    if despachante is not None:
        pergunta = montar_pergunta(acervo, pendentes_do_acervo(acervo))
    sessao = Sessao(cal=cal, rastreador=rastreador, aprendiz=aprendiz, acervo=acervo)
    while True:
        atender_comandos(leitor, registro, eventos, despachante, agora, mono, rastreador, acervo=acervo, assinaturas_vivas=cal.assinaturas)


def laco_da_agenda(args):
    acervo = AcervoDeIdentidades(PASTA_IDENTIDADES, simulando=args.dry_run)
    while True:
        atender_comandos(leitor, registro, eventos, despachante, agora, mono, None, acervo=acervo)
'''


class TestNenhumaLigacaoDoBatismoSomeEmSilencio:
    """Cinco linhas de `__main__.py` que a suite inteira nao defenderia.

    ESTA E A TERCEIRA APLICACAO DO MESMO MOLDE NESTE PROJETO, e as duas
    anteriores nasceram de defeitos de campo, e nao de teoria:

    - **Fase 1**: `Rastreador.assinaturas_configuradas` tinha default `False` e
      era atribuido em OITO lugares, todos em teste. O unico construtor de
      producao nao passava o argumento. O silencio do `#linhaN` estava provado
      na suite e DESLIGADO no jogo, desde que a identidade por imagem foi
      escrita. Dai nasceu `tests/test_acervo.py::TestNenhumRastreadorNasceMudo`.
    - **Fase 2**: tres linhas de `__main__.py` sem guarda nenhuma. A
      verificacao arrancou `aprendiz=aprendiz` e os 3514 testes ficaram VERDES
      — a feature inteira desligada em campo, e nada acusando. Dai nasceu
      `tests/test_aprendiz.py::TestNenhumaLigacaoDoAprendizSomeEmSilencio`.

    A Fase 3 acabou de criar CINCO lugares novos com exatamente essa forma, e
    esta classe e o molde aplicado a eles. Cada elo tem uma mutacao plantada, e
    cada caso afirma que a mutacao PEGOU antes de afirmar que o detector
    reclamou: sem essa linha, um `replace` que nao casasse deixaria o caso
    verde provando nada.

    O QUE O PORTAO **NAO** CONSERTA, dito para ninguem esperar dele o que ele
    nao da: ele nao muda default nenhum e nao impede que um TESTE construa sem
    os argumentos. Tornar `simulando` obrigatorio quebraria os casos de
    `tests/test_acervo.py` e `tests/test_aprendiz.py` que constroem
    `AcervoDeIdentidades(tmp_path)`, e esta fase nao reescreve teste que passa.
    Quem quiser o default continua podendo — mas em PRODUCAO tem de escrever a
    escolha, e ai ela aparece no diff de alguem.
    """

    def test_as_cinco_ligacoes_estao_no_fonte_de_producao(self):
        _, queixas = _elos_do_batismo_em_producao()
        assert not queixas, "\n".join(queixas)

    def test_o_portao_nao_passa_por_vacuidade(self):
        """Um portao que nao acha nada passa sem provar nada.

        Mesma assercao, pela mesma razao, das duas guardas anteriores. Se
        `laco_principal` for renomeado, movido, ou o detector olhar para a
        pasta errada, e AQUI que aparece — em vez de os cinco elos ficarem
        verdes por ausencia. O preco desta licao ja foi pago pelo comando de
        verificacao que "passava sem rodar nada" do plano 10-02.
        """
        achados, _ = _elos_do_batismo_em_producao()
        vazios = [elo for elo, locais in achados.items() if not locais]
        assert not vazios, (
            "o detector nao encontrou NENHUMA ocorrencia destes elos em "
            f"l2scanner/: {vazios}. O portao esta olhando para o lugar errado"
        )

    def test_o_detector_nao_acusa_o_fonte_que_cumpre(self):
        """A outra metade: quem cumpriu a regra nao pode ser acusado."""
        achados, queixas = _elos_do_batismo(FONTE_QUE_CUMPRE, "<fabricado>")
        assert queixas == [], "\n".join(queixas)
        assert all(achados.values()), achados

    def test_o_detector_acusa_a_Sessao_sem_o_acervo(self):
        """Sem ele o aprendizado nunca pergunta: a fase nasce muda em campo."""
        envenenado = FONTE_QUE_CUMPRE.replace(
            "aprendiz=aprendiz, acervo=acervo)", "aprendiz=aprendiz)"
        )
        assert envenenado != FONTE_QUE_CUMPRE, "a mutacao plantada nao pegou"
        achados, queixas = _elos_do_batismo(envenenado, "<fabricado>")
        assert queixas, "o detector nao acusaria uma `Sessao(...)` sem `acervo=`"
        assert achados[ELO_SESSAO_ACERVO] == []

    def test_o_detector_acusa_SO_UM_dos_lacos_passando_o_acervo(self):
        """A mutacao mais provavel num diff de verdade, e a mais cara.

        O marcador `comando_<id>` e compartilhado: se o laco da agenda receber
        a mensagem primeiro e nao tiver acervo, ele CONSOME o marcador,
        responde a recusa e o batismo do usuario e perdido. O laco principal
        continua verde em qualquer teste que so olhe para ele.
        """
        envenenado = FONTE_QUE_CUMPRE.replace(
            "mono, None, acervo=acervo)", "mono, None)"
        )
        assert envenenado != FONTE_QUE_CUMPRE, "a mutacao plantada nao pegou"
        achados, queixas = _elos_do_batismo(envenenado, "<fabricado>")
        assert queixas, (
            "o detector nao acusaria um `atender_comandos(...)` sem `acervo=`"
        )
        assert len(achados[ELO_COMANDOS_ACERVO]) == 1, (
            "o laco que ainda cumpre continua sendo achado; o portao acusa o "
            "OUTRO"
        )

    def test_o_detector_acusa_o_acervo_trocado_por_None(self):
        """Guarda contra o conserto preguicoso.

        `acervo=None` satisfaria "passou o argumento" e deixaria o defeito
        inteiro de pe: a chamada existe, o comando responde, e a resposta e
        sempre "nao consigo mexer nas identidades agora".
        """
        envenenado = FONTE_QUE_CUMPRE.replace(
            "mono, None, acervo=acervo)", "mono, None, acervo=None)"
        )
        assert envenenado != FONTE_QUE_CUMPRE, "a mutacao plantada nao pegou"
        _, queixas = _elos_do_batismo(envenenado, "<fabricado>")
        assert queixas, "o detector nao acusaria um `acervo=None` literal"

    def test_o_detector_acusa_a_lista_viva_arrancada(self):
        """Sem ela o nome so vale depois de reiniciar, e D-08 morre calado."""
        envenenado = FONTE_QUE_CUMPRE.replace(
            ", assinaturas_vivas=cal.assinaturas", ""
        )
        assert envenenado != FONTE_QUE_CUMPRE, "a mutacao plantada nao pegou"
        achados, queixas = _elos_do_batismo(envenenado, "<fabricado>")
        assert queixas, (
            "o detector nao acusaria os dois lacos sem `assinaturas_vivas=`"
        )
        assert achados[ELO_COMANDOS_LISTA_VIVA] == []

    def test_o_detector_acusa_a_varredura_de_arranque_arrancada(self):
        """Sem ela a fase nao funciona no unico acervo real que existe.

        As tres entradas anonimas do disco do usuario nunca produzem
        `Aprendizado` nenhum: elas entram na lista viva, casam ~1.000 contra
        elas mesmas, e `Casamento.nome` de uma anonima e a string VAZIA. So a
        varredura as alcanca.
        """
        # O BLOCO INTEIRO, e nao so a linha de dentro: arrancar so a linha
        # deixaria um `if` sem corpo, que nem compila. A mutacao realista num
        # diff de verdade e a remocao do bloco.
        envenenado = FONTE_QUE_CUMPRE.replace(
            "    if despachante is not None:\n"
            "        pergunta = montar_pergunta(acervo, pendentes_do_acervo(acervo))\n",
            "",
        )
        assert envenenado != FONTE_QUE_CUMPRE, "a mutacao plantada nao pegou"
        achados, queixas = _elos_do_batismo(envenenado, "<fabricado>")
        assert queixas, (
            "o detector nao acusaria um `laco_principal` que nao varre o acervo"
        )
        assert achados[ELO_VARREDURA] == []

    def test_o_detector_acusa_o_acervo_construido_sem_simulando(self):
        """O default e `False`, que e o valor silenciosamente perigoso.

        Um `--dry-run` rodando ao lado do scanner de verdade gravaria
        `perguntado_<chave>` na pasta COMPARTILHADA e apagaria para sempre a
        pergunta da instancia real. O marcador nao tem desfazer, e nao ha
        comando de esquecer no v1.
        """
        envenenado = FONTE_QUE_CUMPRE.replace(
            "AcervoDeIdentidades(PASTA_IDENTIDADES, simulando=args.dry_run)",
            "AcervoDeIdentidades(PASTA_IDENTIDADES)",
            1,
        )
        assert envenenado != FONTE_QUE_CUMPRE, "a mutacao plantada nao pegou"
        _, queixas = _elos_do_batismo(envenenado, "<fabricado>")
        assert queixas, (
            "o detector nao acusaria um `AcervoDeIdentidades(...)` que nao "
            "decide sobre `simulando`"
        )


def _ramo_atribui_avisar_o_grupo(fonte: str, membro: str) -> bool:
    """O ramo daquele comando ATRIBUI `avisar_o_grupo` no proprio corpo?

    Le a estrutura, e nao o comportamento. O caso de comportamento passaria por
    acidente se o comando ANTERIOR da mesma volta do laco tivesse deixado o
    valor certo na variavel; so a atribuicao dentro do ramo impede a heranca
    silenciosa de voltar num refactor.
    """
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.If):
            continue
        if membro not in ast.dump(no.test):
            continue
        atribuicoes = [
            alvo.id
            for filho in no.body
            if isinstance(filho, ast.Assign)
            for alvo in filho.targets
            if isinstance(alvo, ast.Name)
        ]
        return "avisar_o_grupo" in atribuicoes
    raise AssertionError(f"nao ha ramo para Comando.{membro} no fonte lido")


RAMO_FABRICADO_SEM_A_FLAG = """
def atender_comandos():
    if pedido.comando is Comando.BATIZAR:
        resposta = responder_batismo(acervo, pedido.argumento)
"""


class TestORamoDoBatismoAtribuiAvisarOGrupo:
    """Copia direta do portao do `/tiat`, com `BATIZAR` no lugar de `JANELA`.

    `avisar_o_grupo` e uma variavel de escopo de FUNCAO, atribuida dentro dos
    ramos e lida no bloco de despacho. Um ramo que nao a atribua herda EM
    SILENCIO o valor do comando ANTERIOR da mesma volta do laco, e o efeito e
    resposta privada vazando para o grupo.

    No caminho feliz do batismo a leitura nem acontece — o ramo devolve
    `RespostaDePresenca` e o `isinstance` curto-circuita antes —, mas isso e
    uma coincidencia que nada no codigo preserva, e o ramo SEM acervo devolve
    `str`, onde a flag e lida de verdade.
    """

    def test_o_ramo_de_producao_atribui_a_flag(self):
        import inspect

        from l2scanner import __main__ as principal

        assert _ramo_atribui_avisar_o_grupo(
            inspect.getsource(principal.atender_comandos), "BATIZAR"
        ), (
            "o ramo do BATIZAR nao seta `avisar_o_grupo`: ele herdaria em "
            "silencio o valor do comando anterior da mesma volta do laco, e "
            "uma recusa privada vazaria para o grupo"
        )

    def test_o_detector_acusaria_um_ramo_fabricado_SEM_a_atribuicao(self):
        """Senao o portao passaria por acidente. A outra metade obrigatoria."""
        assert not _ramo_atribui_avisar_o_grupo(
            RAMO_FABRICADO_SEM_A_FLAG, "BATIZAR"
        )

    def test_o_detector_falha_alto_quando_o_ramo_nao_existe(self):
        """Um portao que nao acha o ramo passa sem provar nada."""
        with pytest.raises(AssertionError):
            _ramo_atribui_avisar_o_grupo(
                RAMO_FABRICADO_SEM_A_FLAG, "COMANDO_QUE_NAO_EXISTE"
            )
