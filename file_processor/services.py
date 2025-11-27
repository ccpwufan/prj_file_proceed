import os
import requests
from django.conf import settings
from .models import ImageAnalysis, AnalysisResult

class DifyAPIService:
    def __init__(self, api_key=None):
        self.api_key = api_key if api_key is not None else settings.DIFY_API_KEY
        self.user = settings.DIFY_USER
        self.server = settings.DIFY_SERVER
        # 从环境变量读取超时设置，默认为60秒
        self.timeout = int(os.getenv('DIFY_TIMEOUT', '60'))
    
    def upload_image(self, image_path):
        """Upload image to Dify and return file_id"""
        url = f'{self.server}/v1/files/upload'
        headers = {'Authorization': f'Bearer {self.api_key}'}
        
        ext = os.path.splitext(image_path)[-1].lower()
        mime = 'image/png' if ext == '.png' else 'image/jpeg'
        
        with open(image_path, 'rb') as file:
            files = {'file': (os.path.basename(image_path), file, mime)}
            data = {'user': self.user}
            response = requests.post(url, headers=headers, files=files, data=data, timeout=self.timeout)
        
        if response.status_code == 201:
            return response.json()['id']
        else:
            raise Exception(f"Upload failed: {response.status_code} - {response.text}")
    
    def run_workflow(self, file_id):
        """Run Dify workflow and return analysis result"""
        url = f"{self.server}/v1/workflows/run"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
            "user": self.user,
            "response_mode": "blocking"
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
        
        if response.status_code == 200:
            resp_json = response.json()
            wf_status = resp_json.get("data", {}).get("status")
            if wf_status == "succeeded":
                outputs = resp_json.get("data", {}).get("outputs", {})
                return True, outputs.get("result", {}), ""
            else:
                error_info = resp_json.get("data", {}).get("error") or resp_json.get("message")
                return False, {}, error_info
        else:
            return False, {}, f"Workflow failed: {response.status_code}"
    
    def run_workflow_files(self, file_ids):
        """Run Dify workflow with multiple files and return analysis result"""
        url = f"{self.server}/v1/workflows/run"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建文件列表，符合Dify workflow的file-list类型要求
        files_list = []
        for file_id in file_ids:
            files_list.append({
                "type": "image",
                "transfer_method": "local_file",
                "upload_file_id": file_id
            })
        
        data = {
            "inputs": {
                "upload": files_list
            },
            "user": self.user,
            "response_mode": "blocking"
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
        
        if response.status_code == 200:
            resp_json = response.json()
            wf_status = resp_json.get("data", {}).get("status")
            if wf_status == "succeeded":
                outputs = resp_json.get("data", {}).get("outputs", {})
                return True, outputs.get("result", {}), ""
            else:
                error_info = resp_json.get("data", {}).get("error") or resp_json.get("message")
                return False, {}, error_info
        else:
            return False, {}, f"Workflow failed: {response.status_code}"
    
    def analyze_images(self, analysis_id):
        """Analyze multiple images for a given analysis"""
        try:
            analysis = ImageAnalysis.objects.get(id=analysis_id)
            analysis.status = 'processing'
            analysis.save()
            
            for image in analysis.images.all():
                try:
                    # Upload image to Dify
                    file_id = self.upload_image(image.image_file.path)
                    
                    # Run workflow
                    success, result_data, error_msg = self.run_workflow(file_id)
                    
                    if success:
                        # Save result to database
                        AnalysisResult.objects.create(
                            analysis=analysis,
                            image=image,
                            result_data=result_data
                        )
                    else:
                        # Save error result
                        AnalysisResult.objects.create(
                            analysis=analysis,
                            image=image,
                            result_data={"error": error_msg}
                        )
                
                except Exception as e:
                    # Save exception result
                    AnalysisResult.objects.create(
                        analysis=analysis,
                        image=image,
                        result_data={"error": str(e)}
                    )
            
            analysis.status = 'completed'
            analysis.save()
            
        except Exception as e:
            analysis.status = 'failed'
            analysis.save()
            print(f"Analysis failed: {str(e)}")
    
    def analyze_single_image(self, image):
        """Analyze a single image and return result data"""
        try:
            # Upload image to Dify
            file_id = self.upload_image(image.file_detail_filename.path)
            
            # Run workflow
            success, result_data, error_msg = self.run_workflow(file_id)
            
            if success:
                return result_data
            else:
                return {"error": error_msg}
                
        except Exception as e:
            return {"error": str(e)}
