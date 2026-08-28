"""O .bat da ponte nao pode mexer no ambiente do scanner, e o roteiro nao pode mentir.

Dois riscos moram aqui, e nenhum dos dois aparece lendo o codigo Python.

O PRIMEIRO e o instalador. O `vigiar-party.bat` termina a sonda de dependencias
dele com um `pip install -r requirements.txt` sobre o `.venv` COMPARTILHADO, e
os pinos daquele arquivo sao abertos de proposito (`mss>=10.2.0`, `numpy>=2.0`,
`windows-capture>=1.4`). Copiar esse final para o `.bat` da ponte significaria
que dois cliques nele COM O SCANNER FARMANDO rodariam o instalador contra um
ambiente onde `cv2.pyd` e as DLLs do `numpy` estao CARREGADAS - falha de arquivo
travado, ou pior, um upgrade silencioso da pilha numerica no meio do farm. Seria
o criterio 1 da fase quebrado ao pe da letra: "nenhum dos dois sente o outro
subir ou cair". So o `vigiar-party.bat` monta o ambiente; este confere e recusa.

O SEGUNDO e a armadilha de mencao do roteiro. Uma mensagem que MENCIONA o bot
chega com o texto preenchido mesmo com a intent MESSAGE CONTENT desligada, entao
um teste com arroba da verde sem provar nada. O aviso e a diferenca entre um
portao humano PROVADO e um portao humano ENCENADO, e por isso ele tem teste: um
aviso sem teste some na primeira reescrita do arquivo.
"""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BAT = RAIZ / "ponte-discord.bat"
ROTEIRO = RAIZ / "PORTAO-DISCORD.txt"

CHAMADA = "l2scanner.ponte_discord"

# Os nomes que NAO podem aparecer numa linha executavel do .bat. Sao os dois
# lados da mesma proibicao: o instalador e o arquivo que ele leria.
NOMES_DO_INSTALADOR = ("pip", "requirements.txt")


def _bat() -> str:
    # cp1252 e o que o `test_calibrar_mercado_bat.py` usa, e o arquivo e ASCII
    # puro de proposito (ver `test_o_bat_e_ascii_puro`), entao a leitura da o
    # mesmo resultado em qualquer um dos dois encodings da raiz.
    return BAT.read_text(encoding="cp1252")


def _roteiro() -> str:
    return ROTEIRO.read_text(encoding="cp1252")


def _linhas_executaveis(texto: str) -> list[str]:
    """As linhas que o cmd EXECUTA. Comentario `REM` nao conta.

    Descartar os `REM` antes de varrer nao e detalhe: o comentario que EXPLICA
    por que o instalador nao pode estar ali contem as mesmas palavras que a
    asercao procura. Um teste que fica vermelho por causa da propria
    justificativa e um teste que alguem apaga - e e o mesmo cuidado que o
    `test_calibrar_mercado_bat.py` toma ao exigir que a frase venha de um
    `echo` e nao de um `REM`.
    """
    linhas = []
    for bruta in texto.splitlines():
        despida = bruta.strip()
        if not despida or despida.lower().startswith("rem"):
            continue
        linhas.append(despida)
    return linhas


class TestOsArquivosExistem:
    def test_o_bat_da_ponte_existe(self):
        """Sem ele o usuario teria que abrir um cmd e digitar `-m`. OPER-01."""
        assert BAT.is_file(), "ponte-discord.bat sumiu"

    def test_o_roteiro_do_portao_humano_existe(self):
        """Os 4 passos so o usuario pode dar; sem o roteiro ele nao sabe quais."""
        assert ROTEIRO.is_file(), "PORTAO-DISCORD.txt sumiu"

    def test_o_bat_e_ascii_puro(self):
        """A raiz tem .bat em cp1252 E em utf-8 misturados - medido.

        `calibrar-mercado.bat` e cp1252; `avisos-tvt.bat` e `vigiar-party.bat`
        sao utf-8. Um travessao neste arquivo apareceria certo para um leitor e
        quebrado para o outro. ASCII puro decodifica igual nos dois, e e a
        unica forma de o teste ler o mesmo que o cmd executa.
        """
        cru = BAT.read_bytes()

        fora_do_ascii = [b for b in cru if b > 127]

        assert not fora_do_ascii, (
            f"{len(fora_do_ascii)} bytes fora do ASCII no .bat: dependendo do "
            f"editor ou do console eles viram caractere quebrado"
        )


class TestAFormaDaCasa:
    def test_o_bat_vai_para_a_pasta_dele_antes_de_qualquer_coisa(self):
        """Dois cliques podem vir de um atalho com outro diretorio atual.

        Sem o `cd /d`, o `.venv` e o `config.toml` sao procurados na pasta
        errada e o usuario le "ambiente nao preparado" com o ambiente pronto.
        """
        assert 'cd /d "%~dp0"' in _bat()

    def test_o_bat_chama_o_python_do_venv_por_caminho_literal(self):
        """Sem `activate` e sem `uv`, como todos os .bat da raiz.

        `activate` num duplo clique e o passo que o usuario esquece; o caminho
        literal entre aspas nao tem como ser esquecido.
        """
        texto = _bat()

        assert f'".venv\\Scripts\\python.exe" -m {CHAMADA}' in texto

    def test_o_bat_repassa_os_argumentos(self):
        """Sem `%*`, um `--conferir` do 01-02 seria engolido calado."""
        chamada = _bat().find(CHAMADA)
        fim_da_linha = _bat().find("\n", chamada)

        assert "%*" in _bat()[chamada:fim_da_linha]

    def test_o_bat_termina_em_pause(self):
        """Dois cliques sem `pause` fecham a janela antes de o erro ser lido."""
        executaveis = _linhas_executaveis(_bat())

        assert executaveis[-1].lower() == "pause"

    def test_o_bat_se_despede_depois_da_chamada_do_python(self):
        """Ha relato de um RuntimeError cosmetico do Proactor no Ctrl+C.

        Ele aparece DEPOIS de o processo ja ter saido limpo. Para quem nao
        programa, um traceback e "quebrou". A linha de despedida e o que diz
        que a saida foi normal - e ela so serve se vier depois da chamada.
        """
        texto = _bat()
        chamada = texto.find(CHAMADA)
        despedida = texto.find("Ponte encerrada", chamada)

        assert chamada != -1
        assert despedida > chamada, "a despedida sumiu ou vem antes da chamada"


class TestAsGuardasVemAntesDeSubir:
    def test_a_guarda_do_venv_vem_antes_da_chamada_e_sai_com_codigo_de_falha(self):
        """Nao basta existir a guarda: ela tem de INTERROMPER o caminho.

        Uma guarda depois da chamada nao guarda nada, e sair com 0 depois de
        falhar mentiria para quem encadeia o .bat.
        """
        texto = _bat()
        guarda = texto.find('if not exist ".venv\\Scripts\\python.exe"')
        chamada = texto.find(CHAMADA)

        assert guarda != -1, "sumiu a guarda do .venv"
        assert guarda < chamada, "a guarda do .venv vem DEPOIS da chamada"
        assert "exit /b 1" in texto[guarda:chamada]

    def test_a_guarda_do_config_vem_antes_da_chamada(self):
        """Sem config.toml a ponte nao sabe quais canais ouvir (CONF-03)."""
        texto = _bat()
        guarda = texto.find('if not exist "config.toml"')
        chamada = texto.find(CHAMADA)

        assert guarda != -1, "sumiu a guarda do config.toml"
        assert guarda < chamada


class TestASondaDeDependencia:
    def test_a_sonda_tem_um_alvo_so_e_e_o_import_do_discord(self):
        """UM alvo. A ponte so precisa de uma biblioteca a mais que o scanner.

        Sondar a lista inteira faria esta janela reclamar de dependencia do
        scanner, que nao e problema dela.
        """
        assert 'import discord' in _bat()

    def test_a_sonda_recusa_e_sai_com_codigo_de_falha_antes_de_subir(self):
        """Faltando a biblioteca, a janela PARA. Ela nao tenta consertar."""
        texto = _bat()
        sonda = texto.find("import discord")
        chamada = texto.find(CHAMADA)

        assert sonda != -1 and sonda < chamada
        trecho = texto[sonda:chamada]
        assert "errorlevel 1" in trecho
        assert "exit /b 1" in trecho

    def test_a_sonda_manda_rodar_o_vigiar_party_em_vez_de_instalar(self):
        """O conserto certo e no lugar certo: quem monta o ambiente e ele."""
        texto = _bat()
        sonda = texto.find("import discord")
        chamada = texto.find(CHAMADA)

        assert "vigiar-party.bat" in texto[sonda:chamada]


class TestEstaJanelaNuncaMexeNoAmbienteDoScanner:
    def test_nenhuma_linha_EXECUTAVEL_cita_o_instalador_nem_a_lista_de_requisitos(self):
        """A forma EXECUTAVEL de dizer "esta janela nao instala nada".

        Uma promessa escrita num REM e so uma promessa. Esta asercao e o que
        impede alguem de "consertar" a sonda copiando o final do
        `vigiar-party.bat` para ca - que e a coisa mais natural do mundo de se
        fazer, e o jeito exato de escrever por cima do cv2.pyd no meio do farm.
        """
        ofensas = [
            (linha, nome)
            for linha in _linhas_executaveis(_bat())
            for nome in NOMES_DO_INSTALADOR
            if nome in linha.lower()
        ]

        assert not ofensas, (
            f"linha executavel do ponte-discord.bat citando o instalador: "
            f"{ofensas}. So o vigiar-party.bat monta o ambiente."
        )

    def test_o_comentario_que_explica_a_proibicao_continua_no_lugar(self):
        """Sem o porque escrito, a proibicao vira cerimonia e alguem a remove.

        E tambem o dado que prova que a varredura acima corta comentario: o
        motivo esta escrito no arquivo, num REM, e mesmo assim a asercao de
        cima passa verde.
        """
        texto = _bat().lower()

        assert "nunca instala nada" in texto
        assert "vigiar-party.bat" in texto


class TestORoteiroDoPortaoHumano:
    def test_o_roteiro_tem_os_quatro_passos(self):
        """Tres passos deixam o usuario com um bot conectado e sem destino."""
        texto = _roteiro()

        for numero in (1, 2, 3, 4):
            assert f"PASSO {numero}" in texto, f"sumiu o passo {numero}"

    def test_o_roteiro_manda_ligar_a_intent_MESSAGE_CONTENT(self):
        """E o passo sem o qual tudo o mais funciona e nada serve.

        Sem essa intent o bot conecta, fica online e recebe toda mensagem com o
        texto vazio - o modo de falha mais caro do milestone.
        """
        assert "MESSAGE CONTENT" in _roteiro()

    def test_o_roteiro_traz_o_texto_de_teste_LITERAL(self):
        """"poste alguma coisa" reabre a porta para a arroba.

        Dar a frase pronta e o que faz o usuario copiar e colar em vez de
        improvisar um `@ponte teste`.
        """
        assert "teste da ponte 1" in _roteiro()

    def test_o_roteiro_avisa_para_NAO_mencionar_o_bot(self):
        """A asercao que impede o portao humano de virar encenacao.

        Uma mensagem que menciona o bot chega com texto MESMO COM A INTENT
        DESLIGADA. Testar com arroba faz o console mostrar verde enquanto o
        modo de falha mais caro do projeto continua escondido, e ele so
        apareceria no primeiro anuncio de guild de verdade.
        """
        texto = _roteiro()

        assert "NAO pode mencionar o bot" in texto
        assert "MESMO COM A INTENT DESLIGADA" in texto
        assert "sem arroba" in texto

    def test_o_roteiro_diz_para_nao_reusar_a_conversa_de_comando(self):
        """Anuncio de guild caindo no canal de comando mistura duas coisas.

        Uma delas e a conversa de onde o scanner ACEITA COMANDO; enche-la de
        anuncio e o caminho mais curto para alguem parar de ler as duas.
        """
        assert "CHATWOOT_CONVERSAS_COMANDO" in _roteiro()
