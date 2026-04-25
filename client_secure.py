"""
client_secure.py
Feature 3: AES-256-CBC Encrypted Chat Client

Drop-in replacement for client.py that encrypts every outgoing
message and decrypts every incoming message using AES-256-CBC.

Differences from the plaintext client (with some AI assistance):
- All socket sends use sendall(frame) where frame is
  [4-byte length prefix | 16-byte IV | AES ciphertext].
- The background receive thread calls recv_frame() to read just
  one AES frame per iteration, then decrypts before printing.
- Per-session encryption metrics are printed when the client exits,
  displaying the average latency added per message and
  ciphertext size overhead compared to plaintext.

Usage:
    python client_secure.py
    > Enter your display name: Neal
    > Hello everyone!          <- broadcast (Feature 1)
    > @Bob Hello, Bob!         <- private message (Feature 2)
    Ctrl-C to quit and see metrics.
"""

import socket
import threading

from encryption_utils import (
    encrypt,
    decrypt,
    recv_frame,
    EncryptionMetrics,
)

PORT = 5556  # must match server_secure.py

# Per-client metrics object to track encryption performance for this session
metrics = EncryptionMetrics()


# Receive thread that continuously reads and decrypts messages

def receive_messages(client_socket: socket.socket):
    """
    Background thread continuously reads AES frames from the server,
    decrypts them, and prints them to stdout.
    """
    while True:
        try:
            frame = recv_frame(client_socket)
            if frame is None:
                print("\n[INFO] Disconnected from server.")
                break

            plaintext, dec_ms = decrypt(frame)
            metrics.record_decrypt(dec_ms)

            # Show the decrypted message
            print(f"\n[ENCRYPTED] {plaintext}  [{dec_ms:.3f} ms to decrypt]")

        except Exception as exc:
            print(f"\n[ERROR] Receive thread: {exc}")
            break


# Client entry point

def start_client():
    # Ask for the IP, but default to localhost if they just press Enter
    server_ip = input("Enter server IP (press Enter for localhost): ").strip()
    if not server_ip:
        server_ip = "127.0.0.1"

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((server_ip, PORT))

    print(f"[SECURE CLIENT] Connected to {server_ip}:{PORT}")
    print(f"[SECURE CLIENT] Transport: AES-256-CBC - all messages encrypted\n")

    name = input("Enter your display name: ").strip()

    name_frame, enc_ms, pl, cl = encrypt(name)
    client.sendall(name_frame)
    metrics.record_encrypt(enc_ms, pl, cl)

    # Check if the server sent an initial response (e.g., welcome or duplicate name prompt)
    first_frame = recv_frame(client)
    if first_frame:
        first_msg, dec_ms = decrypt(first_frame)
        metrics.record_decrypt(dec_ms)
        print(f"\n{first_msg}")
        # If it's a taken-name prompt, fall into the retry loop below
        if "is already taken" in first_msg:
            name = input("New display name: ").strip()
            name_frame, enc_ms, pl, cl = encrypt(name)
            client.sendall(name_frame)
            metrics.record_encrypt(enc_ms, pl, cl)
    
    # Keep trying to get a unique name if the server says it's taken
    while True:
        response_frame = recv_frame(client)
        if response_frame is None:
            print("[ERROR] Server disconnected during handshake.")
            return
        response, dec_ms = decrypt(response_frame)
        metrics.record_decrypt(dec_ms)
        if "[SERVER]" in response and "is already taken" in response:
            print(f"\n{response}")
            name = input("New display name: ").strip()
            name_frame, enc_ms, pl, cl = encrypt(name)
            client.sendall(name_frame)
            metrics.record_encrypt(enc_ms, pl, cl)
        else:
            # First non-handshake message (e.g. join broadcast) — print it and break
            print(f"\n[ENCRYPTED] {response}  [{dec_ms:.3f} ms to decrypt]")
            break

    print(f"[INFO] Username sent as AES-256 ciphertext "
          f"({pl} bytes -> {cl} bytes, encrypted in {enc_ms:.4f} ms)")
    print(f"[INFO] Local address: {client.getsockname()}\n")
    print("===" * 17)
    print("  Send a message  : just type and press Enter")
    print("  Private message : @username <your message>")
    print("  Quit            : Ctrl-C")
    print("===" * 17 + "\n")

    # Start background receive thread
    recv_thread = threading.Thread(
        target=receive_messages,
        args=(client,),
        daemon=True,
    )
    recv_thread.start()

    # Main send loop
    try:
        while True:
            message = input()
            if not message:
                continue

            # Let the user type /quit to leave gracefully
            if message.strip() == "/quit":
                print("[INFO] Quitting...")
                break

            # Encrypt and send
            frame, enc_ms, plain_len, cipher_len = encrypt(message)
            client.sendall(frame)
            metrics.record_encrypt(enc_ms, plain_len, cipher_len)

            # Show how much encryption adds per message
            overhead = cipher_len - plain_len
            print(f"  ↑ sent {plain_len}B plaintext → {cipher_len}B ciphertext "
                  f"(+{overhead}B overhead, {enc_ms:.3f} ms to encrypt)")

    except KeyboardInterrupt:
        print("\n[INFO] Closing connection...")

    finally:
        client.close()
        # Print session summary metrics
        print(metrics.summary())


if __name__ == "__main__":
    start_client()
