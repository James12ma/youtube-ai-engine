"""Conservative numerical consistency checks, not full semantic verification."""
from __future__ import annotations
import re

_WORD_TO_NUMBER = {'zero':'0','one':'1','two':'2','three':'3','four':'4','five':'5',
 'six':'6','seven':'7','eight':'8','nine':'9','ten':'10','eleven':'11',
 'twelve':'12','thirteen':'13','fourteen':'14','fifteen':'15',
 'sixteen':'16','seventeen':'17','eighteen':'18','nineteen':'19','twenty':'20'}
_NUM = re.compile(r'(?<![\w])\d+(?:[.,]\d+)*(?![\w])')

def numbers(text: str) -> set[str]:
    simplified=text.lower()
    for word,value in _WORD_TO_NUMBER.items():
        simplified=re.sub(r'\b'+word+r'\b',value,simplified)
    return {m.group().replace(',','') for m in _NUM.finditer(simplified)}
