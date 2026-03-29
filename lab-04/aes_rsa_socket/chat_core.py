import socket
import threading
from dataclasses import dataclass
from typing import Callable, Optional

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


def encrypt_message(key: bytes, message: str) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC)
    ciphertext = cipher.encrypt(pad(message.encode("utf-8"), AES.block_size))
    return cipher.iv + ciphertext


def decrypt_message(key: bytes, encrypted_message: bytes) -> str:
    iv = encrypted_message[: AES.block_size]
    ciphertext = encrypted_message[AES.block_size :]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return plaintext.decode("utf-8")


@dataclass
class ClientSession:
    client_socket: socket.socket
    address: tuple[str, int]
    aes_key: bytes
    name: str


class AesRsaChatServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 12345,
        on_log: Optional[Callable[[str], None]] = None,
        on_client_count: Optional[Callable[[int], None]] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.on_log = on_log
        self.on_client_count = on_client_count

        self.server_socket: Optional[socket.socket] = None
        self.server_key = RSA.generate(2048)
        self.is_running = False

        self._clients: list[ClientSession] = []
        self._clients_lock = threading.Lock()
        self._accept_thread: Optional[threading.Thread] = None

    def _log(self, message: str) -> None:
        if self.on_log:
            self.on_log(message)

    def _notify_client_count(self) -> None:
        if self.on_client_count:
            with self._clients_lock:
                count = len(self._clients)
            self.on_client_count(count)

    def start(self) -> None:
        if self.is_running:
            return

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        self.is_running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()
        self._log(f"Server started at {self.host}:{self.port}")

    def stop(self) -> None:
        if not self.is_running:
            return

        self.is_running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

        with self._clients_lock:
            sessions = list(self._clients)

        for session in sessions:
            self._disconnect_client(session, log=False)

        self._notify_client_count()
        self._log("Server stopped")

    def _accept_loop(self) -> None:
        while self.is_running and self.server_socket:
            try:
                client_socket, client_address = self.server_socket.accept()
            except OSError:
                break

            thread = threading.Thread(
                target=self._handle_client,
                args=(client_socket, client_address),
                daemon=True,
            )
            thread.start()

    def _handle_client(self, client_socket: socket.socket, client_address: tuple[str, int]) -> None:
        session: Optional[ClientSession] = None
        try:
            client_socket.sendall(self.server_key.publickey().export_key(format="PEM"))
            client_public_key = RSA.import_key(client_socket.recv(4096))

            aes_key = get_random_bytes(16)
            encrypted_aes_key = PKCS1_OAEP.new(client_public_key).encrypt(aes_key)
            client_socket.sendall(encrypted_aes_key)

            session = ClientSession(
                client_socket=client_socket,
                address=client_address,
                aes_key=aes_key,
                name=f"{client_address[0]}:{client_address[1]}",
            )

            with self._clients_lock:
                self._clients.append(session)
            self._notify_client_count()
            self._log(f"Connected: {session.name}")

            while self.is_running:
                encrypted_message = client_socket.recv(4096)
                if not encrypted_message:
                    break

                message = decrypt_message(aes_key, encrypted_message)
                if message.strip().lower() == "exit":
                    break

                if message.startswith("/name "):
                    new_name = message.replace("/name ", "", 1).strip()
                    if new_name:
                        old_name = session.name
                        session.name = new_name
                        self._log(f"Rename: {old_name} -> {new_name}")
                    continue

                self._log(f"{session.name}: {message}")
                self.broadcast(f"{session.name}: {message}", exclude_client=client_socket)

        except Exception as error:
            self._log(f"Client error {client_address}: {error}")
        finally:
            if session:
                self._disconnect_client(session, log=True)
            else:
                try:
                    client_socket.close()
                except OSError:
                    pass

    def broadcast(self, message: str, exclude_client: Optional[socket.socket] = None) -> None:
        with self._clients_lock:
            sessions = list(self._clients)

        for session in sessions:
            if exclude_client and session.client_socket == exclude_client:
                continue
            try:
                encrypted = encrypt_message(session.aes_key, message)
                session.client_socket.sendall(encrypted)
            except OSError:
                self._disconnect_client(session, log=True)

    def _disconnect_client(self, session: ClientSession, log: bool) -> None:
        removed = False
        with self._clients_lock:
            if session in self._clients:
                self._clients.remove(session)
                removed = True

        try:
            session.client_socket.close()
        except OSError:
            pass

        if removed:
            self._notify_client_count()
            if log:
                self._log(f"Disconnected: {session.name}")


class AesRsaChatClient:
    def __init__(
        self,
        on_message: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.on_message = on_message
        self.on_status = on_status

        self.client_socket: Optional[socket.socket] = None
        self.client_key: Optional[RSA.RsaKey] = None
        self.aes_key: Optional[bytes] = None
        self.is_connected = False
        self._receive_thread: Optional[threading.Thread] = None

    def _status(self, text: str) -> None:
        if self.on_status:
            self.on_status(text)

    def connect(self, host: str = "127.0.0.1", port: int = 12345) -> None:
        if self.is_connected:
            return

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))

        self.client_key = RSA.generate(2048)
        server_public_key = RSA.import_key(self.client_socket.recv(4096))
        self.client_socket.sendall(self.client_key.publickey().export_key(format="PEM"))

        encrypted_aes_key = self.client_socket.recv(4096)
        self.aes_key = PKCS1_OAEP.new(self.client_key).decrypt(encrypted_aes_key)

        self.is_connected = True
        self._status(f"Connected to {host}:{port}")

        self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._receive_thread.start()

    def _receive_loop(self) -> None:
        while self.is_connected and self.client_socket and self.aes_key:
            try:
                encrypted_message = self.client_socket.recv(4096)
                if not encrypted_message:
                    break
                message = decrypt_message(self.aes_key, encrypted_message)
                if self.on_message:
                    self.on_message(message)
            except OSError:
                break
            except Exception as error:
                self._status(f"Receive error: {error}")
                break

        self.disconnect(silent=True)
        self._status("Disconnected from server")

    def send(self, message: str) -> None:
        if not self.is_connected or not self.client_socket or not self.aes_key:
            raise RuntimeError("Client is not connected")
        encrypted_message = encrypt_message(self.aes_key, message)
        self.client_socket.sendall(encrypted_message)

    def disconnect(self, send_exit: bool = False, silent: bool = False) -> None:
        if not self.is_connected:
            return

        if send_exit:
            try:
                self.send("exit")
            except OSError:
                pass

        self.is_connected = False

        if self.client_socket:
            try:
                self.client_socket.close()
            except OSError:
                pass
            self.client_socket = None

        if not silent:
            self._status("Connection closed")
