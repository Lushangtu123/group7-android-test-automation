import subprocess
from types import SimpleNamespace
import unittest
from group7_auto.android_network import check_android_network

class AndroidNetworkTests(unittest.TestCase):
    def test_hostname_http_204_is_verified_and_command_is_scoped(self):
        calls=[]
        def run(command,**kwargs):
            calls.append((command,kwargs));return SimpleNamespace(returncode=0,stdout='HTTP/1.1 204 No Content\n\n',stderr='')
        result=check_android_network('/sdk/adb','emulator-5554',run=run)
        self.assertTrue(result['hostname_http_204'])
        self.assertEqual(calls[0][0][:3],['/sdk/adb','-s','emulator-5554'])
        self.assertIn('connectivitycheck.gstatic.com',calls[0][0])

    def test_portal_redirect_is_not_internet_success(self):
        result=check_android_network('adb','device',run=lambda *a,**k:SimpleNamespace(returncode=0,stdout='HTTP/1.1 302 Found',stderr=''))
        self.assertFalse(result['hostname_http_204'])

    def test_nonzero_exit_does_not_accept_a_stale_204_string(self):
        result=check_android_network('adb','device',run=lambda *a,**k:SimpleNamespace(returncode=1,stdout='HTTP/1.1 204 No Content',stderr='failure'))
        self.assertFalse(result['hostname_http_204'])

    def test_timeout_is_evidence_not_a_retry(self):
        calls=[]
        def run(*a,**k):calls.append(a);raise subprocess.TimeoutExpired(a[0],8)
        result=check_android_network('adb','device',run=run)
        self.assertEqual(result['status'],'PROBE_TIMEOUT')
        self.assertFalse(result['hostname_http_204']);self.assertEqual(len(calls),1)
