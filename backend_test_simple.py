#!/usr/bin/env python3
"""
Simplified FiveM Portal Backend API Testing Script
"""
import requests
import sys
import json
from datetime import datetime

def test_endpoint(method, url, expected_codes, description, data=None):
    """Test a single endpoint"""
    try:
        print(f"Testing {description}...")
        
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'}, timeout=10)
        elif method == 'DELETE':
            response = requests.delete(url, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
            
        print(f"   Status: {response.status_code}")
        
        if response.status_code in expected_codes:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED (expected {expected_codes}, got {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    base_url = "https://server-whitelist-hub.preview.emergentagent.com/api"
    
    print("🚀 FiveM Portal Backend API Tests")
    print(f"📡 Base URL: {base_url}")
    print("=" * 60)
    
    tests = [
        # Basic endpoints
        ('GET', f'{base_url}/', [200], 'API Root'),
        ('GET', f'{base_url}/server/status', [200], 'Server Status'),
        ('GET', f'{base_url}/stats', [200], 'Stats'),
        ('GET', f'{base_url}/queue/list', [200], 'Queue List'),
        
        # Authentication endpoints
        ('GET', f'{base_url}/auth/login', [302, 307, 308], 'Steam Login Redirect'),
        ('GET', f'{base_url}/auth/me', [401], 'Auth Me (Protected)'),
        
        # Queue endpoints
        ('POST', f'{base_url}/queue/join', [401], 'Queue Join (Protected)'),
        ('DELETE', f'{base_url}/queue/leave', [401], 'Queue Leave (Protected)'),
        ('GET', f'{base_url}/queue/status', [200], 'Queue Status'),
        
        # Application endpoints  
        ('POST', f'{base_url}/applications', [401, 422], 'Applications Submit', {}),
        ('GET', f'{base_url}/applications/my', [401], 'My Applications (Protected)'),
        
        # Admin endpoints
        ('GET', f'{base_url}/admin/applications', [401, 403], 'Admin Applications (Protected)'),
        ('GET', f'{base_url}/admin/queue', [401, 403], 'Admin Queue (Protected)'),
        ('GET', f'{base_url}/admin/users', [401, 403], 'Admin Users (Protected)'),
    ]
    
    passed = 0
    total = len(tests)
    
    print()
    for method, url, expected_codes, description, *args in tests:
        data = args[0] if args else None
        if test_endpoint(method, url, expected_codes, description, data):
            passed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️ {total-passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())