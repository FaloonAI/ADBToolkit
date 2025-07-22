import subprocess
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
import threading
import time
import os
import re
from colorama import Fore
from localization_data import texts
import tempfile
import win32gui  # Make sure you have pywin32 installed: pip install pywin32
import tkinter.ttk as ttk # For Combobox

current_language = 'en'
text_widgets = {}
menu_items = {}

# --- Language Switching Integration ---
# Store references to all menu and menu items for language switching
menu_refs = {}

try:
    from PIL.Image import Resampling
except ImportError:
    Resampling = None

def wait_for_device():
    print(Fore.LIGHTGREEN_EX + "[*] Waiting for device...")
    for _ in range(10):
        try:
            result = subprocess.check_output(["adb", "devices"], text=True)
            lines = result.strip().splitlines()
            if len(lines) > 1 and "device" in lines[1]:
                print(Fore.LIGHTGREEN_EX + "[*] Device found. Starting remote access...")
                return True
        except subprocess.SubprocessError:
            pass
        time.sleep(1)
    return False

def send_popup_message():
    msg = simpledialog.askstring(texts[current_language]['input_title'], texts[current_language]['input_prompt'])
    if not msg:
        return
    msg_sanitized = msg.replace(" ", "_")
    subprocess.run(["adb", "shell", "input", "text", msg_sanitized])
    messagebox.showinfo(texts[current_language]['success'], texts[current_language]['operation_complete'])

def get_ip_address():
    output = subprocess.check_output(["adb", "shell", "ip", "addr"], text=True)
    interfaces = output.split("\n\n")

    for interface in interfaces:
        if "inet " in interface and "127.0.0.1" not in interface:
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', interface)
            if match:
                print(Fore.LIGHTGREEN_EX + f"[*] Device IP Address: {match.group(1)}")
                return match.group(1)
    raise Exception("Failed to retrieve IP address. Make sure the device is connected to WiFi.")

def launch_scrcpy_filtered(ip_address):
    process = subprocess.Popen(["scrcpy", "-s", f"{ip_address}:5555"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True)

    if process.stdout is not None:
        for line in process.stdout:
            if any(phrase in line for phrase in [
                "scrcpy", "https://github.com/Genymobile/scrcpy",
                "skipped.", "adb.exe:", "adb reverse", "WARN:"
            ]):
                continue
            print(line, end="")

def tcp_connect_wifi():
    try:
        if not wait_for_device():
            raise Exception(texts[current_language]['no_device'])

        subprocess.run(["adb", "tcpip", "5555"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

        ip_address = get_ip_address()
        print(Fore.LIGHTGREEN_EX + f"[*] Attempting to connect to {ip_address}:5555 ..." + Fore.RESET)

        connect_result = subprocess.run(["adb", "connect", f"{ip_address}:5555"],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        text=True)

        filtered_output = "\n".join(
            line for line in connect_result.stdout.splitlines()
            if not any(skip in line for skip in [
                "skipped.", "adb.exe:", "adb reverse", "WARN:"
            ])
        )
        if "connected" not in connect_result.stdout.lower():
            raise Exception(f"ADB connection failed:\n{filtered_output.strip()}")

        # Launch scrcpy with filtered output
        launch_scrcpy_filtered(ip_address)

        messagebox.showinfo(texts[current_language]['success'], f"Successfully connected to {ip_address}:5555")

    except subprocess.CalledProcessError as e:
        messagebox.showerror(texts[current_language]['error'], f"Command failed:\n{e}")
    except Exception as e:
        messagebox.showerror(texts[current_language]['error'], str(e))

def tcp_disconnect_wifi():
    try:
        target_ip = simpledialog.askstring(texts[current_language]['input_title'], "Enter the device IP (e.g., 192.168.1.123):")
        if target_ip:
            subprocess.run(["adb", "disconnect", f"{target_ip}:5555"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            messagebox.showinfo(texts[current_language]['success'], f"Disconnected from {target_ip}:5555")
    except Exception as e:
        messagebox.showerror(texts[current_language]['error'], f"Failed to disconnect:\n{e}")



def check_device():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    if len(lines) > 1 and lines[1] and "device" in lines[1]:
        messagebox.showinfo(texts[current_language]['success'], texts[current_language]['device_list'])
    else:
        messagebox.showerror(texts[current_language]['error'], texts[current_language]['no_device'])

def take_screenshot():
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, "android_screenshot.png")
    subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/screen.png"])
    subprocess.run(["adb", "pull", "/sdcard/screen.png", temp_path])

    preview_win = tk.Toplevel(app)
    preview_win.title("Screenshot Preview")
    preview_win.geometry("600x800")
    preview_win.resizable(True, True)

    img = Image.open(temp_path)
    if Resampling is not None:
        img.thumbnail((600, 800), Resampling.LANCZOS)
    else:
        img.thumbnail((600, 800))
    img_tk = ImageTk.PhotoImage(img)
    img_label = tk.Label(preview_win, image=img_tk)
    setattr(img_label, 'image', img_tk)
    img_label.pack(expand=True, fill="both", padx=10, pady=10)

    def save_image():
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if save_path:
            img.save(save_path)
            messagebox.showinfo("Saved", f"Screenshot saved to {save_path}")

    save_btn = tk.Button(preview_win, text="Save", command=save_image)
    save_btn.pack(pady=10)

def open_terminal():
    subprocess.Popen(["adb", "shell"], creationflags=subprocess.CREATE_NEW_CONSOLE)

def extract_contacts():
    try:
        output = subprocess.check_output(["adb", "shell", "content", "query", "--uri", "content://contacts/phones/"], text=True)
        with open("contacts.txt", "w", encoding="utf-8") as f:
            f.write(output)
        messagebox.showinfo(texts[current_language]['success'], "Contacts extracted and saved to contacts.txt")
    except Exception as e:
        messagebox.showerror(texts[current_language]['error'], f"Failed to extract contacts.\n{e}")

def extract_gallery():
    try:
        save_folder = "gallery_images"
        os.makedirs(save_folder, exist_ok=True)
        subprocess.run(["adb", "shell", "su", "-c", f"ls /sdcard/DCIM/Camera/"], stdout=subprocess.DEVNULL)
        files = subprocess.check_output(["adb", "shell", "ls", "/sdcard/DCIM/Camera/"], text=True).splitlines()
        pulled = 0
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                subprocess.run(["adb", "pull", f"/sdcard/DCIM/Camera/{file}", f"{save_folder}/{file}"])
                pulled += 1
        messagebox.showinfo(texts[current_language]['success'], f"Downloaded {pulled} images to folder: {save_folder}")
    except Exception as e:
        messagebox.showerror(texts[current_language]['error'], f"Failed to extract images.\n{e}")
        
def start_activity():
    full_str = simpledialog.askstring("Start Activity", "Enter in form: package/activity")
    if full_str:
        subprocess.run(["adb", "shell", "am", "start", "-n", full_str])
        messagebox.showinfo(f"Started: {full_str}")

def open_url():
    url = simpledialog.askstring("Open URL", "Enter URL to open (e.g. https://example.com)")
    if url:
        subprocess.run(["adb", "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url])
        messagebox.showinfo(f"Opened URL: {url}")

def simulate_tap():
    coords = simpledialog.askstring("Tap", "Enter X,Y coordinates (e.g., 300 800):")
    if coords:
        subprocess.run(["adb", "shell", "input", "tap"] + coords.split())
        messagebox.showinfo(f"Tapped at: {coords}")

def simulate_swipe():
    coords = simpledialog.askstring("Swipe", "Enter x1 y1 x2 y2 duration (ms):")
    if coords:
        subprocess.run(["adb", "shell", "input", "swipe"] + coords.split())
        messagebox.showinfo(f"Swipe: {coords}")

def list_packages():
    output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"], text=True)
    with open("packages.txt", "w", encoding="utf-8") as f:
        f.write(output)
    show_large_output_window(texts[current_language]['output_title'], output)

def uninstall_package():
    package = simpledialog.askstring("Uninstall App", "Enter package name to uninstall:")
    if package:
        subprocess.run(["adb", "shell", "pm", "uninstall", package])
        messagebox.showinfo(f"Uninstalled: {package}")

def view_logcat():
    subprocess.Popen(["adb", "logcat"], creationflags=subprocess.CREATE_NEW_CONSOLE)

def toggle_wifi():
    state = simpledialog.askstring("WiFi", "Enter: enable or disable")
    if state in ("enable", "disable"):
        subprocess.run(["adb", "shell", "svc", "wifi", state])
        messagebox.showinfo("WiFi", f"WiFi {state}d")

def toggle_data():
    state = simpledialog.askstring("Mobile Data", "Enter: enable or disable")
    if state in ("enable", "disable"):
        subprocess.run(["adb", "shell", "svc", "data", state])
        messagebox.showinfo("Data", f"Mobile data {state}d")

        
def start_camera(front=True):
    camera_id = 1 if front else 0
    subprocess.run([
        "adb", "shell", "am", "start", 
        "-a", "android.media.action.VIDEO_CAMERA", 
        "--ez", "android.intent.extra.USE_FRONT_CAMERA", str(front).lower()
    ])
    messagebox.showinfo("Camera", f"{'Front' if front else 'Rear'} camera launched.")


def reboot_device():
    subprocess.run(["adb", "reboot"])
    messagebox.showinfo("Device is rebooting...")

def power_off_device():
    subprocess.run(["adb", "shell", "reboot", "-p"])
    messagebox.showinfo("Device is shutting down...")

def lock_screen():
    subprocess.run(["adb", "shell", "input", "keyevent", "26"])
    messagebox.showinfo("Screen locked.")

def show_battery_info():
    result = subprocess.run(["adb", "shell", "dumpsys", "battery"], capture_output=True, text=True)
    print("Battery Info:\n" + result.stdout)

def launch_app():
    package = simpledialog.askstring("Launch App", "Enter package name (e.g., com.android.chrome):")
    if package:
        subprocess.run(["adb", "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"])
        messagebox.showinfo("", f"Launched: {package}")
        
def start_scrcpy():
    try:
        subprocess.Popen(["scrcpy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        messagebox.showinfo("Screenshare", "Scrcpy launched. A new window should appear.")
    except FileNotFoundError:
        messagebox.showerror("Error", "scrcpy is not installed or not in PATH. Please refer to README.md for installation instructions.")

def browse_files():
    path = simpledialog.askstring("File Browser", "Enter path to browse (e.g., /sdcard/):")
    if path:
        try:
            output = subprocess.check_output(["adb", "shell", "ls", "-F", path], text=True)
            messagebox.showinfo(f"Contents of {path}", output)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to list directory:\n{e.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{e}")

def pull_file():
    remote_path = simpledialog.askstring("Pull File", "Enter remote path on device (e.g., /sdcard/my_file.txt):")
    if remote_path:
        local_path = simpledialog.askstring("Pull File", "Enter local path to save to (e.g., ./my_file.txt):", initialvalue=os.path.basename(remote_path))
        if local_path:
            try:
                subprocess.run(["adb", "pull", remote_path, local_path], check=True)
                messagebox.showinfo("Success", f"File pulled to {local_path}")
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to pull file:\n{e.stderr}")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred:\n{e}")

def push_file():
    local_path = filedialog.askopenfilename(
        title="Select file to send",
        filetypes=[("Все файлы", "*.*")] # Можете настроить типы файлов, например, [("Text files", "*.txt"), ("All files", "*.*")]
    )

    if local_path: # Если файл был выбран
        # 2. Окно для ввода удаленного пути (остается simpledialog, как в вашей первоначальной логике)
        remote_path = simpledialog.askstring(
            "Send file",
            "Enter the remote path on the device (e.g. /sdcard/):",
            initialvalue="/sdcard/"
        )

        if remote_path:
            subprocess.run(["adb", "push", local_path, remote_path], check=True, capture_output=True, text=True)
        else:
            messagebox.showinfo("Отмена", "Отправка файла отменена: удаленный путь не указан.")
    else:
        messagebox.showinfo("Отмена", "Отправка файла отменена: файл не выбран.")

def get_device_network_info():
    try:
        ip_output = subprocess.check_output(["adb", "shell", "ip", "addr", "show"], text=True)
        netstat_output = subprocess.check_output(["adb", "shell", "netstat", "-tupn"], text=True)
        
        info = texts[current_language]['network_info'] + "\n\n" + ip_output + "\n\n" + netstat_output
        show_large_output_window(texts[current_language]['output_title'], info)
    except subprocess.CalledProcessError as e:
        messagebox.showerror(texts[current_language]['error'], f"Failed to get network info:\n{e.stderr}")
    except Exception as e:
        messagebox.showerror(texts[current_language]['error'], f"An error occurred:\n{e}")

def list_running_processes():
    try:
        output = subprocess.check_output(["adb", "shell", "ps", "-A"], text=True)
        show_large_output_window(texts[current_language]['output_title'], output)
    except subprocess.CalledProcessError as e:
        messagebox.showerror(texts[current_language]['error'], f"Failed to list processes:\n{e.stderr}")
    except Exception as e:
        messagebox.showerror(texts[current_language]['error'], f"An error occurred:\n{e}")

def view_app_permissions():
    package = simpledialog.askstring(texts[current_language]['app_permissions'], texts[current_language]['input_prompt'])
    if package:
        try:
            output = subprocess.check_output(["adb", "shell", "dumpsys", "package", package], text=True)
            permissions = [line for line in output.splitlines() if "Permission" in line or "perm" in line]
            show_large_output_window(texts[current_language]['output_title'], "\n".join(permissions))
        except subprocess.CalledProcessError as e:
            messagebox.showerror(texts[current_language]['error'], f"Failed to get permissions:\n{e.stderr}")
        except Exception as e:
            messagebox.showerror(texts[current_language]['error'], f"An error occurred:\n{e}")

def grant_app_permission():
    package = simpledialog.askstring("Grant Permission", "Enter package name:")
    if package:
        permission = simpledialog.askstring("Grant Permission", "Enter permission name (e.g., android.permission.READ_CONTACTS):")
        if permission:
            try:
                subprocess.run(["adb", "shell", "pm", "grant", package, permission], check=True)
                messagebox.showinfo("Success", f"Granted {permission} to {package}")
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to grant permission:\n{e.stderr}")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred:\n{e}")

def revoke_app_permission():
    package = simpledialog.askstring("Revoke Permission", "Enter package name:")
    if package:
        permission = simpledialog.askstring("Revoke Permission", "Enter permission name (e.g., android.permission.READ_CONTACTS):")
        if permission:
            try:
                subprocess.run(["adb", "shell", "pm", "revoke", package, permission], check=True)
                messagebox.showinfo("Success", f"Revoked {permission} from {package}")
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to revoke permission:\n{e.stderr}")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred:\n{e}")

def get_extended_device_info():
    try:
        output = subprocess.check_output(["adb", "shell", "getprop"], text=True)
        show_large_output_window(texts[current_language]['output_title'], output)
    except subprocess.CalledProcessError as e:
        messagebox.showerror(texts[current_language]['error'], f"Failed to get device info:\n{e.stderr}")
    except Exception as e:
        messagebox.showerror(texts[current_language]['error'], f"An error occurred:\n{e}")

def install_apk():
    apk_path = simpledialog.askstring("Install APK", "Enter full path to APK file on your PC (e.g., C:/Users/YourUser/app.apk):")
    if apk_path and os.path.exists(apk_path):
        try:
            subprocess.run(["adb", "install", apk_path], check=True)
            messagebox.showinfo("Success", f"APK installed: {apk_path}")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to install APK:\n{e.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{e}")
    elif apk_path:
        messagebox.showerror("Error", "File not found. Please check the path.")

def show_large_output_window(title, content):
    """Создает новое окно для отображения большого объема текста."""
    output_window = tk.Toplevel(app)
    output_window.title(title)
    output_window.geometry("700x500") # Можно настроить размер
    output_window.configure(bg="#282c34")

    # Создаем текстовый виджет
    text_widget = tk.Text(output_window, wrap="word", bg="#1e1e1e", fg="white", 
                          insertbackground="white", font=("Consolas", 10), state="normal")
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Добавляем скроллбар
    scrollbar = tk.Scrollbar(output_window, command=text_widget.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text_widget.config(yscrollcommand=scrollbar.set)

    # Вставляем контент и делаем виджет только для чтения
    text_widget.insert(tk.END, content)
    text_widget.config(state="disabled")

    # Переводим фокус на это окно
    output_window.grab_set()
    output_window.focus_set()
    output_window.transient(app) # Делаем его дочерним к основному окну
    output_window.wait_window() # Ждем закрытия этого окна

def update_all_texts():
    global current_language
    app.title(texts[current_language]['title'])

    # Обновление пунктов главного меню (menubar)
    # Убедитесь, что menu_refs корректно инициализирован с соответствующими индексами
    if 'device' in menu_refs:
        menubar.entryconfig(menu_refs['device'], label=texts[current_language]['device'])
    if 'file_management' in menu_refs:
        menubar.entryconfig(menu_refs['file_management'], label=texts[current_language]['file_management'])
    if 'actions' in menu_refs:
        menubar.entryconfig(menu_refs['actions'], label=texts[current_language]['actions'])
    if 'permissions' in menu_refs:
        menubar.entryconfig(menu_refs['permissions'], label=texts[current_language]['permissions'])
    if 'terminal' in menu_refs:
        menubar.entryconfig(menu_refs['terminal'], label=texts[current_language]['terminal'])
    if 'camera' in menu_refs: # Убедитесь, что у вас есть ключ 'camera' в localization_data.py
        menubar.entryconfig(menu_refs['camera'], label=texts[current_language]['camera'])
    if 'language' in menu_refs:
        menubar.entryconfig(menu_refs['language'], label=texts[current_language]['language'])

    # Update device menu (corrected indices)
    device_menu.entryconfig(0, label=texts[current_language]['check_device'])
    device_menu.entryconfig(1, label=texts[current_language]['launch_scrcpy'])
    device_menu.entryconfig(2, label=texts[current_language]['get_network_info'])
    device_menu.entryconfig(3, label=texts[current_language]['extended_device_info'])
    device_menu.entryconfig(5, label=texts[current_language]['tcp_connect_wifi'])  # Skip separator at index 4
    device_menu.entryconfig(6, label=texts[current_language]['tcp_disconnect'])

    # File menu (corrected indices)
    file_menu.entryconfig(0, label=texts[current_language]['install_apk'])
    file_menu.entryconfig(1, label=texts[current_language]['browse_files'])
    file_menu.entryconfig(3, label=texts[current_language]['pull_file'])  # Skip separator at index 2
    file_menu.entryconfig(4, label=texts[current_language]['push_file'])

    # Actions menu (corrected indices - must match creation order)
    actions_menu.entryconfig(0, label=texts[current_language]['take_screenshot'], command=take_screenshot)
    actions_menu.entryconfig(1, label=texts[current_language]['screenshare'], command=start_scrcpy)
    actions_menu.entryconfig(2, label=texts[current_language]['front_camera_preview'], command=lambda: start_camera(front=True))
    actions_menu.entryconfig(3, label=texts[current_language]['rear_camera_preview'], command=lambda: start_camera(front=False))
    # Skip separator at index 4
    actions_menu.entryconfig(5, label=texts[current_language]['extract_contacts'], command=extract_contacts)
    actions_menu.entryconfig(6, label=texts[current_language]['extract_gallery_images'], command=extract_gallery)
    # Skip separator at index 7
    actions_menu.entryconfig(8, label=texts[current_language]['battery_info'], command=show_battery_info)
    actions_menu.entryconfig(9, label=texts[current_language]['launch_app_by_package'], command=launch_app)
    actions_menu.entryconfig(10, label=texts[current_language]['lock_screen'], command=lock_screen)
    actions_menu.entryconfig(11, label=texts[current_language]['reboot_device'], command=reboot_device)
    actions_menu.entryconfig(12, label=texts[current_language]['power_off'], command=power_off_device)
    actions_menu.entryconfig(13, label=texts[current_language]['list_running_processes'], command=list_running_processes)
    # Skip separator at index 14
    actions_menu.entryconfig(15, label=texts[current_language]['start_app_activity'], command=start_activity)
    actions_menu.entryconfig(16, label=texts[current_language]['open_url_in_browser'], command=open_url)
    actions_menu.entryconfig(17, label=texts[current_language]['simulate_tap'], command=simulate_tap)
    actions_menu.entryconfig(18, label=texts[current_language]['simulate_swipe'], command=simulate_swipe)
    # Skip separator at index 19
    actions_menu.entryconfig(20, label=texts[current_language]['list_installed_packages'], command=list_packages)
    actions_menu.entryconfig(21, label=texts[current_language]['uninstall_app_by_package'], command=uninstall_package)
    # Skip separator at index 22
    actions_menu.entryconfig(23, label=texts[current_language]['show_logcat'], command=view_logcat)
    actions_menu.entryconfig(24, label=texts[current_language]['toggle_wifi'], command=toggle_wifi)
    actions_menu.entryconfig(25, label=texts[current_language]['toggle_mobile_data'], command=toggle_data)

    # Permissions menu (unchanged)
    permissions_menu.entryconfig(0, label=texts[current_language]['view_app_permissions'])
    permissions_menu.entryconfig(1, label=texts[current_language]['grant_app_permission'])
    permissions_menu.entryconfig(2, label=texts[current_language]['revoke_app_permission'])

    # Camera menu (unchanged)
    camera_menu.entryconfig(0, label=texts[current_language]['stream_front_camera'])
    camera_menu.entryconfig(1, label=texts[current_language]['stream_rear_camera'])

    # Terminal menu (unchanged)
    terminal_menu.entryconfig(0, label=texts[current_language]['open_android_terminal'])

    # Language menu (unchanged)
    language_menu.entryconfig(0, label=texts[current_language]['switch_lang'])

# Language switcher

def switch_language():
    global current_language
    current_language = 'ru' if current_language == 'en' else 'en'
    update_all_texts()

def stream_camera(facing):
    try:
        subprocess.Popen([
            "scrcpy",
            "--video-source=camera",
            f"--camera-facing={facing}"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        messagebox.showerror("Error", "scrcpy is not installed or not in PATH.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to launch camera stream:\n{e}")

def stream_front_camera():
    stream_camera("front")

def stream_rear_camera():
    stream_camera("back")

# def open_advanced_camera_controls():
#     adv_win = tk.Toplevel(app)
#     adv_win.title("Advanced Camera Controls")
#     adv_win.geometry("400x500")
#     adv_win.resizable(False, False)

#     # --- Brightness Control ---
#     tk.Label(adv_win, text="Brightness:").pack(anchor="w", padx=10, pady=(10,0))
#     brightness_var = tk.IntVar(value=0)
#     brightness_slider = ttk.Scale(adv_win, from_=-100, to=100, orient="horizontal", variable=brightness_var)
#     brightness_slider.pack(fill="x", padx=10)

#     # --- Mirroring Controls ---
#     mirror_frame = tk.Frame(adv_win)
#     mirror_frame.pack(fill="x", padx=10, pady=10)
#     mirror_h_var = tk.BooleanVar()
#     mirror_v_var = tk.BooleanVar()
#     tk.Checkbutton(mirror_frame, text="Mirror Horizontally", variable=mirror_h_var).pack(anchor="w")
#     tk.Checkbutton(mirror_frame, text="Mirror Vertically", variable=mirror_v_var).pack(anchor="w")
#     def reset_mirror():
#         mirror_h_var.set(False)
#         mirror_v_var.set(False)
#     tk.Button(mirror_frame, text="Reset Mirroring", command=reset_mirror).pack(anchor="w", pady=2)

#     # --- Resolution Selection ---
#     tk.Label(adv_win, text="Resolution:").pack(anchor="w", padx=10)
#     resolution_var = tk.StringVar(value="1280x720")
#     resolution_menu = ttk.Combobox(adv_win, textvariable=resolution_var, values=[
#         "1920x1080", "1280x720", "640x480", "320x240"
#     ])
#     resolution_menu.pack(fill="x", padx=10)

#     # --- Framerate Selection ---
#     tk.Label(adv_win, text="Framerate:").pack(anchor="w", padx=10)
#     framerate_var = tk.StringVar(value="30")
#     framerate_menu = ttk.Combobox(adv_win, textvariable=framerate_var, values=["15", "24", "30", "60"])
#     framerate_menu.pack(fill="x", padx=10)

#     # --- Flashlight Toggle ---
#     def toggle_flashlight():
#         try:
#             subprocess.run(["adb", "shell", "input", "keyevent", "27"], check=True)
#         except Exception as e:
#             messagebox.showerror("Error", f"Failed to toggle flashlight:\n{e}")
#     tk.Button(adv_win, text="Toggle Flashlight", command=toggle_flashlight).pack(fill="x", padx=10, pady=10)

#     # --- Zoom Control ---
#     def zoom_in():
#         subprocess.run(["adb", "shell", "input", "swipe", "500", "500", "300", "300", "100"])
#     def zoom_out():
#         subprocess.run(["adb", "shell", "input", "swipe", "300", "300", "500", "500", "100"])
#     zoom_frame = tk.Frame(adv_win)
#     zoom_frame.pack(fill="x", padx=10, pady=5)
#     tk.Label(zoom_frame, text="Zoom:").pack(side="left")
#     tk.Button(zoom_frame, text="+", command=zoom_in).pack(side="left", padx=2)
#     tk.Button(zoom_frame, text="-", command=zoom_out).pack(side="left", padx=2)

#     # --- FFmpeg Filter Builder ---
#     def build_ffmpeg_filter():
#         filters = []
#         brightness = brightness_var.get()
#         if brightness != 0:
#             filters.append(f"eq=brightness={brightness/100.0}")
#         if mirror_h_var.get():
#             filters.append("hflip")
#         if mirror_v_var.get():
#             filters.append("vflip")
#         return ",".join(filters) if filters else "null"

#     # --- Virtual Webcam Activation ---
#     def activate_virtual_webcam():
#         def find_scrcpy_window():
#             try:
#                 top_windows = []
#                 # EnumWindows callback to get window handles and titles
#                 def enum_win_callback(hwnd, list_of_windows):
#                     if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
#                         list_of_windows.append((hwnd, win32gui.GetWindowText(hwnd)))

#                 win32gui.EnumWindows(enum_win_callback, top_windows)

#                 scrcpy_window_handle = None
#                 for hwnd, window_title in top_windows:
#                     # Check for common scrcpy window titles. Scrcpy titles often contain "scrcpy"
#                     # or "[device_name] - scrcpy" or "[device_name] - Camera"
#                     if "scrcpy" in window_title.lower() or "camera" in window_title.lower() and win32gui.GetWindowRect(hwnd) != (0,0,0,0):
#                         # Ensure it's not a minimized or off-screen window
#                         rect = win32gui.GetWindowRect(hwnd)
#                         if rect[2] - rect[0] > 0 and rect[3] - rect[1] > 0: # Check if width/height > 0
#                             scrcpy_window_handle = hwnd
#                             break
#                 return scrcpy_window_handle
#             except Exception as e:
#                 # messagebox.showerror("Error", f"Failed to find scrcpy window: {e}") # Suppress this error to avoid spamming
#                 return None

#         hwnd = find_scrcpy_window()
#         if not hwnd:
#             messagebox.showerror("Error", "scrcpy window not found. Start camera stream first.")
#             return
#         ffmpeg_cmd = [
#             "ffmpeg",
#             "-f", "gdigrab",
#             "-framerate", str(framerate_var.get()),
#             "-i", f"title=scrcpy",
#             "-vf", build_ffmpeg_filter(),
#             "-vcodec", "rawvideo",
#             "-pix_fmt", "yuv420p",
#             "-f", "dshow",
#             "-video_size", resolution_var.get(),
#             "-y",
#             "video=OBS-Camera"
#         ]
#         try:
#             def run_ffmpeg():
#                 subprocess.run(ffmpeg_cmd)
#             threading.Thread(target=run_ffmpeg, daemon=True).start()
#             messagebox.showinfo("Virtual Webcam", "Virtual webcam stream started. Select 'OBS-Camera' in your video app.")
#         except Exception as e:
#             messagebox.showerror("Error", f"Failed to start virtual webcam:\n{e}")

#     tk.Button(adv_win, text="Activate Virtual Webcam", command=activate_virtual_webcam, bg="#4caf50", fg="white").pack(fill="x", padx=10, pady=20)

#     info = (
#         "To use your Android camera as a virtual webcam:\n"
#         "1. Start a camera stream with scrcpy (Camera menu).\n"
#         "2. Install OBS Studio and start the Virtual Camera.\n"
#         "3. Click 'Activate Virtual Webcam' here.\n"
#         "4. Select 'OBS-Camera' in your video app (Zoom, Discord, etc).\n"
#         "Requires: ffmpeg, OBS Studio with Virtual Camera, pywin32."
#     )
#     tk.Label(adv_win, text=info, wraplength=380, fg='gray').pack(padx=10, pady=10)

app = tk.Tk()
app.title("ADB Toolkit")
app.iconbitmap('toolkit.ico')
app.geometry("1200x800")
app.configure(bg="#000000")


font_title = ("Consolas", 18, "bold")
font_button = ("Consolas", 12, "bold")

center_frame = tk.Frame(app, bg="#000000")
center_frame.pack(pady=20, expand=True)

if os.path.exists("toolkit.png"):
    logo_img = Image.open("toolkit.png").resize((300, 300))
    logo_photo = ImageTk.PhotoImage(logo_img)
    tk.Label(center_frame, image=logo_photo, bg="#000000").pack()


# --- Menu creation with references for language switching ---
menubar = tk.Menu(app, bg="black", fg="white", tearoff=0, font=font_button)

# Device menu
device_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
device_menu.add_command(label=texts[current_language]['check_device'], command=check_device)
device_menu.add_command(label=texts[current_language]['launch_scrcpy'], command=start_scrcpy)
device_menu.add_command(label=texts[current_language]['get_network_info'], command=get_device_network_info)
device_menu.add_command(label=texts[current_language]['extended_device_info'], command=get_extended_device_info)
device_menu.add_separator()
device_menu.add_command(label=texts[current_language]['tcp_connect_wifi'], command=tcp_connect_wifi)
device_menu.add_command(label=texts[current_language]['tcp_disconnect'], command=tcp_disconnect_wifi)
menubar.add_cascade(label=texts[current_language]['device'], menu=device_menu)

# File menu
file_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
file_menu.add_command(label=texts[current_language]['install_apk'], command=install_apk)
file_menu.add_command(label=texts[current_language]['browse_files'], command=browse_files)
file_menu.add_separator()
file_menu.add_command(label=texts[current_language]['pull_file'], command=pull_file)
file_menu.add_command(label=texts[current_language]['push_file'], command=push_file)
menubar.add_cascade(label=texts[current_language]['file_management'], menu=file_menu)

# Actions menu
actions_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
actions_menu.add_command(label=texts[current_language]['take_screenshot'], command=take_screenshot)
actions_menu.add_command(label=texts[current_language]['screenshare'], command=start_scrcpy)
actions_menu.add_command(label=texts[current_language]['front_camera_preview'], command=lambda: start_camera(front=True))
actions_menu.add_command(label=texts[current_language]['rear_camera_preview'], command=lambda: start_camera(front=False))
actions_menu.add_separator()
actions_menu.add_command(label=texts[current_language]['extract_contacts'], command=extract_contacts)
actions_menu.add_command(label=texts[current_language]['extract_gallery_images'], command=extract_gallery)
actions_menu.add_separator()
actions_menu.add_command(label=texts[current_language]['battery_info'], command=show_battery_info)
actions_menu.add_command(label=texts[current_language]['launch_app_by_package'], command=launch_app)
actions_menu.add_command(label=texts[current_language]['lock_screen'], command=lock_screen)
actions_menu.add_command(label=texts[current_language]['reboot_device'], command=reboot_device)
actions_menu.add_command(label=texts[current_language]['power_off'], command=power_off_device)
actions_menu.add_command(label=texts[current_language]['list_running_processes'], command=list_running_processes)
actions_menu.add_separator()
actions_menu.add_command(label=texts[current_language]['start_app_activity'], command=start_activity)
actions_menu.add_command(label=texts[current_language]['open_url_in_browser'], command=open_url)
actions_menu.add_command(label=texts[current_language]['simulate_tap'], command=simulate_tap)
actions_menu.add_command(label=texts[current_language]['simulate_swipe'], command=simulate_swipe)
actions_menu.add_separator()
actions_menu.add_command(label=texts[current_language]['list_installed_packages'], command=list_packages)
actions_menu.add_command(label=texts[current_language]['uninstall_app_by_package'], command=uninstall_package)
actions_menu.add_separator()
actions_menu.add_command(label=texts[current_language]['show_logcat'], command=view_logcat)
actions_menu.add_command(label=texts[current_language]['toggle_wifi'], command=toggle_wifi)
actions_menu.add_command(label=texts[current_language]['toggle_mobile_data'], command=toggle_data)
menubar.add_cascade(label=texts[current_language]['actions'], menu=actions_menu)

# Permissions menu
permissions_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
permissions_menu.add_command(label=texts[current_language]['view_app_permissions'], command=view_app_permissions)
permissions_menu.add_command(label=texts[current_language]['grant_app_permission'], command=grant_app_permission)
permissions_menu.add_command(label=texts[current_language]['revoke_app_permission'], command=revoke_app_permission)
menubar.add_cascade(label=texts[current_language]['permissions'], menu=permissions_menu)

# Add Camera menu after other menus
camera_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
camera_menu.add_command(label=texts[current_language]['stream_front_camera'], command=stream_front_camera)
camera_menu.add_command(label=texts[current_language]['stream_rear_camera'], command=stream_rear_camera)
menubar.add_cascade(label=texts[current_language]['camera'], menu=camera_menu)

# Terminal menu
terminal_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
terminal_menu.add_command(label=texts[current_language]['open_android_terminal'], command=open_terminal)
menubar.add_cascade(label=texts[current_language]['terminal'], menu=terminal_menu)

# Language menu
language_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
language_menu.add_command(label=texts[current_language]['switch_lang'], command=switch_language)
menubar.add_cascade(label=texts[current_language]['language'], menu=language_menu)

# Assign static indices for menu_refs (order is fixed)
menu_refs['device'] = 0
menu_refs['file_management'] = 1
menu_refs['actions'] = 2
menu_refs['permissions'] = 3
menu_refs['camera'] = 4
menu_refs['terminal'] = 5
menu_refs['language'] = 6

app.config(menu=menubar)

app.mainloop()
