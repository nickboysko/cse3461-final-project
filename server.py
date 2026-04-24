"""
server.py - Feature 1 & 2: Plaintext Chat Server

Handles multiple clients with broadcast and private messaging.
Messages are sent as plaintext over TCP.

Usage:
    python server.py
"""

import socket
import threading

HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5555

# Dictionary to track connected clients: username -> socket
clients = {}
clients_lock = threading.Lock()

def get_local_ip():
    """Extracts the actual local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # We don't actually connect to 10.255.255.255, 
        # but this forces the socket to figure out its routing IP.
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


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
    print(f"Tell your clients to connect to this IP: {get_local_ip()}")

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