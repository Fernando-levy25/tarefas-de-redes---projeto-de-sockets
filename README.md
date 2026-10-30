# Tarefas em Rede — aplicação com sockets TCP

**Disciplina:** Fundamentos de Redes de Computadores  
**Atividade:** Desenvolvimento de Aplicação em Rede utilizando Sockets  
**Integrantes:**

- Matheus Wallace
- João Pedro Veras
- Fernando Levy

## Descrição e problema

Uma equipe precisa compartilhar pequenas tarefas entre computadores de uma rede local. Esta aplicação permite adicionar, listar e concluir tarefas mantidas em um servidor central. Cada integrante executa um cliente de terminal e consulta o mesmo estado. Não é necessário instalar bibliotecas externas.

O escopo é didático: até 20 tarefas por execução, textos de até 200 caracteres após remover espaços nas extremidades. As tarefas ficam **somente em memória**; reiniciar o servidor apaga a lista. Não há autenticação nem criptografia. Execute em ambiente de laboratório ou rede local confiável, sem expor a porta à Internet.

## Arquitetura

- `cliente.py`: processo cliente; abre conexão com `socket.create_connection`, que cria um socket TCP IPv4/IPv6 conforme a resolução do endereço. O servidor deste projeto aceita IPv4.
- `servidor.py`: processo servidor TCP IPv4 com `socketserver.ThreadingTCPServer`, da biblioteca padrão. Essa classe usa sockets e realiza bind, listen e accept; cada conexão é atendida em uma thread.
- `protocolo.py`: serialização, envio com `sendall`, leitura delimitada e validação de mensagens.
- O servidor centraliza as tarefas; uma trava protege as alterações concorrentes e a atribuição de IDs.
- Não há comunicação direta entre clientes. Cada resposta corresponde à requisição anterior na mesma conexão. O cliente aguarda a resposta antes de enviar a próxima operação.

Diagrama: [docs/arquitetura.svg](docs/arquitetura.svg). Fonte editável: [docs/arquitetura.mmd](docs/arquitetura.mmd).

## Transporte: TCP e justificativa

As operações precisam chegar completas, na ordem e sem duplicações de bytes dentro da conexão. TCP oferece fluxo confiável e ordenado, controle de fluxo e controle de congestionamento. Perder um ADD ou receber uma lista incompleta prejudicaria o estado compartilhado; a pequena latência adicional é aceitável.

TCP não preserva fronteiras entre mensagens: usamos JSON UTF-8 terminado em LF para defini-las. `sendall` envia todos os bytes ou sinaliza erro; isso não prova que a operação foi executada no servidor. Se a conexão cair depois de ADD e antes da resposta, o cliente não sabe se a tarefa foi criada: deve reconectar e listar antes de tentar novamente. Não há repetição automática de requisições.

Com UDP, datagramas poderiam se perder, duplicar ou chegar fora de ordem. Seria necessário implementar IDs de requisição, confirmação, timeout, repetição e deduplicação, além de respeitar o tamanho dos datagramas e evitar fragmentação IP. Essa complexidade não traz benefício para este projeto. TCP também não garante disponibilidade nem persistência após reiniciar o processo.

## Endereço IP e porta

| Parâmetro | Padrão | Função |
|---|---|---|
| IP do servidor | `127.0.0.1` | Comunicação no mesmo computador (loopback) |
| Porta TCP | `5000` | Serviço de tarefas |
| Escuta em rede local | `--host 0.0.0.0` | Escuta em todas as interfaces IPv4 |
| IP no cliente remoto | IPv4 real do servidor | Exemplo ilustrativo: `192.168.1.10` |

`0.0.0.0` é endereço de escuta; o cliente deve usar o IP real do servidor. A porta de origem do cliente é normalmente escolhida pelo sistema operacional. Ambos os computadores precisam ter conectividade e a porta TCP deve ser permitida pelo firewall.

## Execução

Requisito: Python 3.9 ou superior. Não é necessário `pip install`. No Linux, use `python3`; no Windows, pode usar `py -3` no lugar de `python3`.

Extraia o ZIP e abra um terminal **dentro de `tarefas_rede`**.

**Terminal 1 — servidor:**

```bash
python3 servidor.py
```

**Terminal 2 — cliente:**

```bash
python3 cliente.py
```

Digite, um comando por vez:

```text
ping
adicionar Preparar a apresentação de redes
listar
concluir 1
listar
sair
```

Abra outro cliente em um terceiro terminal para verificar que ambos consultam a mesma lista. `sair` encerra só o cliente; `Ctrl+C` no servidor encerra o serviço e descarta as tarefas.

**Em dois computadores da mesma rede:**

```bash
# No computador servidor:
python3 servidor.py --host 0.0.0.0 --porta 5000
# No cliente; substitua pelo IPv4 real do computador servidor:
python3 cliente.py --host 192.168.1.10 --porta 5000
```

No Linux, `ip -4 addr` permite consultar os endereços locais; escolha o da interface da rede compartilhada, não loopback nem interfaces de contêiner. No Windows, use `ipconfig`.

## Protocolo próprio da aplicação — TR/1

TR/1 significa Tarefas em Rede, versão 1. JSON é a representação; os campos, as operações, as respostas e as regras de enquadramento abaixo constituem o protocolo próprio.

- Cada mensagem é um objeto JSON codificado em UTF-8, seguido do byte LF (`0x0A`).
- Limite: **32768 bytes sem contar o LF**. A leitura limitada evita crescimento ilimitado do buffer.
- Quebras de linha internas de strings são escapadas pelo JSON; não encerram o quadro.
- Uma conexão aceita várias operações. Não é preciso reconectar a cada mensagem.
- A versão `v` é obrigatória e deve ser o inteiro `1`.
- Requisições contêm exatamente os campos de cada operação; campos extras são rejeitados.
- Respostas sempre contêm `v` e `ok`. Sucesso traz `mensagem`, `tarefa` ou `tarefas`; falha traz `erro` e `mensagem`.
- Cada tarefa possui `id` inteiro positivo, `texto` e `concluida` booleano. IDs são únicos na execução do servidor.
- Após `QUIT` válido, o servidor responde e fecha a conexão. EOF também encerra o atendimento.

| Operação | Requisição JSON, antes do LF | Conteúdo da resposta bem-sucedida |
|---|---|---|
| PING | `{"v":1,"op":"PING"}` | `{"v":1,"ok":true,"mensagem":"PONG"}` |
| ADD | `{"v":1,"op":"ADD","texto":"Estudar redes"}` | `{"v":1,"ok":true,"tarefa":{"id":1,"texto":"Estudar redes","concluida":false}}` |
| LIST | `{"v":1,"op":"LIST"}` | `{"v":1,"ok":true,"tarefas":[{"id":1,"texto":"Estudar redes","concluida":false}]}` |
| DONE | `{"v":1,"op":"DONE","id":1}` | `{"v":1,"ok":true,"tarefa":{"id":1,"texto":"Estudar redes","concluida":true}}` |
| QUIT | `{"v":1,"op":"QUIT"}` | `{"v":1,"ok":true,"mensagem":"Até logo."}` |

Exemplo de erro: `{"v":1,"ok":false,"erro":"NAO_ENCONTRADA","mensagem":"Tarefa inexistente."}` seguido de LF. LIST retorna um vetor vazio quando não há tarefas; DONE repetido mantém a tarefa concluída.

## Situações de erro e tratamento

| Situação | Tratamento |
|---|---|
| Versão diferente, ausente ou de tipo incorreto | `VERSAO_INVALIDA`; mantém a conexão |
| Operação desconhecida ou tipo inválido | `OPERACAO_INVALIDA`; mantém a conexão |
| Campo ausente ou extra | `CAMPOS_INVALIDOS`; mantém a conexão |
| Texto vazio, tipo inválido ou acima de 200 caracteres úteis | `TEXTO_INVALIDO` |
| Lista já tem 20 tarefas | `LIMITE_TAREFAS` |
| ID não inteiro positivo, inclusive booleano | `ID_INVALIDO` |
| ID não cadastrado | `NAO_ENCONTRADA` |
| JSON/UTF-8 inválido, objeto inválido ou mensagem excessiva | `PROTOCOLO_INVALIDO`, quando possível, seguido de fechamento |
| EOF no meio de uma mensagem | Tenta responder erro de protocolo e encerra; não executa mensagem incompleta |
| Cliente inativo por 120 s, inclusive durante mensagem parcial | Servidor registra timeout e fecha a conexão |
| Servidor ausente, IP/porta incorreto ou DNS indisponível | Cliente informa falha e encerra com código 1 |
| Conexão ou resposta demora mais de 5 s | Cliente informa falha, fecha a conexão e orienta verificar estado antes de repetir ADD |
| Cliente desconecta abruptamente | Atendimento termina; outros clientes continuam |
| Porta ocupada ou endereço de escuta inválido | Servidor informa que não pôde iniciar e encerra com código 1 |
| Comando de terminal incorreto | Ajuda local; nenhuma mensagem é enviada |

O timeout do socket é por operação bloqueante de E/S, não um prazo total da sessão. O servidor é didático: não limita o número total de threads e não implementa proteção contra clientes maliciosos.

## Testes e evidências

```bash
python3 testes.py
```

São nove testes automatizados com sockets locais reais: fluxo completo; validação de campos; mensagens fragmentadas/agrupadas; JSON inválido; limite de bytes; desconexão de cliente; concorrência; limite de tarefas e Unicode; UTF-8, formato e fim de quadro. Resultado da execução: [evidencias/testes.txt](evidencias/testes.txt).

O teste reserva uma porta livre automaticamente e não exige executar o servidor manualmente. O registro [evidencias/demonstracao.txt](evidencias/demonstracao.txt) mostra uma execução real do servidor e cliente de terminal em processos separados.

**Captura Wireshark ainda necessária:** este ambiente não disponibiliza Wireshark e bloqueia sockets de captura de pacotes. Os registros de testes e demonstração não substituem uma captura. Siga [docs/wireshark.md](docs/wireshark.md), salve `evidencias/trafego.pcapng` e as imagens solicitadas antes de entregar. Nenhum pacote ou screenshot foi fabricado.

## Documentação e apresentação

- [docs/respostas.md](docs/respostas.md): respostas diretas às dez questões do enunciado.
- [docs/apresentacao.md](docs/apresentacao.md): roteiro de até 10 minutos e perguntas conceituais.
- [docs/checklist.md](docs/checklist.md): mapa dos requisitos e pendências reais.

## Referência do trabalho

Enunciado fornecido: “ATIVIDADE AVALIATIVA — Desenvolvimento de Aplicação em Rede utilizando Sockets”, Fundamentos de Redes de Computadores. A proposta se relaciona à comunicação entre processos da camada de aplicação e à escolha do transporte estudadas no capítulo 2 de Kurose e Ross, indicado no enunciado. Não foram atribuídas páginas nem citações literais ao livro.
# tarefas-de-redes---projeto-de-sockets
# tarefas-de-redes---projeto-de-sockets
