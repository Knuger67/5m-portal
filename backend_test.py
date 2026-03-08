#!/usr/bin/env python3
"""
FiveM Portal Backend API Testing Script
Tests all endpoints with authentication flow
"""
import requests
import sys
import json
from datetime import datetime
import time

class FiveMPortalTester:
    def __init__(self, base_url="https://server-whitelist-hub.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        
        # Test tracking
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.test_results = []
        
    def log_test(self, name, success, response_data=None, error_msg=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
            self.test_results.append({"test": name, "status": "PASSED", "data": response_data})
        else:
            print(f"❌ {name} - FAILED: {error_msg}")
            self.failed_tests.append({"test": name, "error": error_msg})
            self.test_results.append({"test": name, "status": "FAILED", "error": error_msg})
            
    def make_request(self, method, endpoint, **kwargs):
        """Make HTTP request with error handling"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        try:
            # Set headers and timeout
            headers = kwargs.pop('headers', {})
            headers.update({'Content-Type': 'application/json', 'User-Agent': 'FiveMPortalTester/1.0'})
            kwargs['headers'] = headers
            kwargs.setdefault('timeout', 10)
            
            print(f"   → {method} {url}")
            response = requests.request(method, url, **kwargs)
            print(f"   ← Status: {response.status_code}")
            return response
        except requests.exceptions.Timeout:
            print(f"   ⚠ Timeout for {method} {endpoint}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"   ⚠ Request error for {method} {endpoint}: {e}")
            return None
            
    def test_root_endpoint(self):
        """Test API root endpoint"""
        response = self.make_request('GET', '/')
        if response and response.status_code == 200:
            data = response.json()
            self.log_test("API Root", True, data)
            return True
        else:
            self.log_test("API Root", False, error_msg=f"Status: {response.status_code if response else 'No response'}")
            return False
            
    def test_server_status(self):
        """Test server status endpoint"""
        response = self.make_request('GET', '/server/status')
        if response and response.status_code == 200:
            data = response.json()
            required_fields = ['online', 'players_online', 'max_players', 'queue_length', 'server_name']
            missing_fields = [field for field in required_fields if field not in data]
            if not missing_fields:
                self.log_test("Server Status", True, data)
                return data
            else:
                self.log_test("Server Status", False, error_msg=f"Missing fields: {missing_fields}")
                return None
        else:
            self.log_test("Server Status", False, error_msg=f"Status: {response.status_code if response else 'No response'}")
            return None
            
    def test_stats_endpoint(self):
        """Test public stats endpoint"""
        response = self.make_request('GET', '/stats')
        if response and response.status_code == 200:
            data = response.json()
            required_fields = ['total_users', 'queue_length', 'pending_applications', 'players_online', 'max_players']
            missing_fields = [field for field in required_fields if field not in data]
            if not missing_fields:
                self.log_test("Stats Endpoint", True, data)
                return data
            else:
                self.log_test("Stats Endpoint", False, error_msg=f"Missing fields: {missing_fields}")
                return None
        else:
            self.log_test("Stats Endpoint", False, error_msg=f"Status: {response.status_code if response else 'No response'}")
            return None
            
    def test_queue_list(self):
        """Test public queue list endpoint"""
        response = self.make_request('GET', '/queue/list')
        if response and response.status_code == 200:
            data = response.json()
            if 'queue' in data and 'total' in data:
                self.log_test("Queue List", True, {"queue_count": len(data['queue']), "total": data['total']})
                return data
            else:
                self.log_test("Queue List", False, error_msg="Missing 'queue' or 'total' field")
                return None
        else:
            self.log_test("Queue List", False, error_msg=f"Status: {response.status_code if response else 'No response'}")
            return None
            
    def test_steam_login_redirect(self):
        """Test Steam login redirect (should return redirect to Steam)"""
        response = self.make_request('GET', '/auth/login', allow_redirects=False)
        if response and response.status_code in [302, 307, 308]:
            redirect_url = response.headers.get('Location', '')
            if 'steamcommunity.com' in redirect_url:
                self.log_test("Steam Login Redirect", True, {"redirect_url": redirect_url[:100] + "..."})
                return True
            else:
                self.log_test("Steam Login Redirect", False, error_msg=f"Invalid redirect URL: {redirect_url[:100]}")
                return False
        else:
            self.log_test("Steam Login Redirect", False, error_msg=f"Status: {response.status_code if response else 'No response'}")
            return False
            
    def test_protected_endpoints_without_auth(self):
        """Test that protected endpoints return 401 without authentication"""
        protected_endpoints = [
            ('GET', '/auth/me', [401]),  # Should require auth
            ('POST', '/queue/join', [401]),  # Should require auth
            ('DELETE', '/queue/leave', [401]),  # Should require auth
            ('GET', '/queue/status', [200]),  # Public endpoint that returns empty data
            ('POST', '/applications', [401, 422]),  # Should require auth or validation error
            ('GET', '/applications/my', [401]),  # Should require auth
            ('GET', '/admin/applications', [401, 403]),  # Should require auth/admin
            ('GET', '/admin/queue', [401, 403]),  # Should require auth/admin
            ('GET', '/admin/users', [401, 403])  # Should require auth/admin
        ]
        
        all_protected = True
        issues = []
        for method, endpoint, expected_codes in protected_endpoints:
            response = self.make_request(method, endpoint)
            if response and response.status_code in expected_codes:
                print(f"   ✓ {method} {endpoint}: {response.status_code} (expected)")
            else:
                all_protected = False
                actual_code = response.status_code if response else 'No response'
                issues.append(f"{method} {endpoint} returned {actual_code} instead of {expected_codes}")
                print(f"   ⚠ {method} {endpoint}: {actual_code} (expected {expected_codes})")
                
        self.log_test("Protected Endpoints Security", all_protected, 
                     error_msg="; ".join(issues) if issues else None)
        return all_protected
        
    def test_application_submission_validation(self):
        """Test application submission with invalid data (should fail validation)"""
        invalid_data = {
            "application_type": "whitelist",
            "discord_username": "",  # Empty required field
            "in_game_hours": -1,     # Invalid number
            "roleplay_experience": "",  # Empty required field
            "character_backstory": "",  # Empty required field
            "why_join": ""              # Empty required field
        }
        
        response = self.make_request('POST', '/applications', json=invalid_data)
        if response and response.status_code in [400, 401, 422]:  # Should fail validation or auth
            self.log_test("Application Validation", True, {"status": response.status_code, "has_validation": response.status_code == 422})
            return True
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_msg += f", Body: {response.text[:200]}"
                except:
                    pass
            self.log_test("Application Validation", False, error_msg=error_msg)
            return False
            
    def run_all_tests(self):
        """Run all backend tests"""
        print(f"\n🚀 Starting FiveM Portal Backend Tests")
        print(f"📡 Testing API: {self.api_url}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Basic API tests
        print("\n📋 BASIC API TESTS")
        self.test_root_endpoint()
        self.test_server_status()
        self.test_stats_endpoint()
        self.test_queue_list()
        
        # Authentication tests
        print("\n🔐 AUTHENTICATION TESTS")
        self.test_steam_login_redirect()
        self.test_protected_endpoints_without_auth()
        
        # Validation tests
        print("\n✅ VALIDATION TESTS")
        self.test_application_submission_validation()
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"✅ Passed: {self.tests_passed}/{self.tests_run}")
        print(f"❌ Failed: {len(self.failed_tests)}")
        
        if self.failed_tests:
            print(f"\n💥 FAILED TESTS:")
            for failure in self.failed_tests:
                print(f"   - {failure['test']}: {failure['error']}")
        
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": len(self.failed_tests),
            "success_rate": success_rate,
            "failures": self.failed_tests,
            "all_results": self.test_results
        }

def main():
    tester = FiveMPortalTester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    if results["failed_tests"] == 0:
        print(f"\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {results['failed_tests']} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())