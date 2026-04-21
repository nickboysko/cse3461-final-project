import socket
import threading

HOST = "127.0.0.1"
PORT = 5555

# List to store all connected client sockets
clients = []
clients_lock = threading.Lock()


def broadcast(message, sender_socket):
    """
    Send a message to every connected client except the sender.
    """
    with clients_lock:
        disconnected_clients = []

        for client in clients:
            if client != sender_socket:
                try:
                    client.send(message)
                except:
                    disconnected_clients.append(client)

        # Remove any clients that disconnected during broadcast
        for client in disconnected_clients:
            if client in clients:
                clients.remove(client)
                client.close()


def handle_client(client_socket, client_address):
    """
    Handle communication for one client.
    Runs in its own thread.
    """
    print(f"[NEW CONNECTION] {client_address} connected.")

    try:
        while True:
            message = client_socket.recv(1024)

            if not message:
                break

            decoded_message = message.decode("utf-8")
            print(f"[MESSAGE FROM {client_address}] {decoded_message}")

            # Send message to all other clients
            broadcast(message, client_socket)

    except Exception as e:
        print(f"[ERROR] Problem with {client_address}: {e}")

    finally:
        print(f"[DISCONNECTED] {client_address} disconnected.")
        with clients_lock:
            if client_socket in clients:
                clients.remove(client_socket)
        client_socket.close()


def start_server():
    """
    Create the server socket, bind it, and listen for connections.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

    while True:
        client_socket, client_address = server.accept()

        with clients_lock:
            clients.append(client_socket)

        thread = threading.Thread(
            target=handle_client,
            args=(client_socket, client_address)
        )
        thread.start()

        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")


if __name__ == "__main__":
    start_server()