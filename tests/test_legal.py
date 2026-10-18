"""Pre-launch #5: final Terms & Privacy (Canada, 16+), served with the support contact filled in."""
import main


def test_legal_page_is_final_and_has_no_template_left(api, monkeypatch):
    for path in ("/terms", "/privacy"):
        html = api.client.get(path).text
        assert "{{" not in html and "Draft" not in html
        assert "at least 16 years old" in html and "PIPEDA" in html and 'id="contact"' in html
        assert 'href="#privacy"' in html                     # contents links work without JS
    monkeypatch.setattr(main, "SUPPORT_EMAIL", "help@example.com")
    assert 'mailto:help@example.com' in api.client.get("/terms").text


def test_signup_states_the_age_and_both_documents(api):
    html = api.client.get("/").text
    assert "16 or older" in html and 'href="/terms"' in html and 'href="/privacy"' in html
