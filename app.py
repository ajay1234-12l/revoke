import asyncio
import httpx
import jwt
import urllib3
from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

import my_pb2
import output_pb2

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ---------------- CONFIG ----------------
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV = b'6oyZDr22E3ychjM%'

PLATFORM_MAP = {
    3: "Facebook",
    4: "Guest",
    5: "VK",
    6: "Huawei",
    8: "Google",
    11: "X (Twitter)",
    13: "AppleId",
}

# ---------------- UTILS ----------------
def encrypt_message(data: bytes) -> bytes:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(data, AES.block_size))


async def fetch_open_id(access_token: str):
    try:
        async with httpx.AsyncClient(verify=False) as client:

            uid_headers = {
                "access-token": access_token,
                "accept": "application/json",
                "user-agent": "Mozilla/5.0"
            }

            uid_res = await client.get(
                "https://prod-api.reward.ff.garena.com/redemption/api/auth/inspect_token/",
                headers=uid_headers,
                timeout=10
            )

            if uid_res.status_code != 200:
                return None

            uid = uid_res.json().get("uid")
            if not uid:
                return None

            payload = {"app_id": 100067, "login_id": str(uid)}

            openid_res = await client.post(
                "https://topup.pk/api/auth/player_id_login",
                json=payload,
                timeout=10
            )

            if openid_res.status_code != 200:
                return None

            return openid_res.json().get("open_id")

    except:
        return None


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return jsonify({
        "message": "FF Token Revoke Flask API Running",
        "status": "Active"
    })


@app.route("/logout")
def logout():
    access_token = request.args.get("access_token")
    if not access_token:
        return jsonify({"message": "access_token required"}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    open_id = loop.run_until_complete(fetch_open_id(access_token))

    if not open_id:
        return jsonify({"message": "FAILED already logout or token not work"})

    decoded_token = {}
    platform_name = "Unknown"

    login_headers = {
        "User-Agent": "Dalvik/2.1.0",
        "Content-Type": "application/octet-stream",
        "ReleaseVersion": "OB52"
    }

    platforms = [8, 3, 4, 6]

    async def try_login():
        nonlocal decoded_token, platform_name

        async with httpx.AsyncClient(verify=False) as client:
            for platform in platforms:
                game = my_pb2.GameData()
                game.open_id = open_id
                game.access_token = access_token
                game.platform_type = platform

                encrypted = encrypt_message(game.SerializeToString())

                try:
                    res = await client.post(
                        "https://loginbp.ggblueshark.com/MajorLogin",
                        content=encrypted,
                        headers=login_headers,
                        timeout=5
                    )

                    if res.status_code == 200:
                        out = output_pb2.Garena_420()
                        out.ParseFromString(res.content)

                        if out.token:
                            decoded_token = jwt.decode(
                                out.token,
                                options={"verify_signature": False}
                            )
                            platform_name = PLATFORM_MAP.get(
                                decoded_token.get("external_type"),
                                "Unknown"
                            )
                            return True
                except:
                    continue
        return False

    success = loop.run_until_complete(try_login())

    if not success:
        return jsonify({"message": "FAILED already logout or token not work"})

    # ---- LOGOUT CALL ----
    try:
        refresh_token = "1380dcb63ab3a077dc05bdf0b25ba4497c403a5b4eae96d7203010eafa6c83a8"
        logout_url = (
            f"https://100067.connect.garena.com/oauth/logout"
            f"?access_token={access_token}&refresh_token={refresh_token}"
        )

        loop.run_until_complete(httpx.AsyncClient().get(logout_url))
    except:
        pass

    return jsonify({
        "status": "success",
        "message": "LOGOUT SUCCESS",
        "nickname": decoded_token.get("nickname", "N/A"),
        "account_id": decoded_token.get("account_id", "N/A"),
        "region": decoded_token.get("lock_region", "N/A"),
        "platform": platform_name,
        "open_id": open_id,
        "Credit": "@Flexbasei",
        "Power By": "@spideerio_yt"
    })


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1080, debug=False)
