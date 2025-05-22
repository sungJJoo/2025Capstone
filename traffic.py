import cv2
import numpy as np
from ultralytics import YOLO
from gtts import gTTS
import pygame
import os
import time
from picamera2 import Picamera2
import threading
import speech_recognition as sr
from pyzbar import pyzbar

# YOLO 모델 로드
print("YOLO 모델을 로드하는 중...")
model = YOLO("yolov8n.pt")
print("YOLO 모델 로드 완료!")

# pygame 초기화
pygame.mixer.init()
TEMP_AUDIO = "temp_alert"
last_alert_audio = None
mode = "object"  # 현재 모드: "object" 또는 "qr"

# 위험 객체 정의
DANGEROUS_OBJECTS = {
    0: "사람", 1: "자전거", 2: "자동차", 3: "오토바이", 5: "버스",
    7: "트럭", 9: "신호등", 13: "정지 표지판", 15: "벤치",
    17: "고양이", 18: "개", 27: "우산"
}
JOSA_LIST = {"사람", "트럭", "신호등", "정지 표지판", "우산"}
last_alert_time = 0
ALERT_INTERVAL = 3  # 객체 인식 음성 알림 간격 (초)
last_qr_data = ""
last_qr_alert_time = 0
QR_ALERT_INTERVAL = 3  # QR 코드 알림 간격

def is_display_available():
    return os.environ.get("DISPLAY") is not None

def text_to_speech(text, direction, object):
    global last_alert_audio
    try:
        filename = TEMP_AUDIO + direction + object + ".mp3"
        tts = gTTS(text=text, lang='ko')
        tts.save(filename)
        last_alert_audio = filename
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"TTS 오류: {e}")

def text_to_speech_async(text, direction, object):
    threading.Thread(
        target=text_to_speech,
        args=(text, direction, object),
        daemon=True
    ).start()

def check_dangerous_objects(results, frame_width):
    global last_alert_time
    current_time = time.time()
    if current_time - last_alert_time < ALERT_INTERVAL:
        return

    for result in results:
        boxes = result.boxes
        for box in boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            if cls in DANGEROUS_OBJECTS and conf > 0.5:
                x1, y1, x2, y2 = box.xyxy[0]
                center_x = (x1 + x2) / 2

                if center_x < frame_width / 3:
                    direction = "왼쪽"
                elif center_x > frame_width * 2 / 3:
                    direction = "오른쪽"
                else:
                    direction = "정면"

                obj_name = DANGEROUS_OBJECTS[cls]
                josa = "이" if obj_name in JOSA_LIST else "가"
                alert = f"{direction}에 {obj_name}{josa} 있습니다"
                print(alert)
                text_to_speech_async(alert, direction, obj_name)
                last_alert_time = current_time
                return

def voice_command_listener():
    global last_alert_audio, mode
    print("✅ 음성 명령 리스너 시작됨")
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    print("🎤 음성 명령 대기 중... (예: '종료', '다시 안내', '큐알', '객체')")

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        while True:
            try:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)

                print("🗣️ 말하세요...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                command = recognizer.recognize_google(audio, language='ko-KR')
                command = command.lower().replace(" ", "")
                print(f"🎧 인식된 명령어: {command}")

                if "종료" in command:
                    print("🛑 프로그램 종료")
                    os._exit(0)
                elif "다시안내" in command:
                    if last_alert_audio and os.path.exists(last_alert_audio):
                        print("🔁 마지막 안내 재생 중...")
                        pygame.mixer.music.load(last_alert_audio)
                        pygame.mixer.music.play()
                elif "큐알" in command or "qr" in command:
                    mode = "qr"
                    print("🔄 QR 코드 모드로 전환됨")
                    text_to_speech_async("큐알 코드 모드로 전환되었습니다", "qr", "start")
                elif "객체" in command:
                    mode = "object"
                    print("🔄 객체 인식 모드로 전환됨")
                    text_to_speech_async("객체 인식 모드로 전환되었습니다", "object", "start")

            except sr.WaitTimeoutError:
                print("⏳ 음성 대기 timeout")
                continue
            except sr.UnknownValueError:
                print("❓ 음성을 이해하지 못함")
                continue
            except sr.RequestError as e:
                print(f"🌐 음성 인식 서버 오류: {e}")
                time.sleep(2)
                continue
            except Exception as e:
                print(f"🛑 음성 인식 오류: {e}")
                time.sleep(1)
                continue

def main():
    global mode, last_qr_data, last_qr_alert_time
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (640, 480)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.configure("preview")
    picam2.start()
    print("📷 카메라 시작됨! 'q'를 누르면 종료합니다.")

    if is_display_available():
        cv2.namedWindow("장애물 인식", cv2.WINDOW_NORMAL)

    threading.Thread(target=voice_command_listener, daemon=True).start()

    frame_count = 0
    while True:
        frame = picam2.capture_array()
        frame_count += 1

        print(f"🟡 현재 모드: {mode}")

        if mode == "object":
            if frame_count % 3 == 0:
                results = model(frame, conf=0.5)
                check_dangerous_objects(results, frame.shape[1])
                for result in results:
                    annotated = result.plot()
            else:
                annotated = frame

        elif mode == "qr":
            print("🟠 QR 모드 프레임 처리 중...")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            decoded = pyzbar.decode(gray)
            current_time = time.time()

            if decoded:
                for qr in decoded:
                    data = qr.data.decode("utf-8")
                    if data != last_qr_data or (current_time - last_qr_alert_time > QR_ALERT_INTERVAL):
                        print("📦 QR 코드 감지됨:", data)
                        last_qr_data = data
                        last_qr_alert_time = current_time

                        while pygame.mixer.music.get_busy():
                            time.sleep(0.1)

                        text_to_speech_async(f"큐알 코드 내용은 {data} 입니다", "qr", "code")
                    else:
                        print("🔁 중복 또는 너무 빠른 QR 안내 생략")

                    (x, y, w, h) = qr.rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                print("🔍 QR 코드 없음")

            annotated = frame

        if is_display_available():
            cv2.imshow("장애물 인식", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    if is_display_available():
        cv2.destroyAllWindows()
    if os.path.exists(TEMP_AUDIO):
        os.remove(TEMP_AUDIO)

if __name__ == "__main__":
    main()
