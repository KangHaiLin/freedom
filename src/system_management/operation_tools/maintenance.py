"""
运维工具 - 维护操作
清理过期日志、清理临时文件、备份配置、空间估算
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class Maintenance:
    """
    系统维护工具
    - 清理过期日志
    - 清理临时文件
    - 备份配置和元数据
    - 空间估算
    """

    def clean_expired_logs(
        self,
        log_dir: str | Path,
        retention_days: int = 30,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        清理过期日志

        Args:
            log_dir: 日志目录
            retention_days: 保留天数
            dry_run: 是否只统计不删除

        Returns:
            清理统计结果
        """
        log_path = Path(log_dir)
        if not log_path.exists():
            return {
                "deleted_count": 0,
                "deleted_bytes": 0,
                "error": "日志目录不存在",
            }

        cutoff = datetime.now() - timedelta(days=retention_days)
        cutoff_timestamp = cutoff.timestamp()

        deleted_count = 0
        deleted_bytes = 0
        errors: List[str] = []

        # 查找所有日志文件
        extensions = [".log", ".log.gz", ".txt", ".json"]
        for ext in extensions:
            for file_path in log_path.glob(f"**/*{ext}"):
                if not file_path.is_file():
                    continue

                try:
                    mtime = file_path.stat().st_mtime
                    if mtime < cutoff_timestamp:
                        size = file_path.stat().st_size
                        if not dry_run:
                            file_path.unlink()
                        deleted_count += 1
                        deleted_bytes += size
                except Exception as e:
                    errors.append(f"删除 {file_path}: {str(e)}")

        return {
            "deleted_count": deleted_count,
            "deleted_bytes": deleted_count,
            "deleted_mb": deleted_bytes / (1024**2),
            "dry_run": dry_run,
            "errors": errors,
        }

    def clean_temp_files(
        self,
        temp_dir: str | Path = "./tmp",
        max_age_hours: float = 24.0,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        清理临时文件

        Args:
            temp_dir: 临时目录
            max_age_hours: 最大保留小时数
            dry_run: 是否只统计不删除
        """
        temp_path = Path(temp_dir)
        if not temp_path.exists():
            return {
                "deleted_count": 0,
                "deleted_bytes": 0,
                "error": "临时目录不存在",
            }

        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        cutoff_timestamp = cutoff.timestamp()

        deleted_count = 0
        deleted_bytes = 0
        errors: List[str] = []

        for file_path in temp_path.glob("**/*"):
            if not file_path.is_file():
                continue

            try:
                mtime = file_path.stat().st_mtime
                if mtime < cutoff_timestamp:
                    size = file_path.stat().st_size
                    if not dry_run:
                        file_path.unlink()
                    deleted_count += 1
                    deleted_bytes += size
            except Exception as e:
                errors.append(f"删除 {file_path}: {str(e)}")

        # 清理空目录
        if not dry_run:
            for dir_path in sorted(temp_path.glob("**/*"), reverse=True):
                if dir_path.is_dir():
                    try:
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                    except Exception:
                        pass

        return {
            "deleted_count": deleted_count,
            "deleted_bytes": deleted_bytes,
            "deleted_mb": deleted_bytes / (1024**2),
            "dry_run": dry_run,
            "errors": errors,
        }

    def estimate_directory_size(self, directory: str | Path) -> Tuple[int, int]:
        """
        估算目录大小

        Returns:
            (总字节数, 文件数量)
        """
        dir_path = Path(directory)
        total_bytes = 0
        file_count = 0

        for file_path in dir_path.glob("**/*"):
            if file_path.is_file():
                try:
                    total_bytes += file_path.stat().st_size
                    file_count += 1
                except Exception:
                    pass

        return total_bytes, file_count

    def backup_configs(
        self,
        source_dirs: List[str | Path],
        backup_dir: str | Path = "./backups/config",
        include_timestamp: bool = True,
        compress: bool = True,
    ) -> Dict[str, Any]:
        """
        备份配置文件

        Args:
            source_dirs: 源配置目录列表
            backup_dir: 备份目标目录
            include_timestamp: 是否在备份文件名包含时间戳
            compress: 是否压缩
        """
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        total_files = 0
        total_bytes = 0
        errors: List[str] = []

        for source_dir in source_dirs:
            source_path = Path(source_dir)
            if not source_path.exists():
                errors.append(f"源目录 {source_dir} 不存在")
                continue

            for file_path in source_path.glob("**/*"):
                if not file_path.is_file():
                    continue

                # 跳过隐藏文件和备份文件
                if file_path.name.startswith(".") or file_path.name.endswith(".bak"):
                    continue

                rel_path = file_path.relative_to(source_path.parent)
                if include_timestamp:
                    dest_rel = rel_path.with_name(f"{rel_path.stem}_{timestamp}{rel_path.suffix}")
                else:
                    dest_rel = rel_path
                dest_path = backup_path / dest_rel
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    shutil.copy2(file_path, dest_path)
                    total_files += 1
                    total_bytes += file_path.stat().st_size
                except Exception as e:
                    errors.append(f"备份 {file_path}: {str(e)}")

        result = {
            "backup_dir": str(backup_path),
            "timestamp": timestamp,
            "total_files": total_files,
            "total_bytes": total_bytes,
            "total_mb": total_bytes / (1024**2),
            "errors": errors,
            "success": len(errors) == 0,
        }

        if compress and total_files > 0:
            # 创建压缩包
            archive_name = f"config_backup_{timestamp}"
            try:
                archive_path = shutil.make_archive(
                    str(backup_path / archive_name),
                    "gztar",
                    str(backup_path),
                )
                result["archive_path"] = archive_path
                result["archive_size_bytes"] = Path(archive_path).stat().st_size
            except Exception as e:
                result["compress_error"] = str(e)

        return result

    def cleanup_old_backups(
        self,
        backup_dir: str | Path = "./backups",
        retention_days: int = 7,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """清理过期备份"""
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            return {
                "deleted_count": 0,
                "deleted_bytes": 0,
                "error": "备份目录不存在",
            }

        cutoff = datetime.now() - timedelta(days=retention_days)
        cutoff_timestamp = cutoff.timestamp()

        deleted_count = 0
        deleted_bytes = 0
        errors: List[str] = []

        for file_path in backup_path.glob("**/*.tar.gz"):
            if not file_path.is_file():
                continue
            try:
                mtime = file_path.stat().st_mtime
                if mtime < cutoff_timestamp:
                    size = file_path.stat().st_size
                    if not dry_run:
                        file_path.unlink()
                    deleted_count += 1
                    deleted_bytes += size
            except Exception as e:
                errors.append(f"删除备份 {file_path}: {str(e)}")

        return {
            "deleted_count": deleted_count,
            "deleted_bytes": deleted_bytes,
            "deleted_mb": deleted_bytes / (1024**2),
            "dry_run": dry_run,
            "errors": errors,
        }
