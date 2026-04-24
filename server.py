"""
server.py - Feature 1 & 2: Plaintext Chat Server

Handles multiple clients with broadcast and private messaging.
Messages are sent as plaintext over TCP.

Usage:
    python server.py
"""

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

def private_message(message, target, client_socket, username):
    try:
        with clients_lock:
            target_socket = clients.get(target, "n")

        if target_socket != "n":
            formatted = f"[PRIVATE] {username}: {message}"
            target_socket.send(formatted.encode("utf-8"))
        else:
            client_socket.send(f"User '{target}' not found.".encode("utf-8"))

    except ValueError:
        client_socket.send("Invalid private message format.".encode("utf-8"))

# Simple bool check for username in dictionary.
def unique_username(username):
    with clients_lock:
        if username in clients.keys():
            return False
        else:
            return True

def handle_client(client_socket, client_address):
    """
    Handle one client connection in its own thread.
    """

    # Receive the username as the first message. Server checks in dictionary for duplicates.
    while True:
        username = client_socket.recv(1024).decode("utf-8").strip()
        if not unique_username(username):
            client_socket.send("not available".encode("utf-8"))
        else:
            client_socket.send("available".encode("utf-8"))
            break

    with clients_lock:
        clients[username] = client_socket

    print(f"[NEW CONNECTION] {client_address} is {username}")

    # Notify all other clients that a new user joined
    join_msg = f"[SERVER] '{username}' has joined the chat."
    broadcast(join_msg.encode("utf-8"), client_socket)

    try:
        while True:
            message = client_socket.recv(1024)

            if not message:
                break

            decoded_message = message.decode("utf-8")

            if decoded_message.startswith("@"):
                target_name, private_msg = decoded_message.split(" ", 1)
                target_name = target_name[1:]

                private_message(private_msg, target_name, client_socket, username)
            elif decoded_message == "/users":
                formatted = f"[COMMAND] {username}: Users"
                print(formatted)

                private_message("User list:", username, client_socket, username)
                with clients_lock:
                    names = list(clients.keys())
                for name in names:
                    private_message(name, username, client_socket, username)
            else:
                print(f"[MESSAGE FROM {username}] {decoded_message}")

                # Add the sender's name and broadcast to all other clients
                broadcast(f"{username}: {decoded_message}".encode("utf-8"), client_socket)

    except Exception as e:
        print(f"[ERROR] Problem with {client_address}: {e}")

    finally:
        print(f"[DISCONNECTED] {username} disconnected.")
        with clients_lock:
            if username in clients:
                del clients[username]
        
        # Notify all other clients that this user left
        leave_msg = f"[SERVER] '{username}' has left the chat."
        broadcast(leave_msg.encode("utf-8"), client_socket)
        
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