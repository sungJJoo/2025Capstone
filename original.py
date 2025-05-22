import cv2
import numpy as np
from ultralytics import YOLO
from gtts import gTTS
import pygame
import os
import time
from picamera2 import Picamera2
import threading


# YOLO 모델 로드
print("YOLO 모델을 로드하는 중...")
model = YOLO("yolov8n.pt")
print("YOLO 모델 로드 완료!")

# pygame 초기화
pygame.mixer.init()
TEMP_AUDIO = "temp_alert"

# 위험 객체 정의
DANGEROUS_OBJECTS = {
    0: "사람", 1: "자전거", 2: "자동차", 3: "오토바이", 5: "버스",
    7: "트럭", 9: "신호등", 13: "정지 표지판", 15: "벤치",
    17: "고양이", 18: "개", 27: "우산"
}
JOSA_LIST = {"사람", "트럭", "신호등", "정지 표지판", "우산"}
last_alert_time = 0
ALERT_INTERVAL = 3  # 초

def is_display_available():
    return os.environ.get("DISPLAY") is not None

def text_to_speech(text, direction, object):
    try:
        filename = TEMP_AUDIO + direction + object + ".mp3"
        tts = gTTS(text=text, lang='ko')
        tts.save(filename)
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        # ❌ 이 줄 삭제! → 동기 대기 안 함
        # while pygame.mixer.music.get_busy():
        #     pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"TTS 오류: {e}")

def text_to_speech_async(text, direction, object):
    threading.Thread(
        target=text_to_speech,
        args=(text, direction, object),
        daemon=True  # 프로그램 종료 시 자동 정리됨
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
                #text_to_speech(alert, direction, obj_name)
                last_alert_time = current_time
                return

def main():
    # picamera2 설정
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (640, 480)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.configure("preview")
    picam2.start()
    print("카메라 시작됨! 'q'를 누르면 종료합니다.")

    # OpenCV 창 설정 (디스플레이 환경일 때만)
    if is_display_available():
        cv2.namedWindow("장애물 인식", cv2.WINDOW_NORMAL)

    frame_count = 0

    while True:
        frame = picam2.capture_array()
        frame_count += 1

        if frame_count % 3 == 0:  # 3프레임 중 1번만 실행
            results = model(frame, conf=0.5)
            check_dangerous_objects(results, frame.shape[1])
            for result in results:
                annotated = result.plot()
        else:
            annotated = frame

        if is_display_available():
            cv2.imshow("장애물 인식", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("GUI 없음, 화면 출력 생략")
    # 종료 시 처리
    if is_display_available():
        cv2.destroyAllWindows()

    if os.path.exists(TEMP_AUDIO):
        os.remove(TEMP_AUDIO)


if __name__ == "__main__":
    main()
