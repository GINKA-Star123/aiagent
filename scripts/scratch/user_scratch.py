import json
from bilibili_api import user, sync

# 实例化
u = user.User(406948651)


async def main():
    # 用于记录下一次起点
    offset = ""

    # 用于存储所有动态
    dynamics = []

    # 无限循环，直到 has_more != 1
    while True:
        # 获取该页动态
        page = await u.get_dynamics_new(offset)

        dynamics.extend(page["items"])

        if page["has_more"] != 1:
            # 如果没有更多动态，跳出循环
            break

        # 设置 offset，用于下一轮循环
        offset = page["offset"]

    # 打印动态数量
    print(f"共有 {len(dynamics)} 条动态")


# 入口
sync(main())