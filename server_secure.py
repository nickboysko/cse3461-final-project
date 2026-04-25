"""
server_secure.py - Feature 3: AES-256-CBC Encrypted Chat Server

Builds on the Feature 1 and 2 server by adding AES-256-CBC encryption
to the transport layer. This way all messages traveling over the network
are encrypted instead of sent as plaintext.

What server_secure.py does (with AI assistance):
1. Every TCP frame is length-prefixed (4 bytes) so the receiver can
   read exactly one AES frame at a time without getting confused by
   partial reads.
2. The server decrypts each incoming frame to look at the content
   (needed to detect @username private-message routing).
3. The server re-encrypts with a fresh IV before forwarding to other
   clients so each hop on the wire has different ciphertext.
4. We print encryption metrics (latency, size overhead) when a client
   disconnects to see how much impact this all has on performance.

Run alongside client_secure.py. The broadcast and private messaging
features from 1 and 2 still work the same, but the data
moves over the network differently.

Usage:
    python server_secure.py
"""

import socket
import threading

from encryption_utils import (
    encrypt,
    decrypt,
    recv_frame,
    EncryptionMetrics,
)


HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5556  # different port so it coexists with the plaintext server

def get_local_ip():
    """Tries to get the actual local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # We send a dummy packet to figure out which network interface
        # would be used for outgoing traffic
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# username to socket mapping, protected by a lock for thread safety
clients: dict[str, socket.socket] = {}
clients_lock = threading.Lock()

# Server-wide aggregate metrics
server_metrics = EncryptionMetrics()
server_metrics_lock = threading.Lock()


# Broadcast message to all other clients (with a fresh IV each time)

def broadcast_encrypted(plaintext: str, sender_socket: socket.socket):
    """
    Encrypt plaintext and send it to every client except the sender.
    Each recipient gets their own encryption with a new IV.
    """
    disconnected = []

    with clients_lock:
        for username, client_sock in clients.items():
            if client_sock == sender_socket:
                continue
            try:
                frame, enc_ms, plain_len, cipher_len = encrypt(plaintext)
                client_sock.sendall(frame)

                # Track how much time re-encryption takes
                with server_metrics_lock:
                    server_metrics.record_encrypt(enc_ms, plain_len, cipher_len)

            except Exception:
                disconnected.append(username)

        # Remove clients that crashed during broadcast
        for uname in disconnected:
            if uname in clients:
                del clients[uname]


# Per-client thread that manages the full lifecycle of one connected client

def handle_client(client_socket: socket.socket, client_address: tuple):
    """
    Manage the full lifecycle of one connected client.
    Runs in its own thread.
    """
    # Handshake receive encrypted username
    name_frame = recv_frame(client_socket)
    if name_frame is None:
        client_socket.close()
        return

    username, dec_ms = decrypt(name_frame)
    username = username.strip()

    # Show who's already online before the duplicate check loop starts
    with clients_lock:
        online = list(clients.keys())
    if online:
        online_frame, enc_ms, pl, cl = encrypt(
            f"[SERVER] Currently online: {', '.join(online)}"
        )
    else:
        online_frame, enc_ms, pl, cl = encrypt("[SERVER] No other users online yet.")
    client_socket.sendall(online_frame)

    # If username is taken, ask the client to pick another one
    while username in clients:
        with clients_lock:
            online = list(clients.keys())
        if online:
            online_frame, enc_ms, pl, cl = encrypt(
                f"[SERVER] Currently online: {', '.join(online)}"
            )
            client_socket.sendall(online_frame)
        prompt_frame, enc_ms, pl, cl = encrypt(
            f"[SERVER] '{username}' is already taken. Online users: {', '.join(online)}. Enter a new name:"
        )
        client_socket.sendall(prompt_frame)
        name_frame = recv_frame(client_socket)
        if name_frame is None:
            client_socket.close()
            return
        username, dec_ms = decrypt(name_frame)
        username = username.strip()

    # Let the client know their name was accepted so it can exit the handshake loop
    confirm_frame, enc_ms, pl, cl = encrypt("[SERVER] Name accepted.")
    client_socket.sendall(confirm_frame)

    # Track per-client metrics
    client_metrics = EncryptionMetrics()
    client_metrics.record_decrypt(dec_ms)

    with clients_lock:
        clients[username] = client_socket

    print(f"[NEW CONNECTION] {client_address} -> username='{username}'")
    print(f"  (Username received as AES-256 ciphertext, decrypted in "
          f"{dec_ms:.4f} ms)")

    # Notify all others that a new user joined
    join_msg = f"[SERVER] '{username}' has joined the chat."
    broadcast_encrypted(join_msg, client_socket)

    # Main message loop
    try:
        while True:
            frame = recv_frame(client_socket)

            if frame is None:
                # Client closed the connection cleanly
                break

            # Decrypt it to see the content and routing info
            decoded_msg, dec_ms = decrypt(frame)
            client_metrics.record_decrypt(dec_ms)

            # Handle /users command
            if decoded_msg.strip() == "/users":
                with clients_lock:
                    online = list(clients.keys())
                user_list = "[SERVER] Online users: " + ", ".join(online)
                reply_frame, enc_ms, pl, cl = encrypt(user_list)
                client_socket.sendall(reply_frame)
                with server_metrics_lock:
                    server_metrics.record_encrypt(enc_ms, pl, cl)
                continue

            # Handle /quit command
            if decoded_msg.strip() == "/quit":
                print(f"[QUIT] {username} sent /quit")
                break

            # Private message format: @target_user message text
            if decoded_msg.startswith("@"):
                try:
                    target_token, private_text = decoded_msg.split(" ", 1)
                    target_name = target_token[1:]  # strip leading '@'

                    with clients_lock:
                        target_sock = clients.get(target_name)

                    if target_sock is not None:
                        # Encrypt it again with a new IV before sending
                        formatted = f"[PRIVATE] {username}: {private_text}"
                        priv_frame, enc_ms, pl, cl = encrypt(formatted)
                        target_sock.sendall(priv_frame)

                        with server_metrics_lock:
                            server_metrics.record_encrypt(enc_ms, pl, cl)

                        print(f"[PRIVATE] {username} -> {target_name} "
                              f"(enc {enc_ms:.4f} ms, dec {dec_ms:.4f} ms)")
                    else:
                        # Let the sender know that user isn't online
                        err_frame, enc_ms, pl, cl = encrypt(
                            f"[SERVER] User '{target_name}' not found."
                        )
                        client_socket.sendall(err_frame)

                        with server_metrics_lock:
                            server_metrics.record_encrypt(enc_ms, pl, cl)

                except ValueError:
                    err_frame, enc_ms, pl, cl = encrypt(
                        "[SERVER] Invalid format. Use: @username message"
                    )
                    client_socket.sendall(err_frame)

                    with server_metrics_lock:
                        server_metrics.record_encrypt(enc_ms, pl, cl)

                continue  # Do not broadcast private messages

            # Broadcast the message to everyone
            print(f"[MESSAGE] {username}: {decoded_msg}  "
                  f"(dec {dec_ms:.4f} ms)")

            # Add the sender's name so people know who sent it
            broadcast_encrypted(f"{username}: {decoded_msg}", client_socket)

    except Exception as exc:
        print(f"[ERROR] Client {client_address}: {exc}")

    finally:
        # Clean up when the client disconnects
        print(f"[DISCONNECTED] {username}")

        with clients_lock:
            clients.pop(username, None)

        leave_msg = f"[SERVER] '{username}' has left the chat."
        broadcast_encrypted(leave_msg, client_socket)

        client_socket.close()

        # Print per-client and cumulative metrics
        print(client_metrics.summary().replace(
            "AES-256 Encryption Metrics (this session)",
            f"AES-256 Metrics - client '{username}'"
        ))

        with server_metrics_lock:
            print(server_metrics.summary().replace(
                "AES-256 Encryption Metrics (this session)",
                "AES-256 Metrics - server aggregate"
            ))


# Server entry point

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow quick restart without "Address already in use" errors
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    server.settimeout(1.0)

    print(f"[SECURE SERVER] Listening on all interfaces (0.0.0.0:{PORT})")
    print(f"[SECURE SERVER] Tell clients to connect to IP: {get_local_ip()}")
    print(f"[SECURE SERVER] Transport: AES-256-CBC with random IV per message")
    print(f"[SECURE SERVER] Key length: {len(__import__('encryption_utils').SECRET_KEY)*8} bits\n")
    # Added logic to handle Crtl-C 

    # Background thread that lets you type /quit in the server terminal to shut down
    shutdown_event = threading.Event()

    def console_listener():
        """Background thread that checks for /quit on the server terminal."""
        while not shutdown_event.is_set():
            try:
                cmd = input()
                if cmd.strip() == "/quit":
                    print("[SECURE SERVER] /quit received, shutting down...")
                    shutdown_event.set()
            except EOFError:
                break

    console_thread = threading.Thread(target=console_listener, daemon=True)
    console_thread.start()
     
    try:
        while not shutdown_event.is_set():
            try:
                client_socket, client_address = server.accept()
            except socket.timeout:
                continue

            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address),
                daemon=True,
            )
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

    except KeyboardInterrupt:
        print("\n[SECURE SERVER] Shutting down...")
    finally:
        server.close()
        print("[SECURE SERVER] Socket closed. Goodbye.")


if __name__ == "__main__":
    start_server()
