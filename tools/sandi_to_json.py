#!/usr/bin/env python3
"""Конвертує YML-вивантаження з b2b-sandi.com.ua у data/<brand>.json для catalog.html.

Використання:
    python3 tools/sandi_to_json.py шлях/до/вивантаження.xml data/qtap.json
"""
import json, re, sys
import xml.etree.ElementTree as ET

# Порядок категорій у каталозі; «Душова програма» вливаємо у «Змішувачі»
ORDER = ['Змішувачі', 'Кераміка', 'Душові кабіни та бокси', 'Інсталяції',
         'Сифони та трапи', 'Дзеркала', 'Аксесуари']
MERGE = {'Душова програма': 'Змішувачі'}
# Службові характеристики, які покупцю не потрібні
SKIP = {'Зверніть увагу', 'Версія каталогу', 'Кількість вантажних місць',
        'Вага брутто, кг', 'Габарити упаковки (ШхГхВ), мм', 'Бренд'}
MAX_IMG = 8


def main(src, dst):
    root = ET.parse(src).getroot()
    shop_date = root.get('date', '')
    cats = {c.get('id'): (c.text.strip(), c.get('parentId')) for c in root.iter('category')}

    def chain(cid):
        out = []
        while cid in cats:
            out.append(cats[cid][0])
            cid = cats[cid][1]
        return out[::-1]

    items, brand = [], ''
    for o in root.iter('offer'):
        ch = chain(o.findtext('categoryId'))
        if not ch:
            continue
        top = MERGE.get(ch[0], ch[0])
        kind = ch[1] if len(ch) > 1 else ''
        if kind == top:  # напр. «Інсталяції > Інсталяції»
            kind = ch[2] if len(ch) > 2 else ''
        kind = re.sub(r'\s*\(.*?\)$', '', kind)  # «Разом дешевше (Кераміка)» → «Разом дешевше»
        brand = brand or (o.findtext('vendor') or '').strip()
        pr = {}
        if kind:
            pr['Вид виробу'] = kind
        for p in o.findall('param'):
            n, v = p.get('name', '').strip(), (p.text or '').strip()
            if n and v and n not in SKIP and n not in pr:
                pr[n] = v
        desc = re.sub(r'\s*Версія каталогу:.*$', '', (o.findtext('description') or '').strip(), flags=re.S)
        sku = (o.findtext('model') or pr.get('Артикул') or o.get('id')).strip()
        try:
            price = round(float(o.findtext('price') or 0))
        except ValueError:
            price = 0
        it = {'id': o.get('id'), 'n': (o.findtext('name') or '').strip(), 'sku': sku, 'c': top,
              'p': price, 'a': o.get('available') == 'true',
              'img': [p.text.strip() for p in o.findall('picture') if p.text][:MAX_IMG], 'pr': pr}
        if desc:
            it['d'] = desc
        items.append(it)

    present = {it['c'] for it in items}
    categories = [c for c in ORDER if c in present] + sorted(present - set(ORDER))
    data = {'updated': shop_date, 'brand': brand, 'categories': categories, 'items': items}
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    print(f'{brand}: {len(items)} товарів, {sum(i["a"] for i in items)} в наявності → {dst}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
