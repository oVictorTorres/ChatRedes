import socket
import threading
import sqlite3

HOST = '127.0.0.1'
PORT = 5000

# Dicionário para armazenar usuários online e seus sockets
online_users = {}

# Sincronização para evitar problemas com threads
online_users_lock = threading.Lock()

def get_db_connection():
    conn = sqlite3.connect('chat_server.db')
    return conn

def handle_client(conn, addr):
    print(f"[NOVA CONEXÃO] Cliente {addr} conectado.")

    try:
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break

            parts = data.split('|')
            command = parts[0]

            if command == "REGISTER" and len(parts) == 3:
                # ... (lógica de registro, que você já tem) ...
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
            
            elif command == "LOGIN" and len(parts) == 3:
                username = parts[1]
                password = parts[2]
                conn_db = get_db_connection()
                cursor = conn_db.cursor()
                try:
                    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
                    user = cursor.fetchone()
                    if user:
                        with online_users_lock:
                            online_users[username] = conn
                        response = "LOGIN_OK|Login realizado com sucesso."
                        print(f"Usuário {username} logado.")
                    else:
                        response = "LOGIN_FALHA|Usuário ou senha inválidos."
                        print(f"Tentativa de login falhou: usuário ou senha inválidos.")
                finally:
                    conn_db.close()
                conn.sendall(response.encode('utf-8'))

            elif command == "MESSAGE" and len(parts) >= 3:
                sender = parts[1]
                receiver = parts[2]
                message = '|'.join(parts[3:])
                
                print(f"Mensagem de {sender} para {receiver}: {message}")
                
                with online_users_lock:
                    if receiver in online_users:
                        # Envia a mensagem para o destinatário online
                        recipient_conn = online_users[receiver]
                        recipient_conn.sendall(f"MESSAGE|{sender}|{message}".encode('utf-8'))
                        print(f"Mensagem enviada para {receiver}")
                    else:
                        # No futuro, aqui vai a lógica de mensagens offline
                        conn.sendall("ERRO|Destinatário offline.".encode('utf-8'))

    except (socket.error, sqlite3.Error) as e:
        print(f"Erro com o cliente {addr}: {e}")
    finally:
        # Quando o cliente se desconecta, remove-o da lista de online
        with online_users_lock:
            for username, user_conn in list(online_users.items()):
                if user_conn == conn:
                    del online_users[username]
                    print(f"Usuário {username} desconectado.")
                    break
        conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[ESCUTANDO] Servidor está escutando em {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ATIVO] Conexões ativas: {threading.active_count() - 1}")

if __name__ == "__main__":
    start_server()