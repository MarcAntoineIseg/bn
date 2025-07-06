import asyncio
import httpx
import json

async def test_ga4_report():
    """Test du tool ask_ga4_report avec une question simple"""
    
    # URL du serveur MCP
    url = "http://localhost:8000/messages/"
    
    # Données de test
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "ask_ga4_report",
            "arguments": {
                "userId": "a164089e-e8a6-423f-a29e-e129b38bd851",
                "ga4PropertyId": "391870620",
                "question": "Combien de sessions j'ai eu cette semaine ?"
            }
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"Error: {response.text}")
                
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_ga4_report()) 