import unittest
from urllib.error import URLError
from clean_diagnostic_retry import fetch_with_retry

class Response:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return b"<html>ok</html>"

class RetryTests(unittest.TestCase):
    def test_transient_timeout_then_success(self):
        calls=[]
        def opener(request, timeout):
            calls.append(timeout)
            if len(calls)==1: raise TimeoutError("temporary")
            return Response()
        payload, attempts=fetch_with_retry("request", opener, sleep=lambda _: None)
        self.assertEqual(attempts,2)
        self.assertEqual(len(calls),2)
        self.assertEqual(payload,b"<html>ok</html>")

    def test_persistent_timeout_fails_closed(self):
        calls=[]
        def opener(request, timeout):
            calls.append(1)
            raise TimeoutError("unavailable")
        with self.assertRaises(TimeoutError):
            fetch_with_retry("request", opener, sleep=lambda _: None)
        self.assertEqual(len(calls),2)

    def test_urLError_retry(self):
        calls=[]
        def opener(request, timeout):
            calls.append(1)
            if len(calls)==1: raise URLError("reset")
            return Response()
        self.assertEqual(fetch_with_retry("request",opener,sleep=lambda _: None)[1],2)

    def test_bad_payload_is_never_retried(self):
        class Bad(Response):
            def read(self,n): return b""
        calls=[]
        def opener(request, timeout):
            calls.append(1)
            return Bad()
        with self.assertRaises(ValueError):
            fetch_with_retry("request",opener,sleep=lambda _: None)
        self.assertEqual(len(calls),1)

    def test_invalid_limit(self):
        with self.assertRaises(ValueError):
            fetch_with_retry("request",lambda *a,**k:Response(),attempts=5)

if __name__ == "__main__":
    unittest.main()
