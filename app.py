import os
import json
import time
import importlib
import streamlit as st
import comfy_client

importlib.reload(comfy_client)
from comfy_client import ComfyUIBatchClient

st.set_page_config(
    page_title="MiniMax H3 影片批次高清化面板",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 MiniMax H3 影片批次高清化 Web 原型系統")
st.markdown("本系統直接對接您的 ComfyUI 工作流 API (`T8star-MiniMax H3 LMS视频高清化API.json`)，支援自動掃描資料夾、設定持久化記憶、日誌與預覽完整保留、批次索引自動遞增、即時中斷與影片預覽。")

CANCEL_FLAG = "cancel_run.flag"
HISTORY_INPUT_FILE = "history_input.json"
HISTORY_OUTPUT_FILE = "history_output.json"
SETTINGS_FILE = "app_settings.json"

def load_history(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(file_path, path_str, max_items=10):
    if not path_str:
        return
    history = load_history(file_path)
    if path_str in history:
        history.remove(path_str)
    history.insert(0, path_str)
    history = history[:max_items]
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_settings(settings_dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings_dict, f, ensure_ascii=False, indent=2)
    except:
        pass

default_prompt = (
    "Restore and enhance this early low-resolution video with a natural realistic color grade, "
    "removing haze and overexposure, improving optical transparency and local contrast. "
    "Concentrate high-frequency clarity boost strictly on non-skin details: eyes, eyelashes, eyebrows, "
    "lips, hair strands, clothing fibers, and background structures."
)

saved_settings = load_settings()

if "current_start_index" not in st.session_state:
    st.session_state.current_start_index = saved_settings.get("start_index", 0)

if "folder_path_val" not in st.session_state:
    st.session_state.folder_path_val = saved_settings.get("folder_path", r"E:\WorkSpace\AIVideo\output\rika_11")

if "output_prefix_val" not in st.session_state:
    st.session_state.output_prefix_val = saved_settings.get("output_prefix", "video/upscale")

if "batch_count_val" not in st.session_state:
    st.session_state.batch_count_val = saved_settings.get("batch_count", 5)

if "lms_strength_val" not in st.session_state:
    st.session_state.lms_strength_val = saved_settings.get("lms_lora_strength", 0.78)

if "scale_length_val" not in st.session_state:
    st.session_state.scale_length_val = saved_settings.get("scale_to_length", 1024)

if "custom_prompt_val" not in st.session_state:
    st.session_state.custom_prompt_val = saved_settings.get("custom_prompt", default_prompt)

if "execution_logs" not in st.session_state:
    st.session_state.execution_logs = []

if "latest_video_url" not in st.session_state:
    st.session_state.latest_video_url = None

def on_folder_select():
    selected = st.session_state.get("hist_folder_select")
    if selected and selected != "(歷史選取...)":
        st.session_state.folder_path_val = selected

def on_output_select():
    selected = st.session_state.get("hist_output_select")
    if selected and selected != "(歷史選取...)":
        st.session_state.output_prefix_val = selected

st.sidebar.header("⚙️ 系統設定與連線")
server_address = st.sidebar.text_input("ComfyUI 伺服器位址", value="127.0.0.1:8188")

client = ComfyUIBatchClient(server_address=server_address)

is_connected = client.check_connection()
if is_connected:
    st.sidebar.success("🟢 ComfyUI 服務連線正常")
else:
    st.sidebar.error("🔴 無法連線到 ComfyUI，請確認服務已啟動並允許跨域存取")

st.sidebar.markdown("---")
st.sidebar.info("💡 **提示**：所有設定參數與進度會自動存檔於 `app_settings.json`，重啟或重新整理網頁後直接還原上次狀態。")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📁 批次處理與路徑歷史紀錄")
    
    input_col1, input_col2 = st.columns([3, 1])
    with input_col1:
        folder_path = st.text_input(
            "輸入來源影片資料夾絕對路徑",
            value=st.session_state.folder_path_val,
            help="例如：E:\\WorkSpace\\AIVideo\\output\\rika_11"
        )
        st.session_state.folder_path_val = folder_path

    with input_col2:
        input_history = load_history(HISTORY_INPUT_FILE)
        st.selectbox(
            "歷史輸入目錄",
            options=["(歷史選取...)"] + input_history,
            key="hist_folder_select",
            on_change=on_folder_select
        )

    output_col1, output_col2 = st.columns([3, 1])
    with output_col1:
        output_prefix = st.text_input(
            "輸出檔案目錄/前綴名稱 (filename_prefix)",
            value=st.session_state.output_prefix_val,
            help="ComfyUI 輸出檔案的前綴路徑，例如 'video/upscale'"
        )
        st.session_state.output_prefix_val = output_prefix

    with output_col2:
        output_history = load_history(HISTORY_OUTPUT_FILE)
        st.selectbox(
            "歷史輸出目錄",
            options=["(歷史選取...)"] + output_history,
            key="hist_output_select",
            on_change=on_output_select
        )

    total_found = 0
    if os.path.exists(folder_path):
        v_files = client.get_video_files(folder_path)
        total_found = len(v_files)
        st.success(f"📂 資料夾驗證成功！共偵測到 **{total_found}** 個影片檔案（全域索引 0 ~ {max(0, total_found-1)}）。")
        with st.expander("點此檢視待處理影片清單與索引對照"):
            for idx, vf in enumerate(v_files):
                st.text(f"[{idx}] {os.path.basename(vf)}")
    else:
        st.warning("⚠️ 指定的資料夾路徑不存在或無權限存取。")

    st.markdown("---")
    st.subheader("🔢 序列控制 (PrimitiveInt & 批次範圍)")

    seq_col1, seq_col2 = st.columns(2)
    with seq_col1:
        if total_found > 0 and st.session_state.current_start_index >= total_found:
            st.session_state.current_start_index = total_found - 1

        start_index = st.number_input(
            "PrimitiveInt 起始索引 (Start Index)",
            min_value=0,
            max_value=max(0, total_found - 1),
            value=int(st.session_state.current_start_index),
            step=1,
            help="對應工作流節點 424 (PrimitiveInt)。每次批次執行完畢後會自動更新為下一支影片索引。"
        )
        st.session_state.current_start_index = start_index

    with seq_col2:
        batch_count = st.number_input(
            "本次執行序列數量 (Batch Count)",
            min_value=0,
            max_value=max(1, total_found if total_found > 0 else 1000),
            value=int(st.session_state.batch_count_val),
            step=1,
            help="設定本次執行要處理多少個檔案。設為 0 代表從起始索引一路處理到目錄結尾。"
        )
        st.session_state.batch_count_val = batch_count

    if total_found > 0:
        effective_end = min(start_index + batch_count, total_found) if batch_count > 0 else total_found
        current_run_total = max(0, effective_end - start_index)
        st.info(f"📊 **目前序列狀態摘要**：總計 {total_found} 檔 | 起始索引: **{start_index}** | 預計本次處理: **{current_run_total}** 個檔案（索引範圍: {start_index} ~ {max(start_index, effective_end-1)}）")

    st.markdown("---")
    st.subheader("🎛️ 模型與高清化參數")

    param_col1, param_col2 = st.columns(2)
    with param_col1:
        lms_lora_strength = st.slider(
            "LMS LoRA 模型強度 (LoraLoaderModelOnly)",
            min_value=0.0,
            max_value=2.0,
            value=float(st.session_state.lms_strength_val),
            step=0.02,
            help="調整 Node 42 的 strength_model 参数"
        )
        st.session_state.lms_strength_val = lms_lora_strength

    with param_col2:
        scale_to_length = st.number_input(
            "影像縮放長邊尺寸 (Scale to Length)",
            min_value=256,
            max_value=3840,
            value=int(st.session_state.scale_length_val),
            step=64,
            help="調整 Node 363 / 438 的 scale_to_length"
        )
        st.session_state.scale_length_val = scale_to_length

    custom_prompt = st.text_area(
        "✨ 自定義高清化提示詞 (Prompt Override)",
        value=st.session_state.custom_prompt_val,
        height=120
    )
    st.session_state.custom_prompt_val = custom_prompt

with col2:
    st.subheader("🚀 執行控制台")
    st.markdown("確認設定後，可點擊執行或隨時中斷。")
    
    start_btn = st.button("開始批次高清化", type="primary", width="stretch", disabled=not is_connected)
    stop_btn = st.button("🛑 停止執行 (Abort)", type="secondary", width="stretch")

    if stop_btn:
        with open(CANCEL_FLAG, "w") as f:
            f.write("cancel")
        st.warning("⚠️ 已發送中斷請求，當前正在執行的影片完成後將安全停止。")

current_settings = {
    "folder_path": folder_path,
    "output_prefix": output_prefix,
    "start_index": int(start_index),
    "batch_count": int(batch_count),
    "lms_lora_strength": float(lms_lora_strength),
    "scale_to_length": int(scale_to_length),
    "custom_prompt": custom_prompt
}
save_settings(current_settings)

st.markdown("---")
preview_col1, preview_col2 = st.columns([1, 1])

with preview_col1:
    st.subheader("📊 即時執行日誌")
    log_container = st.empty()
    progress_bar = st.progress(0)
    
    if st.session_state.execution_logs:
        full_log = "\n".join(st.session_state.execution_logs[-30:])
        log_container.text_area("即時執行記錄", value=full_log, height=320, key="persistent_log_display")

with preview_col2:
    st.subheader("📺 當前成功影片預覽 (Live Preview)")
    video_preview_container = st.empty()
    
    if st.session_state.latest_video_url:
        with video_preview_container.container():
            st.success("🎉 最近生成的高清化影片：")
            try:
                st.video(st.session_state.latest_video_url)
            except:
                pass
            st.markdown(f"📥 **[點此直接開啟/下載生成影片]({st.session_state.latest_video_url})**")

class StreamlitCallback:
    def __init__(self, log_placeholder, p_bar, video_placeholder):
        self.log_placeholder = log_placeholder
        self.p_bar = p_bar
        self.video_placeholder = video_placeholder

    def __call__(self, status_type, message, video_url=None):
        st.session_state.execution_logs.append(message)
        full_log = "\n".join(st.session_state.execution_logs[-30:])
        self.log_placeholder.text_area("即時執行記錄", value=full_log, height=320, key=f"log_box_{time.time()}")
        
        if video_url:
            st.session_state.latest_video_url = video_url
            with self.video_placeholder.container():
                st.success("🎉 產生最新高清化影片：")
                time.sleep(1.0)
                try:
                    st.video(video_url)
                except Exception as e:
                    st.warning(f"內嵌播放器載入失敗: {e}")
                st.markdown(f"📥 **[點此直接開啟/下載生成影片]({video_url})**")

if start_btn:
    if not os.path.exists(folder_path):
        st.error("錯誤：影片資料夾路徑不存在！")
    else:
        save_history(HISTORY_INPUT_FILE, folder_path)
        save_history(HISTORY_OUTPUT_FILE, output_prefix)

        st.session_state.execution_logs = []
        st.session_state.latest_video_url = None

        importlib.reload(comfy_client)
        from comfy_client import ComfyUIBatchClient
        fresh_client = ComfyUIBatchClient(server_address=server_address)

        cb = StreamlitCallback(log_container, progress_bar, video_preview_container)
        
        try:
            next_idx = fresh_client.run_batch(
                folder_path=folder_path,
                custom_prompt=custom_prompt,
                output_prefix=output_prefix,
                lms_lora_strength=lms_lora_strength,
                scale_to_length=scale_to_length,
                start_index=int(st.session_state.current_start_index),
                batch_count=int(batch_count),
                cancel_flag_path=CANCEL_FLAG,
                progress_callback=cb
            )
            if next_idx is not None:
                st.session_state.current_start_index = next_idx
            
            current_settings["start_index"] = int(st.session_state.current_start_index)
            save_settings(current_settings)

            st.success(f"🎉 批次任務執行完畢！起始索引已自動更新為：{st.session_state.current_start_index}")
        except Exception as e:
            st.error(f"執行過程中發生錯誤: {str(e)}")
