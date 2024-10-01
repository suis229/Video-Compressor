import socket
import os
import sys
import readline


class TCPClient:
    def __init__(self, server_address, server_port):
        self.server_address = server_address
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.buffer_size = 1400
    
    def upload_file(self):
        try:
            file_path = input("アップロードするファイルのパスを入力してください: ")
            if not file_path.endswith('.mp4'):
                print("mp4 ファイルのみアップロード可能です")
                return
            
            file_size_int = os.path.getsize(file_path)
            file_size = file_size_int.to_bytes(32, 'big')

            try:
                self.sock.connect((self.server_address, self.server_port))
            except self.sock.error as err:
                print(err)
                sys.exit(1)
            
            # ファイルサイズの送信
            self.sock.send(file_size)

            # ファイルの送信
            with open(file_path, 'rb') as f:
                while (chunk := f.read(self.buffer_size)):
                    self.sock.sendall(chunk)
                
            # レスポンス受信
            response_bytes = self.sock.recv(16)
            response = int.from_bytes(response_bytes, "big")

            if response == 0x01:
                print("正常にアップロードされました")
            elif response == 0x02:
                print("アップロードに失敗しました")
                sys.exit(1)
            else:
                print("エラーが発生しました")
                sys.exit(1)
        
        finally:
            print("closing socket")
            self.sock.close()
    
    def start(self):
        self.upload_file()

if __name__ == "__main__":
    server_address = '0.0.0.0'
    server_port = 9000
    tcp_client = TCPClient(server_address, server_port)
    tcp_client.start()




