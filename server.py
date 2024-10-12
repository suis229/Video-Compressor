import socket
import json

class TCPServer:
    def __init__(self, server_address, server_port):
        self.server_address = server_address
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((server_address, server_port))
        self.buffer_size = 1400
    
    def receive_mp4(self):
        self.sock.listen(1)

        while True:
            print("接続待機中...")
            connection, client_address = self.sock.accept()
            
            try:
                print(f"connection from {client_address}")

                # ファイルのバイト数を受信
                file_size_data = connection.recv(32)
                file_size = int.from_bytes(file_size_data, 'big')

                # 保存するファイル名を決定
                file_path = f"compressed/uploaded_file_{file_size}.mp4"

                received_data = 0

                # ファイルを受け取って保存
                with open(file_path, 'wb') as f:
                    while received_data < file_size:
                        data = connection.recv(self.buffer_size)
                        if not data:
                            break
                        f.write(data)
                        received_data += len(data)
                
                # 受信完了のメッセージを送信（16バイトのメッセージ）
                if received_data == file_size:
                    status = 0x01
                else:
                    status = 0x02
                    
                status_bytes = status.to_bytes(1, "big")
                connection.send(status_bytes)
            
            except Exception as e:
                print(f"Error: {e}")
            
            finally:
                print("Closing current connection")
                connection.close()
    
    def start(self):
        self.receive_mp4()




if __name__ == "__main__":
    server_address = '0.0.0.0'
    server_port = 9000
    tcp_server = TCPServer(server_address, server_port)
    tcp_server.start()
