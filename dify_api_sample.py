import os
import requests
import openpyxl
from datetime import datetime

# 配置区
API_KEY = "app-hHgjeWQQtQ1T03MoTaodXvji"
USER = "seanc"
DIFY_SERVER = "https://api.dify.ai"
DIR_PATH = "output_images"
# 结果文件名加时间后缀
RESULT_FILE = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

# 字段名与 Dify 输出保持一致，全部英文简洁
FIELDS = [
    "invoice_title",
    "invoice_code",
    "issue_date",
    "buyer_name",
    "buyer_tax_id",
    "seller_name",
    "seller_tax_id",
    "items",
    "total_amount",
    "total_tax",
    "total_with_tax",
    "total_with_tax_in_words", 
    "remarks",
    "issuer"
]

def upload_image(file_path, api_key):
    url = f'{DIFY_SERVER}/v1/files/upload'
    headers = {'Authorization': f'Bearer {api_key}'}
    ext = os.path.splitext(file_path)[-1].lower()
    mime = 'image/png'if ext == '.png'else'image/jpeg'
    with open(file_path, 'rb') as file:
        files = {'file': (os.path.basename(file_path), file, mime)}
        data = {'user': USER}
        response = requests.post(url, headers=headers, files=files, data=data)
    if response.status_code == 201:
        print(f"[上传成功] {file_path}")
        resp = response.json()
        return resp['id']
    else:
        print(f"[上传失败] {file_path}，状态码: {response.status_code}，返回: {response.text}")
        return None

def run_workflow(file_id, api_key):
    url = f"{DIFY_SERVER}/v1/workflows/run"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "inputs": {
            "upload": {
                "type": "image",
                "transfer_method": "local_file",
                "upload_file_id": file_id
            }
        },
        "user": USER,
        "response_mode": "blocking"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        resp_json = response.json()
        wf_status = resp_json.get("data", {}).get("status")
        if wf_status == "succeeded":
            outputs = resp_json.get("data", {}).get("outputs", {})
            return True, outputs, ""
        else:
            error_info = resp_json.get("data", {}).get("error") or resp_json.get("message")
            return False, {}, error_info
    else:
        return False, {}, f"Failed to execute workflow, status code: {response.status_code}"

def batch_process_images_to_excel(dir_path, result_file):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["filename"] + FIELDS + ["error"])
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        if not os.path.isfile(file_path) or not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        print(f"\n处理文件: {file_path}")
        file_id = upload_image(file_path, API_KEY)
        if not file_id:
            ws.append([filename] + [""for _ in FIELDS] + ["上传失败"])
            continue
        success, outputs, error_info = run_workflow(file_id, API_KEY)
        print(f"outputs for {filename}: {outputs}")  # 调试信息
        if success:
            result = outputs.get("result", {})
            print(f"result for {filename}: {result}")  # 调试信息
            row = [filename] + [result.get(field, "") for field in FIELDS] + [""]
        else:
            row = [filename] + [""for _ in FIELDS] + [error_info]
        ws.append(row)
    wb.save(result_file)
    print(f"\n所有结果已写入 {result_file}")

if __name__ == "__main__":
    batch_process_images_to_excel(DIR_PATH, RESULT_FILE) 