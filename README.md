<div align="center">

<img src="assets/banner.jpg" alt="TaskFlow Pro — dark workspace banner" width="100%" />

<br/>

<img src="assets/logo-taskflow.svg" alt="TaskFlow Pro Logo" width="420" />

<br/>

![Developer: Raj Gautam](https://img.shields.io/badge/Developer-Raj%20Gautam-38BDF8?style=for-the-badge&logo=github)
![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Database](https://img.shields.io/badge/Database-SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-Tkinter-F8C300?style=for-the-badge&logo=python&logoColor=black)
![OS](https://img.shields.io/badge/OS-Pop!%5FOS%20%7C%20Linux%20%7C%20Windows-342A6D?style=for-the-badge&logo=linux&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)
![Zero Dependencies](https://img.shields.io/badge/Dependencies-ZERO-10B981?style=for-the-badge)

<br/>

### 🚀 A professional, offline-first Desktop Project Management Tool
**Kanban Board • Interactive Gantt Timeline • Live KPIs • GitHub Issue Import • CSV Reports**

Built with **100% Python standard library** — no `pip install`, no heavy frameworks, no bloat.

</div>

---

## 📸 Application Preview

| Kanban Workflow Board | Interactive Gantt Timeline |
| :---: | :---: |
| ![Kanban Board](assets/preview.png) | ![Gantt Timeline](assets/preview-gantt.png) |

> Screenshots are captured from the real running app. Run `python3 main.py` and use the in-app tabs.

---

## ✨ Key Features

- **▦ Interactive Kanban Board** — Three-colour workflow (`To Do` 🔴 / `In Progress` 🟡 / `Completed` 🟢) with Canvas-drawn rounded task cards, priority badges, assignee, due date, progress bar, one-click `←` / `→` stage transitions, inline edit and delete.
- **📊 Visual Gantt Chart** — A native `tk.Canvas` timeline with month/day headers, weekend shading, task bars from start → end dates, graphical completion %, a red **TODAY** marker, hover tooltips, and smooth horizontal scrolling — without matplotlib or any plotting library.
- **📈 Live Analytics Header** — KPI cards for **Total Tasks**, **In Progress**, **Completed %**, **Overdue** and **High Priority** that refresh instantly after every change.
- **🔄 Real GitHub API Work** — Import open issues from any public repo (e.g. `Rg100152/taskflow`) using built-in `urllib.request` + `json` in a background thread. Bug/urgent labels map to High priority automatically; duplicate issues are skipped.
- **🔔 Webhook Alerts** — Configure a Discord/Telegram-compatible webhook; completing a High-priority task fires **“Task Completed by Raj Gautam!”** from a daemon thread.
- **💬 Daily Motivation** — Fetches a fresh developer quote from `dummyjson.com` on every launch (with an offline fallback).
- **📥 One-Click CSV Export** — Clean, timestamped project report with status, timeline, progress and a summary row.
- **⚡ Lightweight & Fast** — Pure stdlib (`tkinter`, `ttk`, `sqlite3`, `urllib`, `json`, `threading`, `csv`). Runs buttery-smooth on a **4GB RAM Pop!_OS laptop**.

---

## 🧩 System Data Flow (DFD)

```mermaid
flowchart LR
    A[User: Raj Gautam] -->|Add / Move / Filter Tasks| B[Tkinter GUI Engine]
    B <--> C[(SQLite3: taskflow.db)]
    C -->|Column Status Data| D[Kanban Board View]
    C -->|Start & End Dates| E[Gantt Timeline Chart]
    C -->|All Records| F[CSV Report Exporter]
    G[Public GitHub Repo] -->|urllib + json, background thread| B
    B -->|High-priority completion| H[Discord / Telegram Webhook]
    I[dummyjson.com Quotes API] -->|Daily motivation| B
```

---

## 🗂 Project Structure

```text
taskflow-pro-desktop/
├── main.py                     # Tkinter app shell, Canvas logo, KPIs, tabs, toolbar
├── database/
│   └── db_manager.py           # SQLite3 CRUD, schema, indexes & 6-task seeder
├── services/
│   └── github_api.py           # GitHub issues importer, quote fetcher, webhook notifier
├── ui/
│   ├── theme.py                # Dark theme tokens & Canvas drawing helpers
│   ├── kanban_view.py          # 3-column interactive Kanban board
│   ├── gantt_view.py           # Canvas-rendered interactive Gantt timeline
│   └── modals.py               # Add / Edit task, GitHub import & webhook dialogs
├── utils/
│   └── exporter.py             # CSV report generator
├── assets/
│   ├── banner.jpg              # Dark workspace banner (Unsplash, local copy)
│   ├── avatar.jpg              # Developer avatar (Unsplash, local copy)
│   ├── logo-taskflow.svg       # Crisp vector logo for GitHub / docs
│   ├── preview.png             # Kanban screenshot
│   └── preview-gantt.png       # Gantt screenshot
├── .gitignore
└── README.md
```

---

## 🛠 Run Locally (Pop!_OS / Linux / Windows)

```bash
git clone https://github.com/Rg100152/taskflow.git
cd taskflow
python3 main.py
```

**Requirements:** Python 3.8+ with Tkinter (bundled on Pop!_OS/Ubuntu; on Debian-like systems install `sudo apt install python3-tk` once). Nothing else.

Open directly in **Geany** and press **F5** — no virtualenv, no dependency step.

> On first run, `taskflow.db` is created automatically and seeded with 6 realistic developer tasks so both views are populated immediately.

---

## 🖱 Quick Usage Guide

| Action | How |
| :--- | :--- |
| Add task | Click **＋ Add Task**, fill fields, **Save Task** |
| Move stage | Click **←** / **→** on any card (progress auto-sets to 100% on Completed) |
| Edit task | Click the **✎** button or double-click a card / Gantt bar |
| Delete task | Click **✕** and confirm |
| Filter | Type in the search box (title, description or assignee) |
| Import issues | **🔄 Import GitHub** → enter `owner/repo` → **Import Issues** |
| Export | **📥 Export CSV** → choose a location |
| Alerts | **⚙ Webhook** → paste webhook URL |

---

## 👨‍💻 Developer

<div align="center">

<img src="assets/avatar.jpg" alt="Raj Gautam" width="110" style="border-radius:50%" />

<br/>

<b>Raj Gautam</b> — Developer & Linux Enthusiast

📧 graj13099@gmail.com &nbsp;•&nbsp; 📷 [@linuxuser.raj](https://instagram.com/linuxuser.raj) &nbsp;•&nbsp; 🐙 [Rg100152](https://github.com/Rg100152)

</div>

---

<div align="center">
  <sub>Built with Python standard libraries on Pop!_OS · © 2026 Raj Gautam · MIT License</sub>
</div>
