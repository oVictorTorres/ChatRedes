import socket
import threading
import sqlite3

HOST = '127.0.0.1'
PORT = 5000

def get_db_connection():
    """Função para conectar ao banco de dados."""
    conn = sqlite3.connect('chat_server.db')
    return conn

def handle_client(conn, addr):
    """
    Função que lida com cada cliente em uma thread separada.
    Agora lida com comandos de REGISTRO e LOGIN.
    """
    print(f"[NOVA CONEXÃO] Cliente {addr} conectado.")
    
    try:
        data = conn.recv(1024).decode('utf-8')
        if not data:
            return

        parts = data.split('|')
        command = parts[0]

        if command == "REGISTER" and len(parts) == 3:
            username = parts[1]
            password = parts[2]
            
            conn_db = get_db_connection()
            cursor = conn_db.cursor()

            try:
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn_db.commit()
                response = f"REGISTRO_OK|Usuário {username} registrado com sucesso."
                print(f"Usuário {username} registrado.")
            except sqlite3.IntegrityError:
                response = "REGISTRO_FALHA|Nome de usuário já existe."
                print(f"Tentativa de registro falhou: usuário {username} já existe.")
            finally:
                conn_db.close()
            
            conn.sendall(response.encode('utf-8'))

        # Lógica para o login
        elif command == "LOGIN" and len(parts) == 3:
            username = parts[1]
            password = parts[2]

            conn_db = get_db_connection()
            cursor = conn_db.cursor()

            try:
                cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
                user = cursor.fetchone()

                if user:
                    response = "LOGIN_OK|Login realizado com sucesso."
                    print(f"Usuário {username} logado.")
                else:
                    response = "LOGIN_FALHA|Usuário ou senha inválidos."
                    print(f"Tentativa de login falhou: usuário ou senha inválidos.")
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