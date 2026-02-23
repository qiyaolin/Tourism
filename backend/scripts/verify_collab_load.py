import asyncio
import json
import os
import random
import string

import httpx
import websockets

BASE_URL = os.getenv("ATLAS_E2E_BASE_URL", "http://localhost:8000/api/v1")
WS_BASE_URL = os.getenv("ATLAS_E2E_WS_URL", "ws://localhost:8000/api/v1")
TIMEOUT = float(os.getenv("ATLAS_E2E_TIMEOUT_SECONDS", "15"))
NUM_CLIENTS = 5
MESSAGES_PER_CLIENT = 10

def _random_phone() -> str:
    prefix = random.choice(["130", "131", "132", "155", "156", "157", "186"])
    suffix = "".join(random.choice(string.digits) for _ in range(8))
    return f"{prefix}{suffix}"

def _assert_status(resp: httpx.Response, expected: int, action: str) -> dict:
    if resp.status_code != expected:
        raise RuntimeError(f"{action} failed: {resp.status_code} {resp.text}")
    return resp.json()

def setup_test_data() -> tuple[str, str]:
    with httpx.Client(timeout=TIMEOUT) as client:
        # 1. Login
        phone = _random_phone()
        send_resp = client.post(f"{BASE_URL}/auth/send-code", json={"phone": phone})
        code = _assert_status(send_resp, 200, "send_code")["debug_code"]
        
        login_resp = client.post(f"{BASE_URL}/auth/login", json={"phone": phone, "code": code, "nickname": "loadtest"})
        token = _assert_status(login_resp, 200, "login")["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Create Itinerary
        itin_resp = client.post(
            f"{BASE_URL}/itineraries", 
            json={"title": "loadtest", "destination": "loadtest", "days": 1},
            headers=headers
        )
        itin_id = _assert_status(itin_resp, 201, "create_itin")["id"]
        
        # 3. Create Share Code
        share_resp = client.post(
            f"{BASE_URL}/itineraries/{itin_id}/collab/links",
            json={"permission": "edit", "expires_in_hours": 1},
            headers=headers
        )
        share_url = _assert_status(share_resp, 201, "create_link")["share_url"]
        share_code = share_url.split("=")[-1]
        
        return itin_id, share_code

async def simulate_client(client_id: int, itin_id: str, share_code: str, success_count: list[int]):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Login client
            phone = _random_phone()
            send_resp = await client.post(f"{BASE_URL}/auth/send-code", json={"phone": phone})
            code = send_resp.json()["debug_code"]
            login_resp = await client.post(f"{BASE_URL}/auth/login", json={"phone": phone, "code": code, "nickname": f"guest_{client_id}"})
            token = login_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            resolve_resp = await client.post(
                f"{BASE_URL}/collab/code/resolve",
                json={"code": share_code},
                headers=headers
            )
            if resolve_resp.status_code != 200:
                print(f"Client {client_id} failed to resolve code: {resolve_resp.text}")
                return
            collab_grant = resolve_resp.json()["collab_grant"]
             
        # Connect WS
        ws_url = f"{WS_BASE_URL}/itineraries/{itin_id}/collab/ws?collab_grant={collab_grant}"
        async with websockets.connect(ws_url) as ws:
            # Wait for join
            await ws.recv()
             
            # Send updates
            for i in range(MESSAGES_PER_CLIENT):
                msg = {
                    "type": "collab:update",
                    "payload": {
                        "origin": "loadtest",
                        "update": "dummy_yjs_hex_payload"
                    }
                }
                await ws.send(json.dumps(msg))
                # Simulate some typing delay
                await asyncio.sleep(random.uniform(0.01, 0.1))
                 
            success_count[0] += 1
             
    except Exception as e:
        print(f"Client {client_id} error: {repr(e)}")


async def main():
    print("Setting up test data...")
    itin_id, share_code = setup_test_data()
    print(f"Target Itinerary: {itin_id} | Code: {share_code}")
    
    print(f"Starting {NUM_CLIENTS} concurrent clients, each sending {MESSAGES_PER_CLIENT} updates...")
    success_count = [0]
    tasks = [simulate_client(i, itin_id, share_code, success_count) for i in range(NUM_CLIENTS)]
    
    await asyncio.gather(*tasks)
    
    print(f"Load test complete. Successful clients: {success_count[0]}/{NUM_CLIENTS}")
    if success_count[0] == NUM_CLIENTS:
         print("PASS: WebSocket Concurrent Edit Test.")
    else:
         print("FAIL: Some clients did not complete successfully.")

if __name__ == "__main__":
    asyncio.run(main())
