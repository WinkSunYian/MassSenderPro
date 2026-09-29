import time
import random
import pyautogui

from services.SkipKeywordConfig import DEFAULT_KEYWORDS
from services.WeWorkAutoService import WeWorkAutoService
from services.RosterService import RosterService

# 单个用户的处理结果（与 view.enums.cell_status.CellStatus.value 对齐）
SUCCESS = "success"
FAILED = "failed"
SKIPPED = "skipped"
# 中途终止时当前行保留「待发」状态
STOPPED = "pending"


class BatchSendManager:
    def __init__(
        self,
        helper: WeWorkAutoService,
        roster_service: RosterService,
        on_row_start=None,
        on_row_result=None,
        skip_keywords=None,
    ):
        self.helper = helper
        self.roster_service = roster_service
        # 逐行进度回调：on_row_start(row) / on_row_result(row, status, info)
        self.on_row_start = on_row_start
        self.on_row_result = on_row_result
        # 备注包含任一关键字则跳过（configs/skip_keywords.txt，不传用默认值）
        self.skip_keywords = (
            list(skip_keywords) if skip_keywords is not None else list(DEFAULT_KEYWORDS)
        )
        self.failed_roster = []
        self.skipped = {}

    def run_tasks(self, roster_items, rows=None, interval_range=(0.4, 0.5), max_retries=2):
        total = len(roster_items)
        # rows[i] 是 roster_items[i] 在表格中的行号（不传则按顺序对应）
        row_of = list(rows) if rows is not None else list(range(total))
        print(f"=== 开始执行群发任务，名册包含 {total} 个目标 ===")
        try:
            for index, item in enumerate(roster_items, start=1):
                row = row_of[index - 1]
                user_id = item.user_id
                payload = item.payload
                self._emit_start(row)
                print(f"\n[{index}/{total}] 正在处理用户: {user_id}")

                # (状态, 信息, 是否可重试)：只有可重试的失败才继续下一轮
                status, info, retryable = FAILED, "", True
                for attempt in range(1, max_retries + 1):
                    try:
                        status, info, retryable = self._send_single_user(user_id, payload)
                        if status != FAILED:
                            print(f"[{index}/{total}] 用户 {user_id} 处理完毕")
                            break
                        if not retryable:
                            # 确定性失败（姓名不符 / 未定位 / 内容为空）：重试无意义
                            break
                        print(f"[{index}/{total}] 查找失败，第 {attempt} 次重试...")
                        sleep_sec = 1
                        print(f"[等待] {sleep_sec:.2f} 秒后继续查找")
                        time.sleep(sleep_sec)
                    except InterruptedError as e:
                        # 任务被终止（F12 / 活动窗口切换）：标记当前行后向上抛
                        self._emit_result(row, STOPPED, f"已终止：{e}")
                        raise
                    except pyautogui.FailSafeException:
                        self.helper.stop_event = True
                        self._emit_result(row, STOPPED, "已终止：触发鼠标安全角")
                        raise InterruptedError("触发鼠标安全角，任务终止")
                    except Exception as e:
                        status, info, retryable = FAILED, f"失败：发送异常（{e}）", True
                        print(f"[{index}/{total}] 发送出现异常 (第 {attempt} 次): {e}")

                if status == FAILED:
                    if not info:
                        info = f"失败：重试 {max_retries} 次未成功"
                    print(f"[{index}/{total}] 用户 {user_id} 最终处理失败")
                    self.failed_roster.append(user_id)
                self._emit_result(row, status, info)

                if index < total:
                    sleep_sec = random.uniform(*interval_range)
                    print(f"[等待] {sleep_sec:.2f} 秒后继续处理下一个...")
                    time.sleep(sleep_sec)

            print("\n=== 名册内所有任务执行完毕 ===")
            print(
                f"[信息] {len(roster_items)}(总用户) = "
                f"{len(roster_items) - len(self.failed_roster) - self._total_skipped()}(成功) + "
                f"{len(self.failed_roster)}(失败) + {self._total_skipped()}(跳过)"
            )
            self._print_skip_summary()
        finally:
            if self.failed_roster:
                print(f"[异常] 处理失败用户列表 {self.failed_roster}")
                if self.roster_service is not None:
                    self.roster_service.save_failed_roster(self.failed_roster)

    def _emit_start(self, row):
        if self.on_row_start:
            self.on_row_start(row)

    def _emit_result(self, row, status, info):
        if self.on_row_result:
            self.on_row_result(row, status, info)

    def _total_skipped(self):
        return sum(len(v) for v in self.skipped.values())

    def _record_skip(self, keyword, user_id):
        self.skipped.setdefault(keyword, []).append(user_id)

    def _print_skip_summary(self):
        if not self.skipped:
            return
        print("\n=== 跳过统计 ===")
        for keyword, users in self.skipped.items():
            print(f"[{keyword}] 共 {len(users)} 人: {users}")

    def _send_single_user(self, user_id, payload):
        """处理单个用户，返回 (状态, 信息, 是否可重试)。

        口径：只有「备注包含关键字」算跳过，其余没发出去的一律算失败；
        失败里只有「没打开聊天窗口 / 发送异常」才值得重试。
        """
        if not payload:
            return FAILED, "失败：内容为空", False

        if not self.helper.search_and_open_user(user_id):
            return FAILED, "失败：未打开聊天窗口", True

        remark_title = self.helper.get_standalone_chat_title(timeout=3.0)
        print(f"[备注] 用户 [{user_id}] 的备注为 ['{remark_title}']")

        if not remark_title or "全局搜索" in remark_title:
            print(
                f"[拦截] 未搜索到 [{user_id}]（触发全局搜索或未定位到窗口标题: '{remark_title}'），跳过发送。"
            )
            self.helper.close_standalone_window()
            return FAILED, f"失败：未定位到聊天窗口（{remark_title or '无标题'}）", False

        for keyword in self.skip_keywords:
            if keyword in remark_title:
                print(f"[拦截] 用户 [{user_id}] 备注包含'{keyword}'，跳过发送。")
                self.helper.close_standalone_window()
                self._record_skip(keyword, user_id)
                return SKIPPED, f"备注含关键词：{keyword}", False

        if user_id not in remark_title:
            print(f"[拦截] 用户 [{user_id}] 备注和名字不符，按失败处理。")
            self.helper.close_standalone_window()
            return FAILED, f"失败：姓名与备注不符（{remark_title}）", False

        print(
            f"[通过] 用户 [{user_id}] 备注校验无误 ['{remark_title}']，开始发送内容..."
        )
        for content in payload:
            content_type = content.get("type")
            data = content.get("data")
            if content_type == "text":
                self.helper.send_text(data)
            elif content_type == "file":
                self.helper.send_file(data)

        self.helper.close_standalone_window()
        return SUCCESS, f"发送成功：{remark_title}", False