# SeitenBot2 botreq_sendlog.py

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


import collections
import io
import re
from datetime import UTC, datetime, timedelta

import pywikibot

weekday_ja = ("月", "火", "水", "木", "金", "土", "日")
wait = 3


def iso8601toja(timestamp):
    return (
        f"{timestamp.year}年{timestamp.month}月{timestamp.day}日 ({weekday_ja[timestamp.weekday()]})"
        + timestamp.strftime(" %H:%M (UTC)")
    )


def main(*args):
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    @param args: command line arguments
    @type args: list of unicode
    """
    show_diff = False

    for arg in pywikibot.handle_args(args):
        arg, _, _value = arg.partition(":")
        option = arg.partition("-")[2]
        # bot options
        if option in ("showdiff",):
            show_diff = True
        else:
            pywikibot.output(f"Disregarding unknown argument {arg}.")

    site = pywikibot.Site(code="ja", fam="wikipedia")
    if not site.logged_in():
        site.login()

    botreq_title = "Wikipedia:Bot作業依頼"
    botreq = pywikibot.Page(site, botreq_title)
    if not botreq.exists():
        pywikibot.error(f"{botreq_title} doesn't exist.")
        return False
    botreq_text_list = re.split(r"(==[^=].+?==\n)", botreq.text)
    it = iter(botreq_text_list)
    try:
        next(it)
    except StopIteration:
        pywikibot.output(f"There is no request in {botreq_title}")
        return True
    closed_pattern = re.compile(
        r"\{\{\s*(?:(?:解決)?済み|失効)\s*\|.*?(\d{4})年(\d{1,2})月(\d{1,2})日 \([月火水木金土日]\) (\d{2}):(\d{2}) \(UTC\)\s*\}\}"
    )
    sendlog_dict = collections.defaultdict(list)
    while True:
        try:
            section_title = next(it)
            section_content = next(it)
            match = closed_pattern.search(section_content)
            if match:
                closed_datetime = datetime(*map(int, match.groups()), tzinfo=UTC)
                now = datetime.now(UTC)
                if (now - closed_datetime) > timedelta(days=wait):
                    sendlog_dict[match.group(1, 2)].append(
                        (section_title, section_content)
                    )
        except StopIteration:
            break
    if not sendlog_dict:
        pywikibot.output("Don't need to do anything.")
        return True
    for k, li in sendlog_dict.items():
        log_title = "Wikipedia:Bot作業依頼/過去ログ/{}年{}月".format(*k)
        logpage = pywikibot.Page(site, log_title)
        logpageoldtext = logpage.text
        newpage = not logpage.exists()
        with io.StringIO(logpage.text.rstrip("\r\n")) as stream:
            stream.seek(0, io.SEEK_END)
            if newpage:
                stream.write("{{Archives|Wikipedia:Bot作業依頼}}\n\n")
                newpage = True
            else:
                stream.write("\n\n")
            for t in li:
                stream.write(t[0])
                botreq_text_list.remove(t[0])
                stream.write(t[1].strip())
                botreq_text_list.remove(t[1])
                stream.write("\n\n")
            logpage.text = stream.getvalue()
        oldtext = botreq.text
        botreq.text = "".join(botreq_text_list)

        summary2 = f"Botによる: [[特別:固定リンク/{botreq.latest_revision_id}|Wikipedia:Bot作業依頼の{iso8601toja(botreq.latest_revision.timestamp)}時点の版]]から{len(li)}節転記"
        if newpage:
            summary2 += " +{{Archives}}"
        if show_diff:
            pywikibot.showDiff(logpageoldtext, logpage.text)
        logpage.save(summary=summary2, minor=False)

        summary1 = f"Botによる: [[{log_title}]]へ{len(li)}節転記"
        if show_diff:
            pywikibot.showDiff(oldtext, botreq.text)
        botreq.save(summary=summary1, minor=False)


if __name__ == "__main__":
    main()
