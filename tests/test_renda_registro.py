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

from l2scanner.loot import apelido
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
    amostras_ao_vivo,
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


# ---------------------------------------------------------------------------
# TAREFA 2 — o append, um arquivo por personagem, e a dedup que NAO atravessou
# ---------------------------------------------------------------------------


class TestADedupQueNaoAtravessou:
    """C-3, T-02-16: o portao COMPORTAMENTAL, em duas escalas."""

    def test_DUAS_AMOSTRAS_IDENTICAS_DEIXAM_DUAS_LINHAS(self, tmp_path):
        """A escala que pega uma dedup por IDENTIDADE de linha.

        `mercado_registro.chave_da_observacao` exclui o carimbo de proposito,
        para o arquivo do mercado nao crescer uma linha por segundo sobre o
        mesmo anuncio. Aqui uma linha por tique E O PRODUTO: ela e o
        denominador da taxa.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        for carimbo in (0.0, 30.0):
            gravar(registro, campos(), carimbo=carimbo)

        assert len(linhas_cruas(registro.arquivo)) == 2

    def test_CEM_AMOSTRAS_IDENTICAS_DEIXAM_CEM_LINHAS(self, tmp_path):
        """A escala que pega uma dedup POR JANELA, que a de duas nao pegaria.

        Uma dedup "no maximo uma linha por minuto" ou "so grava quando mudou
        desde a ultima" passaria no teste de duas amostras espacadas de 30 s e
        cairia aqui. Cem amostras a ~1 Hz com os tres campos identicos e o caso
        REAL do personagem parado — a adena so muda quando cai loot — e sao
        exatamente as linhas que a taxa da noite conta.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        for tique in range(100):
            gravar(registro, campos(), carimbo=float(tique))

        linhas = linhas_cruas(registro.arquivo)
        assert len(linhas) == 100, (
            "cem amostras identicas com carimbos diferentes deixaram "
            f"{len(linhas)} linhas e nao cem. Alguma forma de dedup atravessou "
            "do mercado, e ela apagaria a MAIORIA das amostras de uma noite de "
            "farm — o denominador da taxa sumiria sem nenhuma mensagem."
        )
        assert len({celula(linha, "carimbo") for linha in linhas}) == 100

    def test_NENHUM_CONJUNTO_NASCE_NO_CONSTRUTOR(self):
        """O portao de ARVORE ao lado do comportamental, e ele pega outra coisa.

        O comportamental pega a dedup ATIVA; este pega o indice sendo montado
        antes de alguem chegar a usa-lo. `RegistroDaRenda` e classe comum e nao
        `dataclass` precisamente para que esta varredura veja codigo de verdade
        em vez do `__init__` vazio que um `dataclass` nao escreve no fonte.
        """
        arvore = ast.parse(FONTE_DO_MODULO.read_text(encoding="utf-8"))
        conjuntos = [
            tipo.__class__.__name__
            for no in ast.walk(arvore)
            if isinstance(no, ast.FunctionDef) and no.name == "__init__"
            for tipo in ast.walk(no)
            if isinstance(tipo, (ast.Set, ast.SetComp))
        ]
        assert conjuntos == []


class TestAsRecusasTambemSaoGravadas:
    """CTX-9, T-02-20: a taxa de RECUSA e dado, e nao ruido."""

    def test_UMA_AMOSTRA_COM_OS_TRES_CAMPOS_RECUSADOS_VIRA_LINHA(self, tmp_path):
        """Um arquivo so com sucessos nao permite auditar a taxa de recusa.

        Sem estas linhas ninguem consegue responder "por que a taxa desta hora
        tem n=12 se o scanner rodou quarenta minutos". A alternativa registrada
        — gravar so as aceitas, arquivo menor e mais limpo — perde exatamente
        essa auditoria, e por isso foi recusada.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        gravar(
            registro,
            campos(recusados=(CAMPO_DO_NIVEL, CAMPO_DO_EXP, CAMPO_DA_ADENA)),
            carimbo=0.0,
        )

        linhas = linhas_cruas(registro.arquivo)
        assert len(linhas) == 1

        (linha,) = linhas
        for _, valor, guarda, motivo in TRES_COLUNAS_POR_CAMPO:
            assert celula(linha, motivo) != ""
            assert celula(linha, valor) == ""
            assert celula(linha, guarda) == ""

    def test_A_LINHA_DE_RECUSA_VOLTA_TIPADA_COM_VALOR_NULO_E_MOTIVO_CHEIO(
        self, tmp_path
    ):
        """A ida e a volta: ausencia de valor e presenca de motivo sao o mesmo fato."""
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        gravar(registro, campos(recusados=(CAMPO_DO_NIVEL,)), carimbo=0.0)

        (amostra,) = amostras_do_arquivo(registro.arquivo)

        assert amostra.nivel is None
        assert amostra.nivel_escalas is None
        assert amostra.motivo_do_nivel == "nivel-vazio"
        assert amostra.exp_decimos == 80_012
        assert amostra.adena == 13_160_684


class TestUmArquivoPorPersonagem:
    """C-5, REG-04, T-02-03: um escritor por arquivo, porque sao duas instancias."""

    def test_DOIS_PERSONAGENS_DOIS_ARQUIVOS_E_NENHUMA_LINHA_ATRAVESSA(
        self, tmp_path
    ):
        """E a coluna concorda com o nome do arquivo, linha a linha.

        Nao sao duas verdades: a COLUNA e o dado que o consumidor le, e o NOME
        DO ARQUIVO e o roteamento que garante um escritor so. Um arquivo
        renomeado a mao continua dizendo de quem ele e.
        """
        for personagem in ("Faerlina", "J4guar"):
            registro = RegistroDaRenda(pasta=tmp_path, personagem=personagem)
            for carimbo in (0.0, 30.0):
                gravar(registro, campos(personagem=personagem), carimbo=carimbo)

        arquivos = sorted(caminho.name for caminho in tmp_path.glob("*.csv"))
        assert arquivos == ["faerlina.csv", "j4guar.csv"]

        for caminho in tmp_path.glob("*.csv"):
            linhas = linhas_cruas(caminho)
            assert len(linhas) == 2
            donos = {celula(linha, "personagem") for linha in linhas}
            assert len(donos) == 1
            (dono,) = donos
            assert apelido(dono) == caminho.stem, (
                f"a coluna `personagem` diz {dono!r} num arquivo chamado "
                f"{caminho.name!r}. A adena de uma instancia entraria na conta "
                "do EXP da outra."
            )

    @pytest.mark.parametrize(
        "hostil",
        [
            "../../Windows/System32",
            "..\\..\\..\\etc\\passwd",
            "C:nome:com:dois-pontos",
        ],
    )
    def test_UM_NOME_HOSTIL_NAO_SAI_DA_PASTA(self, hostil, tmp_path):
        """T-02-17: o nome vem do TITULO DA JANELA do jogo e vira caminho.

        `apelido()` reduz por lista de PERMISSAO (`[^a-z0-9]+` -> `-`), e nao
        por lista de proibicao: nao ha caractere de travessia que sobreviva a
        isso, porque a lista diz o que PASSA em vez de tentar enumerar o que
        nao passa. A comparacao aqui e por `Path.resolve()` contra a pasta
        resolvida, e nunca por inspecao de texto — um teste que so procurasse
        `".."` no nome passaria com um `%2e%2e` ou com um separador exotico.
        """
        alvo = arquivo_do_personagem(tmp_path, hostil).resolve()
        assert alvo.parent == tmp_path.resolve()
        assert tmp_path.resolve() in alvo.parents


class TestAOrigemDoGanho:
    """REND-04, CTX-7: marcador explicito, nunca heuristica."""

    def test_TODA_LINHA_DIZ_INDETERMINADO_INCLUSIVE_AS_DE_RECUSA(self, tmp_path):
        """A coluna existe, sai `indeterminado`, e ninguem a infere por limiar.

        O roadmap ofereceu tres caminhos e os dois primeiros — a forma do salto
        e o painel do mercado estar aberto — sao inferencia por limiar magico
        sobre um dado que o consumidor nao pode auditar. D-02 vale inteiro: um
        numero exibido tem de ter existido. Uma coluna `indeterminado` que o
        `dashboard` mostra como indeterminado e melhor que um balde errado com
        cara de certo.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        gravar(registro, campos(), carimbo=0.0)
        gravar(
            registro,
            campos(recusados=(CAMPO_DO_NIVEL, CAMPO_DO_EXP, CAMPO_DA_ADENA)),
            carimbo=30.0,
        )

        linhas = linhas_cruas(registro.arquivo)
        assert len(linhas) == 2
        for linha in linhas:
            assert celula(linha, "origem_do_ganho") == ORIGEM_INDETERMINADA

    def test_NENHUM_LIMIAR_DECIDE_A_ORIGEM_DENTRO_DE_CAMPOS_DA_LINHA(self):
        """O portao e ESCOPADO A FUNCAO que decide o valor, e o referente e ZERO.

        A versao anterior deste portao contava as comparacoes do ARQUIVO
        INTEIRO e mandava afirmar que o numero "nao cresceu por causa da
        origem". Nao existe referente para "nao cresceu": este modulo NASCE no
        `02-01` e EXPANDE aqui, entao qualquer numero medido seria carimbado
        como linha de base sem ninguem saber contra o que — e um portao cujo
        valor esperado o proprio executor escolhe nao e portao.

        O escopo por funcao tem referente ABSOLUTO — zero — e diz a mesma coisa
        com mais forca: a origem nao pode sair de limiar porque no lugar onde
        ela e decidida nao ha limiar nenhum. `is`, `==` e `!=` continuam
        legitimos ali; o que o portao olha e comparacao de ORDEM.
        """
        arvore = ast.parse(FONTE_DO_MODULO.read_text(encoding="utf-8"))
        funcoes = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.FunctionDef) and no.name == "campos_da_linha"
        ]
        assert len(funcoes) == 1, (
            "`campos_da_linha` tem de existir e ser UMA so: o portao e escopado "
            "a ela pelo nome, e duas definicoes fariam a varredura olhar uma "
            "delas e passar."
        )
        ordens = sorted(
            {
                type(operador).__name__
                for funcao in funcoes
                for comparacao in ast.walk(funcao)
                if isinstance(comparacao, ast.Compare)
                for operador in comparacao.ops
                if isinstance(operador, (ast.Gt, ast.Lt, ast.GtE, ast.LtE))
            }
        )
        assert ordens == []


class TestOAppendEAFalhaDeDisco:
    """T-02-19: a feature desliga, e o PRODUTO nunca."""

    def test_O_ARQUIVO_TERMINA_EM_QUEBRA_DE_LINHA_DEPOIS_DE_CADA_GRAVACAO(
        self, tmp_path
    ):
        """A bicondicional do portao do terminador, do lado do ESCRITOR.

        `csv.writer.writerow` emite UMA unica chamada de escrita contendo a
        linha E o terminador, e o `flush` vem logo atras: um registro esta
        completo se e somente se o arquivo termina em quebra de linha.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        for tique in range(5):
            gravar(registro, campos(), carimbo=float(tique))
            assert registro.arquivo.read_text(encoding="utf-8").endswith("\n")

    def test_UMA_SEGUNDA_SESSAO_APENDA_NO_FIM_E_NAO_REESCREVE(self, tmp_path):
        """Criterio 4 do roadmap, na metade que e do disco (REG-02).

        Reiniciar o scanner nao inventa nem apaga renda: as linhas de antes
        continuam la, NA ORDEM, e as novas vao para o fim. A outra metade — a
        primeira amostra pos-reinicio ser ANCORA e nao delta — e da conta, e
        esta presa no tracer.
        """
        primeira = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        for carimbo in (0.0, 30.0):
            gravar(primeira, campos(), carimbo=carimbo)
        antes = [celula(linha, "carimbo") for linha in linhas_cruas(primeira.arquivo)]

        segunda = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        gravar(segunda, campos(), carimbo=60.0)

        depois = [celula(linha, "carimbo") for linha in linhas_cruas(segunda.arquivo)]
        assert depois[: len(antes)] == antes
        assert len(depois) == 3

    def test_FALHA_DE_ESCRITA_DESLIGA_A_SESSAO_INTEIRA_SEM_NOVA_TENTATIVA(
        self, monkeypatch, tmp_path
    ):
        """Definitivo para a sessao: um retry por tique a 1 Hz enche o log.

        E a gravacao seguinte NAO TOCA O DISCO — a assercao e sobre os BYTES do
        arquivo depois de o substituto ser removido, e nao sobre o valor de
        retorno: um desligamento que ainda abrisse o arquivo a cada tique
        manteria uma alca sobre o CSV que o usuario quer abrir no Sheets.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        gravar(registro, campos(), carimbo=0.0)
        assinatura_de_antes = registro.arquivo.read_bytes()

        original = Path.open

        def open_que_recusa(self, *args, **kwargs):
            if self == registro.arquivo and args and "a" in args[0]:
                raise PermissionError(13, "disco cheio de mentira")
            return original(self, *args, **kwargs)

        monkeypatch.setattr(Path, "open", open_que_recusa)
        assert gravar(registro, campos(), carimbo=30.0) is False
        assert registro.ligado is False

        # E agora SEM o substituto: o disco "voltou", e o registro continua
        # desligado. Quem religa e o proximo arranque, e nao o proximo tique.
        monkeypatch.undo()
        assert gravar(registro, campos(), carimbo=60.0) is False
        assert registro.arquivo.read_bytes() == assinatura_de_antes, (
            "a gravacao seguinte ao desligamento tocou o disco. O desligamento "
            "e DEFINITIVO para a sessao e sem nova tentativa."
        )

    def test_A_MENSAGEM_DO_DESLIGAMENTO_DIZ_QUE_OS_ALERTAS_CONTINUAM(
        self, caplog, monkeypatch, tmp_path
    ):
        """O desligamento e da FEATURE e nunca do PRODUTO.

        Se o registro da renda cai, a morte, a saida e a ressurreicao da party
        continuam sendo detectadas e entregues — e o usuario tem de ler isso na
        mesma mensagem que diz que a renda parou.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        original = Path.open

        def open_que_recusa(self, *args, **kwargs):
            if self == registro.arquivo and args and "a" in args[0]:
                raise PermissionError(13, "disco cheio de mentira")
            return original(self, *args, **kwargs)

        monkeypatch.setattr(Path, "open", open_que_recusa)
        with caplog.at_level("ERROR"):
            gravar(registro, campos(), carimbo=0.0)

        registrado = " ".join(linha.getMessage() for linha in caplog.records)
        assert "REGISTRO DE RENDA DESLIGADO" in registrado
        assert "ressurreicao" in registrado

    def test_CONTROLE_O_APPEND_NAO_CAPTURA_O_QUE_NAO_E_ERRO_DE_SISTEMA(
        self, monkeypatch, tmp_path
    ):
        """`except OSError` E SO, e nunca `except Exception`.

        Um `except Exception` esconderia um `AttributeError` de refatoracao
        como se fosse disco cheio — e o usuario leria "REGISTRO DESLIGADO,
        conserte o arquivo ou a pasta" para um defeito que nao esta nem no
        arquivo nem na pasta dele.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")

        def campos_que_explodem(*args, **kwargs):
            raise AttributeError("um refactor quebrou alguma coisa aqui dentro")

        monkeypatch.setattr(
            "l2scanner.renda_registro.campos_da_linha", campos_que_explodem
        )
        with pytest.raises(AttributeError):
            gravar(registro, campos(), carimbo=0.0)

        assert registro.ligado is True


# ---------------------------------------------------------------------------
# TAREFA 3 — o leitor tolerante, e a refutacao da C-2 presa por teste
# ---------------------------------------------------------------------------


class TestARefutacaoDaC2:
    """"O dashboard acrescenta uma lista de colunas, nao um parser" e FALSO."""

    def test_O_PARSER_DO_MERCADO_APONTADO_PARA_UM_CSV_DE_RENDA_LEVANTA(
        self, tmp_path
    ):
        """A refutacao EXECUTAVEL, e ela e o ponto inteiro desta classe.

        Uma refutacao escrita so em comentario envelhece em silencio. Esta
        aponta o parser do mercado para um `.renda/` REAL, escrito pelo escritor
        desta fase, e afirma que ele levanta a excecao DO MERCADO — porque
        `mercado_registro.observacoes_do_arquivo` confere o cabecalho contra o
        `COLUNAS` GLOBAL daquele modulo (`mercado_registro.py:495`), e
        `dashboard_dados.observacoes_ao_vivo:454` o chama POR NOME, sem ponto de
        injecao nenhum.

        Se um dia alguem parametrizar o cabecalho do mercado, ESTE TESTE CAI — e
        entao a prosa do fonte e reescrita, em vez de continuar mentindo por
        anos.
        """
        from l2scanner import mercado_registro

        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        gravar(registro, campos(), carimbo=0.0)

        with pytest.raises(mercado_registro.ContratoDoArquivoQuebrado):
            mercado_registro.observacoes_do_arquivo(registro.arquivo)

        assert False is False, (
            "se esta linha for alcancada o teste ja passou; a mensagem util "
            "esta na docstring. As duas frases refutadas sao `ROADMAP.md:290` "
            "e `REQUIREMENTS.md:284`."
        )

    def test_A_EXCECAO_DA_RENDA_E_PROPRIA_E_NAO_HERDA_A_DO_MERCADO(self):
        """Herdar acoplaria dois workstreams numa hierarquia de excecao.

        Quem capturasse a do mercado passaria a capturar a da renda sem ter
        pedido. O contrato entre os dois e um arquivo em disco, e mais nada.
        """
        from l2scanner import mercado_registro

        assert ContratoDaRendaQuebrado is not mercado_registro.ContratoDoArquivoQuebrado
        assert not issubclass(
            ContratoDaRendaQuebrado, mercado_registro.ContratoDoArquivoQuebrado
        )

    def test_A_REFUTACAO_ESTA_ESCRITA_NO_FONTE_COM_OS_ENDERECOS(self):
        """A prosa e o teste dizem a MESMA coisa, e por isso os dois tem de existir.

        O teste acima prova que o parser levanta; ele nao prova que alguem que
        abra o arquivo daqui a um ano vai entender POR QUE. A cadeia de quatro
        passos, com endereco em cada um, e o que faz a proxima pessoa nao
        refazer a medicao — e as duas frases refutadas vao citadas pelo numero
        da linha para que a correcao delas seja localizavel.
        """
        fonte = FONTE_DO_MODULO.read_text(encoding="utf-8")

        assert fonte.count("lista de colunas") >= 1
        for endereco in (
            "ROADMAP.md:290",
            "REQUIREMENTS.md:284",
            "dashboard_dados.py:454",
            "mercado_registro.py:495",
        ):
            assert endereco in fonte, (
                f"a refutacao da C-2 nao cita `{endereco}`. Uma refutacao sem "
                "endereco obriga a proxima pessoa a refazer a medicao inteira "
                "para descobrir se ela ainda vale."
            )

    def test_A_CADEIA_DOS_QUATRO_PASSOS_ESTA_NO_FONTE(self):
        """Os quatro passos, e nao so a conclusao.

        1. `observacoes_ao_vivo` chama o parser do mercado POR NOME.
        2. Aquele parser confere o cabecalho contra o `COLUNAS` GLOBAL.
        3. O laco de tipagem monta `ObservacaoLida` — mercado puro.
        4. Acima disso o `payload` e modelo de mercado, cambio e cinco estados.

        Sem os quatro, "e falso" e uma afirmacao sem argumento, e a proxima
        pessoa a ler nao consegue conferir nenhum dos passos.
        """
        fonte = FONTE_DO_MODULO.read_text(encoding="utf-8")

        for marca in (
            "observacoes_ao_vivo",
            "COLUNAS",
            "ObservacaoLida",
            "ModeloDeMercado",
        ):
            assert marca in fonte, (
                f"o passo que cita `{marca}` sumiu da cadeia da C-2. Os quatro "
                "passos juntos sao o argumento; tres deles sao uma opiniao."
            )


class TestONaoImportarDoDashboard:
    """350 modulos com `cv2` e `numpy` para pegar seis linhas de corte."""

    def test_NENHUM_IMPORT_DE_DASHBOARD_CONFERIDO_POR_ARVORE(self):
        """Por ARVORE e nao por texto, e a razao e a refutacao logo acima.

        Este fonte TEM de citar `dashboard_dados.py:454` para explicar a C-2.
        Um portao de `grep` acusaria a propria refutacao e se contradiria com o
        criterio que a exige — a arvore de sintaxe ve import e nao prosa.
        """
        arvore = ast.parse(FONTE_DO_MODULO.read_text(encoding="utf-8"))
        modulos: list[str] = []
        for no in ast.walk(arvore):
            if isinstance(no, (ast.Import, ast.ImportFrom)):
                modulos.append(getattr(no, "module", None) or "")
                modulos.extend(alias.name for alias in no.names)

        assert [nome for nome in modulos if "dashboard" in nome] == []

    def test_IMPORTAR_O_MODULO_NAO_TRAZ_CV2_NEM_NUMPY(self):
        """O corte de cadeia do `raiz.py`, medido do lado de fora.

        Um import de `dashboard_dados` no topo custaria `mercado_console` ->
        `console` -> `rastreador` -> `visao` -> `cv2`, e a copia de seis linhas
        e mais barata que isso.
        """
        import subprocess
        import sys

        codigo = (
            "import sys; sys.path.insert(0, '.');"
            "import l2scanner.renda_registro;"
            "carregados = set(sys.modules);"
            "print('cv2' in carregados, 'numpy' in carregados,"
            " 'l2scanner.dashboard_dados' in carregados)"
        )
        saida = subprocess.run(
            [sys.executable, "-c", codigo],
            capture_output=True,
            text=True,
            cwd=str(FONTE_DO_MODULO.parents[1]),
        )
        assert saida.stdout.strip() == "False False False", saida.stderr


class TestOLeitorTolerante:
    """O corte na ultima linha completa, e os dois portoes DEPOIS dele."""

    def test_UM_ARQUIVO_COMPLETO_E_LIDO_INTEIRO(self, tmp_path):
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        for carimbo in (0.0, 30.0, 60.0):
            gravar(registro, campos(), carimbo=carimbo)

        relido = amostras_ao_vivo(registro.arquivo)

        assert len(relido.amostras) == 3
        assert relido.cauda_incompleta is False

    def test_A_CONTAGEM_DE_LINHAS_COMPLETAS_EXCLUI_O_CABECALHO(self, tmp_path):
        """Tres gravacoes sao TRES linhas completas, e nunca quatro.

        E o arquivo so com cabecalho e ZERO, e nao `-1`: a subtracao acontece so
        quando ha o que subtrair, e nao dentro de um `max` que absorveria o
        sinal de um defeito de verdade.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        assert amostras_ao_vivo(registro.arquivo).linhas_completas == 0

        for carimbo in (0.0, 30.0, 60.0):
            gravar(registro, campos(), carimbo=carimbo)

        assert amostras_ao_vivo(registro.arquivo).linhas_completas == 3

    def test_UMA_CAUDA_PARCIAL_DEVOLVE_AS_COMPLETAS_E_SINALIZA_SEM_LEVANTAR(
        self, tmp_path
    ):
        """A degradacao e REDE DE SEGURANCA, e nao o caminho normal.

        Medido no `dashboard_dados`: ZERO leituras sem terminador em 22.970
        sondagens durante 200.000 appends concorrentes — e o zero e resultado, e
        nao cegueira da sonda, porque um controle positivo que escrevia a linha
        em DUAS chamadas acusou 3.252 de 4.079.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        for carimbo in (0.0, 30.0):
            gravar(registro, campos(), carimbo=carimbo)
        with registro.arquivo.open("a", encoding="utf-8", newline="") as destino:
            destino.write("2026-09-02T00:01:00;Faerlina;67;2;;80")

        relido = amostras_ao_vivo(registro.arquivo)

        assert len(relido.amostras) == 2
        assert relido.linhas_completas == 2
        assert relido.cauda_incompleta is True

    def test_CONTROLE_UM_ARQUIVO_SEM_NENHUMA_QUEBRA_DE_LINHA_NAO_INVENTA_LINHA(
        self, tmp_path
    ):
        """Sem uma linha completa nao ha nem cabecalho: nao e este arquivo.

        A DIVERGENCIA com `dashboard_dados.observacoes_ao_vivo` e deliberada e
        esta escrita no fonte: la quem le e um painel de so-leitura que tem de
        degradar para nao ficar mudo; aqui o mesmo arquivo e do ESCRITOR, e
        apendar num arquivo cujo estado o programa nao consegue afirmar
        produziria a linha parseavel e ERRADA que a fase existe para nao ter. O
        que este CONTROLE prende e que NENHUMA amostra e inventada.
        """
        alvo = tmp_path / "faerlina.csv"
        alvo.write_text("lixo sem quebra de linha nenhuma", encoding="utf-8")

        with pytest.raises(ContratoDaRendaQuebrado) as erro:
            amostras_ao_vivo(alvo)

        assert "quebra de linha" in str(erro.value)

    def test_O_PORTAO_DO_CABECALHO_CONTINUA_DESLIGANDO_ALTO_NA_ROTA_AO_VIVO(
        self, tmp_path
    ):
        """O corte acontece ANTES do portao, e e por isso que o portao existe.

        A tentacao de "pular os portoes na leitura ao vivo, que e so um
        preview" e exatamente o que o `dashboard` recusou e mediu. Um cabecalho
        divergente COM cauda parcial — o caso em que a tentacao seria mais forte
        — continua levantando, e nao devolve linha nenhuma.
        """
        alvo = tmp_path / "faerlina.csv"
        alvo.write_text(
            "carimbo;personagem;alguma_coluna_inventada\n"
            "2026-09-02T00:00:00;Faerlina;42\n"
            "2026-09-02T00:00:30;Faerl",
            encoding="utf-8",
        )

        with pytest.raises(ContratoDaRendaQuebrado) as erro:
            amostras_ao_vivo(alvo)

        assert "alguma_coluna_inventada" in str(erro.value)

    def test_A_MENSAGEM_NOMEIA_O_ARQUIVO_REAL_E_NAO_O_TEXTO_RECORTADO(
        self, tmp_path
    ):
        """A armadilha que o `dashboard` documentou em `:271-274`.

        O adaptador entrega o TEXTO cortado no `open()` e o CAMINHO REAL no
        `__str__`, precisamente para que a mensagem continue nomeando um arquivo
        que o usuario consegue abrir. Uma mensagem que dissesse `<StringIO>`
        seria inutil as 2h da manha.
        """
        alvo = tmp_path / "faerlina.csv"
        alvo.write_text(
            "carimbo;personagem;alguma_coluna_inventada\n"
            "2026-09-02T00:00:00;Faerlina;42\n",
            encoding="utf-8",
        )

        with pytest.raises(ContratoDaRendaQuebrado) as erro:
            amostras_ao_vivo(alvo)

        mensagem = str(erro.value)
        assert "faerlina.csv" in mensagem
        assert "StringIO" not in mensagem

    def test_A_ROTA_DO_RECORTE_E_A_CHAMADA_DIRETA_DAO_O_MESMO_RESULTADO(
        self, tmp_path
    ):
        """O ANTIDOTO do acoplamento de FORMA, e ele vai escrito junto.

        `ArquivoRecortado` implementa `open`, `__str__` e `__fspath__` porque e
        o que `amostras_do_arquivo` usa HOJE; se ela passar a chamar `.stat()`
        ou `.exists()`, o adaptador quebra com `AttributeError`. Este teste de
        equivalencia sobre um arquivo COMPLETO e o que faz essa quebra aparecer
        na suite em vez de aparecer no farm do usuario.
        """
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        for carimbo in (0.0, 30.0, 60.0):
            gravar(registro, campos(), carimbo=carimbo)

        pela_rota = list(amostras_ao_vivo(registro.arquivo).amostras)
        direto = amostras_do_arquivo(registro.arquivo)

        assert pela_rota == direto

    def test_UM_ARQUIVO_AUSENTE_DIZ_AUSENTE_EM_VEZ_DE_EXPLODIR(self, tmp_path):
        """A `.renda/` nasce vazia, e quem le tem de dizer "sem evidencia"."""
        relido = amostras_ao_vivo(tmp_path / "nunca-existiu.csv")

        assert relido.arquivo_ausente is True
        assert relido.amostras == ()
        assert relido.linhas_completas == 0
