# Captura e análise no Wireshark

## Estado da evidência

A captura ainda precisa ser realizada pela equipe. No ambiente de desenvolvimento, Wireshark/tshark/dumpcap não estavam disponíveis, e a tentativa de abrir um socket de captura em loopback retornou `Operation not permitted`. Os arquivos `testes.txt` e `demonstracao.txt` são registros reais da aplicação, mas não são capturas de rede.

## Capturar no próprio computador

1. Abra o Wireshark com permissão de captura configurada no sistema. No Windows, a captura de loopback depende do suporte do Npcap instalado com o Wireshark.
2. Escolha `lo` no Linux ou a interface de loopback no Windows. Em dois computadores, escolha a interface Ethernet/Wi-Fi usada na comunicação.
3. Configure o **filtro de captura** `tcp port 5000` e comece a capturar **antes** de abrir o cliente. Se mudar a porta, ajuste o filtro.
4. Abra `python3 servidor.py` em um terminal e `python3 cliente.py` em outro, dentro da pasta do projeto.
5. Digite `ping`, `adicionar Preparar apresentação`, `listar`, `concluir 1`, `listar` e `sair`, um comando por vez. Use servidor recém-iniciado para garantir ID 1.
6. Pare a captura e salve em `evidencias/trafego.pcapng`.
7. Use o **filtro de exibição** `tcp.port == 5000`. Se houver várias conexões, selecione um pacote do cliente e use “Follow” > “TCP Stream” para isolar a conversa.

## O que analisar e registrar

| Evidência | Como localizar | O que explicar |
|---|---|---|
| Abertura TCP | `tcp.port == 5000 && tcp.flags.syn == 1`, depois inspecione também o ACK seguinte | SYN, SYN/ACK e ACK estabelecem a conexão; anote IPs e portas reais |
| Dados da aplicação | `tcp.port == 5000 && tcp.len > 0` | JSON com versão, operação e LF; compare a solicitação e a resposta |
| Fluxo remontado | Follow > TCP Stream | Operações PING, ADD, LIST, DONE e QUIT; direção de cada mensagem |
| Encerramento | `tcp.port == 5000 && (tcp.flags.fin == 1 || tcp.flags.reset == 1)` | QUIT é mensagem de aplicação; FIN pertence ao TCP. RST indica interrupção, se ocorrer |
| Sequência e confirmação | Selecione pacote TCP e expanda Transmission Control Protocol | Sequence Number, Acknowledgment Number e tamanho do payload |

O Wireshark pode mostrar o protocolo como TCP; não existe um dissector instalado para TR/1. O JSON continua visível nos bytes e no fluxo remontado. Um pacote TCP não equivale obrigatoriamente a uma mensagem: o protocolo depende do LF, não do tamanho dos segmentos.

No loopback, checksums podem aparecer não verificados ou com avisos associados ao mecanismo de captura/offloading. Não atribua esses avisos a uma falha do JSON sem examinar o contexto. Também não espere observar perdas ou retransmissões em toda execução.

## Arquivos a adicionar à entrega

- `evidencias/trafego.pcapng`: captura original.
- `evidencias/01_conexao.png`: lista de pacotes mostrando handshake e colunas de IP/porta.
- `evidencias/02_fluxo.png`: Follow TCP Stream com requisições e respostas.
- `evidencias/03_encerramento.png`: pacotes de encerramento.
- `evidencias/analise.md`: preencha o modelo abaixo com números reais da sua captura.

```text
Data/hora da captura:
Interface:
IP e porta do cliente:
IP e porta do servidor:
Quadros do SYN, SYN/ACK e ACK:
Quadro(s) contendo ADD e sua resposta:
ID e texto da tarefa observados:
Quadros do encerramento:
Observação sobre segmentação/agrupamento:
Conclusão: como a captura confirma a comunicação TR/1 sobre TCP?
```

Para mostrar tratamento de erro na apresentação, use `concluir 999` e observe `NAO_ENCONTRADA`. Essa operação não deve derrubar a conexão. Gere uma nova captura se desejar incluir esse caso. Evite capturar outros serviços ou usar dados pessoais nas tarefas.
