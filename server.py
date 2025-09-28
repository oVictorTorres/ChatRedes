import socket 
import threading 

# Configurações do servidor
HOST = '127.0.0.1'  
PORT = 5000         

def handle_client(conn, addr):
    """
    Esta função lida com cada cliente conectado.
    Ela roda em uma thread separada para não bloquear o servidor.
    """
    print(f"[NOVA CONEXÃO] Cliente {addr} conectado.")

    conn.close()

def start_server():
    """
    Função principal que inicia o servidor.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.bind((HOST, PORT))

    server.listen(5)
    print(f"[ESCUTANDO] Servidor está escutando em {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ATIVO] Conexões ativas: {threading.active_count() - 1}")

if __name__ == "__main__":
    start_server()