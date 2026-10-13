from pathlib import Path
import json,hashlib,unicodedata
from fontTools.ttLib import TTFont
import uharfbuzz as hb

ROOT=Path(__file__).resolve().parents[1]
REQUIRED=set(range(0x400,0x460))|set(map(ord,'‰\u202f₸₽$«»„“‘’–—−→←↑↓×·…№©®™§¶°‹›áéíóúñü¿¡ßäö'))|set(range(0x100,0x180))

def shape(path,text,features=None):
 f=hb.Font(hb.Face(path.read_bytes()));f.scale=(1000,1000)
 b=hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(f,b,features)
 return [(g.codepoint,p.x_advance,p.x_offset,p.y_offset) for g,p in zip(b.glyph_infos,b.glyph_positions)]

files=[];names=set();failures=[]
for fmt in ['TTF','OTF','WOFF2']:
 paths=sorted((ROOT/fmt).glob('*.'+fmt.lower()))
 if len(paths)!=28:failures.append(f'{fmt}: expected 28 files, found {len(paths)}')
 for path in paths:
  f=TTFont(path);cmap=f.getBestCmap();errors=[];mono='Mono-' in path.name
  missing=sorted(REQUIRED-set(cmap))
  if missing:errors.append('Missing codepoints '+','.join('%04X'%x for x in missing))
  h=f['hhea'];o=f['OS/2']
  if (h.ascent,h.descent,h.lineGap,o.sTypoAscender,o.sTypoDescender,o.sTypoLineGap)!=(1040,-320,0,1040,-320,0):errors.append('Vertical metrics')
  if not o.fsSelection&128:errors.append('useTypoMetrics')
  if (o.usWinAscent,o.usWinDescent)!=(1040,320):errors.append('Windows metrics')
  features={r.FeatureTag for tag in ['GSUB','GPOS'] if tag in f for r in f[tag].table.FeatureList.FeatureRecord}
  if not {'ccmp','mark','tnum','pnum','case'}.issubset(features):errors.append('OpenType features')
  if mono:
   if (o.panose.bFamilyType,o.panose.bProportion)!=(2,9):errors.append('Mono PANOSE')
   if not f['post'].isFixedPitch:errors.append('Mono fixed pitch flag')
   if h.advanceWidthMax!=max(v[0] for v in f['hmtx'].metrics.values()):errors.append('advanceWidthMax')
   if o.xAvgCharWidth!=620:errors.append('Mono xAvgCharWidth')
   if 'kern' in features:errors.append('Mono must have no kerning')
   for cp,gn in cmap.items():
    expected=0 if unicodedata.combining(chr(cp)) else 620
    if f['hmtx'][gn][0]!=expected:errors.append(f'Mono advance {gn}');break
  elif 'kern' not in features:errors.append('Sans kerning missing')
  for cp,gn in cmap.items():
   parts=unicodedata.normalize('NFD',chr(cp))
   if len(parts)==2 and chr(cp) not in 'ďĽľť' and all(ord(c) in cmap for c in parts):
    if f['hmtx'][gn][0]!=f['hmtx'][cmap[ord(parts[0])]][0]:errors.append('Accent changes base advance '+chr(cp))
  for base,accent in [('и','й'),('И','Й'),('и','ѝ'),('n','ñ'),('е','ё')]:
   glyphset=f.getGlyphSet()
   from fontTools.pens.boundsPen import BoundsPen
   a=BoundsPen(glyphset);b=BoundsPen(glyphset)
   glyphset[cmap[ord(base)]].draw(a);glyphset[cmap[ord(accent)]].draw(b)
   if b.bounds[3]<=a.bounds[3]+15:errors.append('Accent lost '+accent)
  if fmt=='TTF':
   for c in 'ďĽľť':
    g=f['glyf'][cmap[ord(c)]]
    if not g.isComposite() or 'caron.alt' not in [p.glyphName for p in g.components]:errors.append('Missing side caron '+c)
   if any(f['glyf'][cmap[ord(c)]].numberOfContours!=2 for c in 'eе'):errors.append('Closed e aperture or missing counter')
   for c,expected in {'%':5,'‰':7,'№':4,'@':2,'©':3,'®':4,'§':2,'đ':2,'ð':2,'ŀ':2,'Ħ':2,'₸':2,'₽':2,'¥':1,'€':1,'G':1}.items():
    if f['glyf'][cmap[ord(c)]].numberOfContours!=expected:errors.append('Symbol counters or disconnected parts '+c)
   for text in ['ñ','ё','й']:
    if shape(path,text)!=shape(path,unicodedata.normalize('NFD',text)):errors.append('Composition '+text)
   if shape(path,'[2026]',{'case':True})==shape(path,'[2026]',{'case':False}):errors.append('case inactive')
   prop=[p[1] for p in shape(path,'0123456789',{'pnum':True})]
   if (len(set(prop))==1)!=mono:errors.append('pnum advances')
   if not {'prep','fpgm','cvt '}.issubset(f.keys()):errors.append('Hinting missing')
   if not f['head'].flags&8:errors.append('Integer PPEM flag')
  ps=f['name'].getDebugName(6)
  if (fmt,ps) in names:errors.append('Duplicate PostScript name')
  names.add((fmt,ps))
  if f['name'].getDebugName(9)!='SAB Type, 2026':errors.append('Designer')
  if not f['name'].getDebugName(13):errors.append('License')
  record={'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'characters':len(cmap),'features':sorted(features),'errors':errors}
  files.append(record);failures.extend(path.name+': '+e for e in errors)
report={'implemented_checks_passed':not failures,'failures':failures,'files':files,'unverified':['visual acceptance by owner','blind vote with three reviewers','600-word reading test with two readers','Windows Chrome raster at 12/14/16/18 px','variable fonts and variable WOFF2 size target','web unicode-range subsets','fontbakery all delivered files']}
(ROOT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'files':len(files),'failures':failures},ensure_ascii=False,indent=2))
raise SystemExit(bool(failures))
