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
                    send_file_path = self.compress(media_type, output_file_path)
                
                elif operation == 2:
                    resolution = json_file.get('resolution')
                    send_file_path = self.change_resolution(media_type, output_file_path, resolution)
                
                elif operation == 3:
                    aspect_ratio_num = json_file.get('aspect_ratio_num')
                    send_file_path = self.change_aspect_ratio(media_type, output_file_path, aspect_ratio_num)
                
                elif operation == 4:
                    output_mp3_file_path = "processed/uploaded_file_" + str(payload_size) + ".mp3"
                    send_file_path = self.convert_to_audio(output_file_path, output_mp3_file_path)

                elif operation == 5:
                    output_gif_file_path = "processed/uploaded_file_" + str(payload_size) + ".gif"
                    start_time = json_file.get('start_time')
                    duration = json_file.get('duration')
                    send_file_path = self.create_gif(output_file_path, output_gif_file_path, start_time, duration)
                
                else:
                    print("operationが1~5の数値以外です")
                
                # クライアントへの処理済みファイルの送信
                send_json_file = {
                    "error": False,
                    "error_message": None
                }

                send_json_string_bytes = json.dumps(send_json_file).encode('utf-8')
                send_json_string_bytes_size = len(send_json_string_bytes)
                send_json_string_len_bytes = send_json_string_bytes_size.to_bytes(2, "big")

                send_file_size_int = os.path.getsize(send_file_path)
                send_payload_size = send_file_size_int.to_bytes(5, 'big')

                send_file_split = os.path.splitext(send_file_path)

                send_media_type = send_file_split[1]
                send_media_type_bytes = send_media_type.encode('utf-8')
                send_media_type_bytes_len = len(send_media_type_bytes)
                send_media_type_len_bytes = send_media_type_bytes_len.to_bytes(1, "big")

                send_header = send_json_string_len_bytes + send_media_type_len_bytes + send_payload_size

                connection.sendall(send_header)

                send_body = send_json_string_bytes + send_media_type_bytes

                connection.sendall(send_body)

                with open(send_file_path, 'rb') as f:
                    while (chunk := f.read(self.buffer_size)):
                        connection.sendall(chunk)
            
            except Exception as e:
                print(f"Error: {e}")
                send_json_file = {
                    "error": False,
                    "error_message": None
                }
                send_json_file["error"] = True
                send_json_file["error_message"] = e

                send_json_string_bytes = json.dumps(send_json_file).encode('utf-8')
                send_json_string_bytes_size = len(send_json_string_bytes)
                send_json_string_len_bytes = send_json_string_bytes_size.to_bytes(2, "big")

                send_file_size_int = 0
                send_payload_size = send_file_size_int.to_bytes(5, 'big')

                send_file_split = os.path.splitext(send_file_path)

                send_media_type_bytes_len = 0
                send_media_type_len_bytes = send_media_type_bytes_len.to_bytes(1, "big")

                send_error = send_json_string_len_bytes + send_media_type_len_bytes + send_payload_size + send_json_string_bytes

                connection.sendall(send_error)
            
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

        return output_file_path
    

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
        print(f"解像度は {width}x{height} に変換され、 {output_file_path} へ保存されました")

        return output_file_path
    

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
        print(f"アスペクト比は {aspect_ratio} へ変換され、 {output_file_path} に保存されました")

        return output_file_path


    # 動画をオーディオに変換
    def convert_to_audio(self, output_file_path, output_mp3_file_path):
        temp_output = 'temp_audio.mp3'
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        # 動画ファイルをオーディオに変換
        ffmpeg.input(output_file_path).output(output_mp3_file_path, acodec='mp3').run()
        os.remove(output_file_path)
        print(f"オーディオが抽出され、 {output_mp3_file_path} へ保存されました")

        return output_mp3_file_path
    

    # 時間範囲でのGIFの作成
    def create_gif(self, output_file_path, output_gif_file_path, start_time, duration):
        temp_output = 'temp.gif'
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        # 動画から指定した時間範囲で GIF を作成
        ffmpeg.input(output_file_path, ss=start_time, t=duration).output(output_gif_file_path, vf='fps=10', loop=0).run()
        print(f"{start_time} から {duration} 秒間のGIFが作成され、 {output_gif_file_path} に保存されました")

        return output_gif_file_path


if __name__ == "__main__":
    server_address = '0.0.0.0'
    server_port = 9000
    tcp_server = TCPServer(server_address, server_port)
    tcp_server.start()
