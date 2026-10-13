from PIL import Image
from proof import ROOT,font,draw_text,VARIABLE
import sys,json

out=ROOT/'iterations'/sys.argv[1]
assert out.is_dir()
assert json.loads((out/'measurements.json').read_text()).get('variable_candidate',False)==VARIABLE,'Proof mode differs from the main sheet'
lines=['" “ ” „ « » % ‰ № @','© ® ™ ¼ ½ ¾ ª º ± °','Ыы Ђђ Ћћ Ққ Ĳ Ŀ ŀ ŉ µ','§ đ ð ı i í ì î ï į ї ĵ','Ħ ₸ ₽ ¥ € G']
im=Image.new('RGB',(2400,2820),'white')
for section,(mono,style) in enumerate((m,s) for m in [False,True] for s in ['Regular','Bold','Black']):
 y=section*470
 for col,kind in enumerate(['CoFo','Original','Current']):
  x=25+col*800
  draw_text(im,(x,y+40),kind+' · '+('Mono' if mono else 'Sans')+' · '+style,font('CoFo',24),fill='#777777')
  for i,text in enumerate(lines):draw_text(im,(x,y+120+i*76),text,font(kind,52 if i<3 else 44,style,mono))
names=[arg for arg in sys.argv[2:] if arg!='--variable']
target=out/(names[0] if names else 'symbols.png')
im.save(target)
print(target)
