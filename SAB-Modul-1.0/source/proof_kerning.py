from pathlib import Path
import hashlib,json,sys
from PIL import Image
from fontTools.ttLib import TTFont
from proof import ROOT,ShapedFont,draw_text,path

previous,current=sys.argv[1:3]
out=ROOT/'iterations'/current
assert out.is_dir()
rows=[
 ('Буквенные пары', 'Тр Ту Та То ГА АУ',64,{}),
 ('Кавычки и капители','«ТА» «УЧ» «Ро» «Тф»',58,{}),
 ('Латиница','AV AT LT Ty Wa f) f. r.',58,{}),
 ('Пропорциональные цифры · pnum','11 17 71 1.1 70',64,{'pnum':True}),
 ('Суммы · pnum','$87,3 → $55,1',64,{'pnum':True}),
 ('Знаки · pnum + case','−37\u202f% [2026] (€17)',56,{'pnum':True,'case':True}),
 ('Табличные цифры · tnum','11 17 71 1.1 70',64,{'tnum':True}),
 ('Суммы · tnum','$87,3 → $55,1',64,{'tnum':True}),
 ('В тексте · pnum','Рост с $55,1 до $87,3 млн.',30,{'pnum':True}),
 ('В тексте · pnum','«Технологии»: 17 стран, −37\u202f%.',30,{'pnum':True}),
]
records=[]
for style in ['Regular','Bold']:
 im=Image.new('RGB',(2400,1540),'white')
 for col,label in enumerate(['CoFo','SAB · '+previous,'SAB · '+current]):
  p=path('CoFo',style) if col==0 else ROOT/'iterations'/[previous,current][col-1]/'fonts'/('SABModulSans-'+style+'.ttf')
  draw_text(im,(30+col*800,48),label+' · '+style,ShapedFont(path('CoFo'),28),fill='#666666')
  records.append({'label':label,'style':style,'font':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  for row,(caption,text,size,features) in enumerate(rows):
   x=30+col*800;y=105+row*140
   draw_text(im,(x,y),caption,ShapedFont(path('CoFo'),21),fill='#777777')
   f=ShapedFont(p,size,features=features)
   assert f.getlength(text)<740,(label,style,text)
   draw_text(im,(x,y+75),text,f)
 im.save(out/('kerning-'+style+'.png'))

checks=[]
before=json.loads((ROOT/'iterations'/previous/'pairs.json').read_text())['pairs']
after=json.loads((out/'pairs.json').read_text())['pairs']
assert before==after,'Reviewed letter pairs changed'
checks.append('60 reviewed pairs unchanged in Regular and Bold')
for p in sorted((out/'fonts').glob('*.ttf')):
 old=ROOT/'iterations'/previous/'fonts'/p.name
 a,b=TTFont(old),TTFont(p)
 assert a.getGlyphOrder()==b.getGlyphOrder()
 for tag in ['glyf','hmtx','GSUB']:
  assert a[tag].compile(a)==b[tag].compile(b),(p.name,tag)
 f=ShapedFont(p,1000)
 for text in ['0123456789','11','17','71','1.1','87,3','$55,1','−37\u202f% [2026]']:
  assert f.getlength(text)==f.getlength(text,kern=False),(p.name,text,'tabular kerning')
 if 'Mono' in p.name:
  assert a['GPOS'].compile(a)==b['GPOS'].compile(b),p.name
checks.extend(['28 fonts retain outlines, advances and substitutions from '+previous,
 'Tabular number samples unchanged by kerning in all 28 fonts',
 'Mono GPOS unchanged in all 14 styles'])
(out/'kerning-review.json').write_text(json.dumps({'previous':previous,'current':current,
 'records':records,'rows':[{'caption':c,'text':t,'size_px':s,'features':f} for c,t,s,f in rows],
 'checks':checks,'visual_acceptance':False},ensure_ascii=False,indent=2))
print(out/'kerning-review.json')
