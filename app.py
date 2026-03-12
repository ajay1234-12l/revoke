import asyncio
import httpx
import jwt
import urllib3
import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import my_pb2
import output_pb2


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="FF Token Revoke Ultra Fast API")


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

def encrypt_message(plaintext):
    """AES Encryption for Protobuf Data"""
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    padded_message = pad(plaintext, AES.block_size)
    return cipher.encrypt(padded_message)

async def fetch_open_id(client: httpx.AsyncClient, access_token: str):
    
    try:
        uid_url = "https://prod-api.reward.ff.garena.com/redemption/api/auth/inspect_token/"
        uid_headers = {
            "authority": "prod-api.reward.ff.garena.com",
            "method": "GET",
            "path": "/redemption/api/auth/inspect_token/",
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "access-token": access_token,
            "cookie": "_gid=GA1.2.444482899.1724033242; _ga_XB5PSHEQB4=GS1.1.1724040177.1.1.1724040732.0.0.0; token_session=cb73a97aaef2f1c7fd138757dc28a08f92904b1062e66c; _ga_KE3SY7MRSD=GS1.1.1724041788.0.0.1724041788.0; _ga_RF9R6YT614=GS1.1.1724041788.0.0.1724041788.0; _ga=GA1.1.1843180339.1724033241; apple_state_key=817771465df611ef8ab00ac8aa985783; _ga_G8QGMJPWWV=GS1.1.1724049483.1.1.1724049880.0.0; datadome=HBTqAUPVsbBJaOLirZCUkN3rXjf4gRnrZcNlw2WXTg7bn083SPey8X~ffVwr7qhtg8154634Ee9qq4bCkizBuiMZ3Qtqyf3Isxmsz6GTH_b6LMCKWF4Uea_HSPk;",
            "origin": "https://reward.ff.garena.com",
            "referer": "https://reward.ff.garena.com/",
            "sec-ch-ua": '"Not.A/Brand";v="99", "Chromium";v="124"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        uid_res = await client.get(uid_url, headers=uid_headers, timeout=10.0)
        
        if uid_res.status_code != 200:
            return None, "Garena API Error"
            
        uid_data = uid_res.json()
        uid = uid_data.get("uid")

        if not uid:
            return None, "UID extraction failed"

        openid_url = "https://topup.pk/api/auth/player_id_login"
        openid_headers = { 
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-MM,en-US;q=0.9,en;q=0.8",
            "Content-Type": "application/json",
            "Origin": "https://topup.pk",
            "Referer": "https://topup.pk/",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Android WebView";v="138"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Linux; Android 15; RMX5070 Build/UKQ1.231108.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.7204.157 Mobile Safari/537.36",
            "X-Requested-With": "mark.via.gp",
            "Cookie": "source=mb; region=PK; mspid2=13c49fb51ece78886ebf7108a4907756; _fbp=fb.1.1753985808817.794945392376454660; language=en; datadome=WQaG3HalUB3PsGoSXY3TdcrSQextsSFwkOp1cqZtJ7Ax4YkiERHUgkgHlEAIccQO~w8dzTGM70D9SzaH7vymmEqOrVeX5pIsPVE22Uf3TDu6W3WG7j36ulnTg2DltRO7; session_key=hq02g63z3zjcumm76mafcooitj7nc79y",
        }
        payload = {"app_id": 100067, "login_id": str(uid)}
        openid_res = await client.post(openid_url, headers=openid_headers, json=payload, timeout=10.0)
        
        if openid_res.status_code != 200:
            return None, "Topup.pk Error"

        open_id = openid_res.json().get("open_id")
        return open_id, None

    except Exception as e:
        return None, str(e)

@app.get('/')
async def home():
    return {"message": "FF Token Revoke FastAPI is Running", "status": "Active"}

@app.get('/logout')
async def process_logout(access_token: str = Query(..., description="Garena Access Token")):

    async with httpx.AsyncClient(verify=False) as client:
        
        open_id, error = await fetch_open_id(client, access_token)
        if error:
            return {"message": "FAILED already logout or token not work"}

        decoded_token = {}
        p_name = "Unknown"
        jwt_token_val = None
        platforms = [8, 3, 4, 6]  

        login_headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/octet-stream",
            "Expect": "100-continue",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB52"
        }

        for platform_type in platforms:
            game_data = my_pb2.GameData()
            game_data.timestamp = "2024-12-05 18:15:32"
            game_data.game_name = "free fire"
            game_data.game_version = 1
            game_data.version_code = "1.120.2"
            game_data.os_info = "Android OS 9 / API-28"
            game_data.device_type = "Handheld"
            game_data.network_provider = "Verizon Wireless"
            game_data.connection_type = "WIFI"
            game_data.screen_width = 1280
            game_data.screen_height = 960
            game_data.dpi = "240"
            game_data.cpu_info = "ARMv7 VFPv3 NEON VMH | 2400 | 4"
            game_data.total_ram = 5951
            game_data.gpu_name = "Adreno (TM) 640"
            game_data.gpu_version = "OpenGL ES 3.0"
            game_data.user_id = "Google|74b585a9-0268-4ad3-8f36-ef41d2e53610"
            game_data.ip_address = "172.190.111.97"
            game_data.language = "en"
            game_data.open_id = open_id
            game_data.access_token = access_token
            game_data.platform_type = platform_type
            game_data.field_99 = str(platform_type)
            game_data.field_100 = str(platform_type)

            serialized_data = game_data.SerializeToString()
            encrypted_data = encrypt_message(serialized_data)

            try:
                login_res = await client.post(
                    "https://loginbp.ggblueshark.com/MajorLogin", 
                    content=encrypted_data, 
                    headers=login_headers, 
                    timeout=5.0
                )
                
                if login_res.status_code == 200:
                    example_msg = output_pb2.Garena_420()
                    example_msg.ParseFromString(login_res.content)
                    jwt_token_val = getattr(example_msg, "token", None)
                    
                    if jwt_token_val:
                        decoded_token = jwt.decode(jwt_token_val, options={"verify_signature": False})
                        p_id = decoded_token.get("external_type")
                        p_name = PLATFORM_MAP.get(p_id, f"Unknown ({p_id})")
                        break
            except:
                continue

        logout_msg = "FAILED"
        try:
            refresh_token = "1380dcb63ab3a077dc05bdf0b25ba4497c403a5b4eae96d7203010eafa6c83a8"
            logout_url = f"https://100067.connect.garena.com/oauth/logout?access_token={access_token}&refresh_token={refresh_token}"
            resp = await client.get(logout_url, timeout=10.0)
            
            if resp.status_code == 200 and "error" not in resp.text:
                logout_msg = "LOGOUT SUCCESS"
        except:
            logout_msg = "FAILED"

        if logout_msg == "FAILED":
            return {"message": "FAILED already logout or token not work"}

        return {
            "status": "success",
            "message": logout_msg,
            "nickname": decoded_token.get("nickname", "N/A"),
            "account_id": decoded_token.get("account_id", "N/A"),
            "region": decoded_token.get("lock_region", "N/A"),
            "platform": p_name,
            "open_id": open_id,
            "Credit": "@Flexbasei",
            "Power By": "@spideerio_yt"
        }

if __name__ == '__main__':
    uvicorn.run("app:app", host="0.0.0.0", port=1080, workers=4, access_log=False)
