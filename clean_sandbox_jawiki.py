import re
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
        if option == 'showdiff':
            options[option] = True
        else:
            options[option] = value

    revlimit  = int(options.get('revlimit', 4500))
    assert (revlimit >= 1 and revlimit <= 5000)

    site = pywikibot.Site(code="ja", fam="wikipedia")
    if not site.logged_in():
        site.login()

    page = pywikibot.Page(site, 'Wikipedia:サンドボックス')
    if page.exists():
        revcount = len(tuple(page.revisions()))
    else:
        revcount = 0
    try:
        deletedrevcount = len(next(site.deletedrevs(titles=page, prop=['ids'])).get('revisions', []))
    except StopIteration:
        deletedrevcount = 0
    total = revcount + deletedrevcount
    pywikibot.log('合計{}版'.format(total))

    if total >= revlimit:
        page2 = pywikibot.Page(site, 'Wikipedia:管理者伝言板/各種初期化依頼')
        if not page2.exists():
            pywikibot.error('"Wikipedia:管理者伝言板/各種初期化依頼"が存在しません')
        if ('=== サンドボックスの貝塚送り ===' in page2.text):
            return
        oldtext = page2.text
        newtext = '=== サンドボックスの貝塚送り ===\n[[Wikipedia:サンドボックス]]の版数が削除済みのものを含めて{}以上ありますので、貝塚送りをお願いします。--~~~~\n\n'.format(revlimit)
        if m := re.match(r'^(.*?\n\n?)(\=\= *ビジュアルエディター\/sandboxの初期化依頼 *\=\=.*)$', page2.text, re.S):
            page2.text = m.group(1) + newtext + m.group(2)
        else:
            page2.text += newtext
        if options.get('showdiff', False):
            pywikibot.showDiff(oldtext, page2.text, context=2)
        page2.save(summary='Botによる： サンドボックスの貝塚送りを依頼', minor=False, botflag=False)
    else:
        page.text = '{{subst:サンドボックス}}'
        summary = options.pop('summary', 'Botによる： 砂場ならし（削除済みを含めた版数: {}）'.format('5000以上' if total >= 5000 else total))
        pywikibot.output(summary)
        page.save(summary=summary, minor=False)

if __name__ == "__main__":
    main()
