from __future__ import annotations


def test_get_tax_profile_auto_creates_one(client, auth_headers):
    response = client.get("/profile/tax-profile", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {
        "date_of_birth": None,
        "occupation_sector": None,
        "is_epf_member": False,
        "estimated_annual_income": None,
    }


def test_update_tax_profile_partial_update(client, auth_headers):
    update_resp = client.put(
        "/profile/tax-profile",
        headers=auth_headers,
        json={"occupation_sector": "e_hailing", "is_epf_member": True, "estimated_annual_income": 48000},
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["occupation_sector"] == "e_hailing"
    assert body["is_epf_member"] is True
    assert body["estimated_annual_income"] == 48000.0

    # A second partial update should not clobber fields it doesn't mention.
    second_resp = client.put(
        "/profile/tax-profile", headers=auth_headers, json={"estimated_annual_income": 60000}
    )
    assert second_resp.json()["occupation_sector"] == "e_hailing"
    assert second_resp.json()["estimated_annual_income"] == 60000.0


def test_profile_requires_authentication(client):
    response = client.get("/profile/tax-profile")
    assert response.status_code == 401
