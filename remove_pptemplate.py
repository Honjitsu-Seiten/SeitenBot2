# SeitenBot2 remove_pptemplate.py

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
from contextlib import suppress
import pywikibot
from pywikibot.pagegenerators import GeneratorFactory
from pywikibot.bot import SingleSiteBot, CurrentPageBot
from pywikibot.exceptions import Error
import mwparserfromhell

levelnum = lambda level: ("all", "autoconfirmed", "extendedconfirmed", "sysop").index(level)

class RemovePpBot2(SingleSiteBot, CurrentPageBot):

    update_options = {
        'summary': "Botによる: 保護テンプレートの除去"
    }

    pattern1 = re.compile(r"<noinclude></noinclude>")
    pattern2 = re.compile(r"/\*[ 　\t]*\*/\n?")

    pptemplates = {
        "Pp": "edit",
        "Pp-move": "move",
        "Pp-upload": "upload",
        "Pp-dispute": "edit",
        "Pp-move-dispute": "move",
        "Pp-vandalism": "edit",
        "Pp-move-vandalism": "move",
        "Pp-office": "edit",
        "Pp-reset": "edit",
        "Pp-office-dmca": "edit",
        "Pp-template": "edit",
        "Pp-semi-indef": "edit",
        "保護運用": "edit",
        "保護": "edit",
        "半保護": "edit",
        "拡張半保護": "edit",
        "移動保護" : "move",
        "移動拡張半保護" : "move",
    }

    def setup(self):
        pptemplates_redirect = {}
        for template, action in self.pptemplates.items():
            templatepage = pywikibot.Page(source=self.site, title=template, ns=10)
            for redirect in self.site.pagebacklinks(templatepage, filter_redirects=True, namespaces=10):
                pptemplates_redirect[redirect.title(with_ns=False)] = action
        self.pptemplates.update(pptemplates_redirect)

    def skip_page(self, page):
        if page.namespace() in ('利用者:', 'Mediawiki:', 'モジュール:'):
            return True
        if page.title() in (
        "Wikipedia:サンドボックス",
        "Wikipedia‐ノート:サンドボックス",
        "Template:テスト",
        "Template:X1",
        "Template:X2"):
            return True
        return super().skip_page(page)

    def treat_page(self):
        """Treat page."""
        page = self.current_page
        title = page.title()
        ns = page.namespace()
        try:
            pagetext = page.get(get_redirect=True)
            protection = page.protection()
        except Error as e:
            pywikibot.error(str(e))
            return
        needmovetemplate = needuploadtemplate = False
        editlevel = protection.get("edit", ("all",))[0]
        pywikibot.output("edit: " + editlevel)
        movelevel = protection.get("move", ("all",))[0]
        pywikibot.output("move: " + movelevel)
        if (movelevel != "autoconfirmed") and (levelnum(editlevel) < levelnum(movelevel)):
            needmovetemplate = True
        uploadlevel = protection.get("upload", ("all",))[0]
        if page.namespace() == "ファイル:":
            pywikibot.output("move: " + movelevel)
            if (uploadlevel != "autoconfirmed") and (levelnum(editlevel) < levelnum(uploadlevel)):
                needuploadtemplate = True
        wikicode = mwparserfromhell.parse(pagetext)
        removed = False
        for template in wikicode.filter_templates():
            for pptemplate, action in self.pptemplates.items():
                if template.name.matches(pptemplate):
                    pywikibot.output(str(template.name))
                    with suppress(ValueError):
                        action = template.get('action').value
                    if action == "edit" and editlevel == "all" \
                    or action == "move" and not needmovetemplate \
                    or action == "upload" and not needuploadtemplate:
                        with suppress(ValueError):
                            wikicode.remove(str(template) + "\n")
                            removed = True
                        with suppress(ValueError):
                            wikicode.remove(template)
                            removed = True
        new_text = str(wikicode)

        if removed:
            if  (ns == "Template:") and title.endswith(".css"):
                new_text=self.pattern2.sub("", new_text)
            else:
                new_text=self.pattern1.sub("", new_text)
            self.put_current(
                new_text=new_text,
                summary=self.opt.summary,
                show_diff=not self.opt.always,
                ignore_save_related_errors=True
            )
        else:
            page.touch()

def main(*args):
    local_args = pywikibot.handle_args(args)
    generator_factory = GeneratorFactory()
    local_args = generator_factory.handle_args(local_args)
    options = {}

    site = pywikibot.Site(code="ja", fam="wikipedia")
    if not site.logged_in():
        site.login()

    for arg in local_args:
        arg, _, value = arg.partition(':')
        option = arg[1:]
        options[option] = True

    generator = generator_factory.getCombinedGenerator(preload=True)

    if generator:
        bot = RemovePpBot2(generator=generator, site=site, **options)
        bot.run()
    else:
        pywikibot.showHelp()

if __name__ == "__main__":
    main()
