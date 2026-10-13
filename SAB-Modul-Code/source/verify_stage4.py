"""Check every contextual operator, restoration, cell count and advance with HarfBuzz."""
from pathlib import Path
import hashlib, json, subprocess, re
from fontTools.ttLib import TTFont
from code_operators import OPERATORS
ROOT = Path(__file__).resolve().parents[1]


def shape(path, text, features):
    command = ['hb-shape', str(path), '--text='+text, '--features='+features, '--output-format=json']
    run = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(run.stdout)


def main(font_dir=ROOT/'source/stage4-masters', output=ROOT/'checks/stage4-shaping.json'):
    records=[]
    corpus = OPERATORS + ['!= === <= >= => -> :: ;; || && ?? ?. .. ... *= /= %= <> <<= >>=',
                         'www fi ff ffi office', '----> !=== <<===', 'x->y != z && true',
                         '<<=', '>>=', '<=>', '<==', '==>', '<->', '<-->', '-->', '<!--', '---', '====', '<|>']
    for path in sorted(font_dir.glob('*.ttf')):
        f=TTFont(path)
        checks=[]
        record=dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),checks=checks,status='IN_PROGRESS')
        records.append(record)
        for text in corpus:
            off=shape(path,text,'-calt,-ss10')
            on=shape(path,text,'calt,-ss10')
            restored=shape(path,text,'calt,ss10')
            onlyss=shape(path,text,'-calt,ss10')
            checks.append(dict(text=text,disabled=off,enabled=on,restored=restored,ss10_only=onlyss,status='IN_PROGRESS'))
            output.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
            assert off==restored==onlyss,(path.name,text,'ss10 restore failed')
            assert len(off)==len(on)==len(text),(path.name,text,'cell count changed')
            assert all(g['ax']==600 and g['ay']==0 for g in on+off),(path.name,text,'advance')
            if text in OPERATORS:
                index=OPERATORS.index(text)
                assert [g['g'] for g in on]==[f'code.op{index}.{i}' for i in range(len(text))],(path.name,text,on)
            if text=='www fi ff ffi office':
                assert off==on,(path.name,'letter substitution')
            expected=[]
            for token in re.findall(r'[!%&*+\-./:<=>?^|~]+|[^!%&*+\-./:<=>?^|~]',text):
                if token in OPERATORS:
                    index=OPERATORS.index(token)
                    expected.extend(f'code.op{index}.{i}' for i in range(len(token)))
                else:expected.extend(f.getBestCmap()[ord(c)] for c in token)
            assert [g['g'] for g in on]==expected,(path.name,text,'whole-operator-token',expected,on)
            checks[-1]['expected']=expected
            checks[-1]['status']='PASS'
        tags={r.FeatureTag for r in f['GSUB'].table.FeatureList.FeatureRecord}
        assert 'calt' in tags and 'ss10' in tags and 'dlig' not in tags
        assert 'kern' not in f
        for lookup in f['GPOS'].table.LookupList.Lookup:
            assert lookup.LookupType!=2,(path.name,'GPOS PairPos')
            if lookup.LookupType==9:
                assert all(st.ExtensionLookupType!=2 for st in lookup.SubTable),(path.name,'extension PairPos')
        record['status']='PASS'
        output.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        print(path.name, len(checks), 'cases PASS',flush=True)
    assert len(records)==10
    output.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--font-dir',type=Path,default=ROOT/'source/stage4-masters');parser.add_argument('--output',type=Path,default=ROOT/'checks/stage4-shaping.json');args=parser.parse_args()
    try:main(args.font_dir,args.output)
    except Exception as error:
        output=args.output
        if output.exists():
            records=json.loads(output.read_text())
            if records:records[-1].update(status='FAIL',error=repr(error))
            output.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        raise
