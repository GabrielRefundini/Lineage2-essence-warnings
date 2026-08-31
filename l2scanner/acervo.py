"""O acervo duravel de assinaturas visuais, fora do `calibration.json`.

POR QUE A PASTA E PROPRIA, E NAO UM CAMPO DA CALIBRACAO

`calibrar.py` monta uma `Calibracao` do zero e grava por cima do arquivo
INTEIRO. WINDOWS #13, confirmado em campo em 2026-08-30: o usuario rodou
`calibrar.bat` e perdeu 13 moldes de glifo e 3 ancoras do mercado. O conserto
ja escrito (`fundir_com_a_calibracao_em_disco`) preserva os campos que a party
NAO possui — e `CAMPOS_DA_PARTY` INCLUI `assinaturas`. Ou seja: uma assinatura
aprendida dentro do `calibration.json` nao morreria por bug, morreria por
DESENHO, toda vez que alguem recalibrasse. Por isso `.identidades/` e irma de
`.agenda/` e de `.loot/`, e nao um campo a mais no arquivo que o calibrador
reescreve.

A CHAVE E O HASH DO CONTEUDO, NUNCA DA POSICAO NEM DO NOME

Uma entrada e nomeada pelo `sha256` do material da propria mascara. Isso
satisfaz tres exigencias de uma vez:

- **estavel entre reinicios** — a mesma pessoa, recortada de novo, da o mesmo
  nome de arquivo, entao o acervo nao duplica a cada arranque;
- **independente da POSICAO** — a party window compacta as linhas quando alguem
  sai, e a posicao nunca foi identidade;
- **independente do NOME** — batizar (Fase 3) e criar o arquivo irmao
  `nome_<chave>`, e corrigir e trocar o conteudo dele. A assinatura nao e
  tocada, entao a chave nao muda quando o nome chega ou e corrigido.

A alternativa recusada foi contador sequencial: o usuario roda DUAS instancias
(Yazalaque e Faerlina) sobre a mesma pasta, e as duas gerariam numeros
conflitantes para a MESMA pessoa.

O ACERVO NAO E PODADO, E ISSO FOI MEDIDO

Uma assinatura ocupa 562 bytes, medido no `calibration.json` real do usuario em
2026-08-31. Mil membros dao ~550 KB. O usuario viu o numero e aceitou o
crescimento sem poda nem comando de limpeza no v1 — a mesma decisao do `.loot/`,
pela mesma razao: "quem e o Fulano" e uma pergunta sobre meses, e o `.agenda/`
poda em 3 dias.

O QUE ESTE MODULO NAO CONHECE

Ele nao importa `calibracao`, nem `rastreador`, nem `visao`. Fala `Assinatura` e
`Path`, e so. A fusao com as assinaturas calibradas recebe uma
`list[Assinatura]` justamente para nao arrastar `Calibracao` para ca.

E ele nao tem relogio nenhum — nem `datetime.now()`, nem `time.time()`. A
proibicao esta presa pelo portao AST de `tests/test_presenca.py`, porque a
maneira de um acervo DURAVEL adquirir poda por acidente e adquirir um relogio
proprio primeiro.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .identidade import Assinatura

PREFIXO_ASSINATURA = "assinatura_"
SUFIXO_ASSINATURA = ".json"
PREFIXO_NOME = "nome_"

# Uma chave e 64 digitos hex, e NADA MAIS.
#
# Usado sempre com `fullmatch`, e e o que torna travessia de caminho
# estruturalmente impossivel na leitura: um nome de arquivo que nao seja hex
# puro nunca vira chave, entao nao ha `..` nem separador que chegue a virar
# caminho de irmao.
CHAVE_VALIDA = re.compile(r"[0-9a-f]{64}")

# O charset de nick do L2.
#
# NAO se importa `loot.NICK_VALIDO` de proposito: `loot` importa `agenda`, e
# arrastar essa cadeia para um modulo que precisa NAO ter relogio nenhum (o
# acervo e duravel e nao podado) trocaria uma linha de regex por um acoplamento
# que o portao AST depois teria de raciocinar sobre.
NOME_VALIDO = re.compile(r"[A-Za-z0-9]{2,16}")


def chave_da_assinatura(assinatura: Assinatura) -> str:
    """O nome de arquivo desta assinatura: sha256 do conteudo, 64 digitos hex.

    O material e `f"{altura}x{largura}:{bits}"` — as dimensoes E os bytes
    empacotados da mascara, e nada mais. O `nome` fica de fora POR CONSTRUCAO:
    e o que faz a chave nao mudar quando o nome chega ou e corrigido.

    POR QUE AS DIMENSOES ENTRAM NO MATERIAL. `packbits` de uma mascara 2x8 e de
    uma mascara 4x4 produz os MESMOS bytes. Sem a dimensao no material, duas
    mascaras DIFERENTES compartilhariam chave — e compartilhar chave e
    compartilhar NOME. Nao e uma colisao que depende de sorte: basta um recorte
    de altura diferente.

    POR QUE O HEX INTEIRO, E NAO 16 DIGITOS. Truncar para 16 hex daria colisao
    de aniversario da ordem de 3e-14 com mil entradas — desprezivel na planilha.
    Mas o desfecho de uma colisao AQUI nao e um erro: e "Korzis morreu" quando
    morreu o Kaus, com a mensagem parecendo perfeitamente normal e a party
    socorrendo a pessoa errada. Exatamente a mentira plausivel que a identidade
    por imagem existe para impedir. O preco do hex inteiro sao 48 caracteres a
    mais no nome do arquivo; comprar margem de colisao por isso e barato.

    Decisao travada pelo usuario em 2026-08-31, com o trade na mesa. Ela e de
    mao unica: a chave E o nome do arquivo, e trocar a funcao de hash ou o
    material orfana TODAS as entradas de uma vez, numa pasta gitignored, sem
    backup e sem versionamento.
    """
    dados = assinatura.como_dict()
    material = f"{dados['altura']}x{dados['largura']}:{dados['bits']}"
    return hashlib.sha256(material.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class Identidades:
    """Quem o scanner conhece neste arranque: as calibradas mais o acervo.

    `conhecidas`, `sem_nome` e `resumo` sao DERIVADOS da lista, e nao campos
    guardados: um par de contadores gravado ao lado da lista e um par de
    contadores que pode discordar dela, e a linha de arranque que o usuario le
    seria justamente onde a discordancia apareceria.
    """

    assinaturas: list[Assinatura] = field(default_factory=list)

    @property
    def configuradas(self) -> bool:
        """Ha identidade visual em jogo?

        E este booleano que o `Rastreador` recebe para decidir entre calar e
        pegar emprestado o nome da lista por posicao.
        """
        return bool(self.assinaturas)

    @property
    def conhecidas(self) -> int:
        return len(self.assinaturas)

    @property
    def sem_nome(self) -> int:
        return sum(1 for a in self.assinaturas if a.anonima)

    @property
    def resumo(self) -> str:
        """A linha de arranque. Sem acento e sem travessao, como todo texto que
        o usuario le."""
        if not self.assinaturas:
            return "Identidades: nenhuma assinatura conhecida"
        return (
            f"Identidades: {self.conhecidas} assinatura(s) conhecida(s), "
            f"{self.sem_nome} sem nome"
        )


class AcervoDeIdentidades:
    """As assinaturas em disco, uma por arquivo, na pasta compartilhada.

    Dois tipos de arquivo convivem na pasta, cada um com prefixo proprio:

    - `assinatura_<64 hex>.json` — o conteudo da mascara, SEM o nome.
    - `nome_<64 hex>` — texto puro utf-8 com o nick. Escrito so no batismo.

    Um arquivo por entrada, no molde do `.loot/`: `O_CREAT|O_EXCL` resolve a
    corrida das duas instancias de graca, e nao ha ler-modificar-escrever para
    corromper.

    NAO tem poda, de proposito.
    """

    def __init__(self, pasta: Path) -> None:
        self._pasta = pasta
        self._pasta.mkdir(parents=True, exist_ok=True)

    # -- escrita ------------------------------------------------------------

    def gravar(self, assinatura: Assinatura) -> str:
        """Grava uma assinatura. Tri-estado: criado | ja_existia | falhou.

        ESTE ACERVO SEGUE O `loot.RegistroDeLoot`, E NAO O
        `agenda.RegistroEmDisco`. O projeto tem os dois tri-estados e eles sao
        OPOSTOS, entao a escolha precisa estar escrita.

        O `marcar` da agenda colapsa `OSError` em True porque aviso duplicado e
        melhor que aviso perdido — la existe um desfecho barato para escolher no
        escuro (medido em campo: 2026-08-26 19:30, uma simulacao disputou a
        chave com o scanner real e por milissegundos nao apagou o aviso de TvT).

        Aqui nao existe desfecho barato. Colapsar `"falhou"` em `"criado"` faria
        a Fase 2 acreditar que aprendeu uma pessoa que nao esta em disco, parar
        de perguntar (o batismo pergunta UMA vez) e deixa-la anonima para
        sempre, sem erro em lugar nenhum. Colapsar em `"ja_existia"` seria
        igualmente falso: a deduplicacao tomaria uma falha de disco por
        conhecimento. A escrita duplicada ja e recusada pelo `O_EXCL`, entao a
        unica assimetria que sobra e perdido-contra-repetir — e repetir e de
        graca.

        O `O_CREAT|O_EXCL` resolve a corrida das duas instancias do usuario de
        graca: exatamente uma cria, a outra recebe `"ja_existia"`, e nao ha
        ler-modificar-escrever para corromper.

        O corpo gravado NAO tem a chave `nome`. O nome mora no arquivo irmao, e
        e por isso que a chave nao muda quando ele chega.
        """
        chave = chave_da_assinatura(assinatura)
        corpo = assinatura.como_dict()
        corpo.pop("nome", None)
        dados = json.dumps(corpo).encode("utf-8")
        alvo = self._pasta / f"{PREFIXO_ASSINATURA}{chave}{SUFIXO_ASSINATURA}"

        try:
            descritor = os.open(alvo, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return "ja_existia"
        except OSError:
            return "falhou"

        # Diferenca em relacao ao `.loot/`: la o arquivo e VAZIO e a identidade
        # E o nome. Aqui o corpo carrega o conteudo da assinatura, entao ha uma
        # escrita entre o `open` e o `close` — e ela tambem pode falhar.
        falhou = False
        try:
            falhou = os.write(descritor, dados) != len(dados)
        except OSError:
            falhou = True
        # O `close` entra FORA do try da escrita e conta como falha por conta
        # propria: no Windows os bytes so chegam ao disco no fechamento, entao
        # um `close` que levanta e uma gravacao que nao aconteceu.
        try:
            os.close(descritor)
        except OSError:
            falhou = True

        if falhou:
            # Apagar o que ficou pela metade, e nao deixar para tras.
            #
            # O `O_EXCL` garante que ESTE processo criou o arquivo, entao
            # remove-lo nao pode atropelar a outra instancia. Deixa-lo faria a
            # proxima tentativa receber `"ja_existia"` sobre uma entrada que a
            # leitura descarta — ou seja, o acervo diria para sempre que conhece
            # alguem que ele nao consegue ler.
            try:
                alvo.unlink()
            except OSError:
                pass
            return "falhou"

        return "criado"

    # -- leitura ------------------------------------------------------------

    def chaves(self) -> list[str]:
        """As chaves presentes na pasta, ordenadas.

        So conta o que a leitura de fato aceita: um arquivo cujo conteudo nao
        produz a propria chave nao esta no acervo, e dizer que esta faria a
        contagem do arranque mentir sobre o que o scanner consegue reconhecer.
        """
        return [chave for chave, _ in self._entradas()]

    def assinaturas(self) -> list[Assinatura]:
        """Todas as assinaturas legiveis, ordenadas pela chave.

        A ORDEM E PARTE DO CONTRATO. Ela entra no desempate do guloso de
        `identificar_linhas` (`max` sobre `(pontuacao, -i, -j)`), entao ordem
        instavel entre dois arranques seria reconhecimento instavel entre dois
        arranques — com o jogo e a tela exatamente iguais.
        """
        return [assinatura for _, assinatura in self._entradas()]

    def _entradas(self) -> list[tuple[str, Assinatura]]:
        """Os pares (chave, assinatura) que sobreviveram a conferencia.

        Qualquer arquivo que levante `(OSError, ValueError, TypeError,
        KeyError)` e PULADO sem propagar, como `loot.registros()` faz: a pasta e
        compartilhada e duravel, e lixo que caia nela nao pode virar excecao no
        meio do farm.
        """
        try:
            nomes = sorted(c.name for c in self._pasta.iterdir())
        except OSError:
            return []

        achados: list[tuple[str, Assinatura]] = []
        for nome_do_arquivo in nomes:
            chave = self._chave_do_nome(nome_do_arquivo)
            if chave is None:
                continue
            assinatura = self._ler(chave, nome_do_arquivo)
            if assinatura is not None:
                achados.append((chave, assinatura))
        return achados

    @staticmethod
    def _chave_do_nome(nome_do_arquivo: str) -> str | None:
        if not nome_do_arquivo.startswith(PREFIXO_ASSINATURA):
            return None
        if not nome_do_arquivo.endswith(SUFIXO_ASSINATURA):
            return None
        chave = nome_do_arquivo[
            len(PREFIXO_ASSINATURA) : -len(SUFIXO_ASSINATURA)
        ]
        return chave if CHAVE_VALIDA.fullmatch(chave) else None

    def _ler(self, chave: str, nome_do_arquivo: str) -> Assinatura | None:
        """Le uma entrada e CONFERE que ela e mesmo quem o nome do arquivo diz.

        A chave e RECALCULADA a partir do conteudo lido e comparada com a chave
        do nome do arquivo. Divergiu, a entrada e descartada. Isso faz o nome do
        arquivo deixar de ser uma AFIRMACAO e virar uma SOMA DE VERIFICACAO: um
        arquivo editado a mao (a pasta convida a isso — o batismo da Fase 3
        corrige nomes ali dentro) nao consegue se passar por outra assinatura.

        O `nome` vem EXCLUSIVAMENTE do irmao `nome_<chave>`. Uma chave `nome`
        enfiada a mao dentro do json e ignorada por construcao: ela nao entra no
        material do hash e nao entra no objeto.
        """
        try:
            bruto = json.loads(
                (self._pasta / nome_do_arquivo).read_text(encoding="utf-8")
            )
            candidata = Assinatura.de_dict(
                {
                    "nome": "",
                    "altura": bruto["altura"],
                    "largura": bruto["largura"],
                    "bits": bruto["bits"],
                }
            )
        except (OSError, ValueError, TypeError, KeyError):
            return None

        if chave_da_assinatura(candidata) != chave:
            return None

        nome = self._nome_de(chave)
        return candidata if not nome else Assinatura(nome=nome, mascara=candidata.mascara)

    def _nome_de(self, chave: str) -> str:
        """O nick do irmao `nome_<chave>`, ou `""` quando nao da para confiar.

        O desfecho de um arquivo de nome ruim e SILENCIO, nunca um nome errado.
        Ausente, vazio, multilinha, com separador de caminho, fora do charset ou
        longo demais: tudo devolve `""`, e uma assinatura sem nome e reconhecida
        sem virar sujeito de alerta nenhum.

        Essa e a assimetria que importa: um nome faltando custa um "Membro N" no
        console; um nome errado custa a party socorrendo a pessoa errada.
        """
        try:
            texto = (self._pasta / f"{PREFIXO_NOME}{chave}").read_text(
                encoding="utf-8"
            )
        except (OSError, ValueError):
            return ""
        texto = texto.strip()
        return texto if NOME_VALIDO.fullmatch(texto) else ""


def carregar_identidades(
    calibradas: list[Assinatura], acervo: AcervoDeIdentidades
) -> Identidades:
    """Funde as assinaturas do `calibration.json` com as do acervo em disco.

    AS CALIBRADAS ENTRAM PRIMEIRO, e isso e carregado. `identificar_linhas`
    desempata por `-j`, entao no empate exato vence o indice MENOR: a
    precedencia da calibracao fica estrutural, e nao escrita numa condicao que
    alguem pode inverter sem perceber.

    Recebe `list[Assinatura]` e nao `Calibracao` de proposito — e o que mantem
    este modulo sem importar `calibracao`.

    Deduplicacao entre as duas fontes NAO acontece aqui: ela e o plano 01-02.
    Nesta fase a fusao e concatenacao com a ordem documentada.
    """
    return Identidades(assinaturas=list(calibradas) + acervo.assinaturas())
