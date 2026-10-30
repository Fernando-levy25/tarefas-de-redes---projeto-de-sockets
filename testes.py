"""Testes de integração com sockets TCP reais em loopback."""
import concurrent.futures
import io
import socket
import threading
import unittest
from protocolo import ErroProtocolo, MAX_MENSAGEM, enviar, receber
from servidor import Servidor


class Integracao(unittest.TestCase):
    def setUp(self):
        self.servidor = Servidor(('127.0.0.1', 0))
        self.thread = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.thread.start()
        self.sock = socket.create_connection(self.servidor.server_address, timeout=2)
        self.arquivo = self.sock.makefile('rb')

    def tearDown(self):
        self.arquivo.close()
        self.sock.close()
        self.servidor.shutdown()
        self.servidor.server_close()
        self.thread.join()

    def trocar(self, op, **campos):
        enviar(self.sock, {'v': 1, 'op': op, **campos})
        return receber(self.arquivo)

    def test_fluxo_completo(self):
        self.assertEqual(self.trocar('PING')['mensagem'], 'PONG')
        self.assertEqual(self.trocar('LIST')['tarefas'], [])
        t = self.trocar('ADD', texto='Estudar redes e comunicação')['tarefa']
        self.assertFalse(t['concluida'])
        self.assertTrue(self.trocar('DONE', id=t['id'])['tarefa']['concluida'])
        self.assertEqual(len(self.trocar('LIST')['tarefas']), 1)
        self.assertTrue(self.trocar('QUIT')['ok'])
        self.assertIsNone(receber(self.arquivo))

    def test_validacao(self):
        for op, campos, codigo in [
            ('ADD', {'texto': ' '}, 'TEXTO_INVALIDO'),
            ('ADD', {'texto': 'x' * 201}, 'TEXTO_INVALIDO'),
            ('DONE', {'id': True}, 'ID_INVALIDO'),
            ('DONE', {'id': 999}, 'NAO_ENCONTRADA'),
            ('DELETE', {}, 'OPERACAO_INVALIDA'),
            ('PING', {'extra': 1}, 'CAMPOS_INVALIDOS')]:
            self.assertEqual(self.trocar(op, **campos)['erro'], codigo)
        enviar(self.sock, {'v': 2, 'op': 'PING'})
        self.assertEqual(receber(self.arquivo)['erro'], 'VERSAO_INVALIDA')
        self.assertTrue(self.trocar('PING')['ok'])

    def test_fragmentacao_e_agrupamento(self):
        # LF só chega no segundo envio; depois chegam duas mensagens juntas.
        self.sock.sendall(b'{"v":1,"op":')
        self.sock.sendall(b'"PING"}\n{"v":1,"op":"LIST"}\n')
        self.assertEqual(receber(self.arquivo)['mensagem'], 'PONG')
        self.assertEqual(receber(self.arquivo)['tarefas'], [])

    def test_json_invalido_fecha_conexao(self):
        self.sock.sendall(b'nao e json\n')
        self.assertEqual(receber(self.arquivo)['erro'], 'PROTOCOLO_INVALIDO')
        self.assertIsNone(receber(self.arquivo))

    def test_mensagem_grande(self):
        self.sock.sendall(b'x' * (MAX_MENSAGEM + 1) + b'\n')
        self.assertEqual(receber(self.arquivo)['erro'], 'PROTOCOLO_INVALIDO')

    def test_cliente_cai_servidor_continua(self):
        self.arquivo.close()
        self.sock.close()
        with socket.create_connection(self.servidor.server_address, timeout=2) as outro:
            enviar(outro, {'v': 1, 'op': 'PING'})
            with outro.makefile('rb') as f:
                self.assertEqual(receber(f)['mensagem'], 'PONG')

    def test_clientes_simultaneos(self):
        def adicionar(i):
            with socket.create_connection(self.servidor.server_address, timeout=2) as s:
                enviar(s, {'v': 1, 'op': 'ADD', 'texto': f'Tarefa {i}'})
                with s.makefile('rb') as f:
                    return receber(f)['tarefa']['id']
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            ids = list(pool.map(adicionar, range(10)))
        self.assertEqual(len(set(ids)), 10)
        self.assertEqual(len(self.trocar('LIST')['tarefas']), 10)

    def test_limite_e_utf8(self):
        for _ in range(20):
            self.assertTrue(self.trocar('ADD', texto='😀' * 200)['ok'])
        self.assertEqual(len(self.trocar('LIST')['tarefas']), 20)
        self.assertEqual(self.trocar('ADD', texto='Mais uma')['erro'], 'LIMITE_TAREFAS')


class Enquadramento(unittest.TestCase):
    def test_utf8_array_e_linha_incompleta(self):
        for dados in [b'\xff\n', b'[]\n', b'{"v":1}', b'{"v":NaN}\n']:
            with self.assertRaises(ErroProtocolo):
                receber(io.BytesIO(dados))


if __name__ == '__main__':
    unittest.main(verbosity=2)
