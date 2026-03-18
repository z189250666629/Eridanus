"""Random string helpers hosted under core.toolkit."""

import random


def random_str(
    random_length=7,
    chars="AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789",
):
    """
    生成随机字符串作为验证码。
    """

    string = ""
    length = len(chars) - 1
    for _ in range(random_length):
        string += chars[random.randint(0, length)]
    return string


def random_session_hash(random_length):
    # 给 gradio 一类的 api 用，生成随机 session_hash，避免多任务撞车导致推理出错。
    return random_str(random_length, "abcdefghijklmnopqrstuvwxyz1234567890")


__all__ = ["random_session_hash", "random_str"]
