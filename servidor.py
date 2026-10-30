"""Servidor de tarefas compartilhadas; somente biblioteca padrão do Python."""
import argparse
import logging
import socket
import socketserver
import threading
from protocolo import ErroProtocolo, VERSAO, enviar, receber


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, endereco):
        super().__init__(endereco, Atendimento)
        self.trava = threading.Lock()
        self.tarefas = {}
        self.proximo_id = 1

    def executar(self, req):
        def erro(codigo, texto):
            return {'v': VERSAO, 'ok': False, 'erro': codigo, 'mensagem': texto}
        if type(req.get('v')) is not int or req['v'] != VERSAO:
            return erro('VERSAO_INVALIDA', 'Use v=1.')
        op = req.get('op')
        if not isinstance(op, str) or op not in {'PING', 'ADD', 'LIST', 'DONE', 'QUIT'}:
            return erro('OPERACAO_INVALIDA', 'Operação não reconhecida.')
        campos = {'v', 'op'} | ({'texto'} if op == 'ADD' else {'id'} if op == 'DONE' else set())
        if set(req) != campos:
            return erro('CAMPOS_INVALIDOS', 'Campos ausentes ou desconhecidos.')
        if op == 'PING':
            return {'v': 1, 'ok': True, 'mensagem': 'PONG'}
        if op == 'QUIT':
            return {'v': 1, 'ok': True, 'mensagem': 'Até logo.'}
        # A trava protege a lista e a atribuição de IDs entre clientes concorrentes.
        with self.trava:
            if op == 'ADD':
                texto = req['texto']
                if not isinstance(texto, str) or not 1 <= len(texto.strip()) <= 200:
                    return erro('TEXTO_INVALIDO', 'Texto deve ter de 1 a 200 caracteres úteis.')
                if len(self.tarefas) >= 20:
                    return erro('LIMITE_TAREFAS', 'Máximo de 20 tarefas por execução.')
                tarefa = {'id': self.proximo_id, 'texto': texto.strip(), 'concluida': False}
                self.tarefas[self.proximo_id] = tarefa
                self.proximo_id += 1
                return {'v': 1, 'ok': True, 'tarefa': tarefa.copy()}
            if op == 'LIST':
                # Até 20 textos de 200 caracteres: resposta UTF-8 cabe no limite.
                return {'v': 1, 'ok': True, 'tarefas': [t.copy() for t in self.tarefas.values()]}
            tid = req['id']
            if type(tid) is not int or tid <= 0:
                return erro('ID_INVALIDO', 'ID deve ser inteiro positivo.')
            if tid not in self.tarefas:
                return erro('NAO_ENCONTRADA', 'Tarefa inexistente.')
            self.tarefas[tid]['concluida'] = True
            return {'v': 1, 'ok': True, 'tarefa': self.tarefas[tid].copy()}


class Atendimento(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(120)
        logging.info('Conexão de %s:%s', *self.client_address)
        try:
            while True:
                req = receber(self.rfile)
                if req is None:
                    return
                resp = self.server.executar(req)
                enviar(self.request, resp)
                logging.info('op=%r ok=%s', req.get('op'), resp['ok'])
                if resp['ok'] and req.get('op') == 'QUIT':
                    return
        except ErroProtocolo as exc:
            try:
                enviar(self.request, {'v': 1, 'ok': False, 'erro': 'PROTOCOLO_INVALIDO',
                                      'mensagem': str(exc)})
            except OSError:
                pass
        except socket.timeout:
            logging.info('Cliente inativo por 120 segundos; conexão encerrada.')
        except OSError as exc:
            logging.info('Conexão encerrada: %s', exc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--porta', type=int, default=5000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    try:
        with Servidor((args.host, args.porta)) as servidor:
            logging.info('Escutando em %s:%s; Ctrl+C encerra.', *servidor.server_address)
            servidor.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor encerrado. Tarefas em memória foram descartadas.')
    except (OSError, OverflowError) as exc:
        parser.exit(1, f'Não foi possível iniciar o servidor: {exc}\n')


if __name__ == '__main__':
    main()
