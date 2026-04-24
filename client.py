"""
client.py - Feature 1 & 2: Plaintext Chat Client

Connects to the plaintext chat server and sends/receives messages.
Supports broadcast messages and private messaging with @username syntax.

Usage:
    python client.py
"""

import socket
import threading

HOST = "127.0.0.1"
PORT = 5555


def receive_messages(client_socket):
    """Background thread that listens for incoming messages."""
    while True:
        try:
            message = client_socket.recv(1024)
            if not message:
                print("Disconnected from server.")
                break

            # Display received message
            print("\n" + message.decode("utf-8"))
        except:
            print("Connection to server lost.")
            break


def start_client():
    """Main client loop that connects and handles user input."""
    # Ask for the IP, but default to localhost if they just press Enter
    server_ip = input("Enter server IP (press Enter for localhost): ").strip()
    if not server_ip:
        server_ip = "127.0.0.1"
        
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((server_ip, PORT))

    # Send username to server
    name = input("Enter your display name: ")
    client.send(name.encode("utf-8"))
    print(f"Connected to server at {server_ip}:{PORT}")
    print(f"Local socket info: {client.getsockname()}")

    # Start background thread to receive messages
    receive_thread = threading.Thread(
        target=receive_messages,
        args=(client,),
        daemon=True
    )
    receive_thread.start()

    try:
        # Main loop: get user input and send to server
        while True:
            message = input()
            client.send(message.encode("utf-8"))
    except KeyboardInterrupt:
        print("\nClosing connection...")
    finally:
        client.close()


if __name__ == "__main__":
    start_client()