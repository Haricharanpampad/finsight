import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000")

# 1. Login
login_res = client.post("/api/auth/login", json={"email": "demo@finsight.app", "password": "demo12345"})
assert login_res.status_code == 200, f"Login failed: {login_res.text}"
token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("Login successful!")

# 2. Upload CSV
csv_content = b"""Date,Description,Debit,Credit,Balance
2026-10-12,Airtel Broadband Office,2499.00,,50000
2026-10-13,Client consulting payment,,35000.00,85000
"""
files = {"file": ("bank_statement.csv", csv_content, "text/csv")}
upload_res = client.post("/api/transactions/upload", files=files, headers=headers)
assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
data = upload_res.json()
print("Upload parsed successfully:", data["total"], "items")
assert len(data["items"]) == 2
assert data["items"][0]["category"] == "Utilities"
assert data["items"][1]["type"] == "revenue"

# 3. Bulk insert
bulk_res = client.post("/api/transactions/bulk", json=data["items"], headers=headers)
assert bulk_res.status_code == 201, f"Bulk failed: {bulk_res.text}"
inserted = bulk_res.json()
print("Bulk insert successful:", len(inserted), "inserted")

# 4. Clean up test transactions
for tx in inserted:
    del_res = client.delete(f"/api/transactions/{tx['id']}", headers=headers)
    assert del_res.status_code == 204

print("Universal Ingestion end-to-end test passed completely!")
