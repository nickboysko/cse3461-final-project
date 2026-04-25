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
    buffer = ""
    while True:
        try:
            chunk = client_socket.recv(1024).decode("utf-8")
            if not chunk:
                print("Disconnected from server.")
                break
            
            buffer += chunk
            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)
                print(message)
        except:
            print("Connection to server lost.")
            break


def start_client():
    """Main client loop that connects and handles user input."""
    # Ask for the server IP, or default to localhost
    server_ip = input("Enter server IP (press Enter for localhost): ").strip()
    if not server_ip:
        server_ip = "127.0.0.1"
        
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((server_ip, PORT))

    # Check if the server sent an online users notice before we pick a name
    first_msg = client.recv(1024).decode("utf-8").strip()
    if first_msg:
        print(f"\n{first_msg}")

    # Send username to server, server will check if name is available
    while True:
        name = input("Enter your display name: ")
        client.send(name.encode("utf-8"))
        verification = client.recv(1024).decode("utf-8").strip()
        if verification != "available":
            print("Username already taken. Please try again.")
        else:
            break


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
            if message == "/quit":
                print("Quitting...")
                return
            client.send((message + "\n").encode("utf-8"))
    except KeyboardInterrupt:
        print("\nClosing connection...")
    finally:
        client.close()


if __name__ == "__main__":
    start_client()