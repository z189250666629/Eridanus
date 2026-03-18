"""Memory inspection helpers hosted under core.toolkit."""

import gc
import os


class _Logger:
    def info(self, msg):
        print(msg)


logger = _Logger()


def get_memory_usage():
    """获取当前进程的内存使用情况。"""

    import psutil

    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    rss_mb = memory_info.rss / 1024 / 1024
    return round(rss_mb, 2)


def analyze_objects(index=0):
    """分析内存中的对象。"""

    from pympler import muppy, summary

    gc.collect()
    all_objects = muppy.get_objects()
    sum1 = summary.summarize(all_objects)

    logger.info(f"point: {index}  总对象数: {len(all_objects)}, 内存占用: {get_memory_usage()}MB")
    logger.info("Top 10 对象类型:")
    for i, (obj_type, count, total_size) in enumerate(sum1[:10]):
        size_mb = total_size / (1024 * 1024)
        logger.info(f"  {i + 1}. {str(obj_type):<30} 数量:{count:<8} 大小:{size_mb:.2f}MB")


class MemoryMonitor:
    get_memory_usage = staticmethod(get_memory_usage)
    analyze_objects = staticmethod(analyze_objects)


__all__ = ["MemoryMonitor", "analyze_objects", "get_memory_usage"]
