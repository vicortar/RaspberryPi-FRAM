import machine
import utime
import struct  # 导入 struct 模块

# --- SPI 配置 ---
spi = machine.SPI(0,
                  baudrate=100000,
                  sck=machine.Pin(18),  # 可以根据你的实际连接修改
                  mosi=machine.Pin(19),
                  miso=machine.Pin(16))
cs_pin = 17
cs = machine.Pin(cs_pin, machine.Pin.OUT, value=1)

# --- FRAM 命令 ---
WRITE_ENABLE_COMMAND = 0x06
WRITE_COMMAND = 0x02
READ_COMMAND = 0x03

# --- 常量 ---
WRITE_ADDRESS = 0x000020  # 设置一个用于写入用户输入数据的起始地址
MAX_STRING_LENGTH = 600000  # 设置最大字符串长度为 600000

# --- 低级别 SPI 传输函数 ---
def _transfer(data_out, read_length=0):
    cs.value(0)
    if read_length > 0:
        spi.write(data_out)  # 先发送命令和地址
        data_in = spi.read(read_length)  # 然后读取指定长度的数据
        cs.value(1)
        return data_in
    else:
        spi.write(data_out)  # 对于写入操作，直接发送数据
        cs.value(1)
        return None

# --- FRAM 控制函数 ---
def write_enable():
    _transfer(bytes([WRITE_ENABLE_COMMAND]))

def write_bytes(address, data):
    write_enable()
    command_bytes = bytes([WRITE_COMMAND, (address >> 16) & 0xFF, (address >> 8) & 0xFF, address & 0xFF])
    try:
        _transfer(command_bytes + data)
        utime.sleep_ms(1)  # 写入后添加延时
        return True
    except Exception as e:
        print(f"写入 FRAM 失败: {e}")
        return False

def read_bytes(address, length):
    command_bytes = bytes([READ_COMMAND, (address >> 16) & 0xFF, (address >> 8) & 0xFF, address & 0xFF])
    print(f"read_bytes: 尝试读取 {length} 字节，发送命令: {command_bytes.hex()}") # 调试信息
    try:
        data = _transfer(command_bytes, read_length=length)
        print(f"read_bytes: 接收到的数据: {data.hex() if data else None}") # 调试信息
        utime.sleep_us(1)  # 读取前添加延时
        return data
    except Exception as e:
        print(f"read_bytes: 读取 FRAM 失败: {e}")
        return None

# --- 高级别字符串读写函数 (带长度前缀) ---
def write_string_with_length(address, text):
    data = text.encode('utf-8')
    length = len(data)

    if length > MAX_STRING_LENGTH:
        print(f"警告：输入内容过长 ({length} 字节)，最大允许 {MAX_STRING_LENGTH} 字节。")
        return False

    length_bytes = struct.pack(">H", length)  # 使用 big-endian 的 2 字节存储长度
    print(f"写入字符串: '{text}'，长度: {length}")
    print(f"将长度 {length} 打包为字节: {length_bytes.hex()}")
    print(f"尝试写入长度字节到地址: 0x{address:06X}")
    if write_bytes(address, length_bytes):
        print(f"成功写入长度字节到地址: 0x{address:06X}")
        print(f"尝试写入数据到地址: 0x{address + 2:06X}")
        if write_bytes(address + 2, data):
            print(f"成功写入数据到地址: 0x{address + 2:06X}")
            print(f"成功完成写入操作")
            return True
        else:
            print(f"写入数据到地址 0x{address + 2:06X} 失败")
            return False
    else:
        print(f"写入长度字节到地址 0x{address:06X} 失败")
        return False

def read_string_with_length(address):
    print(f"准备从地址 0x{address:06X} 读取数据...")
    print(f"尝试读取长度字节 (2 字节)")
    length_bytes = read_bytes(address, 2)
    print(f"读取到的原始长度字节: {length_bytes.hex() if length_bytes else None}")
    if length_bytes is None or len(length_bytes) != 2:
        print(f"错误：无法从地址 0x{address:06X} 读取长度信息。")
        return None

    length = struct.unpack(">H", length_bytes)[0]
    print(f"读取到的长度: {length}")

    if length > MAX_STRING_LENGTH:
        print(f"警告：读取到的长度 {length} 大于最大允许长度 {MAX_STRING_LENGTH}，可能数据已损坏。")
        return None

    utime.sleep_ms(1) # 添加延时
    
    print(f"尝试读取数据字节 (长度: {length}) 从地址: 0x{address + 2:06X}")
    data = read_bytes(address + 2, length)
    print(f"读取到的原始数据字节 (前 20): {data[:20].hex() if data and len(data) >= 20 else (data.hex() if data else None)}...")
    if data:
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            print("警告：读取到的数据无法解码为 UTF-8 字符串。")
            return None
    else:
        print(f"警告：从地址 0x{address + 2:06X} 未读取到数据")
        return None

# --- 主循环 ---
while True:
    user_input = input("请输入要写入的内容 (输入 'read' 读取, 'quit' 退出): ")

    if user_input.lower() == 'quit':
        break
    elif user_input.lower() == 'read':
        read_back_string = read_string_with_length(WRITE_ADDRESS)
        if read_back_string:
            print(f"从地址 0x{WRITE_ADDRESS:06X} 读取到的数据: '{read_back_string}'")
        else:
            print(f"地址 0x{WRITE_ADDRESS:06X} 没有有效数据或读取失败。")
    else:
        print(f"准备将内容 '{user_input}' 写入到地址 0x{WRITE_ADDRESS:06X}")
        if write_string_with_length(WRITE_ADDRESS, user_input):
            print("写入成功。")
        else:
            print("写入失败。")

print("程序结束。")