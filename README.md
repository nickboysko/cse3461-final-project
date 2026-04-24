# Chat Application - CSE 3461 Group Project

A simple TCP chat server that supports broadcast and private messaging. The project has two versions: plaintext and encrypted.

## How to use

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

## How to Use

- **Broadcast:** Just type a message and press enter
- **Private message:** Type `@username message` 
- **Quit:** Press Ctrl-C

## File Overview

### Plaintext Versions (Features 1 & 2)
- **server.py** - Handles multiple client connections with broadcast and private messaging
- **client.py** - Connects to the server and sends/receives messages in real-time

### Encrypted Versions (Feature 3, with AI assistance)
- **server_secure.py** - Builds on the plaintext server but encrypts all traffic with AES-256-CBC
- **client_secure.py** - Encrypted version of the client with the same features
- **encryption_utils.py** - Helper functions for encrypting/decrypting messages and tracking performance metrics

### Differences in the Encrypted Version
- All messages are sent as AES-256-CBC ciphertext instead of plaintext
- Each message gets a fresh random IV (initialization vector)
- Length-prefixed frames ensure clean message boundaries
- Performance metrics are printed when clients disconnect to show encryption overhead

## Project Structure

Both versions support the same user-facing features, so you can compare plaintext vs encrypted implementations side-by-side on different ports (5555 for plaintext, 5556 for encrypted).
