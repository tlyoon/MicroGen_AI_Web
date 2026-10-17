"""SDK-to-wire contract verification, intercepting HTTP before any network call.

This exercise uses the ACTUAL installed google-genai serializer and response
parser with a DUMMY API key. No real Gemini HTTP request can be transmitted.
"""
from __future__ import annotations

import base64
import io
import json
import unittest
import wave
from unittest.mock import patch

try:
    import httpx
    from google import genai
    from google.genai import types
    HAVE_SDK = True
except ImportError:
    HAVE_SDK = False

from selenium_pipeline.tts_interactions_trial import (
    MODEL, VOICE, interactions_request, verify_wav,
)


def fake_wav():
    out=io.BytesIO()
    with wave.open(out,"wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x01\x20"*24000)
    return out.getvalue()


@unittest.skipUnless(HAVE_SDK, "Installed google-genai/httpx SDK required")
class RealSdkWireContractTests(unittest.TestCase):
    def make_client(self):
        # The API key is deliberately nonfunctional; HTTP send is intercepted.
        return genai.Client(
            api_key="DUMMY_NO_NETWORK_TEST",
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1)))

    def test_real_sdk_serializes_and_decodes_exact_flash_lite_wav(self):
        calls=[]
        expected=fake_wav()
        def intercept(request,*args,**kwargs):
            body=json.loads(request.content.decode("utf-8"))
            calls.append((request.method,request.url.path,body))
            return httpx.Response(200,request=request,json={
                "id":"interactions/offline_fixture",
                "status":"completed",
                "model":MODEL,
                "output_audio":{
                    "data":base64.b64encode(expected).decode("ascii"),
                    "mime_type":"audio/wav",
                }})
        client=self.make_client()
        try:
            with patch.object(client._api_client._httpx_client,
                              "send", side_effect=intercept):
                response=client.interactions.create(**interactions_request())
            audio,metrics=verify_wav(response)
        finally:
            client.close()
        self.assertEqual(len(calls),1,"SDK must emit one HTTP attempt")
        method,path,body=calls[0]
        self.assertEqual((method,path),("POST","/v1beta/interactions"))
        self.assertEqual(body["model"],MODEL)
        self.assertEqual(body["response_format"],{"type":"audio"})
        self.assertEqual(body["generation_config"],
                         {"speech_config":[{"voice":VOICE}]})
        self.assertEqual(body["input"][0]["content"][0]["type"],"text")
        self.assertEqual(body["input"][0]["content"][0]["annotations"][0]["type"],
                         "speech_metadata")
        self.assertEqual(audio,expected)
        self.assertEqual(metrics["duration_seconds"],1.0)
        self.assertEqual(metrics["sample_rate"],24000)

    def test_sdk_does_not_retry_server_rejection_with_attempts_one(self):
        observed=[]
        def reject(request,*args,**kwargs):
            observed.append(request.url.path)
            return httpx.Response(403,request=request,json={
                "error":{"code":403,"message":"OFFLINE_FAKE_REJECTION",
                         "status":"PERMISSION_DENIED"}})
        client=self.make_client()
        try:
            with patch.object(client._api_client._httpx_client,
                              "send", side_effect=reject):
                with self.assertRaises(Exception):
                    client.interactions.create(**interactions_request())
        finally:
            client.close()
        self.assertEqual(observed,["/v1beta/interactions"])


if __name__=="__main__":
    unittest.main()
