import socket
import json
import os
import ffmpeg

class TCPServer:
    def __init__(self, server_address, server_port):
        self.server_address = server_address
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((server_address, server_port))
        self.buffer_size = 1400
    
    def start(self):
        self.handle_message()
    
    def handle_message(self):
        self.sock.listen(1)

        while True:
            print("接続待機中...")
            connection, client_address = self.sock.accept()
            
            try:
                print(f"connection from {client_address}")

                # ヘッダーを受信
                header = connection.recv(8)
                json_size = int.from_bytes(header[0:2], 'big')
                media_type_size = int.from_bytes(header[2:3], 'big')
                payload_size = int.from_bytes(header[3:8], 'big')

                # ボディ(ペイロード以外)を受信
                body = connection.recv(json_size + media_type_size)
                json_file = json.loads(body[0:json_size].decode("utf-8"))
                media_type = body[json_size : json_size + media_type_size].decode("utf-8")

                # 保存するファイル名を決定
                output_file_path = "processed/uploaded_file_" + str(payload_size) + media_type

                # ファイル(ペイロード)を受け取って保存
                received_data = 0
                
                with open(output_file_path, 'wb') as f:
                    while received_data < payload_size:
                        data = connection.recv(self.buffer_size)
                        if not data:
                            break
                        f.write(data)
                        received_data += len(data)
                
                # 受信完了のメッセージを送信（16バイトのメッセージ）
                if received_data == payload_size:
                    status = 0x01
                else:
                    status = 0x02
                    
                status_bytes = status.to_bytes(1, "big")
                connection.send(status_bytes)

                # jsonファイルに従ってリクエスト処理
                operation = json_file.get('operation')
                
                if operation == 1:
                    self.compress(media_type, output_file_path)
                
                elif operation == 2:
                    resolution = json_file.get('resolution')
                    self.change_resolution(media_type, output_file_path, resolution)
                
                elif operation == 3:
                    aspect_ratio_num = json_file.get('aspect_ratio_num')
                    self.change_aspect_ratio(media_type, output_file_path, aspect_ratio_num)
                
                elif operation == 4:
                    output_mp3_file_path = "processed/uploaded_file_" + str(payload_size) + ".mp3"
                    self.convert_to_audio(output_file_path, output_mp3_file_path)

                elif operation == 5:
                    output_gif_file_path = "processed/uploaded_file_" + str(payload_size) + ".gif"
                    start_time = json_file.get('start_time')
                    duration = json_file.get('duration')
                    self.create_gif(output_file_path, output_gif_file_path, start_time, duration)
                
                else:
                    print("operationが1~5の数値以外です")
                
            
            except Exception as e:
                print(f"Error: {e}")
            
            finally:
                print("Closing current connection")
                connection.close()
    

    # 動画ファイルの圧縮
    def compress(self, media_type, output_file_path):
        temp_output = 'temp_compressed' + media_type

        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        # ビデオのビットレートを調整して圧縮
        ffmpeg.input(output_file_path).output(temp_output, video_bitrate='1M').run()
        
        # 元のファイルを削除して圧縮ファイルに置き換え
        os.replace(temp_output, output_file_path)
        print(f"圧縮された動画は {output_file_path} に保存されました")
    

    # 動画の解像度変更
    def change_resolution(self, media_type, output_file_path, resolution):
        if resolution == "1":
            width = 640
            height = 480
        elif resolution == "2":
            width = 1280
            height = 720
        elif resolution == "3":
            width = 1920
            height = 1080
        else:
            print("resolutionが1~3の数値以外です")
        
        temp_output = 'temp_resolution' + media_type
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        # 動画の解像度を変更
        ffmpeg.input(output_file_path).output(temp_output, vf=f'scale={width}:{height}').run()
        
        # 元のファイルを削除して解像度変更ファイルに置き換え
        os.replace(temp_output, output_file_path)
        print(f"Resolution changed to {width}x{height} and saved to {output_file_path}")
    

    # 動画のアスペクト比変更
    def change_aspect_ratio(self, media_type, output_file_path, aspect_ratio_num):
        temp_output = 'temp_aspect_ratio' + media_type
        if os.path.exists(temp_output):
            os.remove(temp_output)

        if aspect_ratio_num == "1":
            aspect_ratio = 16 / 9
        elif aspect_ratio_num == "2":
            aspect_ratio = 4 / 3
        elif aspect_ratio_num == "3":
            aspect_ratio = 1 / 1
        elif aspect_ratio_num == "4":
            aspect_ratio = 9 / 16
        else:
            print("aspect_ratio_numが1~4以外です")

        print(f"aspect_ratio:{aspect_ratio}")

        # 動画のアスペクト比を変更
        ffmpeg.input(output_file_path).output(temp_output, vf=f'setdar={aspect_ratio}').run()
        
        # 元のファイルを削除してアスペクト比変更ファイルに置き換え
        os.replace(temp_output, output_file_path)
        print(f"Aspect ratio changed to {aspect_ratio} and saved to {output_file_path}")


    # 動画をオーディオに変換
    def convert_to_audio(self, output_file_path, output_mp3_file_path):
        temp_output = 'temp_audio.mp3'
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        # 動画ファイルをオーディオに変換
        ffmpeg.input(output_file_path).output(output_mp3_file_path, acodec='mp3').run()
        os.remove(output_file_path)
        print(f"Audio extracted and saved to {output_mp3_file_path}")
    

    # 時間範囲でのGIFの作成
    def create_gif(self, output_file_path, output_gif_file_path, start_time, duration):
        temp_output = 'temp.gif'
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        # 動画から指定した時間範囲で GIF を作成
        ffmpeg.input(output_file_path, ss=start_time, t=duration).output(output_gif_file_path, vf='fps=10', loop=0).run()
        print(f"GIF created from {start_time} for {duration} seconds and saved to {output_gif_file_path}")
    


if __name__ == "__main__":
    server_address = '0.0.0.0'
    server_port = 9000
    tcp_server = TCPServer(server_address, server_port)
    tcp_server.start()
