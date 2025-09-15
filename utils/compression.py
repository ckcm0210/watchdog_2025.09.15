"""
壓縮工具模組 - 支援 LZ4、Zstd 和 gzip
"""
import os
import json
import gzip
import time
from datetime import datetime
import logging

# 導入壓縮庫並增加詳細的錯誤處理
try:
    import lz4.frame
    HAS_LZ4 = True
    print("[DEBUG] LZ4 模組載入成功")
except ImportError as e:
    HAS_LZ4 = False
    print(f"[WARNING] LZ4 模組載入失敗: {e}")
    print("[WARNING] 請執行: pip install lz4")

try:
    import zstandard as zstd
    HAS_ZSTD = True
    print("[DEBUG] Zstandard 模組載入成功")
except ImportError as e:
    HAS_ZSTD = False
    print(f"[WARNING] Zstandard 模組載入失敗: {e}")
    print("[WARNING] 請執行: pip install zstandard")

import config.settings as settings

class CompressionFormat:
    """壓縮格式枚舉"""
    GZIP = 'gzip'
    LZ4 = 'lz4'
    ZSTD = 'zstd'
    
    @classmethod
    def get_extension(cls, format_type):
        """獲取格式對應的副檔名"""
        extensions = {
            cls.GZIP: '.gz',
            cls.LZ4: '.lz4',
            cls.ZSTD: '.zst'
        }
        return extensions.get(format_type, '.gz')
    
    @classmethod
    def detect_format(cls, filepath):
        """根據副檔名檢測壓縮格式"""
        if filepath.endswith('.lz4'):
            return cls.LZ4
        elif filepath.endswith('.zst'):
            return cls.ZSTD
        elif filepath.endswith('.gz'):
            return cls.GZIP
        return None
    
    @classmethod
    def get_available_formats(cls):
        """獲取可用的壓縮格式"""
        formats = [cls.GZIP]  # gzip 總是可用
        if HAS_LZ4:
            formats.append(cls.LZ4)
        if HAS_ZSTD:
            formats.append(cls.ZSTD)
        return formats
    
    @classmethod
    def validate_format(cls, format_type):
        """驗證壓縮格式是否可用"""
        if format_type == cls.LZ4 and not HAS_LZ4:
            print(f"[ERROR] LZ4 格式不可用，降級到 gzip")
            return cls.GZIP
        elif format_type == cls.ZSTD and not HAS_ZSTD:
            print(f"[ERROR] Zstandard 格式不可用，降級到 gzip")
            return cls.GZIP
        return format_type

def compress_data(data, format_type=None, level=None):
    """
    壓縮數據
    """
    if format_type is None:
        format_type = settings.DEFAULT_COMPRESSION_FORMAT
    
    # 驗證格式可用性
    format_type = CompressionFormat.validate_format(format_type)
    
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # 🔥 移除這行 - 過於詳細的調試訊息
    # print(f"[DEBUG] 使用壓縮格式: {format_type}")
    
    if format_type == CompressionFormat.LZ4 and HAS_LZ4:
        # LZ4 - 快速壓縮
        compression_level = level or settings.LZ4_COMPRESSION_LEVEL
        # 🔥 移除這行 - 過於詳細的調試訊息
        # print(f"[DEBUG] 使用 LZ4 壓縮，級別: {compression_level}")
        return lz4.frame.compress(data, compression_level=compression_level)
    
    elif format_type == CompressionFormat.ZSTD and HAS_ZSTD:
        # Zstd - 高壓縮率
        compression_level = level or settings.ZSTD_COMPRESSION_LEVEL
        # 🔥 移除這行 - 過於詳細的調試訊息
        # print(f"[DEBUG] 使用 Zstd 壓縮，級別: {compression_level}")
        compressor = zstd.ZstdCompressor(level=compression_level)
        return compressor.compress(data)
    
    else:
        # 降級到 gzip
        compression_level = level or settings.GZIP_COMPRESSION_LEVEL
        # 🔥 移除這行 - 過於詳細的調試訊息
        # print(f"[DEBUG] 使用 gzip 壓縮，級別: {compression_level}")
        return gzip.compress(data, compresslevel=compression_level)
        
def decompress_data(compressed_data, format_type=None):
    """
    解壓縮數據
    
    Args:
        compressed_data: 壓縮的字節數據
        format_type: 壓縮格式（如果未指定會自動檢測）
    
    Returns:
        解壓縮後的字符串
    """
    if format_type == CompressionFormat.LZ4 and HAS_LZ4:
        return lz4.frame.decompress(compressed_data).decode('utf-8')
    
    elif format_type == CompressionFormat.ZSTD and HAS_ZSTD:
        decompressor = zstd.ZstdDecompressor()
        return decompressor.decompress(compressed_data).decode('utf-8')
    
    else:
        # 嘗試 gzip 解壓
        try:
            return gzip.decompress(compressed_data).decode('utf-8')
        except gzip.BadGzipFile as e:
            logging.error(f"gzip 解壓縮失敗: {e}")
            # 如果 gzip 失敗，嘗試其他格式
            if HAS_LZ4:
                try:
                    return lz4.frame.decompress(compressed_data).decode('utf-8')
                except lz4.frame.LZ4FrameError as e:
                    logging.error(f"LZ4 解壓縮失敗: {e}")
                    pass
            
            if HAS_ZSTD:
                try:
                    decompressor = zstd.ZstdDecompressor()
                    return decompressor.decompress(compressed_data).decode('utf-8')
                except zstd.ZstdError as e:
                    logging.error(f"Zstandard 解壓縮失敗: {e}")
                    pass
            
            raise ValueError("無法解壓縮數據，未知的壓縮格式")

def save_compressed_file(filepath, data, format_type=None, level=None):
    """
    保存壓縮檔案
    """
    if format_type is None:
        format_type = settings.DEFAULT_COMPRESSION_FORMAT
    
    # 驗證格式可用性
    format_type = CompressionFormat.validate_format(format_type)
    
    # 準備數據
    if isinstance(data, dict):
        json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    else:
        json_data = str(data)
    
    # 添加時間戳
    if isinstance(data, dict):
        data_with_timestamp = data.copy()
        data_with_timestamp['timestamp'] = datetime.now().isoformat()
        data_with_timestamp['compression_format'] = format_type
        json_data = json.dumps(data_with_timestamp, ensure_ascii=False, separators=(',', ':'))
    
    # 壓縮數據
    compressed_data = compress_data(json_data, format_type, level)
    
    # 確定最終檔案路徑
    extension = CompressionFormat.get_extension(format_type)
    final_filepath = filepath + extension
    
    # 🔥 移除這行 - 過於詳細的調試訊息
    # print(f"[DEBUG] 保存壓縮檔案: {final_filepath}")
    
    # 寫入檔案
    with open(final_filepath, 'wb') as f:
        f.write(compressed_data)
    
    return final_filepath

def load_compressed_file(filepath):
    """
    載入壓縮檔案 - 優先選擇設定的格式
    """
    # 嘗試不同的檔案路徑
    possible_paths = []
    
    if os.path.exists(filepath):
        possible_paths.append(filepath)
    
    # 按優先順序添加副檔名 - 優先使用設定的格式
    preferred_format = settings.DEFAULT_COMPRESSION_FORMAT
    available_formats = CompressionFormat.get_available_formats()
    
    # 重新排序：首選格式放在最前面
    ordered_formats = [preferred_format] + [f for f in available_formats if f != preferred_format]
    
    for format_type in ordered_formats:
        ext = CompressionFormat.get_extension(format_type)
        test_path = filepath + ext
        if os.path.exists(test_path):
            possible_paths.append(test_path)
    
    if not possible_paths:
        return None
    
    # 優先選擇設定的格式，而不是最新的檔案
    preferred_ext = CompressionFormat.get_extension(preferred_format)
    preferred_file = filepath + preferred_ext
    
    if preferred_file in possible_paths:
        latest_file = preferred_file
        # 🔥 移除這行 - 過於詳細的調試訊息
        # print(f"[DEBUG] 使用首選格式檔案: {latest_file}")
    else:
        # 如果首選格式不存在，選擇最新的檔案
        latest_file = max(possible_paths, key=os.path.getmtime)
        # 🔥 移除這行 - 過於詳細的調試訊息
        # print(f"[DEBUG] 首選格式不存在，使用最新檔案: {latest_file}")
    
    # 檢測格式
    format_type = CompressionFormat.detect_format(latest_file)
    # 🔥 移除這行 - 過於詳細的調試訊息
    # print(f"[DEBUG] 檢測到格式: {format_type}")
    
    try:
        with open(latest_file, 'rb') as f:
            compressed_data = f.read()
        json_data = decompress_data(compressed_data, format_type)
        return json.loads(json_data)
    except (FileNotFoundError, PermissionError, OSError) as e:
        logging.error(f"載入壓縮檔案失敗 {latest_file}: {e}")
        return None


def get_compression_stats(filepath):
    """
    獲取壓縮統計資訊
    
    Args:
        filepath: 檔案路徑
    
    Returns:
        壓縮統計字典
    """
    if not os.path.exists(filepath):
        return None
    
    format_type = CompressionFormat.detect_format(filepath)
    file_size = os.path.getsize(filepath)
    
    try:
        with open(filepath, 'rb') as f:
            compressed_data = f.read()
        
        decompressed_data = decompress_data(compressed_data, format_type)
        original_size = len(decompressed_data.encode('utf-8'))
        
        compression_ratio = (1 - file_size / original_size) * 100 if original_size > 0 else 0
        
        return {
            'format': format_type,
            'compressed_size': file_size,
            'original_size': original_size,
            'compression_ratio': compression_ratio,
            'savings_bytes': original_size - file_size
        }
    
    except (gzip.BadGzipFile, lz4.frame.LZ4FrameError, zstd.ZstdError, json.JSONDecodeError) as e:
        logging.error(f"獲取壓縮統計資訊失敗: {filepath}, 錯誤: {e}")
        return {
            'format': format_type,
            'compressed_size': file_size,
            'original_size': None,
            'compression_ratio': None,
            'savings_bytes': None
        }

def migrate_baseline_format(old_filepath, new_format):
    """
    遷移基準線檔案格式
    
    Args:
        old_filepath: 舊檔案路徑
        new_format: 新的壓縮格式
    
    Returns:
        新檔案路徑
    """
    # 載入舊檔案
    data = load_compressed_file(old_filepath)
    if data is None:
        return None
    
    # 移除舊的壓縮格式標記
    if 'compression_format' in data:
        del data['compression_format']
    
    # 生成新檔案路徑
    base_path = old_filepath
    for ext in ['.gz', '.lz4', '.zst']:
        if base_path.endswith(ext):
            base_path = base_path[:-len(ext)]
            break
    
    new_filepath = save_compressed_file(base_path, data, new_format)
    
    # 刪除舊檔案
    try:
        os.remove(old_filepath)
    except OSError as e:
        logging.error(f"刪除舊檔案失敗: {old_filepath}, 錯誤: {e}")
        pass
    
    return new_filepath

def test_compression_support():
    """測試壓縮支援"""
    print("=" * 50)
    print("壓縮模組測試")
    print("=" * 50)
    print(f"LZ4 支援: {HAS_LZ4}")
    print(f"Zstandard 支援: {HAS_ZSTD}")
    print(f"可用格式: {CompressionFormat.get_available_formats()}")
    print(f"預設格式: {settings.DEFAULT_COMPRESSION_FORMAT}")
    print(f"驗證後格式: {CompressionFormat.validate_format(settings.DEFAULT_COMPRESSION_FORMAT)}")
    print("=" * 50)