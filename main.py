import base64
import cv2
import numpy as np
import httpx
import asyncio
import os
from PIL import Image
from config.config import gemini
import google.generativeai as genai

NIM_Mhswa = None
Psswrd = None

os.makedirs("re-encryption", exist_ok=True)

client = httpx.AsyncClient(timeout=30)

headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Referer': 'https://auth.sso.udb.ac.id/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
    #'Cookie': 'udb_sopingi=10134af6d4985a7b70064a8d9e30d07a'
}

genai.configure(api_key=gemini)
model = genai.GenerativeModel("gemini-2.5-flash")

async def get_and_solve_captcha():
    print("\n🔄 Mengambil captcha baru...")
    response = await client.get('https://auth.sso.udb.ac.id/renewcaptcha')

    if response.status_code != 200:
        print("❌ Request captcha gagal:", response.status_code)
        return None, None

    data = response.json()
    token = data.get('newtoken')
    image = data.get('newimage')
    print(" Token:", token)

    if not image:
        return token, None

    if image.startswith("data:image/png;base64,"):
        image = image.split(",")[1]

    img_data = base64.b64decode(image)
    original_img_path = "re-encryption/decoded.png"
    clean_img_path = "re-encryption/clean.png"

    with open(original_img_path, "wb") as f:
        f.write(img_data)

    img = cv2.imread(original_img_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
    img[mask > 0] = [255, 255, 255]

    cv2.imwrite(clean_img_path, img)

    prompt = "tanpa penjelasan apapun!. sebutkan 5 angka yang ada di dalam foto tersebut, tanpa koma tanpa titik, contoh : 12345"

    with open(clean_img_path, "rb") as f:
        img_bytes = f.read()

    response = model.generate_content([
        prompt,
        {"mime_type": "image/png", "data": img_bytes}
    ])

    captcha_text = response.text.strip().replace(" ", "").replace("\n", "")
    print(" Hasil OCR Gemini:", captcha_text)
    return token, captcha_text


async def login(token, captcha_value):
    data = {
        'url': '',
        'timezone': '7',
        'skin': 'bootstrap',
        'token': token,
        'user': NIM_Mhswa,
        'password': Psswrd,
        'captcha': captcha_value,
    }

    response = await client.post('https://auth.sso.udb.ac.id/?MA', data=data)
    print(" LOGIN Status:", response.status_code)
    return response.text

async def bigdashboard():
    response = await client.get('https://auth.sso.udb.ac.id/')
    print(" BigDashboard Status:", response.status_code)
    return response.text

async def main():
    global NIM_Mhswa, Psswrd
    
    NIM_Mhswa = int(input("Masukan NIM : "))
    Psswrd = input("Masukan Password : ")
    attempt = 0

    while True:
        attempt += 1
        print(f"\n==============================")
        print(f"🔁 Percobaan LOGIN #{attempt}")
        print(f"==============================")

        token, captcha_text = await get_and_solve_captcha()

        if not token or not captcha_text or len(captcha_text) != 5:
            print("⚠️ Captcha tidak valid, retry...\n")
            continue

        result = await login(token, captcha_text)

        if "captcha" in result.lower() or "wrong" in result.lower():
            print("❌ Login gagal, captcha salah! retry...\n")
            continue

        print("\n LOGIN BERHASIL!")
        print(" Response:", result)

        dashboard = await bigdashboard()
        print(" Dashboard HTML:", dashboard[:300], "...")  # optional
        break


if __name__ == "__main__":
    asyncio.run(main())
