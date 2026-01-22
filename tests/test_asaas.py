import aiohttp
import asyncio

ASAAS_API_KEY = "$aact_hmlg_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OmE5OGQ3OWU0LWJmMDYtNGY4My1iNTk2LThkZmY1YjUzNGZhNTo6JGFhY2hfYWZmNDg4OGMtMmMwOC00ODg3LWEwODEtZmUyMjQ5OTlmNTBm"
ASAAS_API_URL = "https://sandbox.asaas.com/api/v3"

async def test_asaas():
    headers = {"access_token": ASAAS_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        # Test 1: List customers
        print("Testing connection to Asaas sandbox...")
        async with session.get(f"{ASAAS_API_URL}/customers", headers=headers) as resp:
            print(f"Status: {resp.status}")
            text = await resp.text()
            print(f"Response: {text[:500]}")
            
        if resp.status != 200:
            print("Error connecting to Asaas!")
            return
            
        # Test 2: Create customer
        print("\nCreating test customer...")
        customer_data = {
            "name": "Test Bot Fazendeiro",
            "email": "test@botfazendeiro.local",
            "cpfCnpj": "12345678909",  # CPF de teste
            "notificationDisabled": True
        }
        async with session.post(
            f"{ASAAS_API_URL}/customers",
            headers={**headers, "Content-Type": "application/json"},
            json=customer_data
        ) as resp:
            print(f"Status: {resp.status}")
            text = await resp.text()
            print(f"Response: {text[:500]}")
            
        # Test 3: Create PIX payment
        if resp.status == 200:
            customer = (await resp.json() if hasattr(resp, 'json') else {})
            customer_id = customer.get('id', 'cus_000007475054')
            
            print(f"\nCreating PIX charge for customer {customer_id}...")
            import datetime
            tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
            
            charge_data = {
                "customer": customer_id,
                "billingType": "PIX",
                "value": 29.90,
                "dueDate": tomorrow,
                "description": "Test Bot Fazendeiro - Mensal",
                "externalReference": f"test_{int(datetime.datetime.now().timestamp())}"
            }
            print(f"Charge data: {charge_data}")
            
            async with session.post(
                f"{ASAAS_API_URL}/payments",
                headers={**headers, "Content-Type": "application/json"},
                json=charge_data
            ) as resp:
                print(f"Status: {resp.status}")
                text = await resp.text()
                print(f"Response: {text}")
                
                if resp.status == 200:
                    charge = await resp.json() if hasattr(resp, 'json') else {}
                    if 'id' in text:
                        import json
                        charge = json.loads(text)
                        print(f"\nGetting QR Code for payment {charge['id']}...")
                        async with session.get(
                            f"{ASAAS_API_URL}/payments/{charge['id']}/pixQrCode",
                            headers=headers
                        ) as qr_resp:
                            print(f"QR Status: {qr_resp.status}")
                            qr_text = await qr_resp.text()
                            print(f"QR Response (first 200 chars): {qr_text[:200]}")

if __name__ == "__main__":
    asyncio.run(test_asaas())
