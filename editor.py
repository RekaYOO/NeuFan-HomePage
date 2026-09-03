import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional


class BookmarkManager:
    def __init__(self, json_file: str):
        self.json_file = json_file
        self.bookmarks = self.load_bookmarks()

    def load_bookmarks(self) -> Dict:
        try:
            with open(self.json_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as error:
            messagebox.showerror('错误', f'加载书签数据失败: {error}')
            return {}

    def save_bookmarks(self) -> bool:
        try:
            with open(self.json_file, 'w', encoding='utf-8') as file:
                json.dump(self.bookmarks, file, ensure_ascii=False, indent=4)
            return True
        except Exception as error:
            messagebox.showerror('错误', f'保存书签数据失败: {error}')
            return False

    def add_bookmark(
        self,
        page: str,
        category: str,
        name: str,
        url: str,
        aliases: Optional[List[str]] = None,
    ):
        bookmark = {
            'name': name,
            'url': url,
            'aliases': aliases or [],
        }
        if page not in self.bookmarks:
            self.bookmarks[page] = []

        for current_category in self.bookmarks[page]:
            if current_category['name'] == category:
                current_category['links'].append(bookmark)
                return

        self.bookmarks[page].append({
            'name': category,
            'links': [bookmark]
        })

    def delete_bookmark(self, page: str, category: str, name: str, url: str) -> bool:
        for current_category in self.bookmarks.get(page, []):
            if current_category['name'] != category:
                continue
            current_category['links'] = [
                link for link in current_category['links']
                if not (link['name'] == name and link['url'] == url)
            ]
            if not current_category['links']:
                self.bookmarks[page].remove(current_category)
            return True
        return False

    def move_bookmark(self, page: str, category: str, name: str, url: str, direction: str) -> bool:
        for current_category in self.bookmarks.get(page, []):
            if current_category['name'] != category:
                continue
            links = current_category['links']
            for index, link in enumerate(links):
                if link['name'] == name and link['url'] == url:
                    if direction == 'up' and index > 0:
                        links[index], links[index - 1] = links[index - 1], links[index]
                        return True
                    if direction == 'down' and index < len(links) - 1:
                        links[index], links[index + 1] = links[index + 1], links[index]
                        return True
                    return False
        return False

    def sort_category(self, page: str, category: str) -> bool:
        for current_category in self.bookmarks.get(page, []):
            if current_category['name'] != category:
                continue
            current_category['links'].sort(key=self.bookmark_sort_key)
            return True
        return False

    @staticmethod
    def compact_ascii(value: str) -> str:
        return re.sub(r'[^a-z0-9]+', '', str(value).casefold())

    @classmethod
    def full_pinyin_alias(cls, name: str, aliases: List[str]) -> str:
        compact_aliases = []
        for alias in aliases:
            alias = str(alias).strip()
            if not re.fullmatch(r'[A-Za-z0-9 _-]+', alias):
                continue
            compact = cls.compact_ascii(alias)
            if compact and compact not in compact_aliases:
                compact_aliases.append(compact)

        chinese_count = len(re.findall(r'[\u3400-\u9fff]', name))
        literal_ascii = cls.compact_ascii(''.join(char for char in name if char.isascii()))
        initials_length = chinese_count + len(literal_ascii)
        initials = next((
            alias for alias in compact_aliases
            if len(alias) == initials_length and cls.is_subsequence(literal_ascii, alias)
        ), '')
        pinyin_candidates = [alias for alias in compact_aliases if re.search(r'[aeiou]', alias)]
        if initials:
            full_pinyin_candidates = [
                alias for alias in pinyin_candidates
                if len(alias) > len(initials) and cls.is_subsequence(initials, alias)
            ]
            if full_pinyin_candidates:
                return min(full_pinyin_candidates, key=lambda alias: (len(alias), alias))

        return min(pinyin_candidates, key=lambda alias: (len(alias), alias), default='')

    @staticmethod
    def is_subsequence(needle: str, haystack: str) -> bool:
        if not needle:
            return True
        iterator = iter(haystack)
        return all(char in iterator for char in needle)

    @classmethod
    def bookmark_sort_key(cls, link: Dict):
        name = str(link.get('name', ''))
        normalized_name = cls.compact_ascii(name)
        has_chinese = bool(re.search(r'[\u3400-\u9fff]', name))
        if not has_chinese:
            return 0, normalized_name, name.casefold()

        full_pinyin = cls.full_pinyin_alias(name, link.get('aliases', []))
        return 1, full_pinyin or normalized_name, name


class BookmarkEditor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('书签编辑器')
        self.root.geometry('800x600')

        default_json = os.path.join('data', 'bookmarks.json')
        if os.path.exists(default_json):
            self.json_file = default_json
        else:
            self.json_file = filedialog.askopenfilename(
                title='选择 bookmarks.json 文件',
                filetypes=[('JSON 文件', '*.json')]
            )

        if not self.json_file:
            messagebox.showerror('错误', '未选择书签数据文件')
            root.destroy()
            return

        self.manager = BookmarkManager(self.json_file)
        self.create_widgets()
        self.update_category_combo()
        self.update_bookmark_list()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding='10')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        ttk.Label(main_frame, text=f'当前文件: {self.json_file}').grid(row=0, column=0, columnspan=4, sticky=tk.W)

        ttk.Label(main_frame, text='页面:').grid(row=1, column=0, padx=5, pady=5)
        self.page_var = tk.StringVar(value=next(iter(self.manager.bookmarks), 'quick'))
        self.page_combo = ttk.Combobox(main_frame, textvariable=self.page_var)
        self.page_combo.grid(row=1, column=1, padx=5, pady=5)
        self.page_combo['values'] = list(self.manager.bookmarks.keys())
        self.page_combo.bind('<<ComboboxSelected>>', lambda event: self.on_page_change())

        ttk.Label(main_frame, text='分类:').grid(row=1, column=2, padx=5, pady=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(main_frame, textvariable=self.category_var)
        self.category_combo.grid(row=1, column=3, padx=5, pady=5)

        columns = ('category', 'name', 'url', 'aliases')
        self.tree = ttk.Treeview(main_frame, columns=columns, show='headings')
        self.tree.heading('category', text='分类')
        self.tree.heading('name', text='名称')
        self.tree.heading('url', text='URL')
        self.tree.heading('aliases', text='别名')
        self.tree.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=4, pady=5)
        ttk.Button(button_frame, text='添加', command=self.add_bookmark).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text='编辑', command=self.edit_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text='删除', command=self.delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text='上移', command=lambda: self.move_selected('up')).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text='下移', command=lambda: self.move_selected('down')).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text='排序本分类', command=self.sort_current_category).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text='保存', command=self.save_changes).pack(side=tk.LEFT, padx=5)

        input_frame = ttk.LabelFrame(main_frame, text='添加新书签', padding='10')
        input_frame.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(input_frame, text='名称:').grid(row=0, column=0, padx=5, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.name_var).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text='URL:').grid(row=0, column=2, padx=5, pady=5)
        self.url_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.url_var, width=40).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(input_frame, text='别名:').grid(row=1, column=0, padx=5, pady=5)
        self.aliases_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.aliases_var).grid(
            row=1, column=1, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E)
        )

        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(3, weight=1)
        main_frame.rowconfigure(2, weight=1)

    def on_page_change(self):
        self.update_category_combo()
        self.update_bookmark_list()

    def update_category_combo(self):
        current_page = self.page_var.get()
        categories = [category['name'] for category in self.manager.bookmarks.get(current_page, [])]
        self.category_combo['values'] = categories
        if categories and self.category_var.get() not in categories:
            self.category_var.set(categories[0])

    def update_bookmark_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        current_page = self.page_var.get()
        for category in self.manager.bookmarks.get(current_page, []):
            for link in category['links']:
                aliases = ', '.join(link.get('aliases', []))
                self.tree.insert('', tk.END, values=(category['name'], link['name'], link['url'], aliases))

    def add_bookmark(self):
        page = self.page_var.get().strip()
        category = self.category_var.get().strip()
        name = self.name_var.get().strip()
        url = self.url_var.get().strip()
        aliases = self.parse_aliases(self.aliases_var.get())
        if not all([page, category, name, url]):
            messagebox.showwarning('警告', '请填写完整信息')
            return

        old_categories = set(self.category_combo['values'])
        self.manager.add_bookmark(page, category, name, url, aliases)
        self.update_category_combo()
        if category not in old_categories:
            self.category_var.set(category)
        self.update_bookmark_list()
        self.name_var.set('')
        self.url_var.set('')
        self.aliases_var.set('')

    def edit_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning('警告', '请选择要编辑的书签')
            return

        values = self.tree.item(selection[0])['values']
        old_category, old_name, old_url, old_aliases = values

        edit_window = tk.Toplevel(self.root)
        edit_window.title('编辑书签')
        edit_window.transient(self.root)
        edit_window.grab_set()

        ttk.Label(edit_window, text='分类:').grid(row=0, column=0, padx=5, pady=5)
        category_var = tk.StringVar(value=old_category)
        category_combo = ttk.Combobox(edit_window, textvariable=category_var)
        category_combo.grid(row=0, column=1, padx=5, pady=5)
        category_combo['values'] = [category['name'] for category in self.manager.bookmarks.get(self.page_var.get(), [])]

        ttk.Label(edit_window, text='名称:').grid(row=1, column=0, padx=5, pady=5)
        name_var = tk.StringVar(value=old_name)
        ttk.Entry(edit_window, textvariable=name_var).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(edit_window, text='URL:').grid(row=2, column=0, padx=5, pady=5)
        url_var = tk.StringVar(value=old_url)
        ttk.Entry(edit_window, textvariable=url_var).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(edit_window, text='别名:').grid(row=3, column=0, padx=5, pady=5)
        aliases_var = tk.StringVar(value=old_aliases)
        ttk.Entry(edit_window, textvariable=aliases_var).grid(row=3, column=1, padx=5, pady=5)

        def save_edit():
            new_category = category_var.get().strip()
            new_name = name_var.get().strip()
            new_url = url_var.get().strip()
            new_aliases = self.parse_aliases(aliases_var.get())
            if not all([new_category, new_name, new_url]):
                messagebox.showwarning('警告', '请填写完整信息')
                return

            self.manager.delete_bookmark(self.page_var.get(), old_category, old_name, old_url)
            self.manager.add_bookmark(
                self.page_var.get(), new_category, new_name, new_url, new_aliases
            )
            self.update_category_combo()
            self.category_var.set(new_category)
            self.update_bookmark_list()
            edit_window.destroy()

        ttk.Button(edit_window, text='保存', command=save_edit).grid(row=4, column=1, padx=5, pady=5)

    def delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning('警告', '请选择要删除的书签')
            return

        if not messagebox.askyesno('确认', '确定要删除选中的书签吗？'):
            return

        for item in selection:
            category, name, url, _aliases = self.tree.item(item)['values']
            self.manager.delete_bookmark(self.page_var.get(), category, name, url)
        self.update_category_combo()
        self.update_bookmark_list()

    def move_selected(self, direction: str):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning('警告', '请选择要移动的书签')
            return

        category, name, url, _aliases = self.tree.item(selection[0])['values']
        if self.manager.move_bookmark(self.page_var.get(), category, name, url, direction):
            self.update_bookmark_list()

    def sort_current_category(self):
        selection = self.tree.selection()
        if selection:
            category = self.tree.item(selection[0])['values'][0]
        else:
            category = self.category_var.get().strip()

        if not category:
            messagebox.showwarning('警告', '请选择要排序的分类')
            return

        if self.manager.sort_category(self.page_var.get(), category):
            self.category_var.set(category)
            self.update_bookmark_list()
            messagebox.showinfo('完成', f'“{category}”已按名称排序')

    @staticmethod
    def parse_aliases(value: str) -> List[str]:
        aliases = []
        seen = set()
        for alias in value.replace('，', ',').split(','):
            alias = alias.strip()
            normalized = alias.lower()
            if alias and normalized not in seen:
                aliases.append(alias)
                seen.add(normalized)
        return aliases

    def save_changes(self):
        if self.manager.save_bookmarks():
            messagebox.showinfo('成功', '书签已保存')
        else:
            messagebox.showerror('错误', '保存失败')


def main():
    root = tk.Tk()
    BookmarkEditor(root)
    root.mainloop()


if __name__ == '__main__':
    main()
