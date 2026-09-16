import requests
from urllib.parse import urlparse
import whois
import socket
import time
import re
import webbrowser
import pyperclip
import tkinter as tk
from tkinter import messagebox
from pathlib import Path


# ========== 全局配置 ==========
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


# ========== 修改位置：约第 15 行 - 第 45 行 ==========
# 替换 KNOWN_PROVIDER_FORMS 字典
KNOWN_PROVIDER_FORMS = {
    'cloudflare': {
        'name': 'Cloudflare (CDN)',
        'url': 'https://www.cloudflare.com/abuse/',
        'lang': 'en'
    },
    'akamai': {
        'name': 'Akamai Technologies',
        'url': 'https://www.akamai.com/legal/compliance/abuse-policy',
        'lang': 'en'
    },
    'alibaba': {
        'name': '阿里云 (Alibaba Cloud)',
        'url': 'https://netcn.console.aliyun.com/core/abuse/report',
        'lang': 'zh'
    },
    'tencent': {
        'name': '腾讯云 (Tencent Cloud)',
        'url': 'https://cloud.tencent.com/document/product/213/18252',
        'lang': 'zh'
    },
    'amazon': {
        'name': 'AWS (Amazon Host)',
        'url': 'https://aws.amazon.com/forms/aws-abuse',
        'lang': 'en'
    },
    'namecheap': {
        'name': 'Namecheap (域名/主机)',
        'url': 'https://www.namecheap.com/support/knowledgebase/article.aspx/9196/',
        'lang': 'en'
    },
    'godaddy': {
        'name': 'GoDaddy (域名/主机)',
        'url': 'https://support.godaddy.com/abuse-report',
        'lang': 'en'
    }
}


# 常见骨干网运营商特征词
TELECOM_CARRIERS = ['china unicom', 'chinanet', 'china telecom', 'china mobile', 'cmnet', 'chinatelecom']
# ==============================


def get_final_url(url):
    """追溯 301/302 重定向拿到真实落地页"""
    try:
        response = requests.head(url, headers=HEADERS, timeout=5, allow_redirects=True)
        return response.url
    except Exception:
        try:
            response = requests.get(url, headers=HEADERS, timeout=5, allow_redirects=True, stream=True)
            return response.url
        except Exception:
            return url


def get_registrar(domain):
    """查询域名注册商【修复：None/列表判断异常】"""
    try:
        w = whois.whois(domain)
        registrar = w.registrar
        if isinstance(registrar, list) and len(registrar) > 0:
            return str(registrar[0])
        elif registrar is not None:
            return str(registrar)
        else:
            return "未知注册商"
    except Exception:
        return "查询失败"


def get_hosting_provider(domain):
    """通过 IP/ASN 查询 CDN 与托管服务商【修复DNS解析与ip-api返回处理】"""
    try:
        ip = socket.gethostbyname(domain)
        api_url = f"http://ip-api.com/json/{ip}?fields=status,isp,org,as"
        res = requests.get(api_url, timeout=5).json()
        
        if res.get("status") == "success":
            provider = res.get("org") or res.get("isp") or res.get("as") or "未知服务商"
            return str(provider), ip
        else:
            return "IP查询无结果", ip
    except socket.gaierror:
        return "域名DNS解析失败", "0.0.0.0"
    except Exception:
        return "解析失败", "0.0.0.0"


def analyze_provider_status(hosting_string):
    """分析服务商类型，输出针对性处理建议"""
    h_lower = str(hosting_string).lower()

    # 1. 优先匹配主流已知服务商
    for key, info in KNOWN_PROVIDER_FORMS.items():
        if key in h_lower:
            return info['name'], info['url'], "【标准投诉】可直接通过官方 Abuse 页面提交 DMCA 申请。"

    # 2. 匹配三大运营商骨干网
    for carrier in TELECOM_CARRIERS:
        if carrier in h_lower:
            advice = (
                "【这个服务商通常不能直接处理版权投诉】\n"
                "不用担心，你还可以尝试下面的方法：\n\n"
                "1. 【让百度不再显示这个盗文链接】\n"
                "点击下方“去百度版权平台”，向百度提交侵权链接。"
                "如果投诉成功，这个盗文页面可能不再出现在百度搜索结果中。\n\n"
                "2. 【向这个网站的域名注册公司投诉】\n"
                "报告里的“域名注册商”就是负责管理这个网站域名的公司。"
                "你可以搜索这家公司的官网，在官网寻找 Abuse、Report Abuse、"
                "Copyright 或 DMCA 等投诉入口，然后提交侵权链接和版权证明。\n\n"
                "3. 【如果是中国大陆网站，可检查网站备案】\n"
                "点击下方“去工信部 ICP”，查询这个网站是否有正规的 ICP 备案。"
                "如果发现备案信息存在明显问题，再根据官方页面提供的渠道进行反馈。"
            )
            return hosting_string.strip(), None, advice

    # 3. 未知或无公开表单的海外/国内小机房
    advice = (
        "【暂时没有找到这个服务商的直接投诉入口】\n"
        "这不代表无法处理，可以继续尝试下面的方法：\n\n"
        "1. 【先处理搜索结果】\n"
        "如果盗文链接出现在百度或 Google 搜索结果中，可以先向搜索引擎提交版权投诉。"
        "投诉成功后，即使盗文网站暂时还存在，其他读者也会更难通过搜索找到它。\n\n"
        "2. 【再找域名注册公司】\n"
        "查看报告中的“域名注册商”。这是负责管理该网站域名的公司。"
        "进入这家公司的官方网站，寻找 Abuse、Copyright、DMCA 或 Report Abuse "
        "等字样的投诉页面，并提交侵权链接和版权证明。\n\n"
        "3. 【不知道怎么操作也没关系】\n"
        "可以先保存本工具生成的 Excel 报告。报告已经整理好了网站域名、"
        "注册商、服务商和侵权链接，可以作为后续投诉时的线索。"
    )
    return hosting_string.strip(), None, advice


def extract_urls(input_file):
    """从 xlsx/xls/txt 提取链接；xlsx 使用 openpyxl，不再依赖 pandas。"""
    urls = []

    if input_file.lower().endswith(".xlsx"):
        from openpyxl import load_workbook
        wb = load_workbook(input_file, read_only=True, data_only=True)
        try:
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    for val in row:
                        if val is not None:
                            urls.extend(re.findall(r'https?://[^\s]+', str(val)))
        finally:
            wb.close()

    elif input_file.lower().endswith(".xls"):
        raise ValueError(
            "为减小 EXE 体积，精简版不再内置旧版 .xls 读取组件。"
            "请先用 Excel/WPS 将文件另存为 .xlsx 后再上传。"
        )

    else:
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(input_file, "r", encoding="gbk", errors="ignore") as f:
                content = f.read()
        urls = re.findall(r'https?://[^\s]+', content)

    return list(dict.fromkeys(urls))


# ========== 修改位置：约第 105 行 - 第 135 行 ==========
# 替换整个 generate_dmca_text 函数
def generate_dmca_text(author_name, novel_title, original_url, infringing_urls, lang='en'):
    """根据目标平台语言（zh/en）自动生成对应语种的侵权通知信件"""
    urls_str = "\n".join([f"- {u}" for u in infringing_urls])
    current_date = time.strftime('%Y-%m-%d')
    
    if lang == 'zh':
        return f"""【版权侵权下架通知函】

致 相关平台/服务商法务部门：

我是著作权人【{author_name}】，现对贵方网络服务中传输/托管的未授权侵权内容提出正式下架申请。

一、 正版版权信息：
- 作品名称：《{novel_title}》
- 著作权人：{author_name}
- 官方正版发布网址：{original_url}

二、 侵权网址列表：
{urls_str}

三、 法律声明：
1. 本人郑重声明，上述侵权网址所展示的内容未经著作权人或许可人的授权，涉嫌严重侵犯本人著作权。
2. 本通知书中的信息均真实、准确。本人愿承担因声明不实所引发的一切法律责任。

请贵方收到本通知后，依法尽速断开上述侵权链接或下架相关内容。

申诉人电子签名：{author_name}
日期：{current_date}
"""
    else:
        return f"""DMCA Copyright Takedown Notice

Copyright Owner: {author_name}
Work Title: "{novel_title}"
Official Original URL: {original_url}

Infringing URLs:
{urls_str}

Statements:
- I have a good faith belief that the use of the material in the manner complained of is not authorized by the copyright owner, its agent, or the law.
- The information in this notification is accurate, and under penalty of perjury, I declare that I am the copyright owner of the work described above.

Digital Signature: {author_name}
Date: {current_date}
"""


def export_results_excel(results, output_excel):
    """使用 openpyxl 直接写出报告，避免 pandas/numpy 进入 EXE。"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "服务商分析报告"

    headers = [
        "原始链接", "跳转后真实链接", "解析域名", "域名注册商",
        "服务商/CDN", "官方投诉页面", "建议处理路径", "IP 地址"
    ]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(vertical="top")

    for item in results:
        ws.append([item.get(h, "") for h in headers])

    widths = {
        1: 42, 2: 42, 3: 25, 4: 25,
        5: 32, 6: 42, 7: 70, 8: 18
    }
    for idx, width in widths.items():
        ws.column_dimensions[get_column_letter(idx)].width = width

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(output_excel)


def analyze_urls(input_file, author_name, novel_title, original_url, progress_callback=None):
    """执行原有运营商识别流程。【修复域名截取bug】"""
    urls = extract_urls(input_file)
    if not urls:
        raise ValueError("上传的文件中没有找到有效网址。")
    results, provider_summary = [], {}
    for i, raw_url in enumerate(urls, 1):
        if progress_callback:
            progress_callback(i, len(urls), raw_url)
        final_url = get_final_url(raw_url)
        domain = urlparse(final_url).netloc.lower().split(':')[0]
        main_domain = domain  # 修复com.cn类域名错误截取二级域名问题
        registrar = get_registrar(main_domain)
        hosting_provider, ip = get_hosting_provider(domain)
        display_name, complaint_url, advice = analyze_provider_status(hosting_provider)
        provider_summary.setdefault(display_name, {"url": complaint_url, "advice": advice, "urls": []})
        provider_summary[display_name]["urls"].append(final_url)
        results.append({
            "原始链接": raw_url, "跳转后真实链接": final_url, "解析域名": domain,
            "域名注册商": registrar, "服务商/CDN": hosting_provider,
            "官方投诉页面": complaint_url if complaint_url else "无直接入口",
            "建议处理路径": advice.replace("\n", " | "), "IP 地址": ip
        })
        time.sleep(0.5)
    return urls, results, provider_summary


class AntiPiracyReporterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("盗文服务商分析与举报助手 v0.1.4")
        self.geometry("980x720")
        self.minsize(860, 620)
        self.input_file = tk.StringVar()
        self.author_name = tk.StringVar()
        self.novel_title = tk.StringVar()
        self.original_url = tk.StringVar(value="https://www.jjwxc.net/")
        self.provider_summary, self.results = {}, []
        self.imported_urls = []
        self.output_excel = None
        self.busy = False
        self.protocol("WM_DELETE_WINDOW", self.confirm_close)
        self.build_ui()

    def build_ui(self):
        from tkinter import filedialog
        header = tk.Frame(self); header.pack(fill="x", padx=20, pady=(18,8))
        tk.Label(header, text="盗文服务商分析与举报助手", font=("微软雅黑",18,"bold")).pack(anchor="w")
        tk.Label(header, text="上传上一个工具导出的链接 → 识别运营商/CDN → 生成报告 → 打开举报入口",
                 font=("微软雅黑",9), fg="#666666").pack(anchor="w", pady=(3,0))

        box = tk.LabelFrame(self, text=" 1. 上传盗文链接文件 ", padx=12, pady=10)
        box.pack(fill="x", padx=20, pady=8)
        tk.Entry(box, textvariable=self.input_file, state="readonly", font=("微软雅黑",9)).pack(
            side="left", fill="x", expand=True, padx=(0,8))
        def choose():
            p = filedialog.askopenfilename(
                title="选择链接文件",
                filetypes=[
                    ("支持的文件", "*.xlsx *.txt"),
                    ("Excel", "*.xlsx"),
                    ("文本", "*.txt")
                ]
            )
            if not p:
                return
            self.input_file.set(p)
            self.import_selected_file(p)
        tk.Button(box, text="打开 / 上传", command=choose, width=12).pack(side="right")

        info = tk.LabelFrame(self, text=" 2. 版权信息 ", padx=12, pady=10)
        info.pack(fill="x", padx=20, pady=8); info.columnconfigure(1, weight=1)
        for r,(lab,var) in enumerate([("作者笔名：",self.author_name),("小说名称：",self.novel_title),("正版链接：",self.original_url)]):
            tk.Label(info,text=lab).grid(row=r,column=0,sticky="e",padx=(0,8),pady=5)
            tk.Entry(info,textvariable=var).grid(row=r,column=1,sticky="ew",pady=5)

        actions=tk.Frame(self); actions.pack(fill="x",padx=20,pady=8)
        self.analyze_btn=tk.Button(actions,text="开始识别运营商并生成报告",command=self.start_analysis,
                                   font=("微软雅黑",10,"bold"),padx=15,pady=7)
        self.analyze_btn.pack(side="left")
        self.report_btn=tk.Button(actions,text="打开生成的报告",command=self.open_report,state="disabled",padx=12,pady=7)
        self.report_btn.pack(side="left",padx=8)
        self.progress=tk.Label(actions,text="等待上传文件",fg="#555555"); self.progress.pack(side="right")

        content=tk.Frame(self); content.pack(fill="both",expand=True,padx=20,pady=(4,12))
        canvas=tk.Canvas(content,highlightthickness=0)
        sb=tk.Scrollbar(content,orient="vertical",command=canvas.yview)
        self.cards=tk.Frame(canvas)
        self.cards.bind("<Configure>",lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0),window=self.cards,anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        
        # ==========【修复滚轮函数缩进，放到build_ui内部】==========
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        self.cards.bind("<Enter>", _bind_mousewheel)
        self.cards.bind("<Leave>", _unbind_mousewheel)
        # =========================================================

        self.status=tk.Label(self,text="提示：识别依赖公开网络查询，结果提交前请人工核实。",
                             font=("微软雅黑",8),fg="#777777",anchor="w")
        self.status.pack(fill="x",padx=20,pady=(0,14))

    def import_selected_file(self, path):
        """选择文件后立即读取并验证，不再等到点击分析按钮才读取。"""
        try:
            urls = extract_urls(path)
            if not urls:
                self.progress.config(text="读取失败：0 条链接")
                self.set_status("文件已打开，但没有识别到 http/https 链接。")
                messagebox.showwarning(
                    "没有找到链接",
                    "文件已经打开，但没有识别到有效的 http/https 链接。\n\n"
                    "请确认这是上一个工具导出的 Excel/TXT 文件。"
                )
                return

            self.imported_urls = urls
            self.progress.config(text=f"已导入 {len(urls)} 条链接")
            self.set_status(f"已读取：{Path(path).name}；共识别 {len(urls)} 条链接。")
            messagebox.showinfo(
                "导入成功",
                f"文件已读取。\n\n共识别到 {len(urls)} 条链接。\n"
                "现在可以填写版权信息并开始识别运营商。"
            )
        except Exception as e:
            self.imported_urls = []
            self.progress.config(text="文件读取失败")
            self.set_status(f"读取失败：{e}")
            messagebox.showerror("文件读取失败", str(e))

    def set_status(self,text):
        self.after(0,lambda:self.status.config(text=text))

    def start_analysis(self):
        import threading
        p=self.input_file.get().strip()
        if not p:
            messagebox.showwarning("缺少文件","请先点击“打开 / 上传”选择上一个工具导出的 Excel (.xlsx) 或 TXT。"); return
        if not Path(p).exists():
            messagebox.showerror("文件不存在","请重新选择文件。"); return
        if not self.imported_urls:
            try:
                self.imported_urls = extract_urls(p)
            except Exception as e:
                messagebox.showerror("文件读取失败", str(e)); return
            if not self.imported_urls:
                messagebox.showwarning("没有链接", "当前文件中没有识别到有效链接。"); return
        if self.busy: return
        author=self.author_name.get().strip() or "作者"
        novel=self.novel_title.get().strip() or "未命名作品"
        original=self.original_url.get().strip() or "https://www.jjwxc.net/"
        self.busy=True; self.analyze_btn.config(state="disabled"); self.report_btn.config(state="disabled")
        self.clear_cards(); self.set_status("正在识别运营商，请保持网络连接。")
        threading.Thread(target=self.worker,args=(p,author,novel,original),daemon=True).start()

    def worker(self,p,author,novel,original):
        try:
            def prog(i,total,url):
                short_url = url[:60] + "..." if len(url) >60 else url
                self.after(0,lambda i=i,total=total,u=short_url:self.progress.config(text=f"正在分析 {i}/{total}: {u}"))
            urls,results,summary=analyze_urls(p,author,novel,original,prog)
            out=Path.home()/"Documents"/"AntiPiracyReporter_Results"; out.mkdir(parents=True,exist_ok=True)
            safe=re.sub(r'[\\/:*?"<>|]+',"_",novel).strip() or "未命名作品"
            f=out/f"盗文服务商报告_{safe}_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
            export_results_excel(results, f)
            self.results,self.provider_summary,self.output_excel=results,summary,f
            self.after(0,lambda:self.render_cards(author,novel,original))
            self.after(0,lambda:self.progress.config(text=f"完成：{len(urls)} 条 / {len(summary)} 个服务商"))
            self.after(0,lambda:self.report_btn.config(state="normal"))
            self.set_status(f"报告已保存：{f}")
            self.after(0,lambda:messagebox.showinfo("分析完成",f"共分析 {len(urls)} 条链接。\n报告：\n{f}"))
        except Exception as e:
            self.set_status(f"分析失败：{e}")
            self.after(0,lambda e=e:messagebox.showerror("分析失败",str(e)))
        finally:
            self.busy=False; self.after(0,lambda:self.analyze_btn.config(state="normal"))

    def clear_cards(self):
        for w in self.cards.winfo_children(): w.destroy()

    def render_cards(self,author,novel,original):
        self.clear_cards()
        for provider,data in self.provider_summary.items():
            box=tk.LabelFrame(self.cards,text=f" 【{provider}】 关联链接：{len(data['urls'])} 条 ",
                              font=("微软雅黑",10,"bold"),padx=10,pady=8)
            box.pack(fill="x",pady=7,padx=3)
            lang="en"
            if data["url"]:
                for info in KNOWN_PROVIDER_FORMS.values():
                    if info["url"]==data["url"]: lang=info.get("lang","en"); break
            elif any(c in provider.lower() for c in TELECOM_CARRIERS) or "阿里云" in provider or "腾讯云" in provider:
                lang="zh"
            row=tk.Frame(box); row.pack(fill="x",pady=(0,6))
            # ==========修复闭包陷阱==========
            copy_btn_cmd = lambda urls=data["urls"], l=lang, pvd=provider: (
                pyperclip.copy(generate_dmca_text(author, novel, original, urls, lang=l)),
                messagebox.showinfo("已复制", f"已复制【{pvd}】对应的{'中文' if l=='zh' else '英文'}申诉文本。")
            )
            tk.Button(row,text="复制申诉文本",command=copy_btn_cmd).pack(side="left",padx=(0,6))
            if data["url"]:
                tk.Button(row,text="一键打开官方举报页",
                          command=lambda u=data["url"]:webbrowser.open(u)).pack(side="left",padx=3)
            else:
                tk.Button(row,text="去百度版权平台",
                          command=lambda:webbrowser.open("https://newcopyright.baidu.com/")).pack(side="left",padx=3)
                tk.Button(row,text="去工信部 ICP",
                          command=lambda:webbrowser.open("https://beian.miit.gov.cn/")).pack(side="left",padx=3)
            tk.Label(box,text=data["advice"],justify="left",anchor="w",wraplength=850).pack(fill="x",pady=3)
            preview="\n".join(data["urls"][:3])
            if len(data["urls"])>3: preview+=f"\n……另有 {len(data['urls'])-3} 条，详见 Excel"
            tk.Label(box,text=preview,justify="left",anchor="w",wraplength=850,fg="#666666").pack(fill="x")

    def open_report(self):
        if not self.output_excel or not Path(self.output_excel).exists(): return
        try:
            import os; os.startfile(str(self.output_excel))
        except Exception as e: messagebox.showerror("打开失败",str(e))

    def confirm_close(self):
        msg="当前正在分析链接。\n\n确定要关闭应用吗？" if self.busy else "确定要关闭应用吗？"
        if messagebox.askyesno("确认关闭",msg): self.destroy()


def main():
    AntiPiracyReporterApp().mainloop()


if __name__ == "__main__":
    main()
