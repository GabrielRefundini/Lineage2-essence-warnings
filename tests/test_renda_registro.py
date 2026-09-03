"""O arquivo `.renda/<personagem>.csv` como CONTRATO: os portoes, e o que NAO atravessou.

O QUE ESTE ARQUIVO PROVA, E POR QUE ELE E SEPARADO DO TRACER
=============================================================
`tests/test_renda_conta_tracer.py` prova a FATIA — que duas amostras montadas a
mao atravessam regras de par, passo, disco, leitor tolerante e taxa num caminho
so. Ele e uma linha reta e tem de continuar sendo lido como uma.

Este arquivo prova o ARQUIVO EM DISCO, que e a unica coisa desta fase que sai da
arvore e vira contrato com outro workstream. Ele e a expansao, e o que ele
carrega e diferente em natureza: os tres estados do cabecalho com o CONTROLE de
que nenhum byte foi alterado, o invariante das duas metades nos dois sentidos e
para os tres campos, cem amostras identicas produzindo cem linhas, o
desligamento por falha de disco, e a refutacao da C-2 executavel.

AS TRES AFIRMACOES MEDIDAS QUE ESTE ARQUIVO PRENDE
==================================================
- **C-3, a dedup que NAO atravessou.** `mercado_registro.chave_da_observacao`
  exclui o carimbo de proposito, para o arquivo do mercado nao crescer uma linha
  por segundo sobre o mesmo anuncio. Aqui uma linha por tique **E o produto** —
  ela e o denominador da taxa. O portao e comportamental e vem em duas escalas:
  DUAS amostras identicas -> DUAS linhas (pega dedup por identidade) e CEM
  amostras identicas -> CEM linhas (pega dedup por janela, que a de duas nao
  pegaria).
- **C-2, a frase que prometia demais.** `ROADMAP.md:290` e
  `REQUIREMENTS.md:284` afirmam que o `dashboard` acrescenta "uma lista de
  colunas, nao um parser". E falso, e aqui a refutacao e EXECUTAVEL: apontar
  `mercado_registro.observacoes_do_arquivo` para um CSV de renda recem-escrito
  levanta a excecao DO MERCADO, porque aquele parser confere o cabecalho contra
  o `COLUNAS` global dele (`mercado_registro.py:495`).
- **LEIT-11, a guarda que vai gravada.** 3 das 4 leituras erradas de nivel foram
  aceitas POR CONCORDANCIA das duas escalas. Sem a coluna da guarda, ninguem
  consegue perguntar depois se as erradas eram as de duas escalas ou as de uma.

ESTE ARQUIVO NAO PULA POR NADA
==============================
Um `skip` aqui e falha, e nao configuracao de maquina. Nao ha pixel, nao ha OCR,
nao ha rede, nao ha relogio — todo carimbo entra por parametro — e nenhum
caminho de disco sai de `tmp_path`. A `.renda/` real nunca e tocada.
"""

from __future__ import annotations

import ast
import csv
from pathlib import Path

import pytest

from l2scanner.mercado_catalogo import SEPARADOR
from l2scanner.renda_conta import SEM_DESCONTINUIDADE
from l2scanner.renda_leitura import (
    CAMPO_DA_ADENA,
    CAMPO_DO_EXP,
    CAMPO_DO_NIVEL,
    CamposDaRenda,
    RecusaDaRenda,
    ValorDaAdena,
    ValorDaRenda,
)
from l2scanner.renda_registro import (
    COLUNAS,
    ORIGEM_INDETERMINADA,
    ContratoDaRendaQuebrado,
    RegistroDaRenda,
    amostras_do_arquivo,
    arquivo_do_personagem,
    campos_da_linha,
)

FONTE_DO_MODULO = Path(__file__).resolve().parents[1] / "l2scanner" / "renda_registro.py"


# ---------------------------------------------------------------------------
# Os tres campos, DERIVADOS do modulo e nunca escritos a mao no teste
# ---------------------------------------------------------------------------
#
# Cada campo lido leva TRES colunas juntas: o valor, a guarda e o motivo. A
# tabela abaixo e a unica coisa que este arquivo afirma sobre a FORMA das
# colunas, e o teste do invariante confere que ela bate com `COLUNAS` — se um
# quarto campo nascer amanha, a assercao de cobertura cai e alguem tem de vir
# aqui, em vez de o invariante passar a cobrir dois tercos do arquivo em
# silencio.
TRES_COLUNAS_POR_CAMPO = (
    (CAMPO_DO_NIVEL, "nivel", "nivel_escalas", "motivo_do_nivel"),
    (CAMPO_DO_EXP, "exp_decimos", "exp_escalas", "motivo_do_exp"),
    (CAMPO_DA_ADENA, "adena", "adena_glifos", "motivo_da_adena"),
)


def valor_aceito(campo: str):
    """O campo como o leitor de producao o entrega quando ACEITA.

    A GUARDA DO NIVEL E DO EXP E `escalas`; A DA ADENA E `glifos`, e os nomes
    sao diferentes de proposito: a adena e lida por GLIFO e nao tem segunda
    escala com que cruzar, entao um `escalas` ali afirmaria uma guarda que ela
    nao tem — o defeito que o T-01-43 existe para impedir.
    """
    if campo == CAMPO_DA_ADENA:
        return ValorDaAdena(campo=campo, valor=13_160_684, glifos=10, texto="13.160.684")
    if campo == CAMPO_DO_NIVEL:
        return ValorDaRenda(campo=campo, valor=67, escalas=2, texto="67")
    return ValorDaRenda(campo=campo, valor=80_012, escalas=1, texto="8,0012")


def valor_recusado(campo: str) -> RecusaDaRenda:
    """O campo como o leitor de producao o entrega quando RECUSA."""
    return RecusaDaRenda(
        campo=campo, motivo=f"{campo}-vazio", detalhe=f">>><<< ({campo})"
    )


def campos(*, recusados: tuple[str, ...] = (), personagem: str = "Faerlina"):
    """`CamposDaRenda` com os campos nomeados recusados e o resto aceito."""
    escolha = {
        campo: (valor_recusado(campo) if campo in recusados else valor_aceito(campo))
        for campo in (CAMPO_DO_NIVEL, CAMPO_DO_EXP, CAMPO_DA_ADENA)
    }
    return CamposDaRenda(
        personagem=personagem,
        nivel=escolha[CAMPO_DO_NIVEL],
        exp=escolha[CAMPO_DO_EXP],
        adena=escolha[CAMPO_DA_ADENA],
    )


def celula(linha, coluna: str) -> str:
    """A celula da coluna nomeada, com o indice DERIVADO de `COLUNAS`."""
    return linha[COLUNAS.index(coluna)]


def linhas_cruas(arquivo: Path) -> list[list[str]]:
    """As linhas de DADO do arquivo, sem o cabecalho e sem tipagem nenhuma."""
    with arquivo.open("r", encoding="utf-8", newline="") as fonte:
        return list(csv.reader(fonte, delimiter=SEPARADOR))[1:]


def gravar(registro, dados, *, carimbo, descontinuidade=SEM_DESCONTINUIDADE):
    return registro.registrar(dados, carimbo=carimbo, descontinuidade=descontinuidade)


# ---------------------------------------------------------------------------
# TAREFA 1 — as treze colunas, o invariante, e os dois portoes
# ---------------------------------------------------------------------------


class TestOInvarianteDasDuasMetades:
    """Para CADA campo, EXATAMENTE UMA das duas metades esta preenchida."""

    def test_A_TABELA_DOS_TRES_CAMPOS_COBRE_AS_COLUNAS_DO_MODULO(self):
        """CONTROLE da propria tabela: ela e derivada, e nao escrita a mao.

        As nove colunas de campo mais as quatro de moldura (`carimbo`,
        `personagem`, `descontinuidade`, `origem_do_ganho`) sao as treze. Se um
        quarto campo nascer, esta assercao cai antes de o invariante passar a
        cobrir tres quartos do arquivo calado.
        """
        das_colunas = {
            nome
            for _, valor, guarda, motivo in TRES_COLUNAS_POR_CAMPO
            for nome in (valor, guarda, motivo)
        }
        assert das_colunas <= set(COLUNAS)
        assert len(das_colunas) == 9
        assert set(COLUNAS) - das_colunas == {
            "carimbo",
            "personagem",
            "descontinuidade",
            "origem_do_ganho",
        }

    @pytest.mark.parametrize(
        ("campo", "coluna_do_valor", "coluna_da_guarda", "coluna_do_motivo"),
        TRES_COLUNAS_POR_CAMPO,
    )
    def test_ACEITO_TEM_VALOR_E_GUARDA_E_NAO_TEM_MOTIVO(
        self, campo, coluna_do_valor, coluna_da_guarda, coluna_do_motivo
    ):
        linha = campos_da_linha(
            campos(),
            carimbo=0.0,
            descontinuidade=SEM_DESCONTINUIDADE,
            origem_do_ganho=ORIGEM_INDETERMINADA,
        )

        assert celula(linha, coluna_do_valor) != ""
        assert celula(linha, coluna_da_guarda) != "", (
            f"a guarda de `{campo}` esta vazia num campo ACEITO. Ela vai "
            "gravada por causa do LEIT-11: 3 das 4 leituras erradas de nivel "
            "foram aceitas POR CONCORDANCIA das duas escalas, e sem a coluna "
            "ninguem consegue perguntar depois se as erradas eram as de duas "
            "escalas ou as de uma."
        )
        assert celula(linha, coluna_do_motivo) == ""

    @pytest.mark.parametrize(
        ("campo", "coluna_do_valor", "coluna_da_guarda", "coluna_do_motivo"),
        TRES_COLUNAS_POR_CAMPO,
    )
    def test_RECUSADO_TEM_MOTIVO_E_NAO_TEM_VALOR_NEM_GUARDA(
        self, campo, coluna_do_valor, coluna_da_guarda, coluna_do_motivo
    ):
        """A OUTRA direcao do invariante, e ela nao e a mesma assercao virada.

        Um modulo que preenchesse as duas metades passaria no teste do aceito e
        cairia so aqui; um que nao preenchesse nenhuma passaria aqui e cairia
        so la. As duas direcoes juntas sao o invariante.
        """
        linha = campos_da_linha(
            campos(recusados=(campo,)),
            carimbo=0.0,
            descontinuidade=SEM_DESCONTINUIDADE,
            origem_do_ganho=ORIGEM_INDETERMINADA,
        )

        assert celula(linha, coluna_do_motivo) != ""
        assert celula(linha, coluna_do_valor) == ""
        assert celula(linha, coluna_da_guarda) == "", (
            f"`{campo}` recusou e a coluna da guarda tem conteudo. Uma guarda "
            "ao lado de um valor que nao existe e uma guarda afirmada sobre o "
            "nada — o T-01-43 existe para impedir exatamente isso."
        )

    def test_UM_CAMPO_RECUSADO_NAO_APAGA_OS_OUTROS_DOIS(self):
        """Pitfall 3: `ler_a_renda` devolve a PRIMEIRA recusa e esconderia dois.

        `nivel` e o primeiro de `ORDEM_DOS_CAMPOS`, entao uma amostra com EXP e
        adena perfeitos sumiria por causa do campo mais fragil dos tres. E por
        isso que o tipo que atravessa e `CamposDaRenda`, que preserva os tres.
        """
        linha = campos_da_linha(
            campos(recusados=(CAMPO_DO_NIVEL,)),
            carimbo=0.0,
            descontinuidade=SEM_DESCONTINUIDADE,
            origem_do_ganho=ORIGEM_INDETERMINADA,
        )

        assert celula(linha, "motivo_do_nivel") != ""
        assert celula(linha, "exp_decimos") == "80012"
        assert celula(linha, "adena") == "13160684"

    def test_A_LINHA_TEM_EXATAMENTE_TREZE_CELULAS(self):
        linha = campos_da_linha(
            campos(),
            carimbo=0.0,
            descontinuidade=SEM_DESCONTINUIDADE,
            origem_do_ganho=ORIGEM_INDETERMINADA,
        )
        assert len(linha) == len(COLUNAS) == 13


class TestOCarimboEAConversaoUnica:
    """O tempo entra por parametro, e vira `datetime` UMA vez, na saida."""

    def test_O_CARIMBO_SAI_EM_HORA_LOCAL_INGENUA_SEM_FUSO(self):
        from datetime import datetime

        carimbo = 1_756_800_000.0
        linha = campos_da_linha(
            campos(),
            carimbo=carimbo,
            descontinuidade=SEM_DESCONTINUIDADE,
            origem_do_ganho=ORIGEM_INDETERMINADA,
        )

        escrito = celula(linha, "carimbo")
        relido = datetime.fromisoformat(escrito)

        assert relido.tzinfo is None, (
            "o carimbo saiu COM fuso. `Relogio.agora` produz um `datetime` "
            "ingenuo em hora local (`relogio.py:163`), e o resto do projeto le "
            "esse formato — um `+00:00` no fim quebraria a ida e volta."
        )
        assert relido == datetime.fromtimestamp(carimbo)

    def test_UMA_CONVERSAO_DE_EPOCH_NO_MODULO_INTEIRO(self):
        """Portao de arvore: `fromtimestamp` aparece UMA vez, num lugar so.

        A aritmetica da fase e sobre epoch porque a subtracao de dois epochs e
        exata; a conversao mora so na fronteira do disco. Duas conversoes
        seriam dois formatos possiveis para a mesma coluna.
        """
        arvore = ast.parse(FONTE_DO_MODULO.read_text(encoding="utf-8"))
        conversoes = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and getattr(no.func, "attr", "") == "fromtimestamp"
        ]
        assert len(conversoes) == 1

    def test_NENHUMA_CHAMADA_AO_RELOGIO_DA_MAQUINA(self):
        """CTX-10, conferido por ARVORE e nao por texto.

        A docstring idiomatica desta casa DIZ "nenhum `datetime.now()`", entao
        um `grep` acusaria a propria promessa e passaria a nunca poder ser
        escrita. A arvore de sintaxe ve chamada e nao prosa.
        """
        arvore = ast.parse(FONTE_DO_MODULO.read_text(encoding="utf-8"))
        chamados = {
            getattr(no.func, "attr", None) or getattr(no.func, "id", None)
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
        }
        assert sorted(chamados & {"now", "time"}) == []


class TestOsTresEstadosDoCabecalho:
    """Ausente cria, identico carrega, divergente levanta — e so estes tres."""

    def test_AUSENTE_NASCE_COM_O_CABECALHO_E_SEM_AVISO(self, caplog, tmp_path):
        """Primeira execucao numa maquina limpa e estado LEGITIMO, nao erro.

        E o CONTRASTE com o arquivo de zero bytes logo abaixo: la houve uma
        criacao INTERROMPIDA, e por isso ela merece aviso. Aqui nao aconteceu
        nada de anormal.
        """
        with caplog.at_level("WARNING"):
            registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")

        with registro.arquivo.open("r", encoding="utf-8", newline="") as fonte:
            cabecalho = next(csv.reader(fonte, delimiter=SEPARADOR))

        assert tuple(cabecalho) == COLUNAS
        assert caplog.records == []

    def test_ZERO_BYTES_NASCE_COM_O_CABECALHO_E_COM_AVISO(self, caplog, tmp_path):
        """O UNICO caso que nao passa pelo portao, e a razao e que nao ha dado.

        Zero bytes nao tem byte do usuario a preservar: o que aconteceu ali foi
        uma CRIACAO interrompida, e nao uma escrita perdida. Mas ele NAO e igual
        ao arquivo ausente — alguma coisa deu errado —, e por isso o aviso.
        """
        alvo = arquivo_do_personagem(tmp_path, "Faerlina")
        alvo.write_text("", encoding="utf-8")

        with caplog.at_level("WARNING"):
            registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")

        with registro.arquivo.open("r", encoding="utf-8", newline="") as fonte:
            cabecalho = next(csv.reader(fonte, delimiter=SEPARADOR))

        assert tuple(cabecalho) == COLUNAS
        assert any("ZERO BYTES" in linha.getMessage() for linha in caplog.records)

    def test_O_CABECALHO_ESCRITO_E_A_CONSTANTE_DO_MODULO(self, tmp_path):
        """A comparacao e contra `COLUNAS`, e nunca contra um literal.

        Um cabecalho escrito a mao no teste envelheceria em silencio no dia em
        que uma coluna nascesse — e o cabecalho e o CONTRATO com o workstream
        `dashboard`, entao ele e a ultima coisa que pode envelhecer calada.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        with registro.arquivo.open("r", encoding="utf-8", newline="") as fonte:
            cabecalho = next(csv.reader(fonte, delimiter=SEPARADOR))
        assert tuple(cabecalho) == COLUNAS

    def test_IDENTICO_CARREGA(self, tmp_path):
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        gravar(registro, campos(), carimbo=0.0)

        segunda = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        assert len(segunda.carregar()) == 1

    def test_DIVERGENTE_LEVANTA(self, tmp_path):
        alvo = arquivo_do_personagem(tmp_path, "Faerlina")
        alvo.write_text(
            "carimbo;personagem;alguma_coluna_inventada\n", encoding="utf-8"
        )

        with pytest.raises(ContratoDaRendaQuebrado) as erro:
            RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")

        assert "alguma_coluna_inventada" in str(erro.value)

    def test_CONTROLE_O_DIVERGENTE_NAO_ALTERA_UM_BYTE(self, tmp_path):
        """A metade que importa: desligar alto e NAO migrar sao a mesma decisao.

        Migrar sozinho um arquivo que o usuario edita a mao e importa no Sheets
        e como se corrompe dado calado — o append passaria a escrever valores
        nas colunas erradas e o arquivo continuaria abrindo. A comparacao e
        BYTE A BYTE, e nao "o arquivo ainda existe".
        """
        alvo = arquivo_do_personagem(tmp_path, "Faerlina")
        antes = (
            "carimbo;personagem;alguma_coluna_inventada\n"
            "2026-09-02T00:00:00;Faerlina;42\n"
        )
        alvo.write_bytes(antes.encode("utf-8"))

        with pytest.raises(ContratoDaRendaQuebrado):
            RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")

        assert alvo.read_bytes() == antes.encode("utf-8")


class TestOPortaoDoTerminador:
    """Sem quebra de linha no fim, o arquivo INTEIRO e recusado. 5 de 5."""

    def test_SEM_QUEBRA_DE_LINHA_FINAL_LEVANTA(self, tmp_path):
        """Das cinco truncagens medidas, DUAS produzem campos parseaveis.

        `80` vira `8` e `48` vira `4`, e `'8'` e um inteiro perfeitamente
        valido: a contagem de campos nao pega, a validacao por tipo nao pega, e
        so o terminador pega — 5 de 5 (`mercado_registro.py:415-423`).
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        gravar(registro, campos(), carimbo=0.0)

        bruto = registro.arquivo.read_text(encoding="utf-8")
        registro.arquivo.write_text(bruto.rstrip("\r\n"), encoding="utf-8")

        with pytest.raises(ContratoDaRendaQuebrado):
            amostras_do_arquivo(registro.arquivo)

    def test_CONTROLE_O_ARQUIVO_CONTINUA_SEM_A_QUEBRA_DEPOIS_DA_EXCECAO(
        self, tmp_path
    ):
        """Nenhum byte foi consertado, e as duas saidas alternativas dizem por que.

        Truncar a cauda seria o programa apagando bytes do usuario num caminho
        de LEITURA; completar a cauda com uma quebra de linha PROMOVERIA a linha
        possivelmente truncada a dado permanente. As duas foram recusadas.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        gravar(registro, campos(), carimbo=0.0)

        truncado = registro.arquivo.read_text(encoding="utf-8").rstrip("\r\n")
        registro.arquivo.write_text(truncado, encoding="utf-8")
        antes = registro.arquivo.read_bytes()

        with pytest.raises(ContratoDaRendaQuebrado):
            amostras_do_arquivo(registro.arquivo)

        assert registro.arquivo.read_bytes() == antes
        assert not registro.arquivo.read_text(encoding="utf-8").endswith("\n")

    def test_A_MENSAGEM_MOSTRA_A_CAUDA_CRUA_E_DIZ_O_QUE_CONTINUA_FUNCIONANDO(
        self, tmp_path
    ):
        """A mensagem e a unica coisa que religa o registro. Ela tem tres partes.

        O que aconteceu, o que fazer, e o que continua funcionando enquanto
        isso — porque o usuario que le "REGISTRO DESLIGADO" as 2h da manha
        precisa saber que os alertas de morte da party seguem sendo entregues.
        """
        alvo = tmp_path / "faerlina.csv"
        alvo.write_text(
            SEPARADOR.join(COLUNAS) + "\n2026-09-02T00:00:00;Faerlina;6",
            encoding="utf-8",
        )

        with pytest.raises(ContratoDaRendaQuebrado) as erro:
            amostras_do_arquivo(alvo)

        mensagem = str(erro.value)
        assert "2026-09-02T00:00:00;Faerlina;6" in mensagem
        assert "nenhum byte foi" in mensagem.lower()
        assert "ressurreicao" in mensagem


class TestUmaLinhaRuimNaoEUmArquivoRuim:
    """D-14: linha ruim cai sozinha com aviso; arquivo ruim e recusado inteiro."""

    def test_UMA_LINHA_COM_NUMERO_DE_CAMPOS_ERRADO_CAI_SOZINHA(
        self, caplog, tmp_path
    ):
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        gravar(registro, campos(), carimbo=0.0)
        with registro.arquivo.open("a", encoding="utf-8", newline="") as destino:
            destino.write("so;tres;campos\n")
        gravar(registro, campos(), carimbo=30.0)

        with caplog.at_level("WARNING"):
            lidas = amostras_do_arquivo(registro.arquivo)

        assert len(lidas) == 2, (
            "a linha ruim derrubou o arquivo inteiro. Ela cai sozinha e as "
            "outras carregam — arquivo INTEIRO recusado e outra coisa, e tem "
            "excecao propria."
        )
        avisos = [linha.getMessage() for linha in caplog.records]
        assert any("linha 3" in aviso for aviso in avisos)
        assert any("3 campos" in aviso for aviso in avisos)

    def test_UMA_CELULA_COM_LIXO_ONDE_DEVERIA_HAVER_INTEIRO_CAI_SOZINHA(
        self, caplog, tmp_path
    ):
        """Vazio e estado LEGITIMO (o campo recusou); lixo e linha ruim."""
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        gravar(registro, campos(), carimbo=0.0)
        podre = list(linhas_cruas(registro.arquivo)[0])
        podre[COLUNAS.index("nivel")] = "sessenta e sete"
        with registro.arquivo.open("a", encoding="utf-8", newline="") as destino:
            csv.writer(destino, delimiter=SEPARADOR).writerow(podre)

        with caplog.at_level("WARNING"):
            lidas = amostras_do_arquivo(registro.arquivo)

        assert len(lidas) == 1
        assert any("linha 3" in linha.getMessage() for linha in caplog.records)
