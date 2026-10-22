# 后端一面算法详解补充：22 类题目与完整参考实现

这是[主面试指南](F:/aiagent/docs/interview/china-commerce-ads-backend-first-round-guide.md)的算法扩展。主指南已给出 14 类完整实现，本文补齐其余 22 类，合起来覆盖原先的 36 类题目。全排列与子集作为同一训练类别分别给实现。

使用方式：先读题意与不变量，独立写代码，再对照。Python 是参考语言，不代表面试必定允许使用；选择你能稳定解释和调试的语言。下列代码是训练示例，不是项目业务文件，也不具备生产服务的并发、授权和持久化能力。

## 一、36 类题目覆盖表

| 原编号 | 题目 | 完整实现位置 |
| --- | --- | --- |
| 1–6 | 两数之和、最长无重复、和为K、合并区间、二分、反转链表 | 主指南 4.3–4.5 |
| 7–9 | 环入口、合并链表、有效括号 | 本文 A01–A03 |
| 10 | 二叉树层序 | 主指南 4.7 |
| 11 | 最近公共祖先 | 本文 A04 |
| 12–14 | 岛屿、课程表、TopK 高频 | 主指南 4.4、4.6 |
| 15 | 数组第K大 | 本文 A05 |
| 16 | LRU | 主指南 4.5 |
| 17–18 | 股票I、爬楼梯 | 本文 A06–A07 |
| 19 | 最小覆盖子串 | 主指南 4.3 |
| 20–26 | 三数之和、接雨水、窗口最大、旋转数组、K组反转、合并K链表、树最大路径 | 本文 A08–A14 |
| 27–28 | 零钱兑换、LIS | 主指南 4.7 |
| 29–36 | LCS、单词拆分、中位数、排列/子集、并查集、编辑距离、最短路、LFU | 本文 A15–A22 |

建议先完成 P0，再练 P1，LFU 等 P2 不要挤占项目讲述、SQL 和基础题时间。

## 二、链表与树的公共定义

下面示例使用对象身份判断节点，而不是仅比较 val。两个值相同的节点并不一定是同一个节点。单独复制某一题练习时，带上所需定义；将本文按顺序执行时只定义一次即可。

```python
class ListNode:
    def __init__(self, val: int = 0, next_node=None):
        self.val = val
        self.next = next_node


class TreeNode:
    def __init__(self, val: int = 0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
```

## 三、链表、栈与二叉树基础

### A01：环形链表，进一步找环入口

**题意与约束**

给定链表头，存在环则返回环的第一个节点，否则返回 None。不能修改链表，要求额外空间 O(1)。这比“只判断有环”多一步定位。

**推导**

慢指针每次一步，快指针每次两步。如果无环，快指针最终到达 None；如果有环，它们会相遇。设头到入口距离为 a、入口到相遇位置距离为 b、环长为 L，相遇时可推得 `a+b` 是 L 的整数倍，因此从头走 a 步，与从相遇点沿环走 a 步，会同时到达入口。

相遇后把一个指针放回头，另一个保持在相遇点，两者每次一步，再次相遇就是入口。比较的是节点对象身份。

```python
def detect_cycle(head: ListNode | None) -> ListNode | None:
    slow = fast = head
    while fast is not None and fast.next is not None:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:
            entry = head
            while entry is not slow:
                entry = entry.next
                slow = slow.next
            return entry
    return None
```

**复杂度与自测**：O(n) 时间、O(1) 空间。空链表、单节点无环、单节点指向自身、尾部连回中间都要测试。常见错误是先读 fast.next.next 再判断 fast 是否为空，或用值相等代替节点相同。

**追问：为什么不是走到任意环节点就结束？** 因为第一阶段只证明进入同一个环，入口取决于链表头路径，第二阶段才使用头到入口的距离关系。

### A02：合并两个有序链表

**题意**：两个递增链表，合并为递增链表。默认无环且不共享节点；允许复用原节点，因此会修改原链路。若不允许，应新建输出节点。

**不变量**：dummy.next 到 tail 已有序，且包含所有已消费节点。每次从两个头部取较小值；某一条耗尽后，另一条剩余部分已经有序，可以整体连接。

```python
def merge_two_lists(a: ListNode | None, b: ListNode | None) -> ListNode | None:
    dummy = tail = ListNode()
    while a is not None and b is not None:
        if a.val <= b.val:
            tail.next = a
            a = a.next
        else:
            tail.next = b
            b = b.next
        tail = tail.next
    tail.next = a if a is not None else b
    return dummy.next
```

**复杂度**：O(m+n) 时间、O(1) 额外空间，不包含输入。相等时先取 a，可以给出稳定的跨列表约定。

**自测**：两条都空、一条空、`1->3` 与 `1->2`、长度相差很大。若链表共享尾节点，这段标准实现可能产生错误连接甚至环，必须事先说明输入假设，而不是认为所有链表题都无条件安全。

### A03：有效括号

**题意**：判断只包含 `()[]{}` 的字符串是否匹配。本文将其他字符视为非法，而不是静默忽略。

**为什么用栈**：最近出现的未闭合左括号必须最先闭合，正好是后进先出。只比较左右数量无法拒绝 `([)]`。

```python
def valid_parentheses(text: str) -> bool:
    pairs = {')': '(', ']': '[', '}': '{'}
    stack: list[str] = []
    for char in text:
        if char in '([{':
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                return False
        else:
            return False
    return not stack
```

**复杂度与边界**：O(n) 时间、O(n) 最坏空间。空串为 True，单独右括号为 False，结束时还有左括号也为 False。若题目是“包含其他普通文本”，需要另行约定忽略规则。

**追问：只有一种括号能不用栈吗？** 可以维护未闭合计数，途中不为负、最终为零；多种类型则计数不足以表达嵌套顺序。

### A04：二叉树最近公共祖先，支持目标缺失

**题意**：在普通二叉树中找 p 和 q 的最低公共祖先；目标不存在则返回 None，允许 p 与 q 是同一节点。

经典短代码通常默认两个节点都存在。这里递归返回“候选节点、已找到的目标计数”，最终只有计数为 2 才返回结果。每个目标按对象身份计数，p=q 时同一个节点可以同时满足两项。

```python
def lowest_common_ancestor(root: TreeNode | None, p: TreeNode, q: TreeNode):
    def visit(node):
        if node is None:
            return None, 0
        left, left_hits = visit(node.left)
        right, right_hits = visit(node.right)
        hits = left_hits + right_hits + int(node is p) + int(node is q)
        if node is p or node is q:
            return node, hits
        if left is not None and right is not None:
            return node, hits
        return (left if left is not None else right), hits

    candidate, hits = visit(root)
    return candidate if hits == 2 else None
```

**推导**：若目标分居两侧，当前节点是首次汇合；若当前节点就是一个目标，且另一个在其子树，当前节点自然也是祖先。若两个都在同一边，就把那一边的候选向上传。

**复杂度**：O(n) 时间、O(h) 递归栈，退化树 h=n，Python 要注意递归深度。输入应是真正的树，不含共享子节点或环。

**追问：二叉搜索树能更快吗？** 若两个目标确实存在，可利用键大小走向分叉点，时间 O(h)；先确认比较键是否唯一及节点存在性，不能把 BST 假设套到普通树。

## 四、堆、扫描与双指针

### A05：数组第 K 大

**题意**：第 K 大按排序位置计数，重复值算多次，不是第 K 个不同值。选择大小 K 的小根堆是稳妥易讲的方案。

**不变量**：堆始终保留目前见到的最大 K 个元素，堆顶是其中最小的，也就是当前第 K 大。新值不超过堆顶时，不可能进入最大 K 集合。

```python
import heapq


def kth_largest(nums: list[int], k: int) -> int:
    if not 1 <= k <= len(nums):
        raise ValueError('k is out of range')
    heap = nums[:k]
    heapq.heapify(heap)
    for index in range(k, len(nums)):
        value = nums[index]
        if value > heap[0]:
            heapq.heapreplace(heap, value)
    return heap[0]
```

**复杂度**：O(n log(k+1)) 时间上界、O(k) 额外空间。初始切片只复制 k 个元素；后续按下标遍历，避免 `nums[k:]` 又复制剩余元素，把空间意外放大到 O(n)。面试分析应对应实际代码，而不是只看核心数据结构。

**自测**：`[3,2,1,5,6,4],2 -> 5`；`[2,2,1],2 -> 2`；k=1、k=n；非法 k。

**追问**：快速选择平均 O(n)，最坏 O(n²)，随机化降低坏情况概率；排序 O(n log n) 可能足够，先根据规模选择，不为了最优平均复杂度引入自己解释不清的实现。

### A06：买卖股票最佳时机 I

**题意**：只能买一次、卖一次，且先买后卖，也可以不交易。不是允许无限次交易的版本。

**不变量**：minimum 是当前日期以前及当天的最低价格，answer 是已扫描前缀内的最大合法收益。对每一天，只需问“如果今天卖，之前最低价是多少”。

```python
def max_profit(prices: list[int]) -> int:
    minimum = float('inf')
    answer = 0
    for price in prices:
        minimum = min(minimum, price)
        answer = max(answer, price - minimum)
    return answer
```

**复杂度**：O(n) 时间、O(1) 空间。`[7,1,5,3,6,4] -> 5`，递减序列得 0，空数组得 0。不能先求全局最大与最小再相减，因为最大值可能出现在最小值之前。

**追问：允许多次买卖呢？** 无手续费等附加约束时，可以累计相邻上涨收益；有手续费、冷冻期或次数限制时，需要重新定义 DP 状态，不能套一次买卖代码。

### A07：爬楼梯

**题意**：每次上 1 或 2 阶，求到 n 阶的不同走法。本文 n>=0，n=0 定义为一种空走法。

**推导**：最后一步来自 n-1 或 n-2，两组不重叠，故 `f(n)=f(n-1)+f(n-2)`。只依赖前两项，不必保存整个数组。

```python
def climb_stairs(n: int) -> int:
    if n < 0:
        raise ValueError('n must be non-negative')
    previous, current = 1, 1
    for _ in range(n):
        previous, current = current, previous + current
    return previous
```

**复杂度**：按固定宽度整数模型 O(n) 时间、O(1) 个状态；Python 大整数随结果位数增长，精确位复杂度不再是常量算术。普通面试先明确使用哪种分析模型。

**自测**：0→1，1→1，2→2，3→3。不要只背两个初值而忘了题目是否允许 n=0；在 Go 等固定宽度整数中还要注意溢出。

### A08：三数之和

**题意**：返回所有和为 0 的不同三元组，不能重复使用一个下标；值组合不重复。

**推导**：排序后固定第一个数，剩余区间使用双指针。和过小则增大左侧，过大则减小右侧。排序提供了移动方向的单调性。外层与找到解后的双指针都要跳过重复值。

```python
def three_sum(nums: list[int]) -> list[list[int]]:
    values = sorted(nums)
    answer: list[list[int]] = []
    for first in range(len(values) - 2):
        if values[first] > 0:
            break
        if first > 0 and values[first] == values[first - 1]:
            continue
        left, right = first + 1, len(values) - 1
        while left < right:
            total = values[first] + values[left] + values[right]
            if total < 0:
                left += 1
            elif total > 0:
                right -= 1
            else:
                answer.append([values[first], values[left], values[right]])
                left += 1
                right -= 1
                while left < right and values[left] == values[left - 1]:
                    left += 1
                while left < right and values[right] == values[right + 1]:
                    right -= 1
    return answer
```

**复杂度**：O(n²) 时间；本实现复制排序，额外 O(n)，输出空间另计。`[-1,0,1,2,-1,-4]` 返回两组；全零只返回 `[0,0,0]`。常见错误是只给外层去重，导致结果重复。

### A09：接雨水

**题意**：非负柱高、宽度为 1，求总积水。每格容量由左右最高边界的较低者决定。

**不变量与移动理由**：维护两侧已知最高值。若 left_max<=right_max，左边这一格的右侧至少存在 right_max 的边界，其水量由 left_max 决定，因此可结算左侧；反之结算右侧。无需提前知道较高那一侧的最终全局最大值。

```python
def trap_rainwater(heights: list[int]) -> int:
    left, right = 0, len(heights) - 1
    left_max = right_max = 0
    water = 0
    while left <= right:
        if left_max <= right_max:
            left_max = max(left_max, heights[left])
            water += left_max - heights[left]
            left += 1
        else:
            right_max = max(right_max, heights[right])
            water += right_max - heights[right]
            right -= 1
    return water
```

**复杂度**：O(n) 时间、O(1) 空间。`[4,2,0,3,2,5] -> 9`，单调递增/递减得 0，空数组得 0。输入默认非负，若允许负海拔需重新定义场景。

**追问**：前后缀最大数组也可 O(n) 时间，但用 O(n) 空间；单调栈能按凹槽结算，选择自己能解释正确性的方案。

### A10：滑动窗口最大值

**题意**：返回每个长度 k 的连续窗口最大值。k<=0 视为非法；k>n 没有完整窗口，返回空列表。

**为什么存索引**：必须知道元素何时过期；只存数值很难正确区分重复值。队列中的索引递增，对应数值单调递减。新值更大时，旧小值既更小又更早过期，不可能再成为最大值，可以移除。

```python
from collections import deque


def sliding_window_max(nums: list[int], k: int) -> list[int]:
    if k <= 0:
        raise ValueError('k must be positive')
    queue = deque()
    answer: list[int] = []
    for right, value in enumerate(nums):
        while queue and queue[0] <= right - k:
            queue.popleft()
        while queue and nums[queue[-1]] <= value:
            queue.pop()
        queue.append(right)
        if right >= k - 1:
            answer.append(nums[queue[0]])
    return answer
```

**复杂度**：O(n) 时间，因为每个索引最多入队和出队各一次，不是双 while 就 O(n²)。队列 O(min(n,k)) 空间，输出另计。经典样例 `[1,3,-1,-3,5,3,6,7],3 -> [3,3,5,5,6,7]`。

### A11：搜索旋转排序数组

**题意**：原数组严格递增，旋转后找 target，返回下标或 -1。默认无重复值；重复值版本需要额外处理。

**推导**：二分时至少有一半有序。判断左半有序后，若 target 在该半的数值范围里就保留，否则排除；右半同理。每步都保证若答案存在，就仍在保留区间。

```python
def search_rotated(nums: list[int], target: int) -> int:
    left, right = 0, len(nums) - 1
    while left <= right:
        middle = (left + right) // 2
        if nums[middle] == target:
            return middle
        if nums[left] <= nums[middle]:
            if nums[left] <= target < nums[middle]:
                right = middle - 1
            else:
                left = middle + 1
        else:
            if nums[middle] < target <= nums[right]:
                left = middle + 1
            else:
                right = middle - 1
    return -1
```

**复杂度**：O(log n) 时间、O(1) 空间。空数组、未旋转、旋转点两侧和不存在都测。存在大量重复时可能无法判定有序半边，最坏退化为 O(n)，不能仍无条件承诺对数复杂度。

## 五、进阶链表与树形 DP

### A12：K 个一组反转链表

**题意**：每 k 个节点反转，不足 k 的最后一段保持不变；不能只交换 val。k 必须为正。

**步骤**：用 group_previous 指向本组前驱，先向后找 k 个节点确认长度；保存下一组起点 group_next；把本组反转并连接到下一组；再连接前驱并推进到旧组头，也就是新组尾。

```python
def reverse_k_group(head: ListNode | None, k: int) -> ListNode | None:
    if k <= 0:
        raise ValueError('k must be positive')
    dummy = ListNode(next_node=head)
    group_previous = dummy
    while True:
        kth = group_previous
        for _ in range(k):
            kth = kth.next
            if kth is None:
                return dummy.next
        group_next = kth.next
        previous, current = group_next, group_previous.next
        while current is not group_next:
            following = current.next
            current.next = previous
            previous = current
            current = following
        old_head = group_previous.next
        group_previous.next = kth
        group_previous = old_head
```

**复杂度**：O(n) 时间、O(1) 额外空间。`1→2→3→4→5,k=2` 得 `2→1→4→3→5`。常见错误是反转完找不到旧头、把不足 k 段也反转、或在断链前没有保存下一节点。

### A13：合并 K 个有序链表

**题意**：所有链表非递减、无环且互不共享节点，允许复用原节点。总节点数 N，链表数量 K。

**不变量**：堆里只有各条尚未耗尽链表的当前最小节点。每次取出的堆顶就是所有剩余节点中的最小值，取出后再把该链表的下一个节点放入。

```python
import heapq
from itertools import count


def merge_k_lists(lists: list[ListNode | None]) -> ListNode | None:
    serial = count()
    heap = []
    for head in lists:
        if head is not None:
            heapq.heappush(heap, (head.val, next(serial), head))
    dummy = tail = ListNode()
    while heap:
        _, _, node = heapq.heappop(heap)
        following = node.next
        tail.next = node
        tail = node
        if following is not None:
            heapq.heappush(heap, (following.val, next(serial), following))
    tail.next = None
    return dummy.next
```

序号避免数值相同时继续比较 ListNode 对象导致 TypeError。O(N log(K+1)) 时间，堆 O(K) 空间。空列表与全 None 返回 None。若要求不修改输入，需要新建输出节点，空间口径随之改变。

**追问**：分治两两合并也是 O(N log K) 思路；逐条把越来越长的结果与下一条合并，分布不好时更慢，应具体分析而不是看到“合并”就认为一样。

### A14：二叉树最大路径和

**题意**：路径可从任意节点开始到任意节点结束，相邻节点通过父子边连接，同一节点不能重复；非空树路径至少包含一个节点。空树本文返回 0。

**关键区分**：给父节点返回的必须是单边最大贡献，因为父节点还要把它接成一条路径；全局答案可以在当前节点连接左右两边。负贡献可以舍弃，但当前节点不能全部不选，因此全负树答案是最大的负节点值，而不是 0。

```python
def max_path_sum(root: TreeNode | None) -> int:
    if root is None:
        return 0
    best = float('-inf')

    def gain(node):
        nonlocal best
        if node is None:
            return 0
        left = max(0, gain(node.left))
        right = max(0, gain(node.right))
        best = max(best, node.val + left + right)
        return node.val + max(left, right)

    gain(root)
    return best
```

**复杂度**：O(n) 时间、O(h) 栈。`-10,9,20,None,None,15,7` 得 42；只有 -3 得 -3。不能把左右都返回给父节点，否则会得到分叉而非一条路径。

## 六、动态规划与数据流

### A15：最长公共子序列 LCS

**题意**：子序列可以不连续，子串必须连续。求两个字符串共同子序列的最大长度。

**状态与转移**：`dp[i][j]` 是 text1 前 i 个字符与 text2 前 j 个字符的 LCS 长度。末尾相等则接在更短前缀之后加 1；否则舍弃其中一边的末尾，取两种可能的最大值。

下面只保留上一行与当前行，把空间压到较短字符串长度。这样方便解释，也不容易把一维原地更新的左上角值覆盖掉。

```python
def lcs_length(text1: str, text2: str) -> int:
    if len(text1) < len(text2):
        text1, text2 = text2, text1
    previous = [0] * (len(text2) + 1)
    for char1 in text1:
        current = [0] * (len(text2) + 1)
        for j, char2 in enumerate(text2, 1):
            if char1 == char2:
                current[j] = previous[j - 1] + 1
            else:
                current[j] = max(previous[j], current[j - 1])
        previous = current
    return previous[-1]
```

**复杂度**：O(mn) 时间、O(min(m,n)) 空间。`abcde,ace -> 3`；一个为空得 0。要输出实际序列通常需要恢复路径或另做分治，不是这个长度实现直接支持。

### A16：单词拆分

**题意**：字符串能否被字典单词拼接而成，单词可重复使用。空字符串视为可拆分；字典中的空单词不影响结果。

**状态**：reachable[end] 表示前 end 个字符能否完整拆分。枚举最后一个单词长度，只要前面的前缀可达且这一段在字典里，就可达。它不是只看字符串开头的一次贪心，因为局部匹配可能通向死路。

```python
def word_break(text: str, words: list[str]) -> bool:
    dictionary = {word for word in words if word}
    lengths = sorted({len(word) for word in dictionary})
    reachable = [False] * (len(text) + 1)
    reachable[0] = True
    for end in range(1, len(text) + 1):
        for size in lengths:
            if size > end:
                break
            if reachable[end - size] and text[end - size:end] in dictionary:
                reachable[end] = True
                break
    return reachable[-1]
```

**复杂度**：设不同词长 D、最大词长 L，Python 切片与计算字符串哈希都可能花 O(L)，因此可给 O(nDL) 的查询上界，另计字典构建。不要把字符串切片一律视为 O(1) 后轻率报告 O(nD)。状态数组 O(n)，字典存储另计。

**自测**：`leetcode,[leet,code] -> True`；`catsandog,[cats,dog,sand,and,cat] -> False`。若要输出所有拆分，结果数可能很大，需要另外分析输出复杂度。

### A17：数据流中位数

**题意**：不断插入数字，随时返回中位数。不能每次都重新排序全部元素。

**两个不变量**：small 是保存较小一半的最大堆，large 是较大一半的最小堆；small 的大小等于 large 或多 1。所有 small 中元素都不大于 large 中元素。Python 用负号模拟最大堆。

```python
import heapq


class MedianFinder:
    def __init__(self):
        self.small: list[int] = []
        self.large: list[int] = []

    def add_num(self, value: int) -> None:
        if not self.small or value <= -self.small[0]:
            heapq.heappush(self.small, -value)
        else:
            heapq.heappush(self.large, value)
        if len(self.small) > len(self.large) + 1:
            heapq.heappush(self.large, -heapq.heappop(self.small))
        elif len(self.large) > len(self.small):
            heapq.heappush(self.small, -heapq.heappop(self.large))

    def find_median(self) -> float:
        if not self.small:
            raise ValueError('no values')
        if len(self.small) > len(self.large):
            return float(-self.small[0])
        return (-self.small[0] + self.large[0]) / 2
```

**复杂度**：插入 O(log n)，查询 O(1)，存储 O(n)。依次加入 1、2 时中位数 1.5，再加 3 得 2。若要求删除旧值形成滑动中位数，需要额外删除/延迟删除机制，不能直接复用两个堆就结束。

### A18：全排列与子集，包含重复输入

**全排列**：在每个位置选一个还未使用的下标。排序后，若相同值的前一个副本在本层路径中尚未使用，则跳过当前副本，避免生成相同值排列。

```python
def unique_permutations(nums: list[int]) -> list[list[int]]:
    values = sorted(nums)
    used = [False] * len(values)
    path: list[int] = []
    answer: list[list[int]] = []

    def search():
        if len(path) == len(values):
            answer.append(path.copy())
            return
        for i, value in enumerate(values):
            if used[i]:
                continue
            if i > 0 and value == values[i - 1] and not used[i - 1]:
                continue
            used[i] = True
            path.append(value)
            search()
            path.pop()
            used[i] = False

    search()
    return answer
```

无重复时输出 n! 个结果，至少 O(n×n!) 的输出时间和存储；递归与路径 O(n)。不能只说“回溯 O(n)”而忽略输出。

**子集**：每个节点本身就是一个子集；递归只选择当前位置之后的元素，确保不会排列同一子集。同层跳过相同值，而不是把整棵树中的重复值全部禁掉。

```python
def unique_subsets(nums: list[int]) -> list[list[int]]:
    values = sorted(nums)
    path: list[int] = []
    answer: list[list[int]] = []

    def search(start: int):
        answer.append(path.copy())
        for i in range(start, len(values)):
            if i > start and values[i] == values[i - 1]:
                continue
            path.append(values[i])
            search(i + 1)
            path.pop()

    search(0)
    return answer
```

无重复时共 2^n 个子集，复制输出的时间和空间为 O(n×2^n) 上界。`[1,1,2]` 的排列为 3 个、不同子集为 6 个。空输入两者均返回 `[[]]`，表示一个空排列/空子集，而不是没有结果。

## 七、数据结构与扩展题

### A19：并查集与连通分量

**适用**：动态合并集合、判断无向连通性，不直接解决有向图可达、最短路或随意删除边。

**结构**：每个节点指向父节点，根代表集合；find 做路径压缩，union 把小树接到大树，避免退化。components 仅在真正合并两个不同集合时减 1。

```python
class DisjointSet:
    def __init__(self, n: int):
        if n < 0:
            raise ValueError('n must be non-negative')
        self.parent = list(range(n))
        self.size = [1] * n
        self.components = n

    def find(self, node: int) -> int:
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def union(self, a: int, b: int) -> bool:
        root_a, root_b = self.find(a), self.find(b)
        if root_a == root_b:
            return False
        if self.size[root_a] < self.size[root_b]:
            root_a, root_b = root_b, root_a
        self.parent[root_b] = root_a
        self.size[root_a] += self.size[root_b]
        self.components -= 1
        return True

    def connected(self, a: int, b: int) -> bool:
        return self.find(a) == self.find(b)
```

**复杂度**：初始化 O(n)；路径压缩加按大小合并，操作摊还近似 O(α(n))，不是严格每次 O(1)；空间 O(n)。本实现约定节点 ID 在 `[0,n)`，生产接口应做输入检查，尤其 Python 负下标会静默访问末尾。

**自测**：n=4，合并 0/1 与 1/2 后 components=2；重复 union(0,2) 返回 False 且计数不变。用于无向图判环时，自环和重复边的业务定义也需确认。

### A20：编辑距离

**题意**：把一个字符串变成另一个，允许插入、删除、替换，每次代价 1。不是“仅删除的距离”，也不是 LCS。

**状态**：前 i、j 个字符之间的最少操作。末尾相同直接继承左上角；否则考虑删掉第一个串末尾、插入目标字符、替换末尾三种操作，取最小再加 1。初始化空串到长度 j 需要 j 次插入。

```python
def edit_distance(source: str, target: str) -> int:
    if len(source) < len(target):
        source, target = target, source
    previous = list(range(len(target) + 1))
    for i, char1 in enumerate(source, 1):
        current = [i] + [0] * len(target)
        for j, char2 in enumerate(target, 1):
            if char1 == char2:
                current[j] = previous[j - 1]
            else:
                current[j] = 1 + min(previous[j], current[j - 1], previous[j - 1])
        previous = current
    return previous[-1]
```

**复杂度**：O(mn) 时间、O(min(m,n)) 空间。`horse,ros -> 3`，`'',abc -> 3`，相同字符串为 0。交换 source 与 target 合法是因为当前等代价操作模型对称；如果插入、删除的代价不同，就不能不加分析地交换。

### A21：最短路径，什么时候 BFS，什么时候 Dijkstra？

**先区分题型**：所有边等权时 BFS 按层扩展即可；非负权一般可用 Dijkstra；存在负权时其贪心前提可能被破坏，要考虑其他算法并检查负环。不要看到“最短”就固定套一个模板。

下面实现有向图的 Dijkstra，节点编号 `[0,n)`，权重为非负整数。dist 为已发现的最短上界；堆中同一节点可以有旧条目，弹出时跳过已经落后的距离。

```python
import heapq


def dijkstra(n: int, edges: list[tuple[int, int, int]], start: int):
    if n <= 0 or not 0 <= start < n:
        raise ValueError('invalid graph or start')
    graph: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for source, target, weight in edges:
        if not 0 <= source < n or not 0 <= target < n or weight < 0:
            raise ValueError('invalid edge')
        graph[source].append((target, weight))
    distances = [float('inf')] * n
    distances[start] = 0
    heap = [(0, start)]
    while heap:
        distance, node = heapq.heappop(heap)
        if distance != distances[node]:
            continue
        for following, weight in graph[node]:
            candidate = distance + weight
            if candidate < distances[following]:
                distances[following] = candidate
                heapq.heappush(heap, (candidate, following))
    return distances
```

**正确性核心**：非负权保证取出的当前最小有效距离，不会在未来通过更远节点绕回来变得更小。不是“用了小根堆”本身保证正确。

**复杂度**：本实现允许堆保留旧项，堆可能 O(E)，给出 O((V+E)log(V+E+2)) 的保守上界与 O(V+E) 空间；简单图常见表达为 O((V+E)log V)。不可达返回 inf。若是无向图，需要显式加入反向边。

**追问：怎么输出路径？** 只在距离改善时记录 predecessor，结束后从目标反向恢复；不可达不能按缺省前驱伪造路径。

### A22：LFU 缓存，频次相同时按 LRU 淘汰

**题意**：get 和 put 都希望期望 O(1)；淘汰访问频次最小的键，同频次淘汰最久未使用。已有键 put 视为一次使用；capacity=0 不存储。

**结构与不变量**：

- data：key -> (value, frequency)，O(1) 定位键。
- buckets：frequency -> OrderedDict，按时间从旧到新排列同频次键。
- minimum：当前最小频次。新键频次为 1，使用一次从 f 桶移到 f+1 桶。

当一个 minimum 桶因访问变空时，minimum 可以变为 f+1，因为刚被访问的键一定在那里。新键插入后直接设为 1。没有必要每次排序所有频次。

```python
from collections import OrderedDict


class LFUCache:
    def __init__(self, capacity: int):
        if capacity < 0:
            raise ValueError('capacity must be non-negative')
        self.capacity = capacity
        self.minimum = 0
        self.data: dict[int, tuple[int, int]] = {}
        self.buckets: dict[int, OrderedDict] = {}

    def _touch(self, key: int) -> int:
        value, frequency = self.data[key]
        bucket = self.buckets[frequency]
        del bucket[key]
        if not bucket:
            del self.buckets[frequency]
            if self.minimum == frequency:
                self.minimum = frequency + 1
        self.data[key] = (value, frequency + 1)
        self.buckets.setdefault(frequency + 1, OrderedDict())[key] = None
        return value

    def get(self, key: int) -> int:
        if key not in self.data:
            return -1
        return self._touch(key)

    def put(self, key: int, value: int) -> None:
        if self.capacity == 0:
            return
        if key in self.data:
            _, frequency = self.data[key]
            self.data[key] = (value, frequency)
            self._touch(key)
            return
        if len(self.data) == self.capacity:
            bucket = self.buckets[self.minimum]
            old_key, _ = bucket.popitem(last=False)
            del self.data[old_key]
            if not bucket:
                del self.buckets[self.minimum]
        self.data[key] = (value, 1)
        self.buckets.setdefault(1, OrderedDict())[key] = None
        self.minimum = 1
```

**复杂度**：常规哈希与固定宽度计数假设下 get/put 期望 O(1)，存储 O(capacity)。OrderedDict 在这里代表频次桶里的链式有序结构；若面试要求从零实现双向链表，需要说明并替换桶内结构，不能声称已经手写全部底层。

**例子**：容量 2，put(1,1)、put(2,2)、get(1)，频次分别为 2 和 1；put(3,3) 淘汰 2。若随后 get(3)，1 与 3 同频，但 1 更久未使用；下一次插入应淘汰 1。

**追问：LFU 一定比 LRU 好吗？** 不是，历史热点可能长时间占据缓存，对场景变化不敏感；实际策略可能做衰减、采样或混合。这里是算法语义，不等于 Redis 所有淘汰策略的实际精确实现。

## 八、把代码转成面试可说清楚的答案

### 8.1 每题都要回答的六件事

1. 哪些输入假设成立：有无重复、是否有环、节点是否一定存在、是否允许改输入。
2. 暴力方案是什么，重复工作在哪里。
3. 维护什么不变量，为什么每一步不会排除正确答案。
4. 边界怎么处理，空输入与非法参数有什么区别。
5. 时间、额外空间和输出空间分别怎么算，是否包含 Python 切片与复制。
6. 变式改变了哪项前提，原算法为什么还能用或不能用。

### 8.2 三组计时练习

**组一，基础必守**：有效括号 8 分钟、合并链表 12 分钟、股票 8 分钟，再口述两个反例。不要为了计时跳过澄清和自测。

**组二，中等主线**：三数之和 20 分钟、窗口最大值 20 分钟、LCA 20 分钟。重点看去重、索引过期与节点缺失假设。

**组三，项目关联**：拓扑排序 20 分钟、LRU 25 分钟、有界并发设计口述 10 分钟。后者需要能解释取消、关闭和副作用，不只是写出 goroutine。

### 8.3 本题库暂不替代的训练

本文的“样例可运行”不等于你能现场独立完成，也不等于实现经过形式化验证。对极大输入、递归深度、整数溢出、线程安全和对抗性哈希等工程边界，需要按题目约束继续分析。能清楚指出边界，比在答案里反复声称“绝对正确”更有价值。
