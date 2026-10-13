"""Build script subsets and compare their shaping to the complete variable fonts."""
from pathlib import Path
import hashlib,io,json,unicodedata,shutil
from fontTools import subset
from fontTools.ttLib import TTFont
import uharfbuzz as hb

ROOT=Path(__file__).resolve().parents[1]

def unicode_ranges(points):
 ranges=[]
 for cp in sorted(points):
  if ranges and cp==ranges[-1][1]+1:ranges[-1][1]=cp
  else:ranges.append([cp,cp])
 return ', '.join(f'U+{a:04X}'+(f'-{b:04X}' if b!=a else '') for a,b in ranges)

def shaping_font(font):
 font.flavor=None;data=io.BytesIO();font.save(data)
 return hb.Font(hb.Face(data.getvalue())),font.getGlyphOrder()

def shape(pair,text,weight,features):
 font,order=pair;font.scale=(1000,1000);font.set_variations({'wght':weight})
 b=hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(font,b,features)
 return [(order[g.codepoint],p.x_advance,p.y_advance,p.x_offset,p.y_offset) for g,p in zip(b.glyph_infos,b.glyph_positions)]

def build():
 out=ROOT/'WEB';out.mkdir(exist_ok=True);records=[];css=[];experimental_css=[]
 for family in ['Sans','Mono']:
  for italic in [False,True]:
   stem='SABModul'+family+('-Italic' if italic else '')+'[wght]'
   path=ROOT/'VF'/(stem+'.ttf');original=TTFont(path);cmap=original.getBestCmap();points=set(cmap)
   source_hash=hashlib.sha256(path.read_bytes()).hexdigest()
   checked=json.loads(path.with_suffix('.verification.json').read_text())
   assert checked['sha256']==source_hash,'Verify the current VF before subsetting'
   if family=='Sans':
    # One face keeps punctuation and letters in the same browser shaping run.
    filename=stem+'.woff2';shutil.copy2(path.with_suffix('.woff2'),out/filename)
    ranges=unicode_ranges(points)
    css.append("@font-face {\n  font-family: 'SAB Modul "+family+"';\n  font-style: "+('oblique 10deg' if italic else 'normal')+";\n  font-weight: 200 900;\n  font-display: swap;\n  src: url('./"+filename+"') format('woff2');\n  unicode-range: "+ranges+";\n}")
    records.append({'file':filename,'family':family,'style':'Oblique' if italic else 'Roman','script':'complete','characters':len(points),'case_closure_codepoints':[],'unicode_range':ranges,'bytes':(out/filename).stat().st_size,'sha256':hashlib.sha256((out/filename).read_bytes()).hexdigest(),'source':str(path.relative_to(ROOT)),'source_sha256':source_hash,'shaping_comparisons':0,'identical_to_verified_full_woff2':True})
   common={cp for cp in points if unicodedata.combining(chr(cp)) or chr(cp).isspace()}
   groups={'latin':{cp for cp in points if cp<=0xFF},
           'latin-ext':{cp for cp in points if 0x100<=cp<=0x24F or 0x1E00<=cp<=0x1EFF},
           'cyrillic':{cp for cp in points if 0x400<=cp<=0x52F}}
   groups['symbols']=points-set().union(*groups.values())-common
   full=shaping_font(original);covered=set()
   for script,primary in groups.items():
    wanted=primary|common;covered|=wanted
    requested=wanted.copy()
    while True:
     counterparts={ord(s) for cp in wanted for s in [chr(cp).lower(),chr(cp).upper(),chr(cp).title()] if len(s)==1 and ord(s) in points}
     if counterparts<=wanted:break
     wanted|=counterparts
    options=subset.Options();options.layout_features=['*'];options.name_IDs=['*'];options.name_languages=['*'];options.glyph_names=True;options.notdef_outline=True
    font=TTFont(path);subsetter=subset.Subsetter(options);subsetter.populate(unicodes=wanted);subsetter.subset(font)
    assert set(font.getBestCmap())==wanted,(stem,script,'Character coverage changed')
    assert font['name'].getDebugName(13),'License was removed'
    reduced=shaping_font(font)
    samples=[chr(cp) for cp in sorted(wanted)]
    samples+=[''.join(chr(cp) for cp in sorted(primary))]
    samples += [s for s in ['AVATAR Wa Ty 0171','Технологический руководитель банков','−37 % [2026]','a\u0301','е\u0308','и\u0306'] if set(map(ord,s))<=wanted]
    comparisons=0
    for weight in [200,250,400,550,700,800,900]:
     for features in [{'kern':True,'mark':True,'ccmp':True},{'kern':True,'mark':True,'ccmp':True,'pnum':True,'case':True}]:
      for sample in samples:
       assert shape(full,sample,weight,features)==shape(reduced,sample,weight,features),(stem,script,weight,sample,features)
       comparisons+=1
    filename=stem+'-'+script+'.woff2';font.flavor='woff2';font.save(out/filename)
    ranges=unicode_ranges(requested)
    rule=("@font-face {\n  font-family: 'SAB Modul "+family+"';\n  font-style: "+('oblique 10deg' if italic else 'normal')+";\n  font-weight: 200 900;\n  font-display: swap;\n  src: url('./"+filename+"') format('woff2');\n  unicode-range: "+ranges+";\n}")
    experimental_css.append(rule.replace("SAB Modul "+family+"'","SAB Modul "+family+" Subsets'"))
    if family=='Mono':css.append(rule)
    records.append({'file':filename,'family':family,'style':'Oblique' if italic else 'Roman','script':script,'characters':len(wanted),'case_closure_codepoints':sorted(wanted-requested),'unicode_range':ranges,'bytes':(out/filename).stat().st_size,'sha256':hashlib.sha256((out/filename).read_bytes()).hexdigest(),'source':str(path.relative_to(ROOT)),'source_sha256':source_hash,'shaping_comparisons':comparisons})
    print(filename,records[-1]['bytes'],'bytes;',comparisons,'shaping comparisons',flush=True)
   assert covered==points,(stem,'Subset union misses characters')
 (out/'fonts.css').write_text('\n\n'.join(css)+'\n')
 (out/'fonts-subsets.css').write_text('/* Experimental: Sans kerning can break across file boundaries. Use fonts.css for normal text. */\n'+'\n\n'.join(experimental_css)+'\n')
 (out/'verification.json').write_text(json.dumps({'files':records,'shared_characters':'combining marks and spaces are repeated for shaping clusters','payload_bytes_per_family':{f:sum(r['bytes'] for r in records if r['family']==f) for f in ['Sans','Mono']},'visual_acceptance':False,'browser_cross_subset_kerning_verified':False,'recommended_css':'fonts.css','recommended_loading':'Sans complete variable WOFF2; Mono script subsets','experimental_css':'fonts-subsets.css','experimental_sans_cross_subset_kerning':'Known mismatch in Chromium 154 on macOS; retained for diagnosis','recommended_css_browser_verified':False},indent=2))

if __name__=='__main__':build()
