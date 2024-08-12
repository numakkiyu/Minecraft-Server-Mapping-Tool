import socket
import threading
import requests
import dns.resolver
import time

active_mappings = {}

def start_mapping(name, address, local_port):
    if name in active_mappings:
        print(f"映射 {name} 已经在运行。")
        return True  # 如果已经在运行，返回 true 表示成功启动

    try:
        remote_host, remote_port = resolve_minecraft_server(address)
    except Exception as e:
        print(f"解析 {address} 失败: {str(e)}")
        return False  # 返回 false 解析失败

    try:
        stop_event = threading.Event()
        thread = threading.Thread(target=start_proxy, args=(name, remote_host, remote_port, local_port, stop_event))
        thread.start()
        active_mappings[name] = (thread, stop_event)

        # 启动局域网广播
        lan_thread = threading.Thread(target=broadcast_lan, args=(name, local_port, stop_event))
        lan_thread.start()
        return True  # 返回 true 连接成功
    except Exception as e:
        print(f"无法连接到 {address} ({remote_host}:{remote_port}): {str(e)}")
        return False  # 返回 false 连接失败

def stop_mapping(name):
    if name in active_mappings:
        print(f"停止映射 {name}。")
        thread, stop_event = active_mappings[name]
        stop_event.set()  # 触发停止
        thread.join()  # 线程退出
        del active_mappings[name]

def resolve_minecraft_server(server_address):
    srv_records = dns.resolver.resolve(f'_minecraft._tcp.{server_address}', 'SRV')
    for srv in srv_records:
        return str(srv.target), srv.port
    # 如果没有 SRV 记录，使用默认端口
    return server_address, 25565

def start_proxy(name, remote_host, remote_port, local_port, stop_event):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', local_port))
    server.listen(5)
    print(f"[{name}] 监听 0.0.0.0:{local_port}")

    while not stop_event.is_set():
        try:
            server.settimeout(1.0)  # 使用超时来定期检查stop_event
            client_socket, addr = server.accept()
        except socket.timeout:
            continue

        print(f"[{name}] 接受来自 {addr[0]}:{addr[1]} 的连接")

        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((remote_host, remote_port))

        client_handler = threading.Thread(target=handle_client, args=(client_socket, remote_socket, stop_event))
        server_handler = threading.Thread(target=handle_server, args=(remote_socket, client_socket, stop_event))

        client_handler.start()
        server_handler.start()

    server.close()
    print(f"[{name}] 已停止监听 {local_port}")

def handle_client(client_socket, remote_socket, stop_event):
    while not stop_event.is_set():
        try:
            data = client_socket.recv(4096)
            if len(data) == 0:
                break
            remote_socket.sendall(data)
        except:
            break
    client_socket.close()
    remote_socket.close()

def handle_server(remote_socket, client_socket, stop_event):
    while not stop_event.is_set():
        try:
            data = remote_socket.recv(4096)
            if len(data) == 0:
                break
            client_socket.sendall(data)
        except:
            break
    client_socket.close()
    remote_socket.close()

def broadcast_lan(server_name, local_port, stop_event):
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while not stop_event.is_set():
        # MC网广播格式
        message = f"[MOTD]{server_name}[/MOTD][AD]{local_port}[/AD]".encode('utf-8')
        broadcast_socket.sendto(message, ('<broadcast>', 4445))
        time.sleep(1)

    broadcast_socket.close()

def get_servers_from_json():
    try:
        url = "你的服务器列表 JSON 文件地址"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"获取 JSON 失败: {str(e)}")
        return None
