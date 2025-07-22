import subprocess
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
import threading
import time
import os
import re
from colorama import Fore

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
            raise Exception("No ADB device detected. Make sure it's connected via USB and USB debugging is enabled.")

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

        messagebox.showinfo("TCP Connection", f"Successfully connected to {ip_address}:5555")

    except subprocess.CalledProcessError as e:
        messagebox.showerror("ADB Error", f"Command failed:\n{e}")
    except Exception as e:
        messagebox.showerror("Connection Error", str(e))

def tcp_disconnect_wifi():
    try:
        target_ip = simpledialog.askstring("TCP Disconnect", "Enter the device IP (e.g., 192.168.1.123):")
        if target_ip:
            subprocess.run(["adb", "disconnect", f"{target_ip}:5555"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            messagebox.showinfo("TCP Disconnect", f"Disconnected from {target_ip}:5555")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to disconnect:\n{e}")



def check_device():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    if len(lines) > 1 and "device" in lines[1]:
        messagebox.showinfo("Success", "Device detected!")
    else:
        messagebox.showerror("Error", "No connected device.")

def send_popup_message():
    msg = simpledialog.askstring("Send Message", "Enter the message to send to the phone:")
    if not msg:
        return
    msg_sanitized = msg.replace(" ", "_")
    subprocess.run(["adb", "shell", "input", "text", msg_sanitized])
    messagebox.showinfo("Done", "Message sent.")

def take_screenshot():
    subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/screen.png"])
    subprocess.run(["adb", "pull", "/sdcard/screen.png", "./screen.png"])
    messagebox.showinfo("Done", "Screenshot saved as screen.png")

def open_terminal():
    subprocess.Popen(["adb", "shell"], creationflags=subprocess.CREATE_NEW_CONSOLE)

def extract_contacts():
    try:
        output = subprocess.check_output(["adb", "shell", "content", "query", "--uri", "content://contacts/phones/"], text=True)
        with open("contacts.txt", "w", encoding="utf-8") as f:
            f.write(output)
        messagebox.showinfo("Contacts", "Contacts extracted and saved to contacts.txt")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to extract contacts.\n{e}")

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
        messagebox.showinfo("Gallery", f"Downloaded {pulled} images to folder: {save_folder}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to extract images.\n{e}")
        
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

def input_text():
    txt = simpledialog.askstring("Input Text", "Enter text to send to device:")
    if txt is not None:  # Проверяем, что пользователь не отменил ввод
        # Отправляем текст напрямую, adb shell input text обычно корректно обрабатывает пробелы
        # Если текст содержит специальные символы, возможно, потребуется дополнительное экранирование
        subprocess.run(["adb", "shell", "input", "text", txt])
        messagebox.showinfo("Done", f"Text sent: {txt}")
    else:
        messagebox.showinfo("Info", "Text input cancelled.")

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
    messagebox.showinfo("Packages", "Package list saved to packages.txt")

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
    except FileNotFoundError:
        messagebox.showerror("Error", "scrcpy is not installed or not in PATH.")

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
    local_path = simpledialog.askstring("Push File", "Enter local file path to push (e.g., ./my_local_file.txt):")
    if local_path and os.path.exists(local_path):
        remote_path = simpledialog.askstring("Push File", "Enter remote path on device (e.g., /sdcard/):", initialvalue="/sdcard/")
        if remote_path:
            try:
                subprocess.run(["adb", "push", local_path, remote_path], check=True)
                messagebox.showinfo("Success", f"File pushed to {remote_path}")
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to push file:\n{e.stderr}")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred:\n{e}")

def get_device_network_info():
    try:
        ip_output = subprocess.check_output(["adb", "shell", "ip", "addr", "show"], text=True)
        netstat_output = subprocess.check_output(["adb", "shell", "netstat", "-tupn"], text=True)
        
        info = "### IP Addresses and Interfaces ###\n" + ip_output + \
               "\n\n### Active Network Connections (TCP/UDP) ###\n" + netstat_output
        
        messagebox.showinfo("Device Network Info", info)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to get network info:\n{e.stderr}")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred:\n{e}")

def list_running_processes():
    try:
        output = subprocess.check_output(["adb", "shell", "ps", "-A"], text=True)
        messagebox.showinfo("Running Processes", output)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to list processes:\n{e.stderr}")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred:\n{e}")

def view_app_permissions():
    package = simpledialog.askstring("App Permissions", "Enter package name (e.g., com.android.chrome):")
    if package:
        try:
            output = subprocess.check_output(["adb", "shell", "dumpsys", "package", package], text=True)
            permissions = [line for line in output.splitlines() if "Permission" in line or "perm" in line]
            messagebox.showinfo(f"Permissions for {package}", "\n".join(permissions))
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to get permissions:\n{e.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{e}")

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
        # Вместо messagebox.showinfo вызываем новую функцию
        show_large_output_window("Расширенная информация об устройстве", output)
        # Можно также вывести краткое сообщение в консоль, если нужно
        print(f"[*] Расширенная информация об устройстве успешно получена и отображена.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось получить информацию об устройстве:\n{e.stderr}")
        print(f"[!] Ошибка при получении информации об устройстве: {e.stderr}")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Произошла ошибка:\n{e}")
        print(f"[!] Произошла ошибка: {e}")

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

def start_scrcpy():
    try:
        subprocess.Popen(["scrcpy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        messagebox.showinfo("Screenshare", "Scrcpy launched. A new window should appear.")
    except FileNotFoundError:
        messagebox.showerror("Error", "scrcpy is not installed or not in PATH. Please refer to README.md for installation instructions.")

def show_large_output_window(title, content):
    """Создает новое окно для отображения большого объема текста."""
    output_window = tk.Toplevel()
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
    output_window.transient(output_window.master) # Делаем его дочерним к основному окну (если есть master)
    output_window.wait_window() # Ждем закрытия этого окна

app = tk.Tk()
app.title("ADB Toolkit")
app.iconbitmap('toolkit.ico')
app.geometry("1080x720")
app.configure(bg="#000000")


font_title = ("Consolas", 18, "bold")
font_button = ("Consolas", 12, "bold")

center_frame = tk.Frame(app, bg="#000000")
center_frame.pack(pady=20, expand=True)

if os.path.exists("toolkit.png"):
    logo_img = Image.open("toolkit.png").resize((300, 300))
    logo_photo = ImageTk.PhotoImage(logo_img)
    tk.Label(center_frame, image=logo_photo, bg="#000000").pack()


menubar = tk.Menu(app, bg="black", fg="white", tearoff=0, font=font_button)

device_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
device_menu.add_command(label="Check Device", command=check_device)
device_menu.add_command(label="Launch Scrcpy", command=start_scrcpy)
device_menu.add_command(label="Get Network Info", command=get_device_network_info)
device_menu.add_command(label="Extended Device Info", command=get_extended_device_info)
device_menu.add_separator()
device_menu.add_command(label="TCP Connect over WiFi", command=tcp_connect_wifi)
device_menu.add_command(label="TCP Disconnect", command=tcp_disconnect_wifi)
menubar.add_cascade(label="Device", menu=device_menu)

file_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
file_menu.add_command(label="Install APK", command=install_apk)
file_menu.add_command(label="Browse Files", command=browse_files)
file_menu.add_separator()
file_menu.add_command(label="Pull File from Device", command=pull_file)
file_menu.add_command(label="Push File to Device", command=push_file)
menubar.add_cascade(label="File Management", menu=file_menu)

actions_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
actions_menu.add_command(label="Send Message", command=send_popup_message)
actions_menu.add_command(label="Take Screenshot", command=take_screenshot)
actions_menu.add_command(label="Screenshare", command=start_scrcpy)
actions_menu.add_command(label="Front Camera Preview", command=lambda: start_camera(front=True))
actions_menu.add_command(label="Rear Camera Preview", command=lambda: start_camera(front=False))
actions_menu.add_separator()
actions_menu.add_command(label="Extract Contacts", command=extract_contacts)
actions_menu.add_command(label="Extract Gallery Images", command=extract_gallery)
actions_menu.add_separator()
actions_menu.add_command(label="Battery Info", command=show_battery_info)
actions_menu.add_command(label="Launch App by Package", command=launch_app)
actions_menu.add_command(label="Lock Screen", command=lock_screen)
actions_menu.add_command(label="Reboot Device", command=reboot_device)
actions_menu.add_command(label="Power Off", command=power_off_device)
actions_menu.add_command(label="List Running Processes", command=list_running_processes)
actions_menu.add_separator()
actions_menu.add_command(label="Start App Activity", command=start_activity)
actions_menu.add_command(label="Open URL in Browser", command=open_url)
actions_menu.add_command(label="Input Text to Device", command=input_text)
actions_menu.add_command(label="Simulate Tap", command=simulate_tap)
actions_menu.add_command(label="Simulate Swipe", command=simulate_swipe)
actions_menu.add_separator()
actions_menu.add_command(label="List Installed Packages", command=list_packages)
actions_menu.add_command(label="Uninstall App by Package", command=uninstall_package)
actions_menu.add_separator()
actions_menu.add_command(label="Show Logcat", command=view_logcat)
actions_menu.add_command(label="Toggle WiFi", command=toggle_wifi)
actions_menu.add_command(label="Toggle Mobile Data", command=toggle_data)
menubar.add_cascade(label="Actions", menu=actions_menu)

permissions_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
permissions_menu.add_command(label="View App Permissions", command=view_app_permissions)
permissions_menu.add_command(label="Grant App Permission", command=grant_app_permission)
permissions_menu.add_command(label="Revoke App Permission", command=revoke_app_permission)
menubar.add_cascade(label="Permissions", menu=permissions_menu)

terminal_menu = tk.Menu(menubar, tearoff=0, bg="black", fg="white")
terminal_menu.add_command(label="Open Android Terminal", command=open_terminal)
menubar.add_cascade(label="Terminal", menu=terminal_menu)

app.config(menu=menubar)
app.mainloop()
