import os
import time
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from selenium.webdriver.common.action_chains import ActionChains

from browser import launch_edge, attach_edge
from collector import (
    collect_current_page,
    find_numeric_next,
    find_arrow_next,
    result_signature,
    signature_changed,
)
from exporter import export_simple
from config import (
    MAX_SCROLLS,
    MAX_NO_NEW_ROUNDS,
    SCROLL_WAIT_SECONDS,
    MAX_RESULTS,
    PAGE_WAIT_SECONDS,
)

MAX_PAGES = 20
NAVIGATION_CONFIRM_SECONDS = 6.0


def app_data_dir():
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    p = base / "AntiPiracyFinder"
    p.mkdir(parents=True, exist_ok=True)
    return p


def output_dir():
    p = Path.home() / "Documents" / "AntiPiracyFinder_Results"
    p.mkdir(parents=True, exist_ok=True)
    return p


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AntiPiracy Finder v0.1.0-beta - 作者盗文搜索记录工具")
        self.geometry("800x690")
        self.minsize(730, 610)
        self.driver = None
        self._build()

    def _build(self):
        pad = {"padx": 12, "pady": 6}

        ttk.Label(
            self,
            text="AntiPiracy Finder  v0.1.0-beta",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(16, 2))

        ttk.Label(
            self,
            text="帮助作者整理公开搜索结果中的疑似盗文线索；程序不会自动打开候选网站。",
        ).pack(pady=(0, 10))

        info = ttk.LabelFrame(self, text="1. 作品信息")
        info.pack(fill="x", padx=18, pady=6)

        ttk.Label(info, text="书名：").grid(
            row=0, column=0, sticky="e", **pad
        )
        self.book = ttk.Entry(info, width=55)
        self.book.grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(info, text="作者：").grid(
            row=1, column=0, sticky="e", **pad
        )
        self.author = ttk.Entry(info, width=55)
        self.author.grid(row=1, column=1, sticky="ew", **pad)

        info.columnconfigure(1, weight=1)

        edge = ttk.LabelFrame(self, text="2. Edge")
        edge.pack(fill="x", padx=18, pady=6)

        ttk.Label(
            edge,
            text=(
                "点击按钮启动本工具专用 Edge。"
                "请在该 Edge 中手动使用 Google、Bing、百度或 Quark 搜索。"
            ),
        ).pack(anchor="w", padx=12, pady=(8, 3))

        ttk.Button(
            edge,
            text="启动 / 连接 Edge",
            command=self.start_edge,
        ).pack(anchor="w", padx=12, pady=(3, 10))

        action = ttk.LabelFrame(self, text="3. 采集")
        action.pack(fill="x", padx=18, pady=6)

        self.collect_btn = ttk.Button(
            action,
            text="采集当前搜索并自动导出 Excel",
            command=self.start_collect,
        )
        self.collect_btn.pack(side="left", padx=12, pady=12)

        ttk.Button(
            action,
            text="打开结果文件夹",
            command=self.open_results,
        ).pack(side="left", padx=4, pady=12)

        note = ttk.LabelFrame(self, text="使用提示")
        note.pack(fill="x", padx=18, pady=6)

        ttk.Label(
            note,
            text=(
                "⚠ 本工具只负责记录搜索引擎公开展示的链接，不会验证目标网页。\n"
                "部分链接可能返回 403、需要验证码、已经失效或并非侵权页面，"
                "请使用者自行打开并核实。"
            ),
            justify="left",
            wraplength=730,
        ).pack(anchor="w", padx=12, pady=9)

        status = ttk.LabelFrame(self, text="本次记录")
        status.pack(fill="both", expand=True, padx=18, pady=(6, 16))

        self.status = tk.Text(
            status,
            height=13,
            wrap="word",
            state="disabled",
        )
        self.status.pack(fill="both", expand=True, padx=8, pady=8)

        self.log("请填写书名和作者，然后启动 / 连接 Edge。")
        self.log("采集失败时作品信息不会清空，可直接重试。")
        self.log("导航会自动尝试：数字页码 → 下一页/箭头 → 无限滚动。")

    def log(self, text):
        def write():
            self.status.configure(state="normal")
            self.status.insert("end", text + "\n")
            self.status.see("end")
            self.status.configure(state="disabled")

        self.after(0, write)

    def start_edge(self):
        try:
            profile = app_data_dir() / "edge_profile"
            created = launch_edge(profile)
            self.driver = attach_edge()

            if created:
                self.log("✓ 专用 Edge 已启动并连接。")
            else:
                self.log("✓ Edge 已连接。")

        except Exception as e:
            self.log(f"✗ Edge 启动/连接失败：{e}")
            messagebox.showerror("Edge 连接失败", str(e))

    def validate_inputs(self):
        book = self.book.get().strip()
        author = self.author.get().strip()

        if not book or not author:
            messagebox.showwarning(
                "缺少信息",
                "请填写书名和作者名。",
            )
            return None

        return book, author

    def start_collect(self):
        values = self.validate_inputs()
        if not values:
            return

        self.collect_btn.config(state="disabled")

        threading.Thread(
            target=self.collect_job,
            args=values,
            daemon=True,
        ).start()

    def _collect_page(self, book, author, all_rows):
        engine, query, rows = collect_current_page(
            self.driver, book, author
        )

        before = len(all_rows)

        for row in rows:
            all_rows[row["url"]] = row

        return engine, query, rows, len(all_rows) - before

    # ========================================================
    # 点击 + 确认真正发生翻页
    # ========================================================

    def _try_click_and_confirm(
        self,
        element,
        book,
        author,
        strategy_name,
    ):
        before = result_signature(
            self.driver, book, author
        )

        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView("
                "{block:'center', inline:'center'});",
                element,
            )
            time.sleep(0.35)

            # 首选正常 Selenium click
            try:
                element.click()
            except Exception:
                # 普通点击失败时，用 ActionChains 做正常鼠标点击 fallback
                ActionChains(self.driver).move_to_element(
                    element
                ).click().perform()

        except Exception as e:
            self.log(
                f"✗ {strategy_name}点击失败：{type(e).__name__}"
            )
            return False

        deadline = time.time() + NAVIGATION_CONFIRM_SECONDS

        while time.time() < deadline:
            time.sleep(0.5)

            try:
                after = result_signature(
                    self.driver, book, author
                )

                if signature_changed(before, after):
                    self.log(f"✓ {strategy_name}成功，页面已变化。")
                    time.sleep(0.6)
                    return True

            except Exception:
                pass

        self.log(
            f"✗ {strategy_name}未产生页面变化，自动尝试下一种方式。"
        )
        return False

    # ========================================================
    # 无限滚动 fallback
    # ========================================================

    def _try_scroll(self, book, author, all_rows, scroll_no):
        try:
            old_height = self.driver.execute_script(
                "return Math.max("
                "document.body.scrollHeight,"
                "document.documentElement.scrollHeight);"
            )
        except Exception:
            old_height = 0

        before_count = len(all_rows)

        self.driver.execute_script("""
            const h = Math.max(
                document.body.scrollHeight,
                document.documentElement.scrollHeight
            );
            window.scrollTo({
                top: h * 0.88,
                behavior: 'smooth'
            });
        """)

        time.sleep(SCROLL_WAIT_SECONDS)

        self.driver.execute_script(
            "window.scrollBy({"
            "top:window.innerHeight*0.8,"
            "behavior:'smooth'});"
        )

        time.sleep(0.8)

        engine, query, rows, added = self._collect_page(
            book, author, all_rows
        )

        try:
            new_height = self.driver.execute_script(
                "return Math.max("
                "document.body.scrollHeight,"
                "document.documentElement.scrollHeight);"
            )
        except Exception:
            new_height = old_height

        changed = (
            added > 0
            or len(all_rows) > before_count
            or new_height > old_height
        )

        if changed:
            self.log(
                f"✓ 无限滚动 {scroll_no}："
                f"新增 {added} 条，累计 {len(all_rows)} 条"
            )
            return True, engine, query

        self.log(
            f"✗ 无限滚动 {scroll_no} 未发现新搜索结果。"
        )
        return False, engine, query

    # ========================================================
    # 三层自适应导航
    # ========================================================

    def collect_adaptive(self, book, author):
        all_rows = {}

        engine, query, rows, added = self._collect_page(
            book, author, all_rows
        )

        self.log(f"识别搜索引擎：{engine}")
        self.log(
            f"第 1 批：识别 {len(rows)} 条，"
            f"累计 {len(all_rows)} 条"
        )

        navigation_round = 1
        scroll_round = 0
        no_new_scroll = 0

        while (
            len(all_rows) < MAX_RESULTS
            and navigation_round < MAX_PAGES
        ):
            navigation_round += 1

            # ------------------------------------------------
            # 方案 1：数字页码
            # ------------------------------------------------
            numeric, target_page = find_numeric_next(
                self.driver, engine
            )

            if numeric is not None:
                self.log(
                    f"检测到数字分页：尝试进入第 {target_page} 页。"
                )

                if self._try_click_and_confirm(
                    numeric,
                    book,
                    author,
                    f"数字页码 {target_page}",
                ):
                    engine, query, rows, added = self._collect_page(
                        book, author, all_rows
                    )

                    self.log(
                        f"第 {target_page} 页："
                        f"新增 {added} 条，"
                        f"累计 {len(all_rows)} 条"
                    )

                    no_new_scroll = 0

                    # 页面已变化，下一轮从头重新判断三种模式。
                    continue

            # ------------------------------------------------
            # 方案 2：> / → / 下一页 / Next
            # ------------------------------------------------
            arrow = find_arrow_next(
                self.driver, engine
            )

            if arrow is not None:
                self.log(
                    "尝试“下一页 / > / 箭头”分页。"
                )

                if self._try_click_and_confirm(
                    arrow,
                    book,
                    author,
                    "下一页/箭头",
                ):
                    engine, query, rows, added = self._collect_page(
                        book, author, all_rows
                    )

                    self.log(
                        f"分页后新增 {added} 条，"
                        f"累计 {len(all_rows)} 条"
                    )

                    no_new_scroll = 0
                    continue

            # ------------------------------------------------
            # 方案 3：无限滚动
            # ------------------------------------------------
            if scroll_round >= MAX_SCROLLS:
                self.log(
                    "已达到最大滚动次数，停止自动采集。"
                )
                break

            self.log(
                "没有可用分页控件，尝试无限滚动。"
            )

            scroll_round += 1

            changed, engine, query = self._try_scroll(
                book,
                author,
                all_rows,
                scroll_round,
            )

            if changed:
                no_new_scroll = 0

                # 滚动加载之后重新从“数字分页”开始检测。
                continue

            no_new_scroll += 1

            if no_new_scroll >= MAX_NO_NEW_ROUNDS:
                self.log(
                    "连续多次没有发现新结果，自动采集结束。"
                )
                break

        return engine, query, list(all_rows.values())

    def collect_job(self, book, author):
        try:
            if self.driver is None:
                self.driver = attach_edge()

            engine, query, rows = self.collect_adaptive(
                book, author
            )

            result = export_simple(
                rows,
                output_dir(),
                book,
                author,
                engine,
            )

            self.log("✓ 采集完成并已自动导出。")
            self.log(
                f"抓取去重后：{result['raw_count']} 条"
            )
            self.log(
                f"排除晋江/正版结果："
                f"{result['excluded_count']} 条"
            )
            self.log(
                f"最终导出：{result['final_count']} 条"
            )
            self.log(f"来源：{engine}")
            self.log(f"文件：{result['path'].name}")
            self.log(
                "⚠ 链接是否可访问、是否 403、"
                "是否确属盗文，需要使用者自行核实。"
            )

            def done_message():
                messagebox.showinfo(
                    "采集完成",
                    f"抓取去重后：{result['raw_count']} 条\n"
                    f"排除晋江/正版："
                    f"{result['excluded_count']} 条\n"
                    f"最终导出："
                    f"{result['final_count']} 条\n"
                    f"来源：{engine}\n\n"
                    f"文件：{result['path']}\n\n"
                    "提示：本工具仅负责收集公开搜索结果。"
                    "链接是否可访问、是否返回 403、"
                    "是否确属盗文，请自行核实。"
                )

            self.after(0, done_message)

        except Exception as e:
            self.log(
                f"✗ 本次采集失败：{e}"
            )
            self.log(
                "书名和作者信息已保留，"
                "请检查 Edge 当前页面后直接重试。"
            )

            def error_message():
                messagebox.showerror(
                    "采集失败",
                    f"{e}\n\n"
                    "书名和作者信息已保留，"
                    "不需要重新输入。",
                )

            self.after(0, error_message)

        finally:
            self.after(
                0,
                lambda: self.collect_btn.config(
                    state="normal"
                ),
            )

    def open_results(self):
        try:
            os.startfile(str(output_dir()))
        except Exception as e:
            messagebox.showerror(
                "无法打开文件夹",
                str(e),
            )


if __name__ == "__main__":
    App().mainloop()
