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
    """Get the actual local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a dummy address to figure out which network interface
        # would be used for outgoing traffic
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

        for username, client in clients.items():
            if client != sender_socket:
                try:
                    client.send(message)
                except:
                    disconnected_clients.append(username)

        # Clean up clients that failed to receive the message
        for username in disconnected_clients:
            if username in clients:
                del clients[username]

"""
Privately send a message to a user.
message - the message to be sent
target - the user to receive. Function will find socket from dictionary
sender - sender's username to show where message comes from
"""
def private_message(message, target, sender):
    try:
        # Prevent sending messages to yourself
        if sender == target:
            with clients_lock:
                sender_socket = clients.get(sender)
            if sender_socket is not None:
                sender_socket.send("[SERVER] You cannot send a private message to yourself.".encode("utf-8"))
            return

        with clients_lock:
            sender_socket = clients.get(sender)
            target_socket = clients.get(target)

        if target_socket is not None:
            formatted = f"[PRIVATE] {sender}: {message}\n"
            target_socket.send(formatted.encode("utf-8"))
        else:
            # Only send error if sender is still connected
            if sender_socket is not None:
                sender_socket.send(f"User '{target}' not found.\n".encode("utf-8"))

    except Exception as e:
        print(f"Error in private_message: {e}")

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
    # Send currently online users to the new client before they pick a name
    with clients_lock:
        online = list(clients.keys())
    if online:
        client_socket.send(f"[SERVER] Currently online: {', '.join(online)}\n".encode("utf-8"))
    else:
        client_socket.send("[SERVER] No other users online yet.\n".encode("utf-8"))

    # Receive the username as the first message. Server checks in dictionary for duplicates.
    # .strip() will remove the \n if the client sent one.
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
    join_msg = f"[SERVER] '{username}' has joined the chat.\n"
    broadcast(join_msg.encode("utf-8"), client_socket)

    buffer = ""
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            # Add the new chunk of data to buffer
            buffer += data.decode("utf-8")

            # Process all messages in the buffer
            while "\n" in buffer:
                # Split at the first newline, so 
                # decoded_message gets the message, buffer gets whatever is left over.
                decoded_message, buffer = buffer.split("\n", 1)
                decoded_message = decoded_message.strip() 

                if not decoded_message: # Skip empty blank lines
                    continue

                if decoded_message.startswith("@"):
                    target_name, private_msg = decoded_message.split(" ", 1)
                    target_name = target_name[1:]

                    private_message(private_msg, target_name, username)

                elif decoded_message == "/users":
                    print(f"[COMMAND] {username}: Users")
                    with clients_lock:
                        names = list(clients.keys())
                    user_list = "[SERVER] Online users: " + ", ".join(names) + "\n"
                    client_socket.send(user_list.encode("utf-8"))

                else:
                    print(f"[MESSAGE FROM {username}] {decoded_message}")

                    # Add the sender's name and broadcast
                    broadcast(f"{username}: {decoded_message}\n".encode("utf-8"), client_socket)

    except Exception as e:
        print(f"[ERROR] Problem with {client_address}: {e}")

    finally:
        print(f"[DISCONNECTED] {username} disconnected.")
        with clients_lock:
            if username in clients:
                del clients[username]
        
        # Notify all other clients that this user left (Added \n)
        leave_msg = f"[SERVER] '{username}' has left the chat.\n"
        broadcast(leave_msg.encode("utf-8"), client_socket)
        
        client_socket.close()


def start_server():
    """
    Create the server socket, bind it, and listen for connections.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    server.settimeout(1.0)
    
    print(f"[LISTENING] Server is listening on {HOST}:{PORT}")
    print(f"Tell clients to connect to: {get_local_ip()}")
    # Added logic to handle Ctrl-C
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