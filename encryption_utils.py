"""
encryption_utils.py - Feature 3 Helper Module

Provides helpers for encrypting and decrypting messages with AES-256-CBC.
Used by server_secure.py and client_secure.py.

The approach (with some AI assistance):
   - AES-256 is used in CBC mode with a random 16-byte IV for each message.
     Reusing an IV is bad practice, as it can leak patterns in the
     plaintext. The IV is prepended to the ciphertext so the receiver can
     extract it without needing a separate channel to send it.
   - PKCS7 is used for padding via pycryptodome to pad the plaintext to a
     multiple of 16 bytes (the AES block size).
   - The pre-shared 32-byte key is used for symmetric encryption. In a real
     system you'd probably want to use something like Diffie-Hellman or
     TLS to agree on the key, but for this class project it's hardcoded
     it to keep things simple.

Wire format of encrypted frames sent over TCP:
  - 4 bytes: big-endian total payload length
  - 16 bytes: IV
  - N bytes: ciphertext (PKCS7-padded)

The 4-byte length prefix helps the receiver read exactly one frame at
a time without getting stuck on partial TCP reads or mixing up messages.
"""

import os
import struct
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Pre-shared secret key (256-bit / 32 bytes)
# Both server and every client must use the same key
SECRET_KEY: bytes = b"ChatApp_AES256_SecretKey_Feature"  # exactly 32 bytes

# AES block size is always 16 bytes for any key length
BLOCK_SIZE: int = AES.block_size  # 16


# Encryption function

def encrypt(plaintext: str) -> tuple[bytes, float, int, int]:
    """
    Encrypt a UTF-8 string with AES-256-CBC.

    Returns
    -------
    frame        : bytes  - wire-ready frame (length prefix + IV + ciphertext)
    enc_time_ms  : float  - time spent encrypting, in milliseconds
    plain_len    : int    - length of original UTF-8 bytes (for metrics)
    cipher_len   : int    - length of ciphertext bytes (for metrics)
    """
    t0 = time.perf_counter()

    # Generate a new IV for each message
    iv = os.urandom(BLOCK_SIZE)

    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)

    # Convert to UTF-8 bytes and add padding
    raw = plaintext.encode("utf-8")
    padded = pad(raw, BLOCK_SIZE)
    ciphertext = cipher.encrypt(padded)

    enc_time_ms = (time.perf_counter() - t0) * 1000

    # Build the frame: length prefix + IV + encrypted data
    payload = iv + ciphertext
    frame = struct.pack(">I", len(payload)) + payload

    return frame, enc_time_ms, len(raw), len(ciphertext)


# Decryption function

def decrypt(frame: bytes) -> tuple[str, float]:
    """
    Decrypt a wire frame produced by encrypt().

    Parameters
    ----------
    frame : bytes - the raw frame bytes, including the 4-byte length prefix

    Returns
    -------
    plaintext   : str   - recovered UTF-8 string
    dec_time_ms : float - time spent decrypting, in milliseconds
    """
    t0 = time.perf_counter()

    # Remove the length header and extract the IV and ciphertext
    payload = frame[4:]
    iv = payload[:BLOCK_SIZE]
    ciphertext = payload[BLOCK_SIZE:]

    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext), BLOCK_SIZE).decode("utf-8")

    dec_time_ms = (time.perf_counter() - t0) * 1000
    return plaintext, dec_time_ms


# Framed socket I/O

def recv_frame(sock) -> bytes | None:
    """
    Read exactly one AES frame from 'sock'.

    The 4-byte length prefix tells us how many more bytes to read,
    so we never block on a partial TCP segment or read across frames.

    Returns None if the remote side closed the connection.
    """
    # Read the 4-byte length prefix
    header = _recv_exact(sock, 4)
    if header is None:
        return None

    payload_len = struct.unpack(">I", header)[0]

    # Read the exact payload
    payload = _recv_exact(sock, payload_len)
    if payload is None:
        return None

    return header + payload  # return the full frame (prefix + payload)


def _recv_exact(sock, n: int) -> bytes | None:
    """Read exactly 'n' bytes from 'sock', handling partial reads."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


# Metrics helper class

class EncryptionMetrics:
    """Accumulates per-session encryption / decryption statistics."""

    def __init__(self):
        self.msgs_encrypted: int = 0
        self.msgs_decrypted: int = 0
        self.total_enc_ms: float = 0.0
        self.total_dec_ms: float = 0.0
        self.total_plain_bytes: int = 0
        self.total_cipher_bytes: int = 0

    def record_encrypt(self, enc_ms: float, plain_bytes: int, cipher_bytes: int):
        self.msgs_encrypted += 1
        self.total_enc_ms += enc_ms
        self.total_plain_bytes += plain_bytes
        self.total_cipher_bytes += cipher_bytes

    def record_decrypt(self, dec_ms: float):
        self.msgs_decrypted += 1
        self.total_dec_ms += dec_ms

    def summary(self) -> str:
        avg_enc = (self.total_enc_ms / self.msgs_encrypted
                   if self.msgs_encrypted else 0)
        avg_dec = (self.total_dec_ms / self.msgs_decrypted
                   if self.msgs_decrypted else 0)
        overhead_pct = (
            ((self.total_cipher_bytes - self.total_plain_bytes)
             / self.total_plain_bytes * 100)
            if self.total_plain_bytes else 0
        )
        return (
            f"\n{'='*50}\n"
            f"  AES-256 Encryption Metrics (this session)\n"
            f"{'='*50}\n"
            f"  Messages encrypted  : {self.msgs_encrypted}\n"
            f"  Messages decrypted  : {self.msgs_decrypted}\n"
            f"  Avg encrypt latency : {avg_enc:.4f} ms\n"
            f"  Avg decrypt latency : {avg_dec:.4f} ms\n"
            f"  Plaintext bytes     : {self.total_plain_bytes}\n"
            f"  Ciphertext bytes    : {self.total_cipher_bytes}\n"
            f"  Size overhead       : {overhead_pct:.1f}%\n"
            f"{'='*50}\n"
        )
