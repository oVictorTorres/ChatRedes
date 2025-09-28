import socket
import threading
import sqlite3

HOST = '127.0.0.1'
PORT = 5000

# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect('chat_server.db')
    return conn

def handle_client(conn, addr):
    print(f"[NOVA CONEXÃO] Cliente {addr} conectado.")
    
    try:
        data = conn.recv(1024).decode('utf-8')
        if not data:
            return

        # Exemplo de como um cliente enviaria a solicitação de registro
        # Formato: "REGISTER|usuario|senha"
        parts = data.split('|')
        command = parts[0]

        if command == "REGISTER" and len(parts) == 3:
            username = parts[1]
            password = parts[2]
            
            conn_db = get_db_connection()
            cursor = conn_db.cursor()

            try:
                # Tenta inserir um novo usuário no banco de dados
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn_db.commit()
                response = f"REGISTRO_OK|Usuário {username} registrado com sucesso."
                print(f"Usuário {username} registrado.")
            except sqlite3.IntegrityError:
                # O nome de usuário já existe
                response = "REGISTRO_FALHA|Nome de usuário já existe."
                print(f"Tentativa de registro falhou: usuário {username} já existe.")
            finally:
                conn_db.close()
            
            conn.sendall(response.encode('utf-8'))

    except socket.error as e:
        print(f"Erro de socket: {e}")
    finally:
        conn.close()

def start_server():
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