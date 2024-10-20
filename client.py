import socket
import os
import sys
import readline
import json
import ffmpeg

class TCPClient:
    def __init__(self, server_address, server_port):
        self.server_address = server_address
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.buffer_size = 1400
    
    def upload_file(self):
        try:
            # ファイルパス入力
            file_path = input("アップロードするファイルのパスを入力してください: ")
            file_size_int = os.path.getsize(file_path)
            payload_size = file_size_int.to_bytes(5, 'big')
            file_split = os.path.splitext(file_path)

            media_type = file_split[1]
            media_type_bytes = media_type.encode('utf-8')
            media_type_bytes_len = len(media_type_bytes)
            media_type_len_bytes = media_type_bytes_len.to_bytes(1, "big")


            if (media_type != ".mp4" and ".mp3" and ".json" and ".avi"):
                print("アップロード可能なメディアタイプは mp4、mp3、json、avi のいずれかです")
                return
            
            print("1: 動画ファイルの圧縮, 2: 動画の解像度の変更, 3: 動画のアスペクト比の変更, 4: 動画をオーディオに変換, 5: 時間範囲での GIF と WEBM の作成")
            operation_str = input("処理内容を番号で選択してください: ")
            operation = int(operation_str)

            while not (operation >= 1 and operation <= 5):
                operation_str = input("1 から 5 の数字で入力してください: ")
                operation = int(operation_str)

            json_file = {
                "operation": operation,
                "resolution": None,
                "aspect_ratio_num": None,
                "start_time": None,
                "duration": None
            }

            if operation == 2:
                print("1: SD(640×480), 2: HD(1280×720), 3: フルHD(1920×1080)")
                json_file["resolution"] = input("変換後の解像度を番号で入力してください：")
                while not (int(json_file["resolution"]) >= 1 and int(json_file["resolution"]) <= 3):
                    json_file["resolution"] = input("１から３の数値を入力してください：")
            
            elif operation == 3:
                print("1: 16/9, 2: 4/3, 3: 1/1, 4: 9/16")
                json_file["aspect_ratio_num"] = input("変更後の解像度を番号で入力してください：")
                while not (int(json_file["aspect_ratio_num"]) >= 1 and int(json_file["aspect_ratio_num"]) <= 4):
                    json_file["aspect_ratio_num"] = input("１から４の数値を入力してください：")
            
            elif operation == 5:
                # 動画の長さを取得
                video_duration = self.get_video_duration(file_path)
                json_file["start_time"] = self.prompt_for_start_time(video_duration)
                json_file["duration"] = self.prompt_for_duration(json_file["start_time"], video_duration)

            json_string_bytes = json.dumps(json_file).encode('utf-8')
            json_string_bytes_size = len(json_string_bytes)
            json_string_len_bytes = json_string_bytes_size.to_bytes(2, "big")

            # 動画ファイルの送受信用のソケット接続
            try:
                self.sock.connect((self.server_address, self.server_port))
            except self.sock.error as err:
                print(err)
                sys.exit(1)
            
            # ヘッダーの送信
            header = json_string_len_bytes + media_type_len_bytes + payload_size
            self.sock.sendall(header)

            # ボディの送信
            body = json_string_bytes + media_type_bytes
            self.sock.sendall(body)

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
            
            # 処理済みファイル受信
            receive_header = self.sock.recv(8)
            receive_json_size = int.from_bytes(receive_header[0:2], 'big')
            receive_media_type_size = int.from_bytes(receive_header[2:3], 'big')
            receive_payload_size = int.from_bytes(receive_header[3:8], 'big')

            receive_body = self.sock.recv(receive_json_size + receive_media_type_size)
            receive_json = json.loads(receive_body[0:receive_json_size].decode("utf-8"))
            receive_media_type = receive_body[receive_json_size : receive_json_size + receive_media_type_size].decode("utf-8")

            # 保存するファイル名を決定
            file_name = file_split[0].split("/")[1]
            print(file_name)
            receive_file_path = "receive/" + file_name + "_" + str(receive_payload_size) + receive_media_type
            
            # ファイル(ペイロード)を受け取って保存
            received_data = 0
            
            with open(receive_file_path, 'wb') as f:
                while received_data < receive_payload_size:
                    data = self.sock.recv(self.buffer_size)
                    if not data:
                        break
                    f.write(data)
                    received_data += len(data)

            if received_data == receive_payload_size:
                print("処理済みのファイルが正常にダウンロードできました")
            else:
                print("ダウンロードに失敗しました")
        
        except Exception as e:
            print(f"Error: {e}")
        
        finally:
            print("closing socket")
            self.sock.close()
    
    def get_video_duration(self, file_path):
        # 動画の長さを秒単位で取得
        probe = ffmpeg.probe(file_path)
        video_duration = float(probe['format']['duration'])
        return video_duration

    def convert_time_to_seconds(self, time_str):
        # 時間形式 (hh:mm:ss) を秒に変換
        parts = time_str.split(':')
        if len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        else:
            return float(time_str)

    def prompt_for_start_time(self, video_duration):
        while True:
            print("開始時間をhh:mm:ss（時:分:秒）または秒単位（例: 120.5 で2分0.5秒）の形式で入力してください")
            start_time = input("開始時間：")
            try:
                start_seconds = self.convert_time_to_seconds(start_time)
                if start_seconds < 0 or start_seconds > video_duration:
                    print(f"開始時間が無効です。動画の長さは {video_duration:.2f} 秒です。範囲内で入力してください。")
                else:
                    return start_seconds
            except ValueError:
                print("無効な形式です。再度入力してください。")
    
    def prompt_for_duration(self, start_seconds, video_duration):
        while True:
            print("GIFに変換する動画の長さ（秒数）を指定してください")
            duration = input("動画の長さ：")
            try:
                duration_seconds = float(duration)
                if duration_seconds <= 0 or start_seconds + duration_seconds > video_duration:
                    print(f"動画の長さが無効です。開始時間から{video_duration - start_seconds:.2f}秒までが許容範囲です。")
                else:
                    return duration_seconds
            except ValueError:
                print("無効な形式です。再度入力してください。")

    def start(self):
        self.upload_file()

if __name__ == "__main__":
    server_address = '0.0.0.0'
    server_port = 9000
    tcp_client = TCPClient(server_address, server_port)
    tcp_client.start()
