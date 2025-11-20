import requests

url = "http://localhost:8000/upload-dataset"
files = {
    "file": ("sample.csv", open("sample.csv", "rb"), "text/csv")
}

response = requests.post(url, files=files)
print(response.status_code)
print(response.json())
