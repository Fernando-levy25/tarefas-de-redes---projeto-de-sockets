"""Protocolo TR/1: objetos JSON UTF-8 delimitados por LF sobre TCP."""
import json

MAX_MENSAGEM = 32768  # bytes, sem o LF final
VERSAO = 1


class ErroProtocolo(Exception):
    pass


def enviar(sock, mensagem):
    dados = json.dumps(mensagem, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')).encode('utf-8')
    if len(dados) > MAX_MENSAGEM:
        raise ErroProtocolo('Mensagem excede 32768 bytes.')
    sock.sendall(dados + b'\n')


def receber(arquivo):
    # readline mantém os bytes restantes quando TCP agrupa várias mensagens.
    linha = arquivo.readline(MAX_MENSAGEM + 2)
    if not linha:
        return None  # EOF: o outro processo encerrou a conexão.
    if not linha.endswith(b'\n'):
        raise ErroProtocolo('Mensagem sem LF ou acima do limite.')
    if len(linha) - 1 > MAX_MENSAGEM:
        raise ErroProtocolo('Mensagem excede 32768 bytes.')
    try:
        objeto = json.loads(linha[:-1].decode('utf-8'),
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise ErroProtocolo('JSON ou UTF-8 inválido.') from exc
    if not isinstance(objeto, dict):
        raise ErroProtocolo('A mensagem deve ser um objeto JSON.')
    return objeto
