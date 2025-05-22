from flask import Flask
import qrcode
import threading

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <html>
    <head><meta charset="UTF-8"><title>메뉴 안내</title></head>
    <body>
        <h1>🍱 오늘의 메뉴</h1>
        <ul>
            <li>김밥</li>
            <li>떡볶이</li>
            <li>라면</li>
        </ul>
    </body>
    </html>
    """

def run_flask():
    app.run(host="0.0.0.0", port=5000)

def generate_qr(ip_address="192.168.35.89", port=5000):
    url = f"http://{ip_address}:{port}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save("qr_link.png")
    print(f"✅ QR 코드가 생성되었습니다: qr_link.png (접속 주소: {url})")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    generate_qr()

    print("🌐 Flask 서버 실행 중입니다. Ctrl+C로 종료")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("🛑 종료됨")
