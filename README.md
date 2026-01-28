# 👁️ RemoteEye Global v1.0.6 (Jiajin Official)

![Version](https://img.shields.io/badge/version-1.0.6-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

**RemoteEye Global** 是一款輕量、極速且跨越國界的遠端協作工具。提供最直覺、免設定的遠端支援體驗。

## 🌟 功能亮點

* **🌍 全球多國語系**：內建繁中、英、日、法、西、韓六國語言，自動適應。
* **⚡ 極速影像傳輸**：優化數據壓縮演算，實現低延遲的桌面流暢體驗。
* **📂 遠端檔案推送**：支援一鍵傳送檔案至受控端桌面，簡化技術支援流程。
* **📦 雙版本提供**：
    * **安裝版**：提供完整的系統整合與桌面捷徑。
    * **綠色免安裝版**：單一執行檔，點開即用，適合隨身碟緊急救援。
* **🛡️ 安全性**：無密碼快速連線設計（適合內部信任網路或快速技術協助）。

## 🚀 快速開始

### 下載連結
您可以前往我們的 [GitHub Pages 官方網站](https://acmno123.github.io/RemoteEye/) 下載最新版本。

### 使用方法
1.  **受控端 (Agent)**：點擊「接受協助」，將顯示的 IP 地址告知對方。
2.  **控制端 (Controller)**：點擊「協助他人」，輸入對方的 IP 地址後點擊「立即連線」。

## 🛠️ 技術架構

本專案基於 Python 開發，使用了以下核心庫：
* `CustomTkinter`: 現代化的 GUI 介面設計。
* `mss`: 高性能螢幕截圖。
* `zlib`: 高效率數據壓縮傳輸。
* `pyautogui`: 遠端輸入控制指令。

## 📦 打包說明

如果您想自行編譯，請參考以下指令：

**製作免安裝綠色版：**
```bash
python -m PyInstaller --noconsole --onefile --admin --collect-all customtkinter --add-data "logo.png;." --icon="logo.ico" --name "RemoteEye_Portable_v1.0.6" RemoteEye_Global.py
