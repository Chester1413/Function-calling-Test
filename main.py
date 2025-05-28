import openai
import os
import platform
import json
import tkinter as tk
from tkinter import scrolledtext
from rapidfuzz import fuzz, process

# ---------- 設定檔案路徑 ----------
API_KEY_PATH = "sk_key.txt"
KEYWORD_MAP_PATH = "functions.txt"
CONFIG_PATH = "config.txt"

# ---------- 對話歷史 ----------
message_history = [
    {"role": "system", "content": "你是一個能聊天並根據關鍵字開啟檔案的助理。"}
]

# ---------- 讀取 API 金鑰 ----------
def load_api_key(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read().strip()

# ---------- 讀取關鍵字對應表 ----------
def load_keyword_map(filepath):
    keyword_map = {}
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    keyword, path = line.strip().split('=', 1)
                    keyword_map[keyword.strip()] = path.strip()
    return keyword_map

# ---------- 模糊比對 ----------
def find_best_match(user_input, keyword_map):
    threshold = threshold_var.get()
    candidates = list(keyword_map.keys())
    best_match = process.extractOne(user_input, candidates, scorer=fuzz.partial_ratio)
    if best_match and best_match[1] >= threshold:
        return best_match[0]
    return None

# ---------- 開啟多個檔案 ----------
def open_files(file_paths):
    messages = []
    for file_path in file_paths:
        if not os.path.exists(file_path):
            messages.append(f"❌ 檔案不存在: {file_path}")
            continue
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":
                os.system(f"open '{file_path}'")
            else:
                os.system(f"xdg-open '{file_path}'")
            messages.append(f"✅ 已開啟檔案: {file_path}")
        except Exception as e:
            messages.append(f"❌ 開啟檔案失敗: {file_path}\n錯誤: {e}")
    return "\n".join(messages)

# ---------- 儲存/讀取模糊比對門檻值 ----------
def save_threshold_to_config(value):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.write(str(value))
    except Exception as e:
        print(f"⚠️ 儲存門檻設定失敗: {e}")

def load_threshold_from_config(default=75):
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return int(f.read().strip())
        except:
            return default
    return default

# ---------- GPT 聊天回應（支援上下文） ----------
def chat_with_openai(user_input):
    message_history.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=message_history,
        functions=functions if allow_function_calls.get() else None,
        function_call="auto" if allow_function_calls.get() else None
    )

    message = response.choices[0].message

    if message.function_call:
        func_name = message.function_call.name
        arguments = json.loads(message.function_call.arguments)
        if func_name == "open_file":
            result = open_files([arguments["file_path"]])
            message_history.append({
                "role": "assistant",
                "content": f"（執行功能 {func_name}）{result}"
            })
            return result
        else:
            return "⚠️ 無法辨識的功能呼叫"
    else:
        message_history.append({"role": "assistant", "content": message.content})
        return message.content

# ---------- 處理使用者輸入 ----------
def handle_user_input():
    user_input = input_entry.get()
    if not user_input.strip():
        return
    chat_area.insert(tk.END, f"🧑 你：{user_input}\n")
    input_entry.delete(0, tk.END)

    matched_keyword = find_best_match(user_input, keyword_map)
    if matched_keyword and allow_function_calls.get():
        file_path_str = keyword_map[matched_keyword]
        file_paths = [p.strip() for p in file_path_str.split(',') if p.strip()]
        result = open_files(file_paths)
        chat_area.insert(tk.END, f"🤖 助理：已找到「{matched_keyword}」\n{result}\n")
        chat_area.see(tk.END)
        return

    response = chat_with_openai(user_input)
    chat_area.insert(tk.END, f"🤖 助理：{response}\n")
    chat_area.see(tk.END)

# ---------- 清除對話歷史 ----------
def clear_chat_history():
    global message_history
    message_history = [
        {"role": "system", "content": "你是一個能聊天並根據關鍵字開啟檔案的助理。"}
    ]
    chat_area.insert(tk.END, "🧹 助理：對話歷史已清除。\n")
    chat_area.see(tk.END)

# ---------- 門檻滑桿事件 ----------
def on_threshold_change(val):
    save_threshold_to_config(threshold_var.get())

# ---------- 初始化 ----------
client = openai.OpenAI(api_key=load_api_key(API_KEY_PATH))
keyword_map = load_keyword_map(KEYWORD_MAP_PATH)

functions = [
    {
        "name": "open_file",
        "description": "使用系統預設應用程式開啟指定的檔案",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要開啟的完整檔案路徑，例如 C:\\Users\\User\\Desktop\\file.pdf"
                }
            },
            "required": ["file_path"]
        }
    }
]

# ---------- 建立 UI ----------
window = tk.Tk()
window.title("Chat Assistant")
window.geometry("700x700")

threshold_var = tk.IntVar(value=load_threshold_from_config())
allow_function_calls = tk.BooleanVar(value=True)

threshold_frame = tk.Frame(window)
threshold_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

tk.Label(threshold_frame, text="模糊比對(0~100)：", font=("Microsoft JhengHei", 10)).pack(side=tk.LEFT)
threshold_slider = tk.Scale(
    threshold_frame,
    from_=0, to=100,
    orient=tk.HORIZONTAL,
    variable=threshold_var,
    command=on_threshold_change
)
threshold_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

options_frame = tk.Frame(window)
options_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

function_toggle = tk.Checkbutton(
    options_frame,
    text="允許執行檔案開啟功能",
    variable=allow_function_calls,
    font=("Microsoft JhengHei", 10)
)
function_toggle.pack(anchor="w")

chat_area = scrolledtext.ScrolledText(window, wrap=tk.WORD, font=("Microsoft JhengHei", 12))
chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

input_frame = tk.Frame(window)
input_frame.pack(fill=tk.X, padx=10, pady=5)

input_entry = tk.Entry(input_frame, font=("Microsoft JhengHei", 12))
input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
input_entry.bind("<Return>", lambda event: handle_user_input())

send_button = tk.Button(input_frame, text="送出", command=handle_user_input, font=("Microsoft JhengHei", 12))
send_button.pack(side=tk.RIGHT)

clear_button = tk.Button(input_frame, text="清除歷史", command=clear_chat_history, font=("Microsoft JhengHei", 12))
clear_button.pack(side=tk.RIGHT, padx=(5, 0))

chat_area.insert(tk.END, "🤖 助理：您好，我是您的聊天助理！\n")

window.mainloop()
