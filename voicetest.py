import speech_recognition as sr
r = sr.Recognizer()
with sr.Microphone() as source:
    print("말하세요:")
    audio = r.listen(source)
    print("인식 중...")
    print(r.recognize_google(audio, language="ko-KR"))
