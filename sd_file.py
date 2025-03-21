# SeitenBot2 sd_file.py

# MIT License
# 
# Copyright (c) 2025 Honjitsu-Seiten (https://github.com/Honjitsu-Seiten)
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import re, io, time
from collections import defaultdict

import pywikibot
from pywikibot.exceptions import Error
from pywikibot.pagegenerators import GeneratorFactory, PetScanPageGenerator
from pywikibot.data import api
from pywikibot.bot import SingleSiteBot, CurrentPageBot
from pywikibot.tools.chars import url2string

import mwparserfromhell
from mwparserfromhell.nodes.template import Template
from mwparserfromhell.nodes.wikilink import Wikilink
from mwparserfromhell.wikicode import Wikicode

skip_listpage = '利用者:SeitenBot2/即時削除を見送ったファイル'

def get_seitenbot2_table2(wikicode: Wikicode):
    result = wikicode.filter_templates(matches=lambda x: x.name.matches('Table2') and 'seitenbot2' in str(x.get('class').value).split())
    if not result:
        pywikibot.error('一覧表が見つかりません')
        raise ValueError('一覧表が見つかりません')
    return result[0]

class FileSdBot(SingleSiteBot, CurrentPageBot):

    def setup(self):
        self.ignorelist = self.opt.get('ignorelist', False)

        self.import_log_pattern= re.compile(r'^Imported with FileImporter from https\://ja\.wikipedia\.org/wiki/(.+?)$')
        self.skipped_reason = {
            'NotUsedFileImporter': 'A',
            'InvalidCategory': 'B',
            'CommonsFileNotExists': 'C',
            'UsedOldFileName': 'D',
            'IncorrectCommonsFileName': 'E',
            'ChangedAfterExported': 'F',
            'NoticeOfExportation': 'G',
            'OtherIssue': 'Z'
        }
        self.skipped = defaultdict(lambda: [set(), None])
        self.commons_site = pywikibot.Site(code="commons", fam="commons")
        self.except_categories = (
            '自由利用できない画像'
            '屋外美術を含む画像',
            '屋外美術写真の利用方針に違反している画像',
            '日本ではパブリックドメインにあり、米国でパブリックドメインにない画像',
            'ライセンスの正確性に疑義がある画像',
            'パブリックドメインとなる理由が不明の画像',
            '著作権放棄したとされる著作者が不明の画像',
            'ライセンス不明の画像',
            '出典不明の画像',
            '削除依頼中のページ',
            '即時削除対象のページ'
        )

        self.sdtemplates = {'即時削除'} #set
        sdtemplate_redirects = set()
        for template in self.sdtemplates:
            templatepage = pywikibot.Page(source=self.site, title=template, ns=10)
            for redirect in self.site.pagebacklinks(templatepage, filter_redirects=True, namespaces=10):
                sdtemplate_redirects.add(redirect.title(with_ns=False))
        self.sdtemplates.update(sdtemplate_redirects)
        self.sdtemplates_f = {'即時削除/ファイル1-5'} #set
        sdtemplate_f_redirects = set()
        self.valid_reasons = set()
        for template in self.sdtemplates_f:
            templatepage = pywikibot.Page(source=self.site, title=template, ns=10)
            for redirect in self.site.pagebacklinks(templatepage, filter_redirects=True, namespaces=10):
                redirect_title = redirect.title(with_ns=False)
                sdtemplate_f_redirects.add(redirect_title)
                if m := re.match(r"即時削除2?/(.+)$", redirect_title):
                    self.valid_reasons.add(m.group(1))
        self.sdtemplates_f.update(sdtemplate_f_redirects)
        self.nowcommons_templates = {'NowCommons'} #set
        nowcommons_redirects = set()
        for template in self.nowcommons_templates:
            templatepage = pywikibot.Page(source=self.site, title=template, ns=10)
            for redirect in self.site.pagebacklinks(templatepage, filter_redirects=True, namespaces=10):
                nowcommons_redirects.add(redirect.title(with_ns=False))
        self.nowcommons_templates.update(nowcommons_redirects)
        if self.ignorelist:
            return
        self.skipped_listpage = pywikibot.Page(source=self.site, title=skip_listpage)
        self.skipped_listpage.clear_cache()
        self.site.loadrevisions(self.skipped_listpage, user='SeitenBot2', total=1)
        already_deleted_files = self.get_deletedfiles(end=next(iter(self.skipped_listpage._revisions.values())).timestamp)
        #already_deleted_files = self.get_deletedfiles(total=10)
        self.skipped_listpage.clear_cache()
        self.listpage_code = mwparserfromhell.parse(self.skipped_listpage.text)
        table2 = get_seitenbot2_table2(self.listpage_code)
        i = 1
        remove_line_indexs = []
        self.ignore_files = set()
        table2_lines = table2.splitlines()
        for i in range(len(table2_lines)):
            match = re.match(r'\| *{{P\|ファイル\|([^}]+?)}}', table2_lines[i])
            if not match:
                continue
            file = pywikibot.FilePage(source=self.site, title=match.group(1))
            if file in already_deleted_files:
                remove_line_indexs.append(i)
            else:
                self.ignore_files.add(file)
        remove_line_indexs.reverse()
        for index in remove_line_indexs:
            table2_lines.pop(index)
        self.listpage_code.replace(table2, '\n'.join(table2_lines), recursive=False)

    def get_deletedfiles(self, end=None, total=None):
        legen = self.site._generator(api.LogEntryListGenerator, type_arg='delete', total=total)
        legen.request['leaction'] = 'delete/delete'
        legen.set_namespace(6)
        if end is not None:
            legen.request['leend'] = end
        return { pywikibot.FilePage(source=self.site, title=logentry['title']) for logentry in legen if logentry['pageid'] == 0 }

    def init_page(self, item):
        self.description = ''
        assert int(item.namespace()) == 6, 'int(item.namespace()) == 6'
        return pywikibot.FilePage(source=item)

    def skip_page(self, page):
        if not self.ignorelist and page in self.ignore_files:
            return True
        return super().skip_page(page)

    def treat_page(self):
        for category in self.current_page.categories():
            if category.title(with_ns=False) in self.except_categories:
                self._skip_delete('InvalidCategory')
        try:
            self.current_page.text = self.current_page.get().replace('\u200e', '')
        except Error as e:
            pywikibot.error(str(e))
            return
        commons_file_name = self.current_page.title(with_ns=False)
        wikicode = mwparserfromhell.parse(self.current_page.text)
        for template in wikicode.filter_templates():
            template.name = re.sub(r'[ _]+', ' ', str(template.name))
            if template.name.matches(self.sdtemplates):
                if str(template.get(1).value) in self.valid_reasons:
                    try:
                        v = str(template.get(2).value.strip_code())
                        if v:
                            commons_file_name = v
                            break
                    except ValueError:
                        pass
            elif template.name.matches(self.sdtemplates_f):
                commons_file_name = self.current_page.title(with_ns=False)
                try:
                    v = str(template.get(1).value.strip_code())
                    if v:
                        commons_file_name = v
                        break
                except ValueError:
                    pass
        self.commons_page = pywikibot.FilePage(self.commons_site, title=commons_file_name)
        pywikibot.output('テンプレートで指定されたコモンズのファイル名: ', newline=False)
        pywikibot.output(self.commons_page.title(with_ns=False))
        self._check()
        if self.current_page in self.skipped:
            pywikibot.output('\n'.join(self.skipped[self.current_page][0]))
            if 'NotUsedFileImporter' in self.skipped[self.current_page][0] and 'OtherIssue' not in self.skipped[self.current_page][0]:
                self._put_template()
            return
        pywikibot.output('「{}」を削除します'.format(self.current_page.title(with_ns=True)))
        reason = 'Bot: [[WP:CSD#ファイル1-5]] [[c:{}]]へ移行'.format(self.commons_page.title(with_ns=True))
        time.sleep(1)
        self.current_page.delete(reason=reason, prompt= not self.opt.always, automatic_quit=True)

    def _check(self):

        # インポートログ取得するために元のページを保存する
        importlog_target = self.commons_page

        # 即時削除テンプレートで指定されたコモンズのファイルが存在しなければ、移動ログから追跡する
        while True:
            if self.commons_page.exists():
                break
            try:
                movelog = next(iter(self.commons_site.logevents(logtype='move', page=self.commons_page, total=1)))
                self.commons_page = pywikibot.FilePage(source=movelog.target_page())
            except StopIteration:
                self._skip_delete('CommonsFileNotExists')
                return

        # コモンズのファイルがリダイレクトであれば、リダイレクトを辿る
        if self.commons_page.isRedirectPage():
            self.commons_page = self.commons_page.getRedirectTarget()

        time.sleep(1)

        # コモンズからインポートログを取得する
        importlogs = tuple(self.commons_site.logevents(
           logtype='import',
           page=importlog_target,
           tag='fileimporter',
           total=1
        ))
        self.import_log_timestamp = None
        if len(importlogs) > 0:
            importlog = importlogs[0]
            if m := re.match(self.import_log_pattern, importlog.comment()):
                importfrom = url2string(m.group(1)).replace('_', ' ')
                if importfrom != self.current_page.title(with_ns=True):
                    # インポート元が現在のローカルのファイル名と異なる
                    self._skip_delete('IncorrectCommonsFileName')
                    pywikibot.output('指定されたコモンズのファイルのインポート元: ', newline=False)
                    pywikibot.output(importfrom)
                    return
                self.import_log_timestamp = importlog.timestamp()
            else:
                self._skip_delete('OtherIssue')
                pywikibot.error('ログのフォーマットが異常です')
                return
        else:
            time.sleep(1)

            # インポートログがなければ編集履歴を新しい順に走査し、インポート時に自動記入される要約欄を探す
            for revision in iter(self.commons_page.revisions(reverse=False, content=False)):
                if m := re.match(self.import_log_pattern, revision.comment):
                    importfrom = url2string(m.group(1)).replace('_', ' ')
                    if importfrom == self.current_page.title(with_ns=True):
                        self.import_log_timestamp = revision.timestamp
                        break
                    else:
                        self._skip_delete('IncorrectCommonsFileName')
                        pywikibot.output('指定されたコモンズのファイルのインポート元: ', newline=False)
                        pywikibot.output(importfrom)
                        return
                elif m := re.search(r'moved page \[\[(File:.+?)\]\] to \[\[(File:.+?)\]\]', revision.comment):
                    importlog_target = m.group(1)
            else:
                self._skip_delete('NotUsedFileImporter')

        # ローカルのファイルを削除しても読み込みのリンク切れが生じないか確認
        if self.current_page.title(with_ns=False) != self.commons_page.title(with_ns=False):
            it = iter(self.current_page.using_pages())
            try:
                if next(it) == self.current_page:
                    next(it)
            except StopIteration:
                pass
            else:
                self._skip_delete('UsedOldFileName')

        time.sleep(1)

        # FileImporterが使われていない場合に、ファイルのハッシュ値から移入日時を取得する
        if not self.import_log_timestamp:
            original_sha1 = self.current_page.latest_file_info.sha1
            self.commons_page.get_file_history()
            commons_file_histories = self.commons_page.get_file_history()
            for info in (commons_file_histories[k] for k in sorted(commons_file_histories.keys())):
                if info.sha1 == original_sha1:
                    self.import_log_timestamp = info.timestamp
                    break
            else:
                pywikibot.error('ファイルのハッシュ値が一致しません')
                self._skip_delete('OtherIssue')
                return

        # ローカルのファイルの編集履歴を古いに走査し、本文も取得する
        # 編集差分を生成するため、1つ前の版の本文はprevtextに保存する
        prevtext = ''
        for revision in self.current_page.revisions(reverse=True, content=True):
            curtext = revision.text.replace('\u200e', '')
            if revision.timestamp < self.import_log_timestamp:
                # コモンズの移入日時より前であれば、コモンズへの移行に関するお願いのようなものが本文にないか確認する

                # 本文をself.descriptionに保存する
                # {{Moved from Japanese Wikipedia}}の生成において、移入時点での本文を利用するため
                self.description = curtext
                curcode = mwparserfromhell.parse(curtext)
                for template in curcode.ifilter_templates():
                    template.name = re.sub(r'[ _]+', ' ', str(template.name))
                    if template.name.matches('Keep local'):
                        self._skip_delete('NoticeOfExportation')
                        break
                else:
                    if re.search(r'コモンズ.+?(コピー|転載|移[行|出|入|す])', self._remove_minor_codes(curtext)):
                        self._skip_delete('NoticeOfExportation')
            elif revision.user not in ("MGA73", "MGA73bot"):
                # コモンズの移入日時より後であれば、明らかにコモンズへ反映させる必要のない編集のみであるかを確認する
                # ただし特定の利用者による編集は無視する
                pywikibot.output('{0.timestamp} {0.user}'.format(revision))
                pywikibot.showDiff(prevtext, curtext)

                # カテゴリや特定のテンプレートといったものを除去してから比較する
                normalized_prevtext = self._remove_minor_codes(prevtext)
                normalized_curtext = self._remove_minor_codes(curtext)
                if normalized_prevtext == normalized_curtext:
                    continue
                self._skip_delete('ChangedAfterExported')
            prevtext = curtext

    # 未使用
    # def _check_line(self, line):

        # for node in mwparserfromhell.parse(re.sub(r'\s+', ' ', str(line.strip()))).ifilter(recursive=False):
            # if isinstance(node, Wikilink) and node.title.lower().startswith(('category:', 'カテゴリ:')):
                # return
            # if isinstance(node, Template) \
            # and node.name.matches(self.sdtemplates | self.sdtemplates_f | self.nowcommons_templates | {'コモンズへの移動推奨', 'GFDL', 'GFDL-ja', 'Self', 'Copy to Wikimedia Commons', 'MTC'}):
                # return
            # self._skip_delete('ChangedAfterExported')

    def _remove_minor_codes(self, text):
        """カテゴリや特定のテンプレートといった、コモンズへ反映させる必要のないものを除去する"""
        code = mwparserfromhell.parse(text.strip())
        for node in code.ifilter(recursive=False):
            if isinstance(node, Wikilink) and node.title.lower().startswith(('category:', 'カテゴリ:')):
                code.remove(node)
            elif isinstance(node, Template):
                node.name = re.sub(r' +', ' ', str(node.name))
                if node.name.matches(
                    self.sdtemplates |
                    self.sdtemplates_f |
                    self.nowcommons_templates |
                    {'コモンズへの移動推奨', 'GFDL', 'GFDL-ja', 'Self', 'Copy to Wikimedia Commons', 'MTC'}
                    ):
                    code.remove(node)
        return re.sub(r'\W+', '', str(code))

    def _skip_delete(self, reason):
        self.skipped[self.current_page][0].add(reason)
        if getattr(self, 'commons_page', None):
            self.skipped[self.current_page][1] = self.commons_page

    def _put_template(self):
        commons_code = mwparserfromhell.parse(self.commons_page.text)
        for template in commons_code.ifilter_templates(recursive=False):
            template.name = re.sub(r' +', ' ', str(template.name))
            if template.name.matches('Moved from Japanese Wikipedia'):
                pywikibot.output('コモンズに既に{{Moved from Japanese Wikipedia}}が貼られています')
                return False
        try:
            output_text = self._make_template()
        except Error:
            self._skip_delete('OtherIssue')
            return False
        newtext = self.commons_page.text
        code = commons_code
        for section in commons_code.get_sections(include_lead=False):
            if re.search(r'[Oo]riginal[ _]+upload[ _]+log', str(section.nodes[0].title)):
                code = section
                break
        else:
            output_text = '== {{Original upload log}} ==\n' + output_text
        if categories := code.filter_wikilinks(matches=r'\[\[Category:.+?\]\]', flags=re.I):
            commons_code.insert_before(categories[0], output_text)
        else:
            commons_code.insert_after(code, output_text)
        newtext = str(commons_code)
        summary='Bot: Adding upload logs and histories of the original file on Japanese Wikipedia'
        if not hasattr(self.site, '_noDeletePrompt'):
            pywikibot.showDiff(self.commons_page.text, newtext, context=3)
        self.commons_page.text = newtext
        return self._save_page(self.commons_page, self.commons_page.save, summary=summary, minor=False)

    def _make_template(self):
        file_histories = self.current_page.get_file_history()
        infos = [file_histories[k] for k in sorted(file_histories.keys())]
        revisions = tuple(self.current_page.revisions(reverse=True))
        if len(infos) > 9:
            raise pywikibot.Error('元のファイルの版数が多すぎます')
        if len(revisions) > 19:
            raise pywikibot.Error('元の編集履歴が多すぎます')
        output = ['{{Moved from Japanese Wikipedia']
        output.append('| filename = ' + self.current_page.title(with_ns=False))
        wikicode = mwparserfromhell.parse(self.description)
        for comment in wikicode.filter_comments():
            wikicode.remove(comment)
        for template in wikicode.ifilter_templates():
            if template.name.matches('Information'):
                description = re.sub(r'\n+', ' ', str(template.get('Description').value)).strip() if template.has('Description') else ''
                output.append('| description = <nowiki>{}</nowiki>'.format(description))
                break
        else:
            for wikilink in wikicode.filter_wikilinks():
                if wikilink.title.lower().startswith(('category:', 'カテゴリ:')):
                    wikicode.remove(wikilink)
            description = re.sub(r'\n+', ' ', str(wikicode)).strip()
            output.append('| description = <nowiki>{}</nowiki>'.format(description))
        output.append('| file_history = {{Moved from Japanese Wikipedia/FileHistory\n | timezone = UTC')
        i = 1
        info_format = ' | datetime{0} = {timestamp}\n | demensions{0} = {width}x{height}\n | user{0} = {user}'
        for info in infos:
            if info.timestamp >= self.import_log_timestamp:
                break
            output.append(info_format.format(i, **info.__dict__))
            comment = re.sub(r'\n+', ' ', info.comment).strip() if hasattr(info, 'comment') and info.comment else ''
            comment_format = ' | comment{} = <nowiki>{}</nowiki>' if comment else ' | comment{} = '
            output.append(comment_format.format(i, comment))
            i += 1
        output.append('}}\n| page_history = {{Moved from Japanese Wikipedia/PageHistory\n | timezone = UTC')
        i = 1
        for revision in revisions:
            if revision.timestamp >= self.import_log_timestamp:
                break
            revision_format = ' | datetime{0} = {r.timestamp}\n | user{0} = {r.user}'
            output.append(revision_format.format(i, r=revision))
            comment = re.sub(r'\n+', ' ', revision.comment).strip() if revision.comment else ''
            comment_format = ' | summary{} = <nowiki>{}</nowiki>' if comment else ' | summary{} = '
            output.append(comment_format.format(i, comment))
            if revision.minor:
                output.append(' | flag{} = m'.format(i))
            i += 1
        output.append('}}\n| other_information = \n}}\n')
        return '\n'.join(output)

    def teardown(self):
        if self.ignorelist:
            return
        # if len(self.skipped) == 0:
            # pywikibot.output('スキップリストを更新する必要はありません')
            # return
        # if 'sd_file_development.py' in __file__:
            # pywikibot.output('スキップリストへの書き込み操作は省略します')
            # return
        newtable2 = io.StringIO()
        #newtable2 = io.StringIO('{{Table2\n| class= wikitable sortable\n| cols = 4\n| number = 1\n')
        #newtable2.write('| th1=ローカルのファイル |th2=コモンズのファイル |th3=コモンズと同名か |th4=見送った理由')
        #newtable2.write('| cell1-2 = min-width: 13.5em;')
        table2 = get_seitenbot2_table2(self.listpage_code)
        newtable2.write(str(table2)[:table2.rindex('}}')])
        for page, value in self.skipped.items():
            newtable2.write('| {{P|ファイル|')
            newtable2.write(page.title(with_ns=False))
            newtable2.write('}} ')
            if value[1]:
                if value[1].exists():
                    newtable2.write('| [[:c:')
                    newtable2.write(value[1].title(with_ns=True))
                    newtable2.write('|最新版]] ')
                    oldest_revid = str(value[1].oldest_revision.revid)
                    newtable2.write('/ [[:c:Special:PermaLink/')
                    newtable2.write(oldest_revid)
                    newtable2.write('|初版]] / [[:c:Special:Diff/')
                    newtable2.write(oldest_revid)
                    newtable2.write('/cur|差分]] / {{Fullurl|n=c%3A')
                    newtable2.write(value[1].title(with_ns=True, as_url=True))
                    newtable2.write('|p=action=history|s=履歴|t=コモンズの履歴}} ')
                else:
                    newtable2.write('| {{Fullurl|n=c%3ASpecial%3ALog|p=page=')
                    newtable2.write(value[1].title(with_ns=True, as_url=True))
                    newtable2.write('|s=ログ|t=コモンズの記録}} ')
                newtable2.write('| Yes ' if page.title(with_ns=False) == value[1].title(with_ns=False) else "| '''No''' ")
            else:
                newtable2.write('| | ')
            newtable2.write('| ')
            reasons = sorted([self.skipped_reason[r] for r in value[0]])
            newtable2.write(', '.join('[[#{0}|{0}]]'.format(x) for x in reasons))
            newtable2.write('\n')
        newtable2.write('}}')
        self.listpage_code.replace(table2, newtable2.getvalue(), recursive=False)
        self.userPut(self.skipped_listpage, self.skipped_listpage.text, str(self.listpage_code), summary='Botによる: 一覧の更新', minor=False, show_diff=not self.opt.always)


def main(*args):
    local_args = pywikibot.handle_args(args)
    generator_factory = GeneratorFactory()
    local_args = generator_factory.handle_args(local_args)
    options = {}

    site = pywikibot.Site()

    for arg in local_args:
        arg, _, value = arg.partition(':')
        option = arg.partition('-')[2]
        if option in ('always', 'ignorelist', 'recent'):
            options[option] = True
        else:
            options[option] = value
    generator = generator_factory.getCombinedGenerator()
    if not generator:
        generator = PetScanPageGenerator(
            ["コモンズへの移動により即時削除対象となったファイル",],
            namespaces=[6,],
            extra_options={
                'output_limit': generator_factory.limit,
                'outlinks_no': None if options.get('ignorelist', False) else skip_listpage,
                'sortby': 'date',
                'sortorder': 'descending' if options.get('recent', False) else 'ascending'
            }
        )

    FileSdBot(generator=generator, site=site, **options).run()

if __name__ == "__main__":
    main()
