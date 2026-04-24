"""
server.py - Feature 1 & 2: Plaintext Chat Server

Handles multiple clients with broadcast and private messaging.
Messages are sent as plaintext over TCP.

Usage:
    python server.py
"""

from http import server
import socket
import threading

HOST = "127.0.0.1"
PORT = 5555

# Dictionary to track connected clients: username -> socket
clients = {}
clients_lock = threading.Lock()


def broadcast(message, sender_socket):
    """
    Send a message to all clients except the sender.
    """
    with clients_lock:
        disconnected_clients = []

        for client in clients.values():
            if client != sender_socket:
                try:
                    client.send(message)
                except:
                    disconnected_clients.append(client)

        # Clean up clients that failed to receive the message
        for client in disconnected_clients:
            if client in clients:
                del clients[client]


def handle_client(client_socket, client_address):
    """
    Handle one client connection in its own thread.
    """

    # Receive the username as the first message
    username = client_socket.recv(1024).decode("utf-8").strip()

    with clients_lock:
        clients[username] = client_socket

    print(f"[NEW CONNECTION] {client_address} is {username}")

    try:
        while True:
            message = client_socket.recv(1024)

            if not message:
                break

            decoded_message = message.decode("utf-8")

            if decoded_message.startswith("@"):
                try:
                    target_name, private_msg = decoded_message.split(" ", 1)
                    target_name = target_name[1:]

                    with clients_lock:
                        target_socket = clients.get(target_name, "n")

                    if target_socket != "n":
                        formatted = f"[PRIVATE] {username}: {private_msg}"
                        target_socket.send(formatted.encode("utf-8"))
                    else:
                        client_socket.send(f"User '{target_name}' not found.".encode("utf-8"))

                except ValueError:
                    client_socket.send("Invalid private message format.".encode("utf-8"))
                continue

            print(f"[MESSAGE FROM {username}] {decoded_message}")

            # Send message to all other clients
            broadcast(message, client_socket)

    except Exception as e:
        print(f"[ERROR] Problem with {client_address}: {e}")

    finally:
        print(f"[DISCONNECTED] {username} disconnected.")
        with clients_lock:
            if username in clients:
                del clients[username]
        client_socket.close()


def start_server():
    """
    Create the server socket, bind it, and listen for connections.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    server.settimeout(1.0)

    print(f"[LISTENING] Server is listening on {HOST}:{PORT}")
    # Added logic to handle Crtl-C
    try:
        while True:
            try:
                client_socket, client_address = server.accept()
            except socket.timeout:
                continue

            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address)
            )
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()