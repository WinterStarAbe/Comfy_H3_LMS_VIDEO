# 📐 MiniMax H3 影片批次高清化系統 - 技術規格與架構規範書 (Technical Specification)

## 1. 系統架構總覽 (System Architecture)

本系統採用 **Model-View-Controller (MVC)** 概念設計，分為前端展示層、業務橋接層與底層推理引擎：

```
+-------------------------------------------------------------+
|                     Frontend: Streamlit                     |
|  (app.py - UI Layout, State Management, Live Logs, Preview) |
+------------------------------+------------------------------+
                               | REST API / WebSocket
+------------------------------v------------------------------+
|                Bridge: ComfyUIBatchClient                   |
| (comfy_client.py - Directory Scanner, JSON Maper, Loop Runner)|
+------------------------------+------------------------------+
                               | HTTP POST /prompt & /history
+------------------------------v------------------------------+
|               Engine: ComfyUI Backend Server                |
|       (Port 8188 - MiniMax H3 LMS Video Upscaling)          |
+-------------------------------------------------------------+
```

---

## 2. 工作流 API 節點映射規範 (Workflow Node Mapping)

系統直接載入 `workflow_api.json`，並對以下關鍵節點進行動態參數注入：

| 節點 ID | 節點類別 (class_type) | 標題 / 作用 | 對應控制參數 |
| :--- | :--- | :--- | :--- |
| **422** | `ImpactStringSelector` | 影片路徑清單選取器 | 接收資料夾內所有 `.mp4` 絕對路徑組合成的換行字串 (`strings`) |
| **424** | `PrimitiveInt` | 序列索引計數器 | 控制當前讀取清單中的第幾個影片索引 (`value`) |
| **433** | `VHS_LoadVideoPath` | 影片載入器 | 接收被選中的影片路徑進行解碼與加載 |
| **42** | `LoraLoaderModelOnly` | LMS 模型 Lora 載入器 | 調整模型作用強度 (`strength_model`) |
| **363 / 438** | `LayerUtility: ImageScaleByAspectRatio V2` | 影像縮放器 | 控制長邊像素尺寸 (`scale_to_length`) |
| **348** | `PrimitiveStringMultiline` | 提示詞文字節點 | 動態覆寫高清化描述 Prompt (`value`) |
| **364 / 330** | `VHS_VideoCombine` | 影片輸出與合成器 | 設定輸出檔案目錄與前綴 (`filename_prefix`) |

---

## 3. 通訊與 API 互動協定 (API Protocol)

1. **提交任務 (`POST /prompt`)**：
   - 發送修改後的完整工作流 JSON 與 `client_id` 到 `http://<server>/prompt`。
   - 返回 `prompt_id`。
2. **進度監聽與事件同步 (`WebSocket /ws`)**：
   - 連線至 `ws://<server>/ws?clientId=<id>`。
   - 監聽 `executing` 事件，當節點指標歸零且 `prompt_id` 符合時判定當前影片渲染完成。
3. **結果檢索 (`GET /history/{prompt_id}`)**：
   - 任務完成後查詢 `/history/{prompt_id}`，解析 `outputs` 中的 `gifs` / `videos` 資訊。
   - 動態組合影片預覽 URL：`/view?filename=...&subfolder=...&type=output`。

---

## 4. 狀態管理與持久化規範 (State Persistence)

- **`app_settings.json`**：
  - 儲存所有使用者設定（來源目錄、輸出前綴、起始索引、批次數量、LoRA 強度、縮放尺寸、自定義 Prompt）。
  - 啟動時自動讀取，參數變動時即時自動存檔，支援 F5 與重啟無縫還原。
- **`history_input.json` / `history_output.json`**：
  - 自動記錄最近使用過的輸入與輸出目錄路徑清單（最多 10 筆），供右側下拉選單快速選取。
- **`cancel_run.flag`**：
  - 輕量標記檔案機制。點擊停止按鈕時建立此檔案，客戶端迴圈在處理每個檔案前檢查此檔案是否存在，存在即安全中斷。
