from pathlib import Path
import math, unicodedata, json, zipfile
from shapely.geometry import LineString, LinearRing, Point, Polygon, box as rectangle
from shapely.ops import unary_union
from shapely import set_precision, make_valid
from shapely.affinity import affine_transform
from shapely.geometry.polygon import orient
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import OVERLAP_COMPOUND
from fontTools.otlLib.builder import buildStatTable

ROOT=Path(__file__).resolve().parents[1]
VARIANTS={'SAB Modul':(.91,1.0)}
WEIGHTS={'Thin':(200,56),'Light':(300,70),'Regular':(400,80),'Medium':(500,97),'SemiBold':(600,115),'Bold':(700,134),'Black':(900,161)}
MONO_ADVANCE=620
XHEIGHT=500
PASS=26

def curve(start,*segments):
    pts=[start]
    for p1,p2,p3 in segments:
        p0=pts[-1]
        for j in range(1,25):
            t=j/24; u=1-t
            pts.append((u*u*u*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t*t*t*p3[0],u*u*u*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t*t*t*p3[1]))
    return pts

def ellipse(cx,cy,rx,ry,start=0,end=360,power=2):
    pts=[]
    for i in range(97):
        a=math.radians(start+(end-start)*i/96)
        co,si=math.cos(a),math.sin(a)
        pts.append((cx+rx*math.copysign(abs(co)**(2/power),co),cy+ry*math.copysign(abs(si)**(2/power),si)))
    if end-start==360: pts[-1]=pts[0]
    return pts

# Each entry contains independently drawn centerlines in a 1000-unit em.
# Closed contours are expanded and united; no reference-font outlines are read.
def alphabet(variant,mono=False):
    d={}; box=2.18 if variant=='SAB Modul' else 2
    def put(ch,w,*paths): d[ch]=(w,list(paths))
    def oval(w,h=700): return ellipse(w/2,h/2,w/2,h/2,power=box)
    def C(w,h=700): return ellipse(w/2,h/2,w/2,h/2,30,330,power=box)
    put('A',510,[(0,0),(255,700),(510,0)],[(92,245),(418,245)])
    put('B',470,[(0,0),(0,700)],curve((0,700),((630,775),(610,350),(0,365))),curve((0,365),((660,430),(650,-90),(0,0))))
    put('C',505,C(505))
    put('D',500,[(0,0),(0,700)],curve((0,700),((665,765),(665,-65),(0,0))))
    put('E',430,[(430,700),(0,700),(0,0),(430,0)],[(0,350),(365,350)])
    put('F',420,[(420,700),(0,700),(0,0)],[(0,370),(355,370)])
    garc=C(520)
    put('G',520,garc+[(garc[-1][0],345),(300,345)])
    put('H',500,[(0,0),(0,700)],[(500,0),(500,700)],[(0,350),(500,350)])
    put('I',260 if mono else 0,[(130 if mono else 0,0),(130 if mono else 0,700)],*([[(0,700),(260,700)],[(0,0),(260,0)]] if mono else []))
    put('J',355,curve((355,700),((355,700),(355,250),(355,180)),((355,-65),(0,-65),(0,180))))
    put('K',495,[(0,0),(0,700)],[(495,700),(0,285)],[(185,440),(505,0)])
    put('L',405,[(0,700),(0,0),(405,0)])
    put('M',625,[(0,0),(0,700),(312,170),(625,700),(625,0)])
    put('N',510,[(0,0),(0,700),(510,0),(510,700)])
    put('O',520,oval(520))
    put('P',460,[(0,0),(0,700)],curve((0,700),((650,785),(620,280),(0,355))))
    put('Q',520,oval(520),[(310,175),(555,-65)])
    put('R',490,[(0,0),(0,700)],curve((0,700),((650,785),(620,280),(0,355))),[(220,355),(505,0)])
    put('S',460,curve((445,600),((310,795),(0,690),(5,530)),((5,350),(445,370),(450,165)),((460,-60),(105,-65),(0,100))))
    put('T',490,[(0,700),(490,700)],[(245,700),(245,0)])
    put('U',500,curve((0,700),((0,700),(0,300),(0,220)),((0,-90),(500,-90),(500,220)),((500,300),(500,700),(500,700))))
    put('V',500,[(0,700),(250,0),(500,700)])
    put('W',760,[(0,700),(175,0),(380,560),(585,0),(760,700)])
    put('X',490,[(0,700),(490,0)],[(0,0),(490,700)])
    put('Y',510,[(0,700),(255,350),(510,700)],[(255,350),(255,0)])
    put('Z',460,[(0,700),(460,700),(0,0),(460,0)])
    # Lowercase has its own proportions and joins.
    if variant=='SAB Orbita':
        put('a',430,oval(430,510),[(430,510),(430,0)])
    else:
        put('a',405,curve((20,435),((140,575),(405,530),(405,350)),((405,240),(405,100),(405,0))),curve((405,275),((210,340),(-20,270),(0,120)),((25,-75),(310,-40),(405,160))))
    put('b',440,[(0,0),(0,720)],oval(440,510))
    put('c',410,C(410,510))
    put('d',440,oval(440,510),[(440,0),(440,720)])
    put('e',425,curve((425,255),((425,420),(350,510),(215,510)),((80,510),(0,415),(0,255)),((0,90),(80,0),(215,0)),((310,0),(390,55),(400,95))),[(0,255),(425,255)])
    put('f',275,curve((80,0),((80,150),(80,510),(80,570)),((80,755),(235,765),(285,690))),[(0,505),(255,505)])
    if variant=='SAB Forma':
        put('g',420,ellipse(210,333,190,177),curve((40,200),((-40,80),(70,60),(220,65)),((565,85),(520,-220),(200,-210)),((-65,-220),(-70,-15),(70,50))),[(350,475),(470,515)])
    else:
        put('g',430,oval(430,510),curve((430,510),((430,250),(430,0),(430,-40)),((430,-260),(120,-265),(20,-160))))
    put('h',430,[(0,0),(0,720)],curve((0,330),((40,570),(430,605),(430,305)),((430,210),(430,100),(430,0))))
    put('i',0,[(0,0),(0,510)],[(0,680),(0,681)])
    put('j',120,curve((120,510),((120,350),(120,-35),(120,-55)),((120,-245),(20,-250),(-70,-200))),[(120,680),(120,681)])
    put('k',410,[(0,0),(0,720)],[(410,510),(0,170)],[(170,310),(430,0)])
    if mono or variant=='SAB Modul': put('l',170,curve((0,720),((0,600),(0,150),(0,90)),((0,-10),(70,0),(170,0))))
    else: put('l',0,[(0,0),(0,720)])
    put('m',690,[(0,0),(0,510)],curve((0,335),((50,570),(330,585),(330,310)),((330,230),(330,90),(330,0))),curve((330,335),((385,570),(690,585),(690,310)),((690,230),(690,90),(690,0))))
    put('n',430,[(0,0),(0,510)],curve((0,330),((40,570),(430,605),(430,305)),((430,210),(430,100),(430,0))))
    put('o',440,oval(440,510))
    put('p',440,[(0,-220),(0,510)],oval(440,510))
    put('q',440,oval(440,510),[(440,510),(440,-220)])
    put('r',280,[(0,0),(0,510)],curve((0,290),((35,490),(165,585),(285,495))))
    put('s',370,curve((350,430),((230,580),(0,510),(5,380)),((5,230),(365,290),(365,125)),((360,-45),(85,-45),(0,75))))
    put('t',265,curve((80,680),((80,550),(80,170),(80,105)),((80,-20),(195,-20),(265,30))),[(0,505),(265,505)])
    put('u',430,curve((0,510),((0,400),(0,200),(0,170)),((0,-90),(370,-65),(430,170))),[(430,510),(430,0)])
    put('v',415,[(0,510),(207.5,0),(415,510)])
    put('w',650,[(0,510),(150,0),(325,430),(500,0),(650,510)])
    put('x',415,[(0,510),(415,0)],[(0,0),(415,510)])
    put('y',425,[(0,510),(230,0)],curve((425,510),((300,175),(175,-145),(150,-170)),((100,-235),(30,-225),(-10,-210))))
    put('z',380,[(0,510),(380,510),(0,0),(380,0)])
    if mono:
        put('i',240,[(0,510),(120,510),(120,0)],[(0,0),(240,0)],[(120,680),(120,681)])
        put('l',240,[(0,720),(100,720),(100,85),(135,0),(240,0)])
    # Numerals, tabular in both companions.
    put('0',450,oval(450),*([[(65,90),(385,610)]] if mono else []))
    put('1',450,[(70,530),(250,700),(250,0)],[(65,0),(435,0)])
    put('2',450,curve((0,535),((0,790),(480,795),(450,520)),((435,380),(70,195),(0,0))),[(0,0),(460,0)])
    put('3',450,curve((0,590),((130,805),(510,700),(435,505)),((410,405),(290,365),(180,365)),((545,420),(570,0),(260,0)),((120,-5),(35,40),(0,115))))
    put('4',450,[(450,220),(0,220),(330,700),(330,0)])
    put('5',450,[(440,700),(55,700),(25,375)],curve((25,375),((525,540),(580,-10),(235,0)),((95,0),(20,60),(0,110))))
    put('6',450,curve((425,630),((185,885),(-60,455),(10,195))),ellipse(230,213,220,213,power=box))
    put('7',450,[(0,700),(450,700),(125,0)])
    put('8',450,ellipse(225,530,200,170,power=box),ellipse(225,182,225,182,power=box))
    put('9',450,ellipse(220,487,220,213,power=box),curve((440,505),((510,235),(265,-160),(20,75))))
    # Cyrillic: language-specific skeletons, not Latin fallback substitution.
    for cy,lat in zip('АВСЕНКМОРТХаеорсух','ABCEHKMOPT Xaeopcyx'.replace(' ','')):
        d[cy]=d[lat]
    put('У',510,[(0,700),(285,220)],curve((510,700),((385,420),(205,65),(175,40)),((120,-15),(50,-10),(0,10))))
    put('Б',470,[(445,700),(0,700),(0,0)],curve((0,365),((650,480),(650,-100),(0,0))))
    put('Г',420,[(0,0),(0,700),(420,700)])
    put('Д',590,[(25,-130),(25,0),(590,0),(590,-130)],[(80,0),(160,170),(200,700),(510,700),(510,0)])
    put('Ж',760,[(0,700),(380,330),(760,700)],[(0,0),(310,395)],[(450,395),(760,0)],[(380,700),(380,0)])
    d['З']=d['3']
    put('И',510,[(0,700),(0,0),(510,700),(510,0)])
    put('Л',540,[(0,0),(75,35),(125,180),(165,700),(540,700),(540,0)])
    put('П',500,[(0,0),(0,700),(500,700),(500,0)])
    put('Ф',690,ellipse(345,360,345,280,power=box),[(345,750),(345,-60)])
    put('Ц',540,[(0,700),(0,0),(490,0),(490,700)],[(490,0),(555,0),(555,-140)])
    put('Ч',490,curve((0,700),((0,630),(0,510),(0,455)),((0,260),(330,275),(490,390))),[(490,700),(490,0)])
    put('Ш',760,[(0,700),(0,0),(760,0),(760,700)],[(380,0),(380,700)])
    put('Щ',800,[(0,700),(0,0),(745,0),(745,700)],[(372,0),(372,700)],[(745,0),(810,0),(810,-140)])
    put('Ь',465,[(0,700),(0,0)],curve((0,365),((650,480),(650,-100),(0,0))))
    w,paths=d['Ь']; put('Ъ',585,*[[(x+120,y) for x,y in p] for p in paths],[(0,700),(120,700)])
    put('Ы',640,*paths,[(640,700),(640,0)])
    put('Э',505,*[[(505-x,y) for x,y in p] for p in d['C'][1]],[(230,350),(505,350)])
    put('Ю',770,[(0,0),(0,700)],[(0,350),(250,350)],ellipse(510,350,260,350,power=box))
    put('Я',490,*[[(490-x,y) for x,y in p] for p in d['R'][1]])
    for upper,lower in zip('ГДЖЗИЛПЦЧШЩЪЫЬЭЮЯ','гджзилпцчшщъыьэюя'):
        w,paths=d[upper]; put(lower,w*.81,*[[(x*.81,y*510/700) for x,y in p] for p in paths])
    put('б',440,oval(440,510),curve((0,255),((-25,535),(70,650),(240,670)),((350,685),(410,695),(440,730))))
    put('в',400,[(0,0),(0,510)],curve((0,510),((520,565),(510,260),(0,275))),curve((0,275),((575,340),(565,-80),(0,0))))
    put('н',430,[(0,0),(0,510)],[(430,0),(430,510)],[(0,255),(430,255)])
    put('к',410,*d['k'][1][1:],[(0,0),(0,510)])
    put('м',550,[(0,0),(0,510),(275,90),(550,510),(550,0)])
    put('т',420,[(0,510),(420,510)],[(210,510),(210,0)])
    put('ф',620,ellipse(310,255,310,255,power=box),[(310,720),(310,-220)])
    # Cyrillic extensions for Ukrainian, Belarusian and Kazakh.
    d['І']=d['I']; d['і']=d['i']; d['Ј']=d['J']; d['ј']=d['j']; d['Ѕ']=d['S']; d['ѕ']=d['s']
    for c,b in [('Ґ','Г'),('ґ','г')]:
        w,p=d[b]; put(c,w,*p,[(w,700 if c.isupper() else 510),(w,810 if c.isupper() else 620)])
    for c,b in [('Є','Э'),('є','э')]:
        w,p=d[b]; put(c,w,*[[(w-x,y) for x,y in q] for q in p])
    for c,b in [('Қ','К'),('қ','к'),('Ң','Н'),('ң','н')]:
        w,p=d[b];put(c,w,*p,[(w,0),(w+50,0),(w+50,-140)])
    for c,b in [('Ғ','Г'),('ғ','г')]:
        w,p=d[b]; h=700 if c.isupper() else 510;put(c,w,*p,[(-50,h*.52),(w*.7,h*.52)])
    for c,b in [('Ө','О'),('ө','о')]:
        w,p=d[b];h=700 if c.isupper() else 510;put(c,w,*p,[(0,h/2),(w,h/2)])
    for c,b in [('Ә','Э'),('ә','э')]:
        w,p=d[b];h=700 if c.isupper() else 510
        put(c,w,ellipse(w/2,h/2,w/2,h/2,180,500,power=box),[(0,h/2),(w,h/2)])
    d['Ү']=d['Y'];d['Һ']=d['h'];d['һ']=d['h']
    put('ү',415,[(0,510),(207.5,250),(415,510)],[(207.5,250),(207.5,-200)])
    for c,b in [('Ұ','Ү'),('ұ','ү')]:
        w,p=d[b]; put(c,w,*p,[(w*.22,210),(w*.78,210)])
    # Punctuation and common text symbols.
    put(' ',280);put('\u00a0',280);put('\u2009',150);put('\u2002',500);put('\u2003',1000)
    put('.',0,[(0,0),(0,1)]);put(',',80,[(70,25),(30,-100),(0,-140)])
    put(':',0,[(0,100),(0,101)],[(0,415),(0,416)])
    put(';',80,[(70,100),(35,-30),(0,-70)],[(70,415),(70,416)])
    put('!',0,[(0,700),(0,210)],[(0,0),(0,1)])
    put('?',360,curve((0,550),((0,760),(365,780),(360,560)),((360,400),(180,420),(180,230))),[(180,0),(180,1)])
    put('-',260,[(0,270),(260,270)]);put('–',480,[(0,270),(480,270)]);put('—',760,[(0,270),(760,270)])
    put('_',490,[(0,-110),(490,-110)])
    put('(',180,curve((180,780),((-70,575),(-70,125),(180,-100))))
    put(')',180,*[[(180-x,y) for x,y in p] for p in d['('][1]])
    put('[',180,[(180,780),(0,780),(0,-100),(180,-100)])
    put(']',180,[(0,780),(180,780),(180,-100),(0,-100)])
    put('{',250,curve((250,780),((20,820),(100,500),(60,410)),((50,370),(0,350),(-10,340)),((0,325),(50,310),(60,275)),((100,190),(20,-140),(250,-100))))
    put('}',250,*[[(250-x,y) for x,y in p] for p in d['{'][1]])
    put('/',310,[(0,-100),(310,780)]);put('\\',310,[(0,780),(310,-100)])
    put('|',0,[(0,-140),(0,780)])
    put("'",0,[(0,700),(0,510)]);put('"',150,[(0,700),(0,510)],[(150,700),(150,510)])
    put('’',80,[(70,735),(40,615),(0,580)]);put('‘',80,[(70,750),(30,715),(0,590)])
    put('“',300,*d['‘'][1],*[[ (x+220,y) for x,y in p] for p in d['‘'][1]])
    put('”',300,*d['’'][1],*[[ (x+220,y) for x,y in p] for p in d['’'][1]])
    put('„',300,*[[(x,y-640) for x,y in p] for p in d['“'][1]])
    put('«',350,[(150,480),(0,280),(150,80)],[(350,480),(200,280),(350,80)])
    put('»',350,*[[(350-x,y) for x,y in p] for p in d['«'][1]])
    put('‹',150,[(150,480),(0,280),(150,80)]);put('›',150,[(0,480),(150,280),(0,80)])
    put('+',460,[(0,320),(460,320)],[(230,90),(230,550)])
    put('=',460,[(0,430),(460,430)],[(0,210),(460,210)])
    put('<',420,[(420,570),(0,320),(420,70)]);put('>',420,[(0,570),(420,320),(0,70)])
    put('*',330,[(165,710),(165,360)],[(0,620),(330,450)],[(0,450),(330,620)])
    put('#',490,[(150,700),(60,0)],[(425,700),(335,0)],[(0,450),(490,450)],[(0,235),(490,235)])
    put('%',680,ellipse(130,550,130,150),ellipse(550,150,130,150),[(30,0),(650,700)])
    if mono:put('%',440,ellipse(90,595,90,105),ellipse(350,105,90,105),[(10,0),(430,700)])
    put('&',570,curve((550,0),((390,180),(20,490),(20,565)),((0,760),(370,750),(340,570)),((310,450),(-20,340),(0,165)),((20,-85),(440,-65),(520,340))))
    put('@',740,ellipse(365,330,365,370,0,310),ellipse(355,345,145,200),curve((500,550),((500,550),(480,220),(500,200)),((650,30),(730,160),(730,330))))
    put('~',480,curve((0,310),((160,530),(320,90),(480,310))))
    put('^',400,[(0,420),(200,690),(400,420)])
    put('`',160,[(0,740),(160,610)])
    put('$',460,*d['S'][1],[(230,800),(230,-100)])
    put('€',520,ellipse(260,350,260,350,45,315,power=box),[(-20,450),(410,450)],[(-20,250),(360,250)])
    put('£',460,curve((440,600),((360,795),(100,715),(110,515)),((150,210),(110,160),(0,0))),[(0,0),(460,0)],[(0,320),(350,320)])
    put('¥',510,*d['Y'][1],[(40,325),(470,325)],[(40,125),(470,125)])
    put('₽',460,*d['P'][1],[(-45,140),(305,140)])
    put('₸',490,[(0,700),(490,700)],[(0,500),(490,500)],[(245,500),(245,0)])
    put('¢',410,*d['c'][1],[(210,625),(210,-100)])
    put('°',235,ellipse(117.5,587.5,117.5,117.5))
    put('•',0,[(0,280),(0,281)]);put('·',0,[(0,280),(0,281)])
    put('…',400,[(0,0),(0,1)],[(200,0),(200,1)],[(400,0),(400,1)])
    put('×',380,[(0,520),(380,100)],[(0,100),(380,520)])
    put('÷',460,[(0,310),(460,310)],[(230,535),(230,536)],[(230,85),(230,86)])
    d['−']=d['–']
    put('±',460,*d['+'][1],[(0,-60),(460,-60)])
    put('≠',460,*d['='][1],[(100,0),(360,640)])
    put('≤',420,*d['<'][1],[(0,-65),(420,-65)]);put('≥',420,*d['>'][1],[(0,-65),(420,-65)])
    put('≈',480,*d['~'][1],*[[ (x,y-200) for x,y in p] for p in d['~'][1]])
    put('∞',700,curve((350,310),((140,690),(-100,400),(30,165)),((150,-15),(290,170),(350,310)),((560,690),(800,400),(670,165)),((550,-15),(410,170),(350,310))))
    put('√',520,[(0,250),(110,290),(230,0),(420,700),(560,700)])
    for ch,angle in [('→',0),('↑',90),('←',180),('↓',270)]:
        ca,sa=math.cos(math.radians(angle)),math.sin(math.radians(angle))
        paths=[[(0,330),(620,330)],[(390,570),(630,330),(390,90)]]
        put(ch,640,*[[(320+(x-320)*ca-(y-330)*sa,330+(x-320)*sa+(y-330)*ca) for x,y in p] for p in paths])
    put('№',1000,*[[(x*450/510,y) for x,y in p] for p in d['N'][1]],ellipse(870,550,115,150),[(755,280),(985,280)])
    for ch,base in [('©','C'),('®','R')]:
        w,p=d[base]; put(ch,730,ellipse(365,350,365,365),*[[(x*.55+(730-w*.55)/2,y*.55+157) for x,y in q] for q in p])
        if mono and ch=='®':
            w,p=d[ch];put(ch,w,p[0],*[[(365+(x-365)*.94,350+(y-350)*.94) for x,y in q] for q in p[1:]])
    put('™',700,*[[(x*.5,y*.5+350) for x,y in p] for p in d['T'][1]],*[[(x*.5+350,y*.5+350) for x,y in p] for p in d['M'][1]])
    put('§',460,*[[(x,y*.70+offset) for x,y in p] for offset in [0,290] for p in d['S'][1]])
    put('¶',440,[(440,700),(440,-110)],[(260,700),(260,-110)],curve((260,700),((-100,750),(-100,305),(260,340))))
    put('†',360,[(180,700),(180,-120)],[(0,460),(360,460)])
    put('‡',360,*d['†'][1],[(0,200),(360,200)])
    put('¦',0,[(0,780),(0,430)],[(0,220),(0,-140)])
    put('¬',460,[(0,420),(460,420),(460,130)])
    put('¡',0,[(0,510),(0,511)],[(0,300),(0,-190)])
    put('¿',360,*[[(360-x,510-y) for x,y in p] for p in d['?'][1]])
    # Latin additions not produced through canonical accent composition.
    put('ß',440,[(0,0),(0,520)],curve((0,520),((0,850),(470,770),(355,555)),((305,470),(215,440),(255,365)),((640,250),(415,-90),(160,30))))
    for ch,base in [('Ø','O'),('ø','o'),('Ł','L'),('ł','l'),('Đ','D'),('đ','d'),('Ħ','H'),('ħ','h')]:
        w,p=d[base];h=700 if ch.isupper() else 510
        extra=[(-40,h*.3),(w+40,h*.7)] if ch in 'ØøŁł' else [(-55,h*.65),(w*.65,h*.65)]
        if ch=='Ħ':extra=[(-55,575),(w+55,575)]
        put(ch,max(w,100),*p,extra)
    for ch,l,r in [('Æ','A','E'),('Œ','O','E'),('œ','o','e')]:
        wl,pl=d[l];wr,pr=d[r];put(ch,(wl+wr)*.85,*[[(x*.85,y) for x,y in p] for p in pl],*[[(x*.85+wl*.85,y) for x,y in p] for p in pr])
    if mono:put('Æ',530,[(0,0),(345,700)],[(530,700),(345,700),(345,0),(530,0)],[(120.75,245),(345,245)],[(345,350),(500,350)])
    put('Ð',500,*d['D'][1],[(-65,350),(260,350)])
    put('ð',440,oval(440,510),curve((440,255),((460,600),(240,700),(110,740))),[(90,595),(340,735)])
    put('Þ',460,[(0,0),(0,700)],curve((0,545),((640,635),(640,90),(0,180))))
    put('þ',440,[(0,-220),(0,720)],oval(440,510))
    put('ı',d['i'][0],*d['i'][1][:-1]);put('ſ',180,*d['f'][1])
    w,p=d['ß'];put('ẞ',w*1.15,*[[(x*1.15,y) for x,y in q] for q in p])
    w,p=d['f'];put('ƒ',w,*p,curve((80,0),((80,-180),(-30,-220),(-100,-160))))
    put('µ',430,*d['u'][1],[(0,0),(0,-210)])
    put('ℓ',260,curve((0,0),((100,170),(440,705),(190,700)),((60,700),(-80,-120),(260,35))))
    d['‒']=d['–'];d['‑']=d['-'];d['‐']=d['-']
    put('¤',410,ellipse(205,345,150,150),[(0,550),(100,445)],[(310,245),(410,140)],[(0,140),(100,245)],[(310,445),(410,550)])
    # Optical corrections shared by the composed alphabet below.
    put('a',355,curve((20,440),((45,490),(110,510),(190,510)),((300,510),(355,455),(355,355))),[(355,355),(355,0)],curve((355,320),((280,320),(220,320),(160,307)),((55,294),(0,240),(0,155)),((0,65),(55,0),(145,0)),((255,0),(355,85),(355,190))))
    if not mono:
        aw, ap = d['a']
        d['a'] = (aw, [ap[0] + ap[1][1:], *ap[2:]])
    wa,pa=d['a'];we,pe=d['e'];put('æ',(wa+we)*.85,*[[(x*.85,y) for x,y in p] for p in pa],*[[(x*.85+wa*.85,y) for x,y in p] for p in pe])
    put('B',460,[(0,0),(0,700)],curve((0,700),((195,700),(430,740),(430,525)),((430,360),(225,355),(0,355))),curve((0,355),((200,355),(475,400),(475,175)),((475,-35),(195,0),(0,0))))
    put('b',415,[(0,0),(0,720)],ellipse(207.5,255,207.5,255))
    put('d',415,*[[(415-x,y) for x,y in q] for q in d['b'][1]])
    put('đ',415,*d['d'][1],[(235,690),(510,690)])
    put('ð',415,curve((350,430),((320,485),(250,510),(190,510)),((50,510),(0,400),(0,255)),((0,90),(65,0),(200,0)),((340,0),(415,95),(415,255)),((415,320),(390,390),(350,430))),curve((350,430),((340,570),(250,680),(115,750))),[(90,625),(315,775)])
    put('p',415,[(0,-220),(0,510)],*d['b'][1][1:])
    put('q',415,*[[(415-x,y) for x,y in q] for q in d['p'][1]])
    put('n',400,[(0,0),(0,510)],curve((0,300),((0,425),(90,510),(205,510)),((345,510),(400,430),(400,285)),((400,195),(400,100),(400,0))))
    put('h',400,[(0,0),(0,720)],*d['n'][1][1:])
    put('m',645,[(0,0),(0,510)],curve((0,320),((0,435),(70,510),(160,510)),((270,510),(310,435),(310,300)),((310,220),(310,100),(310,0))),curve((310,320),((310,435),(390,510),(490,510)),((610,510),(645,430),(645,300)),((645,215),(645,100),(645,0))))
    put('r',255,[(0,0),(0,510)],curve((0,295),((0,440),(100,545),(255,495))))
    put('s',365,curve((350,425),((300,545),(0,550),(0,380)),((0,225),(365,305),(365,130)),((365,-45),(80,-35),(0,80))))
    put('u',400,curve((0,510),((0,400),(0,260),(0,205)),((0,65),(55,0),(190,0)),((300,0),(400,80),(400,210))),[(400,510),(400,0)])
    put('v',400,[(0,510),(200,0),(400,510)])
    tail=curve((415,510),((305,220),(170,-125),(145,-165)),((110,-215),(55,-235),(-5,-205)))
    junction=LineString([(0,510),(225,0)]).intersection(LineString(tail))
    put('y',415,[(0,510),(junction.x,junction.y)],tail)
    put('t',220,curve((75,675),((75,500),(75,170),(75,110)),((75,-5),(150,-10),(235,25))),[(0,505),(240,505)])
    put('f',230,curve((65,0),((65,200),(65,510),(65,565)),((65,735),(185,760),(260,705))),[(0,505),(240,505)])
    put('l',0,[(0,0),(0,720)])
    if mono:put('l',230,[(0,720),(100,720),(100,95)],curve((100,95),((100,5),(140,0),(230,0))))
    put('в',375,[(0,0),(0,510)],curve((0,510),((90,510),(170,510),(220,510)),((300,510),(340,465),(340,395)),((340,325),(290,265),(215,265)),((140,265),(70,265),(0,265))),curve((0,265),((80,265),(160,265),(230,265)),((315,265),(375,225),(375,138)),((375,50),(320,0),(225,0)),((150,0),(70,0),(0,0))))
    put('я',385,[(385,0),(385,510)],curve((385,510),((305,510),(225,510),(145,510)),((55,510),(0,467),(0,393)),((0,295),(50,245),(145,245)),((225,245),(305,245),(385,245))),[(170,245),(0,0)])
    put('б',420,curve((0,235),((0,560),(55,675),(260,690)),((330,697),(390,708),(435,715))),oval(420,510))
    put('н',415,[(0,0),(0,510)],[(415,0),(415,510)],[(0,250),(415,250)])
    put('и',420,[(0,510),(0,0),(420,510),(420,0)])
    put('т',370,[(0,510),(370,510)],[(185,510),(185,0)])
    put('м',535,[(0,0),(0,510),(267.5,95),(535,510),(535,0)])
    put('л',430,curve((0,0),((90,0),(105,60),(120,215)))+[(145,510),(430,510),(430,0)])
    put('д',470,[(0,-125),(0,0),(470,0),(470,-125)],[(50,0),(100,140),(140,510),(410,510),(410,0)])
    put('ц',430,[(0,510),(0,0),(400,0),(400,510)],[(400,0),(455,0),(455,-125)])
    put('ш',655,[(0,510),(0,0),(655,0),(655,510)],[(327.5,0),(327.5,510)])
    put('щ',655,*d['ш'][1],[(655,0),(710,0),(710,-125)])
    put('ф',560,ellipse(280,255,280,255,power=2.12),[(280,720),(280,-220)])
    put('ж',660,[(0,510),(185,255),(330,255)],[(660,510),(475,255),(330,255)],[(0,0),(185,255)],[(475,255),(660,0)],[(330,510),(330,0)])
    put('к',390,[(0,0),(0,510)],[(390,510),(160,255),(0,255)],[(160,255),(400,0)])
    put('з',365,curve((0,420),((25,480),(90,510),(175,510)),((285,510),(350,475),(350,385)),((350,300),(255,265),(165,265)),((270,265),(370,225),(370,130)),((370,35),(295,0),(175,0)),((85,0),(30,25),(0,80))))
    put('ч',410,curve((0,510),((0,475),(0,370),(0,330)),((0,170),(285,195),(410,300))),[(410,510),(410,0)])
    for cy,la in [('а','a'),('В','B'),('р','p'),('с','c'),('е','e'),('у','y')]: d[cy]=d[la]
    put('Ы',640,[(0,0),(0,700)],curve((0,355),((150,355),(370,385),(370,175)),((370,-15),(140,0),(0,0))),[(640,0),(640,700)])
    put('ы',570,[(0,0),(0,510)],curve((0,265),((140,265),(320,295),(320,130)),((320,-15),(130,0),(0,0))),[(570,0),(570,510)])
    put('µ',400,*d['u'][1],[(0,510),(0,-210)])
    for c,b in [('Қ','К'),('қ','к')]:
        w,paths=d[b];new=[list(p) for p in paths]
        leg=max((i for i,p in enumerate(new) if p[-1][1]==0),key=lambda i:new[i][-1][0])
        x=new[leg][-1][0];new[leg]+=[(x+40,0),(x+40,-140)]
        put(c,w+40,*new)
    # Serbian/Macedonian core alphabet and text spacing.
    put('Ђ',560,[(0,700),(475,700)],[(155,700),(155,0)],curve((155,350),((195,560),(560,585),(560,315)),((560,185),(560,95),(560,0)),((560,-215),(430,-245),(355,-175))))
    put('Ћ',560,[(0,700),(475,700)],[(155,700),(155,0)],curve((155,350),((195,560),(560,585),(560,315)),((560,185),(560,95),(560,0))))
    put('ђ',435,*d['h'][1],curve((400,0),((400,-220),(290,-245),(205,-175))),[(-45,660),(270,660)])
    put('ћ',435,*d['h'][1],[(-45,660),(270,660)])
    for ch,base,h in [('Љ','Л',700),('љ','л',510),('Њ','Н',700),('њ','н',510)]:
        w,paths=d[base]
        put(ch,w+350,*paths,curve((w,h*.52),((w+470,h*.68),(w+470,-70),(w,0))))
    for ch,base,h in [('Џ','Ц',700),('џ','ц',510)]:
        w,paths=d[base];put(ch,w,*paths[:-1],[(w/2,0),(w/2,-125)])
    put('‰',1050,ellipse(130,550,130,150),ellipse(550,150,115,150),ellipse(935,150,115,150),[(30,0),(650,700)])
    if mono:put('‰',730,ellipse(80,595,80,105),ellipse(330,105,80,105),ellipse(640,105,80,105),[(20,0),(520,700)])
    put('\u202f',250)
    put('−',460,[(0,350),(460,350)])
    # Accents are drawn here, shared by composed and combining glyphs.
    accents={
       '\u0300': [[(-100,140),(65,40)]], '\u0301':[[(-65,40),(100,140)]],
       '\u0302':[[(-120,30),(0,150),(120,30)]], '\u030c':[[(-120,150),(0,30),(120,150)]],
       '\u0308':[[(-115,85),(-115,86)],[(115,85),(115,86)]],
       '\u0303':[curve((-145,60),((-50,185),(50,-45),(145,80)))],
       '\u0304':[[(-145,85),(145,85)]], '\u0306':[curve((-135,140),((-100,-10),(100,-10),(135,140)))],
       '\u0307':[[(0,85),(0,86)]], '\u030a':[ellipse(0,110,78,78)],
       '\u030b':[[(-135,40),(-25,150)],[(40,40),(150,150)]],
       '\u0327':[curve((0,0),((-70,-110),(90,-80),(75,-150)),((65,-200),(-50,-205),(-85,-170)))],
       '\u0328':[curve((85,0),((-75,-100),(-25,-190),(80,-130)))],
       '\u0326': [[(30,-65),(0,-160)]], '\u0312':[[(-40,95),(20,185)]]}
    for ch,paths in accents.items(): put(ch,0,*paths)
    # Compose Latin-1, Extended-A, Cyrillic accents without importing any glyphs.
    for cp in list(range(0xc0,0x180))+list(range(0x400,0x460))+list(range(0x218,0x21c))+[0x1e80,0x1e81,0x1e82,0x1e83,0x1e84,0x1e85,0x1ef2,0x1ef3]:
        ch=chr(cp)
        if ch in d: continue
        parts=unicodedata.normalize('NFD',ch)
        if len(parts)<2 or parts[0] not in d or any(a not in accents for a in parts[1:]):continue
        base=parts[0];w,paths=d['ı' if base=='i' and any(a not in '\u0327\u0328\u0326' for a in parts[1:]) else base]; new=list(paths)
        top=700 if base.isupper() else 510
        if base in 'bdfhklt':top=720
        for a in parts[1:]:
            below=a in '\u0327\u0328\u0326'
            new += [[(x+w/2,y+(0 if below else top+55)) for x,y in p] for p in accents[a]]
        put(ch,w,*new)
    d['ĸ']=d['к']
    put('Ŋ',510,*d['N'][1],curve((510,0),((510,-220),(360,-240),(280,-190))))
    put('ŋ',430,*d['n'][1],curve((430,0),((430,-220),(280,-240),(200,-190))))
    for ch,b in [('Ŧ','T'),('ŧ','t')]:
        w,p=d[b];put(ch,w,*p,[(0,310),(w,310)])
    for ch,b in [('Ŀ','L'),('ŀ','l')]:
        w,p=d[b];dotx=300 if mono and ch=='ŀ' else 220
        put(ch,max(w,dotx+40),*p,[(dotx,350),(dotx,351)])
    w,p=d['n'];put('ŉ',w+210,*[[(x+210,y) for x,y in q] for q in p],[(0,680),(-30,540)])
    for ch,base in [('Ĳ','IJ'),('ĳ','ij')]:
        wa,pa=d[base[0]];wb,pb=d[base[1]];put(ch,wa+wb+210,*pa,*[[(x+wa+210,y) for x,y in p] for p in pb])
    for ch,num in [('¹','1'),('²','2'),('³','3'),('ª','a'),('º','o')]:
        w,p=d[num];put(ch,w*.58,*[[(x*.58,y*.58+350) for x,y in q] for q in p])
    for ch,n,den in [('¼','1','4'),('½','1','2'),('¾','3','4')]:
        put(ch,740,*[[(x*.5,y*.5+350) for x,y in p] for p in d[n][1]],[(100,0),(640,700)],*[[(x*.5+500,y*.5) for x,y in p] for p in d[den][1]])
    put('´',160,[(0,610),(160,740)]);put('¨',230,[(0,690),(0,691)],[(230,690),(230,691)])
    put('¯',280,[(0,720),(280,720)]);put('¸',150,*accents['\u0327'])
    put('ȷ',d['j'][0],*d['j'][1][:-1])
    for ch,mark in zip('ˆˇ˘˙˚˛˜˝','̨̂̌̆̇̊̃̋'):
        put(ch,300,*[[(x+150,y+(0 if mark=='̨' else 560)) for x,y in path] for path in accents[mark]])
    put('‚',d[','][0],*d[','][1])
    return d

def name(ch): return 'uni%04X'%ord(ch)

def stroke_ratio(thickness):return .90-max(0,thickness-80)*.0015

def geometry(w,paths,variant,mono,thickness,oblique,ch,_factor=None):
    original_thickness=thickness
    if mono and ch in 'Юю':thickness-=max(0,thickness-80)*.30
    parts=unicodedata.normalize('NFD',ch);base=parts[0]
    ismark=bool(unicodedata.combining(ch))
    lower=base.islower() and base not in 'ßſðþ'
    target_h=XHEIGHT if lower else 700
    source_h=510 if lower else 700
    ratio=stroke_ratio(thickness)
    def ymap(y):
        if ismark:return y+thickness*ratio/2
        if y<0:return thickness*ratio/2+y
        if y<=source_h:return thickness*ratio/2+y*(target_h-thickness*ratio)/source_h
        return target_h-thickness*ratio/2+(y-source_h)
    factor=1.02 if base.isupper() else .91
    if base in 'тт':factor=.94
    if base in 'ЖШЩ':factor=.94
    if mono:factor=min(.96,455/max(w,1))
    if _factor is not None:factor=_factor
    if ch.isspace():
        return Polygon(),(MONO_ADVANCE if mono else 250 if ch=='\u202f' else 150 if ch=='\u2009' else 500 if ch=='\u2002' else 1000 if ch=='\u2003' else 220),0
    geoms=[];a_stem_x=None
    for path_index,path in enumerate(paths):
        if len(path)<2:continue
        dot=len(path)==2 and math.dist(path[0],path[-1])<2
        topaccent=bool(len(parts)>1 and min(y for x,y in path)>source_h+20) or (ch=='ŉ' and path_index==len(paths)-1)
        lift=min(95,max(0,thickness-80)*1.2) if topaccent or (dot and path[0][1]>600) else 0
        overshoot=8 if base in 'oоeеcсOО' and len(path)>20 and not topaccent else 0
        pts=[(x*factor,(ymap(y+lift)+overshoot*(2*y/source_h-1))/ratio) for x,y in path]
        scale=1.0
        if ch=='%':scale=.75-max(0,thickness-80)*.0015
        if ch=='‰':scale=(.50 if mono else .65)-max(0,thickness-80)*.0012
        if ch=='№':scale=(.85 if mono else .90) if path_index==0 else .48 if path_index==1 else .65
        if ch in '@©®':scale=(.70 if mono else .75) if path_index==0 else (.45 if mono else .60)
        if ch=='@' and mono and path_index==0:scale=min(scale,95/thickness)
        if ch=='®' and mono and path_index==0:scale=min(scale,90/thickness)
        if ch=='®' and not mono:scale=.70 if path_index==0 else .55
        if ch=='ð' and path_index==2:scale=.70
        if ch=='™':scale=.45 if mono else .60
        if ch in 'ªº¹²³¼½¾':scale=.45 if mono else .55
        if ch in 'ÆæŒœĲĳ' and mono:scale=.68
        if ch=='Æ' and mono:scale=.85
        if ch in '"“”„‘’':scale=.82-max(0,thickness-80)*.002
        if ch in '°§':scale=.70
        if ismark or topaccent or ch in 'ˆˇ˘˙˚˛˜˝':
            scale=.72
            if '\u030a' in parts or ch in '\u030a˚':scale=.60
        local=thickness*scale
        if len(path)<5:
            diagonals=[abs(b[0]-a[0])>35 and abs(b[1]-a[1])>35 for a,b in zip(path,path[1:])]
            if diagonals and all(diagonals):local*=.92
        clips=[]
        if dot and (ch in '\u0307\u0308˙' or base in 'ijіјĳ'):
            # Optical dots retain enough height in light weights and share the same visual level.
            dw=30+thickness*.75;dh=55+thickness*.50;radius=min(dw,dh)*.18
            cx,cy=pts[0]
            if ch=='\u0308':cx=math.copysign(90+max(0,thickness-80)*.25,cx)
            if base in 'ijіјĳ':cy=625/ratio
            g=rectangle(cx-dw/2+radius,cy-dh/2+radius,cx+dw/2-radius,cy+dh/2-radius).buffer(radius,quad_segs=8)
            g=affine_transform(g,[1,0,0,1/ratio,0,cy*(1-1/ratio)])
        elif dot:g=Point(pts[0]).buffer(local*.52,quad_segs=12)
        else:
            # Align flat stem ends with the baseline/x-height; flat buffer caps stop half a stem short.
            if pts[0]!=pts[-1]:
                for end,neighbor in [(0,1),(-1,-2)]:
                    dx=pts[end][0]-pts[neighbor][0];dy=pts[end][1]-pts[neighbor][1]
                    length=math.hypot(dx,dy)
                    if length and abs(dx)<1e-6:
                        x,y=pts[end];pts[end]=(x,y+math.copysign(local/2,dy))
                    elif length and abs(dy)>abs(dx)*.25 and base.isalpha() and (len(path)<=5 or base in 'yуУ') and ((path[end][1]==0 and dy<0) or (path[end][1]==source_h and dy>0)):
                        # Extend diagonal ends through the alignment line, then cut horizontally.
                        limit=(0 if path[end][1]==0 else target_h)/ratio
                        sign=1 if dy>0 else -1
                        end_y=limit+sign*(local*abs(dx)/length/2+1)
                        x,y=pts[end];pts[end]=(x+(end_y-y)*dx/dy,end_y)
                        clips.append((limit,sign))
            g=LineString(pts).buffer(local/2,cap_style='flat',join_style='round',quad_segs=8)
            for limit,sign in clips:
                x0,y0,x1,y1=g.bounds
                g=g.intersection(rectangle(x0-1,y0-1 if sign>0 else limit,x1+1,limit if sign>0 else y1+1))
        g=affine_transform(g,[1,0,0,ratio,0,0])
        if oblique and base in 'oOоОcCсСeе' and len(path)>20:
            # Counter-shear rounded parts; keep upright stems at the specified 10 degrees.
            slope=math.tan(math.radians(10))*.6
            g=affine_transform(g,[1,-slope,0,1,slope*target_h/2,0])
        if not mono and base in 'aаæª' and path_index==0:
            a_stem_x=pts[-1][0]+local/2
        geoms.append(g)
    if base in 'мМиИ':
        # Flat shoulders and open diagonal joins need drawn geometry, not round line joins.
        span=w*factor;h=target_h;t=thickness
        geoms=[g for g in geoms if g.bounds[1]>h]+[rectangle(-t/2,0,t/2,h),rectangle(span-t/2,0,span+t/2,h)]
        points=[(0,h),(span/2,t*.50),(span,h)] if base in 'мМ' else [(0,t*.25),(span,h-t*.25)]
        diagonal=LineString(points).buffer(t*.45,cap_style='flat',join_style='mitre')
        geoms.append(diagonal.intersection(rectangle(-t/2,0,span+t/2,h)))
    g=unary_union(geoms).simplify(.3,preserve_topology=True) if geoms else Polygon()
    if a_stem_x is not None:
        # Keep the joined outer stem vertical after polygon simplification.
        def straight_stem(ring):
            pts=list(ring.coords)
            for i in range(len(pts)-1):
                a,b=pts[i],pts[i+1]
                if abs(a[0]-a_stem_x)<1 and abs(b[0]-a_stem_x)<1 and abs(a[1]-b[1])>80:
                    pts[i]=(a_stem_x,a[1]);pts[i+1]=(a_stem_x,b[1])
            pts[-1]=pts[0]
            return pts
        polys=[g] if g.geom_type=='Polygon' else list(g.geoms)
        g=unary_union([Polygon(straight_stem(p.exterior),[straight_stem(r) for r in p.interiors]) for p in polys])
    if g.is_empty:return g,(MONO_ADVANCE if mono else round(w+100)),0
    if ch=='§':
        sy=860/(g.bounds[3]-g.bounds[1])
        g=affine_transform(g,[1,0,0,sy,0,-160-sy*g.bounds[1]])
    if base in 'eе':
        # Finish the crossbar at the outer edge; the drawn terminal leaves the aperture open.
        mid=target_h/2;half=thickness*ratio/2;right=w*factor+thickness/2
        g=g.union(rectangle(0,mid-half,right,mid+half))
    if ch in '+−×=÷<>≤≥≈±≠':
        g=affine_transform(g,[1,0,0,1,0,350-(g.bounds[1]+g.bounds[3])/2])
    xmin,ymin,xmax,ymax=g.bounds
    if mono and ch.isalpha() and xmax-xmin>MONO_ADVANCE-48 and factor>.1:
        # Narrow the skeleton, keeping the actual stem thickness and Mono advance.
        return geometry(w,paths,variant,mono,original_thickness,oblique,ch,factor*.95)
    if ismark:advance=0;shift=0
    elif mono:
        advance=MONO_ADVANCE;shift=(advance-(xmax-xmin))/2-xmin
    else:
        left=right=48
        if base in 'ОоСсЭэФфЮюаеОQCGOoeacgs059368':left=right=34
        if base in 'АУТГVWTYAvwxyУуТтГг':left=right=24
        if base in 'нНпПшШщЩиИйЙ':left=right=46
        if base in 'нпшщий':left+=12;right+=12
        if base in 'бвbdhkmnpr':left=48;right=34
        if base in 'лдЛД':left=20;right=40
        if base in 'жЖкКхХ':left=right=30
        if base in 'ilІіı':left=right=58
        if base in '.,:;!':left=right=68
        if base in 'ftr':left=26;right=24
        if base in 'nhm':left+=10;right+=10
        if base in '0123456789+−×=÷<>≤≥≈¬±≠':
            advance=630+round((thickness-80)*.45);shift=(advance-(xmax-xmin))/2-xmin
        else:
            # Optical sidebearings vary gently by weight; outlines grow, counters stay open.
            adjust=(thickness-80)*.08
            left=max(18,left-adjust);right=max(18,right-adjust)
            advance=round(xmax-xmin+left+right);shift=left-xmin
    g=affine_transform(g,[1,0,0,1,shift,0])
    if oblique:g=affine_transform(g,[1,math.tan(math.radians(10)),0,1,-18,0])
    return g,advance,math.floor(g.bounds[0])

def contours(g):
    if g.is_empty:return []
    out=[]
    for poly in ([g] if g.geom_type=='Polygon' else g.geoms):
        p=orient(poly,sign=-1)
        for ring in [p.exterior,*p.interiors]:
            points=[]
            for x,y in list(ring.coords)[:-1]:
                pt=(round(x),round(y))
                if not points or pt!=points[-1]:points.append(pt)
            if len(points)>2:
                if not LinearRing(points).is_simple:
                    # Integer rounding can fold adjacent collinear edges back on themselves.
                    area=Polygon(points).area
                    cleaned=[b for a,b,c in zip(points[-1:]+points[:-1],points,points[1:]+points[:1])
                            if (b[0]-a[0])*(c[1]-b[1])!=(b[1]-a[1])*(c[0]-b[0])]
                    if LinearRing(cleaned).is_simple and abs(Polygon(cleaned).area-area)<1e-6:points=cleaned
                out.append(points)
    return out

def optical_kerning(data,raw,outlines,thickness,style,oblique):
    aliases=dict(zip('АВЕКМНОРСТХаеорсух','ABEKMHOPCTXaeopcyx'))
    keys={}
    for c in data:
        if not c.isalpha() and c not in '.,:;!?«»‹›“”‘’()[]{}-–—−+=$€£₽₸¥%‰№/':continue
        base=unicodedata.normalize('NFD',c)[0]
        base=aliases.get(base,base)
        if base not in data:base=c
        if c in 'ďĽľť':base=c
        keys.setdefault(base,[]).append(c)
    groups={k:v for k,v in keys.items() if not outlines[k].is_empty}
    shapes={k:outlines[k] for k in groups}
    advances={k:raw[name(k)][1] for k in groups}
    members={k:[name(c) for c in chars] for k,chars in groups.items()}
    for c in '0123456789':
        key=c+'.pnum';gn=name(c)+'.pnum'
        dx=40-min(x for q in raw[name(c)][0] for x,y in q)
        groups[key]=[key];members[key]=[gn];advances[key]=raw[gn][1]
        shapes[key]=affine_transform(outlines[c],[1,0,0,1,dx,0])
        assert contours(shapes[key])==raw[gn][0],'Kerning must use the actual pnum outline'
    for c in '()[]{}-–—':
        key=c+'.case';gn=name(c)+'.case'
        ys=[y for q in raw[name(c)][0] for x,y in q]
        groups[key]=[key];members[key]=[gn];advances[key]=raw[gn][1]
        shapes[key]=affine_transform(outlines[c],[1,0,0,1,0,350-(min(ys)+max(ys))/2])
    heights=list(range(5,701,10));profiles={}
    for k in groups:
        g=shapes[k];profile=[]
        for y in heights:
            hit=g.intersection(LineString([(-2000,y),(4000,y)]))
            profile.append(None if hit.is_empty else (hit.bounds[0],hit.bounds[2]))
        profiles[k]=profile
    # ponytail: sampled silhouette distances propose kerning; reviewed text pairs take precedence.
    target=90-(thickness-80)*.10
    corrections={}
    for l in groups:
        for r in groups:
            gaps=[]
            for a,b in zip(profiles[l],profiles[r]):
                if a and b:gaps.append(advances[l]-a[1]+b[0])
            if len(gaps)<3 or min(gaps)<=0:continue
            perceived=(len(gaps)/sum(1/(x*x) for x in gaps))**.5
            correction=round((target-perceived)*.45/5)*5
            correction=max(-45,min(15,correction))
            correction=max(correction,round(22-min(gaps)))
            # The sampled profile can miss terminals; check the complete pair outlines.
            while correction<0 and shapes[l].distance(affine_transform(shapes[r],[1,0,0,1,advances[l]+correction,0]))<24:
                correction+=5
            if abs(correction)>=10:corrections[(l,r)]=correction
    manual={'Тр':-40,'Ту':-35,'Та':-45,'То':-50,'ГА':-45,'АУ':-30,'ЛА':-15,'ДУ':-25,'ЧА':-15,'УЧ':-15,'AV':-45,'AW':-30,'AT':-35,'LT':-30,'PA':-30,'TA':-35,'Ty':-40,'Ve':-30,'Wa':-20,'Yo':-45,'f)':0,'f.':-20,'r.':-30}
    # Reviewed against iterations/06/pairs-{Regular,Bold}.png: 30 Cyrillic and 30 Latin pairs.
    reviewed={'ан':0,'ра':-10,'ко':-15,'ст':-10,'ов':0,'ен':0,'ро':0,'то':-20,'ни':0,'ка':-15,'ре':0,'ер':0,'та':-20,'пр':0,'но':0,'тр':-10,'од':-20,'те':-20,'по':0,'за':-10,'не':0,'от':-15,'на':0,'ел':-20,'нт':-10,'ом':0,'ос':0,'ат':-15,'ор':0,'ме':0,
              'ly':-10,'ti':-10,'pt':0,'im':0,'ma':0,'Fl':-15,'Op':0,'in':0,'yO':-10,'co':-10,'om':0,'le':0,'er':0,'op':0,'ce':-10,'ar':0,'md':0,'re':-10,'an':0,'CT':-15,'ac':0,'or':0,'nk':0,'YY':0,'en':0,'TO':-20,'ew':-10,'ws':-10,'on':0,'ra':-15}
    manual.update(reviewed)
    for pair,value in manual.items():
        l,r=[aliases.get(unicodedata.normalize('NFD',c)[0],c) for c in pair]
        if l in groups and r in groups:corrections[l,r]=value
    # Merge only equivalent edges with identical pair values, preserving reviewed spacing.
    def side_classes(first):
        signatures={};mapping={};classes=[]
        for key in groups:
            edge=tuple(None if p is None else round((advances[key]-p[1] if first else p[0])/5) for p in profiles[key])
            values=tuple(corrections.get((key,other) if first else (other,key),0) for other in groups)
            signature=(edge,values)
            if signature not in signatures:signatures[signature]=len(classes);classes.append([])
            index=signatures[signature];mapping[key]=index;classes[index].extend(members[key])
        return mapping,classes
    first,first_classes=side_classes(True);second,second_classes=side_classes(False)
    lines=[]
    for prefix,classes in [('R',first_classes),('L',second_classes)]:
        for index,glyphs in enumerate(classes):lines.append('@%s%d = [%s];'%(prefix,index,' '.join(glyphs)))
    class_values={}
    for (l,r),value in corrections.items():
        pair=(first[l],second[r])
        assert pair not in class_values or class_values[pair]==value,'Conflicting side-class values'
        class_values[pair]=value
    lines.append('feature kern {')
    for (l,r),v in class_values.items():
        if v:lines.append('pos @R%d @L%d %d;'%(l,r,v))
    lines.append('} kern;')
    if style=='Regular' and not oblique:
        count=sum(len(groups[l])*len(groups[r]) for (l,r),v in corrections.items() if v)
        (ROOT/'kerning-data.json').write_text(json.dumps({'classes':groups,'first_glyph_right_edge_classes':first_classes,'second_glyph_left_edge_classes':second_classes,'class_pairs':len(class_values),'expanded_pairs':count,'values':{l+r:v for (l,r),v in corrections.items()},'tabular_digits':'excluded from kerning; pnum alternates are included'},ensure_ascii=False,indent=2))
    return '\n'.join(lines)

def build(variant,mono,style,weight,thickness,oblique,formats=('ttf','otf','woff2')):
    family=variant+(' Mono' if mono else ' Sans'); sub=style+(' Oblique' if oblique else '')
    data=alphabet(variant,mono); cmap={ord(c):name(c) for c in data}; order=['.notdef']+[cmap[c] for c in sorted(cmap)]
    glyphs={};metrics={};bounds=[];raw={};outlines={}
    nd=Polygon([(35,0),(35,700),(465,700),(465,0)],holes=[[(100,65),(400,65),(400,635),(100,635)]])
    raw['.notdef']=(contours(nd),MONO_ADVANCE if mono else 500,35)
    for ch,(w,paths) in data.items():
        g,adv,lsb=geometry(w,paths,variant,mono,thickness,oblique,ch)
        raw[name(ch)]=(contours(g),adv,lsb);outlines[ch]=g
        if not g.is_empty:bounds.append(g.bounds)
    ratio=stroke_ratio(thickness)
    slope=math.tan(math.radians(10)) if oblique else 0
    caron=Polygon([(0,0),(thickness*.20,0),(35+thickness*.45,180),(35,180)])
    if oblique:caron=affine_transform(caron,[1,slope,0,1,0,0])
    raw['caron.alt']=(contours(caron),0,0)
    def mark_anchor(c):
        y=thickness*ratio/2
        x=85*.91 if c=='\u0328' else 0
        return round(x+slope*y-(18 if oblique else 0)),round(y)
    def base_anchor(c,mark):
        g=outlines[c];advance=raw[name(c)][1]
        below=mark in '\u0327\u0328\u0326'
        y=0 if below else g.bounds[3]+40
        x=advance/2+slope*y-(18 if oblique else 0)
        if mark=='\u0328':
            foot=g.intersection(LineString([(-2000,y+2),(4000,y+2)]))
            if not foot.is_empty:x=foot.bounds[2]-thickness*.25
        return round(x),round(y)
    components={}
    for ch in data:
        parts=unicodedata.normalize('NFD',ch)
        if len(parts)!=2 or any(c not in data for c in parts):continue
        base,mark=parts;body=base
        if ch=='ģ':mark='\u0312'
        elif ch in 'ĢĶķĻļŅņŖŗŢţ':mark='\u0326'
        if mark not in '\u0327\u0328\u0326':
            if base in 'iі':body='ı'
            elif base=='j':body='ȷ'
        advance=raw[name(base)][1]
        body_dx=round((advance-raw[name(body)][1])/2)
        bx,by=base_anchor(body,mark);mx,my=mark_anchor(mark)
        dx,dy=bx+body_dx-mx,by-my
        sx=1;mark_name=name(mark);mark_g=outlines[mark]
        if ch in 'ďĽľť':
            if mono and ch=='ď':
                sx=.8;body_dx=round(outlines[body].bounds[0]*(1-sx))
            body_g=affine_transform(outlines[body],[sx,0,0,1,body_dx,0])
            top=body_g.bounds[3]
            stem=body_g.intersection(LineString([(-2000,top-40),(4000,top-40)]))
            dx=round(stem.bounds[2]+24);dy=round(max(700,top)-180)
            mark_name='caron.alt';mark_g=caron
        g=unary_union([affine_transform(outlines[body],[sx,0,0,1,body_dx,0]),affine_transform(mark_g,[1,0,0,1,dx,dy])])
        if not mono and ch in 'ďĽľť':advance=max(advance,math.ceil(g.bounds[2]+34))
        raw[name(ch)]=(contours(g),advance,math.floor(g.bounds[0]));outlines[ch]=g
        body_name=name(body)
        if sx!=1:
            # Keep the Mono side-caron base as a drawn alternate; scaled components fail raster checks.
            body_name+='.caron'
            raw[body_name]=(contours(body_g),advance,math.floor(body_g.bounds[0]))
            body_dx=0;sx=1
        # Joined ogoneks use the existing union, avoiding overlapping TTF components.
        if mark!='\u0328':components[name(ch)]=[(body_name,body_dx,0,sx),(mark_name,dx,dy,1)]
    bounds=[g.bounds for g in outlines.values() if not g.is_empty]
    for c in '0123456789':
        gn=name(c);cs,adv,lsb=raw[gn]
        if mono:raw[gn+'.pnum']=(cs,adv,lsb)
        else:
            lo=min(x for q in cs for x,y in q);hi=max(x for q in cs for x,y in q)
            dx=40-lo;new=[[(x+dx,y) for x,y in q] for q in cs]
            raw[gn+'.pnum']=(new,round(hi-lo+80),40)
    for c in '()[]{}-–—':
        gn=name(c);cs,adv,lsb=raw[gn];lo=min(y for q in cs for x,y in q);hi=max(y for q in cs for x,y in q)
        dy=350-(hi+lo)/2;raw[gn+'.case']=([[(x,round(y+dy)) for x,y in q] for q in cs],adv,lsb)
    order += [gn for gn in raw if gn not in order]
    for gn,(cs,adv,lsb) in raw.items():
        pen=TTGlyphPen(None)
        for pts in cs:
            pen.moveTo(pts[0]);[pen.lineTo(p) for p in pts[1:]];pen.closePath()
        glyphs[gn]=pen.glyph();metrics[gn]=(adv,lsb)
    for gn,parts in components.items():
        pen=TTGlyphPen(glyphs)
        for base,dx,dy,sx in parts:pen.addComponent(base,(sx,0,0,1,dx,dy))
        glyphs[gn]=pen.glyph();glyphs[gn].components[0].flags|=OVERLAP_COMPOUND
    fb=FontBuilder(1000,isTTF=True);fb.setupGlyphOrder(order);fb.setupCharacterMap(cmap);fb.setupGlyf(glyphs);fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=1040,descent=-320,lineGap=0,caretSlopeRise=1000 if oblique else 1,caretSlopeRun=round(slope*1000))
    legacy=family if style in ['Regular','Bold'] else family+' '+style
    legacy_sub=('Italic' if oblique else 'Regular') if style!='Bold' else ('Bold Italic' if oblique else 'Bold')
    ps=family.replace(' ','')+'-'+sub.replace(' ','')
    names={'familyName':legacy,'styleName':legacy_sub,'typographicFamily':family,'typographicSubfamily':sub,'uniqueFontIdentifier':'SAB:1.100:'+ps,'fullName':family+' '+sub,'psName':ps,'version':'Version 1.100','designer':'SAB Type, 2026','manufacturer':'SAB Type','copyright':'Copyright 2026 Andrew Sabynin (https://sabynin.com/)','description':'SAB Modul is an original type family designed for text, interfaces and display use.','licenseDescription':'This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org. Reserved Font Name: SAB Modul. Modified Versions may not use the Reserved Font Name without explicit written permission of the copyright holder.'}
    fb.setupNameTable(names,mac=False)
    buildStatTable(fb.font,[{'tag':'wght','name':'Weight','ordering':0,'values':[{'value':weight,'name':style,'flags':2 if weight==400 else 0}]},
                           {'tag':'ital','name':'Italic','ordering':1,'values':[{'value':int(oblique),'name':'Oblique' if oblique else 'Roman','flags':0 if oblique else 2,**({} if oblique else {'linkedValue':1})}]}],elidedFallbackName=2,macNames=False)
    fs=(1 if oblique else 0)|(32 if style=='Bold' else 0)|(64 if style!='Bold' and not oblique else 0)|128
    fb.setupOS2(version=4,sTypoAscender=1040,sTypoDescender=-320,sTypoLineGap=0,usWinAscent=max(1040,math.ceil(max(b[3] for b in bounds))),usWinDescent=max(320,math.ceil(-min(b[1] for b in bounds))),usWeightClass=weight,usWidthClass=5,fsType=0,fsSelection=fs,sxHeight=XHEIGHT,sCapHeight=700)
    fb.font['OS/2'].recalcCodePageRanges(fb.font)
    fb.font['OS/2'].panose.bFamilyType=2
    fb.font['OS/2'].panose.bProportion=9 if mono else 0
    fb.font['head'].fontRevision=1.1
    # Truncate the nonzero advance average for Font Validator compatibility.
    widths=[width for width,_ in fb.font['hmtx'].metrics.values() if width]
    fb.font['OS/2'].xAvgCharWidth=sum(widths)//len(widths)
    fb.setupPost(italicAngle=-10 if oblique else 0,isFixedPitch=1 if mono else 0,underlinePosition=-110,underlineThickness=50)
    fb.setupMaxp();fb.font['head'].macStyle=(1 if style=='Bold' else 0)|(2 if oblique else 0)
    features=['languagesystem DFLT dflt;','languagesystem latn dflt;','languagesystem cyrl dflt;']
    # Compositions also make keyboard-entered combining sequences usable.
    cc=[]
    for ch in data:
        parts=unicodedata.normalize('NFD',ch)
        if len(parts)>1 and all(p in data for p in parts):cc.append('sub '+' '.join(name(p) for p in parts)+' by '+name(ch)+';')
    if cc:features.append('feature ccmp {'+'\n'.join(cc)+'} ccmp;')
    markchars=[c for c in data if unicodedata.combining(c)]
    for c in markchars:
        group='ogonek' if c=='\u0328' else 'bottom' if c in '\u0327\u0326' else 'top'
        features.append('markClass %s <anchor %d %d> @%s;'%(name(c),*mark_anchor(c),group))
    positions=[]
    for c,(w,paths) in data.items():
        if not c.isalpha() or unicodedata.combining(c):continue
        gn=name(c);adv=raw[gn][1];cs=raw[gn][0]
        if not cs:continue
        positions.append('pos base %s <anchor %d %d> mark @top <anchor %d %d> mark @bottom <anchor %d %d> mark @ogonek;'%(gn,*base_anchor(c,'\u0301'),*base_anchor(c,'\u0327'),*base_anchor(c,'\u0328')))
    features.append('feature mark {'+'\n'.join(positions)+'} mark;')
    features.append('feature pnum {'+' '.join('sub %s by %s.pnum;'%(name(c),name(c)) for c in '0123456789')+'} pnum;')
    features.append('feature tnum {'+' '.join('sub %s.pnum by %s;'%(name(c),name(c)) for c in '0123456789')+'} tnum;')
    features.append('feature case {'+' '.join('sub %s by %s.case;'%(name(c),name(c)) for c in '()[]{}-–—')+'} case;')
    if not mono:features.append(optical_kerning(data,raw,outlines,thickness,style,oblique))
    addOpenTypeFeaturesFromString(fb.font,'\n'.join(features))
    folder=ROOT;folder.mkdir(exist_ok=True)
    for fmt in formats:
        out=folder/fmt.upper();out.mkdir(exist_ok=True)
        if fmt=='otf':
            # CFF outlines are flattened; these TTF component helpers have no users.
            cff_order=[gn for gn in order if gn not in {'caron.alt',name('d')+'.caron'}]
            ot=FontBuilder(1000,isTTF=False);ot.setupGlyphOrder(cff_order);ot.setupCharacterMap(cmap);ot.setupHorizontalMetrics({gn:metrics[gn] for gn in cff_order})
            strings={}
            for gn in cff_order:
                cs,adv,lsb=raw[gn]
                pen=T2CharStringPen(adv,None)
                for pts in cs:
                    if not LinearRing(pts).is_simple:
                        # CFF unions can acquire sub-unit loops at accent joins after rounding.
                        filled=Polygon(pts).buffer(0)
                        repaired=set_precision(filled,1)
                        assert repaired.geom_type=='Polygon' and not repaired.interiors
                        assert repaired.bounds==filled.bounds and set_precision(repaired,0).symmetric_difference(make_valid(Polygon(pts))).area<=2
                        pts=list(orient(repaired,sign=1 if LinearRing(pts).is_ccw else -1).exterior.coords)[:-1]
                        assert LinearRing(pts).is_simple
                    pen.moveTo(pts[0]);[pen.lineTo(p) for p in pts[1:]];pen.closePath()
                strings[gn]=pen.getCharString()
            ot.setupCFF(ps,{'FullName':family+' '+sub,'FamilyName':family,'Weight':style,'version':'1.100'},strings,{'BlueValues':[-12,0,XHEIGHT,XHEIGHT+12,700,712], 'OtherBlues':[-232,-220], 'BlueFuzz':1})
            for table in ['name','OS/2','hhea','GPOS','GSUB','STAT']:
                if table in fb.font:ot.font[table]=fb.font[table]
            ot.setupPost(italicAngle=-10 if oblique else 0,isFixedPitch=1 if mono else 0,underlinePosition=-110,underlineThickness=50)
            ot.font['head'].macStyle=fb.font['head'].macStyle
            ot.font['head'].fontRevision=1.1
            ot.save(out/(ps+'.otf'))
        else:
            fb.font.flavor='woff2' if fmt=='woff2' else None;fb.save(out/(ps+'.'+fmt))
    return {'family':family,'style':sub,'weight':weight,'characters':len(data),'glyphs':len(order),'file':ps,'minY':math.floor(min(b[1] for b in bounds)),'maxY':math.ceil(max(b[3] for b in bounds))}

if __name__=='__main__':
    import sys
    sample='--sample' in sys.argv
    manifest=[]
    for variant in VARIANTS:
        for mono in (False,True):
            for style,(weight,thickness) in WEIGHTS.items():
                if sample and style not in ['Regular','Bold','Light']:continue
                for oblique in ((False,True) if sample and style=='Regular' else (False,) if sample else (False,True)):
                    manifest.append(build(variant,mono,style,weight,thickness,oblique,('ttf',) if sample else ('ttf','otf','woff2')))
            print(variant,'Mono' if mono else 'Sans',flush=True)
    (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
