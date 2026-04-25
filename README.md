# Chat Application - CSE 3461 Group Project

A simple TCP chat server that supports broadcast and private messaging. The project has two versions: plaintext and encrypted.

## How to Use

### Plaintext Chat (Features 1 & 2)

Terminal 1:
```bash
python server.py
```

Terminal 2+:
```bash
python client.py
```

### Encrypted Chat (Feature 3)

Terminal 1:
```bash
python server_secure.py
```

Terminal 2+:
```bash
python client_secure.py
```

**Note:** Make sure you have pycryptodome installed:
```bash
pip install pycryptodome
```

## Commands

- **Broadcast:** Just type a message and press Enter
- **Private message:** Type `@username message`
- **List online users:** Type `/users`
- **Quit:** Type `/quit` or press Ctrl-C
- **Shut down server:** Type `/quit` in the server terminal (encrypted server only)

## Over-the-Air Mode

The server binds to `0.0.0.0` and prints its local IP on startup. Clients will prompt for a server IP when launched — just press Enter to default to localhost for simulation mode.

## Duplicate Usernames

If a username is already taken, the server will prompt you to pick a new one and show who is currently online to help you choose.

## File Overview

### Plaintext Versions (Features 1 & 2)
- **server.py** - Handles multiple client connections with broadcast and private messaging
- **client.py** - Connects to the server and sends/receives messages in real-time

### Encrypted Versions (Feature 3, with AI assistance)
- **server_secure.py** - Builds on the plaintext server but encrypts all traffic with AES-256-CBC
- **client_secure.py** - Encrypted version of the client with the same features
- **encryption_utils.py** - Shared helpers for encrypting/decrypting messages and tracking performance metrics

### Differences in the Encrypted Version
- All messages are sent as AES-256-CBC ciphertext instead of plaintext
- Each message gets a fresh random IV (initialization vector) so identical messages produce different ciphertext
- Length-prefixed frames ensure clean message boundaries over TCP
- Per-message and session-level metrics are printed on disconnect showing encryption latency and size overhead

## Project Structure

Both versions support the same user-facing features and can run side-by-side on different ports (5555 for plaintext, 5556 for encrypted).