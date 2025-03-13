# SeitenBot2 kyoudou.py

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


import collections, re
from datetime import datetime, timedelta, timezone

import pywikibot
import mwparserfromhell

weekday_ja = ('月', '火', '水', '木', '金', '土', '日')

def iso8601toja(timestamp):
    return u'{}年{}月{}日 ({})'.format(
        timestamp.year,
        timestamp.month,
        timestamp.day,
        weekday_ja[timestamp.weekday()]
        ) + timestamp.strftime(u' %H:%M (UTC)')

def main(*args):
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    @param args: command line arguments
    @type args: list of unicode
    """
    show_diff = False
    options = {}

    for arg in pywikibot.handle_args(args):
        arg, _, value = arg.partition(':')
        option = arg.partition('-')[2]
        # bot options
        if option in ('showdiff', ):
            show_diff = True
        else:
            options[option] = value

    waitfinished = int(options.pop('waitfinished', 7))
    waitold = int(options.pop('waitold', 90))

    site = pywikibot.Site(code="ja", fam="wikipedia")
    if not site.logged_in():
        site.login()

    finishedlist(site, waitfinished, show_diff)
    oldrequest(site, waitold, show_diff)

def finishedlist(site, wait, show_diff):
    finished_title = 'Template:共同翻訳完了項目'
    finishedpage = pywikibot.Page(site, finished_title)
    if not finishedpage.exists():
        pywikibot.error("{} doesn't exist.".format(finished_title))
        return
    finishedpage_oldtext = finishedpage.text
    lines = finishedpage.text.splitlines(keepends=True)
    newlines = lines.copy()
    for line in lines:
        if match := re.match(r'\* ?\[\[(\d{1,2})月(\d{1,2})日\]\]', line):
            now = datetime.now(timezone.utc)
            year = now.year
            month = int(match.group(1))
            day = int(match.group(2))
            if now.month < month:
                year -= 1
            finished_datetime = datetime(year=year, month=month, day=day, tzinfo=timezone.utc)
            if (now - finished_datetime) > timedelta(days=wait + 1):
                newlines.remove(line)
    finishedpage.text = ''.join(newlines)
    if finishedpage_oldtext == finishedpage.text:
        pywikibot.output("掲載期限切れの項目はありません。")
        return
    if show_diff:
        pywikibot.showDiff(finishedpage_oldtext, finishedpage.text)
    finishedpage.save(summary='Botによる: 掲載期限切れの項目を除去', minor=False)

def oldrequest(site, wait, show_diff):
    kyoudou_title = 'Wikipedia:共同翻訳依頼'
    old_title = 'Wikipedia:共同翻訳依頼/古い依頼'

    # 古い依頼を探す
    kyoudou = pywikibot.Page(site, kyoudou_title)
    if not kyoudou.exists():
        pywikibot.error("{} doesn't exist.".format(kyoudou_title))
        return
    kyoudou_oldtext = kyoudou.text
    signature_pattern = re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日 \([月火水木金土日]\) (\d{2}):(\d{2}) \(UTC\)$', re.M)
    old_dict = collections.defaultdict(list)
    old_request_count = 0
    kyoudou_code = mwparserfromhell.parse(kyoudou.text)
    for field in kyoudou_code.get_sections(levels=(2,), matches=lambda h: h.strip() != '関連項目', include_lead=False):
        field_name = str(field.get(0).title).split()[0]
        for request in field.get_sections(levels=(3,), include_lead=False):
            request_core = str(request).split(u"'''コメント'''", maxsplit=1)[0]
            for match in signature_pattern.finditer(request_core):
                signature_datetime = datetime(*map(int, match.groups()), tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if (now - signature_datetime) < timedelta(days=wait):
                    break
            else:
                old_request_count += 1
                old_dict[field_name].append(str(request))
                kyoudou_code.remove(request)
    if not old_dict:
        pywikibot.output("古い依頼はありません。")
        return

    # 古い依頼を転記する
    oldpage = pywikibot.Page(pywikibot.Site('ja', 'wikipedia'), old_title)
    if not oldpage.exists():
        pywikibot.error("{}が存在しません。".format(old_title))
        return
    oldpage_oldtext = oldpage.text
    oldpage_code = mwparserfromhell.parse(oldpage.text)
    for old_field in oldpage_code.get_sections(levels=(2,), include_lead=False):
        old_field_name = str(old_field.get(0).title).split()[0]
        if old_field_name in old_dict:
            old_field.append(old_dict[old_field_name])
    kyoudou.text = str(kyoudou_code)
    oldpage.text = str(oldpage_code)
    oldpage.text = re.sub(r'\[\[ */ *(.+?) */ *\]\]', r'[[Wikipedia:共同翻訳依頼/\1|\1]]', oldpage.text)
    oldpage.text = re.sub(r'\[\[ */ *(.+?) *\]\]', r'[[Wikipedia:共同翻訳依頼/\1]]', oldpage.text)
    summary2 = 'Botによる: [[特別:固定リンク/{}|{}の{}時点の版]]から{}節転記'.format(
        kyoudou.latest_revision_id,
        kyoudou_title,
        iso8601toja(kyoudou.editTime()),
        old_request_count,
    )
    if show_diff:
        pywikibot.showDiff(oldpage_oldtext, oldpage.text)
    oldpage.save(summary=summary2, minor=False)

    summary1 = 'Botによる: [[{}]]へ{}節転記'.format(
        old_title,
        old_request_count,
    )
    if show_diff:
        pywikibot.showDiff(kyoudou_oldtext, kyoudou.text)
        pywikibot.output(summary1)
    kyoudou.save(summary=summary1, minor=False)

if __name__ == "__main__":
    main()
