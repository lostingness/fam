from flask import Flask, request, jsonify
import requests
import threading
import time
import os
import json

app = Flask(__name__)

# CONFIGURATION - Use environment variables for security
OFFICIAL_API_HOST = "https://westeros.famapp.in"
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "eyJlbmMiOiJBMjU2Q0JDLUhTNTEyIiwiZXBrIjp7Imt0eSI6Ik9LUCIsImNydiI6Ilg0NDgiLCJ4IjoiTzZPcTlrYTFndUM1RzR6Q2tZNl9SUlpDVUhQSVh6YlNxVDRWZGswUmIxbWkxbU9weEFxT3RhTnpfVUw5VTRHSnJ2U0FPM2o0N3ZVIn0sImFsZyI6IkVDREgtRVMifQ..OL146WtUeW9Zzb8HMqcqyA.qvM9f3ZKhNjpVSg5DlGn8m6XzBqbtBnJM9rzmV20vLBiq-kc44DRWkRNZZMIuFug8_SGc_YkzNSMXX6n5PoidVqtvXSw2IXNOtUMnkTHMxWDrw_4HBe7yEnhsHhMThs_SwBCtf3-i8PGQR26uZPjdu2CArDwBYQE5xIgXnL1YhowqxB56zSoaogthIdifzjinyAHiy3umPWKDtIWvAMkxMY6vga_2XKGWXPuczbshTBaxyOqWK2dsxOT0JKNg0zcLfQyvkUWKu18NbPVecqkXyEqk44vIAHimnZSJgdyOhZ12-Jc1MHcFOCcKIBSsgPHR1j18cZUoMaQov8t2Fmz_HBt6EWlC8-l22UWPOXAiKJtVfExM21qyQvg8KpbKSq5.odC-dcS9MfZ0CnvE4gTepLtbi4BWaur0GAr47_ik848")
DEVICE_ID = os.environ.get("DEVICE_ID", "6c9b73a9c1a1b1f1")
USER_AGENT = os.environ.get("USER_AGENT", "RMX3987 | Android 15 | Dalvik/2.1.0 | RE5CA3L1 | 0B615941675870616C92D328811D418C04BAC95D | 3.11.5 (Build 525) | 2WMHJNQDVF")

# Initialize session
SESSION = None
FAM_ID_MAPPING = {}

def init_session():
    """Initialize session with headers"""
    global SESSION
    if SESSION is None:
        SESSION = requests.Session()
        SESSION.headers.update({
            "host": "westeros.famapp.in",
            "user-agent": USER_AGENT,
            "x-device-details": USER_AGENT,
            "x-app-version": "525",
            "x-platform": "1",
            "device-id": DEVICE_ID,
            "authorization": f"Token {AUTH_TOKEN}",
            "accept-encoding": "gzip",
            "content-type": "application/json; charset=UTF-8"
        })

def fetch_blocked_list():
    """Fetch blocked list"""
    init_session()
    try:
        response = SESSION.get(
            f"{OFFICIAL_API_HOST}/user/blocked_list/",
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error fetching blocked list: {e}")
        return None

def find_user_in_list(fam_id, blocked_data):
    """Find user in blocked list"""
    if not blocked_data or 'results' not in blocked_data:
        return None

    fam_id_clean = fam_id.replace('@fam', '').lower()

    # Check cache first
    if fam_id in FAM_ID_MAPPING:
        phone = FAM_ID_MAPPING[fam_id]
        for user in blocked_data['results']:
            if user and user.get('contact'):
                contact = user['contact']
                if contact.get('phone_number') == phone:
                    return user

    # Search in list
    for user in blocked_data['results']:
        if user and user.get('contact'):
            contact = user['contact']
            name = contact.get('name', '').lower()

            if fam_id_clean in name:
                phone = contact.get('phone_number', '')
                FAM_ID_MAPPING[fam_id] = phone
                return user

            if 'send' in fam_id_clean:
                name_part = fam_id_clean.replace('send', '').replace('2', '').replace('3', '').strip()
                if name_part and name_part in name:
                    phone = contact.get('phone_number', '')
                    FAM_ID_MAPPING[fam_id] = phone
                    return user

    return None

def instant_unblock(fam_id):
    """INSTANT unblock in background thread"""
    def unblock_task():
        try:
            # Small delay to ensure API got the block
            time.sleep(0.5)
            init_session()

            unblock_payload = {"block": False, "vpa": fam_id}
            response = SESSION.post(
                f"{OFFICIAL_API_HOST}/user/vpa/block/",
                json=unblock_payload,
                timeout=5
            )

            if response.status_code == 200:
                print(f"[AUTO-UNBLOCK] ✓ Instantly unblocked: {fam_id}")
            else:
                print(f"[AUTO-UNBLOCK] ✗ Failed: {fam_id} - {response.status_code}")
        except Exception as e:
            print(f"[AUTO-UNBLOCK ERROR] {fam_id}: {e}")

    # Start unblock in background
    thread = threading.Thread(target=unblock_task, daemon=True)
    thread.start()

@app.route('/')
def home():
    return jsonify({
        "message": "Fam ID to Number API",
        "endpoint": "/get-number?id=username@fam",
        "status": "active",
        "version": "1.0",
        "author": "Your API",
        "credits": "Using your provided credentials"
    })

@app.route('/get-number', methods=['GET'])
def get_number():
    """MAIN ENDPOINT - Instant auto-unblock"""
    fam_id = request.args.get('id')

    if not fam_id:
        return jsonify({"error": "Missing 'id' parameter"}), 400

    if not fam_id.endswith('@fam'):
        return jsonify({"error": "Invalid Fam ID format. Must end with @fam"}), 400

    # Step 1: Check if already in blocked list
    blocked_data = fetch_blocked_list()

    if blocked_data and 'results' in blocked_data:
        user = find_user_in_list(fam_id, blocked_data)

        if user:
            contact = user['contact']
            phone = contact.get('phone_number')
            FAM_ID_MAPPING[fam_id] = phone

            # INSTANT AUTO-UNBLOCK (background)
            instant_unblock(fam_id)

            return jsonify({
                "status": True,
                "fam_id": fam_id,
                "name": contact.get('name'),
                "phone": phone,
                "type": user.get('type'),
                "source": "local_cache"
            })

    # Step 2: Block to get info
    block_payload = {"block": True, "vpa": fam_id}

    try:
        init_session()
        block_response = SESSION.post(
            f"{OFFICIAL_API_HOST}/user/vpa/block/",
            json=block_payload,
            timeout=10
        )

        if block_response.status_code != 200:
            return jsonify({
                "error": f"Block failed: {block_response.status_code}",
                "message": "Unable to block user. Token might be invalid."
            }), 500

        # Step 3: Get updated list
        updated_data = fetch_blocked_list()

        if not updated_data or 'results' not in updated_data:
            return jsonify({"error": "Failed to fetch updated list"}), 500

        # Step 4: Find newest user
        if updated_data['results']:
            newest_user = updated_data['results'][0]

            if newest_user and newest_user.get('contact'):
                contact = newest_user['contact']
                phone = contact.get('phone_number')
                FAM_ID_MAPPING[fam_id] = phone

                # INSTANT AUTO-UNBLOCK (background)
                instant_unblock(fam_id)

                return jsonify({
                    "status": True,
                    "fam_id": fam_id,
                    "name": contact.get('name'),
                    "phone": phone,
                    "type": newest_user.get('type'),
                    "source": "new_block"
                })

        return jsonify({
            "status": False,
            "fam_id": fam_id,
            "error": "No contact info found after blocking",
            "message": "User might not exist or token has no permission"
        })

    except Exception as e:
        return jsonify({"error": f"Request failed: {str(e)}"}), 500

@app.route('/blocked', methods=['GET'])
def blocked_list():
    """View blocked list"""
    data = fetch_blocked_list()

    if not data:
        return jsonify({"error": "Failed to fetch blocked list"}), 500

    users = []
    if 'results' in data:
        for user in data['results']:
            if user and user.get('contact'):
                contact = user['contact']
                users.append({
                    "name": contact.get('name'),
                    "phone": contact.get('phone_number'),
                    "type": user.get('type')
                })

    return jsonify({
        "count": len(users),
        "users": users
    })

@app.route('/unblock-all', methods=['POST'])
def unblock_all():
    """Unblock all users - Use with caution"""
    data = fetch_blocked_list()
    
    if not data or 'results' not in data:
        return jsonify({"error": "Failed to fetch blocked list"}), 500
    
    unblocked_count = 0
    failed_count = 0
    
    for user in data['results']:
        if user and user.get('contact'):
            contact = user['contact']
            vpa = contact.get('name', '')
            
            if vpa and '@fam' in vpa:
                try:
                    unblock_payload = {"block": False, "vpa": vpa}
                    response = SESSION.post(
                        f"{OFFICIAL_API_HOST}/user/vpa/block/",
                        json=unblock_payload,
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        unblocked_count += 1
                        time.sleep(0.1)  # Small delay to avoid rate limiting
                    else:
                        failed_count += 1
                except:
                    failed_count += 1
    
    return jsonify({
        "status": True,
        "message": f"Unblocked {unblocked_count} users, failed: {failed_count}",
        "unblocked": unblocked_count,
        "failed": failed_count
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        init_session()
        response = SESSION.get(f"{OFFICIAL_API_HOST}/user/blocked_list/", timeout=5)
        
        if response.status_code == 200:
            return jsonify({
                "status": "healthy",
                "timestamp": time.time(),
                "token_status": "valid",
                "message": "API is working and token is valid"
            })
        else:
            return jsonify({
                "status": "unhealthy",
                "timestamp": time.time(),
                "token_status": "invalid",
                "error_code": response.status_code
            }), 500
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e)
        }), 500

@app.route('/test-token', methods=['GET'])
def test_token():
    """Test if token is working"""
    init_session()
    
    # Test with a small request
    try:
        response = SESSION.get(f"{OFFICIAL_API_HOST}/user/blocked_list/", timeout=5)
        
        return jsonify({
            "token_valid": response.status_code == 200,
            "status_code": response.status_code,
            "message": "Token is valid" if response.status_code == 200 else "Token might be invalid",
            "device_id": DEVICE_ID,
            "user_agent": USER_AGENT[:50] + "..." if len(USER_AGENT) > 50 else USER_AGENT
        })
    except Exception as e:
        return jsonify({
            "token_valid": False,
            "error": str(e),
            "message": "Token test failed"
        }), 500

# Vercel requirement
application = app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
