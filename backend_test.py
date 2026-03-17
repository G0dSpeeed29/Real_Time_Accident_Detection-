import requests
import sys
import json
from datetime import datetime
import time

class AccidentDetectionTester:
    def __init__(self, base_url="https://realtime-safety-2.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_sources = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:200]}")

            try:
                return success, response.json() if response.text else {}
            except:
                return success, {"raw_response": response.text}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_auth_login(self):
        """Test login with demo admin credentials"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@demo.com", "password": "password123"}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   Logged in as: {response['user']['name']}")
            return True
        return False

    def test_create_youtube_source(self, youtube_url):
        """Create a YouTube video source"""
        success, response = self.run_test(
            "Create YouTube Source",
            "POST",
            "video-sources",
            200,
            data={
                "name": f"Test YouTube Stream {datetime.now().strftime('%H%M%S')}",
                "type": "youtube",
                "url": youtube_url,
                "location": "Test Location"
            }
        )
        if success and 'id' in response:
            self.created_sources.append(response['id'])
            print(f"   Created source ID: {response['id']}")
            return response['id']
        return None

    def test_get_video_sources(self):
        """Get all video sources"""
        success, response = self.run_test(
            "Get Video Sources",
            "GET",
            "video-sources",
            200
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} video sources")
            return success
        return False

    def test_start_detection(self, source_id):
        """Start detection on a video source"""
        success, response = self.run_test(
            "Start Detection",
            "POST",
            f"detection/start/{source_id}",
            200
        )
        if success:
            print(f"   Detection started for source {source_id}")
            return True
        return False

    def test_stop_detection(self, source_id):
        """Stop detection on a video source"""
        success, response = self.run_test(
            "Stop Detection",
            "POST",
            f"detection/stop/{source_id}",
            200
        )
        if success:
            print(f"   Detection stopped for source {source_id}")
            return True
        return False

    def test_delete_video_source(self, source_id):
        """Delete a video source"""
        success, response = self.run_test(
            "Delete Video Source",
            "DELETE",
            f"video-sources/{source_id}",
            200
        )
        if success:
            print(f"   Deleted source {source_id}")
            if source_id in self.created_sources:
                self.created_sources.remove(source_id)
            return True
        return False

    def test_youtube_stream_extraction(self, youtube_url):
        """Test YouTube stream URL extraction"""
        success, response = self.run_test(
            "YouTube Stream Extraction",
            "POST",
            f"youtube/extract?youtube_url={youtube_url}",
            200
        )
        if success and 'stream_url' in response:
            print(f"   Extracted stream URL: {response['stream_url'][:100]}...")
            return True
        return False

    def test_get_accidents(self):
        """Get all accidents"""
        success, response = self.run_test(
            "Get Accidents",
            "GET",
            "accidents",
            200
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} accident records")
            return True
        return False

    def test_analytics_stats(self):
        """Get analytics stats"""
        success, response = self.run_test(
            "Analytics Stats",
            "GET",
            "analytics/stats",
            200
        )
        if success and 'total_accidents' in response:
            print(f"   Total accidents: {response['total_accidents']}")
            print(f"   Active sources: {response.get('active_sources', 0)}")
            return True
        return False

    def cleanup(self):
        """Clean up created sources"""
        for source_id in self.created_sources[:]:
            print(f"\n🧹 Cleaning up source {source_id}...")
            try:
                # Stop detection first
                self.test_stop_detection(source_id)
                time.sleep(1)
                # Then delete
                self.test_delete_video_source(source_id)
            except:
                pass

def main():
    # YouTube URLs for testing
    youtube_urls = [
        "https://www.youtube.com/live/VR-x3HdhKLQ",
        "https://www.youtube.com/live/AQMaw6OAeHY", 
        "https://www.youtube.com/live/8JCk5M_xrBs",
        "https://www.youtube.com/live/Z5Hq9o8768g"
    ]

    tester = AccidentDetectionTester()
    
    print("🚀 Starting Accident Detection System Tests")
    print("=" * 60)

    # Test authentication
    if not tester.test_auth_login():
        print("❌ Login failed, stopping tests")
        return 1

    # Test basic endpoints
    tester.test_get_video_sources()
    tester.test_get_accidents()
    tester.test_analytics_stats()

    # Test YouTube stream extraction
    test_youtube_url = youtube_urls[0]
    print(f"\n📺 Testing YouTube integration with URL: {test_youtube_url}")
    tester.test_youtube_stream_extraction(test_youtube_url)

    # Test video source creation and deletion workflow
    print(f"\n🎥 Testing video source lifecycle...")
    source_id = tester.test_create_youtube_source(test_youtube_url)
    if source_id:
        # Test starting detection
        if tester.test_start_detection(source_id):
            time.sleep(3)  # Let detection run briefly
            # Test stopping detection
            tester.test_stop_detection(source_id)
            time.sleep(1)
        
        # Test deletion (should stop active stream first)
        tester.test_delete_video_source(source_id)

    # Test another YouTube URL
    if len(youtube_urls) > 1:
        print(f"\n🎬 Testing second YouTube URL...")
        source_id2 = tester.test_create_youtube_source(youtube_urls[1])
        if source_id2:
            tester.test_delete_video_source(source_id2)

    # Cleanup any remaining sources
    tester.cleanup()

    # Print results
    print(f"\n📊 Test Results")
    print("=" * 60)
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())