"""A pergunta do batismo passa a levar a IMAGEM do nome (OCRN-03, metade 1).

A DOR, NAS PALAVRAS DO DONO

A pergunta que chega no celular hoje e esta:

    Aprendi 3 pessoas que ainda estao sem nome:
      0dcf6f
      15caec
      f19e3c

E a pergunta dele foi "como vou saber qual hash representa qual nome?". Nao ha
resposta boa: ele teria que adivinhar por eliminacao. E a resposta natural nao
e OCR — e MOSTRAR o recorte, porque o olho dele le o nick que o OCR erra.

ISSO FOI MEDIDO A MAO ANTES DE VIRAR CODIGO, contra o acervo real de
01/09/2026: as 15 mascaras gravadas em `.identidades/` foram reconstruidas para
PNG e lidas sem esforco — `Welazkez`, `PIRULITO`, e tambem os lixos
(`Show Options`, um recorte com `Kills: 4 Deaths` por cima). A mascara e
binaria e pequena (20x110 nas 15 entradas do acervo real) e fica legivel
ampliada, invertida (texto preto no branco). Nao precisa de captura nova: a
mascara ja esta em disco para TODA entrada, inclusive as aprendidas em sessoes
passadas.

O QUE ESTES CASOS PROVAM, E POR QUE NENHUM DELES TOCA A REDE

1. o desenho (`retrato.py`) e deterministico e nao suaviza pixel nenhum;
2. o corpo `multipart/form-data` e montado a mao com a stdlib, e o corpo e
   comparavel byte a byte SEM socket nenhum — e por isso que a peca mais chata
   do encargo e tambem a mais testavel;
3. o caminho de TEXTO PURO continua saindo como JSON, byte a byte;
4. uma falha de anexo NAO engole a pergunta.

Nenhum caso aqui abre socket. `urllib.request.urlopen` e substituido por um
falso que GRAVA a requisicao, e e a requisicao gravada que e afirmada.
"""

from __future__ import annotations

import ast
import json
import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.acervo import (
    PREFIXO_ASSINATURA,
    PREFIXO_NOME,
    AcervoDeIdentidades,
    chave_da_assinatura,
)
from l2scanner.batismo import (
    TETO_DE_IMAGENS,
    montar_pergunta,
    montar_pergunta_com_imagens,
    pendentes_do_acervo,
)
from l2scanner.identidade import Assinatura
from l2scanner.notificador import (
    Categoria,
    ConfigChatwoot,
    Despachante,
    ErroDeEntrega,
    NotificadorChatwoot,
    NotificadorEmMemoria,
    escolher_fronteira,
    montar_multipart,
)
from l2scanner.retrato import (
    AMPLIACAO,
    MARGEM,
    MOLDURA,
    Anexo,
    anexo_do_nome,
    png_do_nome,
)

RAIZ = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Idiomas copiados, e nao importados, pela razao que `test_janela_sob_demanda`
# ja escreve: importar entre arquivos de teste cria dependencia entre eles.
# ---------------------------------------------------------------------------


def mascara_com_texto(semente: int, altura: int = 20, largura: int = 110):
    """Uma mascara 0/1 com a forma de um nome: um bloco de colunas acesas.

    NAO E RUIDO ALEATORIO. Um `rand > 0.5` daria uma mascara sem estrutura, e
    os casos que afirmam "o texto ficou preto e o fundo branco" estariam
    afirmando contra uma nuvem — passariam por sorte. Aqui as colunas acesas
    sao conhecidas, entao a afirmacao e sobre pixels nomeados.
    """
    mascara = np.zeros((altura, largura), dtype=np.uint8)
    # Miolo vertical, como um glifo: nunca a primeira nem a ultima linha.
    mascara[4 : altura - 4, semente % 5 + 2 :: 5] = 1
    # Um pixel unico por semente. O acervo indexa pelo HASH da mascara, entao
    # duas fabricadas iguais virariam UMA entrada so — e um caso que pedisse
    # dez pendentes receberia sete, medindo o gerador em vez do teto.
    mascara[2, 4 + semente] = 1
    return mascara


def assinatura_fabricada(semente: int) -> Assinatura:
    return Assinatura(nome="", mascara=mascara_com_texto(semente))


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


class RequisicaoGravada:
    """O que `urlopen` recebeu, sem nenhum socket por perto."""

    def __init__(self, req) -> None:
        self.url = req.full_url
        self.corpo = req.data
        self.cabecalhos = {k.lower(): v for k, v in req.header_items()}


class UrlopenFalso:
    """Grava cada requisicao. Falha nas que o teste mandar falhar."""

    def __init__(self, falhar_se=None, erro=None) -> None:
        self.requisicoes: list[RequisicaoGravada] = []
        self._falhar_se = falhar_se or (lambda req: False)
        self._erro = erro or OSError("multipart recusado")

    def __call__(self, req, timeout=None):
        gravada = RequisicaoGravada(req)
        self.requisicoes.append(gravada)
        if self._falhar_se(gravada):
            raise self._erro
        return self

    # contexto: `with urlopen(...) as resposta: resposta.read()`
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return b"{}"


def chatwoot(monkeypatch, falso: UrlopenFalso) -> NotificadorChatwoot:
    monkeypatch.setattr("urllib.request.urlopen", falso)
    return NotificadorChatwoot(
        ConfigChatwoot(
            url="https://chat.exemplo",
            conta="1",
            token="segredo",
            conversas=["13"],
        )
    )


# ---------------------------------------------------------------------------
# TAREFA 1: o desenho. O olho le o que o OCR erra.
# ---------------------------------------------------------------------------


class TestOPngDoNome:
    def test_o_png_abre_e_tem_a_altura_da_mascara_ampliada(self):
        """Um PNG que nao abre e uma imagem que o WhatsApp descarta calado."""
        mascara = mascara_com_texto(1)
        bruto = png_do_nome(mascara, "0dcf6f")

        assert bruto[:8] == b"\x89PNG\r\n\x1a\n", "nao e um PNG"

        img = cv2.imdecode(np.frombuffer(bruto, np.uint8), cv2.IMREAD_GRAYSCALE)
        assert img is not None
        altura_do_nome = mascara.shape[0] * AMPLIACAO
        assert img.shape[0] > altura_do_nome, "a moldura sumiu"
        assert img.shape[1] > mascara.shape[1] * AMPLIACAO, (
            "a faixa do apelido sumiu: a largura devia passar da mascara "
            "ampliada"
        )

    def test_o_texto_sai_preto_no_branco_e_sem_meio_tom(self):
        """A inversao e a ampliacao NEAREST, provadas nos pixels.

        Suavizar (INTER_LINEAR) inventaria cinzas entre os pixels do jogo, e
        cinza inventado sobre uma fonte de 20 px de altura e exatamente o que
        transforma um `l` num `I`. A ausencia de meio-tom E a prova.
        """
        mascara = mascara_com_texto(2)
        img = cv2.imdecode(
            np.frombuffer(png_do_nome(mascara, "abc123"), np.uint8),
            cv2.IMREAD_GRAYSCALE,
        )

        # O fundo domina: a mascara acende uma coluna a cada cinco.
        assert (img > 200).mean() > 0.5, "a imagem saiu escura: faltou inverter"

        # Na AREA DO NOME (a direita da faixa do apelido) so ha 0 e 255. A
        # moldura e a margem ficam de fora: elas nao sao pixel do jogo.
        borda = MARGEM + MOLDURA
        area = img[borda:-borda, -(mascara.shape[1] * AMPLIACAO + borda) : -borda]
        tons = set(np.unique(area).tolist())
        assert tons <= {0, 255}, f"a ampliacao suavizou: {sorted(tons)}"

    def test_o_apelido_viaja_DENTRO_dos_pixels(self):
        """A legenda nao pode depender da ordem sobreviver ao cliente.

        Duas imagens da MESMA mascara com apelidos diferentes tem de diferir
        nos PIXELS. Se diferissem so no nome do arquivo, o WhatsApp — que
        reordena e renomeia o que quer — poderia entregar a legenda errada, e a
        legenda errada batiza a pessoa errada.
        """
        mascara = mascara_com_texto(3)

        uma = png_do_nome(mascara, "0dcf6f")
        outra = png_do_nome(mascara, "15caec")

        assert uma != outra, "o apelido nao entrou na imagem"

    def test_mascara_vazia_e_recusada_em_vez_de_virar_png_mentiroso(self):
        """Um PNG de 0x0 sairia no grupo como uma bolha vazia.

        Levantar aqui e o que permite o chamador PULAR a entrada e mandar a
        pergunta assim mesmo — que e a regra 3 do encargo.
        """
        with pytest.raises(ValueError):
            png_do_nome(np.zeros((0, 0), dtype=np.uint8), "0dcf6f")

    def test_o_anexo_leva_o_apelido_no_nome_do_arquivo(self):
        anexo = anexo_do_nome("0dcf6f", mascara_com_texto(4))

        assert anexo.nome_do_arquivo == "0dcf6f.png"
        assert anexo.tipo == "image/png"
        assert anexo.conteudo[:8] == b"\x89PNG\r\n\x1a\n"

    def test_o_acervo_real_do_usuario_ainda_desenha(self):
        """A prova de campo, e ela e read-only.

        As 15 entradas de `.identidades/` sao os unicos recortes REAIS que
        existem. Se elas deixarem de desenhar, o recurso morreu no unico lugar
        onde ele importa. O caso PULA quando a pasta nao existe (outra maquina,
        CI), porque um teste que exige o disco de uma pessoa e um teste que
        quebra na maquina de todo mundo.
        """
        pasta = RAIZ / ".identidades"
        arquivos = sorted(pasta.glob("*assinatura_*.json")) if pasta.exists() else []
        if not arquivos:
            pytest.skip("acervo real ausente nesta maquina")

        for arquivo in arquivos:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            dados.setdefault("nome", "")
            assinatura = Assinatura.de_dict(dados)
            bruto = png_do_nome(assinatura.mascara, "abcdef")
            assert bruto[:8] == b"\x89PNG\r\n\x1a\n", arquivo.name
            # Medido em 01/09/2026: as 15 entradas ficaram entre 3.9 KB e
            # 6.4 KB. O teto de 64 KB e folga de uma ordem de grandeza, e
            # existe para acusar o dia em que alguem trocar o PNG por BMP.
            assert len(bruto) < 64_000, f"{arquivo.name}: {len(bruto)} bytes"


# ---------------------------------------------------------------------------
# TAREFA 2: o multipart, montado a mao e afirmado SEM REDE
# ---------------------------------------------------------------------------


class TestOCorpoMultipart:
    ANEXOS = (
        Anexo(nome_do_arquivo="0dcf6f.png", conteudo=b"\x89PNG-um"),
        Anexo(nome_do_arquivo="15caec.png", conteudo=b"\x89PNG-dois"),
    )

    def test_abre_e_fecha_na_fronteira(self):
        corpo = montar_multipart(
            {"content": "oi", "message_type": "outgoing"}, self.ANEXOS, "FR0NT"
        )

        assert corpo.startswith(b"--FR0NT\r\n")
        assert corpo.endswith(b"--FR0NT--\r\n")

    def test_os_campos_de_texto_viajam_como_partes_de_formulario(self):
        corpo = montar_multipart(
            {"content": "Aprendi 1 pessoa", "message_type": "outgoing"},
            (),
            "FR0NT",
        )

        assert b'Content-Disposition: form-data; name="content"\r\n\r\n' in corpo
        assert b"Aprendi 1 pessoa\r\n" in corpo
        assert (
            b'Content-Disposition: form-data; name="message_type"\r\n\r\n'
            b"outgoing\r\n" in corpo
        )

    def test_cada_anexo_e_uma_parte_attachments_com_os_bytes_intactos(self):
        corpo = montar_multipart({}, self.ANEXOS, "FR0NT")

        assert corpo.count(b'name="attachments[]"') == 2
        assert (
            b'Content-Disposition: form-data; name="attachments[]"; '
            b'filename="0dcf6f.png"\r\nContent-Type: image/png\r\n\r\n'
            b"\x89PNG-um\r\n" in corpo
        )
        assert b"\x89PNG-dois\r\n" in corpo

    def test_a_ordem_das_partes_e_a_ordem_da_lista(self):
        """A ordem do texto e a das imagens tem de ser a MESMA.

        Se elas divergirem, o usuario batiza a pessoa errada — que e a mentira
        plausivel que este projeto inteiro combate.
        """
        corpo = montar_multipart({}, self.ANEXOS, "FR0NT")

        assert corpo.index(b"0dcf6f.png") < corpo.index(b"15caec.png")

    def test_toda_quebra_de_linha_do_envelope_e_CRLF(self):
        """`\\n` sozinho quebra o parser de multipart de servidor nenhum ser gentil.

        Um `\\n` no envelope faz o Rails do Chatwoot ver UMA parte gigante em
        vez de tres, e o desfecho e um 422 que parece erro de token.
        """
        corpo = montar_multipart({"content": "oi"}, self.ANEXOS, "FR0NT")
        envelope = corpo.replace(b"\r\n", b"")

        assert b"\n" not in envelope, "sobrou um \\n solto no envelope"

    def test_a_fronteira_escolhida_nunca_aparece_dentro_de_um_anexo(self):
        """Uma fronteira que aparece no conteudo corta a mensagem ao meio.

        A chance com hex aleatorio e desprezivel, e "desprezivel" nao e
        "impossivel" — e o desfecho seria um anexo truncado que o servidor
        aceita e o usuario recebe pela metade. O caso forca a colisao para
        provar que a escolha REAGE, em vez de confiar na sorte.
        """
        colidido = Anexo(nome_do_arquivo="x.png", conteudo=b"...COLIDE...")
        candidatos = iter(["COLIDE", "COLIDE", "LIMPA"])

        escolhida = escolher_fronteira((colidido,), gerar=lambda: next(candidatos))

        assert escolhida == "LIMPA", (
            "a escolha aceitou uma fronteira que aparece dentro do anexo"
        )

    def test_a_fronteira_de_verdade_e_sorteada_e_nao_fixa(self):
        """Duas chamadas seguidas nao podem devolver a mesma fronteira.

        Uma fronteira constante no fonte e uma fronteira que qualquer conteudo
        futuro pode conter de proposito.
        """
        assert escolher_fronteira(()) != escolher_fronteira(())

    def test_um_nome_de_arquivo_com_aspas_ou_CRLF_nao_injeta_cabecalho(self):
        """O nome do arquivo entra DENTRO de um cabecalho.

        Hoje o apelido e hex e nao tem como conter aspas. Mas o dia em que
        alguem passar o nick do jogador aqui e o dia em que um nick com `"` ou
        com CRLF vira cabecalho HTTP inventado. Custa uma linha fechar agora.
        """
        veneno = Anexo(
            nome_do_arquivo='a"\r\nContent-Type: text/html\r\n\r\n<b>x.png',
            conteudo=b"z",
        )

        corpo = montar_multipart({}, (veneno,), "FR0NT")

        crlf = b"\r\n"
        cabecalhos, _, _ = corpo.partition(crlf + crlf)
        linhas = cabecalhos.split(crlf)

        # Fronteira, Content-Disposition, Content-Type. Nem uma linha a mais:
        # o veneno nao virou cabecalho, virou texto dentro do `filename`.
        assert len(linhas) == 3, linhas
        assert linhas[0] == b"--FR0NT"
        assert linhas[2] == b"Content-Type: image/png"
        assert linhas[1].count(b'"') == 4, (
            "sobrou uma aspa do veneno: o valor do filename escapou"
        )


# ---------------------------------------------------------------------------
# TAREFA 3: o caminho de TEXTO PURO nao muda, byte a byte
# ---------------------------------------------------------------------------


class TestOTextoPuroContinuaJson:
    def test_sem_anexo_o_corpo_e_o_json_de_sempre(self, monkeypatch):
        falso = UrlopenFalso()
        notificador = chatwoot(monkeypatch, falso)

        notificador.enviar("Korzis: HP zerado")

        assert len(falso.requisicoes) == 1
        req = falso.requisicoes[0]
        assert req.cabecalhos["content-type"] == "application/json"
        assert req.corpo == json.dumps(
            {"content": "Korzis: HP zerado", "message_type": "outgoing"}
        ).encode("utf-8")

    def test_com_anexo_o_content_type_e_multipart_e_o_json_nao_sai(
        self, monkeypatch
    ):
        falso = UrlopenFalso()
        notificador = chatwoot(monkeypatch, falso)

        notificador.enviar(
            "Aprendi 1 pessoa",
            anexos=(Anexo(nome_do_arquivo="0dcf6f.png", conteudo=b"\x89PNG"),),
        )

        assert len(falso.requisicoes) == 1, "uma mensagem, e nao duas"
        req = falso.requisicoes[0]
        assert req.cabecalhos["content-type"].startswith("multipart/form-data;")
        assert b"boundary" not in req.corpo, "o boundary e do cabecalho"
        assert b"Aprendi 1 pessoa" in req.corpo
        assert b"0dcf6f.png" in req.corpo


# ---------------------------------------------------------------------------
# TAREFA 4: falha de anexo NAO engole a pergunta
# ---------------------------------------------------------------------------


class TestFalhaDeAnexoNaoEngoleAPergunta:
    ANEXO = (Anexo(nome_do_arquivo="0dcf6f.png", conteudo=b"\x89PNG"),)

    def test_multipart_que_falha_cai_para_o_texto_puro(self, monkeypatch):
        """Uma pessoa que nunca e perguntada fica anonima PARA SEMPRE.

        O marcador `perguntado_<chave>` e de uma vez so, e ja foi queimado
        antes desta chamada existir. Entao nenhum caminho pode terminar sem uma
        tentativa de texto puro.
        """
        falso = UrlopenFalso(
            falhar_se=lambda req: b"attachments[]" in (req.corpo or b"")
        )
        notificador = chatwoot(monkeypatch, falso)

        notificador.enviar(
            "com imagem", anexos=self.ANEXO, texto_sem_anexos="sem imagem"
        )

        assert len(falso.requisicoes) == 2
        segunda = falso.requisicoes[1]
        assert segunda.cabecalhos["content-type"] == "application/json"
        assert json.loads(segunda.corpo)["content"] == "sem imagem", (
            "a reserva tem de ser o texto que NAO promete imagem nenhuma"
        )

    def test_o_texto_de_reserva_omitido_cai_para_o_texto_original(
        self, monkeypatch
    ):
        falso = UrlopenFalso(
            falhar_se=lambda req: b"attachments[]" in (req.corpo or b"")
        )
        notificador = chatwoot(monkeypatch, falso)

        notificador.enviar("so este texto", anexos=self.ANEXO)

        assert json.loads(falso.requisicoes[1].corpo)["content"] == "so este texto"

    def test_quando_os_dois_falham_o_erro_sobe_para_o_despachante_tentar_de_novo(
        self, monkeypatch
    ):
        falso = UrlopenFalso(falhar_se=lambda req: True)
        notificador = chatwoot(monkeypatch, falso)

        with pytest.raises(ErroDeEntrega):
            notificador.enviar("com imagem", anexos=self.ANEXO)

        assert len(falso.requisicoes) == 2

    def test_imagem_que_nao_codifica_nao_impede_a_pergunta(self, monkeypatch):
        """"o que for" do encargo, e o "o que for" inclui o desenho.

        Quem monta a pergunta PULA a entrada cuja mascara nao desenha, e a
        pergunta sai com as outras. Zero imagens desenhadas cai no caminho de
        texto puro, que e o de hoje.
        """
        sem_imagem_nenhuma: tuple[Anexo, ...] = ()
        falso = UrlopenFalso()
        notificador = chatwoot(monkeypatch, falso)

        notificador.enviar("Aprendi 1 pessoa", anexos=sem_imagem_nenhuma)

        assert falso.requisicoes[0].cabecalhos["content-type"] == "application/json"


# ---------------------------------------------------------------------------
# TAREFA 5: a pergunta. UMA mensagem, com as imagens na ordem do texto.
# ---------------------------------------------------------------------------


def apelidos_listados(texto: str) -> list[str]:
    """Os apelidos na ordem em que a mensagem os lista."""
    return [
        linha.strip().split(" ")[0]
        for linha in texto.splitlines()
        if linha.startswith("  ")
    ]


class TestAPerguntaLevaAsImagens:
    def test_tres_anonimas_produzem_UMA_pergunta_com_TRES_imagens(self, tmp_path):
        for semente in range(3):
            semear(tmp_path, assinatura_fabricada(semente))
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        assert pergunta is not None
        assert pergunta.texto.count("Aprendi") == 1, "voltou a rajada de N bolhas"
        assert len(pergunta.imagens) == 3

    def test_a_ordem_das_imagens_e_a_ordem_do_texto(self, tmp_path):
        """Se elas divergirem, o usuario batiza a pessoa errada."""
        for semente in range(4):
            semear(tmp_path, assinatura_fabricada(semente))
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        assert [anexo.nome_do_arquivo for anexo in pergunta.imagens] == [
            f"{apelido}.png" for apelido in apelidos_listados(pergunta.texto)
        ]

    def test_o_texto_avisa_que_a_imagem_veio_junto(self, tmp_path):
        semear(tmp_path, assinatura_fabricada(9))
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        assert "imagem" in pergunta.texto.lower()

    def test_a_reserva_e_o_texto_SEM_a_promessa_de_imagem(self, tmp_path):
        """O texto que sai quando o anexo falha nao pode prometer imagem.

        Prometer uma imagem que nao chegou e a mentira plausivel de sempre:
        parece uma mensagem normal, e manda o dono procurar um anexo que nao
        existe.
        """
        semear(tmp_path, assinatura_fabricada(10))
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        assert "imagem" not in pergunta.texto_sem_imagens.lower()
        assert "/batizar" in pergunta.texto_sem_imagens
        assert apelidos_listados(pergunta.texto_sem_imagens) == apelidos_listados(
            pergunta.texto
        )

    def test_a_pergunta_nova_nao_tem_travessao_e_cabe_no_cp1252(self, tmp_path):
        for semente in range(TETO_DE_IMAGENS + 2):
            semear(tmp_path, assinatura_fabricada(semente))
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        for texto in (pergunta.texto, pergunta.texto_sem_imagens):
            assert "—" not in texto, f"travessao em: {texto!r}"
            assert "–" not in texto, f"meia risca em: {texto!r}"
            texto.encode("cp1252")

    def test_a_frase_nova_nao_cita_posicao_nenhuma(self, tmp_path):
        """`test_a_varredura_NAO_cita_posicao_nenhuma` ja vale para a lista.

        A frase NOVA entra no mesmo texto, entao ela cai sob a mesma regra: a
        varredura nao sabe em que posicao aquela pessoa estava, e inventar uma
        seria a primeira mentira do caminho.
        """
        for semente in range(2):
            semear(tmp_path, assinatura_fabricada(semente))
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        assert "linha" not in pergunta.texto.lower(), pergunta.texto

    def test_montar_pergunta_continua_devolvendo_o_TEXTO(self, tmp_path):
        """O involucro antigo sobrevive, e devolve o mesmo texto.

        Ha cerca de trinta casos afirmando o texto por esta porta. Quebrar a
        assinatura deles nao provaria nada novo.
        """
        semear(tmp_path, assinatura_fabricada(11))
        acervo = AcervoDeIdentidades(tmp_path)

        assert isinstance(montar_pergunta(acervo, pendentes_do_acervo(acervo)), str)

    def test_sem_pendente_nenhum_nao_ha_pergunta_nem_imagem(self, tmp_path):
        acervo = AcervoDeIdentidades(tmp_path)

        assert montar_pergunta_com_imagens(acervo, []) is None


class TestOTetoDeImagens:
    def test_acima_do_teto_so_o_teto_vai_e_o_TEXTO_DIZ_quem_sobrou(
        self, tmp_path
    ):
        """Truncar em silencio e proibido: se sobrar gente, o texto diz.

        O teto e sobre GENTE, e nao sobre bytes: medido em 01/09/2026, as 15
        entradas do acervo real dao PNGs de 3.9 KB a 6.4 KB, entao oito somam
        ~39 KB e nao apertam nada. Oito e o tanto de gente que a party window
        do L2 mostra alem de voce; mais que isso de uma vez nao e uma party na
        tela, e acervo acumulado de varias sessoes.
        """
        sobrando = 3
        for semente in range(TETO_DE_IMAGENS + sobrando):
            semear(tmp_path, assinatura_fabricada(semente))
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        assert len(pergunta.imagens) == TETO_DE_IMAGENS
        # TODOS continuam na lista de apelidos: quem nao tem imagem tem nome.
        assert len(apelidos_listados(pergunta.texto)) == TETO_DE_IMAGENS + sobrando
        assert str(sobrando) in pergunta.texto, (
            f"o texto nao diz quantas ficaram sem imagem:\n{pergunta.texto}"
        )

    def test_no_teto_exato_o_texto_nao_fala_de_sobra_nenhuma(self, tmp_path):
        for semente in range(TETO_DE_IMAGENS):
            semear(tmp_path, assinatura_fabricada(semente))
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta_com_imagens(acervo, pendentes_do_acervo(acervo))

        assert len(pergunta.imagens) == TETO_DE_IMAGENS
        assert "ficaram sem imagem" not in pergunta.texto
        assert "ficou sem imagem" not in pergunta.texto


# ---------------------------------------------------------------------------
# TAREFA 6: A COSTURA. As imagens tem de chegar ao transporte pelos DOIS
# gatilhos, e nao so pelo que o teste de unidade alcanca.
# ---------------------------------------------------------------------------
#
# O precedente e `TestFuncionaNosDoisLacos` de `test_janela_sob_demanda.py`:
# logica certa ligada num caminho so e a familia de defeito que este projeto
# ja pagou. Aqui os dois caminhos sao o APRENDIZADO (dentro da `Sessao`) e a
# VARREDURA DE ARRANQUE (dentro do `laco_principal`), e o do arranque e o
# unico que alcanca as entradas que JA estao no disco do usuario.


def _chamadas_de_despacho_da_pergunta(fonte: str) -> list[ast.Call]:
    """As chamadas de despacho cujo argumento vem de uma pergunta do batismo.

    Le a ESTRUTURA e nao o comportamento, pelo mesmo motivo do portao de elos
    de `test_batismo.py`: um caso de comportamento no `laco_principal` exigiria
    subir o programa inteiro, e o que esta em jogo aqui e uma ligacao que pode
    sumir num refactor sem nenhum teste ficar vermelho.
    """
    achadas = []
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Call):
            continue
        alvo = getattr(no.func, "id", None) or getattr(no.func, "attr", None)
        if alvo not in {"despachar", "_despachar"}:
            continue
        primeiro = no.args[0] if no.args else None
        vindo_da_pergunta = isinstance(primeiro, ast.Attribute) and (
            getattr(primeiro.value, "id", None) == "pergunta"
        )
        if vindo_da_pergunta:
            achadas.append(no)
    return achadas


class TestAsImagensChegamNosDoisGatilhos:
    ARQUIVOS = ("sessao.py", "__main__.py")

    @pytest.mark.parametrize("arquivo", ARQUIVOS)
    def test_o_despacho_da_pergunta_leva_anexos_e_reserva(self, arquivo):
        fonte = (RAIZ / "l2scanner" / arquivo).read_text(encoding="utf-8")

        chamadas = _chamadas_de_despacho_da_pergunta(fonte)
        assert chamadas, (
            f"{arquivo}: nenhum despacho de `pergunta.<campo>`. Ou a pergunta "
            f"deixou de sair, ou ela voltou a ser uma string solta e as "
            f"imagens ficaram para tras"
        )
        for chamada in chamadas:
            passados = {palavra.arg for palavra in chamada.keywords}
            assert "anexos" in passados, (
                f"{arquivo}:{chamada.lineno}: a pergunta sai sem as imagens"
            )
            assert "texto_sem_anexos" in passados, (
                f"{arquivo}:{chamada.lineno}: sem a reserva, uma falha de "
                f"anexo mandaria um texto que promete uma imagem que nao "
                f"chegou"
            )

    @pytest.mark.parametrize("arquivo", ARQUIVOS)
    def test_o_portao_acusaria_os_anexos_arrancados(self, arquivo):
        """Guarda contra prova vazia, POR ARQUIVO.

        Sem isto, um caminho de arquivo errado passaria verde para sempre.
        """
        fonte = (RAIZ / "l2scanner" / arquivo).read_text(encoding="utf-8")
        envenenado = fonte.replace("anexos=pergunta.imagens,", "")

        assert envenenado != fonte, "a mutacao plantada nao pegou"
        for chamada in _chamadas_de_despacho_da_pergunta(envenenado):
            if "anexos" not in {p.arg for p in chamada.keywords}:
                return
        raise AssertionError(
            f"o portao nao acusaria um despacho de {arquivo} sem `anexos=`"
        )


class TestOTransporteLevaAsImagensAteOFim:
    """Do `despachar` ate o `enviar`, com o `Despachante` DE VERDADE.

    Um despachante falso nunca exercitaria a fila nem a thread, e o que esta em
    jogo aqui e justamente se os anexos ATRAVESSAM a fila: eles sao
    assincronos, e a informacao se perderia se ficasse so na chamada.
    """

    def test_os_anexos_atravessam_a_fila(self, tmp_path):
        notificador = NotificadorEmMemoria()
        despachante = Despachante(
            notificador, arquivo_outbox=tmp_path / "outbox.jsonl"
        )
        despachante.iniciar()
        despachante.despachar(
            "com imagem",
            Categoria.SEMPRE,
            anexos=(Anexo(nome_do_arquivo="0dcf6f.png", conteudo=b"\x89PNG"),),
            texto_sem_anexos="sem imagem",
        )
        fim = time.monotonic() + 10.0
        while despachante.entregues == 0 and time.monotonic() < fim:
            time.sleep(0.02)
        despachante.encerrar(espera_maxima=2.0)

        assert notificador.enviados == ["com imagem"]
        assert notificador.anexados == [("0dcf6f.png",)]

    def test_o_outbox_registra_QUAIS_imagens_iam_junto(self, tmp_path):
        """O outbox e a forense pos-farm, e so os NOMES entram.

        Enfiar ~40 KB de PNG por pergunta num JSONL que ninguem poda trocaria
        a utilidade dele por peso.
        """
        outbox = tmp_path / "outbox.jsonl"
        despachante = Despachante(NotificadorEmMemoria(), arquivo_outbox=outbox)
        despachante.despachar(
            "com imagem",
            Categoria.SEMPRE,
            anexos=(Anexo(nome_do_arquivo="0dcf6f.png", conteudo=b"\x89PNG"),),
        )

        bruto = outbox.read_text(encoding="utf-8")
        registro = json.loads(bruto.strip())
        assert registro["anexos"] == ["0dcf6f.png"]
        assert "PNG" not in bruto, "o conteudo do anexo vazou para o outbox"

    def test_sem_imagem_o_outbox_continua_com_os_dois_campos_de_sempre(
        self, tmp_path
    ):
        outbox = tmp_path / "outbox.jsonl"
        despachante = Despachante(NotificadorEmMemoria(), arquivo_outbox=outbox)
        despachante.despachar("Korzis: HP zerado")

        registro = json.loads(outbox.read_text(encoding="utf-8").strip())
        assert set(registro) == {"momento", "texto"}
