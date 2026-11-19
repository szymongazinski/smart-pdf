"""Forgiving page-range input, with strict bounds before expanding ranges."""
import re


def parse_page_ranges(text: str, count: int) -> list[int]:
    if count<1:
        raise ValueError('Dokument nie zawiera stron.')
    if len(text)>10000:
        raise ValueError('Wpisany zakres jest zbyt długi.')
    tokens=re.findall(r'[0-9]+|[-–—−]',text)
    if not tokens:
        raise ValueError('Wpisz numery stron, np. 11-19 i 20-35.')
    pages=set()
    index=0
    def number(token):
        if not token.isascii() or not token.isdecimal() or len(token)>12:
            raise ValueError('Myślnik musi łączyć dwa numery, np. 11-19.')
        value=int(token)
        if not 1<=value<=count:
            raise ValueError(f'Numery stron muszą należeć do zakresu 1-{count}.')
        return value
    while index<len(tokens):
        start=number(tokens[index])
        end=start
        index+=1
        if index<len(tokens) and tokens[index] in '-–—−':
            index+=1
            if index==len(tokens):
                raise ValueError('Dokończ zakres po myślniku, np. 11-19.')
            end=number(tokens[index])
            index+=1
            if end<start:
                raise ValueError('Początek zakresu nie może być większy od końca.')
        pages.update(range(start-1,end))
    return sorted(pages)


def remaining_pages(text: str, count: int, mode: str) -> list[int]:
    selected=parse_page_ranges(text,count)
    if mode=='keep':
        return selected
    if mode!='remove':
        raise ValueError('Wybierz pozostawienie albo usunięcie wskazanych stron.')
    selected=set(selected)
    result=[index for index in range(count) if index not in selected]
    if not result:
        raise ValueError('Dokument musi zachować przynajmniej jedną stronę.')
    return result


def format_page_ranges(indices: list[int]) -> str:
    """Compact, human-readable 1-based ranges in document order."""
    groups=[]
    for value in sorted(set(indices)):
        if groups and value==groups[-1][1]+1:
            groups[-1][1]=value
        else:
            groups.append([value,value])
    return ', '.join(str(a+1) if a==b else f'{a+1}-{b+1}' for a,b in groups)
