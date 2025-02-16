#  /*
#   * Copyright (c) 2025 Xmmy.
#   *
#   * 本程序遵循 GNU General Public License v3.0 发布，允许在遵守该许可证条款的前提下重新分发和修改。
#   *
#   * 本程序按“现状”提供，不附带任何明示或暗示的担保。
#   *
#   * 详细许可证内容请参见：<https://www.gnu.org/licenses/gpl-3.0.en.html>
#   */

import argparse
import hashlib
import os
import shutil
import sys
import zlib
from pathlib import Path
from typing import Union


def get_unique_path(dest_dir: Union[str, Path], filename: str) -> Path:
    """
    生成目标目录中唯一的文件路径，若存在重名则添加数字后缀。
    返回 Path 对象以确保类型一致性。
    """
    dest_dir = Path(dest_dir)
    base, ext = os.path.splitext(filename)
    counter = 1

    while True:
        dest_path = dest_dir / filename
        if not dest_path.exists():
            return dest_path
        filename = f"{base}_{counter}{ext}"
        counter += 1


def compute_file_hash(file_path: Path, algorithm: str) -> str:
    """
    根据指定算法计算文件哈希值，并返回其字符串表示。
    支持算法: CRC32, MD5, SHA256, SHA384, SHA512, MD2, MD4。
    """
    algorithm_upper = algorithm.upper()
    if algorithm_upper == "CRC32":
        hash_val = 0
        with file_path.open('rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_val = zlib.crc32(chunk, hash_val)
        return str(hash_val & 0xffffffff)
    else:
        try:
            hash_obj = hashlib.new(algorithm.lower())
        except ValueError:
            raise ValueError(f"不支持的哈希算法: {algorithm}")
        with file_path.open('rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()


def main():
    parser = argparse.ArgumentParser(description='提取指定后缀文件到目标目录')
    parser.add_argument('target_dir', type=str, help='目标目录路径')
    parser.add_argument('-S', '--source',
                        type=str,
                        default=os.getcwd(),
                        help='源目录路径（默认为当前目录）')
    parser.add_argument('-M', '--move',
                        action='store_true',
                        help='移动文件而不是复制')
    parser.add_argument('-P', '--prefix-length',
                        type=int,
                        default=0,
                        help='前缀位数，非 0 表示启用文件哈希前缀（例如：-P 5 表示初始取 5 位哈希，冲突时逐步增加）')
    parser.add_argument('-E', '--extension',
                        type=str,
                        required=True,
                        help='指定待提取文件的后缀（例如：.exe, .txt），注意需包含点号')
    parser.add_argument('-C', '--case-sensitive',
                        action='store_true',
                        help='强制匹配后缀大小写，默认忽略大小写')
    parser.add_argument('-A', '--algorithm',
                        type=str,
                        default='SHA512',
                        help='选择哈希算法，用于生成文件名前缀，支持：CRC32, MD2, MD4, MD5, SHA256, SHA384, SHA512')

    args = parser.parse_args()

    source_dir = Path(args.source).resolve()
    target_dir = Path(args.target_dir).resolve()

    if not source_dir.is_dir():
        print(f"错误：源目录 '{source_dir}' 不存在")
        sys.exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)

    # 标准化扩展名格式，确保以 '.' 开头
    ext = args.extension if args.extension.startswith('.') else '.' + args.extension

    processed_files = 0

    for file_path in source_dir.rglob('*'):
        if file_path.is_file():
            # 根据是否强制大小写匹配判断扩展名是否符合要求
            if args.case_sensitive:
                match_ext = file_path.suffix == ext
            else:
                match_ext = file_path.suffix.lower() == ext.lower()
            if match_ext:
                try:
                    if args.prefix_length != 0:
                        full_hash = compute_file_hash(file_path, args.algorithm)
                        initial_len = abs(args.prefix_length)
                        prefix_len = initial_len
                        while True:
                            prefix = full_hash[:prefix_len]
                            new_filename = f"{prefix}_{file_path.name}"
                            dest_path = target_dir / new_filename
                            if not dest_path.exists():
                                break
                            if prefix_len >= len(full_hash):
                                dest_path = get_unique_path(target_dir, new_filename)
                                break
                            prefix_len += 1
                    else:
                        new_filename = file_path.name
                        dest_path = get_unique_path(target_dir, new_filename)

                    if args.move:
                        shutil.move(str(file_path), str(dest_path))
                    else:
                        shutil.copy2(str(file_path), str(dest_path))

                    processed_files += 1
                    print(f"成功处理：{file_path} -> {dest_path}")
                except Exception as e:
                    print(f"处理失败 {file_path}: {str(e)}")

    print(f"\n操作完成！共处理 {processed_files} 个文件")
    print(f"目标目录：{target_dir}")


if __name__ == '__main__':
    main()
