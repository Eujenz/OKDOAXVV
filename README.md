<div align="center">
  <img src="https://koeitecmo.wordpress.com/wp-content/uploads/2019/03/peach_logo_rgb.jpg?w=1024" width="100%" alt="OKDOAXVV Banner"/>

 
  <p>
    一個基於圖像識別的《死或生：沙灘排球 女神假期》自動化程序，支援後台執行，基於 <a href="https://github.com/ok-oldking/ok-script">ok-script</a> 框架開發。
    <br />
    An image-recognition-based automation tool for DOAXVV, with background mode support, developed with <a href="https://github.com/ok-oldking/ok-script">ok-script</a>.
  </p>
  
  <p><i>通過模擬 Windows 用戶接口進行操作，無記憶體讀取、無檔案修改，融合擬人化滑鼠軌跡與行為節奏管理</i></p>
</div>

<!-- Badges -->
<div align="center">
  
![平台](https://img.shields.io/badge/platform-Windows-blue)
[![GitHub release](https://img.shields.io/github/v/release/Eujenz/OKDOAXVV)](https://github.com/Eujenz/OKDOAXVV/releases)
[![總下載量](https://img.shields.io/github/downloads/Eujenz/OKDOAXVV/total)](https://github.com/Eujenz/OKDOAXVV/releases)
[![Discord](https://img.shields.io/discord/296598043787132928?color=5865f2&label=%20Discord)](https://discord.gg/vVyCatEBgA)

</div>

---

## ⚠️ 免責聲明

本軟體為外部輔助工具，旨在自動化《死或生：沙灘排球 女神假期》（DOAXVV）的部分遊戲流程（例如自動挑戰活動關卡）。它完全通過模擬常規 Windows 用戶介面與遊戲進行背景交互，遵循相關法律法規。本專案旨在簡化用戶的重複性點擊操作，不會破壞遊戲平衡或提供不公平優勢，也絕不會修改任何遊戲檔案或記憶體數據。

本軟體開源、免費，僅供個人學習與交流使用，請勿用於任何商業或營利性目的。開發者團隊擁有本專案的最終解釋權。因使用本軟體而產生的任何問題，均與本專案及開發者無關。

**使用本軟體即表示您已閱讀、理解並同意以上聲明，並自願承擔一切潛在風險。**

---

## ✨ 主要功能

*   **完全背景執行模式**: 基於 Windows `PostMessage` 接口發送點擊與移動，支援遊戲視窗最小化或被遮擋時在背景流暢運行，絲毫不影響您日常使用電腦。
*   **擬人化滑鼠移動軌跡**: 獨創的**二次貝氏曲線（Bezier Curve）**滑鼠模擬，加入非線性平滑加減速曲線（Smoothstep）與末端逼真手震（Jitter）校正，徹底擺脫機械式瞬移點擊。
*   **次世代擬人化行為引擎**:
    *   **費茨法則（Fitts's Law）**：按鈕越小點擊按壓時間越長，大按鈕則自信快速點擊。
    *   **反應時間對數常態分佈**：符合人類生理學的非對稱「長尾反應延遲」統計。
    *   **AR(1) 時間自相關噪聲**：模擬真實人類節奏慣性與分心延遲，並伴隨隨機的「節奏突變」。
    *   **S型疲勞曲線模型**：隨著運行時間增長累積疲勞度，操作節奏隨之產生擬真衰退與閒置恢復。
    *   **隨機泊松微休息**：無固定週期、非預測性的微休息（放空），防範作弊偵測系統。
*   **JSON-Driven 彈性流程**: 關卡挑戰邏輯與步驟優先級完全解耦至 JSON 配置，有 15% 的隨機眼殘交換步驟檢查順序，完全模擬真人視線。
*   **自癒與模板開發工具鏈**:
    *   `TemplateMakerTask.py`：遊戲內即時截圖、框選、白底遮罩裁剪與 COCO result.json 完美寫入一氣呵成。
    *   `JsonFixerTask.py`：當用戶手動變更或重命名實體圖片，一鍵以 OpenCV 反推按鈕 bbox 重建 result.json 配置文件。
    *   `preflight.py`：啟動前自動預檢過濾失效圖片，防止框架崩潰。

---

## 🚀 快速開始

1.  **環境需求**：本項目基於 **Python 3.12** 開發，請確保您已安裝對應版本。
2.  **以管理員權限開啟終端機**（CMD / PowerShell）或您的 IDE（PyCharm, VSCode 等）。
3.  **複製並安裝依賴項目**：
    ```bash
    pip install -r requirements.txt --upgrade
    ```
4.  **運行程序**：
    *   **運行 Release 正常版本**：
        ```bash
        python main.py
        ```
    *   **運行 Debug 開發調試版本**：
        ```bash
        python main_debug.py
        ```

---

## ⚙️ 專案文件說明

```
├─ assets/               # CV2 使用的範本圖片與配置
│  ├─ images/            # 模板按鈕裁剪圖片 (.png)
│  └─ result.json        # COCO 格式的模板特徵座標 JSON 檔
├─ backend/              # 可選 Web 服務後端配置
├─ configs/              # 本地設定檔儲存資料夾
├─ docs/                 # 說明文件檔
├─ flows/                # JSON 驅動之自動化工作流檔案
│  └─ event_farming.json # 自動刷活動流程定義檔
├─ icons/                # 程式 UI 圖標
├─ src/                  # 核心代碼庫
│  ├─ tasks/             # 各式任務定義
│  │  ├─ MyBaseTask.py       # 底層任務，包含貝氏曲線滑鼠移動軌跡
│  │  ├─ HumanBehavior.py    # 核心擬人化行為與延遲模擬引擎
│  │  ├─ FlowRunnerTask.py   # JSON 工作流執行器
│  │  ├─ TemplateMakerTask.py# 快速模板擷取與 JSON 登錄工具
│  │  └─ JsonFixerTask.py    # 自癒式 result.json 魔法修復工具
│  ├─ config.py          # 程式初始化全域設定檔
│  ├─ globals.py         # 全域單例
│  └─ preflight.py       # 預檢機制，啟動前防崩潰過濾器
├─ main.py               # 正式入口
├─ main_debug.py         # 除錯入口
└─ pyappify.yml          # exe 打包設定檔
```

---

## 🔧 疑難解答 (Troubleshooting)

如果遇到問題，請在提問前按以下步驟逐一排查：

1.  **安裝路徑**：請確保專案位於**純英文路徑**下，避免中文字符與空白字元。
2.  **螢幕顯示與縮放**：
    *   建議將 Windows 的「螢幕顯示與縮放比例」設定為 `100%`。
    *   關閉所有顯卡濾鏡（如 NVIDIA 濾鏡）與銳化設定，維持遊戲默認亮度。
3.  **殺毒軟件與防火牆**：將執行路徑或打包後的 `.exe` 目錄加入 Windows Defender 或第三方防毒軟體的排除名單，防範 PostMessage 指令發送被誤攔截。
4.  **遊戲解析度與畫面**：
    *   支援 16:9 分辨率，若畫面拉伸可能會導致圖片匹配精度降低。
    *   確保遊戲能穩定於 60 FPS 運行以確保滑鼠移動物理模擬軌跡符合時序。

---

## 💻 命令行參數

您可透過指令參數實現腳本快速調用或自動執行：

```bash
# 啟動後自動執行任務列表中的第一個任務，完成後自動退出
python main.py -t 1 -e
```

*   `-t` 或 `--task`: 啟動自動執行的第 N 個任務（由 1 開始計算）。
*   `-e` 或 `--exit`: 任務完全結束後自動關閉整個腳本介面。

---

## 🔗 基於 ok-script 的其他優秀專案：

* 鳴潮 [ok-wuthering-waves](https://github.com/ok-oldking/ok-wuthering-waves)
* 明日方舟:終末地 [ok-end-field](https://github.com/ok-oldking/ok-end-field)
* 少前2 [ok-gf2](https://github.com/ok-oldking/ok-gf2)
* 星鐵 [ok-starrailassistant](https://github.com/Shasnow/ok-starrailassistant)
* 星痕共鳴 [ok-star-resonance](https://github.com/Sanheiii/ok-star-resonance)

---

## ❤️ 贊助與致謝

### 致謝 (Acknowledgements)
*   [ok-script 官方框架](https://github.com/ok-oldking/ok-script)
*   [zhiyiYo/PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)
