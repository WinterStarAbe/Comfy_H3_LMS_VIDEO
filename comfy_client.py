import os
import json
import uuid
import time
import requests
websocket = None
try:
    import websocket
except ImportError:
    pass

class ComfyUIBatchClient:
    def __init__(self, server_address="127.0.0.1:8188", workflow_path="workflow_api.json"):
        self.server_address = server_address
        self.workflow_path = workflow_path
        self.client_id = str(uuid.uuid4())

    def check_connection(self):
        try:
            res = requests.get(f"http://{self.server_address}/system_stats", timeout=3)
            return res.status_code == 200
        except Exception:
            return False

    def load_workflow(self):
        with open(self.workflow_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_video_files(self, folder_path):
        if not os.path.exists(folder_path):
            return []
        return sorted([
            os.path.abspath(os.path.join(folder_path, f))
            for f in os.listdir(folder_path)
            if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))
        ])

    def queue_prompt(self, workflow):
        url = f"http://{self.server_address}/prompt"
        data = {"prompt": workflow, "client_id": self.client_id}
        req = requests.post(url, json=data)
        return req.json()

    def wait_for_prompt_and_get_output(self, prompt_id, timeout=3600):
        ws_url = f"ws://{self.server_address}/ws?clientId={self.client_id}"
        start_time = time.time()
        executed_successfully = False

        if websocket is not None:
            try:
                ws = websocket.WebSocket()
                ws.connect(ws_url, timeout=5)
                while time.time() - start_time < timeout:
                    out = ws.recv()
                    if isinstance(out, str):
                        message = json.loads(out)
                        if message.get("type") == "executing":
                            data = message.get("data", {})
                            if data.get("node") is None and data.get("prompt_id") == prompt_id:
                                executed_successfully = True
                                break
                ws.close()
            except Exception as e:
                print(f"WebSocket warning: {e}, falling back to polling history...")
                executed_successfully = True
        else:
            time.sleep(5)
            executed_successfully = True

        output_video_url = None
        if executed_successfully:
            try:
                hist_res = requests.get(f"http://{self.server_address}/history/{prompt_id}", timeout=5)
                if hist_res.status_code == 200:
                    hist_data = hist_res.json()
                    if prompt_id in hist_data:
                        outputs = hist_data[prompt_id].get("outputs", {})
                        for node_id, node_output in outputs.items():
                            media_list = node_output.get("gifs", []) or node_output.get("videos", [])
                            if media_list:
                                item = media_list[0]
                                filename = item.get("filename")
                                subfolder = item.get("subfolder", "")
                                file_type = item.get("type", "output")
                                output_video_url = (
                                    f"http://{self.server_address}/view?"
                                    f"filename={requests.utils.quote(filename)}&"
                                    f"subfolder={requests.utils.quote(subfolder)}&"
                                    f"type={file_type}"
                                )
                                break
            except Exception as e:
                print(f"Failed to fetch history output: {e}")

        return executed_successfully, output_video_url

    def run_batch(self, folder_path, custom_prompt=None, output_prefix="video/upscale", 
                  lms_lora_strength=0.78, scale_to_length=1024, 
                  start_index=0, batch_count=0, cancel_flag_path="cancel_run.flag", 
                  progress_callback=None):
        
        if os.path.exists(cancel_flag_path):
            try:
                os.remove(cancel_flag_path)
            except:
                pass

        video_files = self.get_video_files(folder_path)
        if not video_files:
            if progress_callback:
                progress_callback("error", "找不到任何影片檔案，請檢查資料夾路徑。", None)
            return start_index

        workflow = self.load_workflow()

        paths_lines = []
        for v in video_files:
            clean_path = v.replace("/", "\\")
            paths_lines.append(f'"{clean_path}"')
        
        workflow["422"]["inputs"]["strings"] = "\n".join(paths_lines)

        if custom_prompt and "348" in workflow:
            workflow["348"]["inputs"]["value"] = custom_prompt

        if "42" in workflow:
            workflow["42"]["inputs"]["strength_model"] = float(lms_lora_strength)

        if "363" in workflow:
            workflow["363"]["inputs"]["scale_to_length"] = int(scale_to_length)
        if "438" in workflow:
            workflow["438"]["inputs"]["scale_to_length"] = int(scale_to_length)

        if "364" in workflow:
            workflow["364"]["inputs"]["filename_prefix"] = output_prefix
        if "330" in workflow:
            workflow["330"]["inputs"]["filename_prefix"] = f"{output_prefix}_comparison"

        total_files = len(video_files)
        start_idx = max(0, min(start_index, total_files - 1))
        if batch_count and batch_count > 0:
            end_idx = min(start_idx + batch_count, total_files)
        else:
            end_idx = total_files

        target_indices = list(range(start_idx, end_idx))
        run_total = len(target_indices)

        if progress_callback:
            progress_callback("info", f"📁 總資料夾檔案數: {total_files} | 本次預定執行: {run_total} 個影片 (起始索引: {start_idx})...", None)

        last_processed_idx = start_idx

        for count, idx in enumerate(target_indices):
            if os.path.exists(cancel_flag_path):
                if progress_callback:
                    progress_callback("warning", "🛑 偵測到用戶中斷請求,批次任務已安全停止！", None)
                break

            video_path = video_files[idx]
            filename = os.path.basename(video_path)
            
            if progress_callback:
                progress_callback("progress", f"▶️ [進度: {count+1}/{run_total}] 正在處理: {filename} (索引: {idx})", None)

            workflow["424"]["inputs"]["value"] = idx

            try:
                res = self.queue_prompt(workflow)
                prompt_id = res.get("prompt_id")
                if not prompt_id:
                    if progress_callback:
                        progress_callback("error", f"❌ [{filename}] 提交失敗: {res}", None)
                    continue

                success, video_url = self.wait_for_prompt_and_get_output(prompt_id)
                
                if success:
                    last_processed_idx = idx
                    if progress_callback:
                        progress_callback("success", f"✅ [完成: {count+1}/{run_total}] 成功處理: {filename}", video_url)
                else:
                    if progress_callback:
                        progress_callback("error", f"❌ [{filename}] 執行逾時或失敗", None)

            except Exception as e:
                if progress_callback:
                    progress_callback("error", f"🚨 [{filename}] 發生異常: {str(e)}", None)

        if os.path.exists(cancel_flag_path):
            try:
                os.remove(cancel_flag_path)
            except:
                pass

        # 計算下一次執行的建議起始索引 (若順利完成當前批次，則指向下一支影片)
        next_start_index = last_processed_idx + 1 if last_processed_idx >= start_idx else start_idx
        if next_start_index >= total_files:
            next_start_index = total_files - 1 if total_files > 0 else 0

        if progress_callback:
            progress_callback("done", f"🎉 本次批次序列執行完畢！建議下次起始索引已更新為: {next_start_index}", None)

        return next_start_index
