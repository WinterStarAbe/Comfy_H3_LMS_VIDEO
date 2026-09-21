# 🎬 MiniMax H3 影片批次高清化 Web 應用系統 (ComfyUI Automation Panel)

基於 ComfyUI 官方 REST API 與 MiniMax H3 LMS 高清化工作流（`T8star-MiniMax H3 LMS视频高清化API.json`）打造的輕量級、響應式 **Streamlit 批次自動化處理 Web 應用**。

---

## ✨ 核心功能特色

1. **工作流原生批次整合**：
   - 完美對應 ComfyUI 內建的 `ImpactStringSelector` (節點 422) 與 `PrimitiveInt` 計數器 (節點 424)，支援將整個資料夾的 `.mp4` 影片自動打包並序列化批次處理。
2. **路徑歷史紀錄與快捷下拉**：
   - 輸入目錄與輸出前綴欄位右側皆配備歷史紀錄下拉選單，自動記憶最近 10 筆常用路徑，一鍵快速切換。
3. **靈活的序列與斷點續跑控制**：
   - 可自由設定 **起始索引 (Start Index)** 與 **本次執行數量 (Batch Count)**。任務完成後自動推進索引，支援隨時中斷與斷點續跑。
4. **即時中斷機制 (Abort)**：
   - 執行控制台中提供「停止執行」按鈕，會在當前影片渲染完畢後安全停止，保留已完成的成果。
5. **即時日誌與高清影片預覽**：
   - 介面左右分欄實時顯示執行日誌與最新產生的影片即時預覽（內嵌播放器與下載連結）。
6. **設定參數持久化記憶**：
   - 所有設定參數（路徑、強度、尺寸、Prompt、斷點索引）自動存檔於 `app_settings.json`，即使重新整理（F5）或重啟服務也能完美還原上次狀態。

---

## 🛠️ 快速安裝與啟動指南

### 1. 安裝環境依賴
確保您的 Python 環境已安裝專案所需套件：
```bash
pip install -r requirements.txt
```

### 2. 啟動 ComfyUI 後端
請確保您的 ComfyUI 服務已啟動，並且允許 API 訪問（預設埠為 `8188`）：
```bash
python main.py --listen 127.0.0.1 --port 8188
```

### 3. 啟動 Streamlit 網頁面板
在專案根目錄下執行以下指令：
```bash
streamlit run app.py
```
啟動後瀏覽器將自動開啟操作介面（通常為 `http://localhost:8501`）。
