"""Comandos vindos do WhatsApp: o scanner passa a OUVIR, nao so a falar.

Ate aqui o caminho era de mao unica. Isto abre a volta — e abrir a volta e
abrir uma superficie de ataque, entao o desenho comeca pela seguranca e nao
pela funcionalidade.

TRES TRAVAS, E NENHUMA E OPCIONAL:

1. **Allowlist de conversa.** So conversas explicitamente configuradas em
   `CHATWOOT_CONVERSAS_COMANDO` sao lidas. Medido no Chatwoot do usuario: a
   conta tem 22 conversas, 11 com mensagens de entrada, e sao CLIENTES REAIS —
   uma delas, do Joao Pedro, diz literalmente "Quero cancelar". Um leitor que
   varresse a conta inteira obedeceria a ele.

2. **Prefixo estrito.** Comandos comecam com barra (`/cancelar`), a convencao
   do proprio Lineage (`/target`, `/invite`). A forma antiga com ponto segue
   ACEITA e nao anunciada — ver `PREFIXOS`. Sem prefixo nenhum, qualquer
   conversa sobre "cancelar o silencio" viraria uma acao.

3. **So `incoming`.** `message_type == 0`. O scanner nunca pode obedecer as
   proprias mensagens — um comando ecoado viraria laco infinito.

E UMA QUARTA, contra repeticao: cada mensagem so e obedecida uma vez, por id.
O registro e o mesmo `.agenda/`, entao vale entre reinicios e entre as duas
instancias do usuario.

E UMA QUINTA, sobre QUEM manda: a allowlist de telefone
(`CHATWOOT_TELEFONES_COMANDO`), que vale ate dentro de um grupo, onde a
allowlist de conversa sozinha liberaria todo mundo.

**E A QUINTA TEM DOIS NIVEIS.** Ela era global e binaria: um telefone na
allowlist podia TUDO, inclusive `.corrigir` e `.pegou`, que reescrevem a
estatistica permanente do `.loot/` — pasta que nunca e podada e nao tem
backup. Quando a party ganhou `.join` e `.leave`, por os telefones dos quatro
a oito party-mates naquela lista teria dado a todos eles esse poder, de carona
numa funcionalidade de presenca. Entao:

- **Dono** (`CHATWOOT_TELEFONES_COMANDO`, no `.env`): alcanca TODO comando do
  enum. Avaliado primeiro, e ADITIVO — nada aqui foi tirado dele.
- **Membro** (`[[membro]]` no `config.toml`, nick + telefone): alcanca
  EXCLUSIVAMENTE o que estiver em `COMANDOS_DE_MEMBRO`.

Ver `autorizado_para`, onde a ordem das duas perguntas e a decisao inteira.

NOTA DE CAMPO (2026-08-24): o grupo do usuario NAO entrega mensagens de entrada
ao Chatwoot — a ponte Baileys vem com ingestao de grupo desligada. Conversas
1-a-1 entregam normalmente. Por isso a conversa de comandos e configuravel
separada da de avisos: da para receber comando no privado e responder no grupo.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

# A gramatica do batismo vem do `batismo` e nao e reescrita aqui, no mesmo
# precedente do `interpretar_pegou` logo ao lado: uma gramatica so, que valida
# na interpretacao e le no responder.
from .batismo import interpretar_batismo
from .esquecimento import interpretar_esquecimento
from .loot import NICK_VALIDO, apelido, interpretar_pegou

# O prefixo OFICIAL, e o unico que aparece em TEXTO: ajuda, respostas, README,
# comentarios do `config.toml`. E a barra porque e a convencao do proprio
# Lineage — a mao que joga ja digita `/target` e `/invite`, entao o comando do
# bot cai no mesmo dedo.
PREFIXO = "/"

# O que o parser ACEITA. A barra primeiro, a forma antiga depois — aceita e
# NUNCA anunciada.
#
# O ponto nao foi cortado por causa de um modo de falha concreto deste
# desenho: comando nao reconhecido morre EM SILENCIO, no `continue` do laco de
# autorizacao de `comandos_novos`. Nao existe resposta de recusa (e nao pode
# existir: responder a texto arbitrario de terceiro abriria eco). Entao um
# corte seco deixaria os cinco party-mates ja treinados no ponto digitando
# `.join` e recebendo NADA — indistinguivel, do lado deles, de "o bot caiu".
# Manter a forma antiga custa um caractere nesta tupla.
#
# QUAL USAR: `PREFIXO` para montar texto que alguem vai LER; `PREFIXOS` para
# decidir se um texto e comando. Trocar os dois de lugar anuncia o legado ou
# recusa a barra, e as duas falhas sao silenciosas.
PREFIXOS = (PREFIXO, ".")

# Chatwoot usa INT em message_type. 0 = incoming (pessoa), 1 = outgoing (bot).
# Descoberto lendo a API de verdade — a documentacao fala em strings.
MESSAGE_TYPE_INCOMING = 0

# Quantos digitos FINAIS do telefone comparar.
#
# Nao e preguica — e o unico jeito que funciona no Brasil. Celulares ganharam um
# NONO DIGITO e a base do WhatsApp carrega as duas formas da mesma pessoa.
# Medido nesta conta: o usuario se identifica como +5544997077000 e o Chatwoot
# registra o dono do grupo dele como 554497077000, sem o 9.
#
#   +5544997077000 -> 97077000
#    554497077000  -> 97077000
#
# Comparacao exata falharia em SILENCIO: o comando seria ignorado sem erro
# nenhum, que e o pior modo de falha possivel para uma trava de seguranca.
#
# O preco: dois numeros diferentes com os mesmos 8 digitos finais colidem. Numa
# allowlist de duas a cinco pessoas isso e aceitavel, e esta documentado.
DIGITOS_FINAIS_DO_TELEFONE = 8


class Comando(Enum):
    """O que o scanner aceita obedecer. Fechado de proposito.

    Cada item aqui e uma coisa que qualquer pessoa do grupo pode mandar o
    scanner fazer. A lista curta nao e falta de imaginacao — e o limite do
    estrago possivel.
    """

    CANCELAR_SILENCIO = "cancelar_silencio"
    STATUS = "status"

    # Entrar e sair do modo solo sem reiniciar. E o comando que mais faz
    # sentido vir do WhatsApp: a hora de virar solo e quando a party se
    # desfaz, e nesse momento o usuario esta no jogo, nao no console.
    SOLO = "solo"
    PARTY = "party"

    # Entrar e sair da lista de presenca do proximo Solo Boss. Sao os dois
    # PRIMEIROS comandos alcancaveis por um SEGUNDO nivel de autorizacao: o
    # telefone de um party-mate declarado em `[[membro]]` no config.toml chega
    # ate estes dois e para neles.
    #
    # E e por isso que este enum passa a precisar do `COMANDOS_DE_MEMBRO` logo
    # abaixo. Sem um conjunto explicito, "o que um party-mate alcanca" seria
    # uma regra espalhada por ifs, e uma fronteira de autorizacao que so da
    # para conferir lendo o arquivo inteiro nao e uma fronteira.
    JOIN = "join"
    LEAVE = "leave"

    # O controle de loot do Solo Boss. Sao os dois primeiros comandos com
    # ARGUMENTO (o nick), e por isso nao moram no _VOCABULARIO — quem os
    # reconhece e `interpretar_dinamico`.
    LOOT_DESIGNAR = "loot_designar"
    LOOT_CONSULTA = "loot_consulta"

    # O UNICO comando DESTRUTIVO da superficie dinamica: ele APAGA estado
    # duravel em vez de escrever por cima. Por isso a sintaxe dele e
    # explicita (hifen ou palavra reservada) e `.loot` sozinho nao serve —
    # ver D-02 em `interpretar_dinamico`.
    LOOT_CANCELAR = "loot_cancelar"

    # O PRIMEIRO comando que reescreve HISTORICO. Os outros tres mexem na VEZ
    # do proximo boss — estado que expira sozinho quando o horario passa. Este
    # mexe na estatistica, que nunca e podada e nao tem backup. E por isso que
    # o alcance dele para no registro MAIS RECENTE: o limite do estrago
    # possivel nao pode depender de quem digita lembrar de ter cuidado.
    LOOT_CORRIGIR = "loot_corrigir"

    # O SEGUNDO comando que reescreve historico, e o limite dele e de outra
    # natureza. O `.corrigir` e contido por NAO TER SINTAXE que alcance o
    # passado: nao ha como digitar um horario, entao nao ha como errar de
    # boss por meses. O `.pegou` tem exatamente essa sintaxe — e o motivo dele
    # existir, porque o `.corrigir` nao alcanca "nao ha registro nenhum" —, e
    # paga por ela com duas protecoes proprias: o horario tem que ENCAIXAR
    # numa ocorrencia real do Solo Boss (nunca nasce registro orfao) e a
    # resposta sempre diz o DIA de volta, para quem digitou conferir na hora
    # que acertou o boss. Os dois limites sao reais e sao diferentes; e por
    # isso que os dois comandos coexistem em vez de um substituir o outro.
    LOOT_ATRIBUIR = "loot_atribuir"

    # Desligar e religar TODOS os avisos do Solo Boss — a chamada de 1h50 e o
    # lembrete de 10 minutos, juntos e nunca um sem o outro.
    #
    # TUDO OU NADA E DECISAO DE PRODUTO, NAO PREGUICA DE SINTAXE. A chamada sem
    # o lembrete convida a party para um boss que ninguem lembra de ir; o
    # lembrete sem a chamada avisa 10 minutos antes uma party que nunca foi
    # consultada. Meia-mudez e pior que os dois extremos, entao nao existe
    # comando que alcance metade — o gate mora em `agenda.avisos_devidos`, no
    # funil por onde os tres tipos de aviso passam.
    #
    # SAO DOIS COMANDOS, E NAO UM COM ARGUMENTO. O armazenamento e o gate ja
    # sao genericos por evento, porque isso nao custou uma linha a mais; a
    # SUPERFICIE nao e. Um `/avisos <evento> off` alcancaria TvT e Prime, que
    # ninguem pediu, e esta lista e curta de proposito — ver o cabecalho deste
    # enum.
    #
    # E OS DOIS FICAM FORA DE `COMANDOS_DE_MEMBRO`, logo abaixo. Um `/entrar`
    # de party-mate mexe numa linha da lista de UMA ocorrencia e quem digitou
    # ve o efeito. Isto apaga doze chamadas por dia da party INTEIRA, por tempo
    # indeterminado, e o efeito e a AUSENCIA de mensagem — do lado dos outros,
    # indistinguivel do bot ter caido. Nao e um `/entrar` maior; e outra
    # categoria de estrago.
    DESATIVAR_SOLO_BOSS = "desativar_solo_boss"
    ATIVAR_SOLO_BOSS = "ativar_solo_boss"

    # A IRMA FINA DO PAR ACIMA: desliga so a maquinaria de MONTAR GRUPO do Solo
    # Boss, e deixa o boss falando.
    #
    # O QUE CAI: a chamada "Quem vai?", o `/entrar`, o `/sair`, o fechamento da
    # lista quando o boss nasce, e a designacao de loot (`/loot-<nick>` e a
    # linha `Loot:` do aviso).
    #
    # O QUE NAO CAI, E E O PONTO INTEIRO: o lembrete de antecedencia. A party
    # parou de fazer Solo Boss em grupo e o usuario quer continuar sabendo que
    # o boss vai nascer. Tambem nao cai o HISTORICO de loot — `/pegou`,
    # `/corrigir` e `/<nick>` continuam inteiros, porque desligar a lista nao
    # e apagar o passado.
    #
    # NAO HA PRECEDENCIA ENTRE ESTE PAR E O DE CIMA, e por isso sao dois pares
    # e nao um estado de tres valores. O `/desativarsoloboss` e um martelo
    # maior NA CHAMADA (cala os tres tipos de aviso), mas nao alcanca o
    # `/entrar`, nem o fechamento, nem a designacao. Nenhum dos dois contem o
    # outro, e um "desliguei tudo" unico esconderia metade — alem de deixar o
    # usuario sem saber qual comando religa o que.
    #
    # E OS DOIS TAMBEM FICAM FORA DE `COMANDOS_DE_MEMBRO`, pela razao do par
    # acima e com uma agravante propria: um party-mate podia desligar a lista
    # de presenca de todos os OUTROS, e o sintoma do lado deles seria uma
    # chamada que simplesmente parou de chegar.
    DESATIVAR_LISTA = "desativar_lista"
    ATIVAR_LISTA = "ativar_lista"

    # A janela de respawn dos bosses vigiados, sob demanda. O bot ja anuncia
    # sozinho quando cada janela vence; isto responde a mesma coisa na hora em
    # que alguem pergunta, sem esperar o proximo vencimento.
    #
    # O NOME E GENERICO DE PROPOSITO, E NAO PODE SER `TIAT`. Todo o workstream
    # da janela foi construido sobre os blocos `[[boss]]` do config.toml,
    # porque o usuario disse desde o inicio que no futuro o mesmo codigo serve
    # para outro mob. Um membro chamado `TIAT` seria o UNICO lugar do sistema
    # preso a um boss especifico — o unico ponto onde trocar de boss exigiria
    # editar codigo em vez de editar configuracao.
    #
    # `/tiat` FUNCIONA MESMO ASSIM, e e a forma que o usuario pediu com todas
    # as letras. Ela entra no `_VOCABULARIO` como uma das formas escritas, do
    # mesmo jeito que `scanner` alcanca o `STATUS`: o simbolo e generico e a
    # palavra que a mao digita no meio do farm e concreta. Nenhuma das duas
    # precisa ceder para a outra.
    #
    # NAO ACEITA ARGUMENTO. Responde sobre TODOS os bosses vigiados, na ordem
    # do config.toml, e por isso mora aqui e nao em `interpretar_dinamico`.
    # Filtrar por boss custaria uma sintaxe nova para escolher entre os DOIS
    # itens que a lista tem hoje, e a resposta inteira cabe numa tela.
    JANELA = "janela"

    # Dar NOME a uma assinatura que o scanner aprendeu sozinho e PERGUNTOU
    # quem era.
    #
    # E O TERCEIRO COMANDO QUE ESCREVE ESTADO DURAVEL QUE NUNCA E PODADO,
    # depois de `LOOT_CORRIGIR` e `LOOT_ATRIBUIR`, e o dano de um nome errado e
    # da MESMA familia do deles: corrupcao duravel e dificil de notar, num
    # acervo sem comando de esquecer e sem backup. O sintoma nao e um erro nem
    # uma linha no log — e a party socorrendo a pessoa errada, com a mensagem
    # parecendo perfeitamente normal.
    #
    # POR ISSO ELE FICA FORA DE `COMANDOS_DE_MEMBRO` (decisao 2 do ROADMAP, ja
    # travada), e ele fica de fora SOZINHO: aquele conjunto e LISTA DE
    # INCLUSAO, entao um comando destrutivo novo NASCE fora do alcance e
    # ninguem precisou lembrar de excluir nada. `/entrar` e `/sair` alcancam o
    # `[[membro]]` porque sao baratos e so falam do proprio remetente; batizar
    # nao e nenhum dos dois.
    #
    # E ELE NAO ENTRA NO `_VOCABULARIO`: tem ARGUMENTO, entao quem o reconhece
    # e `interpretar_dinamico`, como `.loot-<nick>`, `.corrigir-<nick>` e
    # `.pegou <hora> <nick>`.
    #
    # O ALVO E A CHAVE DE CONTEUDO DA ASSINATURA, E NUNCA UMA LINHA (D-03). A
    # party se reorganiza entre a pergunta e a resposta, e resolver por posicao
    # batizaria a pessoa errada em silencio.
    BATIZAR = "batizar"

    # Tirar do acervo uma assinatura que nunca deveria ter entrado.
    #
    # E O COMANDO MAIS DESTRUTIVO DO PROJETO, e por isso a razao dele ficar
    # FORA de `COMANDOS_DE_MEMBRO` e mais forte que a do `/batizar` logo acima,
    # e nao apenas igual. Um batismo errado corrompe um NOME, e o proximo
    # alerta mostra a mentira. Um esquecimento errado tira do reconhecimento
    # uma pessoa que o scanner enxerga hoje, e o sintoma e ela virar "Membro N"
    # no meio de um farm, sem uma linha de log dizendo por que. Foi assim que
    # um membro passou DUAS HORAS como "Membro 1" em 2026-08-25.
    #
    # Ele fica de fora SOZINHO, sem ninguem ter lembrado de excluir nada:
    # `COMANDOS_DE_MEMBRO` e LISTA DE INCLUSAO, exatamente para que o proximo
    # comando destrutivo do projeto NASCA fora do alcance de um party-mate.
    #
    # E ELE NAO E "APAGAR", nem no nome nem no efeito. `acervo.esquecer`
    # RENOMEIA os dois arquivos da entrada, e a resposta diz para quais nomes:
    # a operacao inteira e desfeita a mao, com dois `rename` e um reinicio. Um
    # `unlink` comandado por WhatsApp numa pasta sem backup seria a unica
    # operacao irreversivel deste projeto.
    #
    # ELE NAO ENTRA NO `_VOCABULARIO`: tem ARGUMENTO, entao quem o reconhece e
    # `interpretar_dinamico`, como o `/batizar`.
    #
    # O ALVO E A CHAVE DE CONTEUDO, E NUNCA UMA LINHA, pela razao ja escrita em
    # D-03: a party se reorganiza entre a pergunta e a resposta.
    ESQUECER = "esquecer"

    # O UNICO comando que nao muda estado nenhum, e o unico cujo conteudo e
    # DERIVADO dos outros: ele le a tabela `_AJUDA` e devolve o que os demais
    # membros deste enum dizem sobre si mesmos. Por isso ele e o unico que
    # ganha um teste-tripwire — crescer o enum sem crescer a tabela quebra a
    # suite de proposito.
    AJUDA = "ajuda"


# O que o SEGUNDO nivel de autorizacao alcanca — e nada alem disto.
#
# LISTA DE INCLUSAO, NUNCA DE EXCLUSAO, e a diferenca nao e estetica. Escrita
# como exclusao (`set(Comando) - {LOOT_CORRIGIR, LOOT_ATRIBUIR}`), o proximo
# comando destrutivo do projeto NASCERIA alcancavel por qualquer party-mate, e
# so seria contido se quem o escreveu lembrasse de vir aqui excluir. Escrita
# como inclusao, ele nasce FORA do alcance e ninguem precisa lembrar de nada.
#
# O teste da fronteira deriva a lista de RECUSA daqui — `set(Comando) -
# COMANDOS_DE_MEMBRO` — entao a prova cresce sozinha quando o enum crescer.
#
# CADA ENTRADA PRECISA DIZER POR QUE MERECE ESTAR AQUI, e a disciplina vale
# tambem para a que nao muda estado nenhum:
#
# - `JOIN` e `LEAVE`: mexem numa linha da lista de UMA ocorrencia, e quem
#   digitou ve o efeito na hora. Sao a razao de este conjunto existir.
#
# - `JANELA`: e o primeiro comando SOMENTE-LEITURA da lista, e o argumento e
#   diferente dos dois de cima. Ele nao escreve nada, nao fala do remetente e
#   nao muda o que o grupo recebe. E o que ele revela, o proprio bot JA
#   ANUNCIA ao grupo por conta propria quando cada janela vence — entao um
#   party-mate que digita `/tiat` nao fica sabendo nada que ele nao fosse
#   receber sozinho daqui a pouco. O comando so adianta, sob demanda, um texto
#   que ja e publico para exatamente esta plateia. Recusa-lo teria o custo
#   ja documentado no `_VOCABULARIO`: comando nao autorizado morre no
#   `continue` do laco, sem resposta de recusa, e o silencio e indistinguivel
#   do bot ter caido.
COMANDOS_DE_MEMBRO: frozenset[Comando] = frozenset(
    {Comando.JOIN, Comando.LEAVE, Comando.JANELA}
)


# As formas escritas que valem para cada comando. Varias por comando porque
# ninguem lembra a sintaxe exata no meio de um farm.
_VOCABULARIO: dict[str, Comando] = {
    "cancelar": Comando.CANCELAR_SILENCIO,
    "cancelarsilencio": Comando.CANCELAR_SILENCIO,
    "silencio": Comando.CANCELAR_SILENCIO,
    "voltar": Comando.CANCELAR_SILENCIO,
    "status": Comando.STATUS,
    "scanner": Comando.STATUS,
    "solo": Comando.SOLO,
    "soloplay": Comando.SOLO,
    "party": Comando.PARTY,
    "pt": Comando.PARTY,
    "grupo": Comando.PARTY,
    # `.join` e `.leave` nao tem ARGUMENTO, entao moram aqui e nao em
    # `interpretar_dinamico` — mesma razao de `.solo` e `.party`. E estar neste
    # dicionario ja os protege de virar consulta de nick: o ramo `.{nick}`
    # recusa por nome tudo que esta aqui.
    #
    # O PRECO, ACEITO E DOCUMENTADO, e o mesmo de `_PALAVRAS_DE_CANCELAMENTO`:
    # cada palavra registrada aqui e um personagem que deixa de ser consultavel
    # por `.<nick>`. Um char chamado "Sair" nao responde mais a `.sair`. E
    # exatamente por isso que a lista de apelidos e CURTA — duas formas por
    # comando, a inglesa que a party ja usa em jogo e a portuguesa que a mao
    # digita sozinha.
    #
    # QUAL DELAS O PRODUTO ANUNCIA mudou em 2026-08-27: a party e brasileira e
    # a mao digita portugues sozinha, entao "entrar" e "sair" passaram a ser a
    # sintaxe da tabela `_AJUDA` e "join" e "leave" viraram apelido ANUNCIADO
    # ali — demovidos da vitrine, nunca apagados dela.
    #
    # AS QUATRO ENTRADAS ABAIXO NAO SAEM DAQUI. Comando nao reconhecido e
    # descartado no `continue` do laco de autorizacao: nao existe resposta de
    # recusa. Quem decorou "join" e o digitasse depois de um corte receberia
    # NADA — indistinguivel, do lado dele, de o bot ter caido.
    "join": Comando.JOIN,
    "entrar": Comando.JOIN,
    "leave": Comando.LEAVE,
    "sair": Comando.LEAVE,
    # Duas formas por comando, e o `interpretar` entrega mais quatro de graca:
    # ele tira hifens e sublinhados do miolo, entao `/desativar-solo-boss` cai
    # em `desativarsoloboss`, e junta as duas primeiras palavras, entao
    # `/desativar boss` cai em `desativarboss`.
    #
    # A FORMA CURTA NAO E CAPRICHO: a longa tem 17 caracteres e quem digita no
    # meio de um farm erra. O preco e o mesmo ja documentado no topo deste
    # dicionario — um personagem chamado "DesativarBoss" deixa de ser
    # consultavel por `/<nick>`. A forma longa nem cobra esse preco: 17
    # caracteres nao casam `NICK_VALIDO`, que para em 16.
    #
    # `/desativar` SOZINHO NAO ESTA AQUI, e a ausencia e deliberada — mesma
    # disciplina do D-02 no `.loot`. Comando sem argumento nao pode mexer em
    # estado duravel: quem digita `/desativar` nao disse O QUE desativar, e
    # adivinhar seria calar o boss por conta propria.
    "desativarsoloboss": Comando.DESATIVAR_SOLO_BOSS,
    "desativarboss": Comando.DESATIVAR_SOLO_BOSS,
    "ativarsoloboss": Comando.ATIVAR_SOLO_BOSS,
    "ativarboss": Comando.ATIVAR_SOLO_BOSS,
    # O par da LISTA, e aqui o segundo nome NAO E ABREVIACAO — e SINONIMO. A
    # diferenca importa: `desativarboss` nasceu porque `desativarsoloboss` tem
    # 17 caracteres e a mao erra no meio do farm; `desativarlista` ja tem 14 e
    # nao precisa encolher. O risco aqui e outro, e e a PALAVRA — quem pensa
    # "presenca" em vez de "lista" digitaria uma forma que morre no `continue`
    # do laco de autorizacao, SEM resposta de recusa nenhuma, e o sintoma do
    # lado de quem digitou e o bot ter caido.
    #
    # AUDITORIA DE COLISAO com `_NICK_VALIDO` ([A-Za-z0-9]{2,16}), feita como o
    # comentario do topo deste dicionario manda:
    #
    #   desativarlista     14 letras  casa  -> "DesativarLista" perde o /<nick>
    #   ativarlista        11 letras  casa  -> "AtivarLista" perde o /<nick>
    #   ativarpresenca     14 letras  casa  -> "AtivarPresenca" perde o /<nick>
    #   desativarpresenca  17 letras  NAO casa (o teto e 16) -> preco zero
    #
    # Preco aceito e documentado, o mesmo ja pago por `desativarboss`. Nenhuma
    # delas colide com o roster real.
    #
    # `lista` E `presenca` SOZINHOS NAO ENTRAM, e a ausencia e deliberada em
    # dobro: e a mesma disciplina do D-02 (comando sem argumento nao mexe em
    # estado duravel) e "Lista" e nome de personagem plausivel demais para
    # queimar.
    "desativarlista": Comando.DESATIVAR_LISTA,
    "desativarpresenca": Comando.DESATIVAR_LISTA,
    "ativarlista": Comando.ATIVAR_LISTA,
    "ativarpresenca": Comando.ATIVAR_LISTA,
    # A JANELA DE RESPAWN, e aqui a lista de formas escritas e MAIOR que as
    # duas por comando do resto do dicionario. A razao e que o simbolo e
    # generico e a palavra que a mao digita nao e: quem esta no farm pensa no
    # BOSS ("tiat"), quem leu a ajuda pensa no conceito ("janela"), e quem
    # decorou o config.toml pensa no campo ("respawn"). Sao tres vocabularios
    # diferentes para a mesma pergunta, e uma forma que morre no `continue` do
    # laco de autorizacao nao produz recusa nenhuma — do lado de quem digitou,
    # e indistinguivel do bot ter caido.
    #
    # `tiat` E A UNICA PALAVRA DESTE DICIONARIO PRESA A UM BOSS, e ela e uma
    # FORMA ESCRITA e nao um simbolo: o dia em que o usuario vigiar outro mob,
    # apagar esta linha nao mexe em mais nada. O simbolo `Comando.JANELA` ja
    # nasceu generico exatamente para isso.
    #
    # AUDITORIA DE COLISAO com `_NICK_VALIDO` ([A-Za-z0-9]{2,16}), feita como o
    # comentario do topo deste dicionario manda:
    #
    #   tiat     4 letras  casa  -> "Tiat" perde o /<nick>
    #   janela   6 letras  casa  -> "Janela" perde o /<nick>
    #   janelas  7 letras  casa  -> "Janelas" perde o /<nick>
    #   boss     4 letras  casa  -> "Boss" perde o /<nick>
    #   bosses   6 letras  casa  -> "Bosses" perde o /<nick>
    #   respawn  7 letras  casa  -> "Respawn" perde o /<nick>
    #
    # Preco aceito e documentado, o mesmo ja pago por `desativarboss`. Nenhuma
    # delas colide com o roster real, e `Tiat` como nome de PERSONAGEM seria
    # uma escolha estranha justamente por ja ser o nome do boss.
    "tiat": Comando.JANELA,
    "janela": Comando.JANELA,
    "janelas": Comando.JANELA,
    "boss": Comando.JANELA,
    "bosses": Comando.JANELA,
    "respawn": Comando.JANELA,
    "help": Comando.AJUDA,
    "ajuda": Comando.AJUDA,
    "comandos": Comando.AJUDA,
    # `.?` cabe sem gambiarra: `interpretar` faz uma CONSULTA de dicionario,
    # nao uma validacao de charset, entao "?" atravessa os dois `replace`
    # intacto. E como ele nao casa `_NICK_VALIDO`, nao existe colisao com o
    # ramo de consulta por nick — verificado antes de entrar aqui.
    "?": Comando.AJUDA,
}


@dataclass(frozen=True)
class LinhaDeAjuda:
    """O que a ajuda sabe dizer sobre UM comando."""

    familia: str
    sintaxe: str
    descricao: str
    apelidos: tuple[str, ...] = ()


# A ajuda, DERIVADA e nao escrita a mao.
#
# O projeto ganhou CINCO comandos em UM dia (`.loot-`, `.<nick>`,
# `.loot-cancelar`, `.corrigir`, `.pegou`). Um texto de ajuda escrito a mao
# estaria desatualizado antes do fim da semana — e ajuda desatualizada e PIOR
# que ajuda nenhuma: ela ensina sintaxe que NAO FUNCIONA, e quem digitou
# conclui que o bot esta quebrado. Por isso existe esta tabela, e por isso
# existe o tripwire em `tests/test_comandos.py` afirmando
# `set(_AJUDA) == set(Comando)`: comando novo sem ajuda quebra a suite.
#
# A CHAVE E O ENUM, E NAO O `_VOCABULARIO`, e a razao e concreta: os comandos
# dinamicos (`.loot-<nick>`, `.loot-`, `.<nick>`, `.corrigir-<nick>`,
# `.pegou <hora> <nick>`) NAO moram no vocabulario — quem os reconhece e
# `interpretar_dinamico`. Um tripwire contra o vocabulario nao os enxergaria,
# e sao justamente eles os cinco que nasceram no mesmo dia.
#
# A ORDEM DE INSERCAO E A ORDEM DA RESPOSTA (dict preserva ordem): uma fonte
# so para a tabela e para o texto, em vez de duas listas para divergirem.
_AJUDA: dict[Comando, LinhaDeAjuda] = {
    Comando.STATUS: LinhaDeAjuda(
        "Vigilancia",
        "/status",
        "Digo se estou vigiando ou calado, e qual o proximo evento",
    ),
    Comando.SOLO: LinhaDeAjuda(
        "Vigilancia", "/solo", "Vigio so o seu personagem e paro de reclamar de party"
    ),
    Comando.PARTY: LinhaDeAjuda(
        "Vigilancia", "/party", "Volto a vigiar a party inteira", ("/pt",)
    ),
    # A SINTAXE ANUNCIADA E `/tiat`, e nao a generica, embora o simbolo do enum
    # seja generico. A ajuda existe para a mao que digita no meio do farm, e
    # essa mao pensa no BOSS. Anunciar so `/janela` faria o usuario que pediu
    # este comando com o nome `/tiat` procurar na lista uma palavra que ele nao
    # usa. O apelido generico vai junto, na mesma linha, para o dia em que o
    # boss vigiado for outro — demovida da vitrine, a forma nunca some dela, que
    # e a mesma disciplina de `/join` e `/leave`.
    #
    # A DESCRICAO DIZ AS TRES COISAS que a resposta entrega, e nao so a
    # primeira. Quem le "quando a janela abre" e recebe tres frases por boss
    # conclui que o bot falou demais; quem le a linha inteira sabe o que vem.
    Comando.JANELA: LinhaDeAjuda(
        "Vigilancia",
        "/tiat",
        "Quando a janela de cada boss vigiado abre, de que nascimento sai a "
        "conta, e quanto dela e sorteio",
        ("/janela", "/boss"),
    ),
    Comando.CANCELAR_SILENCIO: LinhaDeAjuda(
        "Silencio", "/cancelar", "Tira o silencio de TvT/Prime que estiver rolando"
    ),
    # Na familia "Silencio" e logo depois do `/cancelar` porque a ordem de
    # insercao E a ordem da resposta: os tres controles de "parar de falar"
    # ficam no mesmo bloco da tela do celular, em vez de o desligamento do boss
    # aparecer perdido entre presenca e loot.
    #
    # A descricao diz OS DOIS AVISOS por extenso. Quem le a ajuda precisa saber
    # que e tudo ou nada antes de digitar — descobrir depois, pela ausencia de
    # uma chamada que ele achava que tinha mantido, e descobrir tarde.
    Comando.DESATIVAR_SOLO_BOSS: LinhaDeAjuda(
        "Silencio",
        "/desativarsoloboss",
        "Paro com TUDO do Solo Boss: nem a chamada, nem o lembrete. Continua "
        "desligado depois de reiniciar",
        ("/desativarboss",),
    ),
    Comando.ATIVAR_SOLO_BOSS: LinhaDeAjuda(
        "Silencio",
        "/ativarsoloboss",
        "Volto a chamar e a lembrar do Solo Boss",
        ("/ativarboss",),
    ),
    # Logo depois do par de cima porque a ordem de insercao E a ordem da
    # resposta, e os dois pares tem que ser lidos JUNTOS: escolher o errado e o
    # unico jeito de o usuario desligar coisa diferente da que queria.
    #
    # A descricao diz que o lembrete CONTINUA, e essa e a informacao inteira.
    # Quem le a ajuda precisa saber o recorte antes de digitar — descobrir
    # depois, pela presenca de um aviso que achava que tinha desligado (ou pela
    # ausencia de um que achava que tinha mantido), e descobrir tarde.
    Comando.DESATIVAR_LISTA: LinhaDeAjuda(
        "Silencio",
        "/desativarlista",
        "Paro de perguntar quem vai no Solo Boss: sem chamada, sem /entrar e "
        "sem designar loot. O lembrete de 10 minutos CONTINUA chegando",
        ("/desativarpresenca",),
    ),
    Comando.ATIVAR_LISTA: LinhaDeAjuda(
        "Silencio",
        "/ativarlista",
        "Volto a perguntar quem vai e a aceitar /entrar e /sair",
        ("/ativarpresenca",),
    ),
    # A familia Presenca vem ANTES de "Loot do Solo Boss" porque essa e a ordem
    # do ciclo do boss: primeiro a party diz quem vai, so depois se decide de
    # quem e o loot. A ordem de insercao deste dict E a ordem da resposta.
    Comando.JOIN: LinhaDeAjuda(
        "Presenca",
        "/entrar",
        "Entro na lista do proximo Solo Boss",
        ("/join",),
    ),
    Comando.LEAVE: LinhaDeAjuda(
        "Presenca",
        "/sair",
        "Saio da lista do proximo Solo Boss",
        ("/leave",),
    ),
    Comando.LOOT_DESIGNAR: LinhaDeAjuda(
        "Loot do Solo Boss", "/loot-<nick>", "Marca quem pega o loot do proximo boss"
    ),
    Comando.LOOT_CANCELAR: LinhaDeAjuda(
        "Loot do Solo Boss", "/loot-", "Desmarca: o proximo boss volta a ser de ninguem"
    ),
    Comando.LOOT_CONSULTA: LinhaDeAjuda(
        "Loot do Solo Boss",
        "/<nick>",
        "Quantos loots o char ja pegou, e quando foi o ultimo",
    ),
    Comando.LOOT_CORRIGIR: LinhaDeAjuda(
        "Loot do Solo Boss",
        "/corrigir-<nick>",
        "Troca o dono do ultimo loot ja registrado",
    ),
    Comando.LOOT_ATRIBUIR: LinhaDeAjuda(
        "Loot do Solo Boss",
        "/pegou <hora> <nick>",
        "Registra loot de um boss que ja passou (ex.: 18:00 Korzis)",
    ),
    # A familia "Identidade" nasce DEPOIS de "Loot do Solo Boss" e ANTES de
    # "Ajuda", e a ordem de insercao E a ordem da resposta. Ela e a menos
    # digitada da lista — o batismo acontece uma vez por pessoa, para sempre —
    # entao ela nao pode empurrar para baixo o que se usa todo dia.
    #
    # A DESCRICAO PRECISA DIZER DE ONDE VEM O APELIDO. Sem isso o usuario le a
    # ajuda e nao sabe o que digitar no primeiro argumento, que e a unica coisa
    # nao obvia deste comando: ele nao e um nick, nao e um numero de linha, e
    # nao esta em lugar nenhum a nao ser na pergunta que o scanner mandou.
    Comando.BATIZAR: LinhaDeAjuda(
        "Identidade",
        "/batizar <apelido> <nick>",
        "Dou nome a alguem que eu aprendi sozinho. O apelido e o codigo de "
        "digitos que eu cito na pergunta",
        ("/nomear <apelido> <nick>",),
    ),
    # Logo depois do `/batizar` porque a ordem de insercao E a ordem da
    # resposta, e os dois tem que ser lidos JUNTOS: sao as duas unicas coisas
    # que se pode fazer com uma assinatura, e a recusa de nome ocupado do
    # batismo aponta para ca.
    #
    # A FORMA EM LOTE E ANUNCIADA COMO APELIDO, e nao escondida. Sao 7 entradas
    # mortas na pasta do usuario hoje: uma forma que existe e nao aparece na
    # ajuda nao existe para quem tem que digitar. O tripwire
    # `test_todo_apelido_anunciado_volta_como_o_comando_certo` roda esta linha
    # pelo caminho real, entao ela nao pode ensinar sintaxe morta.
    #
    # A DESCRICAO DIZ "TIRO DE CIRCULACAO" E NAO "APAGO", porque nao apaga
    # mesmo: uma ajuda que dissesse "apago" ensinaria um medo errado (e o
    # usuario nao usaria o comando) ou uma confianca errada (e ele acharia que
    # ha um desfazer que nao existe). As duas leituras sao caras.
    Comando.ESQUECER: LinhaDeAjuda(
        "Identidade",
        "/esquecer <apelido>",
        "Tiro de circulacao uma assinatura que nao e gente, ou que ficou "
        "velha. Nada e apagado: eu digo como desfazer na mao",
        ("/esquecer fora-de-forma",),
    ),
    Comando.AJUDA: LinhaDeAjuda(
        "Ajuda", "/help", "Esta lista", ("/ajuda", "/comandos")
    ),
}


def texto_de_ajuda() -> str:
    """A lista de comandos, montada a partir do `_AJUDA`.

    NUNCA escrever esta lista a mao. Cinco comandos nasceram num dia so; uma
    ajuda escrita a mao envelheceria antes do fim da semana, e ajuda
    desatualizada e pior que ajuda nenhuma — ela ensina sintaxe que nao
    funciona.

    Sem moldura, sem ANSI e sem `rich`: este texto vai para o CELULAR. A
    `console.moldurar` casa a largura da borda com a linha mais longa, e sao
    dezenove linhas aqui — a moldura viraria uma parede de asteriscos na tela
    do telefone. Ver D-04.
    """
    linhas = [f"Comandos do scanner — sempre com barra ({PREFIXO}) na frente:"]
    familia_atual = ""
    for entrada in _AJUDA.values():
        if entrada.familia != familia_atual:
            familia_atual = entrada.familia
            linhas.append("")
            linhas.append(f"{familia_atual}:")
        sintaxe = entrada.sintaxe
        if entrada.apelidos:
            sintaxe += " (" + ", ".join(entrada.apelidos) + ")"
        linhas.append(f"  {sintaxe} — {entrada.descricao}")
    return "\n".join(linhas)


@dataclass(frozen=True)
class MensagemDeComando:
    """Uma mensagem que pede alguma coisa ao scanner."""

    id: int
    comando: Comando
    autor: str | None
    texto: str

    # De qual conversa o pedido veio. E o que permite RESPONDER onde
    # perguntaram, em vez de responder sempre no grupo de avisos.
    conversa: str | None = None

    # O argumento dos comandos dinamicos, SEMPRE COMO FOI DIGITADO: o nick,
    # na maioria deles, e o argumento inteiro do `.pegou` ("18:00 Korzis"),
    # ainda cru. A resposta mostra o que a pessoa escreveu; normalizar — e,
    # no caso do `.pegou`, reler a gramatica — e trabalho de quem consome.
    argumento: str | None = None

    # O nick do JOGO de quem mandou, quando o telefone dele esta declarado em
    # `[[membro]]` no config.toml. None quando nao esta — e None e o caso
    # NORMAL do dono do scanner, que costuma estar so em
    # CHATWOOT_TELEFONES_COMANDO.
    #
    # Deliberadamente separado do `autor` logo acima: aquele e o `sender.name`
    # do Chatwoot, escrito por quem e dono do telefone, e serve ao log. Este e
    # o nome do PERSONAGEM, e e o unico dos dois que pode ir para uma lista de
    # presenca. Ver a docstring de `Membro`.
    nick: str | None = None


@dataclass(frozen=True)
class Membro:
    """Um party-mate que pode entrar e sair da lista de presenca.

    O CAMPO `nick` E A RAZAO DESTA CLASSE EXISTIR. O Chatwoot entrega um
    `sender.name` junto de cada mensagem e seria de graca usa-lo — mas aquilo
    e o nome do CONTATO, escrito pelo dono do telefone, e nao tem relacao
    nenhuma com o nick do personagem no jogo. Ele muda quando a pessoa troca o
    proprio nome no WhatsApp, vem vazio quando o contato nunca foi nomeado e
    vem com emoji quando a pessoa quis. O nick do jogo, esse, esta escrito no
    config.toml pela mesma mao que calibrou o scanner.

    Mesma disciplina que a deteccao de tela segue desde a Fase 3: nome sempre
    da configuracao, nunca lido de fora.

    Mora NESTE arquivo, e nao no `config.py`, por causa da direcao das
    importacoes: `config` importa `comandos`, e o contrario fecharia um ciclo
    no primeiro uso. A docstring do topo deste arquivo e sobre a superficie de
    seguranca, que e exatamente do que esta classe trata.
    """

    nick: str
    telefone: str


def so_digitos(telefone: str | None) -> str:
    """Descarta tudo que nao e digito: +, espaco, parentese, traco."""
    return "".join(c for c in str(telefone or "") if c.isdigit())


def telefone_equivalente(a: str | None, b: str | None) -> bool:
    """Os dois textos sao o mesmo telefone?

    Compara pelos digitos FINAIS, para atravessar codigo de pais, DDD,
    formatacao e o nono digito brasileiro. Ver DIGITOS_FINAIS_DO_TELEFONE.
    """
    da, db = so_digitos(a), so_digitos(b)
    if not da or not db:
        return False
    corte = DIGITOS_FINAIS_DO_TELEFONE
    if len(da) < corte or len(db) < corte:
        # Numero curto demais para o sufixo valer: exige igualdade completa,
        # em vez de comparar um pedaco pequeno e casar com meio mundo.
        return da == db
    return da[-corte:] == db[-corte:]


def autor_autorizado(remetente: dict, telefones: list[str]) -> bool:
    """Quem mandou pode mandar?

    Lista VAZIA aceita qualquer um — e a compatibilidade com quem ja tinha
    configurado comandos so por conversa. O aviso de arranque cuida de deixar
    isso visivel, porque "qualquer um pode mandar no scanner" nao pode ser um
    estado que se descobre por acidente.
    """
    if not telefones:
        return True
    numero = remetente.get("phone_number")
    return any(telefone_equivalente(numero, permitido) for permitido in telefones)


def membro_do_remetente(
    remetente: dict, membros: Sequence[Membro]
) -> Membro | None:
    """Qual party-mate configurado mandou isto? None quando nenhum.

    O UNICO LUGAR QUE RESPONDE "quem e este telefone?". Havia dois pontos de
    decisao sobre essa mesma pergunta — um para decidir se o remetente e membro
    e outro para descobrir o nick dele — e eles podiam divergir do mesmo jeito
    que duas implementacoes do corte de 8 digitos divergiriam: no primeiro
    ajuste. Um filtro futuro ("membro desativado") aplicado so num dos dois
    produziria uma mensagem AUTORIZADA entrando na lista com `nick=None`, e o
    bot responderia "nao sei que nick por na lista" a alguem corretamente
    configurado. Ver `comandos_novos`, que resolve uma vez e deriva as duas
    respostas do mesmo valor.

    Compara com `telefone_equivalente`, E ISSO NAO E DETALHE DE ESTILO. Uma
    segunda implementacao do corte de 8 digitos aqui divergiria da primeira no
    primeiro ajuste, e as duas travas passariam a discordar sobre quem e quem —
    em silencio, que e o pior modo de falha possivel para uma trava.
    """
    numero = remetente.get("phone_number")
    for membro in membros:
        if telefone_equivalente(numero, membro.telefone):
            return membro
    return None


def nick_do_membro(remetente: dict, membros: Sequence[Membro]) -> str | None:
    """O nick do party-mate que mandou isto. None quando nenhum.

    Casca fina sobre `membro_do_remetente`, e nao uma segunda varredura: a
    pergunta e a mesma e a resposta tem que vir do mesmo lugar.
    """
    membro = membro_do_remetente(remetente, membros)
    return membro.nick if membro is not None else None


_NAO_RESOLVIDO = object()


def autorizado_para(
    comando: Comando,
    remetente: dict,
    telefones: list[str],
    membros: Sequence[Membro] = (),
    *,
    membro: Membro | None | object = _NAO_RESOLVIDO,
) -> bool:
    """Quem mandou pode mandar ISTO?

    A ORDEM DESTAS DUAS PERGUNTAS E A DECISAO INTEIRA DA FRONTEIRA.

    O nivel de DONO (`CHATWOOT_TELEFONES_COMANDO`) e avaliado PRIMEIRO e e
    ADITIVO: quem esta nele continua alcancando TODO comando do enum, inclusive
    `JOIN` e `LEAVE`. O nivel de membro ACRESCENTA gente a uma superficie
    pequena; ele nunca TIRA nada de ninguem.

    Inverter esta ordem — ou restringir `JOIN` ao nivel de membro — quebra
    `test_toda_sintaxe_anunciada_volta_como_o_comando_certo`, que roda a tabela
    `_AJUDA` INTEIRA pelo caminho real de leitura usando o telefone de dono e
    sem `[[membro]]` nenhum configurado. Quando isso acontecer, o teste esta
    certo e o codigo esta errado: o dono do scanner nao pode deixar de alcancar
    um comando so porque aquele comando ganhou um segundo publico.

    O nivel de MEMBRO (`[[membro]]` no config.toml) so e consultado depois, e
    so para o que estiver em `COMANDOS_DE_MEMBRO`. Um party-mate nao alcanca
    `.corrigir` nem `.pegou`, que reescrevem a estatistica do `.loot/` — pasta
    que nunca e podada e nao tem backup. Era exatamente esse poder que por os
    quatro a oito telefones da party na allowlist de dono teria dado a todos
    eles, so para que pudessem dar `.join`.

    O `membro` por palavra-chave e a resposta JA RESOLVIDA de
    `membro_do_remetente`, e existe para `comandos_novos` nao perguntar duas
    vezes "quem e este telefone?" (uma aqui e outra para preencher o `nick`).
    O sentinela distingue "nao resolvi, procure voce" de "procurei e nao era
    membro" — um `None` default colapsaria os dois e faria a trava recusar todo
    party-mate em silencio. Sem o parametro, a funcao continua se virando
    sozinha com `membros`, que e como todo teste unitario a chama.
    """
    if autor_autorizado(remetente, telefones):
        return True
    if comando not in COMANDOS_DE_MEMBRO:
        return False
    if membro is _NAO_RESOLVIDO:
        membro = membro_do_remetente(remetente, membros)
    return membro is not None


def _forma_canonica(telefone: str | None) -> str:
    """O numero sem o nono digito brasileiro, para dizer se sao a MESMA pessoa.

    Nao substitui `telefone_equivalente` e nem serve para autorizar nada — ela
    responde outra pergunta. `telefone_equivalente` pergunta "estes dois casam
    pela regra que o scanner usa?"; esta pergunta "estes dois sao a mesma
    pessoa escrita de dois jeitos?".

    Celular brasileiro completo tem 13 digitos: 55 + DDD + 9 + os oito. A forma
    canonica joga fora as DUAS coisas que o mesmo numero ganha e perde ao ser
    escrito por gente diferente — o codigo de pais e o nono digito — e devolve
    `DDD + os oito`, que e o que sobra de invariante:

        +5544997077000 -> 4497077000
         554497077000  -> 4497077000
          44997077000  -> 4497077000

    O CODIGO DE PAIS PRECISA CAIR, e nao e refinamento. Sem isso,
    `5544999998888` e `44999998888` — o MESMO celular, um com +55 e outro sem —
    saem como formas diferentes, e `colisoes_de_telefone` reporta uma colisao
    que e pura redundancia. Isso passou a doer quando o par dono contra membro
    deixou de ser aviso e virou recusa de arranque: um usuario que escreveu o
    proprio numero das duas maneiras nao pode ficar sem scanner por causa
    disso.

    Nao substitui `telefone_equivalente` e nem autoriza nada: ela responde
    "estes dois sao a mesma pessoa escrita de dois jeitos?", e a outra responde
    "estes dois casam pela regra que o scanner usa?".
    """
    digitos = so_digitos(telefone)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    if len(digitos) == 11 and digitos[2] == "9":
        digitos = digitos[:2] + digitos[3:]
    return digitos


def _mesma_pessoa(a: str | None, b: str | None) -> bool:
    """Os dois textos sao o MESMO numero, so escrito diferente?

    IGUALDADE DA FORMA CANONICA, E NUNCA SUFIXO — e a diferenca e uma falha de
    seguranca, nao estilo.

    A versao anterior aceitava "um e sufixo do outro" e com isso calava
    exatamente o par que esta funcao existe para deixar visivel. Um numero
    curto e sufixo de meio mundo: com `CHATWOOT_TELEFONES_COMANDO=99998888`
    (sem DDD, sem +55) e um `[[membro]]` `+5544999998888`, o sufixo casava, a
    colisao era descartada como "redundancia", e o party-mate passava a
    alcancar `.corrigir` e `.pegou` sem uma linha no console. A supressao
    escondia a ESCALADA DE PRIVILEGIO enquanto ela acontecia.

    A supressao continua existindo e continua certa, mas so por PROVA: tirar o
    nono digito ja normaliza as duas formas que a base do WhatsApp carrega do
    mesmo numero (`+5544997077000` e `554497077000` viram o mesmo texto). O
    que ela nao pode mais fazer e adivinhar identidade por parentesco de
    sufixo — uma pergunta que a heuristica nunca respondeu.
    """
    ca, cb = _forma_canonica(a), _forma_canonica(b)
    return bool(ca) and ca == cb


ORIGEM_DONO = "dono"
ORIGEM_MEMBRO = "membro"


class ConfiguracaoPerigosa(Exception):
    """O scanner NAO sobe: a configuracao daria poder a quem nao deveria ter.

    Separada de `AgendaInvalida` de proposito. `AgendaInvalida` quer dizer "o
    config.toml nao faz sentido"; esta quer dizer "o config.toml faz sentido, e
    o sentido dele e perigoso". A primeira e um erro de digitacao; a segunda e
    uma escalada de privilegio, e o desfecho tem que ser o mesmo que o de uma
    trava de seguranca que falhou: parar.
    """


class Colisao(NamedTuple):
    """Um par de entradas configuradas que o scanner nao consegue distinguir.

    Carrega a ORIGEM dos dois lados porque o arranque trata os tres tipos de
    par com pesos diferentes. Sem a origem, quem le a lista teria que
    redescobrir de onde veio cada texto — um SEGUNDO ponto de decisao sobre a
    mesma pergunta, que e a forma como as duas travas deste modulo passariam a
    discordar em silencio.

    `escala_privilegio` e a unica pergunta que muda o desfecho do arranque:
    dono contra membro e a unica combinacao em que alguem GANHA poder.
    """

    primeiro: str
    segundo: str
    origem_do_primeiro: str
    origem_do_segundo: str

    @property
    def escala_privilegio(self) -> bool:
        return {self.origem_do_primeiro, self.origem_do_segundo} == {
            ORIGEM_DONO,
            ORIGEM_MEMBRO,
        }


def colisoes_de_telefone(
    telefones: list[str], membros: Sequence[Membro] = ()
) -> list[Colisao]:
    """Pares de entradas configuradas que o scanner nao consegue distinguir.

    O comentario do `DIGITOS_FINAIS_DO_TELEFONE` aceitou a colisao por escrito,
    e aceitou para um tamanho: "numa allowlist de duas a cinco pessoas isso e
    aceitavel". O `[[membro]]` acrescenta de quatro a oito telefones a mesma
    superficie comparada, e nesse tamanho a colisao deixa de ser teorica.

    SAO TRES TIPOS DE PAR, E SO UM DELES E PERIGOSO:

    - dono contra dono: dois numeros do mesmo nivel. Redundancia, nada muda.
    - membro contra membro: o `.join` de um pode ser creditado ao nick do
      outro. Errado, visivel, e ninguem ganha poder nenhum.
    - **dono contra membro: ESCALADA DE PRIVILEGIO, E SILENCIOSA.**
      `autorizado_para` pergunta pelo nivel de dono primeiro, entao aquele
      party-mate passa a alcancar `.corrigir` e `.pegou` — que reescrevem a
      estatistica do `.loot/` — sem que nada no sistema diga uma palavra.

    Funcao PURA e de ordem DETERMINISTICA: os telefones de dono na ordem do
    `.env`, depois os membros na ordem do config.toml, e os pares na ordem dos
    indices. Cada par sai com os dois textos COMO FORAM CONFIGURADOS, e nao
    normalizados, para o usuario achar as duas linhas nos arquivos dele.

    Devolve `Colisao`, e nao um par cru, porque a ORIGEM de cada lado e o que
    distingue o par inofensivo do par que derruba o arranque. Quem decide o
    que fazer com cada tipo e `__main__.montar_leitor_de_comandos`, e ele
    RECUSA A SUBIR no par dono contra membro — um `log.warning` num console
    que rola nao e mitigacao de escalada de privilegio.
    """
    entradas = [(str(t), ORIGEM_DONO) for t in telefones]
    entradas += [(m.telefone, ORIGEM_MEMBRO) for m in membros]

    pares: list[Colisao] = []
    for i, (primeiro, origem_do_primeiro) in enumerate(entradas):
        for segundo, origem_do_segundo in entradas[i + 1 :]:
            if not telefone_equivalente(primeiro, segundo):
                continue
            # O mesmo numero escrito de dois jeitos nao e colisao: e o usuario
            # tendo posto o proprio celular com e sem o 9, ou com e sem o +55.
            # A prova e IGUALDADE canonica — ver `_mesma_pessoa` e o defeito
            # de seguranca que a heuristica de sufixo escondia.
            if _mesma_pessoa(primeiro, segundo):
                continue
            pares.append(
                Colisao(primeiro, segundo, origem_do_primeiro, origem_do_segundo)
            )
    return pares


def sem_prefixo(palavra: str) -> str | None:
    """O que sobra depois do prefixo, ou None quando nao ha prefixo nenhum.

    O UNICO ponto de decisao sobre prefixo do parser. Com dois prefixos vivos,
    duas copias do `startswith` divergiriam no primeiro ajuste e o vocabulario
    fixo passaria a aceitar uma forma que a superficie dinamica recusa — em
    SILENCIO, que e o pior modo de falha desta trava.

    Os chamadores testam `is None`, nunca verdade: um prefixo SOZINHO devolve
    string vazia, que e um caso legitimo e morre sozinho mais adiante (nao casa
    vocabulario nem `_NICK_VALIDO`). Tratar "" como ausencia de prefixo daria o
    mesmo resultado hoje e esconderia a diferenca no dia em que nao der.
    """
    for prefixo in PREFIXOS:
        if palavra.startswith(prefixo):
            return palavra[len(prefixo) :]
    return None


def interpretar(texto: str | None) -> Comando | None:
    """Que comando este texto pede? None quando nao pede nenhum.

    Exige o prefixo. "vamos cancelar o silencio?" nao e comando; "/cancelar" e.
    A diferenca entre conversar sobre uma acao e pedir a acao tem que ser
    visivel no texto, senao o scanner age no meio de uma conversa.
    """
    if not texto:
        return None

    primeira = texto.strip().split()
    if not primeira:
        return None

    palavra = primeira[0]
    miolo_cru = sem_prefixo(palavra)
    if miolo_cru is None:
        return None

    # `/cancelar` e `/cancelar silencio` sao o mesmo pedido — juntamos as duas
    # primeiras palavras para aceitar as duas formas sem gramatica nenhuma.
    miolo = miolo_cru.lower()
    if len(primeira) > 1:
        junto = (miolo + primeira[1].lower()).replace("-", "").replace("_", "")
        if junto in _VOCABULARIO:
            return _VOCABULARIO[junto]

    return _VOCABULARIO.get(miolo.replace("-", "").replace("_", ""))


# O nome privado sobrevive porque os seis usos deste arquivo ja falam essa
# lingua. A DEFINICAO (e o comentario que explica o charset do L2 e o minimo
# de 2 caracteres) mudou para o `loot.py`, porque `interpretar_pegou` precisa
# dela e o `loot` nao pode importar `comandos` sem fechar um ciclo.
_NICK_VALIDO = NICK_VALIDO

# `.offline` e convencao humana do grupo — quem digita esta avisando GENTE,
# nao o bot. Excluido por nome para jamais virar consulta de nick, nem que
# um dia exista um personagem chamado Offline.
#
# D-05: a exclusao e AGNOSTICA DE PREFIXO, e vale para os dois. Com a barra o
# risco humano praticamente some (ninguem digita `/offline` para avisar
# gente), mas a forma antiga continua aceita, e tornar a protecao especifica
# de prefixo criaria uma DIVERGENCIA DE COMPORTAMENTO entre duas formas que
# devem ser a mesma coisa — o oposto exato de "os dois valem". O unico preco
# de manter e um personagem hipotetico chamado Offline, que o comentario
# acima ja tinha aceitado perder.
_PALAVRA_HUMANA = "offline"

# As palavras que, no lugar do nick, querem dizer "ninguem" — o `.loot-`
# escrito por extenso, para quem nao lembra que o hifen sozinho basta.
#
# O PRECO, ACEITO E DOCUMENTADO: um personagem chamado "Cancelar" (ou
# "Ninguem", "Nenhum", "Limpar") nao pode ser designado por `.loot-<nick>`.
# E barato perto da alternativa — `.loot-cancelar` DESIGNANDO um personagem
# inexistente chamado "Cancelar" e deixando a party sem jeito de desmarcar.
_PALAVRAS_DE_CANCELAMENTO = frozenset({"cancelar", "ninguem", "nenhum", "limpar"})


def interpretar_dinamico(
    texto: str | None, nicks_conhecidos: frozenset[str]
) -> tuple[Comando, str] | None:
    """Os comandos com argumento: `.loot-<nick>` e `.<nick>`.

    Olha a PRIMEIRA PALAVRA CRUA, com hifens — de proposito. `interpretar`
    remove hifens do miolo, e e por isso que `.loot-j4guar` passa ileso por
    ele; reaproveitar aquele miolo aqui perderia a fronteira entre o comando
    e o nick.

    Superficie dinamica CONTIDA: nick restrito a [A-Za-z0-9]{2,16}, consulta
    so de nick conhecido, vocabulario fixo com precedencia (garantida pelo
    chamador, que tenta `interpretar` primeiro) e `.offline` excluido por
    nome. Um `.palavra` arbitrario continua morrendo em silencio.
    """
    if not texto:
        return None

    palavras = texto.strip().split()
    if not palavras:
        return None

    primeira = palavras[0]
    crua = sem_prefixo(primeira)
    if crua is None:
        return None

    # `.loot-<nick>` e `.loot <nick>`: o comando e case-insensitive, o nick
    # e preservado como digitado.
    if crua.lower().startswith("loot-"):
        nick = crua[len("loot-") :]
        # A ORDEM E A COISA MAIS IMPORTANTE DESTE RAMO: o cancelamento vem
        # ANTES do `_NICK_VALIDO`, porque "cancelar" casa o charset de nick
        # e viraria uma designacao para um personagem que nao existe.
        if not nick or nick.lower() in _PALAVRAS_DE_CANCELAMENTO:
            return (Comando.LOOT_CANCELAR, "")
        if _NICK_VALIDO.fullmatch(nick):
            return (Comando.LOOT_DESIGNAR, nick)
        return None
    if crua.lower() == "loot":
        # Mesma ordem do ramo com hifen, pela mesma razao: sem isto,
        # `.loot cancelar` DESIGNARIA um personagem chamado "cancelar".
        if len(palavras) > 1 and palavras[1].lower() in _PALAVRAS_DE_CANCELAMENTO:
            return (Comando.LOOT_CANCELAR, "")
        if len(palavras) > 1 and _NICK_VALIDO.fullmatch(palavras[1]):
            return (Comando.LOOT_DESIGNAR, palavras[1])
        # D-02, E ISTO NAO E ESQUECIMENTO: `.loot` SOZINHO nao faz nada.
        # Comando sem argumento nao pode ser destrutivo — quem digita `.loot`
        # no meio de um farm quase sempre esta PERGUNTANDO de quem e a vez,
        # nao mandando apagar. Um dia alguem vai querer "consertar" esta
        # linha fazendo-a cancelar; nao consertem.
        return None

    # `.corrigir-<nick>`: troca o dono do ultimo loot ja consumado. Sem
    # palavras reservadas aqui — `.corrigir` nao tem forma destrutiva sem
    # argumento, entao nao existe a colisao que obrigou o
    # `_PALAVRAS_DE_CANCELAMENTO` a nascer.
    if crua.lower().startswith("corrigir-"):
        nick = crua[len("corrigir-") :]
        if _NICK_VALIDO.fullmatch(nick):
            return (Comando.LOOT_CORRIGIR, nick)
        return None
    if crua.lower() == "corrigir":
        if len(palavras) > 1 and _NICK_VALIDO.fullmatch(palavras[1]):
            return (Comando.LOOT_CORRIGIR, palavras[1])
        # O `return None` NAO e redundancia: sem ele o fluxo cai no ramo de
        # consulta logo abaixo, onde `_NICK_VALIDO` casa a palavra "corrigir"
        # e um nick homonimo transformaria o comando numa consulta.
        #
        # E este ramo inteiro existe porque tratar SO o hifen foi exatamente o
        # erro que fez `.loot cancelar` DESIGNAR um personagem chamado
        # "cancelar" na tarefa anterior. A forma de duas palavras nunca e
        # opcional num comando que mexe em estado duravel.
        return None

    # `.pegou-18:00 Korzis` faz o mesmo que `.pegou 18:00 Korzis`. As duas
    # formas existem porque a mao do usuario ja aprendeu `.loot-` e
    # `.corrigir-`, e porque tratar so uma delas foi exatamente o erro que fez
    # `.loot cancelar` DESIGNAR um personagem chamado "cancelar": a forma de
    # duas palavras nunca e opcional num comando que mexe em estado duravel.
    if crua.lower().startswith("pegou-"):
        argumento = " ".join([crua[len("pegou-") :], *palavras[1:]]).strip()
        if interpretar_pegou(argumento) is not None:
            return (Comando.LOOT_ATRIBUIR, argumento)
        return None

    # `.pegou <hora> <nick>`: registra o loot de um boss que JA PASSOU. Quem
    # decide se a gramatica esta certa e `interpretar_pegou`, la no `loot.py`
    # — uma gramatica so, que valida aqui e le no responder. Duas divergiriam
    # no primeiro ajuste e o comando passaria a aceitar o que nao executa.
    if crua.lower() == "pegou":
        argumento = " ".join(palavras[1:])
        if interpretar_pegou(argumento) is not None:
            return (Comando.LOOT_ATRIBUIR, argumento)
        # O `return None` NAO e redundancia, pela mesma razao do `.corrigir`
        # logo acima: sem ele o fluxo cai no ramo de consulta, onde
        # `_NICK_VALIDO` casa a palavra "pegou" e um personagem homonimo
        # transformaria o comando numa consulta dele.
        return None

    # `/batizar <apelido> <nick>` e `/batizar-<apelido> <nick>`, mais as duas
    # formas irmas com `nomear`. Dar nome a uma assinatura que o scanner
    # aprendeu sozinho e PERGUNTOU quem era.
    #
    # A GRAMATICA MORA NO `batismo.py`, E NAO AQUI. Precedente exato do
    # `.pegou`, com a razao que ja esta escrita nele: uma gramatica so, que
    # valida na interpretacao e le no responder. Duas divergiriam no primeiro
    # ajuste e o comando passaria a aceitar o que nao executa.
    #
    # UM LACO PARA AS QUATRO FORMAS, E NAO QUATRO RAMOS. As duas palavras sao
    # SINONIMOS exatos — nenhuma e abreviacao da outra e nenhuma alcanca nada
    # que a outra nao alcance —, entao dois ramos copiados divergiriam no
    # primeiro ajuste, que e a mesma falha que a gramatica unica acima evita.
    # Cada palavra continua tendo as duas formas (hifen e espaco), porque
    # tratar so o hifen foi exatamente o erro que fez `.loot cancelar`
    # DESIGNAR um personagem chamado "cancelar".
    #
    # AUDITORIA DE COLISAO com `_NICK_VALIDO` ([A-Za-z0-9]{2,16}), feita como o
    # comentario do topo do `_VOCABULARIO` manda:
    #
    #   batizar   7 letras   casa  -> "Batizar" perde o /<nick>
    #   nomear    6 letras   casa  -> "Nomear"  perde o /<nick>
    #
    # Nenhuma das duas colide com o roster real (Mostarda, Titander, Pirulito,
    # Welazkez) e nenhuma e nome de personagem plausivel. Preco aceito e
    # documentado, o mesmo ja pago por `desativarboss`.
    #
    # ESTES RAMOS FICAM ANTES do `.{nick}`, que continua sendo o ultimo.
    for _palavra_do_batismo in ("batizar", "nomear"):
        if crua.lower().startswith(f"{_palavra_do_batismo}-"):
            argumento = " ".join(
                [crua[len(_palavra_do_batismo) + 1 :], *palavras[1:]]
            ).strip()
            if interpretar_batismo(argumento) is not None:
                return (Comando.BATIZAR, argumento)
            return None
        if crua.lower() == _palavra_do_batismo:
            argumento = " ".join(palavras[1:])
            if interpretar_batismo(argumento) is not None:
                return (Comando.BATIZAR, argumento)
            # O `return None` NAO e redundancia, pela mesma razao do
            # `.corrigir` e do `.pegou` acima: sem ele o fluxo cai no ramo de
            # consulta logo abaixo, onde `_NICK_VALIDO` casa as palavras
            # "batizar" e "nomear", e um personagem homonimo transformaria o
            # comando numa consulta dele.
            return None

    # `/esquecer <apelido>`, `/esquecer-<apelido>` e as duas formas irmas com a
    # palavra do lote. Tirar do acervo uma assinatura que nunca deveria ter
    # entrado.
    #
    # A GRAMATICA MORA NO `esquecimento.py`, e nao aqui: precedente exato do
    # `.pegou` e do `/batizar`, com a razao ja escrita nos dois — uma gramatica
    # so, que valida na interpretacao e le no responder.
    #
    # UMA PALAVRA SO, e nao duas como `batizar`/`nomear`. Cada palavra
    # registrada num ramo destes e um personagem que deixa de ser consultavel
    # por `/<nick>`, e um comando que se digita uma vez por limpeza nao compra
    # sinonimo com esse dinheiro. A auditoria de colisao, feita como o
    # comentario do topo do `_VOCABULARIO` manda:
    #
    #   esquecer   8 letras   casa `_NICK_VALIDO`  -> "Esquecer" perde o /<nick>
    #
    # Nao colide com o roster real (Mostarda, Titander, Pirulito, Welazkez) e
    # nao e nome de personagem plausivel. Preco aceito e documentado, o mesmo
    # ja pago por `batizar` e por `desativarboss`.
    #
    # AS DUAS FORMAS (hifen e espaco) NAO SAO OPCIONAIS. Tratar so o hifen foi
    # exatamente o erro que fez `.loot cancelar` DESIGNAR um personagem chamado
    # "cancelar", e a forma de duas palavras nunca e opcional num comando que
    # mexe em estado duravel. Aqui ela mexe em estado duravel E destrutivo.
    #
    # ESTE RAMO FICA ANTES do `.{nick}`, que continua sendo o ultimo.
    if crua.lower().startswith("esquecer-"):
        argumento = " ".join(
            [crua[len("esquecer-") :], *palavras[1:]]
        ).strip()
        if interpretar_esquecimento(argumento) is not None:
            return (Comando.ESQUECER, argumento)
        return None
    if crua.lower() == "esquecer":
        argumento = " ".join(palavras[1:])
        if interpretar_esquecimento(argumento) is not None:
            return (Comando.ESQUECER, argumento)
        # O `return None` NAO e redundancia, pela mesma razao do `.corrigir`,
        # do `.pegou` e do `/batizar` acima: sem ele o fluxo cai no ramo de
        # consulta logo abaixo, onde `_NICK_VALIDO` casa a palavra "esquecer",
        # e um personagem homonimo transformaria o comando numa consulta dele.
        return None

    # `.{nick}` sozinho: o portao por nick conhecido e decisao do usuario —
    # sem ele o scanner responderia a qualquer `.palavra` do grupo.
    if len(palavras) == 1 and _NICK_VALIDO.fullmatch(crua):
        baixo = crua.lower()
        if baixo in _VOCABULARIO or baixo == _PALAVRA_HUMANA:
            return None
        if apelido(crua) in nicks_conhecidos:
            return (Comando.LOOT_CONSULTA, crua)
    return None


def comandos_novos(
    mensagens: list[dict],
    ja_obedecidos: set[str],
    telefones: list[str] | None = None,
    nicks_conhecidos: frozenset[str] = frozenset(),
    membros: Sequence[Membro] = (),
) -> list[MensagemDeComando]:
    """Filtra o que veio da API e devolve so o que deve ser obedecido.

    Funcao pura — recebe a resposta ja decodificada. E o que permite testar
    todas as travas sem rede e sem um Chatwoot de verdade.
    """
    achados: list[MensagemDeComando] = []
    for bruta in mensagens:
        # TRAVA 3: nunca obedecer as proprias mensagens.
        if bruta.get("message_type") != MESSAGE_TYPE_INCOMING:
            continue
        # Nota privada de agente nao e pedido de ninguem do grupo.
        if bruta.get("private"):
            continue

        identificador = bruta.get("id")
        if identificador is None:
            continue
        if chave_da_mensagem(identificador) in ja_obedecidos:
            continue

        # O vocabulario FIXO vem primeiro — precedencia explicita, para um
        # nick homonimo de comando jamais sombrear o comando.
        argumento = None
        comando = interpretar(bruta.get("content"))
        if comando is None:
            dinamico = interpretar_dinamico(bruta.get("content"), nicks_conhecidos)
            if dinamico is None:
                continue
            comando, argumento = dinamico

        # TRAVA 5: quem mandou pode mandar ISTO? Vale ate dentro de um grupo,
        # onde a allowlist de conversa sozinha liberaria todo mundo.
        #
        # A pergunta passou a ser por COMANDO, e nao mais so por pessoa, sem
        # precisar mudar de lugar: esta trava ja rodava DEPOIS da
        # interpretacao, entao o comando ja e conhecido neste ponto.
        remetente = bruta.get("sender") or {}
        # UMA pergunta so sobre "quem e este telefone?", e as duas respostas
        # derivadas do MESMO valor: a trava, logo abaixo, e o `nick` que vai
        # para a lista de presenca. Enquanto eram duas chamadas independentes,
        # um filtro futuro aplicado so numa delas produziria uma mensagem
        # autorizada entrando na lista com `nick=None` — e o bot responderia
        # "nao sei que nick por na lista" a alguem corretamente configurado.
        membro = membro_do_remetente(remetente, membros)
        if not autorizado_para(
            comando, remetente, telefones or [], membro=membro
        ):
            continue
        achados.append(
            MensagemDeComando(
                id=int(identificador),
                comando=comando,
                autor=remetente.get("name"),
                texto=str(bruta.get("content", "")),
                conversa=bruta.get("conversation_id"),
                argumento=argumento,
                # O nick sai do mapa `[[membro]]`, NUNCA do `sender.name` que
                # esta tres linhas acima alimentando o `autor`. Ver a docstring
                # de `Membro`: o nome do contato e escrito pelo dono do
                # telefone, e o nick do jogo nao.
                #
                # E sai do MESMO `membro` que a trava acima consultou, e nao de
                # uma segunda varredura.
                nick=membro.nick if membro is not None else None,
            )
        )

    achados.sort(key=lambda m: m.id)
    return achados


def chave_da_mensagem(identificador: int | str) -> str:
    """Chave duravel de 'ja obedeci esta mensagem'.

    Prefixo proprio para nao se confundir com os marcadores de aviso e de
    cancelamento, que dividem o mesmo diretorio.
    """
    return f"comando_{identificador}"


class LeitorDeComandos:
    """Puxa mensagens novas do Chatwoot, com cadencia.

    Cadencia porque isto e rede: a 1 Hz seriam 86 mil requisicoes por dia por
    instancia, para um comando que o usuario manda uma vez por semana. A
    latencia de alguns segundos e irrelevante para "cancele o silencio".
    """

    def __init__(
        self,
        url: str,
        conta: str,
        token: str,
        conversas: list[str],
        segundos_entre_leituras: float = 20.0,
        user_agent: str = "",
        telefones: list[str] | None = None,
        etiqueta: str = "",
        membros: Sequence[Membro] = (),
    ) -> None:
        self._url = url.rstrip("/")
        self._conta = conta
        self._token = token
        self._conversas = list(conversas)
        self._intervalo = segundos_entre_leituras
        self._user_agent = user_agent
        self.telefones = list(telefones or [])
        # Os party-mates do `[[membro]]`, guardados ao lado dos telefones de
        # dono porque os dois juntos SAO a resposta de "quem pode mandar no
        # scanner". Quem le esta classe precisa ver os dois niveis no mesmo
        # lugar, nunca um deles escondido noutro modulo.
        self.membros = list(membros)
        # Etiqueta que transforma uma conversa em canal de comando. Redescoberta
        # a cada leitura de proposito: e o que faz marcar/desmarcar no painel do
        # Chatwoot valer NA HORA, sem editar arquivo e sem reiniciar o scanner.
        self._etiqueta = etiqueta.strip().lower()
        self._ultima_leitura: float | None = None
        self.falhas = 0

    @property
    def ativo(self) -> bool:
        """Ha de onde ouvir? Por id fixo, ou por etiqueta."""
        return bool(self._conversas or self._etiqueta)

    @property
    def aberto_a_qualquer_um(self) -> bool:
        """Esta ouvindo sem restringir quem pode mandar?

        Nao e erro — e compatibilidade. Mas precisa aparecer no arranque: um
        scanner que obedece qualquer um nao pode ser um estado que se descobre
        por acidente.
        """
        return self.ativo and not self.telefones

    def vencido(self, agora: float) -> bool:
        return (
            self._ultima_leitura is None
            or agora - self._ultima_leitura >= self._intervalo
        )

    def ler(self, agora: float) -> list[dict]:
        """Mensagens cruas das conversas de comando. Vazio se nao venceu.

        NUNCA levanta. Uma falha de rede no caminho de ENTRADA nao pode
        derrubar o scanner — o trabalho dele e vigiar a party, e ouvir comando
        e um extra. As falhas sao contadas para o resumo de sessao.
        """
        # `ativo`, e nao `_conversas`: uma configuracao so por ETIQUETA nao tem
        # conversa fixa nenhuma, e olhar a lista errada aqui fazia o leitor
        # nunca ler nada — silenciosamente.
        if not self.ativo or not self.vencido(agora):
            return []
        self._ultima_leitura = agora

        alvos = list(self._conversas)
        if self._etiqueta:
            alvos.extend(c for c in self._por_etiqueta() if c not in alvos)

        tudo: list[dict] = []
        for conversa in alvos:
            try:
                # Carimba a origem: a resposta tem de sair onde a pergunta
                # chegou. A API devolve a mensagem sem dizer de qual conversa
                # ela veio quando pedimos conversa a conversa.
                for bruta in self._puxar(conversa):
                    bruta["conversation_id"] = str(conversa)
                    tudo.append(bruta)
            except Exception:  # noqa: BLE001 — ver docstring
                self.falhas += 1
        return tudo

    def _por_etiqueta(self) -> list[str]:
        """Conversas marcadas com a etiqueta configurada.

        Falha em silencio devolvendo vazio: se a listagem cair, o certo e ouvir
        MENOS, nunca mais. Uma falha de rede nao pode abrir canal nenhum.
        """
        try:
            dados = self._get("/conversations")
        except Exception:  # noqa: BLE001 — ver docstring
            self.falhas += 1
            return []

        bruto = dados.get("data", dados) if isinstance(dados, dict) else dados
        conversas = (
            bruto.get("payload", bruto) if isinstance(bruto, dict) else bruto or []
        )
        marcadas = []
        for conversa in conversas:
            etiquetas = conversa.get("labels") or []
            if any(str(e).strip().lower() == self._etiqueta for e in etiquetas):
                marcadas.append(str(conversa.get("id")))
        return marcadas

    def _get(self, caminho: str):
        alvo = f"{self._url}/api/v1/accounts/{self._conta}{caminho}"
        req = urllib.request.Request(alvo, method="GET")
        req.add_header("api_access_token", self._token)
        req.add_header("Accept", "application/json")
        if self._user_agent:
            req.add_header("User-Agent", self._user_agent)
        with urllib.request.urlopen(req, timeout=10) as resposta:
            return json.loads(resposta.read())

    def _puxar(self, conversa: str) -> list[dict]:
        dados = self._get(f"/conversations/{conversa}/messages")
        return dados.get("payload", []) if isinstance(dados, dict) else []
