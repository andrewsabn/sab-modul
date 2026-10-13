"""Targeted measurements for accepted Fable drawing and shaping findings."""
import argparse, hashlib, json, math, unicodedata
from pathlib import Path
from fontTools.ttLib import TTFont
from verify_code import bbox
from verify_stage2 import shape
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--font-dir',type=Path,default=ROOT/'source/stage6-masters');p.add_argument('--output',type=Path,default=ROOT/'checks/fable/corrections.json');args=p.parse_args()
rows=[]
for path in sorted(args.font_dir.glob('*.ttf')):
 f=TTFont(path);cm=f.getBestCmap();bs={ch:bbox(f,cm[ord(ch)]) for ch in '/\\`\"\'<>^-│'}
 checks={
  'slashes_height':all(bs[c][3]-bs[c][1]>=850 for c in '/\\'),
  'quote_tops':abs(bs['"'][3]-bs["'"][3])<=1,
  'hyphen_width':bs['-'][2]-bs['-'][0]>=260,
  'caret_raised':bs['^'][1]>=300 and bs['^'][3]>=700,
  'angle_width':all(bs[c][2]-bs[c][0]>=400 for c in '<>'),
  'terminal_1_55':bs['│'][3]-bs['│'][1]>=1550,
  'vendor':f['OS/2'].achVendID=='SABT',
 }
 shaped=shape(path,'j\u0301','calt=0')
 checks['soft_dotted_j']=shaped[0]['g']==f.getGlyphID(cm[0x237]) and [x['ax'] for x in shaped]==[600,0]
 for base,expected in [('і',cm[0x131]),('ј',cm[0x237]),('į',cm[0x12F]+'.dotless')]:
  sh=shape(path,base+'\u0301','calt=0')
  checks['soft_dotted_'+base]=sh[0]['g']==f.getGlyphID(expected) and [x['ax'] for x in sh]==[600,0]
 for text in ['ι\u0308\u0301','i\u0307\u0301']:
  sh=shape(path,text,'calt=0');marks=[(g,bbox(f,f.getGlyphOrder()[g['g']])) for g in sh if g['ax']==0]
  checks['stacked_'+text]=len(marks)==2 and marks[1][0]['dy']+marks[1][1][1] >= marks[0][0]['dy']+marks[0][1][3]+39

 accents=[]
 for cp,name in cm.items():
  d=unicodedata.normalize('NFD',chr(cp))
  if cp not in (0x010F,0x013D,0x013E,0x0165) and len(d)==2 and all(ord(c) in cm for c in d):
   g=f['glyf'][name]
   accents.append(g.isComposite() and g.components[-1].glyphName==cm[ord(d[1])])
 checks['shared_canonical_marks']=bool(accents) and all(accents)
 rows.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),checks=checks,bounds=bs,accent_count=len(accents)))
 print(path.name,[key for key,ok in checks.items() if not ok],flush=True)
args.output.write_text(json.dumps({'status':'PASS' if rows and all(all(r['checks'].values()) for r in rows) else 'FAIL','fonts':rows},indent=2)+'\n')
raise SystemExit(0 if rows and all(all(r['checks'].values()) for r in rows) else 1)
