import argparse
import json
import socket
from protocolo import ErroProtocolo, enviar, receber


def interpretar(linha):
    comando, _, argumento = linha.strip().partition(' ')
    comando = comando.lower()
    if comando == 'adicionar' and argumento.strip():
        return {'v': 1, 'op': 'ADD', 'texto': argumento.strip()}
    if comando == 'concluir':
        try:
            return {'v': 1, 'op': 'DONE', 'id': int(argumento)}
        except ValueError:
            raise ValueError('Use concluir seguido de um ID inteiro.') from None
    ops = {'listar': 'LIST', 'ping': 'PING', 'sair': 'QUIT'}
    if comando in ops and not argumento:
        return {'v': 1, 'op': ops[comando]}
    raise ValueError('Comandos: adicionar TEXTO | listar | concluir ID | ping | sair')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--porta', type=int, default=5000)
    args = parser.parse_args()
    try:
        with socket.create_connection((args.host, args.porta), timeout=5) as sock:
            sock.settimeout(5)
            with sock.makefile('rb') as arquivo:
                print('Conectado. Comandos: adicionar TEXTO | listar | concluir ID | ping | sair')
                while True:
                    try:
                        linha = input('> ')
                    except EOFError:
                        linha = 'sair'
                    try:
                        req = interpretar(linha)
                    except ValueError as exc:
                        print(exc)
                        continue
                    enviar(sock, req)
                    resp = receber(arquivo)
                    if resp is None:
                        print('O servidor encerrou a conexão.')
                        return
                    print(json.dumps(resp, ensure_ascii=False, indent=2))
                    if req['op'] == 'QUIT':
                        return
    except KeyboardInterrupt:
        print('\nCliente encerrado.')
    except (OSError, ErroProtocolo, OverflowError) as exc:
        print(f'Falha de comunicação: {exc}')
        print('Confira IP, porta e servidor. Se houve timeout após ADD, liste as tarefas antes de repetir.')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
