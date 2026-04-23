import socket
import threading

HOST = "127.0.0.1"
PORT = 5555


def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024)
            if not message:
                print("Disconnected from server.")
                break

            print("\n" + message.decode("utf-8"))
        except:
            print("Connection to server lost.")
            break


def start_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))

    # send username to handler
    name = input("Enter your display name: ")
    client.send(name.encode("utf-8"))
    print(f"Connected to server at {HOST}:{PORT}")
    print(f"Local socket info: {client.getsockname()}")

    receive_thread = threading.Thread(
        target=receive_messages,
        args=(client,),
        daemon=True
    )
    receive_thread.start()

    try:
        while True:
            message = input()
            full_message = f"{message}"
            client.send(full_message.encode("utf-8"))
    except KeyboardInterrupt:
        print("\nClosing connection...")
    finally:
        client.close()


if __name__ == "__main__":
    start_client()