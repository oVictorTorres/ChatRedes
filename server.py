import socket
import threading
import sqlite3
from datetime import datetime

HOST = '127.0.0.1'
PORT = 5000

# Dicionário para armazenar usuários online e seus sockets
online_users = {}

# Sincronização para evitar problemas com threads
online_users_lock = threading.Lock()

def get_db_connection():
    """Função para conectar ao banco de dados."""
    conn = sqlite3.connect('chat_server.db')
    return conn

def deliver_offline_messages(username, conn):
    """
    Entrega mensagens que estavam armazenadas para o usuário.
    """
    conn_db = get_db_connection()
    cursor = conn_db.cursor()

    try:
        cursor.execute("SELECT sender, message, timestamp FROM offline_messages WHERE receiver=?", (username,))
        messages = cursor.fetchall()
        
        if messages:
            print(f"Entregando {len(messages)} mensagens offline para {username}.")
            for sender, message, timestamp in messages:
                conn.sendall(f"MESSAGE|{sender}|{message}|{timestamp}".encode('utf-8'))
            
            # Deleta as mensagens do banco de dados após a entrega
            cursor.execute("DELETE FROM offline_messages WHERE receiver=?", (username,))
            conn_db.commit()
            print(f"Mensagens offline para {username} removidas do banco de dados.")

    except sqlite3.Error as e:
        print(f"Erro ao entregar mensagens offline: {e}")
    finally:
        if conn_db:
            conn_db.close()


def handle_client(conn, addr):
    """
    Função que lida com cada cliente em uma thread separada.
    """
    print(f"[NOVA CONEXÃO] Cliente {addr} conectado.")
    current_username = None

    try:
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break

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
                except sqlite3.IntegrityError:
                    response = "REGISTRO_FALHA|Nome de usuário já existe."
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
                        current_username = username
                        response = "LOGIN_OK|Login realizado com sucesso."
                        print(f"Usuário {username} logado.")
                        deliver_offline_messages(username, conn)
                    else:
                        response = "LOGIN_FALHA|Usuário ou senha inválidos."
                        print(f"Tentativa de login falhou: usuário ou senha inválidos.")
                finally:
                    conn_db.close()
                conn.sendall(response.encode('utf-8'))

            elif command == "MESSAGE" and len(parts) >= 3:
                receiver = parts[1]
                message = '|'.join(parts[2:])
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with online_users_lock:
                    if receiver in online_users:
                        # Envia a mensagem para o destinatário online
                        recipient_conn = online_users[receiver]
                        recipient_conn.sendall(f"MESSAGE|{current_username}|{message}|{timestamp}".encode('utf-8'))
                        print(f"Mensagem enviada de {current_username} para {receiver}")
                    else:
                        # Armazena a mensagem para destinatário offline
                        conn_db = get_db_connection()
                        cursor = conn_db.cursor()
                        try:
                            cursor.execute("INSERT INTO offline_messages (sender, receiver, timestamp, message) VALUES (?, ?, ?, ?)", (current_username, receiver, timestamp, message))
                            conn_db.commit()
                            conn.sendall("INFO|Mensagem armazenada, será entregue quando o usuário ficar online.".encode('utf-8'))
                            print(f"Mensagem de {current_username} para {receiver} armazenada.")
                        except sqlite3.Error as e:
                            print(f"Erro ao armazenar mensagem offline: {e}")
                            conn.sendall("ERRO|Falha ao armazenar mensagem.".encode('utf-8'))
                        finally:
                            if conn_db:
                                conn_db.close()

            elif command == "TYPING" and len(parts) == 2:
                receiver = parts[1]
                # Envia o evento de digitação para o destinatário se ele estiver online
                with online_users_lock:
                    if receiver in online_users:
                        recipient_conn = online_users[receiver]
                        recipient_conn.sendall(f"TYPING|{current_username}".encode('utf-8'))
                        print(f"Indicador 'digitando...' de {current_username} para {receiver}")

            elif command == "TYPING_STOP" and len(parts) == 2:
                receiver = parts[1]
                # Envia o evento de parada de digitação para o destinatário
                with online_users_lock:
                    if receiver in online_users:
                        recipient_conn = online_users[receiver]
                        recipient_conn.sendall(f"TYPING_STOP|{current_username}".encode('utf-8'))
                        print(f"Indicador 'digitando...' de {current_username} encerrado para {receiver}")
            
    except (socket.error, sqlite3.Error) as e:
        print(f"Erro com o cliente {addr}: {e}")
    finally:
        # Quando o cliente se desconecta, remove-o da lista de online
        with online_users_lock:
            if current_username in online_users:
                del online_users[current_username]
                print(f"Usuário {current_username} desconectado.")
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