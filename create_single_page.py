# SeitenBot2 create_single_page.py

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


import re
from datetime import datetime, timezone, timedelta
import pywikibot

def main(*args):
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    @param args: command line arguments
    @type args: list of unicode
    """
    options = {}

    for arg in pywikibot.handle_args(args):
        arg, _, value = arg.partition(':')
        option = arg.partition('-')[2]
        # bot options
        if option in ('format', 'showdiff', 'noredirect'):
            options[option] = True
        else:
            options[option] = value

    site = pywikibot.Site(code="ja", fam="wikipedia")
    if not site.logged_in():
        site.login()

    hoursdelta = int(options.pop('hoursdelta', 9))
    dt = datetime.now(tz=timezone(timedelta(hours=hoursdelta)))
    format_dict = {
        'year': dt.year,
        'month': dt.month,
        'day': dt.day,
    }
    f = open(options['file'], mode='r', encoding='utf-8')
    str = f.read()
    f.close()
    match = re.match(r"'''([^\n]+)'''[\r\n]+(.+)", str, re.S)
    if not match:
        pywikibot.error('Invalid file format')
        return False
    del str
    title = match.group(1)
    format = options.pop('format', False)
    if format:
        title = title.format(**format_dict)
    page = pywikibot.Page(site, title)
    if page.exists():
        if options.pop('noredirect', False):
            pywikibot.error('Page "{}" exists.'.format(title))
            return True
        elif not page.isRedirectPage():
            pywikibot.error('Page "{}" exists and it\'s not redirect.'.format(title))
            return True
    page.text = match.group(2).strip()
    if format:
        page.text = page.text.format(**format_dict)
    summary = options.pop('summary', 'Botによる：ページの作成')
    show_diff = options.pop('showdiff', False)
    if show_diff:
        pywikibot.showDiff('', page.text)
    page.save(summary=summary, minor=False, createonly=True)

if __name__ == "__main__":
    main()
