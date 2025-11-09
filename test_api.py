"""
Quick API Test Script
Tests the parking reservation API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8003"

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✓ Health Check: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Health Check Failed: {e}")
        return False

def test_parse_arrival():
    """Test parse-arrival endpoint"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/parse-arrival",
            json={"utterance": "today at 3 PM"},
            timeout=5
        )
        print(f"✓ Parse Arrival: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Parse Arrival Failed: {e}")
        return False

def test_parse_duration():
    """Test parse-duration endpoint"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/parse-duration",
            json={"utterance": "2 hours 30 minutes"},
            timeout=5
        )
        print(f"✓ Parse Duration: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Parse Duration Failed: {e}")
        return False

def test_quote():
    """Test quote endpoint"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/quote",
            json={
                "vehicle_reg": "TEST123",
                "vehicle_type": "car",
                "duration_hours": 2
            },
            timeout=5
        )
        result = response.json()
        print(f"✓ Quote: Price ${result['price_cents']/100:.2f} for {result['duration_hours']} hours")
        return True
    except Exception as e:
        print(f"✗ Quote Failed: {e}")
        return False

def test_create_reservation():
    """Test create reservation endpoint"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/reservations",
            json={
                "customer_name": "Test User",
                "vehicle_reg": "TEST456",
                "vehicle_type": "car",
                "duration_hours": 2
            },
            timeout=5
        )
        result = response.json()
        print(f"✓ Reservation Created: Confirmation {result['confirmation_code']}, Spot {result['spot_label']}")
        return True
    except Exception as e:
        print(f"✗ Create Reservation Failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("Testing RapidPark API")
    print("="*60)
    print()
    
    tests = [
        ("Health Check", test_health),
        ("Parse Arrival Time", test_parse_arrival),
        ("Parse Duration", test_parse_duration),
        ("Get Quote", test_quote),
        ("Create Reservation", test_create_reservation),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting: {name}")
        print("-" * 40)
        if test_func():
            passed += 1
        else:
            failed += 1
    
    print()
    print("="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n🎉 All tests passed! Your API is working correctly!")
        print("\nNext steps:")
        print("1. Edit .env and add your Cartesia API key")
        print("2. Set up ngrok: ngrok http 8003")
        print("3. Run: python scripts/setup_cartesia.py")
        print("4. Configure Twilio and test voice calls")
    else:
        print(f"\n⚠️ {failed} test(s) failed. Make sure the server is running on port 8003")
        print("Run: .venv\\Scripts\\uvicorn.exe app.main:app --reload --port 8003")
