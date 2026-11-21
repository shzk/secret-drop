"""Synthetic no-secret verification of the elicitation wire-shape fixture."""
import unittest

from wire_shapes import (
    capability_advertisement,
    confirmation_form,
    credential_url_request,
    model_visible_result,
)


class ElicitationSafetyFixtureTests(unittest.TestCase):
    def test_form_schema_contains_only_destination_and_boolean(self):
        form = confirmation_form()
        self.assertEqual(form["mode"], "form")
        keys = set(form["requestedSchema"]["properties"])
        self.assertEqual(keys, {"destination", "confirm"})
        self.assertNotIn("password", keys)
        self.assertNotIn("api_key", keys)
        self.assertNotIn("token", keys)
        self.assertFalse(form["requestedSchema"]["additionalProperties"])

    def test_form_does_not_ask_for_secret_value(self):
        form = confirmation_form()
        self.assertIn("No API key or password should be entered", form["message"])
        for schema in form["requestedSchema"]["properties"].values():
            self.assertNotIn("writeOnly", schema)

    def test_url_mode_has_no_secret_form_content(self):
        url = "https://secrets.example.invalid/request/fixture-01"
        req = credential_url_request(url, protocol="2026-07-28")
        self.assertEqual(req["mode"], "url")
        self.assertEqual(req["url"], url)
        self.assertNotIn("requestedSchema", req)
        self.assertNotIn("elicitationId", req)

    def test_legacy_version_includes_id(self):
        request = credential_url_request(
            "https://secrets.example.invalid/request/fixture-01",
            protocol="2025-11-25",
        )
        self.assertTrue(request["elicitationId"])

    def test_url_rejects_credentials_query_unapproved_host_and_http(self):
        for url in (
            "http://secrets.example.invalid/request/fixture",
            "https://other.example.invalid/request/fixture",
            "https://person:pass@secrets.example.invalid/request/fixture",
            "https://secrets.example.invalid/request/fixture?token=synthetic",
            "https://secrets.example.invalid/request/fixture#private",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                credential_url_request(url, protocol="2026-07-28")

    def test_client_capabilities_differ_by_protocol_version(self):
        legacy = capability_advertisement("2025-11-25")
        modern = capability_advertisement("2026-07-28")
        self.assertIn("elicitation", legacy["capabilities"])
        self.assertIn(
            "elicitation",
            modern["_meta"]["io.modelcontextprotocol/clientCapabilities"],
        )

    def test_model_result_only_contains_status_not_value(self):
        result = model_visible_result(saved=True, variable_name="TEST_KEY")
        self.assertEqual(result["content"][0]["text"], "TEST_KEY saved locally")
        self.assertNotIn("FAKE_VALUE", repr(result))


if __name__ == "__main__":
    unittest.main()
