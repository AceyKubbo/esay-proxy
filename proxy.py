import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import socket

class ProxyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("端口转发代理工具")

        # 存储转发规则
        self.forwarding_rules = []

        # 创建 GUI 元素
        self.create_widgets()

    def create_widgets(self):
        # 表格显示转发规则
        self.tree = ttk.Treeview(self.root, columns=("Local Port", "Remote Host", "Remote Port"), show="headings")
        self.tree.heading("Local Port", text="本地端口")
        self.tree.heading("Remote Host", text="远程主机")
        self.tree.heading("Remote Port", text="远程端口")
        self.tree.pack(pady=10)

        # 添加规则按钮
        self.add_button = tk.Button(self.root, text="添加转发规则", command=self.add_forwarding_rule)
        self.add_button.pack(side=tk.LEFT, padx=5)

        # 删除规则按钮
        self.delete_button = tk.Button(self.root, text="删除选中规则", command=self.delete_forwarding_rule)
        self.delete_button.pack(side=tk.LEFT, padx=5)

        # 启动代理按钮
        self.start_button = tk.Button(self.root, text="启动代理", command=self.start_proxy)
        self.start_button.pack(side=tk.LEFT, padx=5)

        # 停止代理按钮
        self.stop_button = tk.Button(self.root, text="停止代理", command=self.stop_proxy, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # 日志文本框
        self.log_text = tk.Text(self.root, height=10, width=60)
        self.log_text.pack(pady=10)

    def add_forwarding_rule(self):
        # 弹出对话框获取用户输入
        local_port = simpledialog.askinteger("添加规则", "请输入本地端口:")
        if local_port is None:
            return

        remote_host = simpledialog.askstring("添加规则", "请输入远程主机 IP 地址:")
        if remote_host is None:
            return

        remote_port = simpledialog.askinteger("添加规则", "请输入远程端口:")
        if remote_port is None:
            return

        # 添加规则到表格
        self.tree.insert("", tk.END, values=(local_port, remote_host, remote_port))
        self.forwarding_rules.append((local_port, remote_host, remote_port))
        self.log_text.insert(tk.END, f"已添加转发规则: {local_port} -> {remote_host}:{remote_port}\n")

    def delete_forwarding_rule(self):
        # 删除选中规则
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择要删除的规则")
            return

        self.tree.delete(selected_item)
        # 更新转发规则列表
        self.forwarding_rules = [(local_port, remote_host, remote_port) 
                                for local_port, remote_host, remote_port in self.forwarding_rules 
                                if (local_port, remote_host, remote_port) != 
                                (self.tree.set(selected_item, "Local Port"),
                                 self.tree.set(selected_item, "Remote Host"),
                                 self.tree.set(selected_item, "Remote Port"))]
        self.log_text.insert(tk.END, "已删除选中规则\n")

    def start_proxy(self):
        if not self.forwarding_rules:
            messagebox.showwarning("警告", "请先添加转发规则")
            return

        # 启动代理线程
        self.proxy_thread = threading.Thread(target=self.run_proxy_server)
        self.proxy_thread.daemon = True
        self.proxy_thread.start()

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, "代理已启动\n")

    def stop_proxy(self):
        # 停止代理
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.log_text.insert(tk.END, "代理已停止\n")

    def run_proxy_server(self):
        self.running = True
        self.log_text.insert(tk.END, "开始处理转发规则...\n")

        for local_port, remote_host, remote_port in self.forwarding_rules:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                server_socket.bind(("127.0.0.1", local_port))
                server_socket.listen(5)
                self.log_text.insert(tk.END, f"[*] Listening on 127.0.0.1:{local_port}\n")

                while self.running:
                    client_socket, addr = server_socket.accept()
                    self.log_text.insert(tk.END, f"[*] Accepted connection from {addr[0]}:{addr[1]}\n")

                    proxy_thread = threading.Thread(target=self.handle_client, 
                                                  args=(client_socket, remote_host, remote_port))
                    proxy_thread.daemon = True
                    proxy_thread.start()
            except Exception as e:
                self.log_text.insert(tk.END, f"Error binding to port {local_port}: {e}\n")
            finally:
                server_socket.close()

    def handle_client(self, client_socket, remote_host, remote_port):
        try:
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((remote_host, remote_port))

            client_to_remote_thread = threading.Thread(
                target=self.forward_data,
                args=(client_socket, remote_socket)
            )
            remote_to_client_thread = threading.Thread(
                target=self.forward_data,
                args=(remote_socket, client_socket)
            )
            client_to_remote_thread.daemon = True
            remote_to_client_thread.daemon = True
            client_to_remote_thread.start()
            remote_to_client_thread.start()

            client_to_remote_thread.join()
            remote_to_client_thread.join()
        except Exception as e:
            self.log_text.insert(tk.END, f"Error: {e}\n")
        finally:
            client_socket.close()
            remote_socket.close()

    def forward_data(self, source, destination):
        while self.running:
            try:
                data = source.recv(4096)
                if not data:
                    break
                destination.send(data)
            except Exception as e:
                self.log_text.insert(tk.END, f"Forwarding error: {e}\n")
                break

if __name__ == "__main__":
    root = tk.Tk()
    app = ProxyApp(root)
    root.mainloop()