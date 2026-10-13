"""Record measured delivery parameters; leave unsampled local strokes unverified."""
from pathlib import Path
import hashlib,json
from fontTools.ttLib import TTFont
from verify_code import bbox,stroke_widths
ROOT=Path(__file__).resolve().parents[1]
records=[]
for path in sorted((ROOT/'release/SAB-Modul-Code-1.0/TTF').glob('*.ttf')):
 f=TTFont(path);c=f.getBestCmap()
 axes={ch:(bbox(f,c[ord(ch)])[1]+bbox(f,c[ord(ch)])[3])/2 for ch in '-−=+'}
 stems={ch:stroke_widths(f,c[ord(ch)],y) for ch,y in [('H',175),('l',350),("'",600),('"',500),('+',400),('#',270)]}
 records.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'weight':f['OS/2'].usWeightClass,
 'italic':bool(f['post'].italicAngle),'operator_axes':axes,'normal_strokes':stems,
 'bounds':{ch:bbox(f,c[ord(ch)]) for ch in '-−=+.,;:()[]{}<>~*#%@&^'},
 'unsampled_local_strokes':['curly quotes','grave','diagonal operators','curved operators','%','&','@','^','~'],
 'tilde_centerline_amplitude':{'source_parameter':180,'measured_from_compiled_centerline':False}})
(ROOT/'checks/final-parameters.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('Recorded',len(records),'fonts; unsampled strokes explicitly listed')
