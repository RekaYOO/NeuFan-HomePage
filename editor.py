import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import re
import os
from typing import Dict, List, Optional

class BookmarkManager:
    def __init__(self, html_file: str):
        self.html_file = html_file
        self.bookmarks = self.load_bookmarks_from_html()
        
    def load_bookmarks_from_html(self) -> Dict:
        """从HTML文件中提取书签数据"""
        try:
            with open(self.html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用正则表达式提取JSON数据
            pattern = r'const bookmarks = ref\(({.*?})\);'
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            else:
                return {}
        except Exception as e:
            messagebox.showerror("错误", f"加载书签数据失败: {str(e)}")
            return {}

    def save_bookmarks_to_html(self):
        """将书签数据保存回HTML文件"""
        try:
            with open(self.html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换JSON数据
            pattern = r'const bookmarks = ref\(({.*?})\);'
            new_json = json.dumps(self.bookmarks, ensure_ascii=False, indent=4)
            new_content = re.sub(pattern, f'const bookmarks = ref({new_json});', content, flags=re.DOTALL)
            
            with open(self.html_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存书签数据失败: {str(e)}")
            return False

    def add_bookmark(self, page: str, category: str, name: str, url: str):
        """添加新书签"""
        if page not in self.bookmarks:
            self.bookmarks[page] = []
        
        # 查找或创建分类
        category_found = False
        for cat in self.bookmarks[page]:
            if cat["name"] == category:
                cat["links"].append({"name": name, "url": url})
                category_found = True
                break
        
        if not category_found:
            self.bookmarks[page].append({
                "name": category,
                "links": [{"name": name, "url": url}]
            })

    def edit_bookmark(self, page: str, category: str, old_name: str, old_url: str, new_name: str, new_url: str):
        """编辑书签"""
        for cat in self.bookmarks[page]:
            if cat["name"] == category:
                for link in cat["links"]:
                    if link["name"] == old_name and link["url"] == old_url:
                        link["name"] = new_name
                        link["url"] = new_url
                        return True
        return False

    def delete_bookmark(self, page: str, category: str, name: str, url: str):
        """删除书签"""
        for cat in self.bookmarks[page]:
            if cat["name"] == category:
                cat["links"] = [link for link in cat["links"] if not (link["name"] == name and link["url"] == url)]
                # 如果分类为空，删除该分类
                if not cat["links"]:
                    self.bookmarks[page].remove(cat)
                return True
        return False

    def move_bookmark(self, page: str, category: str, name: str, url: str, direction: str):
        """移动书签位置"""
        for cat in self.bookmarks[page]:
            if cat["name"] == category:
                links = cat["links"]
                for i, link in enumerate(links):
                    if link["name"] == name and link["url"] == url:
                        if direction == "up" and i > 0:
                            links[i], links[i-1] = links[i-1], links[i]
                        elif direction == "down" and i < len(links) - 1:
                            links[i], links[i+1] = links[i+1], links[i]
                        return True
        return False

class BookmarkEditor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("书签编辑器")
        self.root.geometry("800x600")
        
        # 查找HTML文件
        html_files = [f for f in os.listdir('.') if f.endswith('.html')]
        if not html_files:
            messagebox.showerror("错误", "未找到HTML文件")
            root.destroy()
            return
        
        # 如果有多个HTML文件，让用户选择
        if len(html_files) > 1:
            self.html_file = filedialog.askopenfilename(
                title="选择HTML文件",
                filetypes=[("HTML files", "*.html")]
            )
        else:
            self.html_file = html_files[0]
        
        if not self.html_file:
            root.destroy()
            return
        
        self.manager = BookmarkManager(self.html_file)
        self.setup_ui()
        
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 页面选择
        ttk.Label(main_frame, text="页面:").grid(row=0, column=0, sticky=tk.W)
        self.page_var = tk.StringVar()
        self.page_combo = ttk.Combobox(main_frame, textvariable=self.page_var)
        self.page_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.page_combo.bind('<<ComboboxSelected>>', self.on_page_change)
        
        # 添加书签区域
        add_frame = ttk.LabelFrame(main_frame, text="添加书签", padding="5")
        add_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(add_frame, text="类别:").grid(row=0, column=0, sticky=tk.W)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(add_frame, textvariable=self.category_var)
        self.category_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.category_combo.bind('<<ComboboxSelected>>', self.on_category_change)
        
        ttk.Label(add_frame, text="名称:").grid(row=1, column=0, sticky=tk.W)
        self.name_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.name_var).grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(add_frame, text="URL:").grid(row=2, column=0, sticky=tk.W)
        self.url_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.url_var).grid(row=2, column=1, sticky=(tk.W, tk.E))
        
        ttk.Button(add_frame, text="添加", command=self.add_bookmark).grid(row=3, column=1, sticky=tk.E)
        
        # 书签列表
        list_frame = ttk.LabelFrame(main_frame, text="书签列表", padding="5")
        list_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.tree = ttk.Treeview(list_frame, columns=("category", "name", "url"), show="headings")
        self.tree.heading("category", text="类别")
        self.tree.heading("name", text="名称")
        self.tree.heading("url", text="URL")
        self.tree.column("category", width=100)
        self.tree.column("name", width=150)
        self.tree.column("url", width=300)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 操作按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky=tk.E)
        
        ttk.Button(button_frame, text="编辑", command=self.edit_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="删除", command=self.delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="上移", command=lambda: self.move_selected("up")).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="下移", command=lambda: self.move_selected("down")).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存", command=self.save_changes).pack(side=tk.LEFT, padx=5)
        
        # 初始化UI
        self.update_page_combo()
        self.on_page_change(None)
        
    def update_page_combo(self):
        """更新页面下拉框"""
        pages = list(self.manager.bookmarks.keys())
        self.page_combo['values'] = pages
        if pages:
            self.page_var.set(pages[0])
            
    def update_category_combo(self):
        """更新类别下拉框，并自动选中第一个类别"""
        current_page = self.page_var.get()
        categories = []
        if current_page in self.manager.bookmarks:
            categories = [cat["name"] for cat in self.manager.bookmarks[current_page]]
        self.category_combo['values'] = categories
        if categories:
            # 如果当前类别不在新类别列表中，自动选中第一个
            if self.category_var.get() not in categories:
                self.category_var.set(categories[0])
        else:
            self.category_var.set("")
        self.update_bookmark_list()

    def update_bookmark_list(self):
        """更新书签列表"""
        self.tree.delete(*self.tree.get_children())
        current_page = self.page_var.get()
        
        if current_page in self.manager.bookmarks:
            for cat in self.manager.bookmarks[current_page]:
                for link in cat["links"]:
                    self.tree.insert("", tk.END, values=(cat["name"], link["name"], link["url"]))
                    
    def on_page_change(self, event):
        """页面变更事件处理"""
        self.update_category_combo()
        self.update_bookmark_list()
        
    def on_category_change(self, event):
        self.update_bookmark_list()
        
    def add_bookmark(self):
        """添加新书签"""
        page = self.page_var.get()
        category = self.category_var.get()
        name = self.name_var.get()
        url = self.url_var.get()
        if not all([page, category, name, url]):
            messagebox.showwarning("警告", "请填写完整信息")
            return
        # 判断是否新类别
        old_categories = set(self.category_combo['values'])
        self.manager.add_bookmark(page, category, name, url)
        self.update_category_combo()
        # 如果是新类别，自动切换到新类别
        if category not in old_categories:
            self.category_var.set(category)
            self.update_bookmark_list()
        self.name_var.set("")
        self.url_var.set("")
        
    def edit_selected(self):
        """编辑选中的书签"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要编辑的书签")
            return
            
        item = self.tree.item(selection[0])
        values = item['values']
        old_category = values[0]
        old_name = values[1]
        old_url = values[2]
        
        # 创建编辑对话框
        edit_window = tk.Toplevel(self.root)
        edit_window.title("编辑书签")
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        ttk.Label(edit_window, text="类别:").grid(row=0, column=0, padx=5, pady=5)
        category_var = tk.StringVar(value=old_category)
        category_combo = ttk.Combobox(edit_window, textvariable=category_var)
        category_combo.grid(row=0, column=1, padx=5, pady=5)
        category_combo['values'] = [cat["name"] for cat in self.manager.bookmarks[self.page_var.get()]]
        
        ttk.Label(edit_window, text="名称:").grid(row=1, column=0, padx=5, pady=5)
        name_var = tk.StringVar(value=old_name)
        ttk.Entry(edit_window, textvariable=name_var).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(edit_window, text="URL:").grid(row=2, column=0, padx=5, pady=5)
        url_var = tk.StringVar(value=old_url)
        ttk.Entry(edit_window, textvariable=url_var).grid(row=2, column=1, padx=5, pady=5)
        
        def save_edit():
            new_category = category_var.get()
            new_name = name_var.get()
            new_url = url_var.get()
            
            # 先删除旧的书签
            self.manager.delete_bookmark(
                self.page_var.get(),
                old_category,
                old_name,
                old_url
            )
            
            # 添加新的书签
            self.manager.add_bookmark(
                self.page_var.get(),
                new_category,
                new_name,
                new_url
            )
            
            self.update_category_combo()
            self.update_bookmark_list()
            edit_window.destroy()
                
        ttk.Button(edit_window, text="保存", command=save_edit).grid(row=3, column=1, padx=5, pady=5)
        
    def delete_selected(self):
        """删除选中的书签"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要删除的书签")
            return
            
        if messagebox.askyesno("确认", "确定要删除选中的书签吗？"):
            for item in selection:
                values = self.tree.item(item)['values']
                self.manager.delete_bookmark(
                    self.page_var.get(),
                    values[0],  # category
                    values[1],  # name
                    values[2]   # url
                )
            self.update_category_combo()
            self.update_bookmark_list()
            
    def move_selected(self, direction: str):
        """移动选中的书签"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要移动的书签")
            return
            
        item = selection[0]
        values = self.tree.item(item)['values']
        if self.manager.move_bookmark(
            self.page_var.get(),
            values[0],  # category
            values[1],  # name
            values[2],  # url
            direction
        ):
            self.update_bookmark_list()
            
    def save_changes(self):
        """保存更改到HTML文件"""
        if self.manager.save_bookmarks_to_html():
            messagebox.showinfo("成功", "书签已保存")
        else:
            messagebox.showerror("错误", "保存失败")

def main():
    root = tk.Tk()
    app = BookmarkEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main() 